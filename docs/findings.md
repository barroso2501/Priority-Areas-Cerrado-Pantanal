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
