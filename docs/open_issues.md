# Open issues

| ID | Issue | Status | Impact | How to close |
|---|---|---|---|---|
| P1 | Code ↔ name for the 6 areas absent from the MMA layer (codes 57, 61, 81, 93, 171, 286 ↔ Mococa, Rio Coronel Vanick, Rio Cravari II, Rio Jauru – MT, Rio Cinta Larga, Xique-xique) | open. [H] Absorbed into hybrid areas (see [findings](findings.md) §4). | low for spatial analysis (the geometry lives in the hybrids); high for tracking each area's history | request the MMA/GEF editing database (`CerradoPantanal_pos_v5`) or the harmonization table |
| P2 | Link between each hybrid and its area of origin (no common attribute) | open | determines the class used and the 2006 × 2012 comparison at biome borders | by geometry (overlap with 2006, adjacency to the CP layer) or the MMA editing database |
| P3 | Meaning of `SUM_NAT_2` in the target GDB | open. [H] Native area (ha) within the target distribution | needed for Q3 (target goals) | recompute 2009 native area per target and compare |
| P4 | Land-system code crosswalk: Annex II (`AAcDnSa`) × GDB (`LANDSCAPE5` + `GRUPO_VEG`) | open | goals of ecosystem targets | infer the coding rule or request the legend |
| P5 | Annex II (goals, % met) exists only as PDF | open; text is extractable | Q3 | extract to CSV |
| P6 | Whether the 1st update (2006) used a formal cost surface | open. [L] Nothing in the available documents | defines whether cost at T0 is retrospective (see D4) | MMA (2007) *Biodiversidade 31* report |
