"""
product2_units.py — Product 2 (D15): fire-regime indicators per priority area, with the
robustness levels decided after the calibration (D15 §7, accepted 2026-10-06).

Per unit (348 = 294 MMA areas + 54 hybrids) it writes:
  - regime composition (D15 §4, product thresholds N=20, k=2, short interval < 3 years):
    share of stable savanna + grassland above / as expected / below; same per type;
    share of stable forest affected by fire; wetland reported with the same counts;
  - robustness of the unit flags (D15 §7):
      below   "robust"     > 50% below even with N=25
              "threshold"  > 50% below with N=20 only
      above   "robust"     > 20% above even counting annual fire only (1-year intervals, k=2)
              "threshold"  > 20% above with the product rule only (1- or 2-year intervals)
      forest  "robust"     > 50% affected also in the class-stable universe
              "threshold"  > 50% affected in the domain-stable universe only
    (units with < 1,000 ha of the stable vegetation concerned are not flagged: "small");
  - change 2012-2018 -> 2019-2025 (fire years / calendar years, stable open vegetation):
    annual burned fraction, share with consecutive burned years, and the main seasonal
    indicator, the July-August share of the burned area ("sem ignição natural", D15 §5,
    accepted 2026-10-06), only where the burned area of the sub-period reaches
    max(1,000 ha; 1% of the stable open vegetation); the critical-window share is kept as a
    descriptor; the monthly profile per sub-period is written to a separate table;
  - the latitude band of the unit (centroid) and the July-August share of the stable matrix
    outside the units in the same band (Cerrado and Pantanal only), for the relative
    reading (D15 §5).

Input : data/interim/extract/fire_regime.parquet, fire_calib.parquet, fire_calib_month.parquet
        data/derived/zones_attributes.csv, data/derived/product1/units_bounds.csv,
        data/derived/product1/calibration_units.csv (names, importance, priority, UF)
Output: data/derived/product2/units_fire.csv          one row per unit
        data/derived/product2/units_fire_months.csv   unit x sub-period x month: burned ha
        data/derived/product2/matrix_fire.csv         matrix outside the units, per latitude band
        data/derived/product2/matrix_regime.csv       matrix regime composition per type (Cerrado + Pantanal)

Run from the repository root:
  python scripts/analysis/product2_units.py

What can break, and how you would notice:
  - A unit missing from units_bounds.csv gets no latitude band (column empty) and no matrix
    reference; the script prints how many.
  - The flag counts printed at the end must equal calibration_report.txt (base: 177 below,
    74 above, 52 forest); if not, the thresholds here and there diverged.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/interim/extract"
OUT = ROOT / "data/derived/product2"
import importlib.util
_spec = importlib.util.spec_from_file_location("p2cal", ROOT / "scripts/analysis/product2_calibration.py")
p2cal = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p2cal)

MIN_HA = 1000.0
BANDS = [(-90, -18, "ao sul de 18°S"), (-18, -12, "18–12°S"), (-12, -8, "12–8°S"), (-8, 90, "ao norte de 8°S")]
WINDOW = {0: [7, 8, 9], 1: [7, 8, 9], 2: [8, 9, 10], 3: [8, 9, 10]}     # critical window per band
SP_YEARS = {"sp1": 7, "sp2": 7}


def band_of(lat):
    for i, (a, b, _) in enumerate(BANDS):
        if a <= lat < b:
            return i
    return np.nan


def main():
    zu = p2cal.units_table()
    fc = pd.read_parquet(EXT / "fire_calib.parquet")
    fc = fc[fc.window == "fy"]
    fr = pd.read_parquet(EXT / "fire_regime.parquet").merge(zu, on="zone_id")
    fm = pd.read_parquet(EXT / "fire_calib_month.parquet").merge(zu, on="zone_id")

    # --- 1. Composition and robustness, from the calibration signature -----------------------
    def metrics(p):
        return p2cal.unit_metrics(p2cal.run_variant(fc, zu, {**p2cal.BASE, **p}))
    base, n25, ann, cst = metrics({}), metrics({"N": 25}), metrics({"short": 1}), metrics({"univ": "class"})
    d = p2cal.run_variant(fc, zu, p2cal.BASE)
    d = d[d.inside]
    comp = d.groupby(["unit", "type", "cls"]).stable_ha.sum().unstack(["type", "cls"], fill_value=0)
    u = pd.DataFrame(index=base.index)
    u["open_ha"] = base.open_ha
    u["forest_ha"] = base.forest_ha
    for t, nm in ((2, "savanna"), (3, "grassland"), (4, "wetland")):
        tot = sum(comp.get((t, c), 0) for c in (1, 2, 3))
        u[f"{nm}_ha"] = tot
        for c, cn in ((1, "above"), (2, "expected"), (3, "below")):
            u[f"{nm}_{cn}"] = comp.get((t, c), 0) / tot.replace(0, np.nan)
    u["open_above"], u["open_below"] = base.above, base.below
    u["open_expected"] = 1 - base.above - base.below
    u["forest_affected"] = base.forest_affected

    def level(b, r, small):
        return np.select([small, r, b], ["small", "robust", "threshold"], "")
    small_o = (u.open_ha.fillna(0) < MIN_HA)
    small_f = (u.forest_ha.fillna(0) < MIN_HA)
    u["flag_below"] = level(base.flag_below50, n25.flag_below50.reindex(u.index, fill_value=False), small_o)
    u["flag_above"] = level(base.flag_above20, ann.flag_above20.reindex(u.index, fill_value=False), small_o)
    u["flag_forest"] = level(base.flag_forest50, cst.flag_forest50.reindex(u.index, fill_value=False), small_f)
    u["open_above_annual_only"] = ann.above
    u["open_below_n25"] = n25.below

    # --- 2. Change between sub-periods (stable savanna + grassland) ----------------------------
    op = fr[fr.type.isin([2, 3]) & (fr.unit != "OUTSIDE")].groupby("unit").sum(numeric_only=True)
    for sp in ("sp1", "sp2"):
        st = op.stable_ha
        u[f"{sp}_burned_frac_yr"] = op[f"{sp}_fireyears_ha"] / (st * SP_YEARS[sp])
        u[f"{sp}_consec_share"] = op[f"{sp}_consec_ha"] / st
        enough = op[f"{sp}_burned_ha"] >= np.maximum(MIN_HA, 0.01 * st)
        u[f"{sp}_burned_ha"] = op[f"{sp}_burned_ha"]
        u[f"{sp}_julaug"] = (op[f"{sp}_nonatural_ha"] / op[f"{sp}_burned_ha"]).where(enough)
        u[f"{sp}_window"] = (op[f"{sp}_season_ha"] / op[f"{sp}_burned_ha"]).where(enough)

    # --- 3. Latitude band and matrix reference --------------------------------------------------
    bounds = pd.read_csv(ROOT / "data/derived/product1/units_bounds.csv", dtype={"unit": str}).set_index("unit")
    lat = (bounds.miny + bounds.maxy) / 2
    u["latband"] = lat.reindex(u.index).map(band_of)
    print("units without latitude band:", int(u.latband.isna().sum()))
    mo = fm[fm.type.isin([2, 3])]
    # matrix = zones outside the units inside the Cerrado and Pantanal (2019 limits); the zone
    # grid also covers bits of the neighbouring biomes, which are left out of the reference
    zb = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")[["zone_id", "biome_2019"]]
    mo = mo.merge(zb, on="zone_id")
    mat = mo[(mo.unit == "OUTSIDE") & mo.biome_2019.isin(["Cerrado", "Pantanal"])].groupby(["latband", "subperiod", "month"]).ha.sum().unstack("month", fill_value=0)
    mrows = []
    for (lb, sp), r in mat.iterrows():
        tot = r.sum()
        mrows.append({"latband": lb, "band": BANDS[lb][2], "subperiod": sp, "burned_ha": tot,
                      "julaug": r[[7, 8]].sum() / tot, "window": r[WINDOW[lb]].sum() / tot})
    M = pd.DataFrame(mrows)
    for sp in ("sp1", "sp2"):
        ref = M[M.subperiod == sp].set_index("latband").julaug
        u[f"{sp}_julaug_matrix"] = u.latband.map(ref)

    # Regime composition of the matrix (Cerrado and Pantanal outside the units), product thresholds
    dm = p2cal.run_variant(fc, zu, p2cal.BASE).merge(zb, on="zone_id")
    dm = dm[~dm.inside & dm.biome_2019.isin(["Cerrado", "Pantanal"])]
    MR = dm.groupby(["type", "cls"]).stable_ha.sum().rename("ha").reset_index()
    MR["share"] = MR.ha / MR.groupby("type").ha.transform("sum")

    # --- 4. Monthly profile per unit -----------------------------------------------------------
    um = (mo[mo.unit != "OUTSIDE"].groupby(["unit", "subperiod", "month"]).ha.sum()
          .rename("burned_ha").reset_index())

    # --- 5. Attributes -------------------------------------------------------------------------
    at = pd.read_csv(ROOT / "data/derived/product1/calibration_units.csv", dtype={"unit": str}).set_index("unit")
    u = at[["NOME", "Import_bio", "Prior_acao", "Estados", "is_hybrid"]].join(u, how="left")

    OUT.mkdir(parents=True, exist_ok=True)
    u.round(4).to_csv(OUT / "units_fire.csv")
    um.round(1).to_csv(OUT / "units_fire_months.csv", index=False)
    M.round(4).to_csv(OUT / "matrix_fire.csv", index=False)
    MR.round(4).to_csv(OUT / "matrix_regime.csv", index=False)
    for f in ("flag_below", "flag_above", "flag_forest"):
        print(f, u[f].value_counts().to_dict())
    print(f"units: {len(u)}; written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
