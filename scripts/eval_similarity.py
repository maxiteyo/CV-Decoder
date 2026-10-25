"""Etapa B.2 — Evalúa la similitud CV-oferta contra las notas humanas.

Lee la planilla de pares calificados a mano y mide la correlación de Spearman
entre el orden que da el sistema y el orden que dieron las personas. Si es alta
(>= 0,75), el puntaje de similitud es confiable aunque la escala sea distinta.

También reporta:
  - intervalo de confianza del 95% (bootstrap, semilla 42),
  - correlación de Pearson (acuerdo en la magnitud, no solo en el orden),
  - distribución de los puntajes calibrados (para verificar que la escala 0-100
    no esté aplastada).

Uso:
    .venv/bin/python scripts/eval_similarity.py --motor tfidf
    .venv/bin/python scripts/eval_similarity.py --motor embeddings_fragmentos
    .venv/bin/python scripts/eval_similarity.py --matriz   # justifica el techo 0-100
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

MOTORES = ("tfidf", "embeddings", "embeddings_fragmentos")


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
    """Intervalo de confianza del 95% para Spearman, remuestreando.

    Si se pasan `grupos` (por ejemplo, el CV de cada par), se remuestrean los
    grupos completos y no los pares sueltos. Es más honesto: 50 pares con 25 CVs
    distintos no son 50 observaciones independientes.
    """
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


def evaluar_matriz(rows: list[dict], modelo) -> None:
    """Distribución del coseno entre TODOS los CVs y TODAS las ofertas del banco.

    Sirve para justificar el techo de calibración: el techo (coseno = 100 puntos)
    tiene que quedar por encima de lo que produce cualquier par del corpus, para
    que un CV escrito a medida todavía pueda superar a los pares observados.
    """
    cvs = sorted({row["cv_texto"] for row in rows})
    ofertas = sorted({row["oferta_texto"] for row in rows})
    valores = sorted(modelo.similitud(cv, oferta) for cv in cvs for oferta in ofertas)
    n = len(valores)
    resumen = {
        "motor": modelo.nombre,
        "cvs": len(cvs),
        "ofertas": len(ofertas),
        "pares": n,
        "techo": modelo.techo,
        "coseno": {
            "min": valores[0],
            "mediana": float(np.median(valores)),
            "p90": valores[int(0.90 * (n - 1))],
            "p99": valores[int(0.99 * (n - 1))],
            "max": valores[-1],
        },
    }
    print(
        f"\n=== MATRIZ COMPLETA ({len(cvs)} CVs × {len(ofertas)} ofertas"
        f" = {n} pares) ==="
    )
    for nombre, valor in resumen["coseno"].items():
        print(f"  coseno {nombre:8s}: {valor:.4f}   (puntaje {modelo.puntaje(valor):5.1f})")
    ruta = config.MODELS_DIR / f"similarity_matriz_{modelo.nombre}.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Reporte guardado en: {ruta}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motor", choices=MOTORES, default="tfidf")
    parser.add_argument(
        "--archivo",
        type=Path,
        default=config.BENCHMARKS_DIR / "pares_para_calificar.csv",
    )
    parser.add_argument("--max", type=int, default=0, help="Limitar cantidad de pares (0 = todos).")
    parser.add_argument(
        "--matriz",
        action="store_true",
        help="Medir todos los pares CV×oferta posibles y justificar el techo de calibración.",
    )
    args = parser.parse_args()

    if not args.archivo.exists():
        print(f"No existe {args.archivo}. Corré scripts/build_rating_pairs.py primero.")
        return

    rows = load_rows(args.archivo)
    if args.max:
        rows = rows[: args.max]

    try:
        from src.models.similarity import get_similarity_model

        modelo = get_similarity_model(args.motor)
    except ImportError as error:
        print(f"No se pudo cargar el motor '{args.motor}': {error}")
        print("Sugerencia: usá --motor tfidf o instalá sentence-transformers.")
        return

    if args.matriz:
        evaluar_matriz(rows, modelo)
        return

    pares = []
    for row in rows:
        if not row.get("cv_texto") or not row.get("oferta_texto"):
            continue
        humano = (row.get("puntaje_humano") or "").strip()
        if not humano:
            continue
        try:
            nota = float(humano)
        except ValueError:
            continue
        crudo = modelo.similitud(row["cv_texto"], row["oferta_texto"])
        pares.append(
            {
                "par_id": row["par_id"],
                "oferta_titulo": row.get("oferta_titulo", "")[:60],
                "cv_grupo": hashlib.sha1(row["cv_texto"].encode("utf-8")).hexdigest()[:12],
                "humano": nota,
                "crudo": crudo,
                "sistema": modelo.puntaje(crudo),
            }
        )

    print(f"Motor    : {modelo.nombre}")
    print(f"Pares    : {len(rows)} (calificados a mano: {len(pares)})")
    print(f"Techo    : coseno {modelo.techo:.2f} = 100 puntos")

    if len(pares) < 10:
        print("\nHacen falta al menos 10 pares calificados para medir Spearman.")
        return

    from scipy.stats import pearsonr, spearmanr

    sistema = [p["sistema"] for p in pares]
    humanos = [p["humano"] for p in pares]
    rho, p_valor = spearmanr(sistema, humanos)
    r_pearson, p_pearson = pearsonr(sistema, humanos)
    ic_bajo, ic_alto = bootstrap_ic(sistema, humanos)
    ic_cv_bajo, ic_cv_alto = bootstrap_ic(
        sistema, humanos, grupos=[p["cv_grupo"] for p in pares]
    )
    cvs_distintos = len({p["cv_grupo"] for p in pares})

    print("\n=== SIMILITUD vs NOTAS HUMANAS ===")
    print(f"Correlación de Spearman : {rho:.4f}  (objetivo >= 0.75)")
    print(f"IC 95% (remuestreo de pares)  : [{ic_bajo:.3f}, {ic_alto:.3f}]")
    print(f"IC 95% (remuestreo de CVs)    : [{ic_cv_bajo:.3f}, {ic_cv_alto:.3f}]")
    print(f"Valor p                 : {p_valor:.3g}")
    print(f"Pearson (magnitud)      : {r_pearson:.4f}  (p = {p_pearson:.3g})")
    print(f"Pares comparados        : {len(pares)} (sobre {cvs_distintos} CVs distintos)")

    ordenados = sorted(pares, key=lambda p: -p["humano"])
    print("\nLos 5 pares mejor calificados a mano:")
    for p in ordenados[:5]:
        print(f"  {p['par_id']}: humano {p['humano']:5.0f} | sistema {p['sistema']:5.1f} | {p['oferta_titulo']}")
    print("Los 3 peores:")
    for p in ordenados[-3:]:
        print(f"  {p['par_id']}: humano {p['humano']:5.0f} | sistema {p['sistema']:5.1f} | {p['oferta_titulo']}")

    report = {
        "motor": modelo.nombre,
        "techo_calibracion": modelo.techo,
        "pares_comparados": len(pares),
        "cvs_distintos": cvs_distintos,
        "spearman": float(rho),
        "spearman_ic95": [ic_bajo, ic_alto],
        "spearman_ic95_por_cv": [ic_cv_bajo, ic_cv_alto],
        "p_value": float(p_valor),
        "pearson": float(r_pearson),
        "pearson_p_value": float(p_pearson),
        "puntaje_sistema": {
            "min": min(sistema),
            "mediana": float(np.median(sistema)),
            "max": max(sistema),
        },
        "detalle": pares,
    }
    report_path = config.MODELS_DIR / f"similarity_{modelo.nombre}_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
