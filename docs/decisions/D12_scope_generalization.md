# D12 — Scope and generalization

**Status:** Accepted (2026-10-02, project lead)

## Decision
1. **The Cerrado (with the Pantanal) is the pilot.** The pipeline is **parameterized by biome**: priority-area layers, hybrids, milestones, fire rules and legend groupings are inputs, not hard-coded values.
2. **Limits of generalization, stated upfront:**
   - **Milestones (D1) become a per-biome table.** The 2nd update had different dates and processes per biome (Amazon, Caatinga, Atlantic Forest, Pampa, coastal-marine).
   - **Fire rules do not transfer.** D9 is valid for fire-adapted savanna systems. In the Amazon and the Atlantic Forest, fire in native vegetation is almost always degradation; the Pampa and the Pantanal have their own regimes. The thresholds in D3 are biome-specific.
   - **Coastal and marine systems.** MapBiomas covers the coastal fringe (mangrove, hypersaline tidal flat, beach/dune) but not the marine environment. **The marine zone is outside the scope of this method.** This is stated to MMA explicitly rather than stretching the approach.
   - **Hybrid areas become a national concern**, not only the Cerrado ones. The flat partition (D7) already supports any set of layers.
3. **Products:**
   - the MMA diagnostic (primary);
   - data-governance lessons ([`../data_governance.md`](../data_governance.md));
   - a scientific paper (secondary). Candidate contributions: Q6, Q3, and the fire regime in stable areas with censored intervals.
