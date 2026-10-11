"""Etapa A.5 — Evaluación de la DETECCIÓN DE SECCIONES (lo que usa el producto).

El diagnóstico pide saber si el CV tiene las 4 secciones clave:
  Contacto, Experiencia, Educacion, Habilidades.

Aquí medimos qué tan bien el sistema (modelo de entidades + diccionario + reglas)
decide si cada sección ESTÁ PRESENTE o NO en un CV. Se reporta F1 por sección,
F1 macro y exactitud global.

Uso:
    .venv/bin/python scripts/eval_sections.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spacy
from spacy.matcher import PhraseMatcher

from src import config
from src.data_loader.skills_lexicon import build_skill_lexicon

# Reglas simples de apoyo.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")

SECTION_GOLD = {
    "Contacto": ["PERSONA", "CORREO", "UBICACION"],
    "Experiencia": ["EMPRESA", "PUESTO", "ANIOS_EXPERIENCIA"],
    "Educacion": ["TITULO", "INSTITUCION", "ANIO_EGRESO"],
    "Habilidades": ["HABILIDAD"],
}


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main() -> None:
    model_dir = config.MODELS_DIR / "ner_dataturks_sm"
    if not model_dir.exists():
        print(f"No existe el modelo {model_dir}. Entrená primero con train_ner.py.")
        return
    nlp = spacy.load(model_dir)
    for pipe in ["tagger", "parser", "attribute_ruler", "lemmatizer"]:
        if pipe in nlp.pipe_names:
            nlp.disable_pipe(pipe)

    lexicon = build_skill_lexicon(config.REFS_DIR, None, include_job_skills=False)
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("HABILIDAD", [nlp.make_doc(t) for t in lexicon if len(t) >= 2])

    test_records = load_records(config.NER_DIR / "test.jsonl")

    # Contador por sección: [TP, FP, FN]
    stats = {section: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for section in SECTION_GOLD}

    for record in test_records:
        text = record["text"]
        doc = nlp(text)

        predicted_labels = {ent.label_ for ent in doc.ents}
        if EMAIL_RE.search(text) or PHONE_RE.search(text):
            predicted_labels.add("CORREO")
        if matcher(doc):
            predicted_labels.add("HABILIDAD")

        gold_labels = {ent["label"] for ent in record["entities"]}

        for section, labels in SECTION_GOLD.items():
            gold = any(lbl in gold_labels for lbl in labels)
            pred = any(lbl in predicted_labels for lbl in labels)
            s = stats[section]
            if gold and pred:
                s["tp"] += 1
            elif pred and not gold:
                s["fp"] += 1
            elif gold and not pred:
                s["fn"] += 1
            else:
                s["tn"] += 1

    print("=== DETECCIÓN DE SECCIONES (34 CVs de prueba) ===")
    print(f"{'Sección':14s} {'F1':>7s} {'Prec':>7s} {'Rec':>7s} {'Aciertos':>9s}")
    f1_values = []
    totals = {"tp": 0, "fp": 0, "fn": 0}
    for section, s in stats.items():
        p = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else 0.0
        r = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        acc = (s["tp"] + s["tn"]) / sum(s.values())
        f1_values.append(f)
        for k in totals:
            totals[k] += s[k]
        print(f"{section:14s} {f:7.3f} {p:7.3f} {r:7.3f} {acc:9.3f}")
    macro_f1 = sum(f1_values) / len(f1_values)
    p = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 0.0
    r = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 0.0
    micro_f1 = 2 * p * r / (p + r) if p + r else 0.0
    print(f"\nF1 macro: {macro_f1:.4f}")
    print(f"F1 micro: {micro_f1:.4f}")

    report = {
        "metricas_por_seccion": stats,
        "f1_macro": macro_f1,
        "f1_micro": micro_f1,
    }
    report_path = config.MODELS_DIR / "sections_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
