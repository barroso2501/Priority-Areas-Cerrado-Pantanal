"""
product1_factsheets.py — Fact sheets ("fichas") of Product 1 (D13), one HTML page per unit,
in Portuguese for the MMA Biodiversity Directorate.

Every number comes from tables, never typed by hand (findings.md §1: the 2012 fact sheets
were a report generated from the layer). Categories and flags come from
data/derived/product1/calibration_units.csv, the single source of the classification.

Inputs
  data/derived/product1/calibration_units.csv   categories, rates, flags (product1_calibration.py)
  data/derived/product1/calibration_matrix.csv  same metrics for the matrix by biome (context)
  data/interim/extract/lulc_area.parquet        annual area per zone and class
  data/interim/extract/p1_transitions.parquet   direct transitions 2012 -> 2025
  data/interim/extract/p1_persistence.parquet   persistence of natural vegetation
  data/derived/zones_attributes.csv, data/derived/reconciliation_2nd_update.csv,
  data/derived/fichas_targets.csv, data/reference/mapbiomas_col11_legend_groups.csv
  data/raw/areas_hibridas/... (hybrid actions; optional)
Output
  data/derived/product1/fichas/ficha_<unit>.html   one self-contained page per unit
  data/derived/product1/fichas/prototipo.html      the selected units on one page (when --units is given)
  data/derived/product1/fichas/index.html          table of all units with a text filter (--units all)

Run from the repository root:
  python scripts/analysis/product1_factsheets.py                 # prototype units (29 252 244)
  python scripts/analysis/product1_factsheets.py --units all     # all 348 units
  python scripts/analysis/product1_factsheets.py --units 29 75 111

What can break, and how you would notice:
  - A unit code not in calibration_units.csv: KeyError naming the code.
  - A class missing from CLASS_GROUP below falls into "Outros usos" (anthropic) or
    "Outras formações naturais" (natural) by the legend `nature`; a new MapBiomas class
    would therefore not disappear, but may be mislabeled. Check the composition table.
  - Charts are inline SVG: no internet or library needed to open the page.
"""
import argparse
import base64
import html
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data/interim/extract"
P1 = ROOT / "data/derived/product1"
OUT = P1 / "fichas"
OUT.mkdir(parents=True, exist_ok=True)
Y0, YS, Y1 = 2012, 2018, 2025

ap = argparse.ArgumentParser()
ap.add_argument("--units", nargs="+", default=["29", "252", "244"])
args = ap.parse_args()

# --- Labels (Portuguese) ------------------------------------------------------------------
CAT_PT = {"net gain": "Ganho líquido", "stable": "Estável", "turnover": "Rotatividade",
          "moderate loss": "Perda moderada", "intense loss": "Perda intensa",
          "very intense loss": "Perda muito intensa", "no natural vegetation": "Sem vegetação natural"}
CAT_RULE = {"net gain": "tendência > +0,2%/ano, com ganho ≥ 0,5 p.p. da área e ≥ 100 ha",
            "stable": "tendência entre −0,2 e +0,2%/ano e conversão bruta ≤ 0,5%/ano",
            "turnover": "tendência entre −0,2 e +0,2%/ano, mas conversão bruta > 0,5%/ano",
            "moderate loss": "tendência entre −1 e −0,2%/ano",
            "intense loss": "tendência entre −2 e −1%/ano",
            "very intense loss": "tendência abaixo de −2%/ano"}
# Ordinal colour of the category badge (diverging blue <-> red, grey midpoint). The label is
# always printed, so colour never carries the meaning alone.
CAT_COLOR = {"net gain": "#256abf", "stable": "#8a8984", "turnover": "#8a8984",
             "moderate loss": "#ec835a", "intense loss": "#d03b3b", "very intense loss": "#8f1d1d",
             "no natural vegetation": "#8a8984"}
DRIVER_PT = {"pasture": "pastagem", "soybean": "soja", "other crops": "outras lavouras",
             "mosaic of uses": "mosaico de usos", "forest plantation": "silvicultura", "mining": "mineração",
             "urban": "área urbana", "other non-vegetated": "outras áreas não vegetadas",
             "aquaculture": "aquicultura", "energy": "energia (solar/eólica)"}
