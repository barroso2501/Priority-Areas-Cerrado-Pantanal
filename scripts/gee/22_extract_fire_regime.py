"""
22_extract_fire_regime.py — Product 2 (D15): fire-regime class of every pixel of natural
vegetation stable 1985-2025, aggregated per zone x vegetation type x regime class, with
change metrics per sub-period.

Settings: config.yml -> fire_regime. Definitions (D15):
  stable pixel   natural vegetation (MapBiomas level 1 classes 1-2) in every year 1985-2025
  type           by modal class 1985-2025: 1 forest (3, 6), 2 savanna (4), 3 grassland (12),
                 4 wetland (11, 7); other natural classes are left out
  fire year y    burned in April..December of y, or January..March of y+1
                 (y = last mapped year: April..December only)
  category       on the full series of fire years 1985-2025 (D15, revised 2026-10-06):
     forest       1 not affected by fire (no fire in 41 fire years), 2 affected by fire
     savanna, grassland (wetland reported with the same rule, without interpretation)
                  1 above expected: at least `excess_short_intervals` (2) intervals shorter
                    than `expected_min` (3 years), i.e. repeated annual or biennial fire
                  2 as expected: everything else (intervals mostly within 3-20 years)
                  3 below expected: no fire in the last `expected_max` (20) fire years,
                    never-burned pixels included
     "Below expected" is assigned first: it describes the current state even when the
     pixel burned too often in the past.

Output (Drive): fire_regime.csv  columns: key, sum (list of 11 ha values), window
  key = zone_id * 100 + type * 10 + class
  sum = [stable_ha,
         sp1_fireyears_ha, sp1_consec_ha, sp1_season_ha, sp1_nonatural_ha, sp1_burned_ha,
         sp2_fireyears_ha, sp2_consec_ha, sp2_season_ha, sp2_nonatural_ha, sp2_burned_ha]
    *_fireyears_ha  pixel area x number of burned fire years in the sub-period
                    (burned fraction per year = fireyears / (stable_ha x years))
    *_consec_ha     area with at least one pair of consecutive burned fire years in it
    *_season_ha     pixel area x number of calendar years of the sub-period burned in the
                    critical window of the pixel's latitude band (season_bands: July-September
                    south of 12 S, August-October north of 12 S)
    *_nonatural_ha  same, for July-August (sem ignição natural: no lightning in these months)
    *_burned_ha     pixel area x number of calendar years of the sub-period burned at all
                    (seasonal ratio = season_ha / burned_ha)
Decoded by 90_collect_exports.py into fire_regime.parquet.

Run from the repository root (or the Colab notebook, step 10):
  python scripts/gee/22_extract_fire_regime.py

Variant by latitude band (Colab step 12; for the executive summary, matrix of the same band):
  python scripts/gee/22_extract_fire_regime.py --latband
  Output fire_regime_lat.csv: key = ((zone*4 + latband)*5 + type)*10 + class, sum = stable ha
  latband 0 south of 18 S, 1 18-12 S, 2 12-8 S, 3 north of 8 S (per pixel). The sub-period
  metrics are not computed in this variant (lighter task).

What can break, and how you would notice:
  - Memory or time-out (41-year stacks, as in 21_extract_fire_intervals.py): raise
    export.tile_scale to 8 or 16 and run again.
  - QC in 90_collect_exports.py: per zone and type, the sum of stable_ha over classes must
    equal the stable area of that modal class in fire_intervals (same stability rule).
  - The month band of the fire product holds one month per pixel and year. A pixel burned
    twice in the same calendar year counts once; the fire-year rule is therefore a lower
    bound for very frequent fire.
"""
import argparse
import importlib

import ee

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

ap = argparse.ArgumentParser()
ap.add_argument("--latband", action="store_true", help="stable area per latitude band only")
args, _ = ap.parse_known_args()

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4)
R = gc.CFG["fire_regime"]
T = R["thresholds"]
first_year, last_year = gc.years()[0], gc.years()[-1]
fy_start = int(R["fire_year_start_month"])

# --- Stable natural vegetation and vegetation type ---------------------------------------------
NAT = ee.List(gc.natural_vegetation_classes())
s0, s1 = int(R["stability"]["start"]), int(R["stability"]["end"])
ys = list(range(s0, s1 + 1))
# Same pixel type for every image of a collection (EE "homogeneous image collection" error)
nat_flags = [gc.lulc(y).remap(NAT, ee.List.repeat(1, NAT.size()), 0).toInt8() for y in ys]
stable = ee.ImageCollection(nat_flags).min().eq(1)
modal = ee.ImageCollection([gc.lulc(y).toInt16() for y in ys]).mode()
src, dst = [], []
for t, classes in R["types"].items():
    for c in classes:
        src.append(int(c)); dst.append(int(t))
