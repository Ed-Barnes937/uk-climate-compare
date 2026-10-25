import re, json, glob
NAMES = {
 'aberporth':('Aberporth','Cardigan Bay coast','Wales'),
 'armagh':('Armagh','Armagh','Northern Ireland'),
 'ballypatrick':('Ballypatrick Forest','Antrim coast','Northern Ireland'),
 'bradford':('Bradford','Bradford','England'),
 'braemar':('Braemar','Cairngorms','Scotland'),
 'camborne':('Camborne','West Cornwall','England'),
 'cambridge':('Cambridge','Cambridge','England'),
 'cardiff':('Cardiff','Cardiff','Wales'),
 'chivenor':('Chivenor','Barnstaple, North Devon','England'),
 'cwmystwyth':('Cwmystwyth','Mid Wales uplands','Wales'),
 'dunstaffnage':('Dunstaffnage','Oban','Scotland'),
 'durham':('Durham','Durham','England'),
 'eastbourne':('Eastbourne','Eastbourne','England'),
 'eskdalemuir':('Eskdalemuir','Southern Uplands','Scotland'),
 'heathrow':('Heathrow','West London','England'),
 'hurn':('Hurn','Bournemouth','England'),
 'lerwick':('Lerwick','Shetland','Scotland'),
 'leuchars':('Leuchars','St Andrews, Fife','Scotland'),
 'lowestoft':('Lowestoft','Lowestoft, Suffolk','England'),
 'manston':('Manston','Margate & Ramsgate, Kent','England'),
 'nairn':('Nairn','Nairn, Moray Firth','Scotland'),
 'newtonrigg':('Newton Rigg','Penrith, Cumbria','England'),
 'oxford':('Oxford','Oxford','England'),
 'paisley':('Paisley','Glasgow','Scotland'),
 'ringway':('Ringway','Manchester','England'),
 'rossonwye':('Ross-on-Wye','Herefordshire','England'),
 'shawbury':('Shawbury','Shrewsbury, Shropshire','England'),
 'sheffield':('Sheffield','Sheffield','England'),
 'southampton':('Southampton','Southampton','England'),
 'stornoway':('Stornoway','Isle of Lewis','Scotland'),
 'suttonbonington':('Sutton Bonington','Nottingham & Loughborough','England'),
 'tiree':('Tiree','Inner Hebrides','Scotland'),
 'valley':('Valley','Anglesey','Wales'),
 'waddington':('Waddington','Lincoln','England'),
 'whitby':('Whitby','Whitby, North Yorkshire','England'),
 'wickairport':('Wick','Caithness','Scotland'),
 'yeovilton':('Yeovilton','Yeovil, Somerset','England'),
}
def num(s):
    s = s.replace('*','').replace('#','').replace('$','')
    try: return float(s)
    except: return None
stations, rows = [], []
for f in sorted(glob.glob('*.txt')):
    sid = f[:-4]
    lines = open(f, encoding='latin-1').read().splitlines()
    hdr = '\n'.join(lines[:6])
    ll = re.findall(r'Lat\s*(-?[\d.]+)\s*Lon\s*(-?[\d.]+)', hdr)
    el = re.findall(r'(\d+)\s*m(?:etres)?\s*amsl', hdr)
    cnt = {k:0 for k in ['tmax','tmin','af','rain','sun']}
    n = 0
    for ln in lines:
        p = ln.split()
        if len(p) >= 7 and p[0].isdigit() and len(p[0]) == 4:
            y, m = int(p[0]), int(p[1])
            if 2006 <= y <= 2025:
                r = dict(station=sid, year=y, month=m, tmax=num(p[2]), tmin=num(p[3]), af=num(p[4]), rain=num(p[5]), sun=num(p[6]))
                rows.append(r); n += 1
                for k in cnt:
                    if r[k] is not None: cnt[k] += 1
    name, place, nation = NAMES[sid]
    print(f"{sid:16} {ll[-1] if ll else None} el={el[-1] if el else None} months={n} {cnt}")
    if ll:
        stations.append(dict(station=sid, name=name, place=place, nation=nation, lat=float(ll[-1][0]), lon=float(ll[-1][1]), elevation_m=int(el[-1]) if el else None, months=n))
json.dump(stations, open('stations.json','w'))
json.dump([r for r in rows], open('monthly.json','w'), separators=(',',':'))
