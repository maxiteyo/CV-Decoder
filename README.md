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
| **Sensors (Sensores)** | Lector de archivos PDF (`pdfplumber`) y endpoints HTTP de entrada (`POST /api/v1/analyze-cv`) desarrollados en **FastAPI**. |

---

## 3. Origen y Naturaleza de los Datos

El proyecto utiliza tres conjuntos de datos complementarios extraídos de fuentes públicas para el entrenamiento, la calibración y el análisis exploratorio (EDA):

1. **Dataset de NER para CVs ([Resume Entities for NER - Kaggle](https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner)):**
   * **Naturaleza:** Archivo en formato JSON con CVs anotados a nivel de token (`Skills`, `Degree`, `Designation`, `Companies`, `Years of Experience`).
   * **Uso:** Entrenamiento y fine-tuning del modelo de Reconocimiento de Entidades Nombradas (NER).
2. **Dataset de Ofertas Laborales ([LinkedIn Job Postings - Kaggle](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)):**
   * **Naturaleza:** Dataset tabular (JSON/CSV) con descripciones reales de puestos en tecnología y gestión.
   * **Uso:** Calibración del motor de embeddings semánticos y construcción de diccionarios de competencias requeridas.
3. **Dataset de Evaluación (Benchmark Interno):**
   * **Naturaleza:** Muestra curada de PDFs de control en español, inglés y *spanglish* para pruebas *End-to-End* de parseabilidad.

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
* **Detección de Secciones:** $F1\text{-}Score \ge 0.80$ al decidir si el CV contiene cada sección clave (Contacto, Experiencia, Educación, Habilidades). *(Resultado Etapa A: 0,945).*
* **Extracción de Entidades (métrica secundaria):** $F1\text{-}Score$ de las etiquetas detalladas (nombre, email, empresa, título, etc.). Con 220 CVs anotados, el valor realista es 0,4–0,6 (no 0,80).
* **Similitud Semántica:** Correlación de orden de Spearman $r_s \ge 0.75$ evaluada frente a pares de (CV, Vacante) calificados por expertos.
* **Desempeño Operativo:** Cobertura de parseabilidad correcta en al menos el $90\%$ de los formatos de PDF testeados.

> **Nota sobre habilidades:** en el dataset, las habilidades están anotadas como **bloques** (toda la lista junta), no una por una. Por eso la extracción de habilidades se resuelve con un **diccionario curado** (necesario además para el *keyword gap*), y no se le exige un F1 de token exacto.

---

## 5. Límites del Alcance (Out of Scope - MVP)

En concordancia con los lineamientos de la modalidad grupal, el esfuerzo inicial se concentra de manera exclusiva en la ingeniería de datos, el modelado de IA y la API de inferencia:

[ PDF del CV ] + [ Texto de Vacante ] ==> (│    Core CV-Decoder    │ ◄── Extracción + NER + Embeddings) ==> [ JSON con Diagnóstico ]

### Incluido en el MVP:
* API REST funcional desarrollada en **FastAPI**.
* Endpoint `POST /api/v1/analyze-cv` que recibe el archivo PDF del CV y un string con la oferta laboral.
* Pipeline de NLP que procesa el texto, identifica entidades y calcula embeddings semánticos multilingües (`Sentence-Transformers`).
* Retorno de un JSON estandarizado con 4 dimensiones de diagnóstico: *Match Semántico*, *Parseabilidad*, *Completitud de Secciones* y *Gaps de Palabras Clave*.

### Fuera del Alcance (Out of Scope):
* Frontend web o interfaces complejas en React/Angular (las pruebas se realizan vía Swagger/Postman).
* Módulos de autenticación, login de usuarios o bases de datos relacionales persistentes.
* Reescritura, edición o generación automática del archivo PDF resultante.
* Scraping en tiempo real de portales de empleo.

---

## 6. Arquitectura Técnica y Stack Tecnológico

* **Lenguaje Principal:** Python $\ge 3.10$
* **Extracción de Texto PDF:** `pdfplumber`, `pypdf`
* **Procesamiento de Lenguaje Natural (NLP):** `spaCy` (modelo NER entrenado en **inglés**; el español se cubre con embeddings multilingües + diccionario bilingüe).
* **Vectorización y Embeddings:** `sentence-transformers` (Modelo: `paraphrase-multilingual-mpnet-base-v2`)
* **Puntuación / Scoring:** reglas ponderadas con `scikit-learn` (TF-IDF para el *keyword gap*). No se usa un clasificador entrenado porque no existen etiquetas de verdad para el score final.
* **Servicio y API REST:** `FastAPI`, `pydantic`

---

## 7. Estructura del Repositorio

El proyecto cumple con la separación modular exigida por la cátedra:

```text
cv-decoder/
├── .gitignore              # Archivos excluidos del control de versiones (data, venv, cache)
├── README.md               # Propuesta formal y documentación técnica del proyecto (Project Charter)
├── requirements.txt        # Manifiesto de dependencias con versiones exactas
│
├── data/                   # Excluido de Git. Almacena datasets crudos y procesados
│   ├── raw/                # Datasets originales en JSON / CSV
│   └── processed/          # Dataframes limpios listos para entrenamiento
│
├── scripts/                # Scripts ejecutables (limpieza, entrenamiento, evaluación)
│   ├── build_ner_dataset.py
│   ├── train_ner.py
│   ├── eval_sections.py
│   └── eval_skills_gazetteer.py
│
├── src/                    # Código fuente modularizado
│   ├── __init__.py
│   ├── config.py           # Rutas y semilla global (42)
│   ├── api/                # Endpoints FastAPI y esquemas Pydantic (Etapa C)
│   ├── data_loader/        # Lectura y limpieza de datos + diccionario de habilidades
│   ├── parsing/            # Lectura de PDFs y control de parseabilidad (Etapa B)
│   ├── models/             # Inferencia, NER y embeddings
│   └── utils/              # Funciones auxiliares y fijación de semillas
│
└── models/                 # Artefactos y pesos guardados de los modelos entrenados