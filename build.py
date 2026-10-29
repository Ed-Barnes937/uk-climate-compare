"""Build the site: index.html (the list of dashboards) and climate.html (one self-contained page with d3,
the data and the dashboard inlined).

When data/private/ holds the private house price file (not in git), also builds private.html: the same
page with the 4-5 bed layer, encrypted with StatiCrypt using the password kept in the macOS Keychain.

python3 build.py --previews also redraws the link preview images in previews/ (needs Google Chrome).
"""
import csv, html, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).parent
DATASETS = {
    'monthly': 'uk_station_monthly_2006_2025.csv',
    'stations': 'uk_stations2.csv',
    'stationgrid': 'uk_station_grid_1991_2020.csv',
    'areas': 'uk_areas.csv',
    'areagrid': 'uk_area_grid_1991_2020.csv',
    'boundaries': 'uk_boundaries.json',
    'houses': 'uk_area_houses.csv',
}
PRIVATE_HOUSES = 'private/uk_area_houses_private.csv'
KEYCHAIN_SERVICE = 'uk-climate-compare-private'
STATICRYPT = 'staticrypt@3.5.4'
SITE = 'https://ed-barnes937.github.io/uk-house-dashboards/'
SITE_TITLE = 'House moving helpers'
SITE_DESCRIPTION = 'Tools for planning a move in the UK: where to live and what it costs.'
# The hub lists these in order, except hidden ones (still built and shareable, just not listed).
# planner.html is hand-written (it was the next-move-planner repo); build.py only keeps its preview tags current. houses.html is built by the private uk-house-history repo, which adds the
# same preview tags itself (keep its title and description in step with this entry).
DASHBOARDS = [
    {'slug': 'climate', 'file': 'climate.html', 'title': 'UK Climate Compare', 'locked': False, 'hidden': True,
     'description': 'Compare average weather across UK council areas and Met Office stations: temperature, rain, '
                    'rain days, sunshine, frost and day length.'},
    {'slug': 'planner', 'file': 'planner.html', 'title': 'Next Move Planner', 'locked': False, 'theme': 'green',
     'description': 'Plan selling your home and buying the next: deposit, stamp duty, borrowing and mortgage '
                    'deals compared by true cost.'},
    {'slug': 'climate-private', 'file': 'private.html', 'title': 'UK Climate Compare (private)', 'locked': True,
     'description': 'The climate dashboard with an extra layer of 4-5 bed detached house prices.'},
    {'slug': 'houses', 'file': 'houses.html', 'title': 'UK House Prices', 'locked': True,
     'description': 'Detached houses across Great Britain: what your budget buys, where prices have grown and '
                    'how often houses sell.'},
]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def inline(path):
    """Text going inside a <script> element."""
    text = read(path)
    assert '</script' not in text.lower(), f'{path} would close its script tag early'
    return text


def dataset(name, file):
    kind = 'application/json' if file.endswith('.json') else 'text/csv'
    return f'<script type="{kind}" data-dataset="{name}">{inline("data/" + file)}</script>'


FOOTER = """<footer class="site-foot">
  <p>Sources: Met Office historic station data and HadUK-Grid v1.3.2 (via the CEDA archive), &copy; Crown copyright, Met Office, used under the
  <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3</a>.
  Council area boundaries from the ONS Open Geography Portal; contains OS data &copy; Crown copyright and database right 2026.
  Town and village names &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> (ODbL).
  House prices: HM Land Registry Price Paid Data and UK House Price Index (OGL v3); Code-Point Open postcodes, contains OS data &copy; Crown copyright 2026; NISRA Northern Ireland House Price Index.{extra}
  Ireland and Isle of Man outlines from Natural Earth. Charts drawn with <a href="https://d3js.org">d3</a>.</p>
</footer>"""


def page(datasets, title, head, extra=''):
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>{head}
<style>
{read('src/theme.css')}
</style>
<script>{inline('vendor/d3.min.js')}</script>
</head>
<body>
<main>
{chr(10).join(dataset(n, f) for n, f in datasets.items())}
<script>{inline('src/standalone.js')}</script>
{read('src/dashboard.html')}
{FOOTER.format(extra=extra)}
</main>
</body>
</html>
"""


def dashboard(slug):
    return next(d for d in DASHBOARDS if d['slug'] == slug)


def social(title, description, url, image, locked=False):
    """Description and link preview (Open Graph) tags. Locked pages also ask search engines not to index them."""
    tags = [('name', 'description', description), ('property', 'og:type', 'website'),
            ('property', 'og:site_name', SITE_TITLE), ('property', 'og:title', title),
            ('property', 'og:description', description), ('property', 'og:url', url),
            ('property', 'og:image', image), ('property', 'og:image:width', '1200'),
            ('property', 'og:image:height', '630'), ('name', 'twitter:card', 'summary_large_image')]
    if locked:
        tags.append(('name', 'robots', 'noindex'))
    return ''.join(f'\n<meta {k}="{n}" content="{html.escape(v)}">' for k, n, v in tags)


def dashboard_social(d):
    return social(d['title'], d['description'], SITE + d['file'], f"{SITE}previews/{d['slug']}.png", d['locked'])


def hub():
    items = '\n'.join(f"""<li><a class="card" href="{d['file']}">
  <img src="previews/{d['slug']}-map.png" width="480" height="300" alt="">
  <span class="card-text"><span class="card-title">{html.escape(d['title'])}</span>{' <span class="tag">Password</span>' if d['locked'] else ''}
  <span class="card-desc">{html.escape(d['description'])}</span></span>