FLAG_PT = {
    "flag_acceleration": ("Aceleração", "a perda em 2018–2025 foi maior que em 2012–2018 em mais de 0,5 p.p./ano, acima do ruído"),
    "low_confidence": ("Baixa confiança", "a tendência está a menos de um erro-padrão de um limite de categoria"),
    "flag_hydro": ("Dinâmica hidrológica", "trocas entre vegetação natural e água/areia são > 20% das trocas brutas; não contam como perda"),
    "flag_possible_reservoir": ("Possível reservatório", "vegetação de 2012 virou água e ficou água em 2020–2025 (≥ 100 ha e ≥ 0,5%); não confirmado com lista de barragens"),
    "flag_small": ("Área pequena", "menos de 5 mil ha; taxas instáveis"),
    "is_hybrid": ("Área híbrida", "área de harmonização entre biomas; classes pós-harmonização"),
}
STATE_PT = {"<20%": "< 20% de vegetação natural", "20-50%": "20–50% de vegetação natural",
            "50-80%": "50–80% de vegetação natural", ">=80%": "≥ 80% de vegetação natural"}
# Composition groups for the table and the "where did it go" chart
CLASS_GROUP = {3: "Formação florestal", 5: "Formação florestal", 6: "Formação florestal", 49: "Formação florestal",
               4: "Formação savânica", 7: "Savana alagada", 12: "Formação campestre", 11: "Campo alagado",
               29: "Outras formações naturais", 32: "Outras formações naturais", 50: "Outras formações naturais",
               77: "Outras formações naturais", 84: "Outras formações naturais",
               15: "Pastagem", 39: "Soja", 20: "Outras lavouras", 40: "Outras lavouras", 41: "Outras lavouras",
               62: "Outras lavouras", 46: "Outras lavouras", 47: "Outras lavouras", 48: "Outras lavouras",
               35: "Outras lavouras", 21: "Mosaico de usos", 9: "Silvicultura",
               24: "Urbano, mineração e outros", 30: "Urbano, mineração e outros", 25: "Urbano, mineração e outros",
               31: "Urbano, mineração e outros", 75: "Urbano, mineração e outros", 91: "Urbano, mineração e outros",
               33: "Água", 23: "Praia, duna e areal"}
NAT_GROUPS = ["Formação florestal", "Formação savânica", "Savana alagada", "Formação campestre",
              "Campo alagado", "Outras formações naturais"]
USE_GROUPS = ["Pastagem", "Soja", "Outras lavouras", "Mosaico de usos", "Silvicultura", "Urbano, mineração e outros"]
NNV_GROUPS = ["Água", "Praia, duna e areal"]
ACTION_PT = {"recuperacao": "Recuperação", "car - boas praticas": "CAR – boas práticas",
             "fomento ao uso sustentavel": "Fomento ao uso sustentável", "criacao ucpi": "Criação de UC de proteção integral",
             "corredor_mosaico": "Corredor / mosaico", "criacao uc": "Criação de UC", "criacao de uc": "Criação de UC",
             "ordenamento": "Ordenamento territorial", "compensacao": "Compensação",
             "criacao ucus": "Criação de UC de uso sustentável", "inventario": "Inventário"}
MAP_CLASSES = [(1, "Vegetação natural estável", "#1f6f3a"), (2, "Perda de vegetação natural", "#eb6834"),
               (3, "Ganho de vegetação natural", "#4a3aa7"), (4, "Uso antrópico estável", "#d8d2c4"),
               (5, "Água ou areia estável", "#2a78d6"), (6, "Trocas com água ou areia", "#56b4e9")]
MAPS = ROOT / "data/interim/maps"   # PNGs from scripts/gee/31_export_maps.py (not versioned)
TARGET_PT = {"PLANTAS": "Plantas", "MAMIFEROS": "Mamíferos", "REPTEIS": "Répteis", "AVES": "Aves",
             "ANFIBIO": "Anfíbios", "PEIXES": "Peixes", "SISTEMAS_DE_TERRAS": "Sistemas de terras",
             "ECOSSISTEMA_AQUATICO": "Ecossistemas aquáticos"}


