"""Etapa A.5 — Evaluación de la DETECCIÓN DE SECCIONES (lo que usa el producto).

El diagnóstico pide saber si el CV tiene las 4 secciones clave:
  Contacto, Experiencia, Educacion, Habilidades.

Aquí medimos qué tan bien el sistema (modelo de entidades + diccionario +
encabezados) decide si cada sección ESTÁ PRESENTE o NO en un CV. Se reporta F1
por sección, F1 macro y exactitud global.

Se evalúa con el mismo detector que usa el producto (`detectar_secciones`), no
con una copia de las reglas, para que el número reportado sea el real.

Uso:
    .venv/bin/python scripts/eval_sections.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.core.diagnostico import detectar_secciones
from src.core.nlp_engine import get_nlp

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

    nlp = get_nlp()
    test_records = load_records(config.NER_DIR / "test.jsonl")

    # Contador por sección: [TP, FP, FN, TN]
    stats = {section: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for section in SECTION_GOLD}

    for record in test_records:
        text = record["text"]
        doc = nlp(text)
        predicciones = detectar_secciones(text, {ent.label_ for ent in doc.ents})
        gold_labels = {ent["label"] for ent in record["entities"]}

        for section, labels in SECTION_GOLD.items():
            gold = any(lbl in gold_labels for lbl in labels)
            pred = predicciones[section]
            s = stats[section]
            if gold and pred:
                s["tp"] += 1
            elif pred and not gold:
                s["fp"] += 1
            elif gold and not pred:
                s["fn"] += 1
            else:
                s["tn"] += 1

    print(f"=== DETECCIÓN DE SECCIONES ({len(test_records)} CVs de prueba) ===")
    print("Detector: modelo de entidades + diccionario de habilidades + encabezados\n")
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
    exactitud = (totals["tp"] + sum(s["tn"] for s in stats.values())) / (
        sum(sum(s.values()) for s in stats.values())
    )
    print(f"\nF1 macro: {macro_f1:.4f}   (objetivo >= 0,80)")
    print(f"F1 micro: {micro_f1:.4f}")
    print(f"Exactitud por sección: {exactitud:.4f}")

    report = {
        "modelo": str(model_dir.name),
        "cvs_evaluados": len(test_records),
        "metricas_por_seccion": stats,
        "f1_macro": macro_f1,
        "f1_micro": micro_f1,
        "exactitud": exactitud,
        "objetivo": 0.80,
    }
    report_path = config.MODELS_DIR / "sections_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
