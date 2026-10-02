# D10 — Reprojection of the 1st-update layer

**Status:** Accepted (2026-10-02, project lead)

Transform the 2006 layers from SAD69 (Polyconic, CM −54°) to SIRGAS 2000 using the **official IBGE transformation grid**, not a 3-parameter shift. Do this before building the partition (D7). Without it, polygons shift by tens of metres and create false *left/entered* slivers. Record the transformation used and the observed shift statistics in the output metadata.
