"""Dimensión 1 del diagnóstico: ¿se puede leer el texto de un PDF?

Un ATS necesita poder extraer texto "limpio" del PDF. Si el PDF es una imagen
escaneada, o tiene columnas/tablas raras, el texto sale vacío o desordenado y el
CV se descarta. Acá leemos el PDF y medimos la calidad del texto obtenido.
"""

from pathlib import Path

import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text


def extract_pdf_pages(path: str | Path) -> list[dict]:
    """Devuelve la estructura y el texto de cada página del PDF.

    Se usa pdfplumber porque expone las imágenes y los caracteres de cada
    página (sirve para detectar escaneos). Ojo: su texto pega palabras cuando
    el PDF no tiene espacios explícitos, por eso el texto "oficial" del CV sale
    de `extract_pdf_text` (pdfminer).

    Un PDF armado solo con imágenes puede no tener páginas legibles para el
    lector (0 páginas): en ese caso devuelve una lista vacía.
    """
    pages: list[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                {
                    "pagina": index,
                    "texto": text,
                    "imagenes": len(page.images),
                    "caracteres": len(page.chars),
                }
            )
    return pages


def extract_pdf_text(path: str | Path, separator: str = "\n") -> str:
    """Devuelve todo el texto del PDF.

    Se prefiere pdfminer.six (respeta los espacios entre palabras) y se usa
    pdfplumber como respaldo si pdfminer no recupera nada.
    """
    try:
        texto = pdfminer_extract_text(str(path)).strip()
    except Exception:
        texto = ""
    if texto:
        return texto
    return separator.join(page["texto"] for page in extract_pdf_pages(path)).strip()


def read_pdf(path: str | Path) -> dict:
    """Lee un PDF sin lanzar excepciones (sirve para benchmarks y para la API).

    Devuelve:
        texto              : todo el texto extraído ("" si no se pudo leer nada).
        paginas            : lista de páginas (estructura + texto de pdfplumber).
        paginas_sin_texto  : cuántas páginas quedaron sin texto.
        imagenes           : cantidad de imágenes detectadas (señal de escaneo).
        error              : None si salió bien; si no, el tipo y mensaje.
    """
    try:
        paginas = extract_pdf_pages(path)
    except Exception as error:  # PDF corrupto, protegido o formato raro
        return {
            "texto": "",
            "paginas": [],
            "paginas_sin_texto": 0,
            "imagenes": 0,
            "error": f"{type(error).__name__}: {error}",
        }

    texto = extract_pdf_text(path)
    return {
        "texto": texto,
        "paginas": paginas,
        "paginas_sin_texto": sum(1 for page in paginas if not page["texto"].strip()),
        "imagenes": sum(page["imagenes"] for page in paginas),
        "error": None,
    }
