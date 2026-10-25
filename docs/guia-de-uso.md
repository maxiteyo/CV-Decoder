# Guía de uso y reproducción — CV-Decoder

**Para quién es esta guía:** cualquier persona que quiera probar la API o
reproducir el proyecto desde cero, aunque no haya visto el código antes.

**Qué necesitás:** una computadora con Linux o macOS, **Python 3.12** y conexión
a internet para la instalación inicial. No hace falta GPU. (El proyecto se probó
con Python 3.12.3; las versiones fijadas de `numpy` y `pandas` no instalan en
3.10/3.11.)

**Tiempo:** 5 minutos si el proyecto ya está instalado; 30–45 minutos desde cero,
sin contar la descarga de datasets opcionales.

> Si ya tenés el proyecto funcionando en esta máquina, andá directo al
> [Camino A](#2-camino-a-probarlo-ya-5-minutos). Si clonaste el repositorio en otra
> máquina, seguí el [Camino B](#3-camino-b-instalarlo-desde-cero).

## Índice

1. [Qué hace el sistema](#1-qué-hace-el-sistema)
2. [Camino A: probarlo ya (5 minutos)](#2-camino-a-probarlo-ya-5-minutos)
3. [Camino B: instalarlo desde cero](#3-camino-b-instalarlo-desde-cero)
4. [Cómo leer el resultado](#4-cómo-leer-el-resultado)
5. [Errores frecuentes y qué hacer](#5-errores-frecuentes-y-qué-hacer)
6. [Reproducir las métricas](#6-reproducir-las-métricas)
7. [Qué se puede reproducir y qué no](#7-qué-se-puede-reproducir-y-qué-no)
8. [Mapa de archivos y documentos](#8-mapa-de-archivos-y-documentos)
9. [Glosario](#9-glosario)
10. [Apéndice A: crear un CV de ejemplo](#apéndice-a-crear-un-cv-de-ejemplo)
11. [Apéndice B: crear un PDF escaneado de prueba](#apéndice-b-crear-un-pdf-escaneado-de-prueba)

---

## 1. Qué hace el sistema

CV-Decoder recibe dos cosas:

- un **CV en formato PDF**;
- el **texto de una oferta laboral**.

Y devuelve un **JSON** con un puntaje global de 0 a 100 y el detalle de cuatro
dimensiones:

| Dimensión | Peso | Qué mide |
|---|---:|---|
| Similitud CV–oferta | 40 % | Qué tanto se parecen los textos (motor TF-IDF). |
| Completitud de secciones | 25 % | Si están Contacto, Experiencia, Educación y Habilidades. |
| Brecha de palabras clave | 20 % | Qué términos pide la oferta y no aparecen en el CV. |
| Parseabilidad | 15 % | Si el PDF tiene texto legible o es un escaneo. |

El puntaje global es una **suma ponderada** de esas cuatro dimensiones. No es una
probabilidad ni una nota oficial: sirve para **comparar y priorizar mejoras**.

El flujo completo es:

```text
PDF del CV  +  texto de la oferta
        │
        ▼
 POST /api/v1/analyze-cv
        │
        ▼
 JSON con puntaje global y las 4 dimensiones
```

La API **no guarda nada**: el PDF se escribe en un archivo temporal, se procesa y
se borra. No hay base de datos, login ni historial.

---

## 2. Camino A: probarlo ya (5 minutos)

Usá este camino si el repositorio ya está en esta máquina y el entorno virtual
`.venv` ya tiene las dependencias instaladas.

### A.1. Verificar que esté todo

```bash
cd /home/maximo/Escritorio/CV-Decoder
source .venv/bin/activate
python --version
test -d models/ner_dataturks_sm && echo "Modelo OK" || echo "FALTA el modelo"
```

Qué deberías ver:

- `Python 3.12.x` (el proyecto se probó con 3.12.3).
- `Modelo OK`.

Si aparece `FALTA el modelo`, andá al [Camino B](#3-camino-b-instalarlo-desde-cero)
para generarlo. La API no puede arrancar sin él.

> **Qué es `.venv`:** una carpeta con una copia aislada de Python y las librerías
> del proyecto. Al activarla, los comandos `python` y `pip` usan esa copia y no
> la del sistema.

### A.2. Levantar la API (terminal 1)

```bash
uvicorn src.api.main:app --reload
```

Dejá esa terminal abierta. La primera vez tarda unos **8 segundos** porque carga
el modelo de entidades y calienta el motor de similitud. Cuando termina, muestra
algo parecido a:

```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

- `127.0.0.1` significa “esta computadora”.
- `8000` es el puerto. Si está ocupado, mirá la sección de errores.

Para detenerla, presioná `Ctrl+C` en esa terminal.

> Si el comando `uvicorn` no existe, probá con `.venv/bin/uvicorn
> src.api.main:app --reload`.

### A.3. Comprobar que está viva (terminal 2)

Abrí otra terminal, activá el entorno y consultá el endpoint de salud:

```bash
cd /home/maximo/Escritorio/CV-Decoder
source .venv/bin/activate
curl -s http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"estado":"ok","version":"0.1.0","modelo_entidades":"ner_dataturks_sm","motor_oficial":"tfidf"}
```

Si ves `estado: "ok"`, la API está lista.

### A.4. Probar desde el navegador (Swagger)

FastAPI genera sola una página para probar la API sin escribir código.

1. Abrí <http://127.0.0.1:8000/docs>.
2. Buscá la tarjeta **POST /api/v1/analyze-cv** y hacé clic para desplegarla.
3. Hacé clic en **Try it out**.
4. En **cv**, elegí un PDF de CV con capa de texto (que se pueda seleccionar texto
   al abrirlo). Si no tenés uno a mano, creá el del
   [Apéndice A](#apéndice-a-crear-un-cv-de-ejemplo).
5. En **oferta**, pegá el texto completo de una búsqueda laboral. Por ejemplo:

   ```text
   We are looking for a Data Analyst with strong Python and SQL skills.
   You will build dashboards, clean data and communicate findings to the team.
   Experience with Excel is required. Knowledge of Docker is a plus.
   Project management experience is valued.
   ```

6. En **motor**, dejá `tfidf` (es el oficial y el más rápido).
7. Hacé clic en **Execute**.

Abajo de todo aparece la respuesta con código **200**. Si usás el CV de ejemplo
del Apéndice A, el resultado esperado es aproximadamente:

| Campo | Valor |
|---|---:|
| `puntaje_global` | 96,7 |
| Parseabilidad | 100,0 |
| Secciones | 100,0 (las cuatro presentes) |
| Brecha de palabras clave | 83,3 (falta `project management`) |
| Similitud | 100,0 |

Con un CV real los números suelen ser más bajos. Por ejemplo, con el archivo
`cv (5).pdf` del equipo y la misma oferta:

| Campo | Valor |
|---|---:|
| `puntaje_global` | 54,6 |
| Parseabilidad | 100,0 |
| Secciones | 75,0 (falta Contacto) |
| Brecha de palabras clave | 33,3 (coinciden `excel` y `python`) |
| Similitud | 35,5 |

> Los valores exactos pueden variar unas décimas según la versión de las
> librerías. Lo importante es la estructura del JSON y la interpretación.

### A.5. Probar los errores desde Swagger

No todo PDF se puede diagnosticar. Estos casos son **esperados** y la API
responde con un error claro en lugar de un puntaje falso:

| Qué subís | Código HTTP | `codigo` | Por qué |
|---|---:|---|---|
| Un PDF escaneado (sin texto) | 422 | `PDF_SIN_TEXTO` | No hay capa de texto; haría falta OCR. |
| Una oferta de menos de 20 palabras | 422 | `OFERTA_MUY_CORTA` | No alcanza para comparar. |
| Un archivo que no termina en `.pdf` | 415 | `FORMATO_NO_SOPORTADO` | La extensión no es PDF. |
| Un `.pdf` que no empieza con `%PDF` | 415 | `NO_ES_PDF` | El contenido no es un PDF real. |
| Un archivo de 0 bytes | 400 | `PDF_VACIO` | No tiene contenido. |
| Un PDF de más de 5 MB | 413 | `PDF_MUY_GRANDE` | Supera el límite del MVP. |
| Un PDF dañado o con contraseña | 422 | `PDF_ILEGIBLE` | No se puede abrir. |

Todos los errores tienen la misma forma:

```json
{
  "error": {
    "codigo": "PDF_SIN_TEXTO",
    "mensaje": "El PDF no tiene texto usable (0 palabras y 1 imágenes detectadas).",
    "sugerencia": "Es un escaneo o una foto. Subí un PDF con capa de texto..."
  }
}
```

Para probar el caso del escaneo, generá un PDF de prueba con el
[Apéndice B](#apéndice-b-crear-un-pdf-escaneado-de-prueba) y subilo desde Swagger.
Para el caso de la oferta corta, pegá solo `Buscamos un analista de datos` y
ejecutá.

### A.6. Probar desde la consola con el script incluido

El script `scripts/cliente_api.py` usa solo la biblioteca estándar de Python, así
que no agrega dependencias. Con la API corriendo en otra terminal:

```bash
# Oferta escrita a mano
.venv/bin/python scripts/cliente_api.py \
  --pdf /tmp/cv_ejemplo.pdf \
  --oferta "We are looking for a Data Analyst with strong Python and SQL skills.
You will build dashboards, clean data and communicate findings to the team.
Experience with Excel is required. Knowledge of Docker is a plus.
Project management experience is valued."

# O un par de la planilla del equipo (si tenés data/benchmarks/pares_para_calificar.csv)
.venv/bin/python scripts/cliente_api.py \
  --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" \
  --par par_005
```

Opciones útiles:

| Opción | Para qué |
|---|---|
| `--pdf` | Ruta del CV en PDF (obligatoria). |
| `--oferta` | Texto de la oferta escrito en el comando. |
| `--oferta-archivo` | Archivo `.txt` con la oferta. |
| `--par` | ID de un par de la planilla (`par_005`, etc.). |
| `--motor` | `tfidf` (oficial), `embeddings` o `embeddings_fragmentos`. |
| `--url` | URL base si la API corre en otro puerto. |

### A.7. Probar con `curl`

Si preferís no usar el script:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/analyze-cv" \
  -F "cv=@/tmp/cv_ejemplo.pdf" \
  -F "oferta=We are looking for a Data Analyst with strong Python and SQL skills. You will build dashboards, clean data and communicate findings to the team. Experience with Excel is required. Knowledge of Docker is a plus. Project management experience is valued." \
  -F "motor=tfidf" | .venv/bin/python -m json.tool
```

`-F` arma el formulario `multipart/form-data`; `@` indica que el valor es un
archivo; `| python -m json.tool` ordena el JSON para leerlo mejor.

### A.8. Correr las pruebas automáticas

```bash
.venv/bin/python -m pytest -q
```

Resultado esperado:

```text
................                                                         [100%]
16 passed in 27.00s
```

Las 16 pruebas **generan sus propios PDFs** (legibles, escaneados y rotos) con
`fpdf2` y `Pillow`, así que no dependen de `data/`. La primera corrida tarda unos
30 segundos por la carga del modelo; las siguientes son más rápidas.

### A.9. Detener todo

1. En la terminal de la API, presioná `Ctrl+C`.
2. Verificá que no queden archivos temporales:

   ```bash
   ls /tmp | grep cv_decoder || echo "Sin temporales: la API limpió bien"
   ```

---

## 3. Camino B: instalarlo desde cero

Este camino asume que el repositorio está clonado en una máquina nueva y que
`data/` y `models/` están vacíos, como ocurre después de un `git clone`.

> **Importante:** `data/` y `models/` **no están en Git** (son datos y artefactos
> binarios). Por eso, para que la API funcione hay que descargar unos datos
> mínimos y entrenar el modelo. La buena noticia es que **no necesitás los 221
> PDFs reales ni las calificaciones humanas** para probar la API.

### B.1. Clonar el repositorio

```bash
git clone https://github.com/maxiteyo/CV-Decoder.git
cd CV-Decoder
```

### B.2. Crear el entorno e instalar dependencias

Requisitos: **Python 3.12** y `git`. Las versiones fijadas de `numpy` (2.5.4) y
`pandas` (3.0.6) no instalan en Python 3.10/3.11.

```bash
python3 --version          # tiene que decir 3.12.x
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip

# PyTorch en versión CPU (no requiere GPU)
pip install "torch==2.14.1+cpu" --index-url https://download.pytorch.org/whl/cpu

# Resto de las dependencias fijadas
pip install -r requirements.txt

# Modelo base de spaCy en inglés (se usa para entrenar el NER)
python -m spacy download en_core_web_sm
```

Qué hace cada paso:

- `venv` crea el entorno aislado.
- `torch` es la librería de aprendizaje profundo; la versión `+cpu` es más
  liviana y no necesita tarjeta gráfica.
- `requirements.txt` fija las versiones exactas de todo lo demás.
- `en_core_web_sm` es el modelo base en inglés sobre el que se entrena el
  reconocedor de entidades.

Verificación rápida:

```bash
python -c "import spacy, fastapi, sklearn, torch; print('Dependencias OK')"
```

Si `torch` falla al instalarse, probá sin fijar la versión:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### B.3. Descargar los datos mínimos

Para **entrenar el modelo y probar la API** alcanza con dos cosas:

1. El dataset **DataTurks** (CVs anotados).
2. Los dos repositorios de referencia que forman el diccionario de habilidades.

El resto de los datasets es opcional y sólo hace falta para reproducir métricas
completas.

#### B.3.1. DataTurks (obligatorio)

Página: <https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner>

Opción A, descarga manual:

1. Descargá el ZIP desde Kaggle.
2. Creá la carpeta y descomprimí ahí:
   ```bash
   mkdir -p data/raw/cvs_ner
   unzip ~/Descargas/resume-entities-for-ner.zip -d data/raw/cvs_ner
   ```
   (Cambiá `~/Descargas` por la carpeta donde bajaste el ZIP.)
3. Verificá que exista este archivo:

   ```text
   data/raw/cvs_ner/Entity Recognition in Resumes.json
   ```

Opción B, con la herramienta de Kaggle:

```bash
pip install kaggle
# Antes: descargá tu token desde Kaggle -> Settings -> Create New Token
# y guardalo en ~/.kaggle/kaggle.json
mkdir -p data/raw/cvs_ner
kaggle datasets download -d dataturks/resume-entities-for-ner \
  -p data/raw/cvs_ner --unzip
ls data/raw/cvs_ner
```

Si el nombre del archivo cambió, renombralo a
`Entity Recognition in Resumes.json` (es la ruta que espera `src/config.py`).

#### B.3.2. Diccionario de habilidades (obligatorio)

Son dos repositorios pequeños de GitHub. Se clonan dentro de
`data/raw/referencias/`:

```bash
mkdir -p data/raw/referencias
git clone https://github.com/Sahme115/ats-resume-keyword-dataset \
  data/raw/referencias/ats_resume_keyword_dataset
git clone https://github.com/sunnypatell/ats-screener \
  data/raw/referencias/ats_screener
```

Verificación:

```bash
ls data/raw/referencias/ats_resume_keyword_dataset/keywords.json
ls data/raw/referencias/ats_screener/skills-taxonomy.ts
ls data/raw/referencias/ats_screener/synonyms.ts
```

Tienen que existir los tres archivos. El diccionario final ronda las **790
habilidades**.

#### B.3.3. Datasets opcionales

| Dataset | Para qué sirve | ¿Hace falta para la API? | Dónde va |
|---|---|---|---|
| [NER Annotated CVs](https://www.kaggle.com/datasets/mehyarmlaweh/ner-annotated-cvs) (5.029 CVs) | Refuerzo del entrenamiento. El modelo final **no lo usó**. | No | `data/raw/cvs_habilidades/ResumesJsonAnnotated/` |
| [LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) | Ofertas reales para calibrar la similitud y armar pares. | No | `data/raw/vacantes/postings.csv` |
| [1.3M LinkedIn Jobs & Skills](https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024) | Frecuencias de habilidades para el diccionario. | No | `data/raw/habilidades/job_skills.csv` |
| PDFs reales del equipo (221 archivos) | Medir parseabilidad real. | No | `data/benchmarks/pdfs_reales/` |
| Planilla de pares calificados (50 pares) | Medir Spearman contra notas humanas. | No | `data/benchmarks/pares_para_calificar.csv` |

Comandos de ejemplo para los opcionales:

```bash
# Refuerzo (600 MB; el script funciona igual si no está)
mkdir -p /tmp/mehyar data/raw/cvs_habilidades
kaggle datasets download -d mehyarmlaweh/ner-annotated-cvs \
  -p /tmp/mehyar --unzip
# Mover la carpeta que contiene directamente los .json
origen=$(dirname "$(find /tmp/mehyar -name '*.json' | head -1)")
mv "$origen" data/raw/cvs_habilidades/ResumesJsonAnnotated

# Ofertas de LinkedIn (500 MB)
mkdir -p data/raw/vacantes
kaggle datasets download -d arshkon/linkedin-job-postings \
  -p data/raw/vacantes --unzip

# Frecuencias de habilidades
mkdir -p data/raw/habilidades
kaggle datasets download -d asaniczka/1-3m-linkedin-jobs-and-skills-2024 \
  -p data/raw/habilidades --unzip
```

> Si el ZIP anida carpetas, buscá el archivo con
> `find data/raw -name postings.csv` y movelo a la ruta exacta de la tabla.

#### B.3.4. Verificar las rutas

Este comando muestra qué encontró el proyecto y qué falta:

```bash
.venv/bin/python - <<'PY'
from src import config

rutas = {
    "DataTurks": config.DATATURKS_PATH,
    "Refuerzo": config.MEHYARMLAWEH_DIR,
    "job_skills.csv": config.JOB_SKILLS_CSV,
    "postings.csv": config.POSTINGS_CSV,
    "Referencias": config.REFS_DIR,
}
for nombre, ruta in rutas.items():
    estado = "OK" if ruta.exists() else "FALTA (opcional)"
    print(f"{nombre:16} {estado:18} {ruta}")
PY
```

Para el camino mínimo, `DataTurks` y `Referencias` tienen que decir `OK`.

### B.4. Generar el dataset y entrenar el modelo

```bash
python scripts/build_ner_dataset.py
python scripts/train_ner.py --sources dataturks --output ner_dataturks_sm
```

Qué hace cada comando:

1. **`build_ner_dataset.py`**: limpia DataTurks, elimina duplicados, arma los
   conjuntos de entrenamiento/validación/prueba (semilla 42) y guarda los
   archivos en `data/processed/ner/`.
   - Si no descargaste el refuerzo de 5.029 CVs, imprime `0` en esa línea y
     continúa. No es un error: el modelo final se entrenó sólo con DataTurks.
2. **`train_ner.py`**: entrena el reconocedor de entidades sobre el modelo base
   `en_core_web_sm` y guarda el resultado en `models/ner_dataturks_sm/`.
   - `--sources dataturks` deja sólo el dataset principal.
   - `--output ner_dataturks_sm` es **obligatorio**: es el nombre exacto que
     busca la API. Si lo omitís, el modelo se guarda como `models/ner_cv/` y la
     API no lo encuentra.

Tarda unos **10 minutos en CPU**. Al final muestra algo parecido a:

```text
Precisión : 0.5...
Recall    : 0.4...
F1 (micro): 0.4679
Reporte guardado en: .../models/ner_dataturks_sm_report.json
```

El F1 de entidades es una **métrica secundaria** y su valor realista con 220 CVs
es 0,4–0,6. La métrica oficial del proyecto es el F1 de detección de secciones
(0,95). El valor puede variar unas centésimas si reentrenás en otra máquina.

Verificación:

```bash
ls models/ner_dataturks_sm
cat models/ner_dataturks_sm_report.json | head -20
```

Tiene que existir la carpeta `models/ner_dataturks_sm/` con los archivos del
modelo (`config.cfg`, `meta.json`, etc.).

### B.5. Levantar la API y probar

Desde la raíz del repositorio y con el entorno activado:

```bash
uvicorn src.api.main:app --reload
```

Esperá el mensaje de `Application startup complete` (unos 8 segundos). En otra
terminal:

```bash
curl -s http://127.0.0.1:8000/health
.venv/bin/python -m pytest -q
```

Resultado esperado: `estado: "ok"` y **16 pruebas en verde**. Después seguí desde
[A.4](#a4-probar-desde-el-navegador-swagger) para probar el diagnóstico.

---

## 4. Cómo leer el resultado

La respuesta completa tiene esta forma (valores abreviados):

```json
{
  "puntaje_global": 54.6,
  "metadatos": {
    "archivo": "cv (5).pdf",
    "paginas": 1,
    "palabras": 151,
    "motor_similitud": "tfidf",
    "tiempo_ms": 1156
  },
  "dimensiones": {
    "parseabilidad": {
      "puntaje": 100.0
    },
    "secciones": {
      "puntaje": 75.0,
      "detalle": {
        "Contacto": false,
        "Experiencia": true,
        "Educacion": true,
        "Habilidades": true
      },
      "faltantes": ["Contacto"]
    },
    "keyword_gap": {
      "puntaje": 33.3,
      "coincidencias": ["excel", "python"],
      "faltantes": ["dashboards", "docker", "project management", "sql"],
      "total_oferta": 6,
      "total_cv": 8
    },
    "similitud": {
      "puntaje": 35.5,
      "motor": "tfidf",
      "crudo": 0.0355
    }
  }
}
```

Cómo interpretarlo:

- **`puntaje_global`**: suma ponderada de las cuatro dimensiones. Un CV con texto
  legible, las cuatro secciones y buena coincidencia de palabras clave sube
  rápido; un escaneo directamente se rechaza.
- **`parseabilidad`**: 100 significa que el PDF tiene texto usable. Si es un
  escaneo, la API responde 422 y no devuelve un puntaje de 0.
- **`secciones`**: porcentaje de las cuatro secciones presentes. Cada sección
  vale 25 puntos. `detalle` dice cuáles encontró y `faltantes` cuáles no.
- **`keyword_gap`**: compara los términos importantes de la oferta con el texto
  del CV. `coincidencias` son los que aparecen; `faltantes`, los que no.
  Un puntaje bajo no siempre es un mal CV: puede que la oferta use sinónimos que
  el motor TF-IDF no reconoce.
- **`similitud`**: parecido textual global, calibrado a 0–100. El campo `crudo`
  es el valor interno antes de calibrar; sirve para auditar.
- **`tiempo_ms`**: tiempo de lectura del PDF + NLP, **sin** contar la subida del
  archivo. En una máquina como la del equipo, un pedido caliente ronda 1 segundo
  con TF-IDF.

El puntaje **no es una verdad absoluta**: es una herramienta de diagnóstico y
ordenamiento. Dos CVs parecidos pueden sacar puntajes distintos si cambia la
oferta, y un CV excelente puede sacar 60 si la oferta está escrita con palabras
muy distintas.

---

## 5. Errores frecuentes y qué hacer

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | El entorno virtual no está activado. | `source .venv/bin/activate` y verificá que aparezca `(.venv)` al inicio del prompt. |
| `uvicorn: command not found` | Se instaló dentro del entorno pero no está activado. | `.venv/bin/uvicorn src.api.main:app --reload`. |
| `No se encontró el modelo de entidades...` | Falta `models/ner_dataturks_sm/`. | Entrenalo con `python scripts/train_ner.py --sources dataturks --output ner_dataturks_sm`. |
| La API arranca pero el modelo es otro | Se entrenó sin `--output ner_dataturks_sm`. | Volvé a entrenar con ese nombre o renombrá la carpeta `models/ner_cv` a `models/ner_dataturks_sm`. |
| `Address already in use` | El puerto 8000 ya está ocupado (a veces por una API anterior). | Cerrá el otro proceso con `Ctrl+C`, o usá `uvicorn src.api.main:app --reload --port 8001` y cambiá la URL. |
| `PDF_SIN_TEXTO` con un PDF que se ve bien | Es una imagen o un escaneo sin capa de texto. | Probalo con un PDF digital; el MVP no tiene OCR. |
| `PDF_ILEGIBLE` | PDF dañado o protegido con contraseña. | Abrilo en un lector, quitá la contraseña y guardalo de nuevo. |
| `OFERTA_MUY_CORTA` | La oferta tiene menos de 20 palabras. | Pegá la descripción completa, no solo el título. |
| `OFERTA_MUY_LARGA` | La oferta supera los 20.000 caracteres. | Recortá y dejá sólo la descripción del puesto. |
| `FORMATO_NO_SOPORTADO` o `NO_ES_PDF` | El archivo no es un PDF real o no empieza con `%PDF`. | Convertilo a PDF desde el documento original. |
| `PDF_MUY_GRANDE` | Supera los 5 MB. | Comprimí el PDF o reducí la calidad de las imágenes. |
| `ERROR_INTERNO` (500) | Falló algo inesperado. | Mirá la terminal donde corre la API: el error completo queda en el log. |
| `No existe .../pares_para_calificar.csv` | No está la planilla del equipo. | Generala con `python scripts/build_rating_pairs.py` (necesita `postings.csv`) o usá `--oferta` en lugar de `--par`. |
| `No existe .../test.jsonl` | No se generó el dataset. | Corré primero `python scripts/build_ner_dataset.py`. |
| `en_core_web_sm` no encontrado | Falta el modelo base de spaCy. | `python -m spacy download en_core_web_sm`. |
| Kaggle devuelve 401/403 | Falta el token o no aceptaste las condiciones del dataset. | Configurá `~/.kaggle/kaggle.json` y aceptá las reglas en la página del dataset. |
| `torch` no se instala | Se está buscando en el índice equivocado. | Instalá primero con `--index-url https://download.pytorch.org/whl/cpu`. |
| `Python 3.10` u `3.11` | Las versiones fijadas de `numpy`/`pandas` piden 3.12+. | Instalá Python 3.12 y recreá `.venv`. |
| `cv (5).pdf` no existe | Los PDFs reales no están versionados. | Usá cualquier CV propio o el del Apéndice A. |
| Las pruebas tardan mucho la primera vez | Se carga el modelo y se generan PDFs. | Es normal: ~30 segundos; después baja. |

Si nada de esto resuelve el problema, revisá la terminal de la API: ahí aparece
el error completo con el archivo y la línea.

---

## 6. Reproducir las métricas

Los comandos de esta sección suponen que ya corriste
`build_ner_dataset.py` y `train_ner.py`.

### 6.1. Detección de secciones (métrica oficial)

```bash
python scripts/eval_sections.py
```

Salida esperada (puede variar en la última decimal si reentrenás):

```text
F1 macro: 0.9532   (objetivo >= 0,80)
F1 micro: 0.9538
Exactitud por sección: 0.9118
```

Qué mide: para cada CV de prueba, decide si están **Contacto, Experiencia,
Educación y Habilidades**, y lo compara contra las anotaciones de DataTurks. Es
la métrica oficial porque es la que usa el producto para puntuar las secciones.

### 6.2. Parseabilidad

**PDFs sintéticos** (60 archivos: una columna, dos columnas y escaneados):

```bash
python scripts/build_test_pdfs.py --n 20
python scripts/eval_parseability.py
```

Resultado esperado: **60/60** PDFs clasificados correctamente.

**PDFs reales** (sólo si tenés los 221 archivos del equipo):

```bash
python scripts/build_pdf_labels.py
python scripts/eval_parseability.py --reales
```

Resultado documentado: **210/210** PDFs únicos. Los 11 duplicados se excluyen de
la métrica y los 26 escaneos se cuentan como “no parseables” (no hay OCR).

### 6.3. Similitud contra notas humanas

Necesitás la planilla `data/benchmarks/pares_para_calificar.csv` con la columna
`puntaje_humano` completa. Esa planilla es **dato del equipo** y no está en Git.

```bash
python scripts/eval_similarity.py --motor tfidf
python scripts/eval_similarity.py --matriz
```

Resultado documentado:

```text
Correlación de Spearman : 0.9523  (objetivo >= 0.75)
Pearson (magnitud)      : 0.9407
```

`--matriz` muestra por qué se eligió el “techo” de calibración de cada motor
(TF-IDF 0,10; embeddings 0,60; fragmentos 0,70). El techo no cambia el orden de
los CVs: sólo estira la escala para que el mejor par no saque 7/100.

Si no tenés la planilla, podés generar una **sin notas** y calificarla vos:

```bash
python scripts/build_rating_pairs.py --n 50
# Abrí el CSV, completá puntaje_humano (0 a 100) en cada fila y volvé a correr
# eval_similarity.py. Con menos de 10 pares calificados no calcula Spearman.
```

### 6.4. Otras mediciones

```bash
python scripts/eval_skills_gazetteer.py   # calidad del diccionario de habilidades
python scripts/eval_cv_reales.py          # extracción sobre CVs reales
```

Estos reportes se guardan en `models/*.json` para auditoría.

### 6.5. Resumen de los números del proyecto

| Métrica | Resultado | ¿Cómo se reproduce? |
|---|---:|---|
| F1 macro de secciones | 0,9532 | `eval_sections.py` (datos públicos) |
| F1 micro de secciones | 0,9538 | `eval_sections.py` |
| Exactitud por sección | 0,9118 | `eval_sections.py` |
| Parseabilidad sintética | 60/60 | `build_test_pdfs.py` + `eval_parseability.py` |
| Parseabilidad real | 210/210 | requiere los 221 PDFs del equipo |
| Spearman de similitud | 0,9523 | requiere las 50 notas humanas |
| Pearson de similitud | 0,9407 | requiere las 50 notas humanas |
| F1 de entidades (secundaria) | 0,4679 | `train_ner.py` (puede variar) |
| Pruebas de la API | 16/16 | `pytest -q` |

---

## 7. Qué se puede reproducir y qué no

Esta distinción es importante para no prometer más de lo que el repositorio
permite:

| Resultado | ¿Se reproduce con datos públicos? | Detalle |
|---|---|---|
| Entrenar el NER | **Sí** | DataTurks + los dos repos de referencia. |
| F1 de secciones ≈ 0,95 | **Sí** | El conjunto de prueba sale de DataTurks; puede variar unas centésimas. |
| Parseabilidad sintética 60/60 | **Sí** | Los PDFs se generan con `fpdf2` y `Pillow`. |
| Las 16 pruebas de la API | **Sí** | Generan sus propios PDFs; sólo necesitan el modelo. |
| Parseabilidad real 210/210 | **No** | Requiere los 221 PDFs del equipo y sus etiquetas. |
| Spearman 0,9523 | **No** | Requiere las 50 calificaciones humanas del equipo. |
| Tiempos de respuesta exactos | **No** | Dependen del hardware. El orden de magnitud sí se reproduce. |

Los datos que faltan **no son un error de instalación**: se excluyeron a propósito
por tamaño (37 MB de PDFs, 500 MB de ofertas) y por privacidad (los CVs son de
personas reales). El código y los scripts para procesarlos sí están versionados.

---

## 8. Mapa de archivos y documentos

| Archivo | Para qué sirve |
|---|---|
| `README.md` | Propuesta formal del proyecto (Project Charter). |
| `docs/guia-de-uso.md` | Esta guía: instalar, probar y reproducir. |
| `docs/etapa-a-resultados.md` | Datos, limpieza y modelo de entidades. |
| `docs/etapa-b-resultados.md` | Parseabilidad, secciones, similitud y limitaciones. |
| `docs/etapa-c-api.md` | API: endpoints, contrato, errores, pruebas y demo. |
| `docs/bitacora-proyecto.md` | Recorrido, decisiones, preguntas del jurado y estado. |
| `src/api/main.py` | Endpoint, validaciones, errores y calentamiento. |
| `src/core/diagnostico.py` | Motor que combina las cuatro dimensiones. |
| `src/parsing/pdf_reader.py` | Lectura del PDF (texto + estructura). |
| `src/models/similarity.py` | TF-IDF, embeddings y calibración. |
| `scripts/build_ner_dataset.py` | Limpieza y splits del dataset de entidades. |
| `scripts/train_ner.py` | Entrenamiento del modelo de entidades. |
| `scripts/cliente_api.py` | Cliente HTTP de consola. |
| `tests/test_api.py` | 16 pruebas automáticas de la API. |
| `data/` | Datos crudos, procesados y benchmarks (no versionado). |
| `models/` | Modelo entrenado y reportes (no versionado). |

---

## 9. Glosario

| Término | Qué significa |
|---|---|
| **API** | Interfaz que permite que un programa pida resultados a otro por HTTP. |
| **Endpoint** | Una dirección concreta de la API, por ejemplo `/api/v1/analyze-cv`. |
| **JSON** | Formato de texto con pares clave–valor; es la respuesta de la API. |
| **Multipart** | Formato de pedido HTTP que permite enviar un archivo y texto juntos. |
| **Swagger** | Página web que FastAPI genera para probar la API sin código. |
| **NER** | *Named Entity Recognition*: reconocer nombres, empresas, títulos, etc. |
| **spaCy** | Librería de NLP usada para el NER. |
| **TF-IDF** | Técnica que compara textos por la importancia de sus palabras. |
| **Embeddings** | Representaciones numéricas del significado; se evaluaron y se descartaron como motor oficial. |
| **Stopwords** | Palabras vacías (“and”, “para”, “con”) que se ignoran al comparar. |
| **Coseno** | Medida de parecido entre dos vectores de texto (0 a 1). |
| **Spearman** | Correlación de orden: mide si el sistema rankea los CVs como las personas. |
| **F1** | Media armónica de precisión y recall; resume aciertos y errores. |
| **Macro / micro** | Promedio por clase / promedio sobre todas las decisiones. |
| **ATS** | *Applicant Tracking System*: filtro automático que usan las empresas. |
| **OCR** | Reconocimiento óptico de caracteres: convertir una imagen en texto. |
| **Parseabilidad** | Qué tan bien se puede extraer texto usable de un PDF. |
| **Gazetteer** | Diccionario curado de habilidades y sinónimos. |
| **Semilla (42)** | Número fijo que hace repetibles los sorteos y divisiones de datos. |
| **venv** | Entorno virtual de Python con las dependencias del proyecto. |
| **CPU** | Procesador; el proyecto no necesita GPU. |

---

## Apéndice A: crear un CV de ejemplo

Si no tenés un CV a mano, generá uno digital (con capa de texto) en `/tmp`:

```bash
cat > /tmp/crear_cv_ejemplo.py <<'PY'
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", size=11)
texto = """ALEX MORGAN
Data Analyst
Email: alex.morgan@example.com | Phone: +1 555 0100 | Location: Remote

SUMMARY
Data analyst with 4 years of experience turning data into decisions.
Strong background in Python, SQL, Excel and business dashboards.

SKILLS
Python, SQL, Excel, Tableau, Docker, Git, Statistics, Data Visualization

EXPERIENCE
Data Analyst - Acme Corp (2021 - Present)
- Built dashboards in Tableau for the sales team.
- Cleaned and analyzed data with Python and SQL.
- Automated weekly reports and reduced manual work by 30%.

EDUCATION
BSc in Computer Science - State University (2020)

LANGUAGES
English, Spanish
"""
pdf.multi_cell(0, 6, texto)
pdf.output("/tmp/cv_ejemplo.pdf")
print("Creado: /tmp/cv_ejemplo.pdf")
PY

.venv/bin/python /tmp/crear_cv_ejemplo.py
```

Después subilo desde Swagger con la oferta de ejemplo de
[A.4](#a4-probar-desde-el-navegador-swagger). El resultado esperado es
**96,7** (las cuatro secciones, similitud 100 y sólo falta `project management`
en la brecha de palabras clave).

---

## Apéndice B: crear un PDF escaneado de prueba

Este PDF contiene el texto dibujado como **imagen**, igual que una foto o un
escaneo: no tiene capa de texto. Sirve para comprobar que la API lo rechaza con
`422 PDF_SIN_TEXTO`.

```bash
cat > /tmp/crear_pdf_escaneado.py <<'PY'
from PIL import Image, ImageDraw

img = Image.new("RGB", (1240, 1754), "white")
dibujo = ImageDraw.Draw(img)
lineas = [
    "ALEX MORGAN",
    "Data Analyst",
    "Email: alex.morgan@example.com",
    "Python, SQL, Excel, Tableau",
    "Experiencia: Acme Corp 2021-2024",
]
y = 80
for linea in lineas:
    dibujo.text((80, y), linea, fill="black")
    y += 40
img.save("/tmp/cv_escaneado.pdf", "PDF")
print("Creado: /tmp/cv_escaneado.pdf")
PY

.venv/bin/python /tmp/crear_pdf_escaneado.py
```

Subilo desde Swagger o probalo con:

```bash
.venv/bin/python scripts/cliente_api.py \
  --pdf /tmp/cv_escaneado.pdf \
  --oferta "We are looking for a Data Analyst with strong Python and SQL skills.
You will build dashboards, clean data and communicate findings to the team.
Experience with Excel is required. Knowledge of Docker is a plus.
Project management experience is valued."
```

La respuesta esperada es `422` con `codigo: "PDF_SIN_TEXTO"`. El script termina
con código de salida 1 porque el pedido falló; eso es correcto.

---

## Enlaces rápidos

- Documentación interactiva: <http://127.0.0.1:8000/docs>
- Salud del servicio: <http://127.0.0.1:8000/health>
- Repositorio: <https://github.com/maxiteyo/CV-Decoder>
- DataTurks: <https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner>
- Diccionario de palabras clave:
  <https://github.com/Sahme115/ats-resume-keyword-dataset>
- Diccionario de habilidades:
  <https://github.com/sunnypatell/ats-screener>
