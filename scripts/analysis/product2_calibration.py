"""
product2_calibration.py — Product 2 (D15 §7): sensitivity of the fire-regime categories to
their thresholds and choices, computed offline from the signature extraction
(scripts/gee/23_extract_fire_calibration.py). No Earth Engine needed.

What is varied (one at a time, against the product setting N=20, k=2, short < 3 years,
fire year, domain-stable universe, windows of D15 §5):
  N      expected maximum interval ("below expected" = no fire in the last N fire years):
         10, 15, 20, 25 years
  k      "above expected" = at least k short intervals: 1, 2, 3
  short  short interval < 3 years (1- or 2-year return) or = 1 year only (annual fire)
  year   fire year (April-March) or calendar year
  univ   domain-stable (natural vegetation every year) or class-stable (same class every year)
  window critical window of each latitude band shifted one month earlier / later

Input : data/interim/extract/fire_calib.parquet, fire_calib_month.parquet (90_collect_exports.py)
        data/derived/zones_attributes.csv, data/derived/phase1/ap2012_units.csv
Output: data/derived/product2/
          calibration_variants.csv  variant x type x inside/outside the units: share of the
                                    stable area in each category
          calibration_units.csv     unit x variant: share above / below (savanna + grassland),
                                    forest affected, and the unit flags
          calibration_windows.csv   latitude band x sub-period x window shift: share of the
                                    burned area (open vegetation) inside the critical window
          calibration_report.txt    readable summary: how much each choice moves the results
Unit flags (descriptive, as used in the presentation draft): below > 50%, above > 20%,
above > 50% of the stable savanna + grassland; forest affected > 50%. Units with less than
1,000 ha of stable open vegetation are kept but not flagged.

Run from the repository root:
  python scripts/analysis/product2_calibration.py

What can break, and how you would notice:
  - fire_calib.parquet missing: run step 11 of the Colab notebook and the decoding cell.
  - Without the calendar-year file (task fire_calib_cy failed), the "year" variant is
    skipped and the report says so; the same for the month file and the window shifts.
  - The baseline row must reproduce fire_regime.parquet; the QC line of 90_collect_exports.py
    checks it. If it did not, the signature key changed in one of the two scripts.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/interim/extract"
OUT = ROOT / "data/derived/product2"

TYPES = {1: "forest", 2: "savanna", 3: "grassland", 4: "wetland"}
N_TSL = {10: 1, 15: 2, 20: 3, 25: 4}       # "below expected" = tsl >= this (see 23_*.py)
MIN_OPEN_HA = 1000.0
BASE = {"N": 20, "k": 2, "short": 3, "year": "fy", "univ": "domain"}

# Variants: the baseline and one change at a time
VARIANTS = [("base", {})] + \
    [(f"N{n}", {"N": n}) for n in (10, 15, 25)] + \
    [(f"k{k}", {"k": k}) for k in (1, 3)] + \
    [("short1_k2", {"short": 1}), ("short1_k1", {"short": 1, "k": 1}),
     ("calendar", {"year": "cy"}), ("class_stable", {"univ": "class"})]


def classify(d: pd.DataFrame, N=20, k=2, short=3) -> pd.Series:
    """Category of each signature row. Open types: 1 above, 2 as expected, 3 below
    (below assigned first). Forest: 1 not affected, 2 affected."""
    below = d.tsl >= N_TSL[N]
    nshort = d.n3 if short == 3 else d.n1
    cls = np.where(below, 3, np.where(nshort >= k, 1, 2))
    cls = np.where(d.type == 1, np.where(d.tsl < 5, 2, 1), cls)
    return pd.Series(cls, index=d.index)


def units_table():
    z = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
    z["unit"] = np.where(z.ap2012_code != "none", z.ap2012_code.str.replace(".0", "", regex=False),
                         np.where(z.hybrid_code != "none", z.hybrid_code, "OUTSIDE"))
    return z[["zone_id", "unit"]]


def run_variant(fc, zu, p):
    d = fc[fc.window == p["year"]]
    if p["univ"] == "class":
        d = d[d.cs == 1]
    d = d.assign(cls=classify(d, p["N"], p["k"], p["short"])).merge(zu, on="zone_id")
    d["inside"] = d.unit != "OUTSIDE"
    return d


def shares(d):
    g = d.groupby(["inside", "type", "cls"]).stable_ha.sum()
    return (g / g.groupby(level=["inside", "type"]).transform("sum")).rename("share").reset_index()


def unit_metrics(d):
    u = d[d.inside]
    op = u[u.type.isin([2, 3])]
    tot = op.groupby("unit").stable_ha.sum()
    ab = op[op.cls == 1].groupby("unit").stable_ha.sum().reindex(tot.index, fill_value=0) / tot
    be = op[op.cls == 3].groupby("unit").stable_ha.sum().reindex(tot.index, fill_value=0) / tot
    fo = u[u.type == 1]
    ftot = fo.groupby("unit").stable_ha.sum()
    fa = fo[fo.cls == 2].groupby("unit").stable_ha.sum().reindex(ftot.index, fill_value=0) / ftot
    m = pd.DataFrame({"open_ha": tot, "above": ab, "below": be}).join(
        pd.DataFrame({"forest_ha": ftot, "forest_affected": fa}), how="outer")
    ok = m.open_ha >= MIN_OPEN_HA
    m["flag_below50"] = ok & (m.below > 0.5)
    m["flag_above20"] = ok & (m.above > 0.2)
    m["flag_above50"] = ok & (m.above > 0.5)
    m["flag_forest50"] = (m.forest_ha >= MIN_OPEN_HA) & (m.forest_affected > 0.5)
    return m


def window_table(fm):
    """Share of burned open vegetation inside the critical window, per latitude band, for the
    product window and the windows shifted one month earlier and later."""
    win = {0: [7, 8, 9], 1: [7, 8, 9], 2: [8, 9, 10], 3: [8, 9, 10]}   # D15 §5
    names = {0: "south of 18S", 1: "18-12S", 2: "12-8S", 3: "north of 8S"}
    op = fm[fm.type.isin([2, 3])].merge(units_table(), on="zone_id")
    op["inside"] = op.unit != "OUTSIDE"
    rows = []
    for (ins, lb, sp), d in op.groupby(["inside", "latband", "subperiod"]):
        tot = d.ha.sum()
        bym = d.groupby("month").ha.sum()
        r = {"inside": ins, "latband": names[lb], "subperiod": sp, "burned_ha": tot}
        for sh in (-1, 0, 1):
            ms = [(m + sh - 1) % 12 + 1 for m in win[lb]]
            r[f"window{sh:+d}"] = bym.reindex(ms, fill_value=0).sum() / tot if tot else np.nan
        r["jul_aug"] = bym.reindex([7, 8], fill_value=0).sum() / tot if tot else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    fc = pd.read_parquet(EXT / "fire_calib.parquet")
    zu = units_table()
    OUT.mkdir(parents=True, exist_ok=True)
    have_cy = (fc.window == "cy").any()
    sh_rows, un_rows, rep = [], [], []
    base_units = None
    for name, ch in VARIANTS:
        p = {**BASE, **ch}
        if p["year"] == "cy" and not have_cy:
            rep.append(f"{name}: skipped (no calendar-year export)")
            continue
        d = run_variant(fc, zu, p)
        s = shares(d).assign(variant=name)
        sh_rows.append(s)
        m = unit_metrics(d).assign(variant=name)
        un_rows.append(m.reset_index())
        if name == "base":
            base_units = m
    S = pd.concat(sh_rows)
    U = pd.concat(un_rows)
    S.to_csv(OUT / "calibration_variants.csv", index=False)
    U.round(4).to_csv(OUT / "calibration_units.csv", index=False)

    # --- Report -----------------------------------------------------------------------------
    lab = {(2, 1): "sav above", (2, 3): "sav below", (3, 1): "grs above", (3, 3): "grs below",
           (1, 2): "forest affected"}
    rep.insert(0, "Fire-regime calibration (D15 §7). Shares of the stable area inside the units "
                  "(outside in brackets); flags = number of units; changed = units whose flag "
                  "differs from the baseline.\n")
    hdr = f"{'variant':<13}" + "".join(f"{v:>21}" for v in lab.values()) + \
          "   below>50%  above>20%  above>50%  forest>50%"
    rep.append(hdr)
    for name, _ in VARIANTS:
        s = S[S.variant == name]
        if s.empty:
            continue
        cells = []
        for (t, c) in lab:
            i = s[(s.inside) & (s.type == t) & (s.cls == c)].share.sum()
            o = s[(~s.inside) & (s.type == t) & (s.cls == c)].share.sum()
            cells.append(f"{i * 100:6.1f}% ({o * 100:5.1f}%)")
        m = U[U.variant == name].set_index("unit")
        fl = []
        for f in ("flag_below50", "flag_above20", "flag_above50", "flag_forest50"):
            n = int(m[f].sum())
            ch = int((m[f] != base_units[f].reindex(m.index, fill_value=False)).sum())
            fl.append(f"{n:4d} ({ch:+3d})" if name != "base" else f"{n:4d}      ")
        rep.append(f"{name:<13}" + "".join(f"{c:>21}" for c in cells) + "   " + "  ".join(fl))
    rep.append("\n(+n) = units whose flag changed relative to the baseline (in either direction).")

    fmp = EXT / "fire_calib_month.parquet"
    if fmp.exists():
        W = window_table(pd.read_parquet(fmp))
        W.round(4).to_csv(OUT / "calibration_windows.csv", index=False)
        rep.append("\nCritical window, share of burned stable open vegetation inside it "
                   "(window shifted -1 / product / +1 month), inside the units:")
        for _, r in W[W.inside].iterrows():
            rep.append(f"  {r.latband:<13} {r.subperiod}: {r['window-1'] * 100:5.1f}%  "
                       f"{r['window+0'] * 100:5.1f}%  {r['window+1'] * 100:5.1f}%   "
                       f"(July-August {r.jul_aug * 100:4.1f}%)")
    else:
        rep.append("\nWindow shifts: skipped (no fire_calib_month.parquet)")

    txt = "\n".join(rep) + "\n"
    (OUT / "calibration_report.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
