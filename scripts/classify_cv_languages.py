"""Clasificacion de idioma y parseabilidad ATS de CVs en PDF/JPG.

Este script recorre un directorio con curriculums (tipicamente el dataset
``amineipad/resumecv-dataset``, con 66 PDF y 34 JPG mezclando frances e ingles)
y produce un reporte que responde DOS preguntas independientes por archivo:

1. **¿En que idioma esta?** -> ``en`` / ``fr`` / ``es`` / ``other`` / ``unknown``
   / ``sin_texto``.
2. **¿Un ATS podria leerlo?** (``ats_parseable``): se usa la definicion
   **oficial** del proyecto, ``src.parsing.quality.is_parseable`` (>=30
   palabras y ratio alfanumerico >=0.5). Un PDF escaneado o un JPG dan
   ``False`` porque no hay texto que parsear.

La distincion entre idioma y parseabilidad es deliberada: el OCR solo se usa
para *adivinar el idioma* de un archivo sin capa de texto, jamas para
"aprobar" el archivo. La ausencia de capa de texto es, precisamente, la
evidencia de que un ATS fallaria.

Este script es **auxiliar de curacion de datos**; no forma parte del motor de
diagnostico oficial (ver ``scripts/README.md``).

Uso
---
    python scripts/classify_cv_languages.py \
        --input data/raw/cvs_pdf_fr_en \
        --output data/processed/cv_language_report.csv \
        --keep-en-dir data/processed/cvs_en --copy --ocr

Salida
------
Un CSV con una fila por archivo y un resumen impreso por consola.
Ver ``scripts/README.md`` para el detalle de columnas.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parsing.pdf_reader import read_pdf
from src.parsing.quality import is_parseable
from src.utils.seeds import set_global_seed

LOGGER = logging.getLogger("classify_cv_languages")

# ---------------------------------------------------------------------------
# Constantes de configuracion (documentadas para la catedra)
# ---------------------------------------------------------------------------

DEFAULT_MIN_CHARS = 50
"""Menos de esta cantidad de caracteres se considera "sin capa de texto".

Se usa para la columna ``tiene_capa_texto`` y para no intentar detectar
idioma sobre texto casi vacio. La parseabilidad ATS NO usa este umbral:
usa ``src.parsing.quality.is_parseable`` (>=30 palabras y ratio
alfanumerico >=0.5), la definicion oficial del proyecto.
"""

MIN_CONFIDENCE = 0.65
"""Confianza minima de ``lingua`` para aceptar el idioma detectado.

Por debajo de este valor, o si el detector no esta seguro, el archivo se marca
como ``review`` (para revision manual) en lugar de arriesgar una clasificacion.
"""

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS

LANGUAGES = ["EN", "FR", "ES"]
"""Idiomas de interes para el proyecto (ingles, frances, espanol)."""

# Mapeo del codigo ISO de ``lingua`` a la etiqueta corta que usamos nosotros.
ISO_TO_LABEL = {
    "EN": "en",
    "FR": "fr",
    "ES": "es",
}


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------


@dataclass
class Classification:
    """Resultado de clasificar un unico archivo."""

    archivo: str
    extension: str
    paginas: str = ""
    caracteres_extraidos: int = 0
    tiene_capa_texto: bool = False
    ats_parseable: bool = False
    idioma: str = "unknown"
    confianza: float = 0.0
    metodo: str = "ninguno"
    estado: str = "ok"
    decision: str = "review"
    notas: str = ""
    ruta_origen: str = ""

    def to_row(self) -> dict:
        """Devuelve la fila como dict sin la ruta interna (no va al CSV)."""
        data = asdict(self)
        data.pop("ruta_origen", None)
        return data


# ---------------------------------------------------------------------------
# Deteccion de idioma
# ---------------------------------------------------------------------------


@dataclass
class LanguageDetector:
    """Envoltura de ``lingua`` con fallback explicito.

    Si ``lingua`` no esta instalada, ``available`` queda en ``False`` y todos
    los archivos se marcan como ``unknown`` (el script sigue funcionando y el
    reporte lo deja claro en la columna ``notas``).
    """

    _detector: object | None = None
    available: bool = False
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        try:
            from lingua import Language, LanguageDetectorBuilder

            self._detector = (
                LanguageDetectorBuilder.from_languages(
                    Language.ENGLISH, Language.FRENCH, Language.SPANISH
                )
                .with_preloaded_language_models()
                .build()
            )
            self.available = True
        except Exception as exc:  # pragma: no cover - depende del entorno
            self.unavailable_reason = f"lingua no disponible: {exc}"
            self.available = False

    def detect(self, text: str) -> tuple[str, float]:
        """Detecta el idioma de ``text``.

        Returns:
            ``(idioma, confianza)`` donde ``idioma`` es ``en``/``fr``/``es`` o
            ``unknown`` si no hay senal suficiente.
        """
        if not self.available or not text.strip():
            return "unknown", 0.0

        values = self._detector.compute_language_confidence_values(text)  # type: ignore[union-attr]
        if not values:
            return "unknown", 0.0

        best = values[0]
        label = ISO_TO_LABEL.get(best.language.iso_code_639_1.name, "unknown")
        return label, float(best.value)


# ---------------------------------------------------------------------------
# Extraccion de texto por formato
# ---------------------------------------------------------------------------


def extract_pdf_text(path: Path) -> tuple[str, int]:
    """Extrae texto de un PDF con el lector oficial del proyecto.

    Usa ``src.parsing.pdf_reader.read_pdf`` (pdfminer.six + pdfplumber), el
    mismo lector que usa el motor de diagnostico, para que esta clasificacion
    y el producto midan sobre el mismo texto.

    Returns:
        ``(texto, paginas)``. El texto viene vacio si el PDF no tiene capa
        de texto (escaneado).
    """
    lectura = read_pdf(path)
    if lectura["error"]:
        raise RuntimeError(lectura["error"])
    return lectura["texto"], len(lectura["paginas"])


def extract_image_text(path: Path) -> str:
    """Extrae texto de una imagen via OCR (``pytesseract``).

    Solo se usa para estimar el idioma, nunca para marcar el archivo como
    parseable. Requiere el binario del sistema ``tesseract`` instalado.

    Returns:
        Texto reconocido (puede venir vacio si el OCR falla).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta pytesseract/Pillow. Instala requirements.txt."
        ) from exc

    with Image.open(path) as img:
        return pytesseract.image_to_string(img, lang="eng+fra+spa")