</a></li>""" for d in DASHBOARDS if not d.get('hidden'))
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE}</title>{social(SITE_TITLE, SITE_DESCRIPTION, SITE, SITE + 'previews/hub.png')}
<style>
{read('src/theme.css')}
{read('src/hub.css')}
</style>
</head>
<body>
<main class="hub">
<h1>{SITE_TITLE}</h1>
<p class="lede">{html.escape(SITE_DESCRIPTION)}</p>
<ul class="cards">
{items}
</ul>
</main>
</body>
</html>
"""


PREVIEW_MARKERS = ('<!-- preview tags: written by build.py -->', '<!-- /preview tags -->')


def update_preview_tags(d):
    """Rewrite the preview tags between the markers in a hand-written page."""
    text = read(d['file'])
    start, end = PREVIEW_MARKERS
    assert text.count(start) == 1 and text.count(end) == 1, f"{d['file']}: expected one {start} ... {end} block"
    before, rest = text.split(start)
    write(d['file'], before + start + dashboard_social(d) + '\n' + end + rest.split(end)[1])


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')
    print(f'{path}: {len(text.encode()) / 1024:.0f} KiB')


def build_private():
    if not (ROOT / 'data' / PRIVATE_HOUSES).exists():
        print(f'private.html: skipped, no data/{PRIVATE_HOUSES}')
        return
    pw = subprocess.run(['security', 'find-generic-password', '-s', KEYCHAIN_SERVICE, '-w'], capture_output=True, text=True)
    if pw.returncode:
        sys.exit(f'private.html: no password in the Keychain. Add one with:\n  security add-generic-password -a "$USER" -s {KEYCHAIN_SERVICE} -w')
    (ROOT / 'build').mkdir(exist_ok=True)
    write('build/private.html', page(
        {**DATASETS, 'houses': PRIVATE_HOUSES}, 'UK Climate Compare (private)',
        head='\n<meta name="robots" content="noindex">',
        extra='\n  Bedroom counts and Scottish sold prices from Rightmove, for personal use only.'
              '\n  <a href="houses.html">Detached house prices by area</a> (same password).'))
    subprocess.run(
        ['npx', '-y', STATICRYPT, 'build/private.html', '-d', '.', '-c', '.staticrypt.json', '--short',
         '--remember', '0', '--template-title', 'UK Climate Compare', '--template-button', 'Open',
         '--template-instructions', 'This version includes 4-5 bed house prices and is password protected.',
         '--template-placeholder', 'Password', '--template-error', 'Wrong password',
         '--template-color-primary', '#d9622b', '--template-color-secondary', '#f6f5f1'],
        cwd=ROOT, check=True, env={**os.environ, 'STATICRYPT_PASSWORD': pw.stdout.rstrip('\n')}, stdout=subprocess.DEVNULL)
    # Link previews only see the password screen, so its head gets the preview tags.
    out = ROOT / 'private.html'
    text = out.read_text(encoding='utf-8')
    charset = '<meta charset="utf-8" />'  # as StatiCrypt's template writes it; the tags go right after it
    assert text.count(charset) == 1, f'private.html: expected one {charset} in the StatiCrypt page'
    out.write_text(text.replace(charset, charset + dashboard_social(dashboard('climate-private')), 1), encoding='utf-8')
    print(f'private.html: {out.stat().st_size / 1024:.0f} KiB, encrypted')


