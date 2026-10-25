"""Demo del motor de diagnóstico: un CV contra una oferta → JSON de 4 dimensiones.

Dos formas de entrar:
  - Con un par de la planilla:   --par par_012
  - Con un PDF real:             --pdf data/benchmarks/pdfs_reales/"cv (10).pdf"

Uso:
    .venv/bin/python scripts/demo_diagnostico.py --motor tfidf --par par_012
    .venv/bin/python scripts/demo_diagnostico.py --pdf "data/benchmarks/pdfs_reales/cv (10).pdf"
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motor", choices=["tfidf", "embeddings", "embeddings_fragmentos"], default="tfidf")
    parser.add_argument("--par", type=str, default="par_012", help="ID del par a analizar.")
    parser.add_argument("--pdf", type=Path, default=None, help="PDF real a analizar (usa la oferta de --par).")
    args = parser.parse_args()

    csv_path = config.BENCHMARKS_DIR / "pares_para_calificar.csv"
    if not csv_path.exists():
        print("No existe la planilla de pares. Corré scripts/build_rating_pairs.py")
        return

    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    oferta = next((r for r in rows if r["par_id"] == args.par), rows[0])

    if args.pdf:
        from src.parsing.pdf_reader import read_pdf

        leido = read_pdf(args.pdf)
        cv_texto = leido["texto"]
        print(f"CV      : {args.pdf}")
        print(f"Páginas : {len(leido['paginas'])} (sin texto: {leido['paginas_sin_texto']})")
        if leido["error"]:
            print(f"ERROR   : {leido['error']}")
        if not cv_texto:
            print("El PDF no tiene texto: es un escaneo o está roto. No se puede diagnosticar sin OCR.")
            return
    else:
        cv_texto = next(r for r in rows if r["par_id"] == args.par)["cv_texto"]
        print(f"Par     : {args.par}")

    from src.core.diagnostico import analizar

    resultado = analizar(cv_texto, oferta["oferta_texto"], motor_similitud=args.motor)

    print(f"Oferta  : {oferta['oferta_titulo']}")
    print(f"Motor   : {args.motor}")
    print("\n=== DIAGNÓSTICO ===")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
