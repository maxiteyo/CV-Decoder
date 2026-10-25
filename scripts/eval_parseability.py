"""Etapa B.1 — Evalúa la parseabilidad de los PDFs (sintéticos o reales).

Dos modos:
  - Sintéticos (por defecto): usa `data/benchmarks/pdfs/manifest.json`, donde se
    conoce el texto original y la maqueta de cada PDF.
  - Reales (`--reales`): usa `data/benchmarks/pdfs_reales/labels.csv`, la
    planilla de etiquetas hecha con `scripts/build_pdf_labels.py`.

En los dos casos la pregunta es la misma: ¿el lector decide bien si un CV se
puede leer? En reales se agregan métricas graduadas (páginas sin texto, palabras
pegadas) porque un PDF puede ser "legible" pero estar a medias.

Uso:
    .venv/bin/python scripts/eval_parseability.py
    .venv/bin/python scripts/eval_parseability.py --reales
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.parsing.pdf_reader import read_pdf
from src.parsing.quality import is_parseable, text_quality, word_coverage

UMBRAL_LEGIBLES = 0.90


def _metricas_binarias(resultados: list[dict]) -> dict:
    """Matriz de confusión: 'parseable' es la clase positiva."""
    tp = sum(1 for r in resultados if r["esperado_parseable"] and r["parseable"])
    fp = sum(1 for r in resultados if not r["esperado_parseable"] and r["parseable"])
    tn = sum(1 for r in resultados if not r["esperado_parseable"] and not r["parseable"])
    fn = sum(1 for r in resultados if r["esperado_parseable"] and not r["parseable"])
    total = len(resultados)
    sensibilidad = tp / (tp + fn) if (tp + fn) else 0.0
    especificidad = tn / (tn + fp) if (tn + fp) else 0.0
    exactitud = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precision * sensibilidad / (precision + sensibilidad)) if (precision + sensibilidad) else 0.0
    return {
        "total": total,
        "verdaderos_positivos": tp,
        "falsos_positivos": fp,
        "verdaderos_negativos": tn,
        "falsos_negativos": fn,
        "exactitud": exactitud,
        "sensibilidad_legibles": sensibilidad,
        "especificidad_escaneados": especificidad,
        "f1": f1,
    }


def _imprimir_binarias(m: dict, titulo: str) -> None:
    print(f"=== {titulo} ===")
    print(f"PDFs evaluados            : {m['total']}")
    print(f"Decisiones correctas      : {m['verdaderos_positivos'] + m['verdaderos_negativos']}/{m['total']} ({m['exactitud']:.1%})")
    print(f"Legibles recuperados      : {m['verdaderos_positivos']}/{m['verdaderos_positivos'] + m['falsos_negativos']} "
          f"(objetivo >= {UMBRAL_LEGIBLES:.0%})  sensibilidad={m['sensibilidad_legibles']:.1%}")
    print(f"Escaneados detectados     : {m['verdaderos_negativos']}/{m['verdaderos_negativos'] + m['falsos_positivos']}  "
          f"especificidad={m['especificidad_escaneados']:.1%}")
    print(f"F1 (clase 'legible')      : {m['f1']:.3f}")


def evaluar_sinteticos() -> None:
    manifest_path = config.PDFS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("No hay PDFs de prueba. Corré primero scripts/build_test_pdfs.py")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    resultados = []
    for item in manifest:
        leido = read_pdf(config.PDFS_DIR / item["pdf"])
        coverage = word_coverage(leido["texto"], item["texto_esperado"])
        parseable = is_parseable(leido["texto"])
        resultados.append(
            {
                "pdf": item["pdf"],
                "maqueta": item["maqueta"],
                "esperado_parseable": item["esperado_parseable"],
                "parseable": parseable,
                "acierto": parseable == item["esperado_parseable"],
                "cobertura": coverage,
                "error_lectura": leido["error"],
                **text_quality(leido["texto"]),
            }
        )

    metricas = _metricas_binarias(resultados)
    _imprimir_binarias(metricas, "PARSEABILIDAD — PDFs SINTÉTICOS")

    print("\nPor maqueta:")
    for layout in ("simple", "columnas", "escaneado"):
        subset = [r for r in resultados if r["maqueta"] == layout]
        if not subset:
            continue
        ok = sum(1 for r in subset if r["acierto"])
        cov = sum(r["cobertura"] for r in subset) / len(subset)
        print(f"  {layout:10s}: {ok}/{len(subset)} decisiones correctas, cobertura media {cov:.3f}")

    report = {**metricas, "modo": "sinteticos", "detalle": resultados}
    destino = config.MODELS_DIR / "parseability_report.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {destino}")


def evaluar_reales() -> None:
    labels_path = config.PDFS_REALES_LABELS
    if not labels_path.exists():
        print(f"No existe {labels_path}. Corré primero scripts/build_pdf_labels.py")
        return

    with open(labels_path, encoding="utf-8", newline="") as handle:
        filas = list(csv.DictReader(handle))
    # Solo se evalúan las filas con etiqueta binaria clara. Las marcadas como
    # "revisar" quedan afuera hasta que alguien las mire a mano.
    filas = [f for f in filas if f["categoria"] in {"legible", "escaneado"}]
    unicos = [f for f in filas if not f["duplicado_de"]]

    resultados = []
    for fila in unicos:
        leido = read_pdf(config.PDFS_REALES_DIR / fila["archivo"])
        q = text_quality(leido["texto"])
        parseable = is_parseable(leido["texto"])
        esperado = fila["esperado_parseable"] == "1"
        resultados.append(
            {
                "archivo": fila["archivo"],
                "categoria": fila["categoria"],
                "esperado_parseable": esperado,
                "parseable": parseable,
                "acierto": parseable == esperado,
                "error_lectura": leido["error"],
                "paginas": len(leido["paginas"]),
                "paginas_sin_texto": leido["paginas_sin_texto"],
                "imagenes": leido["imagenes"],
                **q,
            }
        )

    metricas = _metricas_binarias(resultados)
    _imprimir_binarias(metricas, "PARSEABILIDAD — PDFs REALES (sin duplicados)")
    print(f"(Se excluyeron {len(filas) - len(unicos)} archivos duplicados de {len(filas)})")

    legibles = [r for r in resultados if r["esperado_parseable"]]
    escaneados = [r for r in resultados if not r["esperado_parseable"]]
    print("\nCalidad del texto recuperado (sólo legibles):")
    palabras = sorted(r["palabras"] for r in legibles)
    print(f"  palabras por CV         : mínimo {palabras[0]}, mediana {palabras[len(palabras) // 2]}, máximo {palabras[-1]}")
    con_vacias = [r for r in legibles if r["paginas_sin_texto"]]
    print(f"  con páginas sin texto   : {len(con_vacias)}/{len(legibles)} ({len(con_vacias) / len(legibles):.1%})")
    con_pegadas = [r for r in legibles if r["ratio_palabras_pegadas"] > 0.02]
    print(f"  con palabras pegadas >2%: {len(con_pegadas)}/{len(legibles)} ({len(con_pegadas) / len(legibles):.1%})")
    for r in sorted(con_pegadas, key=lambda x: -x["ratio_palabras_pegadas"])[:5]:
        print(f"    {r['archivo']:18s} {r['ratio_palabras_pegadas']:6.1%} de palabras pegadas")
    if escaneados:
        print(f"  escaneados con texto residual: {sum(1 for r in escaneados if r['palabras']) }/{len(escaneados)}")

    errores = [r for r in resultados if not r["acierto"]]
    if errores:
        print("\nErrores de decisión:")
        for r in errores:
            print(f"  {r['archivo']:18s} esperado={'legible' if r['esperado_parseable'] else 'escaneado'} "
                  f"-> decidió {'legible' if r['parseable'] else 'escaneado'} (palabras={r['palabras']})")
    else:
        print("\nSin errores de decisión.")

    report = {
        **metricas,
        "modo": "reales",
        "archivos_totales": len(filas),
        "duplicados_excluidos": len(filas) - len(unicos),
        "legibles": len(legibles),
        "escaneados": len(escaneados),
        "legibles_con_paginas_sin_texto": len(con_vacias),
        "legibles_con_palabras_pegadas": len(con_pegadas),
        "detalle": resultados,
    }
    destino = config.MODELS_DIR / "parseability_reales_report.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {destino}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reales", action="store_true", help="Evaluar los PDFs reales con labels.csv.")
    args = parser.parse_args()

    if args.reales:
        evaluar_reales()
    else:
        evaluar_sinteticos()


if __name__ == "__main__":
    main()
