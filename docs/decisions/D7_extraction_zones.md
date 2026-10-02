# D7 — Extraction zones (flat partition with markers)

**Status:** Accepted (2026-10-02, project lead)

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
| `uf` | IBGE states | state code |

## Extent
- The union of every priority-area polygon (2006, 2012 and hybrids) with the 2004 and 2019 Cerrado + Pantanal limits.
- Areas outside every priority area are kept as "neither" zones, the pool for controls (D5).

## Rationale
The 2006 and 2012 layers overlap only in part, and the biome limit changed between cycles. A flat partition defers the universe decision (D2) to the analysis stage at no extra GEE cost.
