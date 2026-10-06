"""
23_extract_fire_calibration.py — Product 2 (D15 §7): one extraction from which every
threshold variant of the fire-regime categories is computed offline, without new runs.

Instead of exporting the category of each pixel (22_extract_fire_regime.py does that for the
chosen thresholds), this script exports a pixel *signature* that holds what every variant
needs, and sums the stable area per zone x vegetation type x signature. The analysis script
(scripts/analysis/product2_calibration.py) then rebuilds the categories for each variant.

Signature of a stable pixel (full series 1985-2025, D15 §4):
  n3   number of closed intervals shorter than 3 years (1- or 2-year return), capped at 3
  n1   number of closed intervals of 1 year (fire in consecutive years), capped at 3 (n1 <= n3)
  tsl  band of the last fire year:  0 last fire 2016-2025   1 2011-2015   2 2006-2010
                                    3 2001-2005             4 1985-2000   5 never burned
  cs   1 if the pixel kept the SAME land-cover class in every year (class-stable, D9 option b),
       0 if only stable as natural vegetation (the D15 universe is cs 0 + cs 1)
What each variant reads from it:
  below expected, maximum N years:  N=10 -> tsl>=1, N=15 -> tsl>=2, N=20 -> tsl>=3,
                                    N=25 -> tsl>=4  (never burned always included)
  above expected, k short intervals: n3 >= k (k = 1, 2, 3); annual fire only: n1 >= k
  forest affected by fire: tsl < 5

Three export tasks (Drive, CSV):
  fire_calib_fy     fire years (April..March), as in the product
                    key = (((zone*5 + type)*16 + n3*4 + n1)*6 + tsl)*2 + cs ; sum = stable ha
  fire_calib_cy     same signature on calendar years (sensitivity, D15 §7)
  fire_calib_month  burned area by calendar month and latitude band, per sub-period, for the
                    critical-window shifts (D15 §7):
                    key = (zone*5 + type)*4 + latband
                    latband 0 south of 18 S, 1 18-12 S, 2 12-8 S, 3 north of 8 S
                    sum = [sp1_m01_ha .. sp1_m12_ha, sp2_m01_ha .. sp2_m12_ha] (pixel area x
                    calendar years of the sub-period burned in that month)
Decoded by 90_collect_exports.py into fire_calib.parquet and fire_calib_month.parquet.

Run from the repository root (or the Colab notebook, step 11):
  python scripts/gee/23_extract_fire_calibration.py

What can break, and how you would notice:
  - Memory or time-out: each task stacks 41 years like 22_extract_fire_regime.py. Raise
    export.tile_scale in config.yml to 8 or 16 and run again (only the failed task needs
    to run again: pass its name, e.g.  --only fire_calib_cy).
  - QC in 90_collect_exports.py: per zone and type, the stable area of fire_calib_fy must
    equal the stable area of fire_regime (same universe), and the shares rebuilt with the
    product thresholds (N=20, k=2) must equal the fire_regime classes.
"""
import argparse
import importlib

import ee

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

ap = argparse.ArgumentParser()
ap.add_argument("--only", nargs="*", default=None,
                help="run only these tasks (fire_calib_fy, fire_calib_cy, fire_calib_month)")
args, _ = ap.parse_known_args()
run = set(args.only) if args.only else {"fire_calib_fy", "fire_calib_cy", "fire_calib_month"}

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4)
R = gc.CFG["fire_regime"]
first_year, last_year = gc.years()[0], gc.years()[-1]
fy_start = int(R["fire_year_start_month"])

# --- Universe: identical to 22_extract_fire_regime.py ------------------------------------------
NAT = ee.List(gc.natural_vegetation_classes())
s0, s1 = int(R["stability"]["start"]), int(R["stability"]["end"])
ys = list(range(s0, s1 + 1))
nat_flags = [gc.lulc(y).remap(NAT, ee.List.repeat(1, NAT.size()), 0).toInt8() for y in ys]
stable = ee.ImageCollection(nat_flags).min().eq(1)
modal = ee.ImageCollection([gc.lulc(y).toInt16() for y in ys]).mode()
src, dst = [], []
for t, classes in R["types"].items():
    for c in classes:
        src.append(int(c)); dst.append(int(t))
