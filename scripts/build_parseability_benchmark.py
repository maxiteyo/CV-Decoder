"""Validacion complementaria de fidelidad de extraccion sobre PDFs reales.

Mide, de forma cuantitativa y reproducible, que tan fiel es el texto que
extrae el lector oficial (``src.parsing.pdf_reader.read_pdf``) respecto del
texto de referencia. Usa el dataset ``snehaanbhawal/resume-dataset`` (2.484 CV
reales de livecareer.com), que aporta para cada PDF:

* el archivo ``<ID>.pdf`` bajo ``data/<CATEGORY>/``, y
* su texto de referencia ``Resume_str`` en ``Resume/Resume.csv``.

Se reportan DOS senales:

* **`parseable_oficial`**: la definicion oficial del proyecto
  (``src.parsing.quality.is_parseable``: >=30 palabras y ratio alfanumerico
  >=0.5). Es la misma que usa el motor de diagnostico.
* **`token_f1`** (y ``parseable_similitud``): similitud de tokens contra el
  texto de referencia; valida que la extraccion no pierda contenido. Es una
  validacion complementaria, NO la metrica oficial de parseabilidad.

El texto de referencia proviene del HTML scrapeado, no del PDF, por lo que no
es *ground truth* perfecto: hay diferencias de espacios, orden y saltos. Por
eso se normaliza y se usa una medida tolerante (F1 de conjuntos de tokens), y
se documenta la limitacion. Ver ``docs/informe/metodologia-datos.md``.

Este script es **auxiliar**; no forma parte del motor de diagnostico oficial
(que se evalua con ``scripts/eval_parseability.py`` y se documenta en
``docs/informe/etapa-b-resultados.md``).

Uso
---
    python scripts/build_parseability_benchmark.py \
        --dataset-dir data/raw/cvs_parseabilidad \
        --output data/processed/parseability_report.csv

    # Prueba rapida con una muestra:
    python scripts/build_parseability_benchmark.py \
        --dataset-dir data/raw/cvs_parseabilidad --limit 50
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parsing.pdf_reader import read_pdf
from src.parsing.quality import is_parseable
from src.utils.seeds import set_global_seed

LOGGER = logging.getLogger("build_parseability_benchmark")

DEFAULT_THRESHOLD = 0.70
"""Umbral de similitud de tokens para considerar un PDF parseable.

0.70 significa que al menos ~70% de los tokens coinciden entre lo extraido y
lo esperado. Se elige como punto de partida y se debe **calibrar** mirando la
distribucion real (ver ``--report-percentiles``). Un umbral demasiado alto
marca como rotos PDFs que en realidad estan bien; demasiado bajo deja pasar
layouts que claramente fallan.
"""

NORMALIZE_WHITESPACE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Normalizacion y similitud
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normaliza texto para comparar sin ruido cosmetico.

    Pasos: quita acentos, pasa a minusculas, elimina todo lo que no sea
    letras/numeros/espacio y colapsa espacios multiples.
    """
    if not text:
        return ""
    # Descompone los acentos y los elimina (NFKD deja las marcas aparte).
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = NORMALIZE_WHITESPACE.sub(" ", text)
    return text.strip()


def token_f1(extracted: str, reference: str) -> float:
    """F1 de tokens (multiset) entre texto extraido y de referencia.

    Usa bolsas de tokens con conteo (``Counter``) e interseccion por minimo de
    frecuencias. Es tolerante al orden, adecuado porque ``Resume_str`` y el
    texto del PDF pueden ordenar los bloques distinto.

    Returns:
        Valor entre 0.0 y 1.0. 0.0 si alguno de los textos esta vacio.
    """
    tok_a = Counter(extracted.split())
    tok_b = Counter(reference.split())
    if not tok_a or not tok_b:
        return 0.0

    overlap = sum((tok_a & tok_b).values())
    precision = overlap / sum(tok_a.values())
    recall = overlap / sum(tok_b.values())
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def ratio_similarity(extracted: str, reference: str) -> float:
    """Similitud de secuencia (``difflib``) como metrica de respaldo.

    Penaliza el distinto orden de bloques, por lo que es mas estricta que
    ``token_f1``. Se reporta para tener una segunda senal.
    """
    if not extracted or not reference:
        return 0.0
    return SequenceMatcher(None, extracted, reference).ratio()


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------


