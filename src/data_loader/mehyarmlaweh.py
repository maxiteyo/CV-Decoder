"""Lectura del dataset "NER Annotated CVs" (5029 CVs).

Este dataset es GRANDE pero RUIDOSO: todas sus marcas son del tipo "SKILL:" y
muchas etiquetan palabras que NO son habilidades ("English", "Work", "Project",
"Company"...) y hay documentos vacíos.

Por eso sólo lo usamos como REFUERZO del tipo HABILIDAD y tras una limpieza
fuerte:
  1. se descartan documentos vacíos o muy cortos,
  2. se conservan sólo las marcas cuyo texto esté en un diccionario curado de
     habilidades (o sinónimos válidos),
  3. se descartan palabras genéricas (lista negra),
  4. se resuelven solapamientos.

Formato de cada archivo:
    {"text": "texto del CV",
     "annotations": [[inicio, fin, "SKILL: python"], ...]}
"""

import json
from pathlib import Path

from .cleaning import is_valid_length, resolve_overlaps, strip_surrogates

MAX_ENTITIES_PER_DOC = 60


def load_mehyarmlaweh(
    directory: str | Path,
    skill_lexicon: set[str],
    blacklist: set[str],
) -> list[dict]:
    records: list[dict] = []
    files = sorted(Path(directory).glob("*.json"))

    for index, file_path in enumerate(files):
        with open(file_path, encoding="utf-8") as handle:
            obj = json.load(handle)

        text = strip_surrogates(obj.get("text", "") or "")
        if not is_valid_length(text):
            continue

        entities: list[dict] = []
        for annotation in obj.get("annotations", []):
            if len(annotation) < 3:
                continue
            start, end, label = annotation[0], annotation[1], annotation[2]
            if not isinstance(label, str) or not label.startswith("SKILL:"):
                continue

            surface = label.split(":", 1)[1].strip().lower()
            if surface in blacklist or surface not in skill_lexicon:
                continue
            entities.append({"start": int(start), "end": int(end), "label": "HABILIDAD"})

        entities = [e for e in entities if 0 <= e["start"] < e["end"] <= len(text)]
        entities = resolve_overlaps(entities)[:MAX_ENTITIES_PER_DOC]

        if not entities:
            continue  # documentos sin ninguna habilidad válida no aportan

        records.append(
            {
                "id": f"mehyarmlaweh_{index:05d}",
                "source": "mehyarmlaweh",
                "text": text,
                "entities": entities,
            }
        )
    return records
