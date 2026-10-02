# D11 — Biome limits

**Status:** Accepted (2026-10-02, project lead's guidance)

## Context (project lead)
The official IBGE biome limit changed during the priority-area period:
- **2004 limit** (1:5,000,000): in force for the 1st update (2006) and the 2nd update (2012).
- **2019 limit** (1:250,000): the current one, used by MapBiomas.

The change affects which areas fall in each biome. It also affects MapBiomas queries: querying with the current limit leaves **gaps** where the limit moved.

## Decision
1. **Never clip extraction by biome.** Extraction runs over the D7 extent using the integrated national MapBiomas asset, so no area is lost at moved boundaries.
2. **Biome is a marker, not a mask.** Both `biome_2004` and `biome_2019` are attributes of every zone, so results can be reported under either limit.
3. **Bioma-level statistics** from the MapBiomas platform (computed with the 2019 limit) are not used as denominators for priority-area metrics.

## Caveat to monitor
MapBiomas classifies each biome with its own models and then integrates them. Class definitions can therefore show **seams at the 2019 boundary** (e.g. savanna vs. forest formation), and priority areas crossing it may show spurious class contrasts. Flag zones within a buffer of the 2019 limit and test whether class proportions jump at the line.
