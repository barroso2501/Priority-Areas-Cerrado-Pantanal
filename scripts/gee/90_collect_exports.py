"""
90_collect_exports.py — Decode the CSV exports from Earth Engine into long tables and run
the QC checks. Runs locally (no Earth Engine needed).

Input : the Drive export folder downloaded to data/interim/gee_exports/ (all CSV files)
Output: data/interim/extract/
          lulc_area.parquet         zone_id, year, class, ha
          lulc_transitions.parquet  zone_id, year, class_from, class_to, ha   (year = t, to t+1)
          fire_month.parquet        zone_id, year, stable, class, month, ha
          fire_intervals.parquet    zone_id, window, modal_class, metric, length, ha
        data/interim/extract/qc_report.txt

Run from the repository root:
  python scripts/gee/90_collect_exports.py
  python scripts/gee/90_collect_exports.py --src "/content/drive/MyDrive/APCerrado_gee_exports"   # Colab

QC checks (printed and saved):
  1. LULC: per zone and year, total class area vs. zone area (zones_attributes.csv).
     Small zones lose/gain area at pixel edges; the report lists zones off by > 5%.
  2. Transitions: per zone, total transition area for t->t+1 equals LULC area in t.
  3. Fire intervals: never + sum(left) == stable and never + sum(right) == stable.

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


def read_all(pattern):
    # Re-running a task writes a second file with the same name; Drive then shows
    # "name (1).csv". Keep only the most recent file per logical name, so a year is
    # never counted twice.
    latest = {}
    for f in SRC.glob(pattern):
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

    unrec = [p.name for p in SRC.glob("*.csv")
             if not re.match(r"(lulc_area|lulc_trans|fire_month|fire_intervals)_", p.name)]
    qc.append(f"unrecognized files: {unrec or 'none'}")
    (OUT / "qc_report.txt").write_text("\n".join(qc) + "\n", encoding="utf-8")
    print("\n".join(qc))


if __name__ == "__main__":
    main()
