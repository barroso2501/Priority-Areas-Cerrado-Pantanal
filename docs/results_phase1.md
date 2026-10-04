# Phase 1 — First descriptive results (Q1, Q6)

*Status: first pass, 2026-10-04. Descriptive only (no counterfactual). Milestones are provisional (D1 open): 2002, 2009, 2016, 2025.*
Reproduce with `python scripts/analysis/phase1_q1_q6.py`; tables in `data/derived/phase1/`.
Tags: **[E]** computed from the data · **[H]** interpretation to be tested.

## Definitions
- **Native vegetation:** classes with `fire_domain = native` (D8).
- **Shares** are computed on land area, i.e. excluding open water (class 33).
- **Excluded:** zones outside MapBiomas coverage (findings §9).
- **Rates:** annualized, as a percentage of the native area at the start of each period.
- **Gross loss / gain:** native ↔ non-native transitions summed year by year. **Net:** change in the native stock.

## 1. Strata (each zone counted once; covered land 231.6 Mha)

**Native share (%)** [E]

| Stratum | Land 2025 (Mha) | 1985 | 2002 | 2009 | 2016 | 2025 |
|---|---|---|---|---|---|---|
| stayed (2006 & 2012) | 41.7 | 87.6 | 77.8 | 74.8 | 71.9 | 66.2 |
| left (2006 only) | 57.3 | 86.5 | 76.0 | 73.0 | 70.6 | 66.3 |
| entered (2012 only) | 31.4 | 73.3 | 59.5 | 56.8 | 54.2 | 49.7 |
| hybrid only | 1.1 | 86.0 | 72.7 | 67.7 | 64.3 | 56.8 |
| neither | 99.3 | 66.7 | 49.5 | 46.0 | 43.5 | 39.4 |

**Net change of native area (% per year)** [E]

| Stratum | 1985–2002 | 2002–2009 | 2009–2016 | 2016–2025 |
|---|---|---|---|---|
| stayed | −0.59 | −0.48 | −0.63 | −0.83 |
| left | −0.65 | −0.52 | −0.50 | −0.64 |
| entered | −1.08 | −0.61 | −0.67 | −0.91 |
| hybrid only | −0.89 | −0.98 | −0.71 | −1.31 |
| neither | −1.49 | −0.98 | −0.80 | −1.02 |

**Gross loss (% per year)** [E]

| Stratum | 1985–2002 | 2002–2009 | 2009–2016 | 2016–2025 |
|---|---|---|---|---|
| stayed | 1.45 | 1.33 | 1.46 | 1.63 |
| entered | 1.98 | 1.57 | 1.61 | 1.78 |
| neither | 2.28 | 1.86 | 1.71 | 1.84 |

Gross gain (regrowth) is 0.6–0.9% per year in every stratum. Net change is therefore the difference between two flows of similar order. Secondary vegetation hides part of the conversion of old-growth vegetation; this is relevant for Q1 (D9 stability; see the work plan, "native never converted").

Readings:
- [E] **Every stratum lost native vegetation in every period.** Priority areas keep more native vegetation than "neither", and the gap in stock existed already in 1985 (selection, not effect).
- [E] **After 2016 (designation of the 2nd update) net loss accelerated in the 2012 areas:**
  - stayed: −0.63 → −0.83% per year;
  - entered: −0.67 → −0.91% per year.

  It also accelerated in "neither" (−0.80 → −1.02). The ratio between priority areas and outside is roughly constant.
- [H] Designation shows no detectable braking of loss in the descriptive series. This is **not** an effect estimate: selection, the agricultural frontier (Matopiba) and price cycles all act at the same time. Q2 (matched counterfactual) is needed before any causal statement.

## 2. Q6 — Did the 2012 revision respond to the state of the 2006 areas?
2006 areas of type "Nova" (281 areas), grouped by the share of their area kept in the 2012 layer. [E]

