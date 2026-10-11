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


def text_quality(text: str) -> dict:
    """Devuelve medidas básicas de calidad del texto."""
    n = len(text)
    words = _WORD.findall(text)
    alnum = len(_ALNUM.findall(text))
    return {
        "caracteres": n,
        "palabras": len(words),
        "lineas": text.count("\n") + 1 if text else 0,
        "ratio_alfanumerico": (alnum / n) if n else 0.0,
        "caracteres_rotos": text.count("\ufffd"),
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