# ---------------------------------------------------------------------------
# Clasificacion de un archivo
# ---------------------------------------------------------------------------


def classify_file(
    path: Path,
    detector: LanguageDetector,
    min_chars: int = DEFAULT_MIN_CHARS,
    use_ocr: bool = False,
) -> Classification:
    """Clasifica un unico archivo (PDF o imagen).

    Aplica las reglas documentadas: primero extrae texto, decide la
    parseabilidad por presencia de capa de texto, y recien despues intenta
    detectar el idioma (con OCR opcional cuando no hay capa de texto).
    """
    result = Classification(
        archivo=path.name,
        extension=path.suffix.lower(),
        ruta_origen=str(path),
    )
    ext = result.extension

    if ext not in SUPPORTED_EXTENSIONS:
        result.estado = "ignorado"
        result.decision = "review"
        result.notas = "extension no soportada"
        return result

    # --- Extraccion de texto -------------------------------------------------
    texto = ""
    if ext in PDF_EXTENSIONS:
        try:
            texto, paginas = extract_pdf_text(path)
            result.paginas = str(paginas)
            result.metodo = "texto_pdf"
        except Exception as exc:
            result.estado = "error"
            result.decision = "review"
            result.notas = f"fallo al leer PDF: {exc}"
            return result
    else:  # imagen
        result.metodo = "ninguno"  # las imagenes no tienen capa de texto
        if use_ocr:
            try:
                texto = extract_image_text(path)
                result.metodo = "ocr"
            except Exception as exc:
                result.notas = f"OCR fallo: {exc}"

    result.caracteres_extraidos = len(texto.strip())

    # ``tiene_capa_texto`` es solo "hay texto extraible"; la parseabilidad
    # oficial la decide ``is_parseable`` (palabras + ratio alfanumerico).
    # Las imagenes nunca son parseables por un ATS, por diseno.
    result.tiene_capa_texto = (
        ext in PDF_EXTENSIONS and result.caracteres_extraidos >= min_chars
    )
    result.ats_parseable = ext in PDF_EXTENSIONS and is_parseable(texto)

    # --- Deteccion de idioma -------------------------------------------------
    if result.caracteres_extraidos == 0:
        result.idioma = "sin_texto"
        result.estado = "needs_ocr" if ext in PDF_EXTENSIONS else "imagen"
        result.decision = "needs_ocr"
        if ext in IMAGE_EXTENSIONS and not use_ocr:
            result.notas = (
                result.notas + "; " if result.notas else ""
            ) + "imagen sin OCR (usa --ocr para estimar idioma)"
        return result

    idioma, confianza = detector.detect(texto)
    result.idioma = idioma
    result.confianza = round(confianza, 4)

    if not detector.available:
        result.notas = (result.notas + "; " if result.notas else "") + detector.unavailable_reason

    # --- Decision final ------------------------------------------------------
    baja_confianza = confianza < MIN_CONFIDENCE
    if idioma == "unknown" or baja_confianza:
        result.estado = "baja_confianza"
        result.decision = "review"
    elif idioma == "en":
        result.estado = "ok"
        result.decision = "keep_en"
    elif idioma in {"fr", "es"}:
        result.estado = "ok"
        result.decision = f"discard_{idioma}"
    else:
        result.estado = "ok"
        result.decision = "discard_other"

    return result


# ---------------------------------------------------------------------------
# Recorrido del directorio y escritura de salida
# ---------------------------------------------------------------------------


