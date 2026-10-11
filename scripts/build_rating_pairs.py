"""Etapa B.2 — Arma la planilla de pares (CV + oferta) para calificar a mano.

Genera un CSV con ~50 pares. Los dos integrantes del grupo leen cada par y ponen
en la columna `puntaje_humano` una nota de 0 a 100 ("cuánto encaja este CV con
esta oferta"). Esa nota es la verdad contra la que se mide el sistema (Spearman).

El CSV NO se versiona (está dentro de data/), pero el script sí.

Uso:
    .venv/bin/python scripts/build_rating_pairs.py --n 50
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config


def load_cvs(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_ofertas(path: Path, limit: int = 3000) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        usecols=["job_id", "title", "description"],
        nrows=limit,
        on_bad_lines="skip",
    )
    df = df.dropna(subset=["description", "title"])
    df["largo"] = df["description"].str.len()
    df = df[(df["largo"] >= 300) & (df["largo"] <= 5000)]
    return df.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50, help="Cantidad de pares a generar.")
    args = parser.parse_args()

    rng = random.Random(config.SEED)
    cvs = load_cvs(config.NER_DIR / "test.jsonl")
    ofertas = load_ofertas(config.POSTINGS_CSV)

    if cvs and ofertas.empty:
        print("No se pudieron cargar ofertas con descripción válida.")
        return

    rows = []
    for i in range(args.n):
        cv = rng.choice(cvs)
        oferta = ofertas.iloc[rng.randrange(len(ofertas))]
        rows.append(
            {
                "par_id": f"par_{i + 1:03d}",
                "cv_id": cv["id"],
                "oferta_id": oferta["job_id"],
                "oferta_titulo": str(oferta["title"]).replace("\n", " ").strip(),
                "cv_texto": cv["text"],
                "oferta_texto": str(oferta["description"]),
                "puntaje_humano": "",
                "comentario": "",
            }
        )

    config.BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.BENCHMARKS_DIR / "pares_para_calificar.csv"
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Pares generados: {len(rows)}")
    print(f"Archivo        : {out_path}")
    print("\nSiguiente paso: abran el CSV y completen 'puntaje_humano' (0 a 100).")


if __name__ == "__main__":
    main()
