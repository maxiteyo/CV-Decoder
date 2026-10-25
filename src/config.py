"""Parámetros y rutas centrales del proyecto CV-Decoder.

Tener todo en un solo lugar evita repetir rutas por los scripts y hace que el
proyecto sea reproducible (cualquiera que lo clone obtiene las mismas carpetas).
"""

from pathlib import Path

# --- Rutas base (relativas a la raíz del repositorio) ---
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"
MODELS_DIR = ROOT / "models"

# --- Rutas de los datos crudos ---
DATATURKS_PATH = RAW_DIR / "cvs_ner" / "Entity Recognition in Resumes.json"
MEHYARMLAWEH_DIR = RAW_DIR / "cvs_habilidades" / "ResumesJsonAnnotated"
JOB_SKILLS_CSV = RAW_DIR / "habilidades" / "job_skills.csv"
POSTINGS_CSV = RAW_DIR / "vacantes" / "postings.csv"
REFS_DIR = RAW_DIR / "referencias"

# --- Salidas procesadas ---
NER_DIR = PROCESSED_DIR / "ner"

# --- Benchmarks (PDFs de prueba y su texto esperado) ---
PDFS_DIR = BENCHMARKS_DIR / "pdfs"
# PDFs reales juntados por el equipo + etiquetas hechas a mano.
PDFS_REALES_DIR = BENCHMARKS_DIR / "pdfs_reales"
PDFS_REALES_LABELS = PDFS_REALES_DIR / "labels.csv"

# --- Reproducibilidad ---
SEED = 42
