# Metodología de datos — CV-Decoder

Este documento explica **qué datos usa el proyecto, de dónde salen, cómo se
procesan y qué limitaciones tienen**. Está pensado para que la cátedra pueda
auditar y reproducir cada decisión.

> **Documento complementario.** El pipeline oficial del producto es el de
> `src/` y `scripts/eval_*.py` (ver `docs/etapa-a-resultados.md` y
> `docs/etapa-b-resultados.md`). Acá se documenta la **curación de datasets**
> y **validaciones auxiliares**. La definición oficial de parseabilidad es
> `src.parsing.quality.is_parseable` (≥30 palabras y ratio alfanumérico ≥0.5);
> el `token_f1` es una validación complementaria de fidelidad de extracción.

---

## 1. Inventario de datasets

| # | Dataset | Origen | Licencia | Volumen | Idioma | Uso en CV-Decoder |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **DataTurks — Entity Recognition in Resumes** | Kaggle `dataturks/resume-entities-for-ner` | Ver ficha | 220 CV anotados, 10 entidades | EN | **Entrenamiento del NER** (núcleo). |
| 2 | **NER-Annotated-CVs (Mehyarmlaweh)** | Kaggle/GitHub `mehyarmlaweh` | MIT | 5.029 CV, solo etiqueta `SKILL` | EN | **Refuerzo de HABILIDAD** tras limpieza. Nunca en test. |
| 3 | **LinkedIn Job Postings (Arshkon)** | Kaggle `arshkon/linkedin-job-postings` | CC BY-SA 4.0 | ~124.000 ofertas | EN | Corpus de **ofertas**, vocabulario de skills, pares CV–oferta. |
| 4 | **1.3M LinkedIn Jobs & Skills (Asaniczka)** | Kaggle `asaniczka` | ODC-By | 1,29M filas de skills | EN | **Frecuencias de skills** (muestreado). |
| 5 | **ATS Resume Keyword Dataset (Sahme115)** | GitHub `Sahme115` | MIT | 116 keywords, 10 roles | EN | **Diccionario de sinónimos** para `skills gap`. |
| 6 | **ats-screener (sunnypatell)** | GitHub `sunnypatell` | MIT | Código (no dataset) | EN | **Referencia de diseño**: reglas ATS, taxonomía, detector de secciones. |
| 7 | **Resume Dataset (amineipad)** | Kaggle `amineipad/resumecv-dataset` | MIT | 100 archivos (66 PDF + 34 JPG) | FR / EN | **Reporte de idioma y parseabilidad** (script 1). |
| 8 | **Resume Dataset (snehaanbhawal)** | Kaggle `snehaanbhawal/resume-dataset` | CC0 | 2.484 PDF + CSV | EN | **Benchmark de parseabilidad** (script 2). |
| 9 | **Annotated NER PDF Resumes (Mehyaar)** | HuggingFace `Mehyaar/Annotated_NER_PDF_Resumes` | MIT | 5.035 PDF + 5.029 JSON | EN (~99%) | **Corpus extra de PDF en inglés**; es la fuente original de los JSON de la fila 2. |

> Los datasets crudos viven en `data/raw/` y **no se versionan** (ver `.gitignore`).
> Los derivados limpios van a `data/processed/`. Los benchmarks curados van a
> `data/benchmarks/`.

---

## 2. Script auxiliar 1 — Clasificación de idioma y capa de texto

**Archivo:** `scripts/classify_cv_languages.py`
**Dataset:** `amineipad/resumecv-dataset` (66 PDF + 34 JPG, francés/inglés).

### Qué resuelve
Este dataset mezcla CV **en francés e inglés** sin ninguna etiqueta de idioma, y
un tercio de los archivos son **JPG** (escaneados). El script:

1. **Detecta el idioma** de cada archivo para poder filtrar solo los ingleses.
2. **Determina si un ATS podría leerlo**, lo que permite demostrar que los JPG
   y los PDF escaneados **no pasan** un filtro ATS.

### Cómo se decide cada cosa

