"""Etapa A.1 — Limpieza y armado del dataset para el modelo de entidades.

Pasos:
  1. Leer DataTurks (220 CVs, el dato principal).
  2. Leer y limpiar el dataset ruidoso de 5029 CVs (sólo refuerzo de HABILIDAD).
  3. Evitar "filtración de datos": sacar del refuerzo cualquier CV que ya esté
     en DataTurks.
  4. Separar DataTurks en entrenamiento / validación / prueba (70/15/15).
  5. Guardar todo en data/processed/ner/ (JSONL + formato spaCy) y un resumen.

Uso:
    .venv/bin/python scripts/build_ner_dataset.py
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spacy
from spacy.tokens import DocBin

from src import config
from src.data_loader.cleaning import normalize_for_dedup, spans_from_entities
from src.data_loader.dataturks import load_dataturks
from src.data_loader.labels import LABELS
from src.data_loader.mehyarmlaweh import load_mehyarmlaweh
from src.data_loader.skills_lexicon import BLACKLIST, build_skill_lexicon
from src.utils.seeds import set_global_seed

TRAIN_RATIO = 0.70
DEV_RATIO = 0.15


def dedup(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for record in records:
        key = normalize_for_dedup(record["text"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def to_docbin(records: list[dict], nlp) -> DocBin:
    doc_bin = DocBin()
    for record in records:
        doc = nlp.make_doc(record["text"])
        doc.ents = spans_from_entities(doc, record["entities"])
        doc_bin.add(doc)
    return doc_bin


def write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def label_counts(records: list[dict]) -> dict[str, int]:
    counter: Counter = Counter()
    for record in records:
        for entity in record["entities"]:
            counter[entity["label"]] += 1
    return dict(counter)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--curated-only",
        action="store_true",
        help="Usar solo el diccionario curado de habilidades (más estricto, menos ruido).",
    )
    parser.add_argument(
        "--max-reinforcement",
        type=int,
        default=2000,
        help="Máximo de CVs de refuerzo a usar (0 = todos).",
    )
    args = parser.parse_args()

    set_global_seed(config.SEED)
    config.NER_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/5] Leyendo DataTurks...")
    dataturks = load_dataturks(config.DATATURKS_PATH)
    print(f"      CVs válidos: {len(dataturks)}")

    print("[2/5] Construyendo diccionario de habilidades...")
    lexicon = build_skill_lexicon(
        config.REFS_DIR, config.JOB_SKILLS_CSV, include_job_skills=not args.curated_only
    )
    print(f"      Habilidades en el diccionario: {len(lexicon)}")

    print("[3/5] Leyendo y limpiando dataset de refuerzo (5029 CVs)...")
    reinforcement = load_mehyarmlaweh(config.MEHYARMLAWEH_DIR, lexicon, BLACKLIST)
    print(f"      CVs de refuerzo tras limpieza: {len(reinforcement)}")

    # Evitar filtración: ningún texto de refuerzo puede estar en DataTurks.
    dataturks_keys = {normalize_for_dedup(r["text"]) for r in dataturks}
    reinforcement = [r for r in reinforcement if normalize_for_dedup(r["text"]) not in dataturks_keys]
    reinforcement = dedup(reinforcement)

    # Limitar el refuerzo para no desbalancear demasiado.
    if args.max_reinforcement and len(reinforcement) > args.max_reinforcement:
        reinforcement = random.Random(config.SEED).sample(reinforcement, args.max_reinforcement)
        print(f"      Refuerzo limitado a: {len(reinforcement)} CVs")

    # Deduplicamos también DataTurks.
    dataturks = dedup(dataturks)

    print("[4/5] Separando entrenamiento / validación / prueba...")
    random.Random(config.SEED).shuffle(dataturks)
    n_total = len(dataturks)
    n_train = int(n_total * TRAIN_RATIO)
    n_dev = int(n_total * DEV_RATIO)

    dev = dataturks[n_train : n_train + n_dev]
    test = dataturks[n_train + n_dev :]
    train = dataturks[:n_train] + reinforcement  # el refuerzo SÓLO en entrenamiento

    print("[5/5] Guardando archivos...")
    write_jsonl(train, config.NER_DIR / "train.jsonl")
    write_jsonl(dev, config.NER_DIR / "dev.jsonl")
    write_jsonl(test, config.NER_DIR / "test.jsonl")

    nlp = spacy.blank("en")
    to_docbin(train, nlp).to_disk(config.NER_DIR / "train.spacy")
    to_docbin(dev, nlp).to_disk(config.NER_DIR / "dev.spacy")
    to_docbin(test, nlp).to_disk(config.NER_DIR / "test.spacy")

    stats = {
        "semilla": config.SEED,
        "config": {
            "curated_only": args.curated_only,
            "max_reinforcement": args.max_reinforcement,
        },
        "dataturks_originales": 220,
        "dataturks_tras_limpieza": n_total,
        "refuerzo_tras_limpieza": len(reinforcement),
        "habilidades_diccionario": len(lexicon),
        "train": {"docs": len(train), "entidades": label_counts(train)},
        "dev": {"docs": len(dev), "entidades": label_counts(dev)},
        "test": {"docs": len(test), "entidades": label_counts(test)},
        "etiquetas": LABELS,
    }
    (config.NER_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== RESUMEN ===")
    print(f"Entrenamiento: {len(train)} CVs  (DataTurks {n_train} + refuerzo {len(reinforcement)})")
    print(f"Validación   : {len(dev)} CVs")
    print(f"Prueba       : {len(test)} CVs")
    print("\nEntidades por etiqueta (entrenamiento):")
    for label, count in sorted(label_counts(train).items(), key=lambda x: -x[1]):
        print(f"  {label:20s} {count}")
    print("\nArchivos en:", config.NER_DIR)


if __name__ == "__main__":
    main()
