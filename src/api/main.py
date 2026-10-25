"""API REST del MVP (Etapa C): un PDF + una oferta -> diagnóstico en JSON.

Un solo endpoint productivo (`POST /api/v1/analyze-cv`) más dos de sistema
(`/` y `/health`). La API no guarda nada: escribe el PDF en un archivo temporal,
lo lee, lo borra y devuelve el resultado.

Cómo levantarla:
    .venv/bin/uvicorn src.api.main:app --reload
    http://127.0.0.1:8000/docs   (Swagger: se puede probar desde el navegador)
"""

from __future__ import annotations

import logging
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src import config
from src.api.schemas import (
    DiagnosticoOut,
    ErrorOut,
    MotorSimilitud,
    SaludOut,
)
from src.core.diagnostico import analizar
from src.core.nlp_engine import MODELO_ENTIDADES, get_nlp, get_skill_matcher
from src.models.similarity import get_similarity_model
from src.parsing.pdf_reader import read_pdf
from src.parsing.quality import is_parseable, text_quality

VERSION = "0.1.0"
MAX_PDF_MB = 5
MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024
MIN_PALABRAS_OFERTA = 20
MAX_CARACTERES_OFERTA = 20_000

logger = logging.getLogger("cv_decoder.api")

# Respuestas de error documentadas en Swagger (mismo cuerpo para todas).
RESPUESTAS_ERROR = {
    codigo: {"model": ErrorOut, "description": descripcion}
    for codigo, descripcion in {
        400: "Pedido inválido (por ejemplo, archivo vacío)",
        413: f"El PDF supera los {MAX_PDF_MB} MB",
        415: "El archivo no es un PDF",
        422: "PDF ilegible/escaneado u oferta demasiado corta",
        500: "Error inesperado del servidor",
    }.items()
}


class ErrorAPI(Exception):
    """Error controlado con un cuerpo estable: código, mensaje y sugerencia."""

    def __init__(self, status_code: int, codigo: str, mensaje: str, sugerencia: str):
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.sugerencia = sugerencia
        super().__init__(mensaje)


def _cuerpo_error(codigo: str, mensaje: str, sugerencia: str) -> dict:
    return {"error": {"codigo": codigo, "mensaje": mensaje, "sugerencia": sugerencia}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo una sola vez al arrancar (no en la primera consulta)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    inicio = time.perf_counter()

    # El modelo entrenado no se versiona (pesa varios MB): si falta, el error
    # tiene que decir qué hacer y no un "FileNotFoundError" críptico.
    ruta_modelo = config.MODELS_DIR / MODELO_ENTIDADES
    if not ruta_modelo.exists():
        raise RuntimeError(
            f"No se encontró el modelo de entidades en {ruta_modelo}. "
            "Entrenalo con: .venv/bin/python scripts/train_ner.py (ver README)."
        )

    get_nlp()
    get_skill_matcher()
    modelo = get_similarity_model("tfidf")
    # Primeras llamadas "en frío": spaCy compila y scikit-learn se importa
    # (varios segundos). Se hacen acá para que la primera consulta real no las pague.
    get_nlp()("warm up")
    modelo.similitud("python sql", "python sql")
    logger.info("Modelos cargados y calentados en %.2f s", time.perf_counter() - inicio)
    yield


app = FastAPI(
    title="CV-Decoder API",
    version=VERSION,
    description=(
        "Diagnóstico automático de un CV en PDF contra una oferta laboral.\n\n"
        "Devuelve un puntaje global (0-100) y cuatro dimensiones: "
        "**parseabilidad**, **secciones**, **brecha de habilidades** y **similitud**.\n\n"
        "Probar desde `POST /api/v1/analyze-cv` → **Try it out**."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Diagnóstico",
            "description": "Analiza un CV contra una oferta y devuelve el JSON de 4 dimensiones.",
        },
        {
            "name": "Sistema",
            "description": "Estado del servicio y atajos de documentación.",
        },
    ],
)


@app.exception_handler(ErrorAPI)
async def manejar_error_api(request: Request, exc: ErrorAPI) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_cuerpo_error(exc.codigo, exc.mensaje, exc.sugerencia),
    )


@app.exception_handler(RequestValidationError)
async def manejar_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    campos = ", ".join(str(error["loc"][-1]) for error in exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "codigo": "VALIDACION",
                "mensaje": f"Faltan o son inválidos estos campos: {campos}.",
                "sugerencia": "Revisá la documentación de /docs: el PDF va en 'cv' y el texto en 'oferta'.",
                "detalles": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=_cuerpo_error(
            "ERROR_INTERNO",
            "Ocurrió un error inesperado al procesar el CV.",
            "Volvé a intentarlo. Si persiste, revisá los logs del servidor.",
        ),
    )


def _procesar_pdf(ruta: Path, oferta: str, motor: str) -> tuple[dict, dict]:
    """Parte pesada (bloqueante) del endpoint: leer el PDF y diagnosticarlo.

    Se ejecuta en un hilo aparte para no bloquear el bucle de la API mientras
    pdfminer y spaCy trabajan.
    """
    leido = read_pdf(ruta)

    if leido["error"]:
        logger.warning("PDF ilegible: %s", leido["error"])
        raise ErrorAPI(
            422,
            "PDF_ILEGIBLE",
            "No se pudo abrir el PDF: puede estar dañado o protegido con contraseña.",
            "Abrilo en un lector de PDF y volvé a guardarlo. Si tiene contraseña, quitásela.",
        )

    if not is_parseable(leido["texto"]):
        calidad = text_quality(leido["texto"])
        raise ErrorAPI(
            422,
            "PDF_SIN_TEXTO",
            (
                "El PDF no tiene texto usable "
                f"({calidad['palabras']} palabras y {leido['imagenes']} imágenes detectadas)."
            ),
            "Es un escaneo o una foto. Subí un PDF con capa de texto (no una imagen) "
            "o pasalo primero por un OCR.",
        )

    resultado = analizar(leido["texto"], oferta, motor_similitud=motor)
    return leido, resultado


