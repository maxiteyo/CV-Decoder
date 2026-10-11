"""Lectura del dataset principal: DataTurks "Entity Recognition in Resumes".

Formato de cada línea del archivo:
    {"content": "texto del CV",
     "annotation": [{"label": ["Skills"],
                     "points": [{"start": 10, "end": 14, "text": "Java"}]}]}

Devolvemos registros con este formato común:
    {"id": str, "source": "dataturks", "text": str,
     "entities": [{"start": int, "end": int, "label": str}, ...]}
"""

import json
from pathlib import Path

from .cleaning import is_valid_length, resolve_overlaps, strip_surrogates
from .labels import DATATURKS_LABEL_MAP


def load_dataturks(path: str | Path) -> list[dict]:
    records: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            text = strip_surrogates(obj.get("content", "") or "")

            entities: list[dict] = []
            for annotation in obj.get("annotation", []):
                labels = annotation.get("label") or []
                if not labels:
                    continue
                mapped = DATATURKS_LABEL_MAP.get(labels[0])
                if mapped is None:
                    continue  # etiqueta desconocida o UNKNOWN
                for point in annotation.get("points", []):
                    start, end = point.get("start"), point.get("end")
                    if start is None or end is None:
                        continue
                    entities.append({"start": int(start), "end": int(end), "label": mapped})

            # El texto se deja intacto para no romper las posiciones.
            if not is_valid_length(text):
                continue

            entities = [e for e in entities if 0 <= e["start"] < e["end"] <= len(text)]
            entities = resolve_overlaps(entities)

            records.append(
                {
                    "id": f"dataturks_{index:04d}",
                    "source": "dataturks",
                    "text": text,
                    "entities": entities,
                }
            )
    return records