@dataclass
class ParseResult:
    """Resultado de la validacion para un unico PDF."""

    id: str
    categoria: str
    archivo: str
    paginas: int = 0
    caracteres_pdf: int = 0
    caracteres_ref: int = 0
    token_f1: float = 0.0
    ratio: float = 0.0
    parseable_oficial: bool = False
    parseable_similitud: bool = False
    estado: str = "ok"
    notas: str = ""


# ---------------------------------------------------------------------------
# Carga del dataset
# ---------------------------------------------------------------------------


def find_csv(dataset_dir: Path) -> Path:
    """Localiza ``Resume.csv`` dentro del dataset descargado."""
    candidates = list(dataset_dir.rglob("Resume.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No se encontro Resume.csv dentro de {dataset_dir}"
        )
    return candidates[0]


def load_reference(dataset_dir: Path) -> dict[str, dict]:
    """Carga ``Resume.csv`` y devuelve un indice ``{ID: fila}``.

    El ``ID`` se normaliza a string sin extension para hacer match con el
    nombre de archivo ``<ID>.pdf``.
    """
    csv_path = find_csv(dataset_dir)
    LOGGER.info("Leyendo referencia: %s", csv_path)
    index: dict[str, dict] = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw_id = (row.get("ID") or "").strip()
            key = Path(raw_id).stem
            index[key] = row
    return index


def iter_pdfs(dataset_dir: Path) -> list[Path]:
    """Devuelve los PDFs del dataset, ordenados de forma estable."""
    return sorted(p for p in dataset_dir.rglob("*.pdf") if p.is_file())


# ---------------------------------------------------------------------------
# Evaluacion
# ---------------------------------------------------------------------------


def evaluate_pdf(
    pdf_path: Path,
    reference_rows: dict[str, dict],
    threshold: float,
) -> ParseResult:
    """Evalua un PDF: parseabilidad oficial + fidelidad vs referencia."""
    file_id = pdf_path.stem
    ref_row = reference_rows.get(file_id, {})
    ref_text = normalize_text(ref_row.get("Resume_str", ""))
    categoria = ref_row.get("Category", "") or pdf_path.parent.name

    result = ParseResult(
        id=file_id, categoria=categoria, archivo=pdf_path.name
    )

    lectura = read_pdf(pdf_path)
    if lectura["error"]:
        result.estado = "error"
        result.notas = f"fallo al leer PDF: {lectura['error']}"
        return result

    raw_text = lectura["texto"]
    extracted = normalize_text(raw_text)
    result.paginas = len(lectura["paginas"])
    result.caracteres_pdf = len(extracted)
    result.caracteres_ref = len(ref_text)

    if not ref_text:
        result.estado = "sin_referencia"
        result.notas = "no hay Resume_str para este ID"
    if result.caracteres_pdf == 0:
        result.estado = "sin_texto"
        result.notas = "PDF sin capa de texto (escaneado)"

    result.parseable_oficial = is_parseable(raw_text)
    result.token_f1 = round(token_f1(extracted, ref_text), 4)
    result.ratio = round(ratio_similarity(extracted, ref_text), 4)
    result.parseable_similitud = result.token_f1 >= threshold
    return result


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------


def write_report(rows: list[ParseResult], output: Path) -> None:
    """Escribe el CSV del reporte por archivo."""
    output.parent.mkdir(parents=True, exist_ok=True)
    dict_rows = [asdict(r) for r in rows]
    if not dict_rows:
        LOGGER.warning("No hay resultados que escribir.")
        return
    try:
        import pandas as pd

        pd.DataFrame(dict_rows).to_csv(output, index=False)
    except ImportError:  # pragma: no cover
        with output.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(dict_rows[0].keys()))
            writer.writeheader()
            writer.writerows(dict_rows)


