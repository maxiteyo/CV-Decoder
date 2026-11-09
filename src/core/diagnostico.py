"""Motor de diagnóstico: separa calidad del CV (ATS) y compatibilidad.

Dimensiones:
  1. Parseabilidad  : ¿se puede leer el texto del PDF?
  2. Secciones       : ¿tiene Contacto, Experiencia, Educación y Habilidades?
  3. Brecha de skills: ¿qué habilidades pide la oferta y no están en el CV?
  4. Similitud       : ¿qué tan parecido es el CV a la oferta?

El resultado expone dos puntajes independientes:

  - ``puntaje_ats``   : qué tan bien armado está el CV como documento.
  - ``puntaje_match`` : qué tan bien se adecúa a la oferta.

``puntaje_global`` se conserva como alias de ``puntaje_match`` para no romper la
API existente. El ATS no se suma al match: un CV puede ser 100 ATS y 10 match.
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

# Encabezados de la oferta. Se separan requisitos, deseables y beneficios para
# no contar como obligatorio algo que aparece en "Benefits" o en una tarea.
SECCIONES_OFERTA = {
    "responsabilidades": re.compile(
        r"^(?:responsibilities|responsabilidades|role description|the role|"
        r"about the role|what you(?:'ll| will) do|day to day|key duties|"
        r"main tasks)\b",
        re.IGNORECASE,
    ),
    "requisitos": re.compile(
        r"^(?:requirements|requisitos|qualifications|minimum qualifications|"
        r"basic qualifications|must[\s-]+have|what we(?:'re| are) looking for|"
        r"what you bring)\b",
        re.IGNORECASE,
    ),
    "deseables": re.compile(
        r"^(?:nice[\s-]+to[\s-]+have|preferred qualifications|deseables|"
        r"desired qualifications|bonus points)\b",
        re.IGNORECASE,
    ),
    "beneficios": re.compile(
        r"^(?:benefits|beneficios|we offer|perks|what we offer|compensation)\b",
        re.IGNORECASE,
    ),
}

# "Requirements:" y "Responsibilities:" pueden venir en la misma línea.
ENCABEZADO_INLINE = re.compile(
    r"\b(responsibilities|responsabilidades|role description|the role|"
    r"about the role|requirements|requisitos|qualifications|minimum qualifications|"
    r"nice[\s-]+to[\s-]+have|preferred qualifications|deseables|"
    r"benefits|beneficios|we offer|perks)\s*:",
    re.IGNORECASE,
)

# Sinónimos que aparecen distinto en CVs y ofertas. El valor es la forma
# canónica que se usa para comparar; el listado visible también usa esa forma.
SINONIMOS_HABILIDAD = {
    "quality assurance": "qa",
    "quality assurance (qa)": "qa",
    "qa testing": "qa",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "continuous integration": "ci",
    "ci/cd": "ci",
    "communication skills": "communication",
    "communication skill": "communication",
    "regression testing": "regression",
    "api testing": "api",
    "integration testing": "integration",
    "object-oriented programming": "oop",
    "object oriented programming": "oop",
    "asp.net mvc": "asp.net",
    "dotnet": ".net",
    ".net core": ".net",
    "nodejs": "node.js",
    "reactjs": "react",
}

# Grupos que se consideran equivalentes sin perder el nombre específico en el
# listado de faltantes (por ejemplo, un CV con iOS cubre "mobile").
GRUPOS_EQUIVALENTES = (
    frozenset({"mobile", "ios", "android"}),
)

PESO_DESEABLE = 0.4
CAP_SIN_OBLIGATORIOS_BAJO = 25.0
CAP_SIN_OBLIGATORIOS_MEDIO = 50.0

# Pesos del match: la similitud manda y la brecha de skills aporta, pero la
# calidad del CV (parseabilidad y secciones) no infla la compatibilidad.
PESOS_MATCH = {
    "similitud": 0.90,
    "keyword_gap": 0.10,
    "secciones": 0.0,
    "parseabilidad": 0.0,
}

# Alias histórico: la API y los tests existentes importan este nombre.
PESOS_POR_DEFECTO = PESOS_MATCH

# El ATS es una dimensión aparte: mide el CV como documento, no contra la oferta.
PESOS_ATS = {
    "parseabilidad": 0.50,
    "secciones": 0.50,
}

NIVEL_MATCH_BAJO = 20.0
NIVEL_MATCH_BUENO = 50.0
NIVEL_MATCH_MUY_BUENO = 75.0


def nivel_match(puntaje: float) -> str:
    """Etiqueta cualitativa del match (cortes provisorios de la Fase 1)."""
    if puntaje < NIVEL_MATCH_BAJO:
        return "bajo"
    if puntaje < NIVEL_MATCH_BUENO:
        return "medio"
    if puntaje < NIVEL_MATCH_MUY_BUENO:
        return "bueno"
    return "muy bueno"


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


def _clasificar_encabezado(linea: str) -> str | None:
    """Devuelve la sección de una línea que es solo un encabezado."""
    limpia = linea.strip().strip("•*# ").strip()
    if not limpia or len(limpia) > 80:
        return None
    if limpia.endswith(":"):
        limpia = limpia[:-1].strip()
    elif ":" in limpia:
        # Tiene contenido después de los dos puntos: lo maneja ENCABEZADO_INLINE.
        return None
    limpia = limpia.lower()
    for nombre, patron in SECCIONES_OFERTA.items():
        if patron.match(limpia):
            return nombre
    return None


def segmentar_oferta(texto: str) -> dict[str, str]:
    """Separa la oferta en responsabilidades, requisitos, deseables y beneficios.

    Si un encabezado viene en la misma línea que el contenido ("Requirements:
    Java, SQL"), se corta ahí. El texto sin encabezado queda en ``otros``.
    """
    secciones: dict[str, list[str]] = {
        nombre: [] for nombre in (*SECCIONES_OFERTA, "otros")
    }
    actual = "otros"
    for linea in texto.splitlines():
        coincidencias = list(ENCABEZADO_INLINE.finditer(linea))
        if coincidencias:
            anterior = 0
            for coincidencia in coincidencias:
                fragmento = linea[anterior : coincidencia.start()].strip()
                if fragmento:
                    secciones[actual].append(fragmento)
                actual = _clasificar_encabezado(coincidencia.group(0)) or "otros"
                anterior = coincidencia.end()
            resto = linea[anterior:].strip()
            if resto:
                secciones[actual].append(resto)
            continue

        tipo = _clasificar_encabezado(linea)
        if tipo:
            actual = tipo
        else:
            secciones[actual].append(linea)

    return {nombre: "\n".join(partes).strip() for nombre, partes in secciones.items()}


def normalizar_habilidad(habilidad: str) -> str:
    """Lleva una habilidad a su forma canónica para comparar CV y oferta."""
    limpia = re.sub(r"\s+", " ", habilidad.lower().strip().strip("\"',;:()[]"))
    if limpia.endswith("."):
        limpia = limpia[:-1].rstrip()
    return SINONIMOS_HABILIDAD.get(limpia, limpia)


def _habilidades_de_texto(texto: str, nlp) -> set[str]:
    if not texto.strip():
        return set()
    doc = nlp.make_doc(texto)
    return {normalizar_habilidad(h) for h in _habilidades_de_doc(doc, texto)}


def _coincide_habilidad(habilidad: str, skills_cv: set[str]) -> bool:
    if habilidad in skills_cv:
        return True
    for grupo in GRUPOS_EQUIVALENTES:
        if habilidad in grupo and skills_cv & grupo:
            return True
    return False


def cap_por_requisitos(cobertura_obligatorios: float) -> float | None:
    """Cap del match cuando faltan requisitos centrales (Fase 2)."""
    if cobertura_obligatorios < 30.0:
        return CAP_SIN_OBLIGATORIOS_BAJO
    if cobertura_obligatorios < 50.0:
        return CAP_SIN_OBLIGATORIOS_MEDIO
    return None


def _competencias_de_oferta(oferta_texto: str, nlp) -> dict:
    secciones = segmentar_oferta(oferta_texto)
    if secciones["requisitos"] or secciones["deseables"]:
        confianza = "alta"
        texto_requisitos = secciones["requisitos"]
        texto_deseables = secciones["deseables"]
    else:
        confianza = "baja"
        texto_requisitos = oferta_texto
        texto_deseables = ""

    obligatorios = _habilidades_de_texto(texto_requisitos, nlp)
    deseables = _habilidades_de_texto(texto_deseables, nlp) - obligatorios
    if not obligatorios and not deseables:
        texto_requisitos = oferta_texto
        obligatorios = _habilidades_de_texto(oferta_texto, nlp)
        confianza = "baja"

    detectadas = [
        nombre
        for nombre in ("responsabilidades", "requisitos", "deseables", "beneficios")
        if secciones[nombre]
    ]
    return {
        "obligatorios": obligatorios,
        "deseables": deseables,
        "secciones_detectadas": detectadas or ["texto_completo"],
        "confianza": confianza,
    }


def _evaluar_requisitos(
    obligatorios: set[str],
    deseables: set[str],
    skills_cv: set[str],
) -> dict:
    coincidencias_obligatorias = sorted(
        h for h in obligatorios if _coincide_habilidad(h, skills_cv)
    )
    faltantes_obligatorias = sorted(
        h for h in obligatorios if not _coincide_habilidad(h, skills_cv)
    )
    coincidencias_deseables = sorted(
        h for h in deseables if _coincide_habilidad(h, skills_cv)
    )
    faltantes_deseables = sorted(
        h for h in deseables if not _coincide_habilidad(h, skills_cv)
    )

    cobertura_obligatorios = (
        100.0 * len(coincidencias_obligatorias) / len(obligatorios)
        if obligatorios
        else 100.0
    )
    peso_total = len(obligatorios) + PESO_DESEABLE * len(deseables)
    peso_cubierto = (
        len(coincidencias_obligatorias) + PESO_DESEABLE * len(coincidencias_deseables)
    )
    cobertura_total = 100.0 * peso_cubierto / peso_total if peso_total else 100.0
    cap = cap_por_requisitos(cobertura_obligatorios) if obligatorios else None

    return {
        "coincidencias_obligatorias": coincidencias_obligatorias,
        "faltantes_obligatorias": faltantes_obligatorias,
        "coincidencias_deseables": coincidencias_deseables,
        "faltantes_deseables": faltantes_deseables,
        "coincidencias": sorted(set(coincidencias_obligatorias) | set(coincidencias_deseables)),
        "faltantes": sorted(set(faltantes_obligatorias) | set(faltantes_deseables)),
        "cobertura_obligatorios": round(cobertura_obligatorios, 1),
        "cobertura_total": round(cobertura_total, 1),
        "cap_match": cap,
        "total_oferta": len(obligatorios | deseables),
        "total_cv": len(skills_cv),
    }


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
    """Devuelve el diagnóstico completo de un CV contra una oferta.

    ``pesos`` controla la fórmula del match (no la del ATS). El valor por
    defecto usa 90% similitud + 10% brecha de skills.
    """
    pesos = pesos or PESOS_POR_DEFECTO
    nlp = get_nlp()

    # El CV se procesa una sola vez y de ahí salen entidades, skills y secciones.
    perfil = procesar_cv(cv_texto)
    skills_cv = {normalizar_habilidad(h) for h in perfil["habilidades"]}
    secciones = perfil["secciones"]
    faltantes_seccion = [s for s, presente in secciones.items() if not presente]

    competencias = _competencias_de_oferta(oferta_texto, nlp)
    evaluacion = _evaluar_requisitos(
        competencias["obligatorios"],
        competencias["deseables"],
        skills_cv,
    )

    modelo = get_similarity_model(motor_similitud)
    similitud_valor = modelo.similitud(cv_texto, oferta_texto)

    dim_parseabilidad = puntaje_parseabilidad(cv_texto)
    dim_secciones = round(100 * sum(secciones.values()) / len(secciones), 1)
    dim_gap = evaluacion["cobertura_total"]
    dim_similitud = modelo.puntaje(similitud_valor)

    puntaje_ats = round(
        PESOS_ATS["parseabilidad"] * dim_parseabilidad
        + PESOS_ATS["secciones"] * dim_secciones,
        1,
    )
    puntaje_match_bruto = round(
        pesos["similitud"] * dim_similitud
        + pesos["keyword_gap"] * dim_gap
        + pesos["secciones"] * dim_secciones
        + pesos["parseabilidad"] * dim_parseabilidad,
        1,
    )
    cap = evaluacion["cap_match"]
    puntaje_match = (
        round(min(puntaje_match_bruto, cap), 1) if cap is not None else puntaje_match_bruto
    )
    # Alias de compatibilidad: la API existente sigue leyendo puntaje_global.
    puntaje_global = puntaje_match

    return {
        "puntaje_global": puntaje_global,
        "puntaje_ats": puntaje_ats,
        "puntaje_match": puntaje_match,
        "nivel_match": nivel_match(puntaje_match),
        "requisitos": {
            "obligatorios_cumplidos": evaluacion["coincidencias_obligatorias"],
            "obligatorios_faltantes": evaluacion["faltantes_obligatorias"],
            "deseables_cumplidos": evaluacion["coincidencias_deseables"],
            "deseables_faltantes": evaluacion["faltantes_deseables"],
            "cobertura_obligatorios": evaluacion["cobertura_obligatorios"],
            "cobertura_total": evaluacion["cobertura_total"],
            "cap_match": cap,
            "secciones_detectadas": competencias["secciones_detectadas"],
            "confianza": competencias["confianza"],
        },
        "dimensiones": {
            "parseabilidad": {"puntaje": dim_parseabilidad},
            "secciones": {
                "puntaje": dim_secciones,
                "detalle": secciones,
                "faltantes": faltantes_seccion,
            },
            "keyword_gap": {
                "puntaje": dim_gap,
                "coincidencias": evaluacion["coincidencias"],
                "faltantes": evaluacion["faltantes"],
                "total_oferta": evaluacion["total_oferta"],
                "total_cv": evaluacion["total_cv"],
            },
            "similitud": {
                "puntaje": dim_similitud,
                "motor": modelo.nombre,
                "crudo": round(similitud_valor, 4),
            },
        },
    }
