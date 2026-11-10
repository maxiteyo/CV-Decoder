"""Fase 4 — Evalúa el puntaje_match contra notas humanas y pares buenos.

Mide lo que importa para el producto:
  - orden contra notas humanas (Spearman, objetivo >= 0,85),
  - error absoluto y sesgo (MAE/RMSE),
  - distribución de pares aleatorios y pares buenos,
  - falsos positivos: CVs de otra área (nota humana < 20) con match > 30.

Uso:
    .venv/bin/python scripts/eval_match.py
    .venv/bin/python scripts/eval_match.py --max 20
    .venv/bin/python scripts/eval_match.py --json models/match_report.json
"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src import config


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def bootstrap_ic(
    valores: list[float],
    notas: list[float],
    grupos: list[str] | None = None,
    semilla: int = 42,
    n: int = 5000,
) -> tuple[float, float]:
    """IC 95% de Spearman, remuestreando CVs completos cuando se agrupa."""
    from scipy.stats import spearmanr

    generador = np.random.default_rng(semilla)
    x, y = np.asarray(valores), np.asarray(notas)
    if grupos is None:
        grupos = [str(i) for i in range(len(x))]
    unicos = sorted(set(grupos))
    indices = {g: [i for i, v in enumerate(grupos) if v == g] for g in unicos}

    rhos = []
    for _ in range(n):
        elegidos = generador.choice(unicos, len(unicos), replace=True)
        muestra = [i for g in elegidos for i in indices[g]]
        if len(set(y[muestra])) < 2 or len(set(x[muestra])) < 2:
            continue
        rhos.append(spearmanr(x[muestra], y[muestra])[0])
    return float(np.percentile(rhos, 2.5)), float(np.percentile(rhos, 97.5))


def evaluar(rows: list[dict], con_humano: bool) -> list[dict]:
    from src.core.diagnostico import analizar

    resultados = []
    for row in rows:
        if not row.get("cv_texto") or not row.get("oferta_texto"):
            continue
        humano = (row.get("puntaje_humano") or "").strip()
        nota = None
        if con_humano:
            if not humano:
                continue
            try:
                nota = float(humano)
            except ValueError:
                continue

        diagnostico = analizar(row["cv_texto"], row["oferta_texto"])
        similitud = diagnostico["dimensiones"]["similitud"]
        resultados.append(
            {
                "par_id": row["par_id"],
                "oferta_titulo": row.get("oferta_titulo", "")[:60],
                "cv_grupo": hashlib.sha1(row["cv_texto"].encode("utf-8")).hexdigest()[:12],
                "humano": nota,
                "match": diagnostico["puntaje_match"],
                "ats": diagnostico["puntaje_ats"],
                "similitud": similitud["puntaje"],
                "fuente_similitud": similitud["fuente"],
                "cap": diagnostico["requisitos"]["cap_match"],
                "bono_skills": diagnostico["requisitos"]["bono_skills"],
                "cobertura_obligatorios": diagnostico["requisitos"]["cobertura_obligatorios"],
                "ajuste_seniority": diagnostico["seniority"]["ajuste"],
            }
        )
    return resultados


def resumen(pares: list[dict]) -> dict:
    valores = [p["match"] for p in pares]
    return {
        "pares": len(pares),
        "min": round(min(valores), 1),
        "mediana": round(float(np.median(valores)), 1),
        "max": round(max(valores), 1),
        "p90": round(float(np.percentile(valores, 90)), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archivo",
        type=Path,
        default=config.BENCHMARKS_DIR / "pares_para_calificar.csv",
    )
    parser.add_argument(
        "--buenos",
        type=Path,
        default=config.BENCHMARKS_DIR / "pares_buenos.csv",
    )
    parser.add_argument("--max", type=int, default=0, help="Limitar pares aleatorios (0 = todos).")
    parser.add_argument(
        "--json",
        type=Path,
        default=config.MODELS_DIR / "match_report.json",
        help="Ruta del reporte JSON.",
    )
    args = parser.parse_args()

    if not args.archivo.exists():
        print(f"No existe {args.archivo}. Corré scripts/build_rating_pairs.py primero.")
        return

    rows = load_rows(args.archivo)
    if args.max:
        rows = rows[: args.max]

    print(f"Pares con nota humana: {len(rows)}")
    calificados = evaluar(rows, con_humano=True)
    if len(calificados) < 10:
        print("Hacen falta al menos 10 pares calificados para medir Spearman.")
        return

    from scipy.stats import pearsonr, spearmanr

    sistema = [p["match"] for p in calificados]
    humanos = [p["humano"] for p in calificados]
    rho, p_valor = spearmanr(sistema, humanos)
    r_pearson, p_pearson = pearsonr(sistema, humanos)
    errores = np.asarray(sistema) - np.asarray(humanos)
    mae = float(np.mean(np.abs(errores)))
    rmse = float(np.sqrt(np.mean(errores**2)))
    sesgo = float(np.mean(errores))
    ic_bajo, ic_alto = bootstrap_ic(
        sistema, humanos, grupos=[p["cv_grupo"] for p in calificados]
    )

    otra_area = [p for p in calificados if p["humano"] < 20]
    falsos = [p for p in otra_area if p["match"] > 30]
    max_otra_area = max((p["match"] for p in otra_area), default=0.0)

    buenos = []
    if args.buenos.exists():
        buenos = evaluar(load_rows(args.buenos), con_humano=False)

    print("\n=== MATCH vs NOTAS HUMANAS ===")
    print(f"Spearman                : {rho:.4f}  (objetivo >= 0.85)")
    print(f"IC 95% por CV           : [{ic_bajo:.3f}, {ic_alto:.3f}]")
    print(f"Pearson                 : {r_pearson:.4f}  (p = {p_pearson:.3g})")
    print(f"MAE / RMSE / sesgo      : {mae:.2f} / {rmse:.2f} / {sesgo:+.2f}")
    print(f"Pares                   : {len(calificados)} sobre {len({p['cv_grupo'] for p in calificados})} CVs")
    print(f"Distribución match      : {resumen(calificados)}")
    print(
        f"Otra área (humano < 20) : {len(otra_area)} pares, "
        f"máximo {max_otra_area:.1f} (objetivo <= 30)"
    )
    print(f"Falsos positivos > 30   : {len(falsos)}")

    if buenos:
        print("\n=== PARES BUENOS (sin nota humana) ===")
        print(f"Distribución match      : {resumen(buenos)}")
        print(f"Mínimo                  : {resumen(buenos)['min']:.1f}  (objetivo > 50)")
        for p in sorted(buenos, key=lambda p: p["match"]):
            print(
                f"  {p['par_id']}: match {p['match']:5.1f} | "
                f"sim {p['similitud']:5.1f} | bono {p['bono_skills']:4.1f} | "
                f"cap {p['cap']} | {p['oferta_titulo']}"
            )

    ordenados = sorted(calificados, key=lambda p: -p["humano"])
    print("\nMejores notas humanas:")
    for p in ordenados[:5]:
        print(f"  {p['par_id']}: humano {p['humano']:4.0f} | match {p['match']:5.1f}")
    print("Peores notas humanas:")
    for p in ordenados[-5:]:
        print(f"  {p['par_id']}: humano {p['humano']:4.0f} | match {p['match']:5.1f}")

    aprobado = (
        rho >= 0.85
        and (not buenos or resumen(buenos)["min"] > 50)
        and max_otra_area <= 30
    )
    print(f"\nFase 4: {'APROBADA' if aprobado else 'PENDIENTE'}")

    reporte = {
        "objetivo_spearman": 0.85,
        "spearman": float(rho),
        "spearman_ic95_por_cv": [ic_bajo, ic_alto],
        "p_value": float(p_valor),
        "pearson": float(r_pearson),
        "mae": mae,
        "rmse": rmse,
        "sesgo": sesgo,
        "pares": len(calificados),
        "cvs_distintos": len({p["cv_grupo"] for p in calificados}),
        "distribucion_random": resumen(calificados),
        "otra_area_humano_menor_20": {
            "pares": len(otra_area),
            "max_match": max_otra_area,
            "falsos_positivos_mayor_30": len(falsos),
        },
        "distribucion_buenos": resumen(buenos) if buenos else None,
        "aprobado": aprobado,
        "detalle_random": calificados,
        "detalle_buenos": buenos,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Reporte guardado en: {args.json}")


if __name__ == "__main__":
    main()
