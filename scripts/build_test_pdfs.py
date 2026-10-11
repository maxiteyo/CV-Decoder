"""Etapa B.1 — Genera PDFs de prueba a partir de CVs reales del dataset.

Como todavía no tenemos PDFs reales de candidatos, fabricamos un conjunto de
control con dos maquetas típicas:
  - "simple"    : una sola columna (lo más fácil de leer).
  - "columnas"  : dos columnas (lo que suele romper la lectura automática).

Guardamos también el texto esperado de cada PDF, para poder medir cuánto texto se
recupera al leerlo (cobertura).

Uso:
    .venv/bin/python scripts/build_test_pdfs.py --n 20
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageDraw

from src import config


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def sanitize(text: str) -> str:
    """Deja solo caracteres que la fuente básica de PDF puede dibujar."""
    return text.encode("latin-1", "replace").decode("latin-1")


def write_simple(path: Path, text: str) -> None:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    for line in text.split("\n"):
        pdf.multi_cell(0, 5, line.rstrip() or " ", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.output(str(path))


def write_columns(path: Path, text: str, n_cols: int = 2) -> None:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    margin, gap = 15, 8
    col_w = (pdf.w - 2 * margin - gap * (n_cols - 1)) / n_cols
    top, bottom = margin, pdf.h - margin
    col_y = [top] * n_cols
    col = 0
    for line in text.split("\n"):
        if col_y[col] > bottom:
            col += 1
            if col >= n_cols:
                pdf.add_page()
                col = 0
                col_y = [top] * n_cols
        x = margin + col * (col_w + gap)
        pdf.set_xy(x, col_y[col])
        pdf.multi_cell(col_w, 4.5, line.rstrip() or " ", new_x=XPos.LEFT, new_y=YPos.NEXT)
        col_y[col] = pdf.get_y()
    pdf.output(str(path))


def write_scanned(path: Path, text: str) -> None:
    """Simula un PDF escaneado: el texto se dibuja como IMAGEN.

    Un PDF así NO tiene capa de texto, igual que una foto de un CV: el lector
    automático no puede sacar nada. Sirve para comprobar que el sistema detecta
    correctamente estos casos problema.
    """
    lines = [line[:110] for line in text.split("\n")][:400]
    line_h = 15
    width = 1000
    height = line_h * len(lines) + 40
    image = Image.new("RGB", (width, max(height, 100)), "white")
    draw = ImageDraw.Draw(image)
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black")
        y += line_h

    image_path = path.with_suffix(".png")
    image.save(image_path)

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.image(str(image_path), x=15, y=15, w=pdf.w - 30)
    pdf.output(str(path))
    image_path.unlink()  # no hace falta conservar la imagen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Cantidad de CVs a convertir.")
    args = parser.parse_args()

    config.PDFS_DIR.mkdir(parents=True, exist_ok=True)
    records = load_records(config.NER_DIR / "test.jsonl")
    random.Random(config.SEED).shuffle(records)
    records = records[: args.n]

    manifest = []
    layouts = (
        ("simple", write_simple, True),
        ("columnas", write_columns, True),
        ("escaneado", write_scanned, False),
    )
    for record in records:
        source_id = record["id"]
        text = sanitize(record["text"])
        for layout, writer, esperado in layouts:
            pdf_path = config.PDFS_DIR / f"{source_id}_{layout}.pdf"
            writer(pdf_path, text)
            manifest.append(
                {
                    "pdf": pdf_path.name,
                    "origen": source_id,
                    "maqueta": layout,
                    "esperado_parseable": esperado,
                    "texto_esperado": record["text"],
                }
            )

    manifest_path = config.PDFS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PDFs generados : {len(manifest)} ({len(records)} CVs x {len(layouts)} maquetas)")
    print(f"Carpeta        : {config.PDFS_DIR}")
    print(f"Manifiesto     : {manifest_path}")


if __name__ == "__main__":
    main()
