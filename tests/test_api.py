"""Pruebas de la API (Etapa C).

Se generan PDFs de prueba al vuelo (no dependen de `data/`, que no se versiona):

  - un CV legible con las 4 secciones,
  - un PDF escaneado (solo imagen, sin capa de texto),
  - un PDF roto.

Se ejecutan con:
    .venv/bin/python -m pytest -q
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF
from PIL import Image, ImageDraw

from src.api.main import MAX_CARACTERES_OFERTA, MAX_PDF_BYTES, app
from src.core.diagnostico import PESOS_POR_DEFECTO

URL = "/api/v1/analyze-cv"

CV_TEXTO = """Ana Perez
ana.perez@example.com | +54 11 5555-1234 | Buenos Aires

WORK EXPERIENCE
Data Analyst at Acme Corp 2019-2024
Built dashboards with Python and SQL for the sales team.

EDUCATION
BSc in Computer Science, University of Buenos Aires, 2019

SKILLS
Python, SQL, Excel, Communication
"""

OFERTA = """We are looking for a Data Analyst with strong Python and SQL skills to join our team.
You will build dashboards, work with stakeholders and communicate findings clearly.
Experience with Excel is required. Knowledge of Docker is a plus.
Project management experience is valued."""


@pytest.fixture(scope="session")
def client():
    """Cliente HTTP de pruebas; levanta la app una vez (carga el modelo)."""
    with TestClient(app) as cliente:
        yield cliente


def _pdf_con_texto(ruta: Path, texto: str = CV_TEXTO) -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for linea in texto.splitlines():
        pdf.multi_cell(0, 6, linea or " ", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(ruta))
    return ruta


def _pdf_escaneado(ruta: Path) -> Path:
    """Una página que es solo una imagen: no tiene capa de texto."""
    imagen = Image.new("RGB", (1240, 1754), "white")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.text((100, 100), "Curriculum escaneado", fill="black")
    ruta_imagen = ruta.with_suffix(".png")
    imagen.save(ruta_imagen)

    pdf = FPDF()
    pdf.add_page()
    pdf.image(str(ruta_imagen), x=5, y=5, w=200)
    pdf.output(str(ruta))
    return ruta


def _error(respuesta) -> dict:
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"error"}, cuerpo
    assert cuerpo["error"]["codigo"]
    assert cuerpo["error"]["mensaje"]
    assert cuerpo["error"]["sugerencia"]
    return cuerpo["error"]


# --- Sistema ---------------------------------------------------------------


def test_health(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["motor_oficial"] == "tfidf"
    assert cuerpo["modelo_entidades"]


def test_raiz(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert respuesta.json()["endpoint"] == URL


def test_openapi_disponible(client):
    respuesta = client.get("/openapi.json")
    assert respuesta.status_code == 200
    assert URL in respuesta.json()["paths"]


# --- Camino feliz ----------------------------------------------------------


def test_diagnostico_completo(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
            data={"oferta": OFERTA},
        )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert 0 <= cuerpo["puntaje_global"] <= 100
    assert cuerpo["metadatos"]["archivo"] == "cv.pdf"
    assert cuerpo["metadatos"]["paginas"] >= 1
    assert cuerpo["metadatos"]["palabras"] >= 20
    assert cuerpo["metadatos"]["motor_similitud"] == "tfidf"
    assert cuerpo["metadatos"]["tiempo_ms"] >= 0

    dimensiones = cuerpo["dimensiones"]
    assert dimensiones["parseabilidad"]["puntaje"] == 100.0

    secciones = dimensiones["secciones"]
    assert secciones["puntaje"] == 100.0
    assert all(secciones["detalle"].values())
    assert secciones["faltantes"] == []

    gap = dimensiones["keyword_gap"]
    assert {"python", "sql"} <= set(gap["coincidencias"])
    assert "docker" in gap["faltantes"]
    assert gap["total_cv"] >= 2
    assert gap["total_oferta"] >= 3

    similitud = dimensiones["similitud"]
    assert similitud["motor"] == "tfidf"
    assert 0 <= similitud["crudo"] <= 1
    assert 0 <= similitud["puntaje"] <= 100

    # El global tiene que ser la suma ponderada de las 4 dimensiones.
    esperado = (
        PESOS_POR_DEFECTO["similitud"] * similitud["puntaje"]
        + PESOS_POR_DEFECTO["secciones"] * secciones["puntaje"]
        + PESOS_POR_DEFECTO["keyword_gap"] * gap["puntaje"]
        + PESOS_POR_DEFECTO["parseabilidad"] * dimensiones["parseabilidad"]["puntaje"]
    )
    assert cuerpo["puntaje_global"] == pytest.approx(esperado, abs=0.11)


def test_no_deja_archivos_temporales(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    patron = "cv_decoder_*.pdf"
    antes = set(Path(tempfile.gettempdir()).glob(patron))

    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
            data={"oferta": OFERTA},
        )

    assert respuesta.status_code == 200
    assert set(Path(tempfile.gettempdir()).glob(patron)) == antes


def test_nombre_de_archivo_se_sanea(client, tmp_path):
    """Si el cliente manda una ruta, solo se devuelve el nombre del archivo."""
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("../../carpeta/cv.pdf", archivo, "application/pdf")},
            data={"oferta": OFERTA},
        )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["metadatos"]["archivo"] == "cv.pdf"


# --- Errores controlados ---------------------------------------------------


def test_rechaza_archivo_que_no_es_pdf(client):
    respuesta = client.post(
        URL,
        files={"cv": ("cv.txt", b"no soy un pdf", "text/plain")},
        data={"oferta": OFERTA},
    )
    assert respuesta.status_code == 415
    assert _error(respuesta)["codigo"] == "FORMATO_NO_SOPORTADO"


def test_rechaza_pdf_falso(client):
    respuesta = client.post(
        URL,
        files={"cv": ("cv.pdf", b"no soy un pdf", "application/pdf")},
        data={"oferta": OFERTA},
    )
    assert respuesta.status_code == 415
    assert _error(respuesta)["codigo"] == "NO_ES_PDF"


def test_rechaza_archivo_vacio(client):
    respuesta = client.post(
        URL,
        files={"cv": ("cv.pdf", b"", "application/pdf")},
        data={"oferta": OFERTA},
    )
    assert respuesta.status_code == 400
    assert _error(respuesta)["codigo"] == "PDF_VACIO"


def test_rechaza_pdf_roto(client):
    respuesta = client.post(
        URL,
        files={"cv": ("cv.pdf", b"%PDF-1.4\ncontenido roto", "application/pdf")},
        data={"oferta": OFERTA},
    )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "PDF_ILEGIBLE"


def test_rechaza_pdf_escaneado(client, tmp_path):
    pdf = _pdf_escaneado(tmp_path / "escaneado.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("escaneado.pdf", archivo, "application/pdf")},
            data={"oferta": OFERTA},
        )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "PDF_SIN_TEXTO"


def test_rechaza_oferta_muy_corta(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
            data={"oferta": "Data Analyst"},
        )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "OFERTA_MUY_CORTA"


def test_rechaza_oferta_muy_larga(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    oferta = "palabra " * (MAX_CARACTERES_OFERTA // 8 + 10)
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
            data={"oferta": oferta},
        )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "OFERTA_MUY_LARGA"


def test_rechaza_pdf_demasiado_grande(client):
    respuesta = client.post(
        URL,
        files={"cv": ("cv.pdf", b"x" * (MAX_PDF_BYTES + 1), "application/pdf")},
        data={"oferta": OFERTA},
    )
    assert respuesta.status_code == 413
    assert _error(respuesta)["codigo"] == "PDF_MUY_GRANDE"


def test_falta_la_oferta(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
        )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "VALIDACION"
    assert "oferta" in respuesta.json()["error"]["mensaje"]


def test_motor_invalido(client, tmp_path):
    pdf = _pdf_con_texto(tmp_path / "cv.pdf")
    with open(pdf, "rb") as archivo:
        respuesta = client.post(
            URL,
            files={"cv": ("cv.pdf", archivo, "application/pdf")},
            data={"oferta": OFERTA, "motor": "motor_inventado"},
        )
    assert respuesta.status_code == 422
    assert _error(respuesta)["codigo"] == "VALIDACION"
