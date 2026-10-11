"""Construcción de un diccionario curado de habilidades.

Se combinan tres fuentes (todas dentro de data/raw/referencias y data/raw):
  1. keyword + synonyms del dataset "ats-resume-keyword-dataset" (MIT),
  2. lista de habilidades y sinónimos del proyecto "ats-screener" (MIT),
  3. nombres de habilidades más frecuentes de job_skills.csv (muestra).

El diccionario sirve para LIMPIAR el dataset ruidoso de 5029 CVs: sólo se
conservan como "habilidad" las marcas que estén en este diccionario.
"""

import json
import re
from pathlib import Path

# Palabras genéricas que NO son habilidades. Se excluyen siempre.
BLACKLIST: set[str] = {
    "skills", "skill", "work", "personal", "information", "knowledge",
    "nationality", "company", "companies", "project", "projects", "name",
    "address", "email", "phone", "mobile", "objective", "summary", "profile",
    "reference", "references", "hobby", "hobbies", "declaration", "date",
    "birth", "gender", "marital", "status", "year", "years", "month",
    "experience", "education", "details", "resume", "cv", "page", "total",
}

# Extrae cadenas entre comillas simples o dobles de un archivo TypeScript.
_TS_STRING = re.compile(r"['\"]([A-Za-z0-9+#./&\- ]{2,40})['\"]")


def _strings_from_ts(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {match.strip().lower() for match in _TS_STRING.findall(text)}


def _load_keyword_dataset(refs_dir: Path) -> set[str]:
    lexicon: set[str] = set()
    json_path = refs_dir / "ats_resume_keyword_dataset" / "keywords.json"
    if not json_path.exists():
        return lexicon
    for entry in json.loads(json_path.read_text(encoding="utf-8")):
        lexicon.add(entry["keyword"].strip().lower())
        for synonym in entry.get("synonyms", []):
            lexicon.add(str(synonym).strip().lower())
    return lexicon


def _load_screener(refs_dir: Path) -> set[str]:
    base = refs_dir / "ats_screener"
    lexicon = _strings_from_ts(base / "skills-taxonomy.ts")
    lexicon |= _strings_from_ts(base / "synonyms.ts")
    return lexicon


def _load_job_skills(csv_path: Path, max_rows: int = 50_000) -> set[str]:
    """Toma nombres de habilidades de las primeras filas de job_skills.csv."""
    lexicon: set[str] = set()
    if not csv_path.exists():
        return lexicon
    with open(csv_path, encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            if index == 0 or index > max_rows:
                continue
            parts = line.split(",", 1)
            if len(parts) < 2:
                continue
            for skill in parts[1].split(","):
                skill = skill.strip().strip('"').lower()
                if 1 < len(skill) <= 40:
                    lexicon.add(skill)
    return lexicon


def build_skill_lexicon(
    refs_dir: Path,
    job_skills_csv: Path | None = None,
    include_job_skills: bool = True,
) -> set[str]:
    lexicon = set()
    lexicon |= _load_keyword_dataset(refs_dir)
    lexicon |= _load_screener(refs_dir)
    if include_job_skills and job_skills_csv is not None:
        lexicon |= _load_job_skills(job_skills_csv)

    # Saneamos: quitamos lista negra y cadenas demasiado cortas.
    return {item for item in lexicon if item not in BLACKLIST and len(item) >= 2}
