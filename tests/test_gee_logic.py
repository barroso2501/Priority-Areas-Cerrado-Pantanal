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
