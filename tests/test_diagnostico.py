"""Pruebas del motor de diagnóstico (requieren el modelo NER entrenado)."""

from __future__ import annotations

import pytest

from src import config
from src.core.diagnostico import (
    analizar,
    bono_por_skills,
    cap_por_requisitos,
    normalizar_habilidad,
    segmentar_oferta,
)

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

CV_ARQUITECTO = (
    "Carlos Rossi\n"
    "Project Architect\n"
    "Email: carlos.rossi@example.com\n"
    "Work Experience\n"
    "Senior Project Architect, design and BIM with Revit, 2018-2024.\n"
    "Education\n"
    "Bachelor in Architecture, 2017.\n"
    "Skills\n"
    "Architectural Design, Revit, AutoCAD, Project Management.\n"
)

OFERTA_QA = """Responsibilities
Collaborate with Product, Design, and Development teams to understand product requirements and create test plans.
Requirements
3+ years of mobile app automation with Espresso, XCUITest, Java, Android and iOS.
Expertise in regression testing, accessibility and Agile practices.
Excellent communication skills.
Nice to have
Knowledge of Swift.
Benefits
Healthcare benefits and paid time off.
"""

CV_QA = (
    "Ana QA\n"
    "QA Engineer\n"
    "Email: ana@example.com\n"
    "Work Experience\n"
    "QA testing for mobile apps, 2020-2024.\n"
    "Education\n"
    "BSc Computer Science, 2019.\n"
    "Skills\n"
    "QA, communication.\n"
)

