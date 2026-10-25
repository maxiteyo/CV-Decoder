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
from src.data_loader.cleaning import resolve_overlaps
from src.models.similarity import get_similarity_model

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-()]{6,}\d)")

SECCION_POR_ETIQUETA = {
    "Contacto": {"PERSONA", "CORREO", "UBICACION"},
    "Experiencia": {"EMPRESA", "PUESTO", "ANIOS_EXPERIENCIA"},
    "Educacion": {"TITULO", "INSTITUCION", "ANIO_EGRESO"},
}

# Encabezados típicos de sección. Se usan como señal de apoyo: en CVs reales el
# modelo de entidades puede no reconocer una empresa o un puesto, pero el título
# "WORK EXPERIENCE" está ahí a la vista. Se exige que la línea sea corta para no
# confundir una frase ("experience in sales...") con un encabezado.
SECCION_ENCABEZADOS = {
    "Experiencia": re.compile(
        r"^(?:\W*)(work\s+)?(experience|employment|professional\s+experience|"
        r"work\s+history|career\s+(history|summary)|employment\s+history|"
        r"professional\s+background)\b",
        re.IGNORECASE,
    ),
    "Educacion": re.compile(
        r"^(?:\W*)(education|academic\s+(background|qualifications?)|"
        r"educational\s+background|qualifications|studies)\b",
        re.IGNORECASE,
    ),
    "Habilidades": re.compile(
        r"^(?:\W*)(skills|technical\s+skills|core\s+competenc|competencies|"
        r"technologies|areas\s+of\s+expertise|expertise)\b",
        re.IGNORECASE,
    ),
}
MAX_LARGO_ENCABEZADO = 60

PESOS_POR_DEFECTO = {
    "similitud": 0.40,
    "secciones": 0.25,
    "keyword_gap": 0.20,
    "parseabilidad": 0.15,
}


def _entidades_de_doc(doc) -> list[dict]:
    return [
        {"etiqueta": ent.label_, "texto": ent.text, "inicio": ent.start_char}
        for ent in doc.ents
    ]


def _habilidades_de_doc(doc, texto: str) -> list[str]:
    """Habilidades del diccionario dentro de un documento ya procesado.

    Si dos términos se pisan ("communication" dentro de "communication skills"),
    se queda el más largo: así no se cuenta dos veces la misma habilidad.
    """
    spans = [
        {
            "start": doc[start].idx,
            "end": doc[end - 1].idx + len(doc[end - 1].text),
            "label": "HABILIDAD",
        }
        for _, start, end in get_skill_matcher()(doc)
    ]
    return sorted(
        {
            texto[span["start"] : span["end"]].lower().strip()
            for span in resolve_overlaps(spans)
        }
    )


def extraer_entidades(texto: str) -> list[dict]:
    """Entidades del modelo de NER (nombre, correo, empresa, puesto, etc.)."""
    return _entidades_de_doc(get_nlp()(texto))


def extraer_habilidades(texto: str) -> list[str]:
    """Habilidades encontradas con el diccionario curado (únicas, ordenadas)."""
    return _habilidades_de_doc(get_nlp()(texto), texto)


def _tiene_encabezado(texto: str, patron: re.Pattern) -> bool:
    """True si alguna línea corta del CV es el encabezado de esa sección."""
    for linea in texto.splitlines():
        linea = linea.strip()
        if 0 < len(linea) <= MAX_LARGO_ENCABEZADO and patron.match(linea):
            return True
    return False


def detectar_secciones(
    texto: str,
    etiquetas: set[str],
    habilidades: list[str] | None = None,
) -> dict[str, bool]:
    """Decide qué secciones tiene el CV combinando tres señales.

    Señales: entidades del modelo, encabezados visibles y diccionario de
    habilidades (+ email/teléfono para Contacto).
    """
    presentes = {seccion: bool(etiquetas & labels) for seccion, labels in SECCION_POR_ETIQUETA.items()}
    for seccion, patron in SECCION_ENCABEZADOS.items():
        if not presentes.get(seccion) and _tiene_encabezado(texto, patron):
            presentes[seccion] = True
    if EMAIL_RE.search(texto) or PHONE_RE.search(texto):
        presentes["Contacto"] = True
    if habilidades is None:
        habilidades = extraer_habilidades(texto)
    presentes["Habilidades"] = presentes.get("Habilidades", False) or len(habilidades) > 0
    return presentes


def procesar_cv(texto: str) -> dict:
    """Saca entidades, habilidades y secciones procesando el texto UNA sola vez.

    El modelo de NLP es la parte más cara del diagnóstico; procesar el mismo CV
    tres veces (para entidades, habilidades y secciones) triplicaba ese costo.
    """
    doc = get_nlp()(texto)
    entidades = _entidades_de_doc(doc)
    etiquetas = {e["etiqueta"] for e in entidades}
    habilidades = _habilidades_de_doc(doc, texto)
    secciones = detectar_secciones(texto, etiquetas, habilidades=habilidades)
    return {
        "entidades": entidades,
        "etiquetas": etiquetas,
        "habilidades": habilidades,
        "secciones": secciones,
    }


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
    nlp = get_nlp()

    # El CV se procesa una sola vez y de ahí salen entidades, skills y secciones.
    perfil = procesar_cv(cv_texto)
    skills_cv = perfil["habilidades"]
    secciones = perfil["secciones"]
    faltantes_seccion = [s for s, presente in secciones.items() if not presente]

    skills_oferta = _habilidades_de_doc(nlp(oferta_texto), oferta_texto)
    coincidencias = sorted(set(skills_cv) & set(skills_oferta))
    gaps = sorted(set(skills_oferta) - set(skills_cv))
    cobertura = (len(coincidencias) / len(skills_oferta)) if skills_oferta else 1.0

    modelo = get_similarity_model(motor_similitud)
    similitud_valor = modelo.similitud(cv_texto, oferta_texto)

    dim_parseabilidad = puntaje_parseabilidad(cv_texto)
    dim_secciones = round(100 * sum(secciones.values()) / len(secciones), 1)
    dim_gap = round(100 * cobertura, 1)
    dim_similitud = modelo.puntaje(similitud_valor)

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
            "similitud": {
                "puntaje": dim_similitud,
                "motor": modelo.nombre,
                "crudo": round(similitud_valor, 4),
            },
        },
    }
