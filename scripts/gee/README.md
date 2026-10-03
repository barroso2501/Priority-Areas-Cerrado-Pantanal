# Earth Engine extraction (Phase 1)

**Using Google Colab?** Open [`notebooks/colab_phase1_extraction.ipynb`](../../notebooks/colab_phase1_extraction.ipynb). It runs steps 4–6 below and explains what is stored where: the code in Drive `Trabalho/APCerrado`, the exports in `My Drive/APCerrado_gee_exports`.

Run order, from the repository root. Steps 1–2 are local; steps 3–6 need an Earth Engine account with a registered Cloud project (non-commercial use).

| Step | Command | What it does |
|---|---|---|
| 1 | `python scripts/build_zones.py` | Builds the flat zone partition (D7), ~20 min |
| 2 | `python scripts/gee/01_prepare_zones_upload.py` | Writes `data/interim/zones_upload.zip` (zone_id only, EPSG:4674, 10 m coverage simplification, 1e-6° snapping) |
| 3 | Code Editor → Assets → New → *Shape files* | Upload the zip; put its asset ID in `config.yml → zones_asset` |
| 4 | `python scripts/gee/00_discover_assets.py` | Lists MapBiomas assets; checks LULC Col. 11 years and class values (P8) and Fire Col. 5 (P7). Copy the IDs into `config.yml` and update the legend table |
| 5 | `python scripts/gee/10_extract_lulc.py --test`, then without `--test` | Annual area per zone × class, and annual transitions |
|   | `python scripts/gee/20_extract_fire_monthly.py --test`, then without | Monthly burned area per zone × class × stability flag |
|   | `python scripts/gee/21_extract_fire_intervals.py` | Fire-return intervals in stable native vegetation, with censoring (D9) |
| 6 | Download the Drive folder to `data/interim/gee_exports/`; run `python scripts/gee/90_collect_exports.py` | Decodes keys into long tables (Parquet) and runs the QC checks |

Offline check of the encodings and of the interval algorithm: `python tests/test_gee_logic.py`.

## Settings
- `config.yml` holds the Cloud project, asset IDs, export folder, `tile_scale` and the fire-interval windows.
- Extraction scripts refuse to run while any value is still `VERIFY` or a placeholder.

## Notes
- **Grid.** Reductions run in the native MapBiomas grid (CRS + transform of the LULC asset). Areas come from `ee.Image.pixelArea()` in hectares.
- **No biome clipping (D11).** The region is the bounding box of the zones. Pixels outside zones are masked by the zone raster.
- **Fire year.** Burn flags use the calendar year, provisionally; the fire-year definition is still open in D9.
