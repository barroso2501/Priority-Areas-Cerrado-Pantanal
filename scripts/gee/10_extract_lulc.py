"""
10_extract_lulc.py — Annual land use/cover area per zone and class (Q1, Q6).
Also exports annual transitions (class in year t -> class in year t+1) per zone.

Output (Google Drive, folder in config.yml), one CSV per year:
  lulc_area_<year>.csv          columns: key, sum (ha), year    key = zone_id*1000 + class
  lulc_trans_<year>_<year+1>.csv columns: key, sum (ha), year    key = zone_id*10000 + from*100 + to
Decode with 90_collect_exports.py.

Run from the repository root:
  python scripts/gee/10_extract_lulc.py --test      # one year (2025), to check tasks finish
  python scripts/gee/10_extract_lulc.py             # all years (82 tasks)
  python scripts/gee/10_extract_lulc.py --no-transitions

Design notes:
  - No biome clipping (D11): the region is the bounding box of all zones; pixels outside
    the zones are masked by the zone raster, so only zone pixels are counted.
  - Reductions run in the native MapBiomas grid (crs + crsTransform), so pixels are not
    resampled. Area uses ee.Image.pixelArea() (true area of each pixel), in hectares.
  - Finest class extracted; aggregation happens later with the D8 legend table.

What can break, and how you would notice:
  - Tasks failing with "Computation timed out" or "User memory limit exceeded":
    raise export.tile_scale in config.yml (4 -> 8 -> 16) and re-run the failed years.
  - QC after collection: for each year, the summed area of all classes per zone must equal
    the zone area in zones_attributes.csv within ~1% (pixel-edge effects on small zones).
"""
import argparse

import ee

import gee_common as gc

ap = argparse.ArgumentParser()
ap.add_argument("--test", action="store_true")
ap.add_argument("--no-transitions", action="store_true")
args = ap.parse_args()

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4).rename("ha")
yrs = [gc.years()[-1]] if args.test else gc.years()

for y in yrs:
    cls = gc.lulc(y)
    key = zone.multiply(1000).add(cls).rename("key").int()
    g = gc.grouped_sum(key.addBands(area), 1, region)
    gc.export_groups(g, f"lulc_area_{y}", {"year": y})

    if not args.no_transitions and y < gc.years()[-1]:
        nxt = gc.lulc(y + 1)
        tkey = zone.multiply(10000).add(cls.multiply(100)).add(nxt).rename("key").int()
        g = gc.grouped_sum(tkey.addBands(area), 1, region)
        gc.export_groups(g, f"lulc_trans_{y}_{y + 1}", {"year": y})
