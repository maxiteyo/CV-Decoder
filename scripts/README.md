# Scripts de datos auxiliares

Scripts de **curación de datos y validación** del proyecto CV-Decoder. Son
**complementarios** al pipeline oficial: no forman parte del motor de
diagnóstico (ver `src/`, `scripts/eval_*.py` y `docs/informe/etapa-b-resultados.md`).

Cada script es ejecutable de forma independiente y reproducible (semilla 42).

## Requisitos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Para el OCR opcional hay que instalar el binario del sistema:

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-spa
pip install pytesseract
```

## 1. `classify_cv_languages.py`

**Qué hace:** recorre una carpeta de CVs (PDF e imágenes) y responde dos cosas
por archivo, de forma **independiente**:

1. **Idioma** (`en` / `fr` / `es` / `other` / `unknown` / `sin_texto`).
2. **Parseabilidad ATS** (`ats_parseable`): usa la **definición oficial** del
   proyecto, `src.parsing.quality.is_parseable` (≥30 palabras y ratio
   alfanumérico ≥0.5). Un PDF escaneado o un JPG dan `False`.

**Por qué importa:** un ATS descarta CVs sin capa de texto (escaneados, JPG).
Este script lo demuestra con evidencia y clasifica el idioma para filtrar el
corpus. El OCR solo se usa para *adivinar el idioma* de archivos sin texto,
nunca para marcarlos como parseables. La extracción usa el lector oficial
`src.parsing.pdf_reader.read_pdf` (pdfminer.six + pdfplumber).

**Dataset objetivo:** `amineipad/resumecv-dataset` (100 CV: 66 PDF + 34 JPG,
francés/inglés).

**Descarga:**
```bash
kaggle datasets download -d amineipad/resumecv-dataset \
  -p data/raw/cvs_pdf_fr_en --unzip
```

**Uso:**
```bash
python scripts/classify_cv_languages.py \
  --input data/raw/cvs_pdf_fr_en \
  --output data/processed/cv_language_report.csv \
  --keep-en-dir data/processed/cvs_en --copy --ocr
```

**Flags:** `--input`, `--output`, `--keep-en-dir`, `--copy`/`--symlink`,
`--ocr`, `--min-chars` (default 50, solo para `tiene_capa_texto`),
`--seed` (default 42), `--verbose`.

**Columnas del CSV:**

| Columna | Significado |
| :--- | :--- |
| `archivo` | Nombre del archivo. |
| `extension` | `.pdf`, `.jpg`, etc. |
| `paginas` | Cantidad de páginas (solo PDF). |
| `caracteres_extraidos` | Caracteres de texto obtenidos (0 = sin capa de texto). |
| `tiene_capa_texto` | `True` si el PDF trae texto (≥ `--min-chars`). |
| `ats_parseable` | `True` si pasa `is_parseable` (métrica oficial). |
| `idioma` | Idioma detectado. |
| `confianza` | Confianza de la detección (0–1). |
| `metodo` | `texto_pdf` / `ocr` / `ninguno`. |
| `estado` | `ok` / `needs_ocr` / `imagen` / `baja_confianza` / `error`. |
| `decision` | `keep_en` / `discard_fr` / `discard_es` / `discard_other` / `review` / `needs_ocr`. |
| `notas` | Observaciones (motivo de fallo, OCR, etc.). |

**Reglas de decisión (documentadas):**

- PDF con texto: detecta idioma sobre el texto → `keep_en` o `discard_*`.
  `ats_parseable` = `is_parseable(texto)`.
- PDF escaneado (0 chars): `needs_ocr`, `ats_parseable=False`.
- Imagen: `imagen`, `ats_parseable=False`; con `--ocr` intenta estimar idioma.
- Confianza < `MIN_CONFIDENCE` (0.65) → `review` (revisión manual).

## 2. `build_parseability_benchmark.py`

**Qué hace:** valida **dos cosas** sobre PDFs reales:

1. **Parseabilidad oficial** (`parseable_oficial`): `is_parseable` del
   proyecto, la misma que usa el motor de diagnóstico.
2. **Fidelidad de extracción** (`token_f1`, `parseable_similitud`): compara el
   texto extraído con `read_pdf` contra el `Resume_str` de referencia.
   Es una validación **complementaria**, no la métrica oficial.

**Dataset objetivo:** `snehaanbhawal/resume-dataset` (2.484 CV reales, 24
categorías). Aporta los PDFs y, para cada uno, su `Resume_str` (texto esperado).

**Descarga:**
```bash
kaggle datasets download -d snehaanbhawal/resume-dataset \
  -p data/raw/cvs_parseabilidad --unzip
```

**Uso:**
```bash
# Todos los PDFs
python scripts/build_parseability_benchmark.py \
  --dataset-dir data/raw/cvs_parseabilidad \
  --output data/processed/parseability_report.csv

# Muestra rápida
python scripts/build_parseability_benchmark.py \
  --dataset-dir data/raw/cvs_parseabilidad --limit 50
```

**Flags:** `--dataset-dir`, `--output`, `--limit`, `--threshold` (default 0.70,
solo para `parseable_similitud`), `--seed`, `--verbose`.

**Métricas:**

- `parseable_oficial`: `is_parseable` (≥30 palabras + ratio alfanumérico ≥0.5).
- `token_f1`: F1 de bolsas de tokens (tolera distinto orden de bloques).
- `ratio`: similitud de secuencia con `difflib` (respaldo, más estricta).
- `parseable_similitud`: `token_f1 >= --threshold`.

**Columnas del CSV:** `id, categoria, archivo, paginas, caracteres_pdf,
caracteres_ref, token_f1, ratio, parseable_oficial, parseable_similitud,
estado, notas`.

**Limitación documentada:** `Resume_str` proviene del HTML scrapeado, no del
PDF, así que **no es ground-truth perfecto**. Por eso se normaliza el texto y se
usa una medida tolerante. Ver `docs/informe/metodologia-datos.md`.

## Relación con el pipeline oficial

| Tema | Oficial (motor) | Estos scripts (auxiliar) |
| :--- | :--- | :--- |
| Parseabilidad | `src/parsing/quality.is_parseable` | Lo reutilizan + `token_f1` |
| Extracción PDF | `src/parsing/pdf_reader.read_pdf` | Lo reutilizan |
| Corpus | 210 PDFs reales + 60 sintéticos | 100 amineipad, 2.484 LiveCareer |
| Evaluación | `scripts/eval_*.py` | Este directorio |

## Reproducibilidad

- Semilla global 42 (`src/utils/seeds.py`) en ambos scripts.
- Sin pasos aleatorios: mismo dataset → mismo reporte.
- Las dependencias están fijadas en `requirements.txt`.
