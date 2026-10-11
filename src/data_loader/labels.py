"""Esquema de etiquetas del modelo de detección de entidades.

Traducimos las etiquetas originales de DataTurks a nombres propios del proyecto
(en español) y definimos a qué sección del CV pertenece cada una.
"""

# Mapeo directo desde las etiquetas originales de DataTurks a las nuestras.
# Las que mapean a None se descartan.
DATATURKS_LABEL_MAP: dict[str, str | None] = {
    "Name": "PERSONA",
    "Email Address": "CORREO",
    "Location": "UBICACION",
    "Companies worked at": "EMPRESA",
    "Designation": "PUESTO",
    "Skills": "HABILIDAD",
    "Degree": "TITULO",
    "College Name": "INSTITUCION",
    "Graduation Year": "ANIO_EGRESO",
    "Years of Experience": "ANIOS_EXPERIENCIA",
    "UNKNOWN": None,
}

# Etiquetas finales del modelo (orden estable y documentado).
LABELS: list[str] = [
    "PERSONA",
    "CORREO",
    "UBICACION",
    "EMPRESA",
    "PUESTO",
    "HABILIDAD",
    "TITULO",
    "INSTITUCION",
    "ANIO_EGRESO",
    "ANIOS_EXPERIENCIA",
]

# Esquema "grueso": agrupa etiquetas finas en pocas categorías con más ejemplos.
# Sirve para el diagnóstico por SECCIONES (no necesitamos distinguir "empresa"
# de "puesto" para saber si la sección Experiencia existe).
COARSE_MAP: dict[str, str] = {
    "PERSONA": "PERSONA",
    "CORREO": "CORREO",
    "UBICACION": "UBICACION",
    "EMPRESA": "EXPERIENCIA",
    "PUESTO": "EXPERIENCIA",
    "ANIOS_EXPERIENCIA": "EXPERIENCIA",
    "TITULO": "EDUCACION",
    "INSTITUCION": "EDUCACION",
    "ANIO_EGRESO": "EDUCACION",
    "HABILIDAD": "HABILIDAD",
}

COARSE_LABELS: list[str] = [
    "PERSONA",
    "CORREO",
    "UBICACION",
    "EXPERIENCIA",
    "EDUCACION",
    "HABILIDAD",
]

# Qué etiquetas se consideran evidencia de cada sección del CV (esquema grueso).
SECTION_ENTITIES: dict[str, list[str]] = {
    "Contacto": ["PERSONA", "CORREO", "UBICACION"],
    "Experiencia": ["EXPERIENCIA"],
    "Educacion": ["EDUCACION"],
    "Habilidades": ["HABILIDAD"],
}


def labels_for_schema(schema: str) -> list[str]:
    """Devuelve la lista de etiquetas según el esquema elegido."""
    return COARSE_LABELS if schema == "coarse" else LABELS


def remap_label(label: str, schema: str) -> str:
    """Traduce una etiqueta fina a la del esquema pedido."""
    return COARSE_MAP.get(label, label) if schema == "coarse" else label
