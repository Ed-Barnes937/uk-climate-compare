"""Build index.html: one self-contained page with d3, the data and the dashboard inlined."""
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
  House prices: HM Land Registry Price Paid Data and UK House Price Index (OGL v3); Code-Point Open postcodes, contains OS data &copy; Crown copyright 2026; NISRA Northern Ireland House Price Index.
  Ireland and Isle of Man outlines from Natural Earth. Charts drawn with <a href="https://d3js.org">d3</a>.</p>
</footer>"""

page = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UK Climate Compare</title>
<meta name="description" content="Compare average weather across UK council areas and Met Office stations: temperature, rain, rain days, sunshine, frost and day length.">
<style>
{read('src/theme.css')}
</style>
<script>{inline('vendor/d3.min.js')}</script>
</head>
<body>
<main>
{chr(10).join(dataset(n, f) for n, f in DATASETS.items())}
<script>{inline('src/standalone.js')}</script>
{read('src/dashboard.html')}
{FOOTER}
</main>
</body>
</html>
"""
(ROOT / 'index.html').write_text(page, encoding='utf-8')
print(f'index.html: {len(page.encode()) / 1024:.0f} KiB')
