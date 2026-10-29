# UK House Dashboards

Dashboards for choosing where to live in the UK, served at https://ed-barnes937.github.io/uk-house-dashboards/.

The main one here is UK Climate Compare: average weather across UK council areas and Met Office climate stations (summer and winter temperatures, rainfall, days with rain, sunshine, air frosts and day length, for 2016-2025 or 2006-2025).

The pages are generated, so edit the sources and rebuild:

```sh
python3 build.py              # index.html, climate.html and (with data/private/) private.html
python3 build.py --previews   # also redraw the link preview images in previews/ (needs Google Chrome)
```

To add a dashboard, add an entry to `DASHBOARDS` in `build.py` (the hub lists them in order, and each gets a preview image), then rebuild with `--previews`.

| Path | What |
| --- | --- |
| `index.html` | The hub: a card per dashboard in `DASHBOARDS` |
| `climate.html` | UK Climate Compare: one self-contained page (d3 and all data inlined) |
| `previews/` | Link preview images (1200x630, `<slug>.png`) and the hub's map thumbnails (`<slug>-map.png`), drawn from public data only. Every page carries Open Graph tags pointing at its image; on the encrypted pages they are added to the password screen, which is all a link preview can see |
| `src/dashboard.html` | The dashboard: markup, styles, calcs and drawing |
| `src/standalone.js` | Small runtime the dashboard calls (`dash.calc`, `dash.data`, `dash.params`, ...): embedded datasets, picks and filters saved in `localStorage` |
| `src/theme.css` | Colour, spacing and type tokens, light and dark |
| `src/hub.css`, `src/preview.css` | Styles for the hub and the preview images |
| `data/` | Prepared datasets (below) |
| `private.html` | Password-protected build (StatiCrypt) with an extra 4-5 bed detached price layer from data that is not in this repo. `build.py` makes it when `data/private/` is present, using the password stored in the macOS Keychain under `uk-climate-compare-private`. |
| `houses.html` | Password-protected detached house prices dashboard, linked from the private page's footer. Built and encrypted (same salt and password, so "Remember me" carries across) by the private uk-house-history repo's `build.py --real --publish`; do not edit it here. |
| `scripts/` | The scripts that prepared `data/`, kept for reference. They expect the raw downloads (Met Office station files, HadUK-Grid netCDF, ONS boundaries, OpenStreetMap places) next to them and are not a one-command pipeline. |

## Method

- **Stations:** monthly means from the Met Office historic station data, needing 70% of years reported.
- **Council areas:** the HadUK-Grid 1991-2020 average over the area's 5 km squares, weighted by overlap, shifted to the chosen period by the inverse-distance-weighted difference between the nearest four stations' recent readings and their own 1991-2020 grid values.
- Councils over about 1,000 km² are split into pieces of about that size (k-means centres, Voronoi cells clipped to the council) and named after their biggest town or village.
- Days with rain are 1991-2020 grid values everywhere. Day length is calculated from latitude.
- Detached house price (`scripts/house.py`): England and Wales use the median of open-market detached sales over the latest 36 months of Land Registry Price Paid Data, placed in each area by postcode (blank under 30 sales). Scotland uses the council's UK HPI detached price; Northern Ireland estimates it from NISRA's NI detached price scaled by each council's overall price level. Both are scaled by the typical sales-median to HPI ratio across English and Welsh councils. No source records bedrooms.

## Sources

- Met Office historic station data and HadUK-Grid v1.3.2 (via CEDA), © Crown copyright, [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- Council boundaries: ONS Open Geography Portal, local authority districts May 2026. Contains OS data © Crown copyright and database right 2026.
- House prices: HM Land Registry Price Paid Data and UK House Price Index (OGL v3), NISRA Northern Ireland House Price Index, Code-Point Open postcodes (contains OS data © Crown copyright 2026).
- Place names © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL).
- Ireland and Isle of Man outlines: Natural Earth.
- [d3](https://d3js.org) v7.9.0 (ISC licence) in `vendor/`.