@app.post(
    "/api/v1/analyze-cv",
    response_model=DiagnosticoOut,
    responses=RESPUESTAS_ERROR,
    tags=["Diagnóstico"],
    summary="Diagnosticar un CV contra una oferta",
    description=(
        "Recibe el PDF del CV y el texto de la oferta (multipart/form-data). "
        "El PDF no se guarda: se procesa en un archivo temporal y se borra.\n\n"
        "El motor oficial es `tfidf`. Los otros dos (`embeddings` y "
        "`embeddings_fragmentos`) se ofrecen para comparar y tardan más."
    ),
)
async def analyze_cv(
    cv: Annotated[UploadFile, File(description=f"PDF del CV (máximo {MAX_PDF_MB} MB)")],
    oferta: Annotated[str, Form(description="Texto completo de la oferta laboral")],
    motor: Annotated[
        MotorSimilitud,
        Form(description="Motor de similitud; el oficial y más rápido es 'tfidf'"),
    ] = "tfidf",
) -> DiagnosticoOut:
    inicio = time.perf_counter()
    # Algunos clientes mandan la ruta completa; se guarda solo el nombre.
    nombre = Path((cv.filename or "cv.pdf").replace("\\", "/")).name

    if not nombre.lower().endswith(".pdf"):
        await cv.close()
        raise ErrorAPI(
            415,
            "FORMATO_NO_SOPORTADO",
            f"El archivo '{nombre}' no tiene extensión .pdf.",
            "Convertí el CV a PDF y volvé a subirlo.",
        )

    contenido = await cv.read(MAX_PDF_BYTES + 1)
    await cv.close()

    if not contenido:
        raise ErrorAPI(400, "PDF_VACIO", "El archivo está vacío.", "Elegí un PDF que tenga contenido.")

    if len(contenido) > MAX_PDF_BYTES:
        raise ErrorAPI(
            413,
            "PDF_MUY_GRANDE",
            f"El PDF supera el máximo de {MAX_PDF_MB} MB.",
            "Comprimí el PDF o reducí su tamaño (por ejemplo, bajando la calidad de las imágenes).",
        )

    if not contenido.lstrip().startswith(b"%PDF"):
        raise ErrorAPI(
            415,
            "NO_ES_PDF",
            "El archivo no parece un PDF válido (no empieza con la firma %PDF).",
            "Asegurate de subir el archivo .pdf original y no una captura de pantalla.",
        )

    oferta = oferta.strip()
    palabras_oferta = len(oferta.split())
    if palabras_oferta < MIN_PALABRAS_OFERTA:
        raise ErrorAPI(
            422,
            "OFERTA_MUY_CORTA",
            f"La oferta tiene {palabras_oferta} palabras (mínimo {MIN_PALABRAS_OFERTA}).",
            "Pegá el texto completo de la oferta, no solo el título del puesto.",
        )
    if len(oferta) > MAX_CARACTERES_OFERTA:
        raise ErrorAPI(
            422,
            "OFERTA_MUY_LARGA",
            f"La oferta supera los {MAX_CARACTERES_OFERTA} caracteres.",
            "Pegá solo la descripción del puesto; si es un archivo enorme, recortalo.",
        )

    # El PDF se escribe en un archivo temporal porque pdfminer/pdfplumber leen
    # desde disco. Se borra siempre, incluso si el diagnóstico falla.
    temporal = tempfile.NamedTemporaryFile(prefix="cv_decoder_", suffix=".pdf", delete=False)
    ruta = Path(temporal.name)
    try:
        with temporal:
            temporal.write(contenido)
        leido, resultado = await run_in_threadpool(_procesar_pdf, ruta, oferta, motor)
    finally:
        ruta.unlink(missing_ok=True)

    respuesta = {
        "puntaje_global": resultado["puntaje_global"],
        "metadatos": {
            "archivo": nombre,
            "paginas": len(leido["paginas"]),
            "palabras": len(leido["texto"].split()),
            "motor_similitud": resultado["dimensiones"]["similitud"]["motor"],
            "tiempo_ms": int((time.perf_counter() - inicio) * 1000),
        },
        "dimensiones": resultado["dimensiones"],
    }
    return DiagnosticoOut.model_validate(respuesta)


@app.get("/health", response_model=SaludOut, tags=["Sistema"], summary="Estado del servicio")
def health() -> SaludOut:
    return SaludOut(
        estado="ok",
        version=VERSION,
        modelo_entidades=MODELO_ENTIDADES,
        motor_oficial="tfidf",
    )


@app.get("/", include_in_schema=False)
def raiz() -> dict:
    return {
        "nombre": "CV-Decoder API",
        "version": VERSION,
        "documentacion": "/docs",
        "endpoint": "/api/v1/analyze-cv",
        "salud": "/health",
    }
