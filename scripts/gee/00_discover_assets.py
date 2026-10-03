"""
00_discover_assets.py — Find and check the MapBiomas assets before any extraction.
Closes open issues P7 (fire collection/period) and P8 (Collection 11 pixel values).

What it does:
  1. Lists every asset under the search roots in config.yml (LULC and fire folders),
     so you can copy the exact Collection 11 / Fire Collection 5 IDs into config.yml.
  2. If lulc_asset is filled in: prints its bands (years), checks 1985-2025 are all present,
     and computes the histogram of class values inside the study extent for 1985 and 2025
     (sampled at 300 m to stay fast). It writes data/reference/col11_class_values_found.csv
     and compares them with the legend grouping table (D8).
  3. If fire_monthly_asset is filled in: prints its bands and checks the year range and
     the value range (expected months 1-12).

Run from the repository root:   python scripts/gee/00_discover_assets.py

What can break, and how you would notice:
  - "Permission denied"/"not found" on a search root: MapBiomas reorganized its folders.
    Look up the current path on the MapBiomas download/toolkit pages and edit config.yml.
  - Class values >= 100 are reported as an error: the key encodings in gee_common.py
    assume classes < 100 and must be changed before extraction.
  - Classes present in the data but absent from the legend table are listed: add them
    to data/reference/mapbiomas_col11_legend_groups.csv (pixel_id_status = verified).
"""
import ee
import pandas as pd

import importlib

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

gc.init()
m = gc.CFG["mapbiomas"]

# 1) List assets under the search roots (two levels deep) -------------------------------
def walk(root, depth=0):
    try:
        for a in ee.data.listAssets({"parent": root}).get("assets", []):
            print("  " * depth + f"{a['type']:<16} {a['name']}")
            if a["type"] == "FOLDER" and depth < 2:
                walk(a["name"], depth + 1)
    except Exception as e:  # folder moved or not public
        print("  " * depth + f"!! cannot list {root}: {e}")

for root in m["search_roots"]:
    print(f"\n# {root}")
    walk(root)

zone_img, extent = gc.zones_image()  # zone raster + precomputed bounding box (config.yml, zones_bbox)

# 2) LULC asset checks ----------------------------------------------------------------
if m["lulc_asset"] != "VERIFY":
    img = ee.Image(m["lulc_asset"])
    bands = img.bandNames().getInfo()
    want = [m["lulc_band_pattern"].format(year=y) for y in gc.years()]
    missing = [b for b in want if b not in bands]
    print(f"\nLULC bands: {len(bands)} ({bands[0]} … {bands[-1]}); missing years: {missing or 'none'}")
    rows = []
    for y in (gc.years()[0], gc.years()[-1]):
        h = img.select(m["lulc_band_pattern"].format(year=y)).updateMask(zone_img.mask()).reduceRegion(
            ee.Reducer.frequencyHistogram(), extent, scale=300, maxPixels=1e10, tileScale=4).getInfo()
        for k, v in list(h.values())[0].items():
            rows.append({"year": y, "pixel_value": int(float(k)), "n_samples_300m": v})
    found = pd.DataFrame(rows)
    found.to_csv(gc.ROOT / "data/reference/col11_class_values_found.csv", index=False)
    vals = sorted(found.pixel_value.unique())
    print("class values present:", vals)
    if max(vals) >= 100:
        print("ERROR: class values >= 100 break the key encodings in gee_common.py")
    lg = pd.read_csv(gc.LEGEND)
    known = set(lg.pixel_id.dropna().astype(int))
    print("present but not in legend table:", sorted(set(vals) - known) or "none")
    print("in legend table but not present in extent:", sorted(known - set(vals)) or "none")

# 3) Fire asset checks ----------------------------------------------------------------
if m["fire_monthly_asset"] != "VERIFY":
    f = ee.Image(m["fire_monthly_asset"])
    fb = f.bandNames().getInfo()
    want = [m["fire_monthly_band_pattern"].format(year=y) for y in gc.years()]
    print(f"\nFire bands: {len(fb)}; missing years: {[b for b in want if b not in fb] or 'none'}")
    mm = f.select(want[-1]).reduceRegion(ee.Reducer.minMax(), extent, scale=300,
                                          maxPixels=1e10, tileScale=4).getInfo()
    print("value range in last year (expect 1-12):", mm)
