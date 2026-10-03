"""
21_extract_fire_intervals.py — Fire-return intervals in STABLE native vegetation (D9),
including never-burned pixels and censored intervals, per zone and modal class.

For each analysis window [a, b] in config.yml (fire_intervals.windows):
  - Stable pixel: native vegetation in every year a..b (domain level, D9 proposal (a)).
    Transitioning pixels are excluded from the regime assessment.
  - Annual burn flag: burned in any month of the calendar year (fire-year definition is
    still open in D9; calendar year is the provisional rule).
  - Interval types, in years (lengths are lower bounds when censored):
      closed_L : between two consecutive fires, L = y2 - y1
      left_L   : before the first fire,  L = first - a + 1   (left-censored)
      right_L  : after the last fire,    L = b - last + 1    (right-censored)
      never    : no fire in the window,  L = b - a + 1       (fully censored)
  - Every count is weighted by pixel area, so values are "hectares of pixels with that
    interval"; a pixel with 3 closed intervals contributes 3 times its area.

Output (Drive): fire_intervals_<window>.csv  columns: key, sum (list), window
  key = zone_id * 100 + modal_class ; sum = list of band totals in this order:
  [stable_ha, never_ha, closed_1..closed_{W-1}, left_1..left_W, right_1..right_W]
  where W = b - a + 1. 90_collect_exports.py expands the list into a long table.

Run from the repository root:   python scripts/gee/21_extract_fire_intervals.py

What can break, and how you would notice:
  - Heavy computation (41-year stacks): raise tile_scale to 8 or 16 if the task fails.
  - QC after collection, per zone and class: never_ha + (left_ha summed over L) must equal
    stable_ha; every stable pixel has either no fire or exactly one first fire. The same
    holds for right-censored intervals. A mismatch means the interval logic or the burn
    flag is wrong.
"""
import ee

import gee_common as gc

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4)
native = ee.List(gc.native_classes())

for w in gc.CFG["fire_intervals"]["windows"]:
    a, b = w["start"], w["end"]
    ys = list(range(a, b + 1))
    W = len(ys)

    lulc = {y: gc.lulc(y) for y in ys}
    is_nat = [lulc[y].remap(native, ee.List.repeat(1, native.size()), 0) for y in ys]
    stable = ee.ImageCollection(is_nat).min().eq(1)
    modal = ee.ImageCollection([lulc[y] for y in ys]).mode().rename("modal")
    burned = {y: gc.fire_month(y).mask().gt(0).unmask(0) for y in ys}

    # Running "year of the previous fire" (0 = none yet); closed interval at each burn
    prev = ee.Image(0)
    closed_bands = []
    for y in ys:
        b_y = burned[y]
        closed_bands.append(b_y.And(prev.gt(0)).multiply(ee.Image(y).subtract(prev)))  # 0 if none
        prev = prev.where(b_y, y)
    last = prev  # last fire year, 0 if never
    first = ee.ImageCollection([burned[y].multiply(y).selfMask() for y in ys]).min().unmask(0)
    closed_stack = ee.Image.cat(closed_bands)

    bands = [area.rename("stable_ha"),
             first.eq(0).multiply(area).rename("never_ha")]
    for L in range(1, W):
        bands.append(closed_stack.eq(L).reduce(ee.Reducer.sum()).multiply(area).rename(f"closed_{L}"))
    left_len = ee.Image(-a + 1).add(first)    # first - a + 1
    right_len = ee.Image(b + 1).subtract(last)  # b - last + 1
    for L in range(1, W + 1):
        bands.append(first.gt(0).And(left_len.eq(L)).multiply(area).rename(f"left_{L}"))
    for L in range(1, W + 1):
        bands.append(last.gt(0).And(right_len.eq(L)).multiply(area).rename(f"right_{L}"))

    values = ee.Image.cat(bands).updateMask(stable)
    key = zone.multiply(100).add(modal).rename("key").int().updateMask(stable)
    g = gc.grouped_sum(key.addBands(values), len(bands), region)
    gc.export_groups(g, f"fire_intervals_{w['name']}", {"window": w["name"], "W": W})