def iter_files(input_dir: Path) -> Iterable[Path]:
    """Recorre recursivamente ``input_dir`` y devuelve archivos soportados."""
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def write_report(rows: list[Classification], output: Path) -> None:
    """Escribe el reporte CSV con ``pandas`` (o csv planos si no esta)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    dict_rows = [r.to_row() for r in rows]
    try:
        import pandas as pd

        pd.DataFrame(dict_rows).to_csv(output, index=False)
    except ImportError:  # pragma: no cover
        import csv

        with output.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(dict_rows[0].keys()))
            writer.writeheader()
            writer.writerows(dict_rows)


def copy_english_pdfs(
    rows: list[Classification], target_dir: Path, mode: str
) -> int:
    """Copia (o enlaza) los PDF en ingles a ``target_dir``.

    Args:
        mode: ``"copy"`` o ``"symlink"``.

    Returns:
        Cantidad de archivos procesados.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in rows:
        if row.decision != "keep_en":
            continue
        src = Path(row.ruta_origen)
        dst = target_dir / src.name
        if dst.exists():
            dst.unlink()
        if mode == "symlink":
            dst.symlink_to(src.resolve())
        else:
            shutil.copy2(src, dst)
        count += 1
    return count


def summarize(rows: list[Classification]) -> str:
    """Construye un resumen legible del reporte."""
    total = len(rows)
    pdf = sum(1 for r in rows if r.extension in PDF_EXTENSIONS)
    img = sum(1 for r in rows if r.extension in IMAGE_EXTENSIONS)
    parseable = sum(1 for r in rows if r.ats_parseable)
    con_texto = sum(1 for r in rows if r.tiene_capa_texto)
    por_idioma: dict[str, int] = {}
    por_decision: dict[str, int] = {}
    for r in rows:
        por_idioma[r.idioma] = por_idioma.get(r.idioma, 0) + 1
        por_decision[r.decision] = por_decision.get(r.decision, 0) + 1

    lines = [
        "=" * 60,
        "RESUMEN DE CLASIFICACION DE CVs",
        "=" * 60,
        f"Total de archivos analizados : {total}",
        f"  - PDF                      : {pdf}",
        f"  - Imagenes (JPG/PNG/...)   : {img}",
        f"Con capa de texto               : {con_texto}",
        f"Parseables por ATS (oficial)    : {parseable} "
        f"({(parseable / total * 100) if total else 0:.1f}%)",
        f"No parseables                   : {total - parseable}",
        "-" * 60,
        "Idioma detectado:",
    ]
    for lang, n in sorted(por_idioma.items(), key=lambda x: -x[1]):
        lines.append(f"  {lang:<10}: {n}")
    lines.append("-" * 60)
    lines.append("Decision:")
    for dec, n in sorted(por_decision.items(), key=lambda x: -x[1]):
        lines.append(f"  {dec:<12}: {n}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Clasifica CVs en PDF/JPG por idioma y por parseabilidad ATS."
        )
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="Carpeta con los CVs."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/cv_language_report.csv"),
        help="Ruta del CSV de salida.",
    )
    parser.add_argument(
        "--keep-en-dir",
        type=Path,
        default=None,
        help="Carpeta donde juntar los PDF en ingles.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--copy",
        action="store_true",
        help="Copia los PDF en ingles a --keep-en-dir (por defecto).",
    )
    group.add_argument(
        "--symlink",
        action="store_true",
        help="Enlaza (symlink) los PDF en ingles en lugar de copiarlos.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Usa OCR en imagenes/escaneados para estimar el idioma.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=DEFAULT_MIN_CHARS,
        help=(
            f"Minimo de caracteres para 'tiene_capa_texto' (default {DEFAULT_MIN_CHARS}). "
            "No define la parseabilidad ATS: esa usa is_parseable."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla global (default 42) para reproducibilidad.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Logging detallado."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    set_global_seed(args.seed)

    input_dir: Path = args.input
    if not input_dir.is_dir():
        LOGGER.error("No existe la carpeta de entrada: %s", input_dir)
        print(f"ERROR: no existe la carpeta {input_dir}", file=sys.stderr)
        return 2

    detector = LanguageDetector()
    if not detector.available:
        LOGGER.warning(detector.unavailable_reason)

    files = list(iter_files(input_dir))
    if not files:
        print(f"ERROR: no se encontraron PDF/imagenes en {input_dir}", file=sys.stderr)
        return 2

    print(f"Analizando {len(files)} archivos en {input_dir} ...")
    rows: list[Classification] = []
    for i, path in enumerate(files, start=1):
        rows.append(
            classify_file(
                path, detector, min_chars=args.min_chars, use_ocr=args.ocr
            )
        )
        if i % 25 == 0 or i == len(files):
            print(f"  ... {i}/{len(files)}")

    write_report(rows, args.output)
    print(f"\nReporte escrito en: {args.output}")

    mode = "symlink" if args.symlink else "copy"
    target = args.keep_en_dir
    if target is not None:
        n = copy_english_pdfs(rows, target, mode)
        print(f"PDF en ingles ({mode}) -> {target}: {n} archivos")

    print()
    print(summarize(rows))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
