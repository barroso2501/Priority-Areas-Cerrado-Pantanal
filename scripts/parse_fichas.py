"""
parse_fichas.py — Extract the MMA area fact sheets ("fichas") of the 2nd update
(Cerrado & Pantanal) into two tidy tables.

Input : data/raw/fichas_cerrado_pantanal_2a_atualizacao_2018-2.pdf  (MMA download)
Output: data/derived/fichas_areas.csv   -> one row per priority area
        data/derived/fichas_targets.csv -> one row per (area, target group, target)

Run from the repository root:   python scripts/parse_fichas.py

What can break, and how you would notice:
  - The script calls `pdftotext -layout` (poppler-utils). If it is missing you get
    FileNotFoundError; install poppler (apt install poppler-utils / conda install poppler).
  - A different pdftotext version may change line layout. Expected counts with the
    2018 PDF are 278 areas and 33,016 area-target pairs; any other number means the
    header patterns ("CÓDIGO:", "ALVOS", group names) stopped matching.
  - A target group not listed in GROUPS would be silently read as targets of the
    previous group: look for all-caps, space-free "targets" in fichas_targets.csv.
"""
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/fichas_cerrado_pantanal_2a_atualizacao_2018-2.pdf"
OUT = ROOT / "data/derived"

# Header label in the PDF -> output column name
FIELDS = {
    "NOME DA ÁREA PRIORITÁRIA": "name",
    "IMPORTÂNCIA BIOLÓGICA": "biological_importance",
    "PRIORIDADE DE AÇÃO": "action_priority",
    "ÁREA TOTAL DO POLÍGONO (HA)": "area_ha",
    "AÇÃO RECOMENDADA (PRINCIPAL)": "action_main",
    "AÇÃO RECOMENDADA (SECUNDÁRIA1)": "action_sec1",
    "AÇÃO RECOMENDADA (SECUNDÁRIA2)": "action_sec2",
    "AÇÃO RECOMENDADA (SECUNDÁRIA3)": "action_sec3",
}
# Closed list of target-group headers observed in the document
GROUPS = {"ANFIBIO", "AVES", "MAMIFEROS", "PEIXES", "PLANTAS", "REPTEIS",
          "SISTEMAS_DE_TERRAS", "ECOSSISTEMA_AQUATICO"}
# Repeated page headers/footers to skip
NOISE = re.compile(r"ÁREAS PRIORITÁRIAS PARA CONSERVAÇÃO|DOS BENEFÍCIOS DA BIODIVERSIDADE|"
                   r"BIOMAS CERRADO E PANTANAL|^\*PARA INFORMAÇÕES|^\f")


def pdf_to_text(pdf: Path) -> str:
    # Keep the physical layout so each field stays on its own line
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout


def parse(text: str):
    areas, targets = [], []
    # Each fact sheet starts with "CÓDIGO: <n>"
    for block in re.split(r"\n\s*CÓDIGO:\s*", text)[1:]:
        lines = [l.strip() for l in block.split("\n")]
        rec = {"code": int(lines[0])}
        group, in_targets = None, False
        for s in lines[1:]:
            if not s or NOISE.search(s):
                continue
            if not in_targets:
                m = re.match(r"([^:]+):\s*(.*)", s)
                if m and m.group(1).strip() in FIELDS:
                    rec[FIELDS[m.group(1).strip()]] = m.group(2).strip() or None
                    continue
                if s == "ALVOS":          # from here on, only target lists
                    in_targets = True
                continue
            if s in GROUPS:               # group header
                group = s
                continue
            targets.append({"code": rec["code"], "group": group, "target": s})
        # Area uses a decimal comma in the PDF (e.g. 565285,4016)
        if rec.get("area_ha"):
            rec["area_ha"] = float(rec["area_ha"].replace(",", "."))
        areas.append(rec)
    return areas, targets


def main():
    areas, targets = parse(pdf_to_text(PDF))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "fichas_areas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["code", *FIELDS.values()])
        w.writeheader()
        w.writerows(areas)
    with open(OUT / "fichas_targets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["code", "group", "target"])
        w.writeheader()
        w.writerows(targets)
    print(f"{len(areas)} areas, {len(targets)} area-target pairs")


if __name__ == "__main__":
    main()