vtype = modal.remap(src, dst, 0).rename("type")
universe = stable.And(vtype.gt(0))


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


LAT = ee.Image.pixelLonLat().select("latitude")


def in_months(m, months):
    out = ee.Image(0)
    for mm in months:
        out = out.Or(m.eq(int(mm)))
    return out


def calendar_flags(y):
    """Burned at all, burned in the critical window of the pixel's latitude band, and burned
    in the months without natural ignition, for calendar year y."""
    m = month_img(y)
    burned = m.gt(0)
    season = ee.Image(0)
    for band in R["season_bands"]:
        in_band = LAT.gte(band["lat_min"]).And(LAT.lt(band["lat_max"]))
        season = season.Or(in_band.And(in_months(m, band["months"])))
    nonat = in_months(m, R["no_natural_ignition_months"])
    return burned.toInt8(), season.toInt8(), nonat.toInt8()


# --- Regime category over the full series (fire years 1985-2025) ------------------------------
# The universe is stable over 41 years, so the category is judged over the same 41 years.
emin, emax = int(T["expected_min"]), int(T["expected_max"])        # expected interval, years
k_short = int(T["excess_short_intervals"])
n_all = ee.Image(0); last_fire = ee.Image(0); prev = ee.Image(0); n_short = ee.Image(0)
for y in range(first_year, last_year + 1):
    f = fire_year_flag(y)
    n_all = n_all.add(f)
    # closed interval ending at this burn, counted as short when below the expected minimum
    short = f.And(prev.gt(0)).And(ee.Image(y).subtract(prev).lt(emin))
    n_short = n_short.add(short)
    prev = prev.where(f, y)
    last_fire = last_fire.where(f, y)
# below expected: no fire in the last `expected_max` fire years (never burned included)
deficit = n_all.eq(0).Or(last_fire.lte(last_year - emax))
# above expected: repeated short intervals (one isolated short interval is not excess)
excess = n_short.gte(k_short)
open_cls = (ee.Image(2)                    # 2 as expected
            .where(excess, 1)              # 1 above expected
            .where(deficit, 3))            # 3 below expected (current state wins)
forest_cls = ee.Image(1).where(n_all.gt(0), 2)    # 1 not affected by fire, 2 affected
cls = open_cls.where(vtype.eq(1), forest_cls).rename("cls")

# --- Variant: stable area per zone x latitude band x type x class --------------------------------
if args.latband:
    LATB = ee.Image(0).where(LAT.gte(-18), 1).where(LAT.gte(-12), 2).where(LAT.gte(-8), 3)
    key = (zone.multiply(4).add(LATB).multiply(5).add(vtype).multiply(10).add(cls)
           .rename("key").int().updateMask(universe))
    g = gc.grouped_sum(key.addBands(area.rename("stable_ha").updateMask(universe)), 1, region)
    gc.export_groups(g, "fire_regime_lat", {"window": f"fy{first_year}_{last_year}"})

# --- Sub-period change metrics -----------------------------------------------------------------
if not args.latband:
    bands = [area.rename("stable_ha")]
    for sp in R["subperiods"]:
        a, b = int(sp["start"]), int(sp["end"])
        nfy = ee.Image(0); cons = ee.Image(0); seas = ee.Image(0); nolt = ee.Image(0); burn = ee.Image(0)
        prev_flag = None
        for y in range(a, b + 1):
            f = fire_year_flag(y)
            nfy = nfy.add(f)
            if prev_flag is not None:
                cons = cons.Or(f.And(prev_flag))
            prev_flag = f
            bu, se, nl = calendar_flags(y)
            burn = burn.add(bu); seas = seas.add(se); nolt = nolt.add(nl)
        name = sp["name"]
        bands += [nfy.multiply(area).rename(f"{name}_fireyears_ha"),
                  cons.multiply(area).rename(f"{name}_consec_ha"),
                  seas.multiply(area).rename(f"{name}_season_ha"),
                  nolt.multiply(area).rename(f"{name}_nonatural_ha"),
                  burn.multiply(area).rename(f"{name}_burned_ha")]

    values = ee.Image.cat(bands).updateMask(universe)
    key = zone.multiply(100).add(vtype.multiply(10)).add(cls).rename("key").int().updateMask(universe)
    g = gc.grouped_sum(key.addBands(values), len(bands), region)
    gc.export_groups(g, "fire_regime", {"window": f"fy{first_year}_{last_year}"})
