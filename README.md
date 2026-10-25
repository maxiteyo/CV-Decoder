# CV-Decoder: Diagnosticador de CVs y Optimizador ATS Multilingüe

> **Asignatura:** Inteligencia Artificial (2026)  
> **Institución:** Centro Regional Universitario Córdoba - IUA | Universidad de la Defensa Nacional  
> **Docente:** Ing. González, Hernando Alexis  
> **Modalidad:** Grupal (MVP Funcional)  

---

## 1. Contexto y Descripción del Problema

En el mercado laboral actual, la primera barrera que enfrenta un postulante es un sistema **ATS** (*Applicant Tracking System*). Estos filtros automatizados descartan un gran porcentaje de currículums por incompatibilidades de formato (tablas, columnas complejas, texto no parseable) o por falta de coincidencia semántica de palabras clave frente a la oferta laboral.

**CV-Decoder** es una solución basada en **Inteligencia Artificial (NLP y Machine Learning)** diseñada para auditar y diagnosticar un CV en formato PDF en relación con un puesto de trabajo específico. El sistema analiza el documento en español, inglés o *spanglish*, evalúa la integridad del texto, extrae entidades clave y calcula la similitud semántica contra la vacante, entregando un reporte técnico estructurado para optimizar las probabilidades de éxito del candidato frente a los sistemas ATS.

---

## 2. Modelado del Entorno (Modelo PEAS)

Para definir formalmente el comportamiento del agente de IA, se establece la matriz PEAS:

| Componente | Descripción |
| :--- | :--- |
| **Performance (Métricas)** | • F1-Score $\ge 0.80$ en la **detección de secciones** del CV (Contacto, Experiencia, Educación, Habilidades). Métrica secundaria: F1 de extracción de entidades.<br>• Correlación Spearman $\ge 0.75$ en la similitud semántica.<br>• Tiempo de inferencia por PDF $< 3.0$ segundos. |
| **Environment (Entorno)** | Archivos PDF heterogéneos de CVs (1 y 2 columnas, bilingües) y bloques de texto no estructurado que representan ofertas de empleo (*Job Descriptions*). |
| **Actuators (Actuadores)** | API REST que emite un objeto **JSON estructurado** con el score global de compatibilidad, tasa de parseabilidad, secciones faltantes y brecha de palabras clave (*skills gap*). |
| **Sensors (Sensores)** | Lector de archivos PDF (`pdfminer.six` para el texto + `pdfplumber` para páginas/imágenes) y endpoints HTTP de entrada (`POST /api/v1/analyze-cv`) desarrollados en **FastAPI**. |

---

## 3. Origen y Naturaleza de los Datos

El proyecto utiliza tres conjuntos de datos complementarios extraídos de fuentes públicas para el entrenamiento, la calibración y el análisis exploratorio (EDA):

1. **Dataset de NER para CVs ([Resume Entities for NER - Kaggle](https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner)):**
   * **Naturaleza:** Archivo en formato JSON con CVs anotados a nivel de token (`Skills`, `Degree`, `Designation`, `Companies`, `Years of Experience`).
   * **Uso:** Entrenamiento y fine-tuning del modelo de Reconocimiento de Entidades Nombradas (NER).
2. **Dataset de Ofertas Laborales ([LinkedIn Job Postings - Kaggle](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)):**
   * **Naturaleza:** Dataset tabular (JSON/CSV) con descripciones reales de puestos en tecnología y gestión.
   * **Uso:** Calibración del motor de similitud (TF-IDF) y construcción de diccionarios de competencias requeridas.
3. **Dataset de Evaluación (Benchmark Interno):**
   * **Naturaleza:** **221 PDFs reales** de CVs (profesiones variadas, casi todos en inglés; 26 escaneados sin capa de texto) + **60 PDFs sintéticos** de control (una columna, dos columnas, escaneado).
   * **Uso:** Medición *End-to-End* de parseabilidad y de calidad de extracción. Los PDFs reales no se versionan (pesan 37 MB y no hacen falta para reproducir el código).

