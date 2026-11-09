"""Esquemas de entrada y salida de la API (Etapa C).

Se describen con tipos y ejemplos para que Swagger (`/docs`) sirva como
documentación viva: quien prueba la API ve exactamente qué recibe y qué devuelve.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MotorSimilitud = Literal["tfidf", "embeddings", "embeddings_fragmentos"]

EJEMPLO_RESPUESTA = {
    "puntaje_global": 25.0,
    "puntaje_ats": 87.5,
    "puntaje_match": 25.0,
    "nivel_match": "medio",
    "requisitos": {
        "obligatorios_cumplidos": [],
        "obligatorios_faltantes": [".net", "asp.net", "database design", "problem-solving"],
        "deseables_cumplidos": [],
        "deseables_faltantes": [],
        "cobertura_obligatorios": 0.0,
        "cobertura_total": 0.0,
        "cap_match": 25.0,
        "secciones_detectadas": ["responsabilidades", "requisitos"],
        "confianza": "alta",
    },
    "metadatos": {
        "archivo": "cv.pdf",
        "paginas": 1,
        "palabras": 418,
        "motor_similitud": "tfidf",
        "tiempo_ms": 512,
    },
    "dimensiones": {
        "parseabilidad": {"puntaje": 100.0},
        "secciones": {
            "puntaje": 75.0,
            "detalle": {
                "Contacto": True,
                "Experiencia": True,
                "Educacion": True,
                "Habilidades": False,
            },
            "faltantes": ["Habilidades"],
        },
        "keyword_gap": {
            "puntaje": 0.0,
            "coincidencias": [],
            "faltantes": [".net", "asp.net", "database design", "problem-solving"],
            "total_oferta": 4,
            "total_cv": 8,
        },
        "similitud": {"puntaje": 38.9, "motor": "tfidf", "crudo": 0.0623},
    },
}


class ParseabilidadOut(BaseModel):
    """Dimensión 1: ¿se puede extraer texto usable del PDF?"""

    puntaje: float = Field(ge=0, le=100, description="0 = ilegible, 100 = texto limpio")


class SeccionesOut(BaseModel):
    """Dimensión 2: qué secciones tiene el CV."""

    puntaje: float = Field(ge=0, le=100, description="Porcentaje de secciones presentes")
    detalle: dict[str, bool] = Field(description="Sección -> presente o no")
    faltantes: list[str] = Field(description="Secciones que no se detectaron")


class KeywordGapOut(BaseModel):
    """Dimensión 3: habilidades que pide la oferta y no están en el CV."""

    puntaje: float = Field(ge=0, le=100, description="Porcentaje de la oferta cubierto")
    coincidencias: list[str] = Field(description="Habilidades presentes en ambos")
    faltantes: list[str] = Field(description="Habilidades de la oferta ausentes en el CV")
    total_oferta: int = Field(ge=0, description="Habilidades detectadas en la oferta")
    total_cv: int = Field(ge=0, description="Habilidades detectadas en el CV")


class SimilitudOut(BaseModel):
    """Dimensión 4: parecido CV-oferta."""

    puntaje: float = Field(ge=0, le=100, description="Puntaje calibrado de 0 a 100")
    motor: str = Field(description="Motor usado: tfidf (oficial), embeddings o embeddings_fragmentos")
    crudo: float = Field(ge=0, le=1, description="Coseno sin calibrar (0 a 1)")


class DimensionesOut(BaseModel):
    """Las cuatro dimensiones del diagnóstico."""

    parseabilidad: ParseabilidadOut
    secciones: SeccionesOut
    keyword_gap: KeywordGapOut
    similitud: SimilitudOut


class MetadatosOut(BaseModel):
    """Datos de la corrida (útiles para auditar y medir tiempos)."""

    archivo: str = Field(description="Nombre original del PDF")
    paginas: int = Field(ge=0, description="Páginas con estructura legible")
    palabras: int = Field(ge=0, description="Palabras extraídas del PDF")
    motor_similitud: str = Field(description="Motor que se usó finalmente")
    tiempo_ms: int = Field(ge=0, description="Lectura del PDF + diagnóstico, en milisegundos")


class RequisitosOut(BaseModel):
    """Requisitos de la oferta separados por obligatorios y deseables."""

    obligatorios_cumplidos: list[str] = Field(description="Skills obligatorias presentes en el CV")
    obligatorios_faltantes: list[str] = Field(description="Skills obligatorias ausentes en el CV")
    deseables_cumplidos: list[str] = Field(description="Skills deseables presentes en el CV")
    deseables_faltantes: list[str] = Field(description="Skills deseables ausentes en el CV")
    cobertura_obligatorios: float = Field(
        ge=0, le=100, description="Porcentaje de requisitos obligatorios cubiertos"
    )
    cobertura_total: float = Field(
        ge=0, le=100, description="Cobertura ponderada: obligatorios 100%, deseables 40%"
    )
    cap_match: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Tope aplicado al match si faltan requisitos centrales",
    )
    secciones_detectadas: list[str] = Field(
        description="Secciones de la oferta usadas para extraer requisitos"
    )
    confianza: Literal["alta", "baja"] = Field(
        description="Alta si se detectaron secciones; baja si se usó todo el texto"
    )


class DiagnosticoOut(BaseModel):
    """Resultado completo del diagnóstico de un CV contra una oferta."""

    model_config = ConfigDict(json_schema_extra={"example": EJEMPLO_RESPUESTA})

    puntaje_global: float = Field(
        ge=0,
        le=100,
        description="Alias de puntaje_match (compatibilidad CV-oferta)",
    )
    puntaje_ats: float = Field(
        ge=0,
        le=100,
        description="Calidad del CV como documento: parseabilidad + secciones",
    )
    puntaje_match: float = Field(
        ge=0,
        le=100,
        description="Compatibilidad CV-oferta: 90% similitud + 10% brecha de skills",
    )
    nivel_match: Literal["bajo", "medio", "bueno", "muy bueno"] = Field(
        description="Etiqueta cualitativa de puntaje_match"
    )
    requisitos: RequisitosOut
    metadatos: MetadatosOut
    dimensiones: DimensionesOut


class ErrorDetalle(BaseModel):
    """Cuerpo de error, siempre con el mismo formato."""

    codigo: str = Field(description="Código estable para programar contra la API")
    mensaje: str = Field(description="Qué pasó, en una frase")
    sugerencia: str = Field(description="Qué puede hacer quien llama para resolverlo")
    detalles: list[dict] | None = Field(
        default=None,
        description="Detalle técnico de los campos inválidos (solo en errores de validación)",
    )


class ErrorOut(BaseModel):
    """Formato único de error para todas las respuestas 4xx/5xx."""

    error: ErrorDetalle


class SaludOut(BaseModel):
    """Estado del servicio."""

    estado: str
    version: str
    modelo_entidades: str
    motor_oficial: str
