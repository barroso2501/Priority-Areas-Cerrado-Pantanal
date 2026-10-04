# Findings from source reconciliation

Reproducible with `scripts/reconcile_2nd_update.py` unless noted. Tags: **[E]** evidence · **[H]** hypothesis.

## 1. The MMA layer and the fact sheets are the same dataset
[E] For the 278 areas with a fact sheet, the MMA layer agrees **278/278** on name, biological importance, action priority, area (ratio exactly 1.0) and all four actions (`Acao1` = main; `Acao2..4` = secondary 1..3). The fact sheets are a report generated from the layer.

## 2. The WWF/MMA (2015) report mislabels importance as "priority"
[E] The "Prioridade" column in Annex I of the report equals `Import_bio` in the MMA layer and the fact sheets. It does **not** equal `Prior_acao`. This was checked on 17 areas by visual comparison; for example, Rio Taboco reads "Muito Alta" in Annex I, while the layer has importance Muito Alta and priority Extremamente Alta. The report text ("69 of extreme priority, 152 very high, 79 high") also follows importance.
**Rule adopted:** use the MMA layer fields; treat the report's "priority" as biological importance.

## 3. The 22 codes missing from the fact sheets
- [E] **16** of them are in the MMA layer (codes 4, 13, 17, 27, 30, 42, 44, 85, 86, 88, 95, 96, 98, 103, 152, 154). **All 16** lie within 2 km of a Cerrado/Pantanal hybrid area. Among the 278 areas with a fact sheet, only 20 do.
- [H, strong] Fact sheets were not issued for areas edited during inter-biome harmonization.
- [E] The other **6** codes (57, 61, 81, 93, 171, 286) are absent from the MMA layer.

## 4. The six areas absorbed into hybrids
- [E] Manual comparison of Annex I with the layer. Annex I has 300 rows: 69 Extremamente Alta, 152 Muito Alta and 79 Alta, matching the report text. The six rows missing from the layer are:
  - Mococa (MG/SP, Muito Alta)
  - Rio Coronel Vanick (MT, Muito Alta)
  - Rio Cravari II (MT, Muito Alta)
  - Rio Jauru – MT (MT, Muito Alta)
  - Rio Cinta Larga (MT, Alta)
  - Xique-xique (BA, Alta)
- [H] They were absorbed into hybrid areas. Supporting evidence:
  - All six lie in transition zones with the Amazon, Caatinga or Atlantic Forest.
  - The town of Xique-Xique is 12 km from `CAA_CerraPa007` and 72 km from the nearest Cerrado area.
  - Area balance: 74.28 Mha (layer) + 1.91 Mha (CerraPa hybrids) = 76.19 Mha, against 76.36 Mha in Table 1 of the report (−0.2%).
  - The MMA page states that the 2016 areas are kept except for overlaps, which are now delivered as hybrid areas.
- **Not determinable** from these sources: which free code belongs to which name (open issue P1).

## 5. Consequences for the assessment
- **Universe of the 2nd update:** 294 MMA areas + 54 `*CerraPa*` hybrids (decision D2).
- Hybrid classes (`IB_pos`/`PA_pos`) may differ from the original class. Example: Xique-xique was Alta in Annex I; the neighbouring hybrid is Muito Alta importance / Extremamente Alta priority.
- No attribute links a hybrid to its area of origin; the link is by geometry only (open issue P2).
- Report statistics that use "priority" must be re-read as importance before any comparison by class.

## 6. Self-overlaps in the 1st-update layer
[E] Twenty pairs of 2006 areas overlap by more than 1 ha, 124 kha in total. The largest is Pa016 × Pa021 (109 kha); the others are mostly a few hundred to a few thousand hectares (Ce007 × Ce009, 8.6 kha). The 2nd-update layer and the hybrids have no self-overlaps. The partition keeps overlapping pieces with a multi-code marker (D7). Reports of the 2006 network area must use the flattened total (101.05 Mha), not the sum of individual areas.

## 7. Effect of the biome-limit change on the priority areas
[E] From the zone partition (`data/derived/zones_attributes.csv`):

| Layer | Total (Mha) | Outside Cerrado+Pantanal, 2004 limit | Outside Cerrado+Pantanal, 2019 limit | Biome label differs 2004 vs. 2019 |
|---|---|---|---|---|
| 1st update (2006) | 101.05 | 2.68 (2.7%) | 6.80 (6.7%) | 7.70 (7.6%) |
| 2nd update (2012) | 74.28 | 0.76 (1.0%) | 4.28 (5.8%) | 5.78 (7.8%) |
| Cerrado/Pantanal hybrids | 1.91 | 0.16 (8.6%) | 0.55 (28.7%) | 0.51 (26.7%) |