| Situación | Extracción | Idioma | `tiene_capa_texto` | `ats_parseable` |
| :--- | :--- | :--- | :--- | :--- |
| PDF con texto | `read_pdf` (oficial) | `lingua` sobre el texto | `True` | `is_parseable(texto)` |
| PDF escaneado (0 chars) | — | OCR opcional | `False` | `False` |
| JPG / imagen | OCR opcional | OCR opcional (`lingua`) | `False` | `False` |

**Umbrales elegidos y por qué:**

- `--min-chars 50`: un PDF con menos de 50 caracteres se considera sin capa de
  texto (columna `tiene_capa_texto`). **No** define la parseabilidad ATS.
- **Parseabilidad ATS**: se usa `is_parseable` **oficial**
  (`src/parsing/quality.py`: ≥30 palabras y ratio alfanumérico ≥0.5), la misma
  que el motor de diagnóstico. Un solo criterio en todo el proyecto.
- `MIN_CONFIDENCE = 0.65`: por debajo, el archivo va a `review` en lugar de
  arriesgar una clasificación errónea.
- Detector `lingua`: elegido por ser **offline, determinístico y robusto en
  textos cortos**. `langdetect` es aleatorio salvo semilla y peor en textos
  con nombres propios/siglas.

### Resultados sobre el dataset real (sin OCR)

Ejecución del 2026-10-25 sobre `data/raw/cvs_pdf_fr_en` (100 archivos).
Re-verificada con la métrica oficial `is_parseable` (2026-11-02): mismos
valores.

| Grupo | Archivos | Idioma |
| :--- | ---: | :--- |
| PDF con capa de texto | **58** | **3 inglés** / **55 francés** |
| PDF escaneado (sin texto) | 8 | desconocido |
| JPG (imagen) | 34 | desconocido |
| **Total** | **100** | |

- Parseables por ATS (`is_parseable` oficial): **58/100 (58%)**; no
  parseables: **42/100 (42%)**.
- Los 3 CV en inglés son `CV_GhandiAli.pdf`, `CV_RashidSaid.pdf` y
  `CV_ShihabAmri.pdf` (copiados a `data/processed/cvs_en/`).
- **Validación cruzada:** se comparó `lingua` contra un heurístico de palabras
  funcionales FR/EN sobre los 58 PDF con texto. Coincidencia **100%** (3/3 en,
  55/55 fr, sin desacuerdos), así que el bajo número de ingleses es real: el
  dataset es casi enteramente francés, no un error del detector.
- Los 42 archivos sin texto no se clasificaron por idioma porque requerirían
  OCR; para el objetivo del proyecto son **irrelevantes** (son exactamente los
  que un ATS no puede leer).

### Limitaciones
- El idioma de archivos sin capa de texto depende del OCR (ruidoso).
- Un CV bilingüe se asigna al idioma dominante.
- Este dataset es **pequeño (100) y desbalanceado** (3 EN vs 55 FR); sirve para
  demostrar parseabilidad e idioma, no para entrenar.
- Con `lingua` restringido a EN/FR/ES, un CV en otro idioma (p. ej. árabe) cae
  en el idioma latino más parecido; por eso existe la categoría `review`.

---

## 3. Script auxiliar 2 — Validación de fidelidad de extracción

**Archivo:** `scripts/build_parseability_benchmark.py`
**Dataset:** `snehaanbhawal/resume-dataset` (2.484 PDF, 24 categorías).

### Qué resuelve
Este script **no reemplaza** la medición oficial de parseabilidad (210 PDFs
reales, `docs/etapa-b-resultados.md`). Aporta algo distinto: para cada PDF
compara el texto que extrae `read_pdf` contra su `Resume_str`, lo que permite
medir de forma **automática y estadística** (no a mano) la **fidelidad de la
extracción**. Además reporta `parseable_oficial` con la misma métrica que usa
el motor de diagnóstico.

### Métricas

- **`parseable_oficial`**: `src.parsing.quality.is_parseable` (≥30 palabras y
  ratio alfanumérico ≥0.5). Es la **definición oficial** de parseabilidad.
- **`token_f1`** (fidelidad): F1 de bolsas de tokens entre el texto extraído y
  el de referencia. Usa `Counter` e intersección por mínimo de frecuencias. Es
  **tolerante al orden**, necesario porque los bloques del PDF y del HTML
  scrapeado no tienen por qué aparecer en el mismo orden.
