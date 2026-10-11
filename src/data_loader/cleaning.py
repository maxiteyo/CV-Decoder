"""Funciones de limpieza y validación de datos.

IMPORTANTE: para los datasets con entidades anotadas (detección de entidades)
NO modificamos el texto, porque cualquier carácter que saquemos o agreguemos
cambiaría las posiciones (offsets) de las etiquetas y las rompería.
La limpieza de texto (HTML, unicode) se aplica sólo a textos sin etiquetas.
"""

import re
import unicodedata

from spacy.tokens import Span
from spacy.util import filter_spans

MIN_TEXT_LEN = 100
MAX_TEXT_LEN = 50_000

_HTML_TAG = re.compile(r"<[^>]+>")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")


def is_valid_length(text: str, min_len: int = MIN_TEXT_LEN, max_len: int = MAX_TEXT_LEN) -> bool:
    """Descarta textos vacíos, demasiado cortos o exageradamente largos."""
    return bool(text) and min_len <= len(text) <= max_len


def strip_surrogates(text: str) -> str:
    """Reemplaza caracteres 'sustitutos' rotos (emojis mal codificados) por espacios.

    Se reemplaza 1 carácter por 1 carácter para NO mover las posiciones de las
    etiquetas.
    """
    return "".join(
        " " if 0xD800 <= ord(char) <= 0xDFFF else char for char in text
    )


def clean_text(text: str) -> str:
    """Limpia texto SIN etiquetas (HTML residual, unicode invisible, espacios)."""
    text = unicodedata.normalize("NFKC", text)
    text = _HTML_TAG.sub(" ", text)
    text = _CONTROL_CHARS.sub("", text)
    text = text.replace("\xa0", " ")
    return text


def normalize_for_dedup(text: str) -> str:
    """Versión normalizada para detectar duplicados (ignora mayúsculas y espacios)."""
    return _WHITESPACE.sub(" ", text.strip().lower())


def spans_from_entities(doc, entities: list[dict]) -> list:
    """Convierte entidades (start, end, label) en spans válidos para spaCy.

    Recorta el espacio en blanco de los bordes (causa del error E024 de spaCy)
    y elimina solapamientos. No toca signos como '+' o '.' internos, para no
    romper habilidades como 'C++' o 'Node.js'.
    """
    spans = []
    for entity in entities:
        span = doc.char_span(
            entity["start"], entity["end"], label=entity["label"], alignment_mode="expand"
        )
        if span is None:
            continue
        start, end = span.start, span.end
        while start < end and doc[start].is_space:
            start += 1
        while end > start and doc[end - 1].is_space:
            end -= 1
        if start >= end:
            continue
        spans.append(Span(doc, start, end, label=entity["label"]))
    return filter_spans(spans)


def resolve_overlaps(entities: list[dict]) -> list[dict]:
    """Resuelve entidades superpuestas dejando la más larga.

    Recibe entidades con 'start', 'end' y 'label' y devuelve una lista donde
    ninguna se solapa con otra (requisito de spaCy).
    """
    ordered = sorted(entities, key=lambda e: (e["start"], -(e["end"] - e["start"])))
    kept: list[dict] = []
    for ent in ordered:
        if ent["end"] <= ent["start"]:
            continue
        if kept and ent["start"] < kept[-1]["end"]:
            previous = kept[-1]
            if (ent["end"] - ent["start"]) > (previous["end"] - previous["start"]):
                kept[-1] = ent  # la nueva es más larga: reemplaza a la anterior
            continue
        kept.append(ent)
    return kept


def merge_adjacent(entities: list[dict]) -> list[dict]:
    """Une entidades contiguas con la misma etiqueta en un solo bloque.

    Ejemplo (esquema grueso): "B.Sc." + "MIT" + "2015" seguidos pasan a ser un
    único bloque de EDUCACION si quedan pegados.
    """
    ordered = sorted(entities, key=lambda e: (e["start"], e["end"]))
    merged: list[dict] = []
    for ent in ordered:
        if merged and merged[-1]["label"] == ent["label"] and ent["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], ent["end"])
        else:
            merged.append(dict(ent))
    return merged


def apply_schema(entities: list[dict], schema: str) -> list[dict]:
    """Traduce las entidades al esquema pedido ('fine' o 'coarse')."""
    from .labels import remap_label

    remapped = [
        {"start": e["start"], "end": e["end"], "label": remap_label(e["label"], schema)}
        for e in entities
    ]
    return merge_adjacent(resolve_overlaps(remapped))
