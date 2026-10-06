"""
90_collect_exports.py — Decode the CSV exports from Earth Engine into long tables and run
the QC checks. Runs locally (no Earth Engine needed).

Input : the Drive export folder downloaded to data/interim/gee_exports/ (all CSV files)
Output: data/interim/extract/
          lulc_area.parquet         zone_id, year, class, ha
          lulc_transitions.parquet  zone_id, year, class_from, class_to, ha   (year = t, to t+1)
          fire_month.parquet        zone_id, year, stable, class, month, ha
          fire_intervals.parquet    zone_id, window, modal_class, metric, length, ha
          p1_transitions.parquet    zone_id, start, end, class_start, class_end, ha   (Product 1, D13)
          fire_regime.parquet       zone_id, type, cls, stable_ha, sp{1,2}_{fireyears,consec,season,nonatural,burned}_ha (D15)
          fire_regime_lat.parquet   zone_id, latband, type, cls, stable_ha (D15, summary by latitude band)
          fire_calib.parquet        zone_id, window (fy|cy), type, n3, n1, tsl, cs, stable_ha (D15 §7)
          fire_calib_month.parquet  zone_id, type, latband, subperiod, month, ha (D15 §7)
          p1_persistence.parquet    zone_id, window, start, end, k_water, class_start,
                                    nat_start_ha, strict_ha, never_anthropic_ha, water_persistent_ha
        data/interim/extract/qc_report.txt

Run from the repository root:
  python scripts/gee/90_collect_exports.py
  python scripts/gee/90_collect_exports.py --src "/content/drive/MyDrive/APCerrado_gee_exports"   # Colab

QC checks (printed and saved):
  1. LULC: per zone and year, total class area vs. zone area (zones_attributes.csv).
     Small zones lose/gain area at pixel edges; the report lists zones off by > 5%.
  2. Transitions: per zone, total transition area for t->t+1 equals LULC area in t.
  3. Fire intervals: never + sum(left) == stable and never + sum(right) == stable.
  4. Product 1 direct transitions: per zone, total area equals the LULC area of the start year.
  6. Fire regime (D15): per zone and vegetation type, stable_ha summed over regime classes
     equals the stable area of the same modal classes in fire_intervals.
  7. Fire calibration (D15 §7): per zone and type, stable area of fire_calib (fire years)
     equals fire_regime; the classes rebuilt from the signature with the product thresholds
     equal the fire_regime classes; calendar-year stable area equals fire-year stable area.
  5. Product 1 persistence: nat_start equals the natural-vegetation area of the start year
     in lulc_area; strict <= never_anthropic <= nat_start; water_persistent <= nat_start - strict.

What can break, and how you would notice:
  - An unexpected file name pattern is skipped and listed as "unrecognized".
  - Parsing errors in the `sum` column of interval files mean the export format changed
    (Earth Engine writes lists as "[v1,v2,...]").
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/interim/gee_exports"
OUT = ROOT / "data/interim/extract"


def read_all(pattern, exclude=None):
    # Re-running a task writes a second file with the same name; Drive then shows
    # "name (1).csv". Keep only the most recent file per logical name, so a year is
    # never counted twice.
    latest = {}
    for f in SRC.glob(pattern):
        if exclude and re.match(exclude, f.name):
            continue
        stem = re.sub(r" \(\d+\)$", "", f.stem)
        if stem not in latest or f.stat().st_mtime > latest[stem].stat().st_mtime:
            latest[stem] = f
    files = sorted(latest.values())
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else None


def decode_lulc(df):
    k = df["key"].astype(np.int64)
    return pd.DataFrame({"zone_id": k // 1000, "year": df["year"], "class": k % 1000, "ha": df["sum"]})


def decode_trans(df):
    k = df["key"].astype(np.int64)
    return pd.DataFrame({"zone_id": k // 10000, "year": df["year"], "class_from": (k % 10000) // 100,
                         "class_to": k % 100, "ha": df["sum"]})


def decode_fire_month(df):
    k = df["key"].astype(np.int64)
    month = k % 13
    rest = k // 13
    cls = rest % 100
    rest = rest // 100
    return pd.DataFrame({"zone_id": rest // 2, "year": df["year"], "stable": rest % 2,
                         "class": cls, "month": month, "ha": df["sum"]})


def decode_intervals(df):
    rows = []
    for _, r in df.iterrows():
        k = int(r["key"])
        W = int(r["W"])
        vals = json.loads(r["sum"]) if isinstance(r["sum"], str) else list(r["sum"])
        names = (["stable", "never"] + [f"closed_{L}" for L in range(1, W)]
                 + [f"left_{L}" for L in range(1, W + 1)] + [f"right_{L}" for L in range(1, W + 1)])
        for n, v in zip(names, vals):
            if v == 0 and n not in ("stable", "never"):
                continue
            m = re.match(r"(closed|left|right)_(\d+)", n)
            rows.append({"zone_id": k // 100, "window": r["window"], "modal_class": k % 100,
                         "metric": m.group(1) if m else n,
                         "length": int(m.group(2)) if m else (W if n == "never" else np.nan), "ha": v})
    return pd.DataFrame(rows)


def decode_p1_trans(df):
    k = df["key"].astype(np.int64)
    return pd.DataFrame({"zone_id": k // 10000, "start": df["start"], "end": df["end"],
                         "class_start": (k % 10000) // 100, "class_end": k % 100, "ha": df["sum"]})


FR_BANDS = ["stable_ha"] + [f"{sp}_{m}_ha" for sp in ("sp1", "sp2")
                            for m in ("fireyears", "consec", "season", "nonatural", "burned")]


def decode_fire_regime(df):
    vals = df["sum"].map(lambda v: json.loads(v) if isinstance(v, str) else list(v))
    out = pd.DataFrame(vals.tolist(), columns=FR_BANDS)
    k = df["key"].astype(np.int64)
    out.insert(0, "zone_id", k // 100)
    out.insert(1, "type", (k % 100) // 10)
    out.insert(2, "cls", k % 10)
    return out


def decode_fire_regime_lat(df):
    # key = ((zone*4 + latband)*5 + type)*10 + class  (22_extract_fire_regime.py --latband)
    k = df["key"].astype(np.int64)
    return pd.DataFrame({"zone_id": k // 200, "latband": (k // 50) % 4, "type": (k // 10) % 5,
                         "cls": k % 10, "stable_ha": df["sum"].astype(float)})


def decode_fire_calib(df):
    # key = (((zone*5 + type)*16 + n3*4 + n1)*6 + tsl)*2 + cs  (23_extract_fire_calibration.py)
    k = df["key"].astype(np.int64)
    cs = k % 2; k = k // 2
    tsl = k % 6; k = k // 6
    nn = k % 16; k = k // 16
    out = pd.DataFrame({"zone_id": k // 5, "window": df["window"].str[:2], "type": k % 5,
                        "n3": nn // 4, "n1": nn % 4, "tsl": tsl, "cs": cs,
                        "stable_ha": df["sum"].astype(float)})
    return out


def decode_fire_calib_month(df):
    # key = (zone*5 + type)*4 + latband ; sum = [sp1 months 1-12, sp2 months 1-12]
    vals = df["sum"].map(lambda v: json.loads(v) if isinstance(v, str) else list(v))
    k = df["key"].astype(np.int64)
    rows = []
    for kk, v in zip(k, vals):
        z, t, lb = kk // 20, (kk // 4) % 5, kk % 4
        for i, ha in enumerate(v):
            rows.append((z, t, lb, f"sp{i // 12 + 1}", i % 12 + 1, ha))
    return pd.DataFrame(rows, columns=["zone_id", "type", "latband", "subperiod", "month", "ha"])


P1_BANDS = ["nat_start_ha", "strict_ha", "never_anthropic_ha", "water_persistent_ha"]


def decode_p1_persist(df):
    # `sum` holds the four band totals as a list "[v1,v2,v3,v4]" (same format as intervals)
    vals = df["sum"].map(lambda v: json.loads(v) if isinstance(v, str) else list(v))
    out = pd.DataFrame(vals.tolist(), columns=P1_BANDS)
    k = df["key"].astype(np.int64)
    out.insert(0, "zone_id", k // 1000)
    out.insert(1, "window", df["window"])
    out.insert(2, "start", df["start"])
    out.insert(3, "end", df["end"])
    out.insert(4, "k_water", df["k_water"])
    out.insert(5, "class_start", k % 1000)
    return out


def main():
    global SRC, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC), help="folder with the CSV exports")
    ap.add_argument("--out", default=str(OUT), help="folder for the decoded tables")
    a_ = ap.parse_args()
    SRC, OUT = Path(a_.src), Path(a_.out)
    OUT.mkdir(parents=True, exist_ok=True)
    qc = []
    zones = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")[["zone_id", "area_ha"]]

    a = read_all("lulc_area_*.csv")
    if a is not None:
        a = decode_lulc(a)
        a.to_parquet(OUT / "lulc_area.parquet")
        tot = a.groupby(["zone_id", "year"]).ha.sum().reset_index().merge(zones, on="zone_id")
        tot["rel"] = tot.ha / tot.area_ha - 1
        # Zones outside the 2019 national biome map (beyond the border or offshore) have no
        # MapBiomas pixels by construction; report them apart from the QC of covered zones.
        zb = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")[["zone_id", "biome_2019"]]
        tot = tot.merge(zb, on="zone_id")
        outside = tot[tot.biome_2019 == "none"]
        qc.append(f"Zones outside MapBiomas coverage (biome_2019 = none): {outside.zone_id.nunique()} "
                  f"zones, {outside.groupby('zone_id').area_ha.first().sum():,.0f} ha")
        tot = tot[tot.biome_2019 != "none"]
        bad = tot[(tot.rel.abs() > 0.05) & (tot.area_ha > 10)]
        qc.append(f"LULC: {a.year.nunique()} years; covered zone-years (> 10 ha) off by >5%: {len(bad)} "
                  f"(covering {bad.area_ha.sum() / tot.area_ha.sum():.2e} of area); "
                  f"overall area ratio {tot.ha.sum() / tot.area_ha.sum():.4f}")

    t = read_all("lulc_trans_*.csv")
    if t is not None:
        t = decode_trans(t)
        t.to_parquet(OUT / "lulc_transitions.parquet")
        if a is not None:
            c = t.groupby(["zone_id", "year"]).ha.sum().rename("t").reset_index().merge(
                a.groupby(["zone_id", "year"]).ha.sum().rename("a").reset_index(), on=["zone_id", "year"])
            qc.append(f"Transitions vs LULC area, max relative difference: {(c.t / c.a - 1).abs().max():.2e}")

    f = read_all("fire_month_*.csv")
    if f is not None:
        f = decode_fire_month(f)
        f.to_parquet(OUT / "fire_month.parquet")
        qc.append(f"Fire monthly: {f.year.nunique()} years; months present {sorted(f.month.unique())}")

    i = read_all("fire_intervals_*.csv")
    if i is not None:
        i = decode_intervals(i)
        i.to_parquet(OUT / "fire_intervals.parquet")
        g = i.pivot_table(index=["zone_id", "window", "modal_class"], columns="metric",
                          values="ha", aggfunc="sum").fillna(0)
        for side in ("left", "right"):
            if side in g:
                err = ((g["never"] + g[side]) / g["stable"] - 1).abs().max()
                qc.append(f"Intervals: never + {side} vs stable, max relative difference {err:.2e}")

    # --- Product 1 (D13) -----------------------------------------------------------------
    lulc_pq = OUT / "lulc_area.parquet"
    a_all = a if a is not None else (pd.read_parquet(lulc_pq) if lulc_pq.exists() else None)

    p1t = read_all("product1_trans_*.csv")
    if p1t is not None:
        p1t = decode_p1_trans(p1t)
        p1t.to_parquet(OUT / "p1_transitions.parquet")
        if a_all is not None:
            for (s0, e0), d in p1t.groupby(["start", "end"]):
                c = d.groupby("zone_id").ha.sum().rename("t").to_frame().join(
                    a_all[a_all.year == s0].groupby("zone_id").ha.sum().rename("a"), how="inner")
                qc.append(f"P1 direct transitions {s0}->{e0} vs LULC area {s0}, "
                          f"max relative difference: {(c.t / c.a - 1).abs().max():.2e}")

    p1p = read_all("product1_persist_*.csv")
    if p1p is not None:
        p1p = decode_p1_persist(p1p)
        p1p.to_parquet(OUT / "p1_persistence.parquet")
        tol = 1e-6
        order_bad = ((p1p.strict_ha > p1p.never_anthropic_ha + tol)
                     | (p1p.never_anthropic_ha > p1p.nat_start_ha + tol)
                     | (p1p.water_persistent_ha > p1p.nat_start_ha - p1p.strict_ha + tol)).sum()
        qc.append(f"P1 persistence: rows violating strict <= never_anthropic <= nat_start or "
                  f"water <= nat_start - strict: {order_bad}")
        if a_all is not None:
            lg = pd.read_csv(ROOT / "data/reference/mapbiomas_col11_legend_groups.csv")
            nat = set(lg.loc[lg.level1_code.isin([1, 2]), "pixel_id"].astype(int))
            for (wname, s0), d in p1p.groupby(["window", "start"]):
                ref = a_all[(a_all.year == s0) & a_all["class"].isin(nat)].groupby("zone_id").ha.sum()
                c = d.groupby("zone_id").nat_start_ha.sum().rename("p").to_frame().join(ref.rename("a"), how="inner")
                qc.append(f"P1 persistence {wname}: nat_start vs LULC natural vegetation {s0}, "
                          f"max relative difference: {(c.p / c.a - 1).abs().max():.2e}")

    frl = read_all("fire_regime_lat*.csv")
    if frl is not None:
        frl = decode_fire_regime_lat(frl)
        frl.to_parquet(OUT / "fire_regime_lat.parquet")
        if (OUT / "fire_regime.parquet").exists():
            a_ = frl.groupby(["zone_id", "type", "cls"]).stable_ha.sum()
            b_ = pd.read_parquet(OUT / "fire_regime.parquet").groupby(["zone_id", "type", "cls"]).stable_ha.sum()
            c = pd.concat([a_.rename("l"), b_.rename("r")], axis=1).fillna(0)
            c = c[(c.l > 1) | (c.r > 1)]
            qc.append(f"Fire regime by latitude band: sum over bands vs fire_regime, max relative difference "
                      f"{((c.l - c.r).abs() / c[['l', 'r']].max(axis=1)).max():.2e} over {len(c)} cells")
    fr = read_all("fire_regime*.csv", exclude=r"fire_regime_lat")
    if fr is not None:
        fr = decode_fire_regime(fr)
        fr.to_parquet(OUT / "fire_regime.parquet")
        fi_pq = OUT / "fire_intervals.parquet"
        if fi_pq.exists():
            import yaml
            cfg = yaml.safe_load(open(ROOT / "scripts/gee/config.yml", encoding="utf-8"))
            tmap = {int(c): int(t) for t, cl in cfg["fire_regime"]["types"].items() for c in cl}
            fi_ = pd.read_parquet(fi_pq)
            ref = (fi_[fi_.metric == "stable"].assign(type=lambda d: d.modal_class.map(tmap))
                   .dropna(subset=["type"]).groupby(["zone_id", "type"]).ha.sum())
            got = fr.groupby(["zone_id", "type"]).stable_ha.sum()
            c = pd.concat([got.rename("r"), ref.rename("i")], axis=1).dropna()
            qc.append(f"Fire regime: stable area vs fire_intervals, max relative difference "
                      f"{(c.r / c.i - 1).abs().max():.2e} over {len(c)} zone-type pairs; "
                      f"classes present {sorted(fr.cls.unique())}")

    fc = read_all("fire_calib_[fc]y*.csv")
    if fc is not None:
        fc = decode_fire_calib(fc)
        fc.to_parquet(OUT / "fire_calib.parquet")
        frp = OUT / "fire_regime.parquet"
        if frp.exists():
            import yaml
            T = yaml.safe_load(open(ROOT / "scripts/gee/config.yml", encoding="utf-8"))["fire_regime"]["thresholds"]
            n_tsl = {10: 1, 15: 2, 20: 3, 25: 4}[int(T["expected_max"])]
            fr_ = pd.read_parquet(frp)
            fy = fc[fc.window == "fy"].copy()
            # rebuild the product classes from the signature (same rules as 22_extract_fire_regime.py)
            fy["cls"] = np.where(fy.tsl >= n_tsl, 3, np.where(fy.n3 >= int(T["excess_short_intervals"]), 1, 2))
            fy.loc[fy.type == 1, "cls"] = np.where(fy.loc[fy.type == 1, "tsl"] < 5, 2, 1)
            a_ = fy.groupby(["zone_id", "type", "cls"]).stable_ha.sum()
            b_ = fr_.groupby(["zone_id", "type", "cls"]).stable_ha.sum()
            c = pd.concat([a_.rename("c"), b_.rename("r")], axis=1).fillna(0)
            big = c[(c.r > 1) | (c.c > 1)]
            qc.append(f"Fire calibration: classes rebuilt from signature vs fire_regime, max abs difference "
                      f"{(c.c - c.r).abs().max():.3g} ha; max relative difference (cells > 1 ha) "
                      f"{((big.c - big.r).abs() / big[['c', 'r']].max(axis=1)).max():.2e} over {len(big)} cells")
        for w in ("fy", "cy"):
            qc.append(f"Fire calibration {w}: stable area {fc[fc.window == w].stable_ha.sum():,.0f} ha, "
                      f"class-stable share {fc[(fc.window == w) & (fc.cs == 1)].stable_ha.sum() / max(fc[fc.window == w].stable_ha.sum(), 1):.3f}")
    fm = read_all("fire_calib_month*.csv")
    if fm is not None:
        fm = decode_fire_calib_month(fm)
        fm.to_parquet(OUT / "fire_calib_month.parquet")
        frp = OUT / "fire_regime.parquet"
        if frp.exists():
            fr_ = pd.read_parquet(frp)
            for sp in ("sp1", "sp2"):
                a_ = fm[fm.subperiod == sp].groupby(["zone_id", "type"]).ha.sum()
                b_ = fr_.groupby(["zone_id", "type"])[f"{sp}_burned_ha"].sum()
                c = pd.concat([a_.rename("m"), b_.rename("r")], axis=1).dropna()
                c = c[c.r > 1]
                qc.append(f"Fire calibration months {sp}: sum over months vs fire_regime burned, "
                          f"max relative difference {(c.m / c.r - 1).abs().max():.2e} over {len(c)} pairs")

    unrec = [p.name for p in SRC.glob("*.csv")
             if not re.match(r"(lulc_area|lulc_trans|fire_month|fire_intervals|fire_regime|fire_calib|product1_trans|product1_persist)",
                             p.name)]
    qc.append(f"unrecognized files: {unrec or 'none'}")
    (OUT / "qc_report.txt").write_text("\n".join(qc) + "\n", encoding="utf-8")
    print("\n".join(qc))


if __name__ == "__main__":
    main()