### Tratamiento y Limpieza de Datos (EDA)
Dado que los datasets de origen se presentan en estructuras jerárquicas JSON, el pipeline de datos ejecuta un proceso de aplanamiento (*flattening*) con `pandas.json_normalize` para transformar los datos a estructuras tabulares. Se aplican controles de:
* Eliminación de documentos vacíos o corruptos (longitud < 100 caracteres o > 50,000 caracteres).
* Sanitización de etiquetas HTML residuales y caracteres Unicode no imprimibles.
* Desduplicación estricta de documentos para evitar filtrado de información (*data leakage*) entre entrenamiento y prueba.

---

## 4. Métricas de Éxito y Baseline

### Baseline (Punto de Comparación sin IA Avanzada)
El punto de comparación inicial (**Baseline**) consiste en un script clásico de coincidencia de cadenas basado en **TF-IDF + Regex**. Este algoritmo ingenuo cuenta coincidencias exactas de palabras sin considerar la estructura interna del PDF ni la equivalencia semántica de los términos (ej. no comprende que *"Software Engineer"* y *"Desarrollador de Software"* son equivalentes).

### Métricas Objetivas de Éxito
Para superar al baseline, el modelo de IA debe cumplir con las siguientes métricas estadísticas:
* **Detección de Secciones:** $F1\text{-}Score \ge 0.80$ al decidir si el CV contiene cada sección clave (Contacto, Experiencia, Educación, Habilidades). *(Resultado medido: **0,953**).*
* **Extracción de Entidades (métrica secundaria):** $F1\text{-}Score$ de las etiquetas detalladas (nombre, email, empresa, título, etc.). Con 220 CVs anotados, el valor realista es 0,4–0,6 (no 0,80).
* **Similitud Semántica:** Correlación de orden de Spearman $r_s \ge 0.75$ evaluada frente a pares de (CV, Vacante) calificados por expertos. *(Resultado medido: **0,952** con TF-IDF; embeddings: 0,278).*
* **Desempeño Operativo:** Cobertura de parseabilidad correcta en al menos el $90\%$ de los formatos de PDF testeados. *(Resultado medido: **100%** en 210 PDFs reales únicos y 60/60 sintéticos).*

> **Nota sobre habilidades:** en el dataset, las habilidades están anotadas como **bloques** (toda la lista junta), no una por una. Por eso la extracción de habilidades se resuelve con un **diccionario curado** (necesario además para el *keyword gap*), y no se le exige un F1 de token exacto.

> **Resultados completos:** [`docs/etapa-a-resultados.md`](docs/etapa-a-resultados.md) (datos y modelo de entidades) y [`docs/etapa-b-resultados.md`](docs/etapa-b-resultados.md) (parseabilidad, secciones, similitud y limitaciones). El recorrido del proyecto, decisión por decisión, está en [`docs/bitacora-proyecto.md`](docs/bitacora-proyecto.md).

---

## 5. Límites del Alcance (Out of Scope - MVP)

En concordancia con los lineamientos de la modalidad grupal, el esfuerzo inicial se concentra de manera exclusiva en la ingeniería de datos, el modelado de IA y la API de inferencia:

[ PDF del CV ] + [ Texto de Vacante ] ==> (│    Core CV-Decoder    │ ◄── Extracción + NER + Similitud) ==> [ JSON con Diagnóstico ]

### Incluido en el MVP:
* API REST funcional desarrollada en **FastAPI**.
* Endpoint `POST /api/v1/analyze-cv` que recibe el archivo PDF del CV y un string con la oferta laboral.
* Pipeline de NLP que procesa el texto, identifica entidades y calcula la similitud CV–oferta (motor oficial: **TF-IDF con stopwords ES+EN**; embeddings multilingües evaluados y descartados por su bajo ordenamiento).
* Retorno de un JSON estandarizado con 4 dimensiones de diagnóstico: *Match Semántico*, *Parseabilidad*, *Completitud de Secciones* y *Gaps de Palabras Clave*.

