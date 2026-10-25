"""Medición de "parseabilidad": ¿qué tan usable es el texto extraído de un PDF?

Definimos parseabilidad como:
  - el texto tiene suficientes palabras (no quedó vacío ni casi vacío), y
  - la mayoría de sus caracteres son letras o números (no puro símbolo basura).
"""

import re

_WORD = re.compile(r"\S+")
_ALNUM = re.compile(r"[A-Za-z0-9]")
_TOKEN = re.compile(r"[A-Za-z0-9]+")

MIN_PALABRAS = 30
MIN_RATIO_ALFANUMERICO = 0.5
# Una "palabra pegada" es un token larguísimo sin espacios (el PDF perdió los
# espacios al extraer, ej. "Lookingforapromising&challengingcareer"). Rompe el
# matcheo de habilidades aunque el texto "se lea".
PALABRA_PEGADA_MIN = 20


def text_quality(text: str) -> dict:
    """Devuelve medidas básicas de calidad del texto.

    El ratio alfanumérico se mide sobre los caracteres que no son espacios:
    un PDF con columnas deja muchos espacios de relleno y eso no es "texto
    roto". Lo que importa es qué proporción de lo visible son letras/números.
    """
    n = len(text)
    words = _WORD.findall(text)
    alnum = len(_ALNUM.findall(text))
    visibles = sum(1 for c in text if not c.isspace())
    pegadas = sum(1 for w in words if len(w) >= PALABRA_PEGADA_MIN)
    return {
        "caracteres": n,
        "palabras": len(words),
        "lineas": text.count("\n") + 1 if text else 0,
        "ratio_alfanumerico": (alnum / visibles) if visibles else 0.0,
        "caracteres_rotos": text.count("\ufffd"),
        "palabras_pegadas": pegadas,
        "ratio_palabras_pegadas": (pegadas / len(words)) if words else 0.0,
    }


def is_parseable(
    text: str,
    min_palabras: int = MIN_PALABRAS,
    min_ratio: float = MIN_RATIO_ALFANUMERICO,
) -> bool:
    """Decide si el texto extraído es utilizable."""
    q = text_quality(text)
    return q["palabras"] >= min_palabras and q["ratio_alfanumerico"] >= min_ratio


def word_set(text: str) -> set[str]:
    """Palabras normalizadas (minúsculas, solo letras/números) de un texto."""
    return {token.lower() for token in _TOKEN.findall(text)}


def word_coverage(extracted: str, expected: str) -> float:
    """Qué fracción de las palabras esperadas aparece en el texto extraído.

    1.0 = se recuperaron todas las palabras; 0.0 = no se recuperó ninguna.
    """
    expected_words = word_set(expected)
    if not expected_words:
        return 1.0
    return len(expected_words & word_set(extracted)) / len(expected_words)
