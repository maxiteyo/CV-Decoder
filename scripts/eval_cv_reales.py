"""Etapa B.1b — Mide qué se obtiene de los CVs reales (sin oferta de por medio).

Qué mide:
  - cuántas de las 4 secciones (Contacto, Experiencia, Educación, Habilidades)
    se detectan en cada CV real,
  - cuántas habilidades del diccionario aparecen,
  - cuántas entidades reconoce el modelo,
  - cuánto tarda el pipeline por CV (lectura del PDF + NLP).

No mide "aciertos" de entidades porque no hay etiquetas para estos CVs: es una
medición descriptiva para detectar problemas de extracción. La exactitud del
detector de secciones se mide aparte, con etiquetas (ver `eval_sections.py`).

Uso:
    .venv/bin/python scripts/eval_cv_reales.py
"""

import csv
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.core.diagnostico import procesar_cv, puntaje_parseabilidad
from src.parsing.pdf_reader import read_pdf

SECCIONES = ("Contacto", "Experiencia", "Educacion", "Habilidades")


def main() -> None:
    labels_path = config.PDFS_REALES_LABELS
    if not labels_path.exists():
        print(f"No existe {labels_path}. Corré primero scripts/build_pdf_labels.py")
        return
    with open(labels_path, encoding="utf-8", newline="") as handle:
        filas = [
            f
            for f in csv.DictReader(handle)
            if f["categoria"] == "legible" and not f["duplicado_de"]
        ]

    lecturas: list[float] = []
    nlp_tiempos: list[float] = []
    palabras: list[int] = []
    habilidades: list[int] = []
    entidades: list[int] = []
    secciones_ok: list[int] = []
    faltantes: dict[str, int] = {s: 0 for s in SECCIONES}
    sin_persona: list[str] = []
    detalle: list[dict] = []

    for fila in filas:
        inicio = time.perf_counter()
        leido = read_pdf(config.PDFS_REALES_DIR / fila["archivo"])
        lectura = time.perf_counter() - inicio

        inicio = time.perf_counter()
        texto = leido["texto"]
        perfil = procesar_cv(texto)
        entidades_cv = perfil["entidades"]
        etiquetas = perfil["etiquetas"]
        secciones = perfil["secciones"]
        skills = perfil["habilidades"]
        nlp = time.perf_counter() - inicio

        lecturas.append(lectura)
        nlp_tiempos.append(nlp)
        palabras.append(len(texto.split()))
        habilidades.append(len(skills))
        entidades.append(len(entidades_cv))
        presentes = sum(1 for s in SECCIONES if secciones[s])
        secciones_ok.append(presentes)
        for seccion in SECCIONES:
            if not secciones[seccion]:
                faltantes[seccion] += 1
        if "PERSONA" not in etiquetas:
            sin_persona.append(fila["archivo"])
        detalle.append(
            {
                "archivo": fila["archivo"],
                "palabras": len(texto.split()),
                "secciones_detectadas": presentes,
                "secciones": secciones,
                "habilidades": len(skills),
                "entidades": len(entidades_cv),
                "parseabilidad": puntaje_parseabilidad(texto),
                "segundos_lectura": round(lectura, 3),
                "segundos_nlp": round(nlp, 3),
            }
        )

    n = len(detalle)
    if not n:
        print("No hay CVs legibles etiquetados.")
        return

    def resumen(valores: list[float]) -> str:
        ordenados = sorted(valores)
        p10 = ordenados[int(0.10 * (n - 1))]
        p90 = ordenados[int(0.90 * (n - 1))]
        return f"mediana {statistics.median(valores):.2f} | p10 {p10:.2f} | p90 {p90:.2f}"

    print(f"=== CALIDAD DE EXTRACCIÓN SOBRE CVs REALES (n={n}) ===")
    print(f"Palabras por CV          : {resumen(palabras)}")
    print(f"Habilidades por CV       : {resumen(habilidades)}")
    print(f"Entidades por CV         : {resumen(entidades)}")
    print(f"Tiempo de lectura        : {resumen(lecturas)} s")
    print(f"Tiempo de NLP            : {resumen(nlp_tiempos)} s")
    print(f"Tiempo total por CV      : {resumen([a + b for a, b in zip(lecturas, nlp_tiempos)])} s")

    print("\nSecciones detectadas por CV:")
    for cantidad in range(len(SECCIONES) + 1):
        cuantos = sum(1 for s in secciones_ok if s == cantidad)
        print(f"  {cantidad}/{len(SECCIONES)} secciones: {cuantos:3d} CVs ({cuantos / n:.1%})")
    print(f"  CVs con las 4 secciones: {sum(1 for s in secciones_ok if s == len(SECCIONES))}/{n} "
          f"({sum(1 for s in secciones_ok if s == len(SECCIONES)) / n:.1%})")
    print("\nSección que falta (cuántos CVs):")
    for seccion, cuantos in faltantes.items():
        print(f"  {seccion:12s}: {cuantos:3d} ({cuantos / n:.1%})")
    print(f"\nCVs sin entidad PERSONA : {len(sin_persona)} ({len(sin_persona) / n:.1%})")
    for archivo in sin_persona[:5]:
        print(f"  {archivo}")

    report = {
        "modo": "cv_reales",
        "cvs": n,
        "palabras_mediana": statistics.median(palabras),
        "habilidades_mediana": statistics.median(habilidades),
        "entidades_mediana": statistics.median(entidades),
        "segundos_lectura_mediana": round(statistics.median(lecturas), 3),
        "segundos_nlp_mediana": round(statistics.median(nlp_tiempos), 3),
        "cvs_con_4_secciones": sum(1 for s in secciones_ok if s == len(SECCIONES)),
        "secciones_faltantes": faltantes,
        "cvs_sin_persona": sin_persona,
        "detalle": detalle,
    }
    destino = config.MODELS_DIR / "cv_reales_reporte.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {destino}")


if __name__ == "__main__":
    main()
