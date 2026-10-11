"""Etapa A.3 — Entrenamiento y evaluación del modelo de entidades (NER).

Entrena un modelo de spaCy en CPU, guarda el mejor modelo (según la validación)
y finalmente lo mide sobre el conjunto de prueba. Reporta precisión, recall y
F1 (micro) y F1 por clase.

Dos modos de arranque:
  --base blank : modelo vacío (aprende todo desde cero).
  --base sm    : parte de "en_core_web_sm" (transferencia de aprendizaje).

Uso:
    .venv/bin/python scripts/train_ner.py --sources dataturks --base sm --epochs 25
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spacy
from spacy.training import Example
from spacy.util import minibatch

from src import config
from src.data_loader.cleaning import apply_schema, spans_from_entities
from src.data_loader.labels import labels_for_schema
from src.utils.seeds import set_global_seed

# Componentes que NO necesitamos para detectar entidades (los sacamos para ir más rápido).
UNUSED_PIPES = ["tagger", "parser", "attribute_ruler", "lemmatizer", "senter", "textcat"]


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_nlp(base: str, labels: list[str]):
    if base == "sm":
        nlp = spacy.load("en_core_web_sm")
        for pipe in UNUSED_PIPES + ["ner"]:
            if pipe in nlp.pipe_names:
                nlp.remove_pipe(pipe)
        ner = nlp.add_pipe("ner")
    else:
        nlp = spacy.blank("en")
        ner = nlp.add_pipe("ner")
    for label in labels:
        ner.add_label(label)
    return nlp


def make_annotated_docs(nlp, records: list[dict], max_chars: int | None = None) -> list:
    docs = []
    for record in records:
        text = record["text"]
        entities = record["entities"]
        if max_chars and len(text) > max_chars:
            text = text[:max_chars]
            entities = [e for e in entities if e["end"] <= max_chars]
        doc = nlp.make_doc(text)
        doc.ents = spans_from_entities(doc, entities)
        docs.append(doc)
    return docs


def make_examples(nlp, docs: list) -> list[Example]:
    return [Example(nlp.make_doc(doc.text), doc) for doc in docs]


def clean_scores(scores: dict) -> dict:
    """Convierte números de numpy a float nativo para poder guardarlos en JSON."""
    per_type = {
        label: {"p": float(s["p"]), "r": float(s["r"]), "f": float(s["f"])}
        for label, s in scores.get("ents_per_type", {}).items()
    }
    return {
        "precision": float(scores.get("ents_p", 0.0)),
        "recall": float(scores.get("ents_r", 0.0)),
        "f1": float(scores.get("ents_f", 0.0)),
        "f1_por_etiqueta": per_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.30)
    parser.add_argument("--base", choices=["blank", "sm"], default="sm")
    parser.add_argument(
        "--schema",
        choices=["fine", "coarse"],
        default="coarse",
        help="fine = 10 etiquetas detalladas; coarse = 6 categorías agrupadas.",
    )
    parser.add_argument(
        "--reinforcement",
        type=int,
        default=-1,
        help="Cuántos CVs de refuerzo usar (-1 = todos los que haya en train.jsonl).",
    )
    parser.add_argument("--max-chars", type=int, default=20_000)
    parser.add_argument(
        "--sources",
        type=str,
        default="",
        help="Filtrar por origen de datos, separado por comas (ej: dataturks). Vacío = todos.",
    )
    parser.add_argument("--output", type=str, default="ner_cv", help="Nombre de la carpeta del modelo.")
    args = parser.parse_args()

    set_global_seed(config.SEED)

    train_records = load_records(config.NER_DIR / "train.jsonl")
    dev_records = load_records(config.NER_DIR / "dev.jsonl")
    test_records = load_records(config.NER_DIR / "test.jsonl")

    if args.sources:
        allowed = {s.strip() for s in args.sources.split(",") if s.strip()}
        train_records = [r for r in train_records if r["source"] in allowed]
        dev_records = [r for r in dev_records if r["source"] in allowed]
        test_records = [r for r in test_records if r["source"] in allowed]

    # Limitar cuántos CVs de refuerzo entran al entrenamiento.
    if args.reinforcement >= 0:
        main_data = [r for r in train_records if r["source"] == "dataturks"]
        extra = [r for r in train_records if r["source"] != "dataturks"]
        if len(extra) > args.reinforcement:
            extra = random.Random(config.SEED).sample(extra, args.reinforcement)
        train_records = main_data + extra

    # Aplicar el esquema de etiquetas (fino o grueso).
    labels = labels_for_schema(args.schema)
    for records in (train_records, dev_records, test_records):
        for record in records:
            record["entities"] = apply_schema(record["entities"], args.schema)

    from collections import Counter

    entity_counts = Counter(e["label"] for r in train_records for e in r["entities"])
    print(
        f"Datos: train={len(train_records)}  dev={len(dev_records)}  test={len(test_records)}  "
        f"base={args.base}  esquema={args.schema}  max_chars={args.max_chars}"
    )
    print(f"Entidades (train): {dict(entity_counts)}")

    nlp = build_nlp(args.base, labels)
    train_docs = make_annotated_docs(nlp, train_records, args.max_chars)
    dev_docs = make_annotated_docs(nlp, dev_records, args.max_chars)
    test_docs = make_annotated_docs(nlp, test_records, args.max_chars)

    train_examples = make_examples(nlp, train_docs)
    dev_examples = make_examples(nlp, dev_docs)

    optimizer = nlp.initialize(lambda: train_examples)

    output_dir = config.MODELS_DIR / args.output
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)

    best_f1 = 0.0
    history = []
    for epoch in range(1, args.epochs + 1):
        random.Random(config.SEED + epoch).shuffle(train_examples)
        losses = {}
        for batch in minibatch(train_examples, size=args.batch_size):
            nlp.update(batch, drop=args.dropout, sgd=optimizer, losses=losses)

        dev_scores = nlp.evaluate(dev_examples)
        f1 = float(dev_scores.get("ents_f", 0.0))
        history.append({"epoch": epoch, "loss_ner": float(losses.get("ner", 0.0)), "dev_f1": f1})
        print(f"Época {epoch:2d}  pérdida={losses.get('ner', 0.0):.2f}  F1(val)={f1:.4f}")

        if f1 >= best_f1:
            best_f1 = f1
            nlp.to_disk(output_dir)

    print(f"\nMejor F1 en validación: {best_f1:.4f}")
    print("Evaluando el mejor modelo sobre el conjunto de PRUEBA...")

    best_nlp = spacy.load(output_dir)
    test_examples = make_examples(best_nlp, test_docs)
    test_scores = best_nlp.evaluate(test_examples)

    report = {
        "config": {
            "semilla": config.SEED,
            "base": args.base,
            "esquema": args.schema,
            "epocas": args.epochs,
            "batch_size": args.batch_size,
            "dropout": args.dropout,
            "max_chars": args.max_chars,
            "fuentes": args.sources or "todas",
            "refuerzo": args.reinforcement,
        },
        "mejor_f1_validacion": float(best_f1),
        "test": clean_scores(test_scores),
        "historial": history,
    }
    report_path = config.MODELS_DIR / f"{args.output}_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== RESULTADO EN PRUEBA ===")
    print(f"Precisión : {report['test']['precision']:.4f}")
    print(f"Recall    : {report['test']['recall']:.4f}")
    print(f"F1 (micro): {report['test']['f1']:.4f}")
    print("\nF1 por etiqueta:")
    for label, s in sorted(report["test"]["f1_por_etiqueta"].items(), key=lambda x: -x[1]["f"]):
        print(f"  {label:20s} F1={s['f']:.3f}  (P={s['p']:.3f}  R={s['r']:.3f})")
    print(f"\nModelo guardado en: {output_dir}")
    print(f"Reporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