- **`ratio`** (respaldo): similitud de secuencia con `difflib`. Penaliza el
  distinto orden, por eso es más estricta.
- **`parseable_similitud`**: `token_f1 >= --threshold`, con `--threshold` por
  defecto `0.70`. Es una señal complementaria, **no** la métrica oficial.

### Cómo calibrar el umbral
El valor 0.70 es un punto de partida, **no una verdad**. Para calibrarlo:

1. Correr el script y mirar la distribución (`p10/p50/p90` que imprime el
   resumen).
2. Inspeccionar manualmente los "peores casos" que lista el script.
3. Ajustar el umbral según dónde aparezca la separación natural entre PDFs bien
   y mal extraídos, y **dejarlo documentado** aquí.

### Resultados sobre el dataset real

Ejecución completa del 2026-10-25 sobre `data/raw/cvs_parseabilidad`
(2.484 PDF, 24 categorías, ~22 min). Los valores de `token_f1` corresponden a
la primera ejecución (criterio de fidelidad); el script actual agrega
`parseable_oficial` con `is_parseable`:

| Métrica | Valor |
| :--- | :--- |
| PDF evaluados | **2.484** |
| Parseables (`token_f1 >= 0.70`) | **2.482 (99,9%)** |
| No parseables | **2 (0,1%)** |
| `token_f1` medio | **0,9904** |
| `token_f1` p10 / p50 / p90 | 0,980 / 0,994 / 1,000 |
| `token_f1` mínimo | 0,000 |
| Errores de lectura | 0 |

**Idioma:** se muestrearon 120 PDF al azar (semilla 42) y **120/120 están en
inglés** y tienen capa de texto. Es decir, este dataset también sirve como
**corpus de 2.484 PDF en inglés con texto** (no solo como benchmark). Caveat:
son PDFs de formato homogéneo (misma plantilla), por eso la parseabilidad es tan
alta; para variedad de layouts hay que complementar con el dataset `amineipad`.

Los 2 fallos:

1. `12632728.pdf` (BUSINESS-DEVELOPMENT): **sin capa de texto** (escaneado),
   `token_f1 = 0`. Es el único PDF del dataset que no es digital.
2. `14663897.pdf` (CHEF): extrajo 10.260 caracteres contra 34.366 de
   referencia (`token_f1 = 0,452`). Es el único caso con pérdida grande de texto
   (probable PDF con tablas/columnas o texto en imágenes).

**Decisión de calibración:** se **mantiene el umbral 0,70**. La distribución es
muy compacta (p10 = 0,98), así que subir el umbral a 0,90 solo agregaría 7 falsos
negativos (archivos con extracción levemente distinta, no rotos). Con 0,70 se
aíslan limpiamente los 2 casos realmente problemáticos.

### Advertencia sobre la representatividad

El 99,9% de fidelidad **no significa que el 99,9% de los CV del mundo sean
parseables**: este dataset está compuesto casi en su totalidad por PDF
**digitales homogéneos**. Sirve como **línea base de PDFs "limpios"**, no como
muestra de la variedad real (escaneados, 2 columnas, tablas). Esa variedad la
aporta el dataset `amineipad`. Además, la **medición oficial** de parseabilidad
del proyecto es sobre 210 PDFs reales (`docs/etapa-b-resultados.md`), no sobre
este corpus. En el informe hay que presentar **ambos** números, cada uno con su
corpus, para no sobreestimar.

### Limitación importante (declarar en el informe)
`Resume_str` proviene del **HTML scrapeado**, no del PDF. Por lo tanto:

- Puede haber diferencias de espacios, orden, encabezados y saltos.
- **No es ground-truth perfecto**, sino **texto de referencia aproximado**.

Por eso se normaliza (minúsculas, sin acentos, sin puntuación, espacios
colapsados) y se usa una medida tolerante. La similitud tiende a **subestimar**
levemente la calidad real de la extracción; aun así, sirve para comparar
formatos y detectar PDFs rotos.

---

## 4. Corpus extra de PDFs en inglés (Mehyaar)

