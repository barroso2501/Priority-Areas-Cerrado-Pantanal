"""
build_zones.py — Build the flat partition of extraction zones (decision D7).

Every piece of territory in the study extent receives the full set of markers:
  ap2006_code, ap2006_type, ap2012_code, hybrid_code, biome_2004, biome_2019, uf
Each unique marker combination is one zone (zone_id). GEE extracts MapBiomas
statistics per zone_id; any analysis territory is rebuilt afterwards by summing zones.

Inputs (see data/README.md):
  data/raw/ap2006/Areas_prioritarias_2006_codigos.shp        1st update (SAD69 / Polyconic)
  data/raw/cerrado_pantanal/Cerrado_Pantanal_2a_atualizacao.shp
  data/raw/areas_hibridas/Areas_hibridas_2a_atualizacao.shp
  data/raw/biomas_2004/Biomas5000.shp                         IBGE 1:5,000,000 (2004 limit)
  data/raw/biomas_2019/lm_bioma_250.shp                       IBGE 1:250,000 (2019 limit)
  data/raw/uf/BR_UF_2025.shp                                  IBGE states (assumed stable, see below)
  data/grids/br_ibge_SAD69_003.tif                            official IBGE SAD69->SIRGAS 2000 grid (D10)
Outputs:
  data/interim/zones.gpkg            zone polygons (EPSG:4674, for upload to GEE) + Albers copy
  data/derived/zones_attributes.csv  one row per zone_id: markers + area_ha
  data/derived/zones_qc.txt          QC report (grid shift, slivers, area checks)

Run from the repository root:   python scripts/build_zones.py      (takes several minutes)

Assumptions recorded here:
  - State (UF) limits did not change significantly during the assessment period
    (project lead, 2026-10-02), so a single 2025 UF layer is used.
  - The IBGE 2004 file ships its CRS as "Biomas5000.prj.txt" (not read by GDAL); its
    content is SIRGAS 2000 geographic, so EPSG:4674 is assigned explicitly.
  - Study extent = Cerrado + Pantanal under the 2004 OR 2019 limit, plus every priority
    area polygon (2006, 2012, Cerrado/Pantanal hybrids), whatever biome it falls in.

What can break, and how you would notice:
  - Missing grid file -> the script stops with an explicit error. It never falls back to a
    3-parameter shift, which would silently misplace the 2006 polygons by ~5 m.
  - The QC report prints the SAD69->SIRGAS shift statistics. Expect tens of metres
    (~40-60 m in Central Brazil). Values near 0 mean the grid was not applied.
  - Total zone area must equal the extent area (QC prints the relative difference; it
    should be < 0.01%). A larger value means overlay pieces were lost.
  - Sliver zones (< 1 ha, i.e. about 11 MapBiomas pixels) are kept but listed in QC. When
    rasterized at 30 m they may vanish, so their area should be small in total.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import shapely
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[1]
RAW, DER, INT = ROOT / "data/raw", ROOT / "data/derived", ROOT / "data/interim"
GRIDS = ROOT / "data/grids"
ALBERS = "ESRI:102033"  # South America Albers Equal Area Conic (metres)


def clean(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Repair invalid geometries and keep only polygonal parts
    g = g.copy()
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g.explode(index_parts=False)  # also splits GeometryCollections into parts
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"]) & ~g.is_empty]
    return g


def load_2006() -> tuple[gpd.GeoDataFrame, str]:
    """1st-update areas: dissolve by code, SAD69 -> SIRGAS 2000 with the IBGE grid (D10)."""
    grid = GRIDS / "br_ibge_SAD69_003.tif"
    if not grid.exists():
        raise FileNotFoundError(f"IBGE grid not found: {grid}. See data/README.md (D10).")
    pyproj.datadir.append_data_dir(str(GRIDS))
    g = gpd.read_file(RAW / "ap2006/Areas_prioritarias_2006_codigos.shp")
    g = clean(g).dissolve("COD_ID", aggfunc="first").reset_index()
    # Step 1: undo the Polyconic projection only (same SAD69 datum, no datum shift)
    g = g.to_crs(4618)
    # Step 2: explicit grid shift SAD69 -> SIRGAS 2000 (no fallback allowed)
    pipe = pyproj.Transformer.from_pipeline(
        "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
        f"+step +proj=hgridshift +grids={grid.name} +step +proj=unitconvert +xy_in=rad +xy_out=deg")
    before = g.geometry.representative_point()
    g["geometry"] = [shp_transform(lambda x, y, z=None: pipe.transform(x, y), geom) for geom in g.geometry]
    g = g.set_crs(4674, allow_override=True)
    # QC: shift of the representative points, in metres
    # Same numbers read as SIRGAS vs. shifted coordinates = displacement caused by the grid
    b = gpd.GeoSeries(list(before), crs=4674).to_crs(ALBERS)
    a = gpd.GeoSeries([shp_transform(lambda x, y, z=None: pipe.transform(x, y), p) for p in before], crs=4674).to_crs(ALBERS)
    d = b.distance(a)
    if not np.isfinite(d).all() or d.max() < 1:
        raise RuntimeError("Grid shift not applied (non-finite or ~0 m shift).")
    qc = f"SAD69->SIRGAS grid shift (m): min {d.min():.1f}, median {d.median():.1f}, max {d.max():.1f}"
    g = g.rename(columns={"COD_ID": "ap2006_code", "FIRST_tipo": "ap2006_type"})
    return g[["ap2006_code", "ap2006_type", "geometry"]], qc


def flatten_overlaps(g: gpd.GeoDataFrame, cols: list[str]) -> gpd.GeoDataFrame:
    """Turn a layer with overlapping polygons into non-overlapping pieces.

    The 1st-update layer has overlapping areas (e.g. Pa016 x Pa021, ~109 kha). An identity
    overlay would duplicate those pieces and inflate totals. Here each piece of the
    planar arrangement keeps every code covering it, joined with "|" (e.g. "Pa016|Pa021").
    """
    lines = shapely.union_all(g.boundary.values)
    pieces = gpd.GeoDataFrame(geometry=list(shapely.get_parts(shapely.polygonize([lines]))), crs=g.crs)
    pts = gpd.GeoDataFrame(geometry=pieces.representative_point(), crs=g.crs)
    j = gpd.sjoin(pts, g, predicate="within")
    agg = j.groupby(level=0)[cols].agg(lambda x: "|".join(sorted(set(map(str, x)))))
    out = pieces.join(agg, how="inner")  # pieces covered by no polygon (holes) are dropped
    return out.dissolve(cols).reset_index()


def load_layers():
    ap06, qc_shift = load_2006()
    ap12 = clean(gpd.read_file(RAW / "cerrado_pantanal/Cerrado_Pantanal_2a_atualizacao.shp"))
    ap12 = ap12.rename(columns={"COD_area": "ap2012_code"})[["ap2012_code", "geometry"]]
    hyb = clean(gpd.read_file(RAW / "areas_hibridas/Areas_hibridas_2a_atualizacao.shp"))
    hyb = hyb[hyb.COD_area.str.contains("CerraPa")].rename(columns={"COD_area": "hybrid_code"})
    hyb = hyb[["hybrid_code", "geometry"]]
    b04 = gpd.read_file(RAW / "biomas_2004/Biomas5000.shp").set_crs(4674, allow_override=True)
    b04 = clean(b04).rename(columns={"NOM_BIOMA": "biome_2004"})[["biome_2004", "geometry"]]
    b19 = clean(gpd.read_file(RAW / "biomas_2019/lm_bioma_250.shp"))
    b19 = b19.rename(columns={"Bioma": "biome_2019"})[["biome_2019", "geometry"]]
    uf = clean(gpd.read_file(RAW / "uf/BR_UF_2025.shp")).rename(columns={"SIGLA_UF": "uf"})[["uf", "geometry"]]
    layers = {"ap2006": ap06, "ap2012": ap12, "hybrid": hyb, "b04": b04, "b19": b19, "uf": uf}
    # Reprojection can re-introduce invalid rings: repair again in Albers and snap to a
    # 1 cm grid so the overlays below are numerically stable
    out = {}
    for k, v in layers.items():
        v = clean(v.to_crs(ALBERS))
        v["geometry"] = shapely.set_precision(v.geometry.values, 0.01)
        out[k] = clean(v)  # make_valid + explode collections + keep polygons
    # Overlaps exist only in the 2006 layer (checked: none in the 2012 layer or the hybrids)
    out["ap2006"] = clean(flatten_overlaps(out["ap2006"], ["ap2006_code", "ap2006_type"]))
    return out, qc_shift


def main():
    L, qc_shift = load_layers()
    # Study extent: Cerrado+Pantanal under either limit, plus every priority-area polygon
    target = ["Cerrado", "Pantanal"]
    parts = [L["b04"][L["b04"].biome_2004.isin(target)], L["b19"][L["b19"].biome_2019.isin(target)],
             L["ap2006"], L["ap2012"], L["hybrid"]]
    extent = shapely.union_all([shapely.union_all(p.geometry.values) for p in parts])
    ext = gpd.GeoDataFrame(geometry=[extent], crs=ALBERS)
    print("extent built")

    # Sequential identity overlays: every piece keeps the markers of every layer
    z = ext
    for key in ["b04", "b19", "uf", "ap2006", "ap2012", "hybrid"]:
        lyr = clean(gpd.clip(L[key], ext))  # restrict to the extent first (speed); clip can return mixed types
        z = gpd.overlay(z, lyr, how="identity", keep_geom_type=True)
        print(f"overlay {key}: {len(z)} pieces")

    markers = ["ap2006_code", "ap2006_type", "ap2012_code", "hybrid_code", "biome_2004", "biome_2019", "uf"]
    for m in markers:  # explicit "none" so groupby keeps empty markers
        z[m] = z[m].astype("object").where(z[m].notna(), "none").astype(str)
    zones = z.dissolve(markers).reset_index()
    zones.insert(0, "zone_id", np.arange(1, len(zones) + 1, dtype=int))
    zones["area_ha"] = zones.area / 1e4

    # QC ------------------------------------------------------------------------------
    rel = abs(zones.area_ha.sum() - extent.area / 1e4) / (extent.area / 1e4)
    sl = zones[zones.area_ha < 1]
    qc = [qc_shift,
          f"zones: {len(zones)}; extent {extent.area/1e10:.3f} Mha; zones sum {zones.area_ha.sum()/1e6:.3f} Mha; rel diff {rel:.2e}",
          f"sliver zones < 1 ha: {len(sl)} ({sl.area_ha.sum():.1f} ha in total)",
          "area (Mha) by priority status:",
          zones.assign(s=np.select([(zones.ap2006_code != "none") & (zones.ap2012_code != "none"),
                                    zones.ap2006_code != "none", zones.ap2012_code != "none",
                                    zones.hybrid_code != "none"],
                                   ["both", "2006 only (left)", "2012 only (entered)", "hybrid only"], "neither"))
               .groupby("s").area_ha.sum().div(1e6).round(3).to_string(),
          "area (Mha) biome_2004 x biome_2019:",
          zones.pivot_table(index="biome_2004", columns="biome_2019", values="area_ha", aggfunc="sum").div(1e6).round(3).to_string()]
    DER.mkdir(parents=True, exist_ok=True); INT.mkdir(parents=True, exist_ok=True)
    (DER / "zones_qc.txt").write_text("\n".join(qc) + "\n", encoding="utf-8")
    print("\n".join(qc))

    zones.drop(columns="geometry").to_csv(DER / "zones_attributes.csv", index=False)
    zones.to_crs(4674).to_file(INT / "zones.gpkg", layer="zones_sirgas", driver="GPKG")
    zones.to_file(INT / "zones.gpkg", layer="zones_albers", driver="GPKG")


if __name__ == "__main__":
    main()
