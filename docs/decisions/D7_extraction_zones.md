# D7 — Extraction zones (flat partition with markers)

**Status:** Accepted (2026-10-02, project lead) · Implemented

## Decision
Overlay all territorial layers **once**, in vector, to produce a flat partition in which every piece carries a full set of markers. Each unique marker combination receives a `zone_id`. GEE extracts statistics per `zone_id`. Every analysis territory is recovered afterwards by aggregating zones, without going back to GEE: 2006 area, 2012 area, hybrids, transition strata, biome (2004 or 2019 limit), state.

## Markers
| Marker | Source | Values |
|---|---|---|
| `ap2006_code` | 1st update (reprojected per D10) | Ce###/Pa### or null |
| `ap2006_type` | 1st update | Nova / Protegida / null |
| `ap2012_code` | MMA 2nd-update layer | 1–300 or null |
| `hybrid_code` | MMA hybrids (`*CerraPa*`) | code or null |
| `biome_2004` | IBGE 2004 limit (1:5,000,000) | biome name |
| `biome_2019` | IBGE 2019 limit (1:250,000) | biome name |
| `uf` | IBGE states, 2025 | state code; limits assumed stable over the period (project lead, 2026-10-02) |

## Extent
- The union of every priority-area polygon (2006, 2012 and hybrids) with the 2004 and 2019 Cerrado + Pantanal limits.
- Areas outside every priority area are kept as "neither" zones, the pool for controls (D5).

## Implementation notes (2026-10-02)
- **Script:** `scripts/build_zones.py`. Output: 3,387 zones over a 234.4 Mha extent; zone areas sum to the extent (relative difference 2 × 10⁻¹⁰).
- **Overlapping 2006 codes.** The 1st-update layer has self-overlapping areas (20 pairs > 1 ha, 124 kha in total; largest Pa016 × Pa021, 109 kha). These pieces carry a **multi-code marker** joined with "|" (e.g. `Pa016|Pa021`), so no area is counted twice. To aggregate by 2006 area, split the marker.
- **Slivers.** 386 zones are smaller than 1 ha (82 ha in total); they may vanish when rasterized at 30 m.
- **Biome markers.** `biome_2004` includes the IBGE classes for inland and coastal water ("Massa Dagua …"); `none` means outside every class of that layer (offshore or edge slivers).

## Rationale
The 2006 and 2012 layers overlap only in part, and the biome limit changed between cycles. A flat partition defers the universe decision (D2) to the analysis stage at no extra GEE cost.
