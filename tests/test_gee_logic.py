"""
Offline tests of the Earth Engine logic (no EE account needed).

1. Key encodings round-trip through the decoders in 90_collect_exports.py.
2. The fire-interval algorithm of 21_extract_fire_intervals.py (re-implemented with
   numpy, operation by operation) matches a direct per-pixel enumeration, and satisfies
   never + sum(left) == stable == never + sum(right).

Run from the repository root:   python tests/test_gee_logic.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collect", ROOT / "scripts/gee/90_collect_exports.py")
collect = importlib.util.module_from_spec(spec); spec.loader.exec_module(collect)
rng = np.random.default_rng(42)

# 1) encodings --------------------------------------------------------------------------
z, c, c2, s, m, y = 3387, 75, 33, 1, 12, 2025
assert collect.decode_lulc(pd.DataFrame({"key": [z*1000+c], "sum": [1.0], "year": [y]})).iloc[0][["zone_id","class"]].tolist() == [z, c]
r = collect.decode_trans(pd.DataFrame({"key": [z*10000+c*100+c2], "sum": [1.0], "year": [y]})).iloc[0]
assert [r.zone_id, r.class_from, r.class_to] == [z, c, c2]
r = collect.decode_fire_month(pd.DataFrame({"key": [((z*2+s)*100+c)*13+m], "sum": [1.0], "year": [y]})).iloc[0]
assert [r.zone_id, r.stable, r["class"], r.month] == [z, s, c, m]
assert ((z*2+1)*100+99)*13+12 < 2**31 and z*10000+9999 < 2**31   # int32 safe
print("encodings OK")

# 2) intervals ---------------------------------------------------------------------------
a, b = 1985, 2025
ys = np.arange(a, b + 1); W = len(ys)
n = 5000
burn = rng.random((n, W)) < rng.uniform(0, 0.5, size=(n, 1))   # pixels with varied fire frequency

# (i) algorithm exactly as written for Earth Engine
prev = np.zeros(n); closed = []
for j, yy in enumerate(ys):
    bj = burn[:, j]
    closed.append(np.where(bj & (prev > 0), yy - prev, 0))
    prev = np.where(bj, yy, prev)
closed = np.stack(closed, 1); last = prev
first = np.where(burn.any(1), ys[np.argmax(burn, 1)], 0)
left_len, right_len = first - a + 1, b + 1 - last
ee_counts = {"never": (first == 0).sum()}
for L in range(1, W):     ee_counts[f"closed_{L}"] = (closed == L).sum()
for L in range(1, W + 1): ee_counts[f"left_{L}"] = ((first > 0) & (left_len == L)).sum()
for L in range(1, W + 1): ee_counts[f"right_{L}"] = ((last > 0) & (right_len == L)).sum()

# (ii) direct enumeration per pixel
ref = {k: 0 for k in ee_counts}
for p in range(n):
    fy = ys[burn[p]]
    if len(fy) == 0: ref["never"] += 1; continue
    ref[f"left_{fy[0]-a+1}"] += 1; ref[f"right_{b-fy[-1]+1}"] += 1
    for d in np.diff(fy): ref[f"closed_{d}"] += 1
assert ee_counts == ref, "interval algorithm differs from enumeration"

# (iii) through the decoder + QC identity
vals = [n, ee_counts["never"]] + [ee_counts[f"closed_{L}"] for L in range(1, W)] \
     + [ee_counts[f"left_{L}"] for L in range(1, W+1)] + [ee_counts[f"right_{L}"] for L in range(1, W+1)]
df = pd.DataFrame({"key": [z*100+4], "sum": [json.dumps([int(v) for v in vals])], "window": ["w"], "W": [W]})
d = collect.decode_intervals(df)
g = d.groupby("metric").ha.sum()
assert g["never"] + g["left"] == g["stable"] == g["never"] + g["right"]
print("intervals OK:", {k: int(v) for k, v in g.items()})

# 3) Product 1 (D13): decoders and persistence masks -----------------------------------------
r = collect.decode_p1_trans(pd.DataFrame({"key": [z*10000+c*100+c2], "sum": [1.0], "start": [2012], "end": [2025]})).iloc[0]
assert [r.zone_id, r.class_start, r.class_end] == [z, c, c2]
r = collect.decode_p1_persist(pd.DataFrame({"key": [z*1000+4], "sum": ["[10.0,6.0,8.0,1.0]"], "window": ["p"],
                                            "start": [2012], "end": [2025], "k_water": [6]})).iloc[0]
assert [r.zone_id, r.class_start, r.nat_start_ha, r.water_persistent_ha] == [z, 4, 10.0, 1.0]

# Masks exactly as written for Earth Engine, on random class sequences
NAT, ANT, WATER, K = {3, 4, 12}, {15, 39}, 33, 6
pool = np.array([3, 4, 12, 15, 39, 33, 23])
yrs = np.arange(2012, 2026)
seq = pool[rng.integers(0, len(pool), size=(4000, len(yrs)))]
seq[:500, -K:] = WATER                     # force some persistent water at the end
nat_y = np.isin(seq, list(NAT)); ant_y = np.isin(seq, list(ANT))
nat_start = nat_y[:, 0]
strict = nat_start & nat_y.min(1)
never_ant = nat_start & ~ant_y.max(1)
water_p = nat_start & (seq[:, -K:] == WATER).min(1)
# per-pixel definitions
for i in range(len(seq)):
    s_ = seq[i]
    if s_[0] not in NAT:
        assert not (strict[i] or never_ant[i] or water_p[i]); continue
    assert strict[i] == all(v in NAT for v in s_)
    assert never_ant[i] == all(v not in ANT for v in s_)
    assert water_p[i] == all(v == WATER for v in s_[-K:])
assert (strict <= never_ant).all() and (water_p & strict).sum() == 0
print("product 1 OK: nat_start", nat_start.sum(), "strict", strict.sum(), "never_anthropic", never_ant.sum(),
      "water_persistent", water_p.sum())

# 4) Fire regime categories (D15 revised): image algebra of 22_extract_fire_regime.py vs. rules
EMIN, EMAX, KSHORT = 3, 20, 2
ALL = list(range(1985, 2026))
p_ = rng.uniform(0, 0.7, size=(20000, 1))
bball = (rng.random((20000, len(ALL))) < p_).astype(int)
stop = rng.integers(1990, 2026, size=20000); stop[rng.random(20000) < 0.6] = 2100
bball[np.array(ALL)[None, :] > stop[:, None]] = 0
bball[rng.random(20000) < 0.1] = 0


def algebra(ball):
    n_all = ball.sum(1); last = np.zeros(len(ball)); prev = np.zeros(len(ball)); n_short = np.zeros(len(ball))
    for j, y in enumerate(ALL):
        f = ball[:, j] == 1
        n_short += f & (prev > 0) & ((y - prev) < EMIN)
        prev[f] = y; last[f] = y
    deficit = (n_all == 0) | (last <= ALL[-1] - EMAX)
    cls = np.full(len(ball), 2); cls[n_short >= KSHORT] = 1; cls[deficit] = 3
    fcls = np.where(n_all > 0, 2, 1)
    return cls, fcls


def direct(row):
    yrs = [y for y, v in zip(ALL, row) if v]
    f = 2 if yrs else 1
    if not yrs or yrs[-1] <= ALL[-1] - EMAX:
        return 3, f
    short = int((np.diff(yrs) < EMIN).sum())
    return (1 if short >= KSHORT else 2), f


oc, fc = algebra(bball)
ref = np.array([direct(r) for r in bball])
assert (oc == ref[:, 0]).all() and (fc == ref[:, 1]).all(), "fire-regime categories differ from the rules"
print("fire regime OK:", {k: int((oc == k).sum()) for k in (1, 2, 3)})


# 5) Fire calibration (D15 §7): signature of 23_extract_fire_calibration.py -----------------
# The signature algebra (as written for Earth Engine) goes through the key encoding and the
# decoder of 90_collect_exports.py, then classify() of product2_calibration.py must give,
# for every threshold variant, the categories of the direct per-pixel rules.
spec2 = importlib.util.spec_from_file_location("p2cal", ROOT / "scripts/analysis/product2_calibration.py")
p2cal = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(p2cal)
LAST = ALL[-1]
EDGES = [LAST - 9, LAST - 14, LAST - 19, LAST - 24]


def signature(ball):
    prev = np.zeros(len(ball)); n3 = np.zeros(len(ball)); n1 = np.zeros(len(ball))
    for j, y in enumerate(ALL):
        f = ball[:, j] == 1
        closed = f & (prev > 0)
        n3 += closed & ((y - prev) < 3)
        n1 += closed & ((y - prev) == 1)
        prev[f] = y
    n3 = np.minimum(n3, 3); n1 = np.minimum(n1, 3)
    tsl = np.full(len(ball), 5)
    tsl[prev > 0] = 4
    for v, e in zip((3, 2, 1, 0), EDGES[::-1]):
        tsl[prev >= e] = v
    return ((n3 * 4 + n1) * 6 + tsl).astype(np.int64)


vt = rng.integers(1, 5, size=len(bball)); zz = rng.integers(1, 3388, size=len(bball)); cs = rng.integers(0, 2, size=len(bball))
key = ((zz * 5 + vt) * 96 + signature(bball)) * 2 + cs
assert key.max() < 2**31
dec = collect.decode_fire_calib(pd.DataFrame({"key": key, "sum": 1.0, "window": "fy1985_2025"}))
assert (dec.zone_id.values == zz).all() and (dec.type.values == vt).all() and (dec.cs.values == cs).all()


def direct_v(row, t, N, k, short):
    yrs = [y for y, v in zip(ALL, row) if v]
    if t == 1:
        return 2 if yrs else 1
    if not yrs or yrs[-1] <= LAST - N:
        return 3
    gaps = np.diff(yrs)
    ns = int((gaps < 3).sum()) if short == 3 else int((gaps == 1).sum())
    return 1 if ns >= k else 2


for N in (10, 15, 20, 25):
    for k in (1, 2, 3):
        for short in (3, 1):
            got = p2cal.classify(dec, N, k, short).values
            ref = np.array([direct_v(r, t, N, k, short) for r, t in zip(bball, vt)])
            assert (got == ref).all(), f"calibration classes differ: N={N} k={k} short={short}"
# the product setting must equal the fire_regime algebra of section 4
got = p2cal.classify(dec, 20, 2, 3).values
assert (got[vt != 1] == oc[vt != 1]).all() and (got[vt == 1] == fc[vt == 1]).all()

# month decoder
mk = (np.array([3387, 1]) * 5 + np.array([3, 2])) * 4 + np.array([2, 0])
mv = [json.dumps(list(range(24))), json.dumps([0.5] * 24)]
dm = collect.decode_fire_calib_month(pd.DataFrame({"key": mk, "sum": mv}))
r = dm.iloc[13]
assert [r.zone_id, r.type, r.latband, r.subperiod, r.month, r.ha] == [3387, 3, 2, "sp2", 2, 13]
print("fire calibration OK: 24 variants match the rules")