def previews():
    """Draw a 1200x630 link preview image per page into previews/: the title next to a map of the areas.

    The maps are shaded with public data only (July highs, or the public Land Registry detached prices), never
    the private layers, since the images are not encrypted.
    """
    rings = json.loads(read('data/' + DATASETS['boundaries']))
    with open(ROOT / 'data' / DATASETS['areagrid'], encoding='utf-8') as f:
        july = {r['id']: float(r['tmax']) for r in csv.DictReader(f) if r['month'] == '7'}
    with open(ROOT / 'data' / DATASETS['houses'], encoding='utf-8') as f:
        # Northern Ireland stays grey: the house prices dashboard does not cover it.
        price = {r['id']: float(r['price']) for r in csv.DictReader(f) if r['price'] and not r['id'].startswith('N')}
    shading = {
        'climate': (july, ['#3b6fb6', '#9fc3dc', '#f3e3b5', '#f0a35a', '#c8452b']),
        'houses': (price, ['#fbe9d9', '#f4b98a', '#e5803f', '#b9531c', '#6e2c0c']),
    }
    x0, x1 = min(p[0] for a in rings for r in a['rings'] for p in r), max(p[0] for a in rings for r in a['rings'] for p in r)
    y0, y1 = min(p[1] for a in rings for r in a['rings'] for p in r), max(p[1] for a in rings for r in a['rings'] for p in r)

    def ramp(values, stops):
        ranked = sorted(values.values())

        def colour(v):
            t = sum(r < v for r in ranked) / max(len(ranked) - 1, 1) * (len(stops) - 1)
            i = min(int(t), len(stops) - 2)
            a, b = (tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in stops[i:i + 2])
            return '#' + ''.join(f'{round(p + (q - p) * (t - i)):02x}' for p, q in zip(a, b))
        return colour

    def svg(kind):
        if kind == 'planner':
            return read('src/calculator.svg')
        values, stops = shading.get(kind, ({}, []))
        colour = ramp(values, stops) if values else None
        paths = []
        for a in rings:
            d = ''.join('M' + 'L'.join(f'{x - x0:.1f},{y1 - y:.1f}' for x, y in r) + 'Z' for r in a['rings'])
            fill = colour(values[a['id']]) if colour and a['id'] in values else '#e7e3da'
            paths.append(f'<path d="{d}" fill="{fill}"/>')
        return (f'<svg viewBox="0 0 {x1 - x0:.0f} {y1 - y0:.0f}" xmlns="http://www.w3.org/2000/svg">'
                f'<g stroke="#f6f5f1" stroke-width="0.6" stroke-linejoin="round" fill-rule="evenodd">{"".join(paths)}</g></svg>')

    cards = [('hub', SITE_TITLE, SITE_DESCRIPTION, False, 'houses')]
    cards += [(d['slug'], d['title'], d['description'], d['locked'], d['slug'].split('-')[0]) for d in DASHBOARDS]
    theme = {d['slug']: d.get('theme', '') for d in DASHBOARDS}
    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    (ROOT / 'previews').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='previews-') as tmp:
        for slug, title, description, locked, kind in cards:
            card = Path(tmp) / f'{slug}.html'
            card.write_text(f"""<!doctype html><meta charset="utf-8"><style>
{read('src/theme.css')}
{read('src/preview.css')}
</style><div class="preview {theme.get(slug, '')}"><div class="preview-text">
<p class="preview-site">{SITE_TITLE if slug != 'hub' else 'ed-barnes937.github.io'}</p>
<h1>{html.escape(title)}</h1><p class="preview-desc">{html.escape(description)}</p>
{'<p class="preview-lock">Password protected</p>' if locked else ''}</div>
<div class="preview-map">{svg(kind)}</div></div>""", encoding='utf-8')
            out = ROOT / 'previews' / f'{slug}.png'
            subprocess.run([chrome, '--headless=new', '--hide-scrollbars', '--force-device-scale-factor=1',
                            '--force-color-profile=srgb', '--window-size=1200,630', f'--screenshot={out}', card.as_uri()],
                           check=True, capture_output=True)
            print(f'previews/{slug}.png: {out.stat().st_size / 1024:.0f} KiB')
            if slug == 'hub':
                continue
            # The hub's thumbnail: the map alone, since the hub prints the title and description beside it.
            card.write_text(f"""<!doctype html><meta charset="utf-8"><style>{read('src/preview.css')}</style>
<div class="thumb {theme.get(slug, '')}">{svg(kind)}</div>""", encoding='utf-8')
            out = ROOT / 'previews' / f'{slug}-map.png'
            subprocess.run([chrome, '--headless=new', '--hide-scrollbars', '--force-device-scale-factor=2',
                            '--force-color-profile=srgb', '--window-size=480,300', f'--screenshot={out}', card.as_uri()],
                           check=True, capture_output=True)


if '--previews' in sys.argv[1:]:
    previews()
write('index.html', hub())
write('climate.html', page(DATASETS, 'UK Climate Compare', dashboard_social(dashboard('climate'))))
update_preview_tags(dashboard('planner'))
build_private()
