"""Dimensión 4 del diagnóstico: ¿qué tan parecido es el CV a la oferta?

Se ofrecen dos motores:
  - "tfidf"      : línea base clásica (cuenta palabras, ignora sinónimos).
  - "embeddings" : modelo de lenguaje multilingüe (entiende sinónimos y frases).
                   Requiere `sentence-transformers`.
"""

from __future__ import annotations

from functools import lru_cache


def _clean(text: str) -> str:
    return " ".join((text or "").split())


class TfidfSimilarity:
    """Baseline: TF-IDF de palabras y n-gramas + similitud coseno."""

    nombre = "tfidf"

    def similitud(self, cv_texto: str, oferta_texto: str) -> float:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [_clean(cv_texto), _clean(oferta_texto)]
        if not corpus[0] or not corpus[1]:
            return 0.0
        vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)
        matrix = vectorizer.fit_transform(corpus)
        return float(cosine_similarity(matrix[0], matrix[1])[0, 0])


class EmbeddingSimilarity:
    """Motor con embeddings multilingües (entiende español, inglés y spanglish)."""

    nombre = "embeddings"

    def __init__(self, modelo: str = "paraphrase-multilingual-mpnet-base-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.modelo = modelo
        self._encoder = SentenceTransformer(modelo)

    def similitud(self, cv_texto: str, oferta_texto: str) -> float:
        import numpy as np

        textos = [_clean(cv_texto), _clean(oferta_texto)]
        if not textos[0] or not textos[1]:
            return 0.0
        embeddings = self._encoder.encode(textos, normalize_embeddings=True)
        return float(np.dot(embeddings[0], embeddings[1]))


@lru_cache(maxsize=2)
def get_similarity_model(kind: str = "embeddings"):
    """Devuelve el motor pedido. Se cachea para no recargar el modelo."""
    if kind == "tfidf":
        return TfidfSimilarity()
    if kind == "embeddings":
        return EmbeddingSimilarity()
    raise ValueError(f"Motor desconocido: {kind}")


def similitud_a_puntaje(valor: float) -> float:
    """Convierte una similitud (0..1) a un puntaje de 0 a 100."""
    return round(max(0.0, min(1.0, valor)) * 100, 1)
