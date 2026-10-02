"""
reconcile_2nd_update.py — Build one table with all 300 area codes of the
2nd update (Cerrado & Pantanal) and check consistency between sources.

Inputs (see data/README.md):
  data/raw/cerrado_pantanal/Cerrado_Pantanal_2a_atualizacao.shp   (MMA, 294 areas)
  data/raw/areas_hibridas/Areas_hibridas_2a_atualizacao.shp       (MMA, 163 hybrid areas)
  data/derived/fichas_areas.csv                                   (scripts/parse_fichas.py)
Output:
  data/derived/reconciliation_2nd_update.csv

Run from the repository root:   python scripts/reconcile_2nd_update.py

What can break, and how you would notice:
  - Missing fichas_areas.csv -> run scripts/parse_fichas.py first (FileNotFoundError).
  - Invalid geometries are repaired with buffer(0) after a 300 m simplification; this is
    only used for the adjacency test (≤ 2 km), never for area statistics.
  - Expected printout: 278/278 matches on every attribute, 16 fichas-less areas that all
    touch a hybrid. Different numbers mean the MMA files or the parser changed.
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, DER = ROOT / "data/raw", ROOT / "data/derived"
ALBERS = "ESRI:102033"  # South America Albers Equal Area (metres)

# Six areas listed in Annex I of the WWF/MMA (2015) publication but absent from the
# MMA layer. Transcribed manually from the PDF images (pp. 40-55); the class shown in
# the Annex "Prioridade" column corresponds to biological importance (see docs/findings.md).
ANNEX_ONLY = [
    ("Mococa", "MG, SP", "Muito Alta"),
    ("Rio Coronel Vanick", "MT", "Muito Alta"),
    ("Rio Cravari II", "MT", "Muito Alta"),
    ("Rio Jauru - MT", "MT", "Muito Alta"),
    ("Rio Cinta Larga", "MT", "Alta"),
    ("Xique-xique", "BA", "Alta"),
]


def norm(s: pd.Series) -> pd.Series:
    # Case/accent-insensitive comparison key
    return (s.fillna("").astype(str).str.normalize("NFKD")
             .str.encode("ascii", "ignore").str.decode("ascii")
             .str.upper().str.replace(r"[^A-Z0-9]", "", regex=True))


def main():
    cp = gpd.read_file(RAW / "cerrado_pantanal/Cerrado_Pantanal_2a_atualizacao.shp")
    hb = gpd.read_file(RAW / "areas_hibridas/Areas_hibridas_2a_atualizacao.shp")
    fichas = pd.read_csv(DER / "fichas_areas.csv")

    # 1) Attribute agreement between the MMA layer and the fichas -------------------
    m = cp.drop(columns="geometry").merge(fichas, left_on="COD_area", right_on="code")
    pairs = [("NOME", "name"), ("Import_bio", "biological_importance"),
             ("Prior_acao", "action_priority"), ("Acao1", "action_main"),
             ("Acao2", "action_sec1"), ("Acao3", "action_sec2"), ("Acao4", "action_sec3")]
    for a, b in pairs:
        print(f"{a:>10} == {b:<22}: {(norm(m[a]) == norm(m[b])).sum()}/{len(m)}")
    print(f"   Area_ha ratio: min {(m.Area_ha / m.area_ha).min():.4f} max {(m.Area_ha / m.area_ha).max():.4f}")

    # 2) Adjacency to Cerrado/Pantanal hybrid areas (≤ 2 km) ---------------------------
    cpa = cp.to_crs(ALBERS)
    cpa["geometry"] = cpa.simplify(300).buffer(0)
    hba = hb[hb.COD_area.str.contains("CerraPa")].to_crs(ALBERS)
    hba["geometry"] = hba.simplify(300).buffer(0)
    j = gpd.sjoin(cpa[["COD_area", "geometry"]],
                  hba[["COD_area", "geometry"]].rename(columns={"COD_area": "hybrid"}),
                  predicate="dwithin", distance=2000)
    near = j.groupby("COD_area").hybrid.apply(lambda x: ";".join(sorted(set(x))))

    # 3) Assemble the 300-row table ----------------------------------------------------
    t = cp.drop(columns=["geometry", "Shape_Leng", "Shape_Area"]).copy()
    t["has_ficha"] = t.COD_area.isin(fichas.code)
    t["hybrids_within_2km"] = t.COD_area.map(near)
    t["source"] = "MMA layer"
    extra = pd.DataFrame(ANNEX_ONLY, columns=["NOME", "Estados", "Import_bio"])
    extra["has_ficha"] = False
    extra["source"] = "Annex I only (absent from MMA layer; free codes 57,61,81,93,171,286)"
    t = pd.concat([t.sort_values("COD_area"), extra], ignore_index=True)
    t.to_csv(DER / "reconciliation_2nd_update.csv", index=False)

    no_ficha = t[(t.source == "MMA layer") & ~t.has_ficha]
    print(f"rows: {len(t)} | MMA areas without ficha: {len(no_ficha)}, "
          f"of which touching a hybrid: {no_ficha.hybrids_within_2km.notna().sum()}")
    rest = t[(t.source == "MMA layer") & t.has_ficha]
    print(f"areas with ficha touching a hybrid: {rest.hybrids_within_2km.notna().sum()}/{len(rest)}")


if __name__ == "__main__":
    main()
