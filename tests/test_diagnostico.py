"""Pruebas del motor de diagnóstico (requieren el modelo NER entrenado)."""

from __future__ import annotations

import pytest

from src import config
from src.core.diagnostico import analizar

pytestmark = pytest.mark.skipif(
    not (config.MODELS_DIR / "ner_dataturks_sm").exists(),
    reason="Requiere el modelo NER (correr scripts/train_ner.py).",
)

CV = (
    "John Smith\n"
    "Senior Java Developer at Acme Corp\n"
    "Work experience: Java, Spring, SQL, Hibernate, communication skills\n"
    "Education: Computer Science, University of Cordoba, 2015\n"
    "Skills: Java, SQL, Spring, Hibernate\n"
    "Email: john.smith@example.com\n"
)
OFERTA = (
    "We are looking for a Java developer with SQL, Spring and strong "
    "communication skills to join our backend team."
)

CV_DOCENTE = (
    "Laura Gomez\n"
    "Biology Teacher\n"
    "Email: laura.gomez@example.com\n"
    "Work Experience\n"
    "Biology Teacher, Colegio San Martin, 2019-2024. Planned lessons and taught science.\n"
    "Education\n"
    "Bachelor in Biology, 2018.\n"
    "Skills\n"
    "teaching, planning, communication.\n"
)

OFERTA_MOBILE = (
    "We are seeking a Senior Quality Engineer in Mobile. "
    "Requirements: 7+ years of mobile app automation, Espresso, XCUITest, "
    "Java, Swift, Android, iOS, regression testing, CI and API testing. "
    "Responsibilities: automate mobile tests and maintain test frameworks."
)


def test_analizar_devuelve_las_cuatro_dimensiones():
    resultado = analizar(CV, OFERTA, motor_similitud="tfidf")

    assert 0 <= resultado["puntaje_global"] <= 100
    dimensiones = resultado["dimensiones"]
    assert set(dimensiones) == {"parseabilidad", "secciones", "keyword_gap", "similitud"}

    for dimension in dimensiones.values():
        assert 0 <= dimension["puntaje"] <= 100


def test_analizar_detecta_habilidades_compartidas():
    resultado = analizar(CV, OFERTA, motor_similitud="tfidf")
    gap = resultado["dimensiones"]["keyword_gap"]

    assert "java" in gap["coincidencias"]
    assert "java" not in gap["faltantes"]


def test_separa_calidad_ats_de_compatibilidad():
    resultado = analizar(CV_DOCENTE, OFERTA_MOBILE, motor_similitud="tfidf")

    assert resultado["puntaje_global"] == resultado["puntaje_match"]
    assert resultado["puntaje_ats"] >= 80
    assert resultado["puntaje_match"] < 20
    assert resultado["nivel_match"] == "bajo"
    assert resultado["dimensiones"]["keyword_gap"]["faltantes"]
