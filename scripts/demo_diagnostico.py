"""Demo del motor de diagnóstico: un CV contra una oferta → JSON de 4 dimensiones.

Uso:
    .venv/bin/python scripts/demo_diagnostico.py --motor tfidf
    .venv/bin/python scripts/demo_diagnostico.py --motor embeddings
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
    parser.add_argument("--motor", choices=["tfidf", "embeddings"], default="tfidf")
    parser.add_argument("--par", type=str, default="par_005", help="ID del par a analizar.")
    args = parser.parse_args()

    csv_path = config.BENCHMARKS_DIR / "pares_para_calificar.csv"
    if not csv_path.exists():
        print("No existe la planilla de pares. Corré scripts/build_rating_pairs.py")
        return

    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next((r for r in rows if r["par_id"] == args.par), rows[0])

    from src.core.diagnostico import analizar

    resultado = analizar(row["cv_texto"], row["oferta_texto"], motor_similitud=args.motor)

    print(f"Par     : {row['par_id']}  (oferta: {row['oferta_titulo']})")
    print(f"Motor   : {args.motor}")
    print("\n=== DIAGNÓSTICO ===")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
