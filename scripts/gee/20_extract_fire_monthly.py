"""
20_extract_fire_monthly.py — Monthly burned area per zone, land-cover class of the same
year, and stability flag (D9). Feeds: fire in native vegetation vs. land use, late-dry-
season fire, fire in forest/vereda, and the separate "fire in transition" table.

Output (Drive), one CSV per year:
  fire_month_<year>.csv   columns: key, sum (ha), year
  key = ((zone_id * 2 + stable) * 100 + class) * 13 + month
    stable = 1 if the pixel is native vegetation in EVERY year of the full series
             (1985-2025, domain-level stability, D9 proposal (a)); 0 otherwise
    class  = MapBiomas LULC class of the same year (finest level, D8)
    month  = 1..12

Run from the repository root:
  python scripts/gee/20_extract_fire_monthly.py --test   # last year only
  python scripts/gee/20_extract_fire_monthly.py

Note: regime metrics (intervals) use only stable pixels (D9) and come from
21_extract_fire_intervals.py. This table is descriptive: burned area by domain, class,
month and year. Pixels with stable = 0 that burn while native are the "fire in
transition" set reported separately.

What can break, and how you would notice:
  - If the fire asset is not aligned with the LULC grid, MapBiomas will have resampled
    it; we still reduce in the LULC grid. Check after collection that annual burned area
    in the whole extent matches MapBiomas Fire platform statistics within a few percent.
  - Memory/time-outs: raise tile_scale in config.yml.
"""
import argparse

import ee

import importlib

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

ap = argparse.ArgumentParser()
ap.add_argument("--test", action="store_true")
args = ap.parse_args()

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4).rename("ha")
native = ee.List(gc.native_classes())

# Stable native (domain level): native in all years of the full series
is_native = [gc.lulc(y).remap(native, ee.List.repeat(1, native.size()), 0) for y in gc.years()]
stable = ee.ImageCollection(is_native).min().rename("stable")  # 1 only if native every year

yrs = [gc.years()[-1]] if args.test else gc.years()
for y in yrs:
    month = gc.fire_month(y)
    key = (zone.multiply(2).add(stable).multiply(100).add(gc.lulc(y))
           .multiply(13).add(month)).rename("key").int()
    key = key.updateMask(month.mask())  # only burned pixels
    g = gc.grouped_sum(key.addBands(area), 1, region)
    gc.export_groups(g, f"fire_month_{y}", {"year": y})
