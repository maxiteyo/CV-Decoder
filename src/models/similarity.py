"""Dimensión 4 del diagnóstico: ¿qué tan parecido es el CV a la oferta?

Hay dos familias de motores:
  - "tfidf"                 : compara palabras (con sinónimos no puede). Rápido,
                              sin descargas. Es el motor oficial del MVP.
  - "embeddings"            : modelo de lenguaje multilingüe (entiende
                              sinónimos y frases). Requiere `sentence-transformers`.
  - "embeddings_fragmentos" : igual, pero compara por fragmentos y se queda con
                              la mejor coincidencia. Queda como experimento.

Por qué el oficial es TF-IDF: medido contra 50 pares calificados a mano, TF-IDF
ordena mejor (Spearman 0,95) que los embeddings de documento entero (0,28) o por
fragmentos (0,50). El detalle está en `docs/etapa-b-resultados.md`.

Calibración: la similitud del coseno vive entre 0 y 1, pero en documentos largos
nunca se acerca a 1. Por eso cada motor define un "techo" (el valor que
consideramos coincidencia total) y el puntaje se estira a 0-100. Sin esto, el
mejor par real sacaba 7,2/100 y hundía el puntaje global.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Stopwords: palabras vacías en inglés y español. Sacarlas subió el Spearman de
# 0,80 a 0,95 porque evita que dos documentos "se parezcan" por puro relleno
# ("and", "with", "para", "con"...).
_PALABRAS_VACIAS_ES = {
    "a", "al", "algo", "ante", "antes", "como", "con", "contra", "cual", "cuando",
    "de", "del", "desde", "donde", "durante", "e", "el", "ella", "ellas", "ellos",
    "en", "entre", "era", "es", "esa", "ese", "eso", "esta", "este", "esto",
    "fue", "ha", "hasta", "hay", "la", "las", "le", "les", "lo", "los", "más",
    "me", "mi", "mis", "mucho", "muy", "no", "nos", "o", "otra", "otro", "para",
    "pero", "poco", "por", "porque", "que", "quien", "se", "sin", "sobre", "su",
    "sus", "también", "te", "tiene", "tu", "tus", "un", "una", "uno", "y", "ya",
    "yo",
}
_PALABRAS_VACIAS_EN = {
    "a", "about", "above", "after", "again", "all", "also", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has",
    "have", "having", "he", "her", "here", "hers", "him", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more",
    "most", "my", "no", "nor", "not", "now", "of", "off", "on", "once", "only",
    "or", "other", "our", "out", "over", "own", "s", "same", "she", "should",
    "so", "some", "such", "t", "than", "that", "the", "their", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with",
    "you", "your", "yours", "yourself",
}
PALABRAS_VACIAS = _PALABRAS_VACIAS_EN | _PALABRAS_VACIAS_ES

# Techos de calibración: coseno que se considera "coincidencia total".
# TF-IDF: 0,10 es el máximo observado en un par realmente bueno del dataset.
# Embeddings: 0,60 (el modelo da ~0,2 entre textos no relacionados y ~0,6 entre
# textos del mismo tema).
TECHO_TFIDF = 0.10
TECHO_EMBEDDINGS = 0.60
TECHO_EMBEDDINGS_FRAGMENTOS = 0.70


def _limpiar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios normalizados.

    Así "Programación" y "programacion" cuentan como la misma palabra.
    """
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def _fragmentos(texto: str, max_palabras: int = 120) -> list[str]:
    """Parte un texto largo en bloques de ~N palabras, respetando los saltos."""
    lineas = [l.strip() for l in re.split(r"\n+", texto or "") if l.strip()]
    bloques: list[str] = []
    actual: list[str] = []
    contador = 0
    for linea in lineas:
        palabras = len(linea.split())
        if contador + palabras > max_palabras and actual:
            bloques.append(" ".join(actual))
            actual, contador = [], 0
        actual.append(linea)
        contador += palabras
    if actual:
        bloques.append(" ".join(actual))
    return bloques or [""]