| Kept in 2012 | Areas | Mha | Native 2002 | Native 2009 | Net 2002–09 (%/yr) | Net 2016–25 (%/yr) | Mean share inside Ce+Pa (2019 limit) | Main UF = SP |
|---|---|---|---|---|---|---|---|---|
| dropped (<10%) | 62 | 8.7 | 0.71 | 0.69 | −0.09 | −0.32 | 0.72 | 18 |
| mostly dropped (10–50%) | 83 | 29.8 | 0.64 | 0.58 | −0.65 | −0.72 | 0.87 | 6 |
| mostly kept (50–90%) | 103 | 33.4 | 0.75 | 0.71 | −0.55 | −0.63 | 0.95 | 8 |
| kept (>90%) | 33 | 4.6 | 0.89 | 0.87 | −0.43 | −0.43 | 0.97 | 5 |

Spearman correlation between the share kept and native share in 2009: 0.16. Between the share kept and net change 2002–2009: −0.09. [E]

Readings:
- [E] **The fully kept areas were the best preserved** (87% native in 2009).
- [E] **The fully dropped areas were not the most degraded.** They had 69% native vegetation and almost no loss in 2002–2009. They lie partly outside the current Cerrado/Pantanal limit (28% of their area on average) and are concentrated in São Paulo (18 of 62).
- [E] **The association between pre-revision state and retention is weak.**
- [H] **The 2012 revision did not systematically drop degraded 2006 areas.** Retention looks driven more by methodology (formal targets, cost surface, Marxan with the 2006 areas pre-selected) and by geography (biome boundary, SP fragments) than by the 2002–2009 trajectory. To test:
  1. at zone level (pieces), not area level;
  2. controlling for biome limit and state;
  3. with the cost surface of 2012 (D4).

## 3. Q1 — 2012 areas (294; hybrids reported separately)

**Medians by biological importance** [E]

| Importance | Native 2009 | Native 2025 | Net 2009–16 | Net 2016–25 |
|---|---|---|---|---|
| Extremamente alta | 0.72 | 0.61 | −0.46 | −0.79 |
| Muito alta | 0.67 | 0.60 | −0.44 | −0.62 |
| Alta | 0.73 | 0.62 | −0.50 | −0.81 |

**Medians by action priority:** Extremamente alta 0.51 native in 2025 (−0.77%/yr); Muito alta 0.61; Alta 0.69. [E]

Readings:
- [E] **There is no gradient by importance class.** Areas of extremely high importance lose native vegetation at the same pace as the others.
- [E] **Priority is inversely related to native share.** This is consistent with priority encoding threat or urgency.
- [E] **Areas whose main action was "create a protected area"** (UC, UCPI, UCUS; 107 areas) kept 68–73% native vegetation in 2025, but still lost 0.5–0.85% per year in 2016–2025. Q4 must check which UCs were actually created.
- [E] **Distribution of net change 2016–2025:** median −0.72% per year. 19 areas lost more than 2% per year; 21 gained (net regrowth).
- [E] **Fastest losses 2016–2025** (native share 2016 → 2025):

  | Area | Code | UF | Native 2016 → 2025 |
  |---|---|---|---|
  | Nascente Uruçuí | 29 | PI | 87% → 56% |
  | Rio de Ondas | 75 | BA | 76% → 54% |
  | Rio Arrojado | 111 | BA | 74% → 55% |
  | Matões | 9 | MA | 96% → 73% |
  | Entorno RVS Veredas | 124 | BA | 80% → 61% |
  | Rio Sucuriju | 24 | MA | 91% → 70% |

  All are Matopiba frontier areas, mostly of extremely high importance.
- [E] **Hybrids** (54): median 70% native in 2025; median net change −0.86% per year in 2016–2025.

## 4. Caveats
- **Classification error.** No map-error band is applied yet. Native ↔ pasture confusion in grasslands inflates both gross loss and gross gain.
- **Milestones.** 2002, 2009 and 2016 are provisional (D1).
- **Hybrids.** Their classes are post-harmonization, and they are not linked to areas of origin (P2).
- **Coverage gaps.** Excluded areas (~86 kha) are not assessed.

## 5. Next analyses
1. **Native vegetation never converted since 1985 vs. secondary vegetation** per area, to separate old-growth loss from churn (needs a pixel-level product or a per-zone count of "never converted" area; not in the current extraction).
2. **Q6 at zone level,** controlling for biome limit and state.
3. **Fire:** burned area by domain and season per stratum; survival analysis of intervals (D9); sensitivity of intervals to small scars.
4. **Figures** for the MMA report: trajectories by stratum; map of net change 2016–2025 per area.