def percentile(values: list[float], pct: float) -> float:
    """Percentil simple (interpolacion lineal), sin depender de numpy."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def summarize(rows: list[ParseResult], threshold: float) -> str:
    """Resumen global y por categoria de la validacion."""
    total = len(rows)
    oficial = sum(1 for r in rows if r.parseable_oficial)
    similitud = sum(1 for r in rows if r.parseable_similitud)
    f1s = [r.token_f1 for r in rows if r.estado != "error"]

    lines = [
        "=" * 64,
        "VALIDACION COMPLEMENTARIA DE EXTRACCION (NO es la metrica oficial)",
        "=" * 64,
        f"Parseables (oficial is_parseable) : {oficial} "
        f"({(oficial / total * 100) if total else 0:.1f}%)",
        f"Parseables (token_f1 >= {threshold:.2f})     : {similitud} "
        f"({(similitud / total * 100) if total else 0:.1f}%)",
        f"PDFs evaluados                    : {total}",
        f"token_f1 medio                    : {sum(f1s) / len(f1s) if f1s else 0:.4f}",
        f"token_f1 p10/p50/p90              : "
        f"{percentile(f1s, 0.10):.3f} / {percentile(f1s, 0.50):.3f} / "
        f"{percentile(f1s, 0.90):.3f}",
    ]
    errores = sum(1 for r in rows if r.estado == "error")
    sin_texto = sum(1 for r in rows if r.estado == "sin_texto")
    lines.append(f"Errores de lectura                : {errores}")
    lines.append(f"PDF sin capa de texto             : {sin_texto}")
    lines.append("-" * 64)
    lines.append("Parseabilidad oficial por categoria:")

    by_cat: dict[str, list[ParseResult]] = defaultdict(list)
    for r in rows:
        by_cat[r.categoria or "(sin categoria)"].append(r)
    for cat, items in sorted(by_cat.items()):
        ok = sum(1 for i in items if i.parseable_oficial)
        pct = ok / len(items) * 100 if items else 0
        lines.append(f"  {cat:<26}: {ok:>4}/{len(items):<4} ({pct:5.1f}%)")
    lines.append("=" * 64)
    return "\n".join(lines)


def worst_cases(rows: list[ParseResult], n: int = 15) -> str:
    """Lista los PDFs con peor similitud (para inspeccion manual)."""
    ordered = sorted(rows, key=lambda r: r.token_f1)[:n]
    lines = ["", f"PEORES {len(ordered)} CASOS (revisar a mano):"]
    for r in ordered:
        lines.append(
            f"  f1={r.token_f1:.3f} ratio={r.ratio:.3f} "
            f"oficial={'si' if r.parseable_oficial else 'no'} "
            f"[{r.categoria}] {r.archivo} ({r.estado})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validacion complementaria: fidelidad de extraccion y "
            "parseabilidad oficial sobre PDFs reales."
        )
    )
    parser.add_argument(
        "--dataset-dir",
        required=True,
        type=Path,
        help="Carpeta raiz del dataset snehaanbhawal/resume-dataset.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/parseability_report.csv"),
        help="Ruta del CSV de salida.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Procesar solo los primeros N PDFs (para pruebas rapidas).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Umbral de token_f1 para parseable_similitud (default {DEFAULT_THRESHOLD}).",
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

    dataset_dir: Path = args.dataset_dir
    if not dataset_dir.is_dir():
        print(f"ERROR: no existe la carpeta {dataset_dir}", file=sys.stderr)
        return 2

    try:
        reference = load_reference(dataset_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    pdfs = iter_pdfs(dataset_dir)
    if args.limit:
        pdfs = pdfs[: args.limit]
    if not pdfs:
        print(f"ERROR: no se encontraron PDFs en {dataset_dir}", file=sys.stderr)
        return 2

    print(f"Evaluando {len(pdfs)} PDFs (referencia: {len(reference)} filas) ...")
    rows: list[ParseResult] = []
    for i, pdf in enumerate(pdfs, start=1):
        rows.append(evaluate_pdf(pdf, reference, args.threshold))
        if i % 100 == 0 or i == len(pdfs):
            print(f"  ... {i}/{len(pdfs)}")

    write_report(rows, args.output)
    print(f"\nReporte escrito en: {args.output}\n")
    print(summarize(rows, args.threshold))
    print(worst_cases(rows))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
