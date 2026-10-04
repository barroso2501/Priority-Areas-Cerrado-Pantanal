"""
phase1_q1_q6.py — First descriptive results of Phase 1 (work plan Q1 and Q6).

Q1: state and trajectory of native vegetation in each priority area (2006 and 2012
    layers, plus the Cerrado/Pantanal hybrids), 1985–2025.
Q6: did the 2012 revision respond to the state of the 2006 areas? We compare the 2006
    areas by how much of them was kept in 2012, and the strata "left", "stayed",
    "entered" and "neither" before the revision.

Inputs : data/interim/extract/lulc_area.parquet, lulc_transitions.parquet (90_collect_exports.py)
         data/derived/zones_attributes.csv, data/derived/reconciliation_2nd_update.csv
         data/reference/mapbiomas_col11_legend_groups.csv
Outputs: data/derived/phase1/
           strata_native_series.csv     native share per stratum and year
           strata_period_rates.csv      net and gross change per stratum and period
           ap2006_units.csv             one row per 2006 area: state, rates, % kept in 2012
           ap2012_units.csv             one row per 2012 area / hybrid: state and rates
           q6_left_vs_kept.csv          2006 areas grouped by share kept in 2012
         printed summary (copied into docs/results_phase1.md by hand)

Run from the repository root:   python scripts/analysis/phase1_q1_q6.py

Definitions (provisional; milestones D1 are still open):
  - Native vegetation = classes with fire_domain == "native" in the legend table (D8).
  - Land area = total area minus "River, lake and ocean" (33). Surface water varies a
    lot from year to year in the Pantanal and would add noise to the denominator.
  - Zones outside MapBiomas coverage (biome_2019 == "none") are excluded (findings §9).
  - Periods: 1985–2002, 2002–2009, 2009–2016, 2016–2025, matching the candidate
    milestones T0 = 2002, T2 = 2009, T3 = 2016 and the last year. Rates are annualized.
  - Gross loss = native → non-native transitions summed over the years of a period.
    Gross gain = the reverse (regrowth). Net change = gain − loss.
  - 2006 pieces with a multi-code marker (overlapping 2006 areas) count for every area
    they belong to at unit level, but only once in the strata.

What can break, and how you would notice:
  - A class missing from the legend table is treated as non-native and listed at the
    start ("classes not in legend"). The list should be empty.
  - Strata area must sum to the covered extent; the script prints both numbers.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/interim/extract"
OUT = ROOT / "data/derived/phase1"
OUT.mkdir(parents=True, exist_ok=True)
PERIODS = [(1985, 2002), (2002, 2009), (2009, 2016), (2016, 2025)]
SNAP = [1985, 2002, 2009, 2016, 2025]
WATER = 33

# --- inputs ------------------------------------------------------------------------------
lg = pd.read_csv(ROOT / "data/reference/mapbiomas_col11_legend_groups.csv")
native = set(lg.loc[lg.fire_domain == "native", "pixel_id"].astype(int))
z = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
z = z[z.biome_2019 != "none"]  # outside MapBiomas coverage
a = pd.read_parquet(EXT / "lulc_area.parquet")
t = pd.read_parquet(EXT / "lulc_transitions.parquet")
a = a[a.zone_id.isin(z.zone_id)]
t = t[t.zone_id.isin(z.zone_id)]
print("classes not in legend:", sorted(set(a["class"]) - set(lg.pixel_id.dropna().astype(int))))

# Stratum of each zone (each zone belongs to exactly one stratum)
z["stratum"] = np.select(
    [(z.ap2006_code != "none") & (z.ap2012_code != "none"),
     (z.ap2006_code != "none") & (z.hybrid_code != "none"),
     z.ap2006_code != "none",
     z.ap2012_code != "none",
     z.hybrid_code != "none"],
    ["stayed (2006 & 2012)", "2006 & hybrid", "left (2006 only)", "entered (2012 only)", "hybrid only"],
    "neither")

# --- per-zone annual native and land area ------------------------------------------------
a["nat"] = a["class"].isin(native) * a.ha
a["land"] = (a["class"] != WATER) * a.ha
zy = a.groupby(["zone_id", "year"])[["nat", "land"]].sum().reset_index()

# Gross loss / gain per zone and transition year (year = t, change t -> t+1)
t["loss"] = (t.class_from.isin(native) & ~t.class_to.isin(native)) * t.ha
t["gain"] = (~t.class_from.isin(native) & t.class_to.isin(native)) * t.ha
zt = t.groupby(["zone_id", "year"])[["loss", "gain"]].sum().reset_index()


def summarise(groups: pd.DataFrame, key: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """groups: zone_id -> key (a zone may map to several keys). Returns series and rates."""
    s = zy.merge(groups, on="zone_id").groupby([key, "year"])[["nat", "land"]].sum().reset_index()
    s["native_share"] = s.nat / s.land
    g = zt.merge(groups, on="zone_id").groupby([key, "year"])[["loss", "gain"]].sum().reset_index()
    rows = []
    for p0, p1 in PERIODS:
        gg = g[(g.year >= p0) & (g.year < p1)].groupby(key)[["loss", "gain"]].sum()
        n0 = s[s.year == p0].set_index(key).nat
        n1 = s[s.year == p1].set_index(key).nat
        land = s[s.year == p0].set_index(key).land
        r = pd.DataFrame({"period": f"{p0}-{p1}", "native_start_ha": n0, "native_end_ha": n1, "land_ha": land})
        r = r.join(gg)
        yrs = p1 - p0
        # Annualized rates, as % of the native area at the start of the period
        r["net_change_pct_yr"] = (r.native_end_ha / r.native_start_ha - 1) / yrs * 100
        r["gross_loss_pct_yr"] = r.loss / r.native_start_ha / yrs * 100
        r["gross_gain_pct_yr"] = r.gain / r.native_start_ha / yrs * 100
        rows.append(r.reset_index())
    return s, pd.concat(rows, ignore_index=True)


# --- strata ------------------------------------------------------------------------------
st_series, st_rates = summarise(z[["zone_id", "stratum"]], "stratum")
print(f"covered extent {zy[zy.year == 2025].land.sum() / 1e6:.2f} Mha land; "
      f"strata sum {st_series[st_series.year == 2025].land.sum() / 1e6:.2f} Mha")
st_series.to_csv(OUT / "strata_native_series.csv", index=False)
st_rates.to_csv(OUT / "strata_period_rates.csv", index=False)

# --- 2006 units (split multi-code markers) ------------------------------------------------
m06 = z[z.ap2006_code != "none"][["zone_id", "ap2006_code", "ap2006_type", "ap2012_code", "area_ha"]].copy()
m06["ap2006_unit"] = m06.ap2006_code.str.split("|")
m06 = m06.explode("ap2006_unit")
kept = (m06.assign(kept_ha=np.where(m06.ap2012_code != "none", m06.area_ha, 0))
        .groupby("ap2006_unit")[["area_ha", "kept_ha"]].sum())
kept["kept_share_2012"] = kept.kept_ha / kept.area_ha
u06_series, u06_rates = summarise(m06[["zone_id", "ap2006_unit"]], "ap2006_unit")
wide = u06_series[u06_series.year.isin(SNAP)].pivot(index="ap2006_unit", columns="year", values="native_share")
wide.columns = [f"native_share_{c}" for c in wide.columns]
rates_w = u06_rates.pivot(index="ap2006_unit", columns="period", values="net_change_pct_yr")
rates_w.columns = [f"net_pct_yr_{c}" for c in rates_w.columns]
types = z[z.ap2006_code != "none"].assign(u=lambda d: d.ap2006_code.str.split("|")).explode("u") \
    .groupby("u").ap2006_type.agg(lambda x: "|".join(sorted(set(x))))
# Share of each 2006 area inside Cerrado+Pantanal under each biome limit (Q6 confounder:
# areas may have been dropped in 2012 because they fall in another biome, not for their state)
zz = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
zz = zz[zz.ap2006_code != "none"].assign(u=lambda d: d.ap2006_code.str.split("|")).explode("u")
cp = ["Cerrado", "Pantanal"]
bio = zz.groupby("u").apply(lambda d: pd.Series({
    "share_in_cp_2004": d.loc[d.biome_2004.isin(cp), "area_ha"].sum() / d.area_ha.sum(),
    "share_in_cp_2019": d.loc[d.biome_2019.isin(cp), "area_ha"].sum() / d.area_ha.sum(),
    "main_uf": d.groupby("uf").area_ha.sum().idxmax()}))
u06 = kept.join(wide).join(rates_w).join(types.rename("type")).join(bio)
u06.index.name = "ap2006_code"
u06.to_csv(OUT / "ap2006_units.csv")

# --- Q6: 2006 areas grouped by share kept in 2012 -----------------------------------------
nova = u06[~u06.type.str.contains("Protegida")].copy()
nova["kept_class"] = pd.cut(nova.kept_share_2012, [-0.01, 0.1, 0.5, 0.9, 1.01],
                            labels=["dropped (<10%)", "mostly dropped (10–50%)",
                                    "mostly kept (50–90%)", "kept (>90%)"])
q6 = nova.groupby("kept_class", observed=True).agg(
    n_areas=("area_ha", "size"), area_Mha=("area_ha", lambda x: x.sum() / 1e6),
    native_2002_median=("native_share_2002", "median"),
    native_2009_median=("native_share_2009", "median"),
    net_pct_yr_2002_2009_median=("net_pct_yr_2002-2009", "median"),
    net_pct_yr_2016_2025_median=("net_pct_yr_2016-2025", "median"),
    share_in_cp_2019_mean=("share_in_cp_2019", "mean"),
    n_areas_SP=("main_uf", lambda x: (x == "SP").sum()))
q6.to_csv(OUT / "q6_left_vs_kept.csv")
rho = nova[["kept_share_2012", "native_share_2009", "net_pct_yr_2002-2009"]].corr(method="spearman")

# --- 2012 units and hybrids ---------------------------------------------------------------
rec = pd.read_csv(ROOT / "data/derived/reconciliation_2nd_update.csv")
m12 = z[z.ap2012_code != "none"][["zone_id", "ap2012_code"]].assign(
    unit=lambda d: d.ap2012_code.astype(float).astype(int).astype(str))
mh = z[z.hybrid_code != "none"][["zone_id", "hybrid_code"]].rename(columns={"hybrid_code": "unit"})
u12_series, u12_rates = summarise(pd.concat([m12[["zone_id", "unit"]], mh]), "unit")
w12 = u12_series[u12_series.year.isin(SNAP)].pivot(index="unit", columns="year", values="native_share")
w12.columns = [f"native_share_{c}" for c in w12.columns]
r12 = u12_rates.pivot(index="unit", columns="period", values="net_change_pct_yr")
r12.columns = [f"net_pct_yr_{c}" for c in r12.columns]
attrs = rec.dropna(subset=["COD_area"]).assign(unit=lambda d: d.COD_area.astype(int).astype(str)) \
    .set_index("unit")[["NOME", "Import_bio", "Prior_acao", "Acao1", "Estados"]]
u12 = w12.join(r12).join(attrs)
u12["is_hybrid"] = ~u12.index.str.isdigit()
u12.index.name = "unit"
u12.to_csv(OUT / "ap2012_units.csv")

# --- printed summary ------------------------------------------------------------------------
pd.set_option("display.width", 200)
print("\n== Native share by stratum (land area, %) ==")
print((st_series[st_series.year.isin(SNAP)].pivot(index="stratum", columns="year", values="native_share") * 100).round(1))
print("\n== Land area by stratum (Mha, 2025) ==")
print(st_series[st_series.year == 2025].set_index("stratum").land.div(1e6).round(2))
print("\n== Net change of native area, % per year ==")
print(st_rates.pivot(index="stratum", columns="period", values="net_change_pct_yr").round(2))
print("\n== Gross loss, % per year ==")
print(st_rates.pivot(index="stratum", columns="period", values="gross_loss_pct_yr").round(2))
print("\n== Gross gain (regrowth), % per year ==")
print(st_rates.pivot(index="stratum", columns="period", values="gross_gain_pct_yr").round(2))
print("\n== Q6: 2006 'Nova' areas by share kept in 2012 ==")
print(q6.round(3).to_string())
print("\nSpearman correlations (2006 'Nova' areas):")
print(rho.round(2))
print("\n== 2012 areas (non-hybrid): native share by importance class, medians ==")
nh = u12[~u12.is_hybrid]
print(nh.groupby(nh.Import_bio.str.lower().str.replace("muita", "muito"))[
    ["native_share_2009", "native_share_2025", "net_pct_yr_2009-2016", "net_pct_yr_2016-2025"]].median().round(3))
print("\n== 2012 areas: distribution of net change 2016–2025 (% per year) ==")
print(nh["net_pct_yr_2016-2025"].describe().round(2))
