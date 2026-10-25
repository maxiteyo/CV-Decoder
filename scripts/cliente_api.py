"""Cliente de consola para probar la API sin instalar nada extra.

Requiere que la API esté corriendo en otra terminal:
    .venv/bin/uvicorn src.api.main:app --reload

Ejemplos:
    .venv/bin/python scripts/cliente_api.py --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" --par par_005
    .venv/bin/python scripts/cliente_api.py --pdf cv.pdf --oferta "Buscamos analista de datos con Python y SQL"
    .venv/bin/python scripts/cliente_api.py --pdf cv.pdf --oferta-archivo oferta.txt

Usa solo la biblioteca estándar (urllib), así no agrega dependencias al proyecto.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config


def _leer_oferta(args) -> str:
    if args.oferta:
        return args.oferta
    if args.oferta_archivo:
        return args.oferta_archivo.read_text(encoding="utf-8")
    if args.par:
        ruta = config.BENCHMARKS_DIR / "pares_para_calificar.csv"
        if not ruta.exists():
            sys.exit(f"No existe {ruta}. Ejecutá scripts/build_rating_pairs.py primero.")
        with open(ruta, encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["par_id"] == args.par:
                    return fila["oferta_texto"]
        sys.exit(f"No encontré el par '{args.par}' en {ruta}.")
    sys.exit(
        "Falta la oferta. Usá --oferta \"texto...\", --oferta-archivo oferta.txt o --par par_005."
    )


def _cuerpo_multipart(pdf: Path, campos: dict[str, str]) -> tuple[bytes, str]:
    frontera = "----cvdecoder" + uuid.uuid4().hex
    partes: list[bytes] = []

    partes.append(
        (
            f"--{frontera}\r\n"
            f'Content-Disposition: form-data; name="cv"; filename="{pdf.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8")
    )
    partes.append(pdf.read_bytes())
    partes.append(b"\r\n")

    for nombre, valor in campos.items():
        partes.append(
            (
                f"--{frontera}\r\n"
                f'Content-Disposition: form-data; name="{nombre}"\r\n\r\n'
            ).encode("utf-8")
        )
        partes.append(valor.encode("utf-8"))
        partes.append(b"\r\n")

    partes.append(f"--{frontera}--\r\n".encode("utf-8"))
    return b"".join(partes), f"multipart/form-data; boundary={frontera}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba la API de CV-Decoder.")
    parser.add_argument("--pdf", type=Path, required=True, help="CV en PDF.")
    parser.add_argument("--oferta", help="Texto de la oferta.")
    parser.add_argument("--oferta-archivo", type=Path, help="Archivo de texto con la oferta.")
    parser.add_argument("--par", help="ID de par de la planilla (ej. par_005).")
    parser.add_argument("--motor", default="tfidf", choices=["tfidf", "embeddings", "embeddings_fragmentos"])
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL base de la API.")
    args = parser.parse_args()

    if not args.pdf.exists():
        sys.exit(f"No existe el PDF: {args.pdf}")

    url = args.url.rstrip("/")

    # 1. Verificar que el servidor esté arriba (error claro si no).
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=5) as respuesta:
            salud = json.load(respuesta)
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        sys.exit(
            f"No pude conectarme a {url}.\n"
            "Abrí otra terminal y levantá la API con:\n"
            "  .venv/bin/uvicorn src.api.main:app --reload"
        )

    print(f"Servidor: {url}  ({salud.get('estado')}, versión {salud.get('version')})")
    print(f"Enviando: {args.pdf.name}  |  motor: {args.motor}")

    oferta = _leer_oferta(args)
    cuerpo, tipo_contenido = _cuerpo_multipart(args.pdf, {"oferta": oferta, "motor": args.motor})

    pedido = urllib.request.Request(
        f"{url}/api/v1/analyze-cv",
        data=cuerpo,
        headers={"Content-Type": tipo_contenido},
        method="POST",
    )

    try:
        with urllib.request.urlopen(pedido, timeout=120) as respuesta:
            resultado = json.load(respuesta)
    except urllib.error.HTTPError as error:
        print(f"\nLa API respondió {error.code}:")
        print(json.dumps(json.load(error), ensure_ascii=False, indent=2))
        sys.exit(1)
    except urllib.error.URLError as error:
        sys.exit(f"Falló la conexión: {error.reason}")

    print("\n=== DIAGNÓSTICO ===")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