**Dataset:** `Mehyaar/Annotated_NER_PDF_Resumes` (HuggingFace, MIT).
Es la **fuente original** de los 5.029 JSON de Mehyarmlaweh (fila 2): aporta
`ResumesPDF.zip` (los PDFs) y `ResumesJsonAnnotated.zip` (las anotaciones). Los
JSON ya los teníamos; lo que faltaba eran **los PDFs**.

**Ejecución del 2026-10-25** (`scripts/classify_cv_languages.py` sobre 5.035
PDF):

| Grupo | Cantidad |
| :--- | ---: |
| PDF totales | 5.035 |
| **Inglés usable (con texto)** | **4.940** |
| PDF escaneado / sin texto | 53 (47 con 0 chars + 6 con solo "Scanned by CamScanner") |
| Español | 21 |
| Francés | 13 |
| Corruptos / ilegibles | 6 |
| Detectado EN pero no usable (texto garbled o hebreo) | 2 |

- Corpus limpio: `data/processed/cvs_en_extra/` (**4.940 PDF**).
- Reportes: `data/processed/cv_language_report_extra.csv` (los 5.035) y
  `data/processed/cv_language_report_extra_en.csv` (solo los 4.940 usables).
- `data/raw/cvs_pdf_en_extra/` se deja **intacto** (5.035) para trazabilidad; los
  descartes **no se borran**.

> **Corpus auxiliar:** el pipeline oficial **no usa** este corpus de PDFs (usa
> 210 PDFs reales en `data/benchmarks/`). Estos datos quedan en local, sin
> versionar, como material de curación y de futuras validaciones.

**Total de PDF en inglés del proyecto: 7.427** (2.487 previos + 4.940 nuevos).
De ese total, **7.426 tienen capa de texto** (1 del corpus original está
escaneado).

**Caveats:** son los mismos CVs que los JSON de Mehyarmlaweh (anotaciones solo
`SKILL` y ruidosas); contienen datos personales reales (anonimizar si se
publica); layouts variados (1–12 páginas), lo que aporta la diversidad de la que
carecía el corpus de plantilla LiveCareer.

---

## 5. Normalización de texto en estas validaciones

- `token_f1` y `ratio` normalizan antes de comparar: NFKD, sin acentos, sin
  puntuación, minúsculas, espacios colapsados.
- `is_parseable` (oficial) mide palabras y ratio alfanumérico sobre el texto
  crudo, sin normalizar.
- Estos scripts **no entrenan modelos**: no hay split train/test ni riesgo de
  data leakage. La semilla global `42` solo garantiza determinismo.

---

## 6. Reproducibilidad

- Semilla fija (`src/utils/seeds.py`) en todos los scripts.
- Dependencias con versiones exactas (`requirements.txt`).
- Cada script escribe su reporte en `data/processed/` con columnas estables.

```bash
# Clasificación de idioma (auxiliar 1)
python scripts/classify_cv_languages.py \
  --input data/raw/cvs_pdf_fr_en \
  --output data/processed/cv_language_report.csv

# Validación de fidelidad (auxiliar 2)
python scripts/build_parseability_benchmark.py \
  --dataset-dir data/raw/cvs_parseabilidad \
  --output data/processed/parseability_report.csv
```

---

## 7. Relación con el pipeline oficial

| Tema | Oficial (motor) | Este documento (auxiliar) |
| :--- | :--- | :--- |
| Parseabilidad | `src/parsing/quality.is_parseable` | Lo reutiliza + `token_f1` |
| Extracción PDF | `src/parsing/pdf_reader.read_pdf` | Lo reutiliza |
| Corpus | 210 PDFs reales + 60 sintéticos | 100 amineipad, 2.484 LiveCareer, 5.035 Mehyaar |
| Scripts | `scripts/eval_*.py` | `scripts/classify_cv_languages.py`, `scripts/build_parseability_benchmark.py` |
| Datos | `data/benchmarks/` (ignorado, se regenera) | `data/raw/`, `data/processed/` (ignorados) |
| Resultados | `docs/etapa-a-resultados.md`, `docs/etapa-b-resultados.md` | Este documento |
- Mismo dataset + mismo comando → mismo resultado.
