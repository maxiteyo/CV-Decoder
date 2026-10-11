"""Dimensión 1 del diagnóstico: ¿se puede leer el texto de un PDF?

Un ATS necesita poder extraer texto "limpio" del PDF. Si el PDF es una imagen
escaneada, o tiene columnas/tablas raras, el texto sale vacío o desordenado y el
CV se descarta. Acá leemos el PDF y medimos la calidad del texto obtenido.
"""

from pathlib import Path

import pdfplumber


def extract_pdf_pages(path: str | Path) -> list[dict]:
    """Devuelve el texto de cada página del PDF."""
    pages: list[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"pagina": index, "texto": text})
    return pages


def extract_pdf_text(path: str | Path, separator: str = "\n") -> str:
    """Devuelve todo el texto del PDF, página por página."""
    pages = extract_pdf_pages(path)
    return separator.join(page["texto"] for page in pages).strip()
