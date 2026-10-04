"""
product1_calibration.py — Calibration of the Product 1 categories (D13, section 6).

For each 2nd-update unit (294 MMA areas + 54 Cerrado/Pantanal hybrids) it computes the
dynamics metrics of D13, estimates how noisy each trend is, applies the provisional
thresholds, and tests how many units change category when each threshold moves by ±50%.
The matrix outside the 2012 units is summarized by biome (2019 limit) as context.

Inputs (not versioned; produced by 90_collect_exports.py):
  data/interim/extract/lulc_area.parquet        annual area per zone and class
  data/interim/extract/lulc_transitions.parquet annual transitions per zone
  data/interim/extract/p1_persistence.parquet   persistence of natural vegetation (D13 §7)
Versioned inputs:
  data/derived/zones_attributes.csv, data/derived/phase1/ap2012_units.csv,
  data/reference/mapbiomas_col11_legend_groups.csv
  data/raw/areas_hibridas/Areas_hibridas_2a_atualizacao.shp (hybrid classes; optional)
  data/interim/extract/p1_transitions.parquet   direct transitions (dominant driver)
Outputs (data/derived/product1/):
  calibration_units.csv        one row per unit: metrics, noise, provisional category, flags
  calibration_sensitivity.csv  units per category when one threshold moves by -50% / +50%
  calibration_report.txt       the numbers quoted in docs/product1_calibration.md

Run from the repository root:   python scripts/analysis/product1_calibration.py

Definitions (D13):
  N(t)  natural vegetation = MapBiomas level 1 classes 1 and 2
  A(t)  anthropic area = legend `nature` anthropic or ambiguous
  X(t)  non-anthropic area = mapped area - A(t). Water and sand are inside X, so flooding
        cycles (and, by decision, reservoirs) do not move it (D13 §5).
  rate  Theil-Sen slope of X(t) over the years, as % per year of N(2012). Negative = loss.
        Computed for 2012-2025 (category) and for 2012-2018 and 2018-2025 (acceleration).
  gross conversion  sum of annual natural -> anthropic transitions 2012->2025, % of N(2012)
        per year. Gross gain is the reverse flow.
  noise  standard deviation of the residuals of X(t) around the Theil-Sen line (% of N2012).
        Trend standard error = noise / sqrt(sum (t - mean t)^2), inflated for lag-1
        autocorrelation of the residuals (effective sample size n(1-r)/(1+r)).

What can break, and how you would notice:
  - Missing parquet files: FileNotFoundError naming the file; run 90_collect_exports.py.
  - Units with no natural vegetation in 2012 get NaN rates and the category "no natural
    vegetation"; the report counts them.
  - If the unit list does not total 348, the zone markers changed: check build_zones.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import theilslopes

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/interim/extract"
OUT = ROOT / "data/derived/product1"
OUT.mkdir(parents=True, exist_ok=True)

Y0, YS, Y1 = 2012, 2018, 2025          # start, sub-period split, end (D13 §3)

# Provisional thresholds (D13 §4). Rates in % per year of N(2012).
T = dict(
    stable_band=0.1,       # |rate| <= band  -> stable or turnover
    turnover_gross=0.5,    # gross conversion above this inside the band -> turnover
    moderate=1.0,          # rate between -band and -moderate -> moderate loss
    intense=2.0,           # between -moderate and -intense -> intense; beyond -> very intense
    accel=0.5,             # acceleration flag: rate(2018-25) - rate(2012-18) < -accel
)
GAIN_MIN_PP = 0.5          # net gain must also be >= 0.5 percentage points of land area ...
GAIN_MIN_HA = 100.0        # ... and >= 100 ha over 2012-2025 (both provisional)
SMALL_HA = 5000.0          # small-unit flag
HYDRO_SHARE = 0.2          # hydrological flag: natural<->water/sand exchange > 20% of all
                           # gross exchanges of natural vegetation
RES_MIN_HA, RES_MIN_PCT = 100.0, 0.5   # possible-reservoir flag: both minima

# --- 1. Legend sets ------------------------------------------------------------------------
lg = pd.read_csv(ROOT / "data/reference/mapbiomas_col11_legend_groups.csv")
NAT = set(lg.loc[lg.level1_code.isin([1, 2]), "pixel_id"].astype(int))
ANT = set(lg.loc[lg.nature.isin(["anthropic", "ambiguous"]), "pixel_id"].astype(int))
NNV = set(lg.loc[(lg.nature == "natural") & lg.level1_code.isin([4, 5]), "pixel_id"].astype(int))  # 23, 33
DRIVER = {15: "pasture", 39: "soybean", 20: "other crops", 40: "other crops", 41: "other crops",
          62: "other crops", 46: "other crops", 47: "other crops", 48: "other crops", 35: "other crops",
          21: "mosaic of uses", 9: "forest plantation", 30: "mining", 24: "urban",
          25: "other non-vegetated", 31: "aquaculture", 75: "energy", 91: "energy"}

# --- 2. Zones -> units -------------------------------------------------------------------
z = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
z["unit"] = np.where(z.ap2012_code != "none", z.ap2012_code.str.replace(".0", "", regex=False),
                     np.where(z.hybrid_code != "none", z.hybrid_code, "OUTSIDE"))
# Matrix outside the units: grouped by biome (2019) as context rows
z.loc[z.unit == "OUTSIDE", "unit"] = "OUTSIDE|" + z.loc[z.unit == "OUTSIDE", "biome_2019"].astype(str)
zu = z[["zone_id", "unit"]]

# --- 3. Annual series per unit -------------------------------------------------------------
a = pd.read_parquet(EXT / "lulc_area.parquet")
a = a[(a.year >= Y0) & (a.year <= Y1)].merge(zu, on="zone_id")
a["N"] = a["class"].isin(NAT) * a.ha
a["A"] = a["class"].isin(ANT) * a.ha
a["land"] = (a["class"] != 33) * a.ha
s = a.groupby(["unit", "year"])[["N", "A", "ha", "land"]].sum()
s["X"] = s.ha - s.A

# --- 4. Gross flows from annual transitions ------------------------------------------------
t = pd.read_parquet(EXT / "lulc_transitions.parquet")
t = t[(t.year >= Y0) & (t.year < Y1)].merge(zu, on="zone_id")
fn, tn = t.class_from.isin(NAT), t.class_to.isin(NAT)
t["conv"] = (fn & t.class_to.isin(ANT)) * t.ha
t["regrow"] = (t.class_from.isin(ANT) & tn) * t.ha
t["hydro"] = ((fn & t.class_to.isin(NNV)) | (t.class_from.isin(NNV) & tn)) * t.ha
t["sub"] = np.where(t.year < YS, "p1", "p2")
g = t.groupby("unit")[["conv", "regrow", "hydro"]].sum()
# Dominant driver: anthropic class in 2025 of the natural vegetation of 2012 that was converted,
# from the DIRECT transition 2012->2025 (D13 §7). Annual transitions would credit the first
# step (often pasture) and hide later steps such as pasture -> soybean.
dt = pd.read_parquet(EXT / "p1_transitions.parquet")
dt = dt[(dt.start == Y0) & (dt.end == Y1) & dt.class_start.isin(NAT) & dt.class_end.isin(ANT)].merge(zu, on="zone_id")
dt["driver"] = dt.class_end.map(DRIVER).fillna("other")
dd = dt.groupby(["unit", "driver"]).ha.sum().reset_index()
drv = dd.sort_values("ha").groupby("unit").tail(1).set_index("unit")
drv_share = drv.ha / dd.groupby("unit").ha.sum().reindex(drv.index)

# --- 5. Persistence (pixel level, D13 §7) ----------------------------------------------------
p = pd.read_parquet(EXT / "p1_persistence.parquet").merge(zu, on="zone_id")
pp = {w: d.groupby("unit")[["nat_start_ha", "strict_ha", "never_anthropic_ha", "water_persistent_ha"]].sum()
      for w, d in p.groupby("window")}


# --- 6. Trend, noise and standard error ------------------------------------------------------
def trend(x, y):
    """Theil-Sen slope, residual SD and autocorrelation-inflated standard error."""
    sl, ic, _, _ = theilslopes(y, x)
    r = y - (ic + sl * x)
    sd = r.std(ddof=2)
    rho = np.corrcoef(r[:-1], r[1:])[0, 1] if r.std() > 0 else 0.0
    rho = 0.0 if np.isnan(rho) else max(rho, 0.0)
    n = len(x)
    neff = max(n * (1 - rho) / (1 + rho), 3.0)
    se = sd / np.sqrt(((x - x.mean()) ** 2).sum()) * np.sqrt(n / neff)
    return sl, sd, se, rho


rows = []
for u, d in s.groupby(level="unit"):
    d = d.droplevel("unit")
    yrs = d.index.values.astype(float)
    n0 = d.N.get(Y0, np.nan)
    rec = {"unit": u, "land_ha_2012": d.land.get(Y0), "nat_ha_2012": n0, "nat_ha_2025": d.N.get(Y1),
           "nat_share_2012": n0 / d.land.get(Y0), "nat_share_2025": d.N.get(Y1) / d.land.get(Y1)}
    if not n0 or n0 <= 0:
        rows.append(rec); continue
    sl, sd, se, rho = trend(yrs, d.X.values)
    m1 = (yrs >= Y0) & (yrs <= YS); m2 = (yrs >= YS) & (yrs <= Y1)
    sl1 = theilslopes(d.X.values[m1], yrs[m1])[0]
    sl2 = theilslopes(d.X.values[m2], yrs[m2])[0]
    rec.update(rate=sl / n0 * 100, rate_2012_2018=sl1 / n0 * 100, rate_2018_2025=sl2 / n0 * 100,
               noise_pct=sd / n0 * 100, se_rate=se / n0 * 100, resid_autocorr=rho,
               net_ha=sl * (Y1 - Y0), net_pp_land=sl * (Y1 - Y0) / d.land.get(Y0) * 100,
               endpoint_rate=(d.X.get(Y1) - d.X.get(Y0)) / (Y1 - Y0) / n0 * 100)
    rows.append(rec)
m = pd.DataFrame(rows).set_index("unit")
yrs_n = Y1 - Y0
m["gross_conv"] = g.conv.reindex(m.index) / m.nat_ha_2012 / yrs_n * 100
m["gross_regrow"] = g.regrow.reindex(m.index) / m.nat_ha_2012 / yrs_n * 100
m["hydro_share"] = g.hydro.reindex(m.index) / (g.hydro + g.conv + g.regrow).reindex(m.index)
m["driver"] = drv.driver.reindex(m.index)
m["driver_share"] = drv_share.reindex(m.index)
q = pp["p2012_2025"].reindex(m.index)
m["touched_share_2012_2025"] = 1 - q.never_anthropic_ha / q.nat_start_ha    # converted at least once
m["water_persistent_ha"] = q.water_persistent_ha
m["water_persistent_pct"] = q.water_persistent_ha / q.nat_start_ha * 100
q85 = pp["p1985_2025"].reindex(m.index)
m["never_converted_since_1985_ha"] = q85.never_anthropic_ha


# --- 7. Categories and flags -----------------------------------------------------------------
def categorize(df, T, gain_pp=GAIN_MIN_PP, gain_ha=GAIN_MIN_HA):
    r, gc_ = df.rate, df.gross_conv
    gain_ok = (r > T["stable_band"]) & (df.net_pp_land >= gain_pp) & (df.net_ha >= gain_ha)
    cat = np.select(
        [df.nat_ha_2012.fillna(0) <= 0,
         gain_ok,
         r > T["stable_band"],                             # positive but below the minima
         (r.abs() <= T["stable_band"]) & (gc_ <= T["turnover_gross"]),
         r.abs() <= T["stable_band"],
         r >= -T["moderate"],
         r >= -T["intense"]],
        ["no natural vegetation", "net gain", "stable", "stable", "turnover",
         "moderate loss", "intense loss"],
        default="very intense loss")
    return pd.Series(cat, index=df.index)


units = m[~m.index.str.startswith("OUTSIDE|")].copy()
units["category"] = categorize(units, T)
# Confidence: low when the trend is within one standard error of the nearest boundary
bounds = np.array([T["stable_band"], -T["stable_band"], -T["moderate"], -T["intense"]])
units["dist_to_boundary"] = units.rate.apply(lambda v: np.min(np.abs(bounds - v)) if pd.notna(v) else np.nan)
units["low_confidence"] = units.dist_to_boundary < units.se_rate
units["flag_acceleration"] = (units.rate_2018_2025 - units.rate_2012_2018) < -T["accel"]
units["flag_small"] = units.land_ha_2012 < SMALL_HA
units["flag_hydro"] = units.hydro_share > HYDRO_SHARE
units["flag_possible_reservoir"] = (units.water_persistent_ha >= RES_MIN_HA) & (units.water_persistent_pct >= RES_MIN_PCT)
units["state_class_2025"] = pd.cut(units.nat_share_2025, [-0.01, 0.2, 0.5, 0.8, 1.01],
                                   labels=["<20%", "20-50%", "50-80%", ">=80%"])
units["is_hybrid"] = ~units.index.str.fullmatch(r"\d+")

# Unit attributes. MMA areas: from the Phase 1 table (MMA layer fields). Hybrids: from the
# hybrid layer (IB_pos, PA_pos, main action). Class labels are normalized, because the source
# layers spell them inconsistently (e.g. "Muita Alta", "Muito alta", "Extremamente alta").
def norm_class(v):
    if not isinstance(v, str):
        return v
    k = v.strip().lower().replace("muita", "muito")
    return {"alta": "Alta", "muito alta": "Muito Alta", "extremamente alta": "Extremamente Alta"}.get(k, v)


attrs = pd.read_csv(ROOT / "data/derived/phase1/ap2012_units.csv", dtype={"unit": str})
attrs = attrs.set_index("unit")[["NOME", "Import_bio", "Prior_acao", "Acao1", "Estados"]]
try:
    import geopandas as gpd
    hy = gpd.read_file(ROOT / "data/raw/areas_hibridas/Areas_hibridas_2a_atualizacao.shp", ignore_geometry=True)
    hy = (hy.rename(columns={"COD_area": "unit", "IB_pos": "Import_bio", "PA_pos": "Prior_acao", "AçãoP_p": "Acao1"})
            .drop_duplicates("unit").set_index("unit")[["Import_bio", "Prior_acao", "Acao1"]])
    attrs = attrs.combine_first(hy)
except Exception as e:  # raw hybrid layer missing: hybrids keep empty attributes
    print("WARNING: hybrid attributes not read:", e)
main_uf = z.assign(ha=z.area_ha).sort_values("ha").groupby("unit").tail(1).set_index("unit").uf
units = units.join(attrs)
units["Estados"] = units.Estados.fillna(main_uf.reindex(units.index))
for c in ("Import_bio", "Prior_acao"):
    units[c] = units[c].map(norm_class)
units.round(4).to_csv(OUT / "calibration_units.csv")

# --- 8. Sensitivity: each threshold at -50% and +50% ------------------------------------------
base = units.category
sens = []
for k in T:
    for f in (0.5, 1.5):
        T2 = dict(T); T2[k] = T[k] * f
        if k == "accel":
            fl = (units.rate_2018_2025 - units.rate_2012_2018) < -T2[k]
            sens.append({"threshold": k, "factor": f, "value": T2[k], "changed": int((fl != units.flag_acceleration).sum()),
                         **{"n_flag_acceleration": int(fl.sum())}})
            continue
        c2 = categorize(units, T2)
        sens.append({"threshold": k, "factor": f, "value": T2[k], "changed": int((c2 != base).sum()),
                     **c2.value_counts().add_prefix("n_").to_dict()})
for gp, gh in ((0.25, 50), (1.0, 200)):
    c2 = categorize(units, T, gp, gh)
    sens.append({"threshold": "gain_minimum", "factor": gp / GAIN_MIN_PP, "value": f"{gp} pp & {gh} ha",
                 "changed": int((c2 != base).sum()), **c2.value_counts().add_prefix("n_").to_dict()})
sens = pd.DataFrame(sens)
sens.to_csv(OUT / "calibration_sensitivity.csv", index=False)

# --- 9. Report -------------------------------------------------------------------------------
L = []
L.append(f"Units: {len(units)} ({(~units.is_hybrid).sum()} MMA areas + {units.is_hybrid.sum()} hybrids)")
L.append("\n== Noise and trend uncertainty (% per year of N2012) ==")
L.append(units[["rate", "se_rate", "noise_pct", "resid_autocorr"]].describe(percentiles=[.1, .25, .5, .75, .9]).round(3).to_string())
L.append(f"Units whose 2*SE exceeds the stable band ({T['stable_band']}): {(2 * units.se_rate > T['stable_band']).sum()}")
L.append(f"Theil-Sen vs endpoint rate: median abs difference {(units.rate - units.endpoint_rate).abs().median():.3f}; "
         f"units differing by > 0.25: {((units.rate - units.endpoint_rate).abs() > 0.25).sum()}")
L.append("\n== Provisional categories ==")
L.append(units.category.value_counts().to_string())
L.append(f"Low confidence (within 1 SE of a boundary): {units.low_confidence.sum()}")
L.append("\nCategory x state 2025:")
L.append(pd.crosstab(units.category, units.state_class_2025).to_string())
L.append("\n== Flags ==")
for f in ["flag_acceleration", "flag_small", "flag_hydro", "flag_possible_reservoir"]:
    L.append(f"{f}: {units[f].sum()}")
L.append("Dominant driver:\n" + units.driver.value_counts().to_string())
L.append("\n== Gain candidates (rate > band) ==")
L.append(units[units.rate > T["stable_band"]][["nat_share_2012", "rate", "se_rate", "net_ha", "net_pp_land", "category"]]
         .round(3).sort_values("rate").to_string())
L.append("\n== Sensitivity (each threshold x0.5 and x1.5; 'changed' = units changing category or flag) ==")
L.append(sens.fillna(0).to_string(index=False))
L.append("\n== Matrix outside the 2012 units, by biome (context) ==")
L.append(m[m.index.str.startswith("OUTSIDE|")][["nat_ha_2012", "nat_share_2012", "nat_share_2025", "rate",
                                                  "rate_2012_2018", "rate_2018_2025", "gross_conv", "gross_regrow",
                                                  "touched_share_2012_2025"]].round(3).to_string())
L.append("\n== By importance and priority (medians of rate; counts per category) ==")
for col in ["Import_bio", "Prior_acao"]:
    L.append(pd.crosstab(units[col], units.category).assign(median_rate=units.groupby(col).rate.median().round(2)).to_string())
(OUT / "calibration_report.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