- Clipping by the current (2019) limit would discard 4.3 Mha of the 2nd-update areas and 6.8 Mha of the 1st-update areas. This confirms D11: biome is a marker, never a mask.
- Within the extent, the biome reassignments between 2004 and 2019 are large:
  - Cerrado (2004) → Caatinga 9.2, Atlantic Forest 5.5, Amazon 4.0, Pantanal 1.0 Mha;
  - into Cerrado (2019) ← Caatinga 6.7, Atlantic Forest 4.1, Amazon 2.7, Pantanal 0.6 Mha.
- Part of these differences reflects map scale (1:5,000,000 vs. 1:250,000) and is not a conceptual change of the limit. The two cannot be separated with these files.

## 8. SAD69 → SIRGAS 2000 shift of the 1st-update layer
[E] With the official IBGE grid, the 2006 polygons shift by 61–74 m (median 67 m). Overlaying them without the datum change would create spurious left/entered strips about two MapBiomas pixels wide.

## 9. First Earth Engine exports (2025 test year)
[E] From `lulc_area_2025.csv` and `fire_month_2025.csv` (test run, 2026-10-03):
- **Area closure.** For zones inside the national limits, the summed MapBiomas area equals the zone area: overall ratio 0.99998. Deviations above 5% occur only in very small zones (pixel-edge effects), 1.25 × 10⁻⁵ of the area.
- **Coverage gap.** About 86 kha of zones lie outside the IBGE state limits (beyond the border with Bolivia/Paraguay, in the Pantanal, or offshore), where MapBiomas Brazil has no pixels. They include 28.6 kha of 1st-update areas (e.g. Pa016) and 13.1 kha of 2nd-update areas (e.g. codes 224, 252). These areas cannot be assessed with MapBiomas Brazil. They are reported separately and never counted as "no vegetation".
- **2025 composition of the extent (234 Mha).** Natural 124.4 Mha; anthropic 109.8 Mha (pasture 61.2, soybean 22.7). Native cover in the 2nd-update areas is 59.7%.
- **2025 fire.** 9.05 Mha burned in the extent: 85% in native vegetation, 15% in land use; peak in September–October (5.9 Mha). [H] To be cross-checked against MapBiomas Fire platform statistics for the same area. The stability flag in this test file may predate the corrected legend (class 7, D8); the full run supersedes it.

## 10. Full Phase 1 extraction, QC (2026-10-03)
[E] From `qc_report.txt` (`90_collect_exports.py`):
- **LULC area.** 41 years (1985–2025); overall area ratio 1.0000. Covered zones above 10 ha that deviate by more than 5% represent 1.25 × 10⁻⁵ of the area (pixel-edge effects in small zones).
- **Transitions.** Total transition area t→t+1 matches the LULC area of year t within 0.33% (maximum relative difference per zone-year).
- **Fire.** Monthly burned area for 41 years, all 12 months present.
- **Coverage gap.** 43 zones with pixels (70 kha) lie outside the 2019 national biome map; they are reported apart (see §9).
- **Fire intervals.** Not in this collection run. The first task failed on an image-type error, fixed in commit ce813c4. The re-run export is analysed in §11.

## 11. Fire-return intervals in stable native vegetation, 1985–2025 (first look)
[E] From `fire_intervals_w1985_2025.csv` (9,993 zone × modal-class groups):
- **QC.** never + Σ left = stable and never + Σ right = stable, exactly (maximum relative difference 0). The interval bookkeeping is consistent.
- **Stable native vegetation** (native in all 41 years, domain level, D9): 105.6 Mha in the extent. **48% never burned** in 1985–2025.

| Modal class | Stable area (Mha) | Never burned |
|---|---|---|
| Savanna formation | 52.3 | 36% |
| Forest formation | 38.0 | 73% |
| Grassland formation | 7.4 | 25% |
| Wetland (campo alagado) | 6.4 | 22% |
| Rocky outcrop | 1.1 | 49% |

- **Closed intervals** (between two observed fires): the area-weighted median is about **3 years** in every major class, including forest formation.

[H] Interpretation, not yet tested:
1. In the Cerrado, "forest formation" includes cerradão and transition forests that can burn. Short intervals in this class may still signal degradation (D3), not a natural regime.
2. Part of the short intervals may come from commission errors in MapBiomas Fire (spurious scars in consecutive years). This needs a sensitivity test, for example a minimum scar size or a confirmed-burn rule, before the result is reported.
3. The closed-interval median ignores the 48% never-burned area and the censored intervals. The regime must be described with survival methods (D9), never with this median alone.
