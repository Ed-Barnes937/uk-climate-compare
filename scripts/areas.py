import csv, json, numpy as np, netCDF4 as nc
from shapely.geometry import Polygon, MultiPolygon, MultiPoint, Point, box
from shapely.ops import unary_union, voronoi_diagram
from shapely import STRtree
from pyproj import Transformer
T = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
NATION = {'E': 'England', 'S': 'Scotland', 'W': 'Wales', 'N': 'Northern Ireland'}
VARS = {'tmax':'tasmax','tmin':'tasmin','rain':'rainfall','sun':'sun','af':'airfrost','raindays':'raindays1mm'}
grids = {}
for k, v in VARS.items():
    d = nc.Dataset(f'grid/{v}_hadukgrid_uk_5km_mon-30y_199101-202012.nc')
    grids[k] = np.ma.filled(d[v][:].astype(float), np.nan)
    xs, ys = np.array(d['projection_x_coordinate'][:]), np.array(d['projection_y_coordinate'][:])

def esri_to_shape(rings):
    # Esri: clockwise rings are outer, counter-clockwise are holes
    outers, holes = [], []
    for r in rings:
        p = Polygon(r)
        if not p.is_valid: p = p.buffer(0)
        a = sum(r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1] for i in range(len(r)-1))
        (outers if a < 0 else holes).append(p)
    shape = unary_union(outers)
    for h in holes: shape = shape.difference(h)
    return shape

lad = json.load(open('lad26.json'))['features']
areas, shapes = [], []
for f in lad:
    a = f['attributes']; s = esri_to_shape(f['geometry']['rings'])
    shapes.append(s)
    lon, lat = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform(a['BNG_E'], a['BNG_N'])
    areas.append(dict(id=a['LAD26CD'], name=a['LAD26NM'], nation=NATION[a['LAD26CD'][0]], lat=round(lat, 4), x=round(a['BNG_E']/1000, 1), y=round(a['BNG_N']/1000, 1)))

# Split very large council areas into pieces of roughly SPLIT_KM2: k-means on a 1 km land
# sample, Voronoi cells of the centres clipped to the council boundary, each piece named
# after its biggest OpenStreetMap place (city > town > village, then population, then
# nearest the piece's middle).
SPLIT_KM2 = 1000
RANK = {'city': 2, 'town': 1, 'village': 0}
places = []
for e in json.load(open('geo/osm_places.json'))['elements']:
    t = e['tags']
    name = t.get('name:en') or t.get('name')
    if not name: continue
    try: pop = int(str(t.get('population', '0')).replace(',', '').split()[0])
    except ValueError: pop = 0
    x, y = T.transform(e['lon'], e['lat'])
    places.append((Point(x, y), RANK[t['place']], pop, name))
ptree = STRtree([p[0] for p in places])

def kmeans(pts, k, seed=0):
    rng = np.random.default_rng(seed)
    cen = pts[[rng.integers(len(pts))]]
    while len(cen) < k:  # k-means++ seeding
        d2 = ((pts[:, None] - cen[None]) ** 2).sum(-1).min(1)
        cen = np.vstack([cen, pts[rng.choice(len(pts), p=d2 / d2.sum())]])
    for _ in range(100):
        lab = ((pts[:, None] - cen[None]) ** 2).sum(-1).argmin(1)
        new = np.array([pts[lab == i].mean(0) for i in range(k)])
        if np.allclose(new, cen): break
        cen = new
    return cen