vtype = modal.remap(src, dst, 0).rename("type")
universe = stable.And(vtype.gt(0))
# class-stable: the land-cover class equals the modal class in every year
same = [gc.lulc(y).toInt16().eq(modal).toInt8() for y in ys]
cstable = ee.ImageCollection(same).min().eq(1)


# --- Burn flags ---------------------------------------------------------------------------------
def month_img(y):
    """Month of burn (1-12), 0 where not burned; 0 everywhere for unmapped years."""
    if y < first_year or y > last_year:
        return ee.Image(0)
    return gc.fire_month(y).unmask(0)


def fire_year_flag(y):
    """1 if burned in fire year y (fy_start..12 of y, or 1..fy_start-1 of y+1)."""
    a = month_img(y)
    b = month_img(y + 1)
    return a.gte(fy_start).Or(b.gt(0).And(b.lt(fy_start))).toInt8()


def calendar_flag(y):
    return month_img(y).gt(0).toInt8()


# --- Signature ------------------------------------------------------------------------------------
# Last-fire bands: lower bounds of the last fire year, from the most recent band to the oldest.
TSL_EDGES = [last_year - 9, last_year - 14, last_year - 19, last_year - 24]   # 2016, 2011, 2006, 2001


def signature(flag_fn):
    """Return the signature code (n3*4 + n1)*6 + tsl for every pixel, using flag_fn(y)."""
    prev = ee.Image(0); n3 = ee.Image(0); n1 = ee.Image(0)
    for y in range(first_year, last_year + 1):
        f = flag_fn(y)
        gap = ee.Image(y).subtract(prev)
        closed = f.And(prev.gt(0))                     # an interval ends at this burn
        n3 = n3.add(closed.And(gap.lt(3)))
        n1 = n1.add(closed.And(gap.eq(1)))
        prev = prev.where(f, y)                        # prev ends as the last fire year (0 = never)
    n3 = n3.min(3); n1 = n1.min(3)
    tsl = (ee.Image(5)
           .where(prev.gt(0), 4)
           .where(prev.gte(TSL_EDGES[3]), 3)
           .where(prev.gte(TSL_EDGES[2]), 2)
           .where(prev.gte(TSL_EDGES[1]), 1)
           .where(prev.gte(TSL_EDGES[0]), 0))
    return n3.multiply(4).add(n1).multiply(6).add(tsl)


def export_signature(flag_fn, name, window):
    sig = signature(flag_fn)
    key = (zone.multiply(5).add(vtype).multiply(16 * 6).add(sig)
           .multiply(2).add(cstable)).rename("key").int().updateMask(universe)
    g = gc.grouped_sum(key.addBands(area.rename("stable_ha").updateMask(universe)), 1, region)
    gc.export_groups(g, name, {"window": window})


if "fire_calib_fy" in run:
    export_signature(fire_year_flag, "fire_calib_fy", f"fy{first_year}_{last_year}")
if "fire_calib_cy" in run:
    export_signature(calendar_flag, "fire_calib_cy", f"cy{first_year}_{last_year}")

# --- Burned area by month and latitude band, per sub-period ---------------------------------------
# One reduction with 24 value bands (12 months x 2 sub-periods): the universe is computed once.
if "fire_calib_month" in run:
    LAT = ee.Image.pixelLonLat().select("latitude")
    latband = ee.Image(0).where(LAT.gte(-18), 1).where(LAT.gte(-12), 2).where(LAT.gte(-8), 3)
    vals = []
    for sp in R["subperiods"]:
        for m in range(1, 13):
            cnt = ee.Image(0)
            for y in range(int(sp["start"]), int(sp["end"]) + 1):
                cnt = cnt.add(month_img(y).eq(m))       # calendar years burned in month m
            vals.append(cnt.multiply(area).rename(f"{sp['name']}_m{m:02d}_ha"))
    key = (zone.multiply(5).add(vtype).multiply(4).add(latband)
           .rename("key").int().updateMask(universe))
    g = gc.grouped_sum(key.addBands(ee.Image.cat(vals).updateMask(universe)), len(vals), region)
    gc.export_groups(g, "fire_calib_month", {"window": "sp_months"})