### Fuera del Alcance (Out of Scope):
* Frontend web o interfaces complejas en React/Angular (las pruebas se realizan vía Swagger/Postman).
* Módulos de autenticación, login de usuarios o bases de datos relacionales persistentes.
* Reescritura, edición o generación automática del archivo PDF resultante.
* Scraping en tiempo real de portales de empleo.

---

## 6. Arquitectura Técnica y Stack Tecnológico

* **Lenguaje Principal:** Python $\ge 3.10$
* **Extracción de Texto PDF:** `pdfminer.six` (texto, respeta mejor los espacios) + `pdfplumber` (páginas e imágenes para detectar escaneos)
* **Procesamiento de Lenguaje Natural (NLP):** `spaCy` (modelo NER entrenado en **inglés**; el español se cubre con embeddings multilingües + diccionario bilingüe).
* **Vectorización y Embeddings:** `scikit-learn` (TF-IDF, motor oficial) y `sentence-transformers` (Modelo: `paraphrase-multilingual-mpnet-base-v2`, evaluado y descartado para el ordenamiento).
* **Puntuación / Scoring:** reglas ponderadas: similitud 0,40 · secciones 0,25 · brecha de habilidades 0,20 · parseabilidad 0,15. No se usa un clasificador entrenado porque no existen etiquetas de verdad para el score final.
* **Servicio y API REST:** `FastAPI`, `pydantic`

---

## 7. Estructura del Repositorio

El proyecto cumple con la separación modular exigida por la cátedra:

```text
cv-decoder/
├── .gitignore              # Excluye data (crudos, benchmarks, PDFs reales), venv, cache y reportes
├── README.md               # Propuesta formal y documentación técnica del proyecto (Project Charter)
├── requirements.txt        # Manifiesto de dependencias con versiones exactas
│
├── data/                   # Excluido de Git. Datasets crudos, procesados y benchmarks
│   ├── raw/                # Datasets originales en JSON / CSV
│   ├── processed/          # Dataframes limpios + splits de entrenamiento
│   └── benchmarks/         # PDFs sintéticos, PDFs reales y planillas de calificación
│
├── docs/                   # Documentación de resultados y bitácora del proyecto
│   ├── etapa-a-resultados.md
│   ├── etapa-b-resultados.md
│   └── bitacora-proyecto.md
│
├── scripts/                # Scripts ejecutables (limpieza, entrenamiento, evaluación)
│   ├── build_ner_dataset.py
│   ├── train_ner.py
│   ├── build_test_pdfs.py
│   ├── build_pdf_labels.py
│   ├── build_rating_pairs.py
│   ├── eval_sections.py
│   ├── eval_skills_gazetteer.py
│   ├── eval_parseability.py
│   ├── eval_cv_reales.py
│   ├── eval_similarity.py
│   └── demo_diagnostico.py
│
├── src/                    # Código fuente modularizado
│   ├── __init__.py
│   ├── config.py           # Rutas y semilla global (42)
│   ├── api/                # Endpoints FastAPI y esquemas Pydantic (Etapa C)
│   ├── core/               # Motor de diagnóstico y carga única del modelo
│   ├── data_loader/        # Lectura y limpieza de datos + diccionario de habilidades
│   ├── parsing/            # Lectura de PDFs y control de parseabilidad (Etapa B)
│   ├── models/             # Similitud (TF-IDF / embeddings) e inferencia
│   └── utils/              # Funciones auxiliares y fijación de semillas
│
└── models/                 # Artefactos y pesos guardados + reportes de evaluación (no versionados)
```

### 7.1 Cómo ejecutar el diagnóstico hoy

```bash
# Crear entorno e instalar dependencias
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Diagnosticar un PDF real contra una oferta de la planilla de pares
python scripts/demo_diagnostico.py --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" --par par_005

# Reproducir todas las mediciones
python scripts/build_pdf_labels.py
python scripts/eval_parseability.py --reales
python scripts/eval_sections.py
python scripts/eval_similarity.py --motor tfidf
python scripts/eval_similarity.py --matriz
```