OFERTA_QA_SINONIMOS = (
    "Requirements: Quality Assurance experience, communication skills and mobile testing."
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


def test_segmentar_oferta_ignora_beneficios_y_tareas():
    secciones = segmentar_oferta(OFERTA_QA)

    assert "design" in secciones["responsabilidades"].lower()
    assert "java" in secciones["requisitos"].lower()
    assert "swift" in secciones["deseables"].lower()
    assert "healthcare" in secciones["beneficios"].lower()


def test_normaliza_sinonimos_de_oferta_y_cv():
    assert normalizar_habilidad("Quality Assurance") == "qa"
    assert normalizar_habilidad("communication skills") == "communication"
    assert normalizar_habilidad("CI/CD") == "ci"
    assert normalizar_habilidad("Regression Testing") == "regression"


def test_qa_matchea_quality_assurance_y_communication_skills():
    resultado = analizar(CV_QA, OFERTA_QA_SINONIMOS, motor_similitud="tfidf")
    requisitos = resultado["requisitos"]

    assert {"qa", "communication"} <= set(requisitos["obligatorios_cumplidos"])


def test_cap_gradual_por_requisitos_centrales():
    assert cap_por_requisitos(0) == 25.0
    assert cap_por_requisitos(14.9) == 25.0
    assert cap_por_requisitos(15) == 55.0
    assert cap_por_requisitos(29.9) == 55.0
    assert cap_por_requisitos(30) == 75.0
    assert cap_por_requisitos(49.9) == 75.0
    assert cap_por_requisitos(50) is None


def test_bono_por_solapamiento_fuerte_de_skills():
    assert bono_por_skills(0) == 0.0
    assert bono_por_skills(3) == 0.0
    assert bono_por_skills(4) == 32.0
    assert bono_por_skills(5) == 40.0
    assert bono_por_skills(10) == 40.0


def test_match_nunca_supera_cien_aunque_haya_bono():
    resultado = analizar(CV, OFERTA, motor_similitud="tfidf")

    assert resultado["puntaje_match"] <= 100
    assert resultado["puntaje_global"] == resultado["puntaje_match"]
    assert resultado["requisitos"]["bono_skills"] == 32.0


def test_arquitecto_contra_qa_queda_bajo_y_sin_falsos_positivos():
    resultado = analizar(CV_ARQUITECTO, OFERTA_QA, motor_similitud="tfidf")
    requisitos = resultado["requisitos"]
    gap = resultado["dimensiones"]["keyword_gap"]

    assert resultado["puntaje_ats"] >= 80
    assert resultado["puntaje_match"] < 20
    assert resultado["nivel_match"] == "bajo"
    assert requisitos["confianza"] == "alta"
    assert requisitos["cap_match"] == 25.0
    assert {"android", "espresso", "ios", "java", "xcuitest"} <= set(
        requisitos["obligatorios_faltantes"]
    )
    assert "swift" in requisitos["deseables_faltantes"]
    assert "design" not in gap["faltantes"]
    assert "healthcare" not in gap["faltantes"]


CV_ESTUDIANTE = (
    "Ana Student\n"
    "Computer Science Student\n"
    "Email: ana@example.com\n"
    "Education\n"
    "BSc Computer Science, 2025\n"
    "Skills\n"
    "Python, SQL, JavaScript, Git, communication.\n"
    "Projects\n"
    "Built web applications with Python and SQL.\n"
)

OFERTA_JUNIOR = (
    "Junior Software Developer\n"
    "Requirements: Python, SQL, JavaScript, Git and communication skills.\n"
    "Responsibilities: build web applications and learn from senior engineers.\n"
)

OFERTA_SENIOR = (
    "Senior Software Engineer\n"
    "Requirements: 5+ years of Python, SQL, JavaScript and Git. Leadership experience.\n"
    "Responsibilities: design distributed systems and mentor engineers.\n"
)

CV_POCA_EXPERIENCIA = (
    "Ana Junior\n"
    "Software Engineer\n"
    "Email: ana@example.com\n"
    "Work Experience\n"
    "Software Engineer, 2023-2024. Built software with Python and SQL.\n"
    "Skills\n"
    "Python, SQL.\n"
)

OFERTA_CINCO_ANIOS = (
    "Software Engineer\n"
    "Responsibilities: build software and maintain APIs.\n"
    "Requirements: 5+ years of Python and SQL.\n"
)


def test_match_usa_secciones_y_expone_detalle():
    resultado = analizar(CV_ARQUITECTO, OFERTA_QA, motor_similitud="tfidf")
    similitud = resultado["dimensiones"]["similitud"]

    assert similitud["fuente"] == "secciones"
    assert {"experiencia", "habilidades", "texto_completo", "secciones"} <= set(
        similitud["detalle"]
    )
    assert similitud["detalle"]["secciones"] == pytest.approx(
        0.60 * similitud["detalle"]["experiencia"]
        + 0.40 * similitud["detalle"]["habilidades"],
        abs=0.2,
    )
    assert similitud["puntaje"] == pytest.approx(
        0.20 * similitud["detalle"]["secciones"]
        + 0.80 * similitud["detalle"]["texto_completo"],
        abs=0.2,
    )


def test_seniority_penaliza_deficit_de_anios_sin_bonificar():
    resultado = analizar(CV_POCA_EXPERIENCIA, OFERTA_CINCO_ANIOS, motor_similitud="tfidf")
    seniority = resultado["seniority"]

    assert seniority["anos_cv"] == 1
    assert seniority["anos_pedidos"] == 5
    assert seniority["nivel_cv"] is None
    assert seniority["nivel_oferta"] is None
    assert seniority["ajuste"] == pytest.approx(0.84)

    suficiente = analizar(CV_ARQUITECTO, OFERTA_QA, motor_similitud="tfidf")["seniority"]
    assert suficiente["anos_cv"] == 6
    assert suficiente["anos_pedidos"] == 3
    assert suficiente["ajuste"] == 1.0


def test_seniority_no_compensa_skills_centrales_faltantes():
    resultado = analizar(CV_DOCENTE, OFERTA_MOBILE, motor_similitud="tfidf")

    assert resultado["seniority"]["anos_cv"] == 5
    assert resultado["seniority"]["anos_pedidos"] == 7
    assert resultado["seniority"]["ajuste"] < 1.0
    assert resultado["requisitos"]["cap_match"] == 25.0
    assert resultado["puntaje_match"] < 20


def test_estudiante_junior_supera_estudiante_senior_sin_quedar_en_bajo_extremo():
    junior = analizar(CV_ESTUDIANTE, OFERTA_JUNIOR, motor_similitud="tfidf")
    senior = analizar(CV_ESTUDIANTE, OFERTA_SENIOR, motor_similitud="tfidf")

    assert junior["puntaje_match"] >= 50
    assert senior["puntaje_match"] >= 20
    assert junior["puntaje_match"] > senior["puntaje_match"]


CV_SIN_SECCION_HABILIDADES = (
    "Ana Developer\n"
    "Software Developer\n"
    "Email: ana@example.com\n"
    "Work Experience\n"
    "Software Developer at Acme, 2020-2024. Built APIs with Python and SQL.\n"
    "Education\n"
    "BSc Computer Science, 2019\n"
)

OFERTA_PYTHON = (
    "Software Developer\n"
    "Responsibilities: build APIs and maintain internal tools.\n"
    "Requirements: Python, SQL and API development.\n"
)


def test_cv_sin_seccion_habilidades_matchea_alto_pero_baja_ats():
    resultado = analizar(
        CV_SIN_SECCION_HABILIDADES, OFERTA_PYTHON, motor_similitud="tfidf"
    )
    secciones = resultado["dimensiones"]["secciones"]

    assert secciones["detalle"]["Habilidades"] is False
    assert "Habilidades" in secciones["faltantes"]
    assert resultado["puntaje_ats"] < 100
    assert resultado["puntaje_match"] >= 50
