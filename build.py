"""Build index.html: one self-contained page with d3, the data and the dashboard inlined.

When data/private/ holds the private house price file (not in git), also builds private.html: the same
page with the 4-5 bed layer, encrypted with StatiCrypt using the password kept in the macOS Keychain.
"""
import os, subprocess, sys
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


def page(datasets, title, head='', extra=''):
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Compare average weather across UK council areas and Met Office stations: temperature, rain, rain days, sunshine, frost and day length.">{head}
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
    print(f'private.html: {(ROOT / "private.html").stat().st_size / 1024:.0f} KiB, encrypted')


write('index.html', page(DATASETS, 'UK Climate Compare'))
build_private()
