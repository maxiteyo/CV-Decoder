"""Etapa B.2 — Evalúa la similitud semántica contra las notas humanas (Spearman).

Lee la planilla de pares calificados a mano y compara el orden que da el sistema
con el orden que dieron las personas. Si coinciden mucho (Spearman >= 0.75), el
puntaje del sistema es confiable.

Uso:
    .venv/bin/python scripts/eval_similarity.py --motor tfidf
    .venv/bin/python scripts/eval_similarity.py --motor embeddings
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motor", choices=["tfidf", "embeddings"], default="tfidf")
    parser.add_argument(
        "--archivo",
        type=Path,
        default=config.BENCHMARKS_DIR / "pares_para_calificar.csv",
    )
    parser.add_argument("--max", type=int, default=0, help="Limitar cantidad de pares (0 = todos).")
    args = parser.parse_args()

    if not args.archivo.exists():
        print(f"No existe {args.archivo}. Corré scripts/build_rating_pairs.py primero.")
        return

    rows = load_rows(args.archivo)
    if args.max:
        rows = rows[: args.max]

    try:
        from src.models.similarity import get_similarity_model, similitud_a_puntaje

        modelo = get_similarity_model(args.motor)
    except ImportError as error:
        print(f"No se pudo cargar el motor '{args.motor}': {error}")
        print("Sugerencia: usá --motor tfidf o instalá sentence-transformers.")
        return

    pares_calificados = []
    for row in rows:
        if not row.get("cv_texto") or not row.get("oferta_texto"):
            continue
        valor = modelo.similitud(row["cv_texto"], row["oferta_texto"])
        puntaje = similitud_a_puntaje(valor)
        row["_similitud"] = valor
        row["_puntaje_sistema"] = puntaje
        humano = (row.get("puntaje_humano") or "").strip()
        if humano:
            try:
                row["_puntaje_humano"] = float(humano)
                pares_calificados.append(row)
            except ValueError:
                pass

    print(f"Motor    : {modelo.nombre}")
    print(f"Pares    : {len(rows)} (calificados a mano: {len(pares_calificados)})")

    if pares_calificados:
        from scipy.stats import spearmanr

        sistema = [r["_puntaje_sistema"] for r in pares_calificados]
        humanos = [r["_puntaje_humano"] for r in pares_calificados]
        rho, p_value = spearmanr(sistema, humanos)
        print(f"\n=== SIMILITUD vs NOTAS HUMANAS ===")
        print(f"Correlación de Spearman : {rho:.4f}  (objetivo >= 0.75)")
        print(f"Valor p                 : {p_value:.4f}")
        print(f"Pares comparados        : {len(pares_calificados)}")

        report = {
            "motor": modelo.nombre,
            "pares_comparados": len(pares_calificados),
            "spearman": float(rho),
            "p_value": float(p_value),
        }
        report_path = config.MODELS_DIR / f"similarity_{modelo.nombre}_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Reporte guardado en: {report_path}")
    else:
        print("\nTodavía no hay notas humanas cargadas.")
        print("Ejemplos de lo que daría el sistema (primeros 5 pares):")
        for row in rows[:5]:
            titulo = (row.get("oferta_titulo") or "")[:40]
            print(f"  {row['par_id']}: {titulo:42s} -> {row['_puntaje_sistema']:.1f}/100")
        print("\nCuando completen 'puntaje_humano' en el CSV, vuelvan a correr este script.")


if __name__ == "__main__":
    main()