COMPASS = ['east', 'north-east', 'north', 'north-west', 'west', 'south-west', 'south', 'south-east']
split_areas, split_shapes, nsplit = [], [], 0
for a, s in zip(areas, shapes):
    k = int(np.ceil(s.area / 1e6 / SPLIT_KM2))
    if k < 2:
        split_areas.append(dict(a, parent='')); split_shapes.append(s); continue
    nsplit += 1
    minx, miny, maxx, maxy = s.bounds
    gx, gy = np.meshgrid(np.arange(minx, maxx, 1000) + 500, np.arange(miny, maxy, 1000) + 500)
    cand = np.column_stack([gx.ravel(), gy.ravel()])
    from shapely import contains_xy
    pts = cand[contains_xy(s, cand[:, 0], cand[:, 1])]
    cen = kmeans(pts, k)
    vor = voronoi_diagram(MultiPoint([tuple(c) for c in cen]), envelope=box(minx - 1e5, miny - 1e5, maxx + 1e5, maxy + 1e5))
    cells = []
    for c in cen:
        cell = next(g for g in vor.geoms if g.contains(Point(c)))
        piece = cell.intersection(s)
        hits = [places[i] for i in ptree.query(piece, predicate='intersects')]
        mid = piece.representative_point()
        best = max(hits, key=lambda p: (p[1], p[2], -p[0].distance(mid)), default=None)
        cells.append((piece, best[3] if best else None))
    names = [n for _, n in cells]
    for i, (piece, town) in enumerate(cells):
        cx, cy = piece.representative_point().coords[0] if piece.centroid.within(piece) is False else piece.centroid.coords[0]
        if not town or names.count(town) > 1:
            ang = np.degrees(np.arctan2(cy - s.centroid.y, cx - s.centroid.x)) % 360
            town = f"{COMPASS[int(((ang + 22.5) % 360) // 45)]}"
            label = f"{a['name']} - {town}"
        else:
            label = f"{a['name']} - {town} area"
        lon, lat = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform(cx, cy)
        split_areas.append(dict(id=f"{a['id']}-{i + 1}", name=label, nation=a['nation'], lat=round(lat, 4), x=round(cx / 1000, 1), y=round(cy / 1000, 1), parent=a['name']))
        split_shapes.append(piece)
labels = [a['name'] for a in split_areas]
dups = {n for n in labels if labels.count(n) > 1}
assert not dups, dups
areas, shapes = split_areas, split_shapes
print('split', nsplit, 'councils; areas now', len(areas))

valid = ~np.isnan(grids['tmax'][0])
vy, vx = np.nonzero(valid)
sq = [box(xs[j]-2500, ys[i]-2500, xs[j]+2500, ys[i]+2500) for i, j in zip(vy, vx)]
tree = STRtree(sq)
rows, counts = [], []
for a, s in zip(areas, shapes):
    idx = list(tree.query(s, predicate='intersects'))
    wts = np.array([sq[i].intersection(s).area for i in idx])
    keep = wts > 0
    idx, wts = [idx[i] for i in range(len(idx)) if keep[i]], wts[keep]
    counts.append(len(idx))
    for m in range(12):
        row = {'id': a['id'], 'month': m+1}
        for k in VARS:
            vals = grids[k][m, vy[idx], vx[idx]]
            ok = ~np.isnan(vals)
            row[k] = round(float(np.average(vals[ok], weights=wts[ok])), 2) if ok.any() else ''
        rows.append(row)
    a['squares'] = round(float(wts.sum()) / 25e6, 1)

# boundaries for drawing: simplify ~400 m, km units
def rings_of(geom):
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    out = []
    for p in polys:
        if p.area < 1.5e6 and len(polys) > 1: continue
        for ring in [p.exterior] + list(p.interiors):
            c = [[round(x/1000, 1), round(y/1000, 1)] for x, y in ring.coords]
            if len(c) >= 4: out.append(c)
    return out
bounds = []
for a, s in zip(areas, shapes):
    bounds.append({'id': a['id'], 'rings': rings_of(s.simplify(400, preserve_topology=True))})

# context land (Ireland, Isle of Man) in km BNG
ctx = []
for r in json.load(open('met/uk_outline.json')):
    if r['uk']: continue
    ctx.append({'id': r['name'], 'rings': [[[round(v/1000, 1) for v in T.transform(lon, lat)] for lon, lat in ring] for ring in r['rings']]})

with open('met/uk_areas.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(areas[0])); w.writeheader(); w.writerows(areas)
with open('met/uk_area_grid_1991_2020.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['id','month'] + list(VARS)); w.writeheader(); w.writerows(rows)
json.dump(bounds + [dict(c, context=True) for c in ctx], open('met/uk_boundaries.json', 'w'), separators=(',', ':'))
print('areas', len(areas), 'squares min/median/max', min(counts), int(np.median(counts)), max(counts), 'tiny', sum(1 for c in counts if c<=2))

# full-resolution shapes (BNG metres) for later point-in-area lookups
import pickle
pickle.dump([(a['id'], s.wkb) for a, s in zip(areas, shapes)], open('grid/area_shapes.pkl', 'wb'))
