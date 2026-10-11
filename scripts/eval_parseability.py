"""Etapa B.1 — Evalúa la parseabilidad de los PDFs de prueba.

Lee cada PDF, mide cuánto texto recupera (cobertura de palabras) y decide si es
"parseable". El objetivo del proyecto es que al menos el 90% de los PDFs sean
legibles.

Uso:
    .venv/bin/python scripts/eval_parseability.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.parsing.pdf_reader import extract_pdf_text
from src.parsing.quality import is_parseable, text_quality, word_coverage


def main() -> None:
    manifest_path = config.PDFS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("No hay PDFs de prueba. Corré primero scripts/build_test_pdfs.py")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    results = []
    for item in manifest:
        pdf_path = config.PDFS_DIR / item["pdf"]
        extracted = extract_pdf_text(pdf_path)
        coverage = word_coverage(extracted, item["texto_esperado"])
        parseable = is_parseable(extracted)
        results.append(
            {
                "pdf": item["pdf"],
                "maqueta": item["maqueta"],
                "esperado_parseable": item["esperado_parseable"],
                "parseable": parseable,
                "acierto": parseable == item["esperado_parseable"],
                "cobertura": coverage,
                **text_quality(extracted),
            }
        )

    n = len(results)
    hits = sum(1 for r in results if r["acierto"])
    buenos = [r for r in results if r["esperado_parseable"]]
    malos = [r for r in results if not r["esperado_parseable"]]
    buenos_ok = sum(1 for r in buenos if r["parseable"])
    malos_ok = sum(1 for r in malos if not r["parseable"])

    print("=== PARSEABILIDAD DE PDFs (decisión correcta) ===")
    print(f"PDFs probados              : {n}")
    print(f"Decisiones correctas       : {hits}/{n} ({hits / n:.1%})")
    print(f"PDFs legibles recuperados  : {buenos_ok}/{len(buenos)} (objetivo >= 90%)")
    print(f"PDFs ilegibles detectados  : {malos_ok}/{len(malos)} (esperado: todos)")

    print("\nPor maqueta:")
    for layout in ("simple", "columnas", "escaneado"):
        subset = [r for r in results if r["maqueta"] == layout]
        if not subset:
            continue
        ok = sum(1 for r in subset if r["acierto"])
        cov = sum(r["cobertura"] for r in subset) / len(subset)
        print(f"  {layout:10s}: {ok}/{len(subset)} decisiones correctas, cobertura media {cov:.3f}")

    report = {
        "pdfs": n,
        "decisiones_correctas": hits,
        "exactitud": hits / n if n else 0.0,
        "legibles_recuperados": buenos_ok,
        "legibles_total": len(buenos),
        "ilegibles_detectados": malos_ok,
        "ilegibles_total": len(malos),
        "detalle": results,
    }
    report_path = config.MODELS_DIR / "parseability_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
