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
  regime class   on fire years 2012-2025 (14 years):
     forest       0 no fire, 1 one event, 2 recurrent (>=2, none consecutive),
                  3 recurrent with consecutive years
     open/wetland 0 absence: no fire in the whole series 1985-2025 (41 fire years)
                  5 prolonged exclusion: burned before, but no fire in the last
                    `exclusion_years` (20) fire years of the series
                  4 consecutive (some pair of consecutive fire years in 2012-2025)
                  3 frequent (shortest interval in 2012-2025 = 2 years)
                  2 compatible (2012-2025: all intervals 3-5 years and no run of more than 4
                    fire-free years, edges included)
                  1 infrequent (everything else, incl. no fire in 2012-2025 but fire 6-19
                    fire years before 2025)
     Assignment order: absence -> prolonged exclusion -> consecutive -> frequent ->
     compatible -> infrequent. Absence and exclusion use the full series (project lead,
     2026-10-06): the universe is stable over 1985-2025, so absence is judged over 41 years.

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

What can break, and how you would notice:
  - Memory or time-out (41-year stacks, as in 21_extract_fire_intervals.py): raise
    export.tile_scale to 8 or 16 and run again.
  - QC in 90_collect_exports.py: per zone and type, the sum of stable_ha over classes must
    equal the stable area of that modal class in fire_intervals (same stability rule).
  - The month band of the fire product holds one month per pixel and year. A pixel burned
    twice in the same calendar year counts once; the fire-year rule is therefore a lower
    bound for very frequent fire.
"""
import importlib

import ee

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

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


# --- Full series: ever burned and last fire year (absence and prolonged exclusion) ----------
n_all = ee.Image(0); last_fire = ee.Image(0)
for y in range(first_year, last_year + 1):
    f = fire_year_flag(y)
    n_all = n_all.add(f)
    last_fire = last_fire.where(f, y)
excl_years = int(T["exclusion_years"])
prolonged = n_all.gt(0).And(last_fire.lte(last_year - excl_years))   # no fire in the last N fire years

# --- Regime class on the classification window ------------------------------------------------
w0, w1 = int(R["window"]["start"]), int(R["window"]["end"])
flags = {y: fire_year_flag(y) for y in range(w0, w1 + 1)}
n = ee.Image(0); consec = ee.Image(0); prev = ee.Image(0)
min_int = ee.Image(99); run = ee.Image(0); max_run = ee.Image(0)
for y in range(w0, w1 + 1):
    b = flags[y]
    n = n.add(b)
    if y > w0:
        consec = consec.Or(b.And(flags[y - 1]))
    # closed interval at this burn: y - previous burn year (only if there was one)
    interval = ee.Image(y).subtract(prev)
    min_int = min_int.where(b.And(prev.gt(0)).And(interval.lt(min_int)), interval)
    prev = prev.where(b, y)
    # longest run of fire-free years, window edges included
    run = run.add(1).multiply(ee.Image(1).subtract(b))
    max_run = max_run.max(run)

cmax = int(T["compatible_max"])
open_cls = (ee.Image(1)                                                   # infrequent
            .where(n.gte(2).And(min_int.gt(T["frequent"])).And(max_run.lte(cmax - 1)), 2)  # compatible
            .where(min_int.eq(T["frequent"]), 3)                          # frequent
            .where(consec, 4)                                             # consecutive
            .where(prolonged, 5)                                          # prolonged exclusion
            .where(n_all.eq(0), 0))                                       # absence (41 years)
forest_cls = (ee.Image(2)                                                 # recurrent
              .where(n.eq(0), 0).where(n.eq(1), 1)
              .where(consec, 3))
cls = open_cls.where(vtype.eq(1), forest_cls).rename("cls")

# --- Sub-period change metrics -----------------------------------------------------------------
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
gc.export_groups(g, "fire_regime", {"window": f"fy{w0}_{w1}"})