class TfidfSimilarity:
    """Línea base: TF-IDF de palabras y pares de palabras + similitud coseno."""

    nombre = "tfidf"
    techo = TECHO_TFIDF

    def similitud(self, cv_texto: str, oferta_texto: str) -> float:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [_limpiar(cv_texto), _limpiar(oferta_texto)]
        if not corpus[0] or not corpus[1]:
            return 0.0
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words=list(PALABRAS_VACIAS),
            # Un token puede tener +, # o punto adentro para no perder
            # "c++", "c#", "asp.net" ni "node.js".
            token_pattern=r"(?u)[A-Za-z0-9][\w+#.]*",
        )
        matriz = vectorizer.fit_transform(corpus)
        return float(cosine_similarity(matriz[0], matriz[1])[0, 0])

    def puntaje(self, valor: float) -> float:
        return similitud_a_puntaje(valor, self.techo)


class EmbeddingSimilarity:
    """Motor con embeddings multilingües (entiende español, inglés y spanglish)."""

    nombre = "embeddings"
    techo = TECHO_EMBEDDINGS

    def __init__(self, modelo: str = "paraphrase-multilingual-mpnet-base-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.modelo = modelo
        self._encoder = SentenceTransformer(modelo)

    def similitud(self, cv_texto: str, oferta_texto: str) -> float:
        import numpy as np

        textos = [_limpiar(cv_texto), _limpiar(oferta_texto)]
        if not textos[0] or not textos[1]:
            return 0.0
        embeddings = self._encoder.encode(textos, normalize_embeddings=True)
        return float(np.dot(embeddings[0], embeddings[1]))

    def puntaje(self, valor: float) -> float:
        return similitud_a_puntaje(valor, self.techo)


class EmbeddingFragmentosSimilarity(EmbeddingSimilarity):
    """Variante por fragmentos: compara bloques y promedia la mejor coincidencia.

    Idea: un CV de 400 palabras no entra completo en el modelo (se corta a ~512
    tokens), así que se parte en bloques y se busca el mejor match para cada
    bloque de la oferta. Mejoró respecto del documento entero (0,28 → 0,50) pero
    sigue por debajo de TF-IDF (0,95): no se usa en el MVP.
    """

    nombre = "embeddings_fragmentos"
    techo = TECHO_EMBEDDINGS_FRAGMENTOS

    def similitud(self, cv_texto: str, oferta_texto: str) -> float:
        import numpy as np

        bloques_cv = [_limpiar(b) for b in _fragmentos(cv_texto)]
        bloques_oferta = [_limpiar(b) for b in _fragmentos(oferta_texto)]
        if not bloques_cv[0] or not bloques_oferta[0]:
            return 0.0
        matriz_cv = self._encoder.encode(bloques_cv, normalize_embeddings=True)
        matriz_oferta = self._encoder.encode(bloques_oferta, normalize_embeddings=True)
        similitudes = matriz_oferta @ matriz_cv.T
        return float(similitudes.max(axis=1).mean())


@lru_cache(maxsize=2)
def get_similarity_model(kind: str = "tfidf"):
    """Devuelve el motor pedido. Se cachea para no recargar el modelo."""
    if kind == "tfidf":
        return TfidfSimilarity()
    if kind == "embeddings":
        return EmbeddingSimilarity()
    if kind == "embeddings_fragmentos":
        return EmbeddingFragmentosSimilarity()
    raise ValueError(
        f"Motor desconocido: {kind}. Opciones: tfidf, embeddings, embeddings_fragmentos."
    )


def similitud_a_puntaje(valor: float, techo: float = TECHO_TFIDF) -> float:
    """Convierte una similitud (0..1) a un puntaje de 0 a 100.

    `techo` es el valor que se considera coincidencia total. El mapeo es lineal
    y monótono: no cambia el orden de los pares (el Spearman queda igual), solo
    hace que la escala 0-100 sea interpretable.
    """
    if techo <= 0:
        return 0.0
    return round(100 * max(0.0, min(1.0, valor / techo)), 1)
