"""Opcional Etapa B/C — 10 pares "buenos" para validar el techo de calibración.

Selecciona 10 pares CV↔oferta del MISMO oficio (título del CV ≈ título de la
vacante y habilidades compartidas), mide su coseno TF-IDF y verifica si el techo
vigente (0,16) sigue siendo válido. El techo original era 0,10; se subió a 0,16
porque el máximo de estos pares es 0,1174 y el 0,10 saturaba.

Los pares se guardan en `data/benchmarks/pares_buenos.csv` con `puntaje_humano`
vacío: el equipo debe revisarlos y calificarlos a mano. La selección es
transparente y reproducible (semilla 42), pero "buen par" es un juicio humano.

Uso:
    .venv/bin/python scripts/build_ceiling_pairs.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.core.nlp_engine import get_skill_lexicon
from src.models.similarity import get_similarity_model
from src.parsing.quality import word_set

# Palabras de seniority que no cambian el oficio ("Senior Java Developer" =
# "Java Developer"). Se sacan para comparar títulos.
SENIORITY = {
    "senior", "sr", "jr", "junior", "lead", "principal", "staff", "i", "ii",
    "iii", "iv", "v", "associate", "trainee", "intern", "internship", "entry",
    "level",
}
# Palabras de relleno de títulos y nombres de empresa.
RELLENO = {
    "at", "the", "of", "and", "for", "in", "on", "with", "pvt", "ltd",
    "limited", "inc", "llc", "corp", "corporation", "company", "co", "services",
    "solutions", "technologies", "technology", "group", "india",
}
# Roles genéricos: un título de una sola palabra ("Developer") no alcanza para
# asegurar que sea el mismo oficio.
ROLES_GENERICOS = {
    "developer", "engineer", "analyst", "consultant", "manager", "lead",
    "associate", "assistant", "executive", "specialist", "administrator",
    "coordinator", "technician", "officer", "director", "architect", "tester",
    "member", "team",
}
# Designaciones que en realidad son títulos académicos.
GRADOS = {
    "b", "e", "btech", "mtech", "be", "me", "bsc", "msc", "mba", "bca", "mca",
    "bcom", "mcom", "bachelor", "master", "degree", "diploma", "engineering",
    "science", "commerce", "arts", "information", "computer", "electronics",
    "electrical", "mechanical", "civil",
}
TECHO_A_VALIDAR = 0.16
MARGEN = 1.38
MAX_POR_OFICIO = 2


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, sin paréntesis ni company suffix."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"\(.*?\)", " ", texto)
    texto = re.sub(r"\bat\b.*$", " ", texto)
    return " ".join(re.sub(r"[^a-z0-9+#.]+", " ", texto).split())


def _tokens_titulo(texto: str) -> set[str]:
    return {
        palabra
        for palabra in _normalizar(texto).split()
        if palabra not in SENIORITY and palabra not in RELLENO and len(palabra) > 1
    }


def _cargar_cvs(path: Path) -> list[dict]:
    """CVs de DataTurks con sus designaciones (títulos de puesto) anotadas."""
    cvs = []
    with open(path, encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            obj = json.loads(line)
            designaciones = []
            for annotation in obj.get("annotation", []):
                if (annotation.get("label") or [""])[0] != "Designation":
                    continue
                for point in annotation.get("points", []):
                    titulo = " ".join((point.get("text") or "").split())
                    tokens = _tokens_titulo(titulo)
                    if tokens and not tokens <= GRADOS:
                        designaciones.append((titulo, tokens))
            if designaciones:
                cvs.append(
                    {
                        "id": f"dataturks_{index:04d}",
                        "text": obj.get("content", "") or "",
                        "designaciones": designaciones,
                    }
                )
    return cvs


def _cargar_ofertas(path: Path, tokens_objetivo: set[str]) -> list[dict]:
    """Ofertas con descripción razonable cuyo título comparte algún token."""
    ofertas, vistos = [], set()
    for chunk in pd.read_csv(
        path,
        usecols=["job_id", "title", "description"],
        chunksize=50_000,
        on_bad_lines="skip",
    ):
        chunk = chunk.dropna(subset=["title", "description"])
        for row in chunk.itertuples(index=False):
            tokens = _tokens_titulo(str(row.title))
            if not tokens or not (tokens & tokens_objetivo):
                continue
            largo = len(str(row.description))
            if not 300 <= largo <= 5000:
                continue
            clave = (row.job_id, row.title)
            if clave in vistos:
                continue
            vistos.add(clave)
            ofertas.append(
                {
                    "id": str(row.job_id),
                    "titulo": " ".join(str(row.title).split()),
                    "texto": str(row.description),
                    "tokens": tokens,
                }
            )
    return ofertas


def _detectar_habilidades(textos: list[str], lexico: set[str]) -> list[set[str]]:
    """Skills del diccionario presentes en cada texto (sin falsos positivos)."""
    unicas = {skill for skill in lexico if " " not in skill}
    frases = [skill for skill in lexico if " " in skill]
    detectadas = []
    for texto in textos:
        normalizado = _normalizar(texto)
        encontradas = unicas & word_set(normalizado)
        encontradas.update(frase for frase in frases if frase in normalizado)
        detectadas.append(encontradas)
    return detectadas


def _puntaje_titulo(titulo_cv: set[str], titulo_oferta: set[str]) -> tuple[float, set[str]]:
    comunes = titulo_cv & titulo_oferta
    if not comunes:
        return 0.0, comunes
    if len(comunes) < 2:
        unico = len(titulo_cv) == 1 and len(titulo_oferta) == 1
        if not (unico and not (comunes & ROLES_GENERICOS)):
            return 0.0, comunes
    cobertura = len(comunes) / len(titulo_cv)
    if cobertura < 0.5:
        return 0.0, comunes
    precision = len(comunes) / len(titulo_oferta)
    return (cobertura + precision) / 2, comunes


def _clave(candidato: dict) -> tuple:
    """Orden de calidad de un par: relevancia, skills compartidas y título."""
    return (
        candidato["relevancia"],
        len(candidato["skills_compartidas"]),
        candidato["score_titulo"],
    )


def _candidatos(cvs: list[dict], ofertas: list[dict], lexico: set[str]) -> list[dict]:
    habilidades_cv = _detectar_habilidades([cv["text"] for cv in cvs], lexico)
    habilidades_oferta = _detectar_habilidades([of["texto"] for of in ofertas], lexico)

    por_token: dict[str, list[int]] = defaultdict(list)
    for indice, oferta in enumerate(ofertas):
        for token in oferta["tokens"]:
            por_token[token].append(indice)

    candidatos: dict[tuple[str, str], dict] = {}
    for cv, skills_cv in zip(cvs, habilidades_cv):
        vistos = set()
        for designacion, tokens_cv in cv["designaciones"]:
            for token in sorted(tokens_cv):
                for indice in por_token.get(token, []):
                    if indice in vistos:
                        continue
                    vistos.add(indice)
                    oferta = ofertas[indice]
                    score, _ = _puntaje_titulo(tokens_cv, oferta["tokens"])
                    if not score:
                        continue
                    compartidas = skills_cv & habilidades_oferta[indice]
                    relevancia = score + min(len(compartidas), 5) / 10
                    if relevancia < 1.0:
                        continue
                    candidato = {
                        "relevancia": relevancia,
                        "score_titulo": score,
                        "skills_compartidas": sorted(compartidas),
                        "cv": cv,
                        "designacion": designacion,
                        "oferta": oferta,
                    }
                    clave = (cv["id"], oferta["id"])
                    actual = candidatos.get(clave)
                    if actual is None or _clave(candidato) > _clave(actual):
                        candidatos[clave] = candidato

    return sorted(
        candidatos.values(),
        key=lambda c: (
            -c["relevancia"],
            -len(c["skills_compartidas"]),
            -c["score_titulo"],
            c["cv"]["id"],
            c["oferta"]["id"],
        ),
    )


def _elegir(candidatos: list[dict], n: int) -> list[dict]:
    elegidos, ofertas_usadas, cvs_usados = [], set(), set()
    por_oficio = defaultdict(int)
    for candidato in candidatos:
        oficio = tuple(sorted(_tokens_titulo(candidato["designacion"])))
        if candidato["oferta"]["id"] in ofertas_usadas:
            continue
        if candidato["cv"]["id"] in cvs_usados:
            continue
        if por_oficio[oficio] >= MAX_POR_OFICIO:
            continue
        elegidos.append(candidato)
        ofertas_usadas.add(candidato["oferta"]["id"])
        cvs_usados.add(candidato["cv"]["id"])
        por_oficio[oficio] += 1
        if len(elegidos) == n:
            break
    return elegidos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10, help="Cantidad de pares buenos.")
    args = parser.parse_args()

    print("[1/4] Leyendo CVs de DataTurks...")
    cvs = _cargar_cvs(config.DATATURKS_PATH)

    # Los 50 pares ya calificados quedan afuera: se buscan pares NUEVOS.
    ya_usados = set()
    calificados = config.BENCHMARKS_DIR / "pares_para_calificar.csv"
    if calificados.exists():
        with open(calificados, encoding="utf-8", newline="") as handle:
            ya_usados = {row["cv_id"] for row in csv.DictReader(handle)}
    cvs = [cv for cv in cvs if cv["id"] not in ya_usados]
    print(f"      CVs nuevos: {len(cvs)}")

    tokens_objetivo = {token for cv in cvs for _, tokens in cv["designaciones"] for token in tokens}

    print("[2/4] Buscando ofertas del mismo oficio...")
    ofertas = _cargar_ofertas(config.POSTINGS_CSV, tokens_objetivo)
    print(f"      Ofertas candidatas: {len(ofertas)}")

    print("[3/4] Cruzando títulos y habilidades...")
    lexico = get_skill_lexicon()
    candidatos = _candidatos(cvs, ofertas, lexico)
    elegidos = _elegir(candidatos, args.n)
    print(f"      Pares seleccionados: {len(elegidos)}")

    modelo = get_similarity_model("tfidf")
    filas, detalles, valores = [], [], []
    for numero, candidato in enumerate(elegidos, start=1):
        cv, oferta = candidato["cv"], candidato["oferta"]
        coseno = modelo.similitud(cv["text"], oferta["texto"])
        valores.append(coseno)
        filas.append(
            {
                "par_id": f"bueno_{numero:02d}",
                "cv_id": cv["id"],
                "cv_designacion": candidato["designacion"],
                "oferta_id": oferta["id"],
                "oferta_titulo": oferta["titulo"],
                "skills_compartidas": ", ".join(candidato["skills_compartidas"]),
                "cv_texto": cv["text"],
                "oferta_texto": oferta["texto"],
                "puntaje_humano": "",
                "comentario": "Par bueno por construcción (mismo oficio + skills); validar a mano.",
            }
        )
        detalles.append(
            {
                "par_id": f"bueno_{numero:02d}",
                "cv_id": cv["id"],
                "designacion": candidato["designacion"],
                "oferta_id": oferta["id"],
                "oferta_titulo": oferta["titulo"],
                "score_titulo": round(candidato["score_titulo"], 3),
                "skills_compartidas": candidato["skills_compartidas"],
                "coseno": round(coseno, 4),
                "puntaje": modelo.puntaje(coseno),
            }
        )

    salida = config.BENCHMARKS_DIR / "pares_buenos.csv"
    config.BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)

    valores_ordenados = sorted(valores)
    maximo = valores_ordenados[-1]
    maximo_matriz = None
    ruta_matriz = config.MODELS_DIR / "similarity_matriz_tfidf.json"
    if ruta_matriz.exists():
        maximo_matriz = json.loads(ruta_matriz.read_text(encoding="utf-8"))["coseno"]["max"]

    techo_sugerido = max(TECHO_A_VALIDAR, round(maximo * MARGEN, 2))
    resumen = {
        "motor": modelo.nombre,
        "techo_a_validar": TECHO_A_VALIDAR,
        "techo_actual": modelo.techo,
        "pares": len(valores),
        "coseno": {
            "min": round(valores_ordenados[0], 4),
            "mediana": round(valores_ordenados[len(valores_ordenados) // 2], 4),
            "max": round(maximo, 4),
        },
        "puntaje_con_techo_a_validar_sin_tope": {
            "min": round(100 * valores_ordenados[0] / TECHO_A_VALIDAR, 1),
            "mediana": round(100 * valores_ordenados[len(valores_ordenados) // 2] / TECHO_A_VALIDAR, 1),
            "max": round(100 * maximo / TECHO_A_VALIDAR, 1),
        },
        "maximo_matriz_aleatoria": round(maximo_matriz, 4) if maximo_matriz else None,
        "supera_techo_a_validar": maximo > TECHO_A_VALIDAR,
        "techo_sugerido": techo_sugerido,
        "criterio_techo_sugerido": f"máximo de los pares buenos × {MARGEN} (redondeado a 2 decimales)",
        "pares_detalle": detalles,
    }
    reporte = config.MODELS_DIR / "techo_pares_buenos.json"
    reporte.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== PARES BUENOS (para revisar a mano) ===")
    for detalle in detalles:
        print(
            f"{detalle['par_id']} | coseno {detalle['coseno']:.4f}"
            f" (puntaje {detalle['puntaje']:5.1f}) | {detalle['cv_id']} "
            f"'{detalle['designacion']}' <-> '{detalle['oferta_titulo']}'"
        )
    print(f"\nMáximo par bueno : {maximo:.4f} (puntaje {100 * maximo / TECHO_A_VALIDAR:.1f} con el techo vigente)")
    if maximo_matriz is not None:
        print(f"Máximo matriz    : {maximo_matriz:.4f} (1.225 pares aleatorios)")
    print(f"¿Supera {TECHO_A_VALIDAR:.2f}? : {'SÍ → recalibrar' if resumen['supera_techo_a_validar'] else 'NO → techo validado'}")
    print(f"Techo sugerido   : {techo_sugerido:.2f}")
    print(f"\nPares guardados  : {salida}")
    print(f"Reporte guardado : {reporte}")
    print("\nSiguiente paso: revisar/calificar `puntaje_humano` en el CSV.")


if __name__ == "__main__":
    main()
