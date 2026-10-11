"""Etapa A.4 — Extracción de habilidades con diccionario (línea base).

Busca habilidades concretas en el texto usando un diccionario curado de 808
términos (+ sinónimos). Es la pieza que alimenta el "keyword gap" del producto.

Nota metodológica: en el dataset DataTurks las habilidades NO están anotadas una
por una, sino como BLOQUES (toda la lista de habilidades junta). Por eso no se
puede medir un F1 clásico de "habilidad exacta" contra ese dataset. Lo que sí
medimos aquí es una verificación de funcionamiento: cuántas habilidades encuentra
y en cuántos CVs.

Uso:
    .venv/bin/python scripts/eval_skills_gazetteer.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spacy
from spacy.matcher import PhraseMatcher

from src import config
from src.data_loader.cleaning import resolve_overlaps
from src.data_loader.skills_lexicon import build_skill_lexicon


def load_records(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main() -> None:
    lexicon = build_skill_lexicon(config.REFS_DIR, None, include_job_skills=False)
    print(f"Términos en el diccionario: {len(lexicon)}")

    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("HABILIDAD", [nlp.make_doc(t) for t in lexicon if len(t) >= 2])

    test_records = load_records(config.NER_DIR / "test.jsonl")
    docs_with_skills = 0
    total_skills = 0
    distinct = set()

    for record in test_records:
        doc = nlp(record["text"])
        spans = [
            {"start": doc[s].idx, "end": doc[e - 1].idx + len(doc[e - 1].text), "label": "HABILIDAD"}
            for _, s, e in matcher(doc)
        ]
        spans = resolve_overlaps(spans)
        if spans:
            docs_with_skills += 1
        total_skills += len(spans)
        for span in spans:
            distinct.add(record["text"][span["start"] : span["end"]].lower().strip())

    n = len(test_records)
    print("\n=== EXTRACCIÓN DE HABILIDADES (diccionario) ===")
    print(f"CVs procesados              : {n}")
    print(f"CVs con al menos 1 habilidad: {docs_with_skills}")
    print(f"Habilidades encontradas     : {total_skills}")
    print(f"Habilidades distintas       : {len(distinct)}")
    print(f"Promedio por CV             : {total_skills / n:.1f}")

    report = {
        "metodo": "gazetteer_lexicon",
        "terminos_diccionario": len(lexicon),
        "cvs": n,
        "cvs_con_habilidades": docs_with_skills,
        "habilidades_encontradas": total_skills,
        "habilidades_distintas": len(distinct),
        "promedio_por_cv": total_skills / n,
    }
    report_path = config.MODELS_DIR / "skills_gazetteer_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