def fnum(v, d=0):
    """Brazilian number format: 1.234,5"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fsig(v, d=2):
    s = fnum(v, d)
    return ("+" + s) if v is not None and not np.isnan(v) and v > 0 else s.replace("-", "−")


esc = html.escape

# --- Data ------------------------------------------------------------------------------------
lg = pd.read_csv(ROOT / "data/reference/mapbiomas_col11_legend_groups.csv")
NAT = set(lg.loc[lg.level1_code.isin([1, 2]), "pixel_id"].astype(int))
NATURE = dict(zip(lg.pixel_id.astype(int), lg.nature))


def group_of(c):
    if c in CLASS_GROUP:
        return CLASS_GROUP[c]
    return "Outras formações naturais" if c in NAT else ("Água" if NATURE.get(c) == "natural" else "Urbano, mineração e outros")


units = pd.read_csv(P1 / "calibration_units.csv", dtype={"unit": str}).set_index("unit")
z = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
z["unit"] = np.where(z.ap2012_code != "none", z.ap2012_code.str.replace(".0", "", regex=False),
                     np.where(z.hybrid_code != "none", z.hybrid_code, "OUTSIDE|" + z.biome_2019.astype(str)))
zu = z[["zone_id", "unit"]]
a = pd.read_parquet(EXT / "lulc_area.parquet").query("year >= @Y0 and year <= @Y1").merge(zu, on="zone_id")
a["grp"] = a["class"].map(group_of)
comp = a.groupby(["unit", "year", "grp"]).ha.sum()
nat_year = a[a["class"].isin(NAT)].groupby(["unit", "year"]).ha.sum()
ANT = set(lg.loc[lg.nature.isin(["anthropic", "ambiguous"]), "pixel_id"].astype(int))
nonant_year = a[~a["class"].isin(ANT)].groupby(["unit", "year"]).ha.sum()   # X(t) of D13
dt = pd.read_parquet(EXT / "p1_transitions.parquet").query("start == @Y0 and end == @Y1").merge(zu, on="zone_id")
dt["g0"], dt["g1"] = dt.class_start.map(group_of), dt.class_end.map(group_of)
# Map class of each direct transition (same rule as 31_export_maps.py)
_ant = set(lg.loc[lg.nature.isin(["anthropic", "ambiguous"]), "pixel_id"].astype(int)); _nnv = {23, 33}
_n0, _n1 = dt.class_start.isin(NAT), dt.class_end.isin(NAT)
_a0, _a1 = dt.class_start.isin(_ant), dt.class_end.isin(_ant)
_w0, _w1 = dt.class_start.isin(_nnv), dt.class_end.isin(_nnv)
dt["mapcls"] = np.select([_n0 & _n1, _n0 & _a1, _a0 & _n1, _a0 & _a1, _w0 & _w1], [1, 2, 3, 4, 5], 6)
pers = pd.read_parquet(EXT / "p1_persistence.parquet").merge(zu, on="zone_id").groupby(["window", "unit"])[
    ["nat_start_ha", "strict_ha", "never_anthropic_ha", "water_persistent_ha"]].sum()
biome = z.groupby(["unit", "biome_2019"]).area_ha.sum()
rec = pd.read_csv(ROOT / "data/derived/reconciliation_2nd_update.csv")
rec["unit"] = rec.COD_area.astype("Int64").astype(str)
rec = rec.set_index("unit")
targets = pd.read_csv(ROOT / "data/derived/fichas_targets.csv", dtype={"code": str})
try:
    import geopandas as gpd
    hy = gpd.read_file(ROOT / "data/raw/areas_hibridas/Areas_hibridas_2a_atualizacao.shp", ignore_geometry=True)
    hy_act = hy.drop_duplicates("COD_area").set_index("COD_area")["AçãoP_p"]
except Exception:
    hy_act = pd.Series(dtype=str)


# --- SVG charts (inline, theme-aware through CSS variables) -----------------------------------
def svg_index_chart(u, ctx, show_nat):
    """Non-anthropic area (natural vegetation + water and sand) indexed to 2012 = 100: the
    basis of the category (D13 §5). The matrix outside the priority areas in the dominant
    biome is drawn as context. When the hydrological flag is on, the natural vegetation of
    the area is added, so the reader sees the flood signal that the category ignores."""
    W, H, l, r, t, b = 880, 260, 44, 190, 16, 30
    series = []
    if show_nat:
        sn = nat_year.loc[u]; series.append((sn / sn.loc[Y0] * 100, "nat", "Vegetação natural (área)"))
    s2 = nonant_year.loc[ctx]; series.append((s2 / s2.loc[Y0] * 100, "ctx", "Matriz do bioma"))
    s1 = nonant_year.loc[u]; series.append((s1 / s1.loc[Y0] * 100, "main", "Esta área"))
    lo = min(s.min() for s, _, _ in series); hi = max(max(s.max() for s, _, _ in series), 100)
    pad = max((hi - lo) * 0.1, 0.5); lo, hi = lo - pad, hi + pad
    X = lambda y: l + (y - Y0) / (Y1 - Y0) * (W - l - r)
    Y = lambda v: t + (hi - v) / (hi - lo) * (H - t - b)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Área não convertida, índice 2012 = 100" class="chart">']
    for v in np.linspace(lo, hi, 5):
        g.append(f'<line x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{l - 6}" y="{Y(v) + 4:.1f}" class="tick" text-anchor="end">{fnum(v, 0)}</text>')
    for y in (2012, 2015, 2018, 2021, 2025):
        g.append(f'<text x="{X(y):.1f}" y="{H - 8}" class="tick" text-anchor="middle">{y}</text>')
    g.append(f'<line x1="{X(YS):.1f}" x2="{X(YS):.1f}" y1="{t}" y2="{H - b}" class="split"/>'
             f'<text x="{X(YS) + 4:.1f}" y="{t + 10}" class="tick">2018</text>')
    # direct labels at the right end, nudged apart so they never overlap
    ends = sorted(((Y(s.iloc[-1]), cls, lab, s.iloc[-1]) for s, cls, lab in series))
    placed = []
    for yy, cls, lab, v in ends:
        if placed and yy - placed[-1] < 15:
            yy = placed[-1] + 15
        placed.append(yy)
        g.append(f'<text x="{X(Y1) + 8:.1f}" y="{yy + 4:.1f}" class="dlabel {cls}">{lab} {fnum(v, 1)}</text>')
    for s, cls, lab in series:
        pts = " ".join(f"{X(y):.1f},{Y(v):.1f}" for y, v in s.items())
        g.append(f'<polyline points="{pts}" class="line {cls}"/>')
        for y, v in s.items():  # hover targets larger than the mark
            g.append(f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="7" class="hit"><title>{lab}, {y}: {fnum(v, 1)}</title></circle>')
    g.append("</svg>")
    return "".join(g)


def svg_hbars(items, unit_label="ha"):
    """Horizontal bars, one hue; value printed at the end of each bar. Values < 1 ha dropped."""
    items = [(k, v) for k, v in items if v >= 1]
    if not items:
        return '<p class="muted">Sem conversão registrada.</p>'
    W, rowh, l, r = 430, 24, 165, 80
    H = rowh * len(items) + 6
    mx = max(v for _, v in items)
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for i, (k, v) in enumerate(items):
        y = 3 + i * rowh
        w = max((W - l - r) * v / mx, 2)
        g.append(f'<text x="{l - 8}" y="{y + 16}" class="tick" text-anchor="end">{esc(k)}</text>'
                 f'<rect x="{l}" y="{y + 4}" width="{w:.1f}" height="16" rx="3" class="bar"><title>{esc(k)}: {fnum(v)} {unit_label}</title></rect>'
                 f'<text x="{l + w + 6:.1f}" y="{y + 16}" class="val">{fnum(v)} {unit_label}</text>')
    g.append("</svg>")
    return "".join(g)


def map_section(u):
    """Change map 2012 -> 2025 with a legend whose hectares come from the tables."""
    ha = dt[dt.unit == u].groupby("mapcls").ha.sum()
    tot = ha.sum()
    leg = "".join(f'<li><span class="sw" style="background:{col}"></span>{lab}<span class="lv">{fnum(ha.get(k, 0))} ha · {fnum(ha.get(k, 0) / tot * 100, 1)}%</span></li>'
                  for k, lab, col in MAP_CLASSES if ha.get(k, 0) >= 1)
    png = MAPS / f"{u}.png"
    img = (f'<img class="map" alt="Mapa de mudanças 2012–2025 da área {esc(u)}" src="data:image/png;base64,{base64.b64encode(png.read_bytes()).decode()}">'
           if png.exists() else '<div class="map placeholder">Mapa ainda não gerado (scripts/gee/31_export_maps.py).</div>')
    return f'''<section>
  <h3>Mapa de mudanças 2012–2025</h3>
  <p class="muted">Comparação dos grupos de nível 1 do MapBiomas em 2012 e 2025. A área está em cores plenas e contornada; o entorno aparece esmaecido, como contexto. O mapa é ilustrativo; as áreas da legenda vêm das tabelas.</p>
  <div class="mapwrap">{img}<ul class="legend">{leg}</ul></div>
</section>'''


# --- One fact sheet ------------------------------------------------------------------------------
def ficha(u):
    m = units.loc[u]
    hyb = bool(m.is_hybrid)
    name = "Área híbrida" if hyb else str(m.NOME)
    bio = biome.loc[u]; bio_share = bio / bio.sum()
    dom_biome = bio_share.idxmax()
    ctx = f"OUTSIDE|{dom_biome}"
    acts = ([rec.loc[u, c] for c in ("Acao1", "Acao2", "Acao3", "Acao4") if u in rec.index and pd.notna(rec.loc[u, c])]
            if not hyb else [x.strip() for x in str(hy_act.get(u, "")).split(";") if x.strip()])
    acts = [ACTION_PT.get(str(x).strip().lower(), str(x)) for x in acts]
    cat = m.category
    flags = [(lab, why) for f, (lab, why) in FLAG_PT.items() if f in m and bool(m[f])]

    # Composition 2012 / 2025
    c = comp.loc[u].unstack("grp").fillna(0)
    land12 = c.loc[Y0].drop(labels=[g for g in ["Água"] if g in c.columns]).sum()
    land25 = c.loc[Y1].drop(labels=[g for g in ["Água"] if g in c.columns]).sum()
    rows = []
    for block, groups in (("Vegetação natural", NAT_GROUPS), ("Uso antrópico", USE_GROUPS), ("Natural não vegetado", NNV_GROUPS)):
        gs = [g_ for g_ in groups if g_ in c.columns and (c.loc[Y0, g_] > 0 or c.loc[Y1, g_] > 0)]
        tot0 = sum(c.loc[Y0, g_] for g_ in gs); tot1 = sum(c.loc[Y1, g_] for g_ in gs)
        if not gs:
            continue
        rows.append(f'<tr class="sub"><th>{block}</th><td>{fnum(tot0)}</td><td>{fnum(tot1)}</td><td>{fsig(tot1 - tot0, 0)}</td></tr>')
        for g_ in gs:
            v0, v1 = c.loc[Y0, g_], c.loc[Y1, g_]
            rows.append(f'<tr><td class="ind">{g_}</td><td>{fnum(v0)}</td><td>{fnum(v1)}</td><td>{fsig(v1 - v0, 0)}</td></tr>')

    # Where the 2012 natural vegetation went, and where the 2025 natural vegetation came from
    d = dt[dt.unit == u]
    lost = d[d.class_start.isin(NAT) & d.g1.isin(USE_GROUPS)].groupby("g1").ha.sum().sort_values(ascending=False)
    gained = d[~d.class_start.isin(NAT) & d.g0.isin(USE_GROUPS) & d.class_end.isin(NAT)].groupby("g0").ha.sum().sort_values(ascending=False)
    to_nnv = d[d.class_start.isin(NAT) & d.g1.isin(NNV_GROUPS)].ha.sum()
    from_nnv = d[d.g0.isin(NNV_GROUPS) & d.class_end.isin(NAT)].ha.sum()

    p12 = pers.loc[("p2012_2025", u)]; p85 = pers.loc[("p1985_2025", u)]
    n12, n25 = m.nat_ha_2012, m.nat_ha_2025

    tg = targets[targets.code == u]
    tg_rows = "".join(f"<tr><td>{TARGET_PT.get(k, k)}</td><td>{v}</td></tr>" for k, v in tg.group.value_counts().items())
    tg_list = "".join(f"<li><b>{TARGET_PT.get(k, k)}:</b> {esc(', '.join(sorted(s.str.capitalize())))}</li>"
                      for k, s in tg.groupby("group").target)

    ctxm = units_ctx.loc[ctx]
    out = f'''
<article class="ficha" id="u{esc(u)}">
<header>
  <p class="eyebrow">Áreas Prioritárias do Cerrado e Pantanal · 2ª atualização · Ficha de estado e dinâmica 2012–2025</p>
  <h2>{esc(name)} <span class="code">código {esc(u)}</span></h2>
  <dl class="ident">
    <div><dt>UF</dt><dd>{esc(str(m.Estados))}</dd></div>
    <div><dt>Área</dt><dd>{fnum(bio.sum())} ha</dd></div>
    <div><dt>Bioma (IBGE 2019)</dt><dd>{"; ".join(f"{esc(k)} {fnum(v * 100, 0)}%" for k, v in bio_share.sort_values(ascending=False).items() if v >= 0.01)}</dd></div>
    <div><dt>Importância biológica</dt><dd>{esc(str(m.Import_bio))}</dd></div>
    <div><dt>Prioridade de ação</dt><dd>{esc(str(m.Prior_acao))}</dd></div>
    <div><dt>Ações</dt><dd>{esc("; ".join(map(str, acts))) or "–"}</dd></div>
  </dl>
</header>

<section class="verdict">
  <div class="kpi">
    <span class="kpi-label">Estado em 2025</span>
    <span class="kpi-value">{fnum(m.nat_share_2025 * 100, 0)}%</span>
    <span class="kpi-note">{STATE_PT.get(m.state_class_2025, "–")} · {fnum(n25)} ha</span>
  </div>
  <div class="kpi">
    <span class="kpi-label">Dinâmica 2012–2025</span>
    <span class="badge" style="--c:{CAT_COLOR[cat]}">{CAT_PT[cat]}</span>
    <span class="kpi-note">{fsig(m.rate)} ± {fnum(m.se_rate, 2)}%/ano · {CAT_RULE.get(cat, "")}</span>
  </div>
  <div class="kpi">
    <span class="kpi-label">Principal vetor de conversão</span>
    <span class="kpi-value small">{esc(DRIVER_PT.get(m.driver, str(m.driver)))}</span>
    <span class="kpi-note">{fnum(m.driver_share * 100, 0)}% da vegetação convertida entre 2012 e 2025</span>
  </div>
</section>
{('<ul class="flags">' + "".join(f'<li><b>{esc(lab)}</b> — {esc(why)}</li>' for lab, why in flags) + '</ul>') if flags else '<p class="muted">Nenhum alerta.</p>'}

{map_section(u)}

<section>
  <h3>Trajetória da área não convertida</h3>
  <p class="muted">Vegetação natural mais água e areia, índice 2012 = 100: é a base da categoria. A linha tracejada é a matriz fora das áreas prioritárias no bioma {esc(dom_biome)}, como <b>contexto</b>; não é uma avaliação de efeito.{" A linha pontilhada mostra só a vegetação natural da área: a oscilação vem das cheias, que não contam como perda." if bool(m.flag_hydro) else ""}</p>
  {svg_index_chart(u, ctx, bool(m.flag_hydro))}
  <table class="num">
    <thead><tr><th></th><th>2012–2025</th><th>2012–2018</th><th>2018–2025</th><th>Matriz do bioma 2012–2025</th></tr></thead>
    <tbody>
      <tr><td>Tendência líquida (%/ano da vegetação de 2012)</td><td>{fsig(m.rate)}</td><td>{fsig(m.rate_2012_2018)}</td><td>{fsig(m.rate_2018_2025)}</td><td>{fsig(ctxm.rate)}</td></tr>
      <tr><td>Conversão bruta (%/ano)</td><td>{fnum(m.gross_conv, 2)}</td><td></td><td></td><td>{fnum(ctxm.gross_conv, 2)}</td></tr>
      <tr><td>Regeneração bruta (%/ano)</td><td>{fnum(m.gross_regrow, 2)}</td><td></td><td></td><td>{fnum(ctxm.gross_regrow, 2)}</td></tr>
    </tbody>
  </table>
</section>

<section>
  <h3>Composição da paisagem (ha)</h3>
  <table class="num">
    <thead><tr><th></th><th>2012</th><th>2025</th><th>Variação</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <p class="muted">Vegetação natural: {fnum(n12 / land12 * 100, 1)}% da área terrestre em 2012 e {fnum(n25 / land25 * 100, 1)}% em 2025.</p>
</section>

<section class="two">
  <div>
    <h3>Para onde foi a vegetação natural de 2012</h3>
    <p class="muted">Vegetação natural em 2012 que era uso antrópico em 2025 (transição direta).</p>
    {svg_hbars(list(lost.items()))}
  </div>
  <div>
    <h3>De onde veio a regeneração</h3>
    <p class="muted">Uso antrópico em 2012 que era vegetação natural em 2025.</p>
    {svg_hbars(list(gained.items()))}
  </div>
</section>
{f'<p class="muted">Dinâmica hidrológica (fora da contabilidade): {fnum(to_nnv)} ha de vegetação natural de 2012 eram água ou areia em 2025, e {fnum(from_nnv)} ha fizeram o caminho inverso. Vegetação que virou água e ficou água em 2020–2025 (possível reservatório): {fnum(p12.water_persistent_ha)} ha.</p>' if (to_nnv + from_nnv) >= 1 else ""}

<section>
  <h3>Persistência</h3>
  <table class="num">
    <tbody>
      <tr><td>Vegetação natural de 2012 nunca convertida em uso até 2025</td><td>{fnum(p12.never_anthropic_ha)} ha</td><td>{fnum(p12.never_anthropic_ha / p12.nat_start_ha * 100, 1)}%</td></tr>
      <tr><td>Vegetação natural de 1985 nunca convertida em uso até 2025</td><td>{fnum(p85.never_anthropic_ha)} ha</td><td>{fnum(p85.never_anthropic_ha / p85.nat_start_ha * 100, 1)}%</td></tr>
      <tr><td>Parcela da vegetação natural de 2025 nunca convertida desde 1985</td><td></td><td>{fnum(min(p85.never_anthropic_ha / n25, 1) * 100, 1)}%</td></tr>
    </tbody>
  </table>
  <p class="muted">A diferença entre a vegetação de 2025 e a vegetação nunca convertida é vegetação secundária ou regenerada, que conta como natural no MapBiomas.{" <b>Nesta área há dinâmica hidrológica:</b> parte da diferença é vegetação que estava alagada em 1985 (água), não vegetação secundária; a terceira linha subestima a vegetação antiga." if bool(m.flag_hydro) else ""}</p>
</section>

<section>
  <h3>Alvos de conservação da área (2ª atualização, listas de 2011–2012)</h3>
  {('<table class="num"><thead><tr><th>Grupo</th><th>Alvos</th></tr></thead><tbody>' + tg_rows + '</tbody></table><details><summary>Lista de alvos</summary><ul class="targets">' + tg_list + '</ul></details>') if len(tg) else '<p class="muted">Sem ficha de alvos (área sem ficha original ou área híbrida).</p>'}
  <p class="muted">As listas são históricas e não representam a lista vigente de espécies ameaçadas.</p>
</section>

<footer>
  <p>Fonte: MapBiomas Coleção 11 (1985–2025); Áreas Prioritárias MMA (Portarias 223/2016 e 463/2018). Método: decisão D13 do projeto. Tendência robusta (Theil–Sen) da área não antrópica, em % ao ano da vegetação natural de 2012; perda e ganho contam só trocas com uso antrópico. Protótipo gerado em {date.today():%d/%m/%Y}; números sujeitos a revisão.</p>
</footer>
</article>'''
    return out


units_ctx = pd.read_csv(P1 / "calibration_matrix.csv").set_index("unit")   # matrix by biome (context)

CSS = '''
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6b6a66;--rule:#e4e2dc;--grid:#ecebe7;
--main:#2a78d6;--ctx:#8a8984;--bar:#2a78d6;--card:#f4f3ef;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--muted:#a3a29a;--rule:#383835;--grid:#2a2a28;--main:#3987e5;--ctx:#8f8e86;--bar:#3987e5;--card:#242422;color-scheme:dark}}
:root[data-theme="dark"]{--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#a3a29a;--rule:#383835;--grid:#2a2a28;
--main:#3987e5;--ctx:#8f8e86;--bar:#3987e5;--card:#242422;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}
.ficha{border-top:3px solid var(--ink);padding-top:16px;margin-bottom:72px}
.eyebrow{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:0}
h2{font-size:26px;margin:4px 0 12px}h2 .code{font-size:14px;font-weight:400;color:var(--muted)}
h3{font-size:16px;margin:28px 0 4px}
.ident{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px 24px;margin:0}
.ident dt{font-size:12px;color:var(--muted)}.ident dd{margin:0}
.verdict{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:20px 0 8px}
.kpi{background:var(--card);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.kpi-label{font-size:12px;color:var(--muted)}.kpi-value{font-size:30px;font-weight:600;line-height:1.1}
.kpi-value.small{font-size:20px}.kpi-note{font-size:13px;color:var(--ink2)}
.badge{align-self:flex-start;font-weight:600;font-size:17px;padding:3px 10px;border-radius:6px;border-left:6px solid var(--c);background:var(--surface)}
.flags{margin:8px 0;padding-left:18px;color:var(--ink2);font-size:14px}
.muted{color:var(--muted);font-size:13px;margin:2px 0 8px}
table.num{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
table.num th,table.num td{padding:4px 8px;border-bottom:1px solid var(--rule);text-align:right}
table.num th:first-child,table.num td:first-child{text-align:left}
table.num thead th{font-weight:600;color:var(--ink2);font-size:12px}
tr.sub th,tr.sub td{font-weight:600;background:var(--card)}td.ind{padding-left:20px!important}
.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--grid);stroke-width:1}.chart .split{stroke:var(--muted);stroke-dasharray:3 3}
.chart .tick{fill:var(--muted);font-size:11px}.chart .val{fill:var(--ink2);font-size:12px}
.chart .line{fill:none;stroke-width:2;stroke-linejoin:round}.chart .line.main{stroke:var(--main)}
.chart .line.ctx{stroke:var(--ctx);stroke-dasharray:6 4}.chart .line.nat{stroke:var(--main);stroke-width:1.5;stroke-dasharray:1.5 3;opacity:.8}
.chart .dlabel{font-size:12px;fill:var(--ink2)}.chart .hit{fill:transparent}.chart .hit:hover{fill:var(--main);fill-opacity:.25}
.chart .bar{fill:var(--bar)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}
details{margin:8px 0;font-size:13px}.targets{color:var(--ink2);padding-left:18px}
footer{border-top:1px solid var(--rule);margin-top:28px;font-size:12px;color:var(--muted)}
.mapwrap{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:16px;align-items:start}
@media (max-width:700px){.mapwrap{grid-template-columns:1fr}}
.map{display:block;max-width:100%;max-height:560px;width:auto;height:auto;margin:0 auto;border:1px solid var(--rule);border-radius:6px;background:#fff}
.map.placeholder{padding:48px 16px;text-align:center;color:var(--muted);font-size:13px;background:var(--card)}
.legend{list-style:none;margin:0;padding:0;font-size:13px}.legend li{display:grid;grid-template-columns:14px 1fr;column-gap:8px;margin-bottom:8px}
.legend .sw{width:14px;height:14px;border-radius:3px;margin-top:3px;grid-row:span 2}.legend .lv{color:var(--muted);grid-column:2}
table.idx td,table.idx th{text-align:left!important}table.idx td:nth-child(6),table.idx td:nth-child(8){text-align:right!important}
nav.toc{font-size:14px;margin-bottom:24px}nav.toc a{color:var(--main);margin-right:16px}
'''


def page(title, body):
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f'<style>{CSS}</style></head><body><main>{body}</main></body></html>')


sel = units.index.tolist() if args.units == ["all"] else args.units
parts = []
for u in sel:
    f = ficha(u)
    (OUT / f"ficha_{u.replace('|', '_')}.html").write_text(page(f"Ficha {u}", f), encoding="utf-8")
    parts.append((u, f))
if args.units != ["all"]:
    toc = '<nav class="toc">' + "".join(f'<a href="#u{esc(u)}">{esc(u)} · {esc(str(units.loc[u].NOME) if not units.loc[u].is_hybrid else "híbrida")}</a>' for u, _ in parts) + "</nav>"
    (OUT / "prototipo.html").write_text(page("Fichas — protótipo", "<h1>Fichas de estado e dinâmica — protótipo</h1>" + toc + "".join(f for _, f in parts)), encoding="utf-8")
else:
    # Index of all fact sheets: one row per unit, with a text filter (first step towards the
    # online query tool; D13 §2 item 4). Keys and filters come from calibration_units.csv.
    rows = []
    sel = sorted(sel, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, x))   # 1, 2, ... then hybrids
    for u in sel:
        m = units.loc[u]
        name = "Área híbrida" if m.is_hybrid else str(m.NOME)
        flags_ = ", ".join(lab for f, (lab, _) in FLAG_PT.items() if f in m and bool(m[f]))
        rows.append(f'<tr><td><a href="ficha_{esc(u)}.html">{esc(u)}</a></td><td>{esc(name)}</td><td>{esc(str(m.Estados))}</td>'
                    f'<td>{esc(str(m.Import_bio))}</td><td>{esc(str(m.Prior_acao))}</td><td>{fnum(m.nat_share_2025 * 100, 0)}%</td>'
                    f'<td>{CAT_PT[m.category]}</td><td>{fsig(m.rate)}</td><td>{esc(flags_)}</td></tr>')
    body = ('<h1>Áreas Prioritárias do Cerrado e Pantanal — estado e dinâmica 2012–2025</h1>'
            f'<p class="muted">{len(sel)} fichas. Digite para filtrar (nome, UF, categoria, importância, alerta…).</p>'
            '<input id="q" type="search" placeholder="Filtrar" style="width:100%;padding:8px;margin:8px 0 12px;font:inherit">'
            '<table class="num idx" id="t"><thead><tr><th>Código</th><th>Nome</th><th>UF</th><th>Importância</th><th>Prioridade</th>'
            '<th>Vegetação natural 2025</th><th>Dinâmica</th><th>%/ano</th><th>Alertas</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
            '<script>const q=document.getElementById("q"),rs=[...document.querySelectorAll("#t tbody tr")];'
            'q.addEventListener("input",()=>{const v=q.value.toLowerCase();rs.forEach(r=>r.style.display=r.textContent.toLowerCase().includes(v)?"":"none")});</script>')
    (OUT / "index.html").write_text(page("Fichas — índice", body), encoding="utf-8")
print("written", len(parts), "fact sheets to", OUT)
