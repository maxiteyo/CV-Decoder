"""Motor de diagnóstico: combina las 4 dimensiones en un solo resultado.

Dimensiones:
  1. Parseabilidad  : ¿se puede leer el texto del PDF?
  2. Secciones       : ¿tiene Contacto, Experiencia, Educación y Habilidades?
  3. Brecha de skills: ¿qué habilidades pide la oferta y no están en el CV?
  4. Similitud       : ¿qué tan parecido es el CV a la oferta?
"""

from __future__ import annotations

import re

from src.core.nlp_engine import get_nlp, get_skill_matcher
from src.models.similarity import get_similarity_model, similitud_a_puntaje

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-()]{6,}\d)")

SECCION_POR_ETIQUETA = {
    "Contacto": {"PERSONA", "CORREO", "UBICACION"},
    "Experiencia": {"EMPRESA", "PUESTO", "ANIOS_EXPERIENCIA"},
    "Educacion": {"TITULO", "INSTITUCION", "ANIO_EGRESO"},
}

PESOS_POR_DEFECTO = {
    "similitud": 0.40,
    "secciones": 0.25,
    "keyword_gap": 0.20,
    "parseabilidad": 0.15,
}


def extraer_entidades(texto: str) -> list[dict]:
    nlp = get_nlp()
    doc = nlp(texto)
    return [
        {"etiqueta": ent.label_, "texto": ent.text, "inicio": ent.start_char}
        for ent in doc.ents
    ]


def extraer_habilidades(texto: str) -> list[str]:
    """Habilidades encontradas con el diccionario curado (únicas, ordenadas)."""
    matcher = get_skill_matcher()
    doc = get_nlp()(texto)
    encontradas = {doc[start:end].text.lower().strip() for _, start, end in matcher(doc)}
    return sorted(encontradas)


def detectar_secciones(texto: str, etiquetas: set[str]) -> dict[str, bool]:
    presentes = {seccion: bool(etiquetas & labels) for seccion, labels in SECCION_POR_ETIQUETA.items()}
    # Contacto también si hay email o teléfono.
    if EMAIL_RE.search(texto) or PHONE_RE.search(texto):
        presentes["Contacto"] = True
    # Habilidades por diccionario.
    presentes["Habilidades"] = len(extraer_habilidades(texto)) > 0
    return presentes


def puntaje_parseabilidad(texto: str, min_palabras: int = 30, min_ratio: float = 0.5) -> float:
    from src.parsing.quality import text_quality

    q = text_quality(texto)
    if q["caracteres"] == 0:
        return 0.0
    suficientes = min(q["palabras"] / min_palabras, 1.0)
    calidad = min(q["ratio_alfanumerico"] / min_ratio, 1.0)
    return round(100 * suficientes * calidad, 1)


def analizar(
    cv_texto: str,
    oferta_texto: str,
    motor_similitud: str = "tfidf",
    pesos: dict[str, float] | None = None,
) -> dict:
    """Devuelve el diagnóstico completo de un CV contra una oferta."""
    pesos = pesos or PESOS_POR_DEFECTO

    entidades = extraer_entidades(cv_texto)
    etiquetas = {e["etiqueta"] for e in entidades}
    secciones = detectar_secciones(cv_texto, etiquetas)
    faltantes_seccion = [s for s, presente in secciones.items() if not presente]

    skills_cv = extraer_habilidades(cv_texto)
    skills_oferta = extraer_habilidades(oferta_texto)
    coincidencias = sorted(set(skills_cv) & set(skills_oferta))
    gaps = sorted(set(skills_oferta) - set(skills_cv))
    cobertura = (len(coincidencias) / len(skills_oferta)) if skills_oferta else 1.0

    modelo = get_similarity_model(motor_similitud)
    similitud_valor = modelo.similitud(cv_texto, oferta_texto)

    dim_parseabilidad = puntaje_parseabilidad(cv_texto)
    dim_secciones = round(100 * sum(secciones.values()) / len(secciones), 1)
    dim_gap = round(100 * cobertura, 1)
    dim_similitud = similitud_a_puntaje(similitud_valor)

    puntaje_global = round(
        pesos["similitud"] * dim_similitud
        + pesos["secciones"] * dim_secciones
        + pesos["keyword_gap"] * dim_gap
        + pesos["parseabilidad"] * dim_parseabilidad,
        1,
    )

    return {
        "puntaje_global": puntaje_global,
        "dimensiones": {
            "parseabilidad": {"puntaje": dim_parseabilidad},
            "secciones": {
                "puntaje": dim_secciones,
                "detalle": secciones,
                "faltantes": faltantes_seccion,
            },
            "keyword_gap": {
                "puntaje": dim_gap,
                "coincidencias": coincidencias,
                "faltantes": gaps,
                "total_oferta": len(skills_oferta),
                "total_cv": len(skills_cv),
            },
            "similitud": {"puntaje": dim_similitud, "motor": modelo.nombre, "crudo": round(similitud_valor, 4)},
        },
    }
