"""Etapa B.1 — Arma la planilla de etiquetas de los PDFs reales.

Recorre `data/benchmarks/pdfs_reales/`, mide cada PDF y escribe `labels.csv` con
la categoría observada. La etiqueta `esperado_parseable` es la verdad contra la
que después se mide el lector (ver `scripts/eval_parseability.py --reales`).

Criterio de etiquetado (automático y auditable):
  - `escaneado`: no hay capa de texto (0 caracteres) pero sí imágenes.
  - `roto`     : el PDF no se puede abrir.
  - `legible`  : tiene texto suficiente y mayormente alfanumérico.
La columna `revisar` marca los casos que conviene mirar a ojo antes de confiar
en la etiqueta (texto muy corto o palabras pegadas).

Uso:
    .venv/bin/python scripts/build_pdf_labels.py
"""

import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.parsing.pdf_reader import read_pdf
from src.parsing.quality import MIN_PALABRAS, is_parseable, text_quality

CAMPOS = [
    "archivo",
    "categoria",
    "esperado_parseable",
    "paginas",
    "paginas_sin_texto",
    "imagenes",
    "caracteres",
    "palabras",
    "ratio_alfanumerico",
    "palabras_pegadas",
    "duplicado_de",
    "revisar",
    "notas",
]


def _hash_archivo(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _hash_texto(texto: str) -> str:
    return hashlib.sha1(" ".join(texto.split()).lower().encode("utf-8")).hexdigest()


def clasificar(palabras: int, imagenes: int, paginas: int, error: str | None, parseable: bool) -> str:
    if error:
        return "roto"
    sin_texto = palabras < MIN_PALABRAS
    if sin_texto:
        # Casi sin texto: si hay imágenes (o el PDF no expone páginas legibles)
        # es un escaneo; si no, algo raro que conviene mirar a mano.
        return "escaneado" if (imagenes or paginas == 0) else "revisar"
    if not parseable:
        # Texto presente pero mayormente basura: no es un escaneo, es un PDF
        # mal exportado. Se revisa a mano antes de etiquetarlo.
        return "revisar"
    return "legible"


def main() -> None:
    folder = config.PDFS_REALES_DIR
    pdfs = sorted(folder.glob("*.pdf"), key=lambda p: p.name)
    if not pdfs:
        print(f"No hay PDFs en {folder}")
        return

    filas: list[dict] = []
    vistos_archivo: dict[str, str] = {}
    vistos_texto: dict[str, str] = {}

    for path in pdfs:
        leido = read_pdf(path)
        texto = leido["texto"]
        paginas = leido["paginas"]
        q = text_quality(texto)
        parseable = is_parseable(texto)
        categoria = clasificar(q["palabras"], leido["imagenes"], len(paginas), leido["error"], parseable)

        duplicado = ""
        hash_archivo = _hash_archivo(path)
        if hash_archivo in vistos_archivo:
            duplicado = vistos_archivo[hash_archivo]
        else:
            vistos_archivo[hash_archivo] = path.name
            # El hash de texto solo vale para CVs con texto real: los escaneos
            # comparten frases genéricas ("Scanned by CamScanner") y darían
            # falsos duplicados.
            if q["palabras"] >= MIN_PALABRAS:
                hash_texto = _hash_texto(texto)
                if hash_texto in vistos_texto:
                    duplicado = vistos_texto[hash_texto]
                else:
                    vistos_texto[hash_texto] = path.name

        sin_texto = sum(1 for p in paginas if len(p["texto"].split()) == 0)
        notas = []
        if leido["error"]:
            notas.append(f"error de lectura: {leido['error']}")
        if categoria == "escaneado":
            if paginas:
                notas.append(f"{leido['imagenes']} imagen(es) y {q['caracteres']} caracteres: sin capa de texto")
            else:
                notas.append("PDF sin páginas legibles (armado como imagen)")
        if categoria == "legible" and q["palabras"] < 120:
            notas.append("CV corto: pocas palabras")
        if q["ratio_palabras_pegadas"] > 0.02:
            notas.append(f"{q['ratio_palabras_pegadas']:.1%} de palabras pegadas")
        if sin_texto:
            notas.append(f"{sin_texto} página(s) sin texto")
        if duplicado:
            notas.append(f"igual a {duplicado}")

        revisar = "si" if categoria == "revisar" or (categoria == "legible" and q["palabras"] < 120) else ""

        filas.append(
            {
                "archivo": path.name,
                "categoria": categoria,
                "esperado_parseable": int(categoria == "legible"),
                "paginas": len(paginas),
                "paginas_sin_texto": sin_texto,
                "imagenes": leido["imagenes"],
                "caracteres": q["caracteres"],
                "palabras": q["palabras"],
                "ratio_alfanumerico": round(q["ratio_alfanumerico"], 3),
                "palabras_pegadas": q["palabras_pegadas"],
                "duplicado_de": duplicado,
                "revisar": revisar,
                "notas": "; ".join(notas),
            }
        )

    salida = config.PDFS_REALES_LABELS
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAMPOS)
        writer.writeheader()
        writer.writerows(filas)

    por_categoria: dict[str, int] = {}
    for fila in filas:
        por_categoria[fila["categoria"]] = por_categoria.get(fila["categoria"], 0) + 1
    duplicados = sum(1 for f in filas if f["duplicado_de"])

    print(f"PDFs analizados : {len(filas)}")
    for categoria, cantidad in sorted(por_categoria.items()):
        print(f"  {categoria:10s}: {cantidad}")
    print(f"Duplicados      : {duplicados}")
    print(f"Para revisar    : {sum(1 for f in filas if f['revisar'])}")
    print(f"Planilla        : {salida}")


if __name__ == "__main__":
    main()
