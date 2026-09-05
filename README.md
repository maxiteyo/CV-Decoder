# CV-Decoder: Diagnosticador de CVs y Optimizador ATS Multilingüe

> **Asignatura:** Inteligencia Artificial (2026)  
> **Institución:** Centro Regional Universitario Córdoba - IUA | Universidad de la Defensa Nacional  
> **Docente:** Ing. González, Hernando Alexis  
> **Modalidad:** Grupal (MVP Funcional)  

---

## 1. Contexto y Descripción del Problema

En el mercado laboral actual, la primera barrera que enfrenta un postulante es un sistema **ATS** (*Applicant Tracking System*). Estos filtros automatizados descartan un gran porcentaje de currículums por incompatibilidades de formato (tablas, columnas complejas, texto no parseable) o por falta de coincidencia semántica de palabras clave frente a la oferta laboral.

**CV-Decoder** es una solución basada en **Inteligencia Artificial (NLP y Machine Learning)** diseñada para auditar y diagnosticar un CV en formato PDF en relación con un puesto de trabajo específico[cite: 1]. El sistema analiza el documento en español, inglés o *spanglish*, evalúa la integridad del texto, extrae entidades clave y calcula la similitud semántica contra la vacante, entregando un reporte técnico estructurado para optimizar las probabilidades de éxito del candidato frente a los sistemas ATS[cite: 1].

---

## 2. Modelado del Entorno (Modelo PEAS)

Para definir formalmente el comportamiento del agente de IA, se establece la matriz PEAS[cite: 1]:

| Componente | Descripción |
| :--- | :--- |
| **Performance (Métricas)** | • F1-Score $\ge 0.80$ en la extracción NER de entidades.<br>• Correlación Spearman $\ge 0.75$ en la similitud semántica.<br>• Tiempo de inferencia por PDF $< 3.0$ segundos. |
| **Environment (Entorno)** | Archivos PDF heterogéneos de CVs (1 y 2 columnas, bilingües) y bloques de texto no estructurado que representan ofertas de empleo (*Job Descriptions*)[cite: 1]. |
| **Actuators (Actuadores)** | API REST que emite un objeto **JSON estructurado** con el score global de compatibilidad, tasa de parseabilidad, secciones faltantes y brecha de palabras clave (*skills gap*)[cite: 1]. |
| **Sensors (Sensores)** | Lector de archivos PDF (`pdfplumber`) y endpoints HTTP de entrada (`POST /api/v1/analyze-cv`) desarrollados en **FastAPI**[cite: 1]. |

---

## 3. Origen y Naturaleza de los Datos

El proyecto utiliza tres conjuntos de datos complementarios extraídos de fuentes públicas para el entrenamiento, la calibración y el análisis exploratorio (EDA)[cite: 1]:

1. **Dataset de NER para CVs ([Resume Entities for NER - Kaggle](https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner)):**
   * **Naturaleza:** Archivo en formato JSON con CVs anotados a nivel de token (`Skills`, `Degree`, `Designation`, `Companies`, `Years of Experience`).
   * **Uso:** Entrenamiento y fine-tuning del modelo de Reconocimiento de Entidades Nombradas (NER)[cite: 1].
2. **Dataset de Ofertas Laborales ([LinkedIn Job Postings - Kaggle](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)):**
   * **Naturaleza:** Dataset tabular (JSON/CSV) con descripciones reales de puestos en tecnología y gestión.
   * **Uso:** Calibración del motor de embeddings semánticos y construcción de diccionarios de competencias requeridas.
3. **Dataset de Evaluación (Benchmark Interno):**
   * **Naturaleza:** Muestra curada de PDFs de control en español, inglés y *spanglish* para pruebas *End-to-End* de parseabilidad.

### Tratamiento y Limpieza de Datos (EDA)
Dado que los datasets de origen se presentan en estructuras jerárquicas JSON, el pipeline de datos ejecuta un proceso de aplanamiento (*flattening*) con `pandas.json_normalize` para transformar los datos a estructuras tabulares[cite: 1]. Se aplican controles de:
* Eliminación de documentos vacíos o corruptos (longitud < 100 caracteres o > 50,000 caracteres).
* Sanitización de etiquetas HTML residuales y caracteres Unicode no imprimibles.
* Desduplicación estricta de documentos para evitar filtrado de información (*data leakage*) entre entrenamiento y prueba[cite: 1].

---

## 4. Métricas de Éxito y Baseline

### Baseline (Punto de Comparación sin IA Avanzada)
El punto de comparación inicial (**Baseline**) consiste en un script clásico de coincidencia de cadenas basado en **TF-IDF + Regex**[cite: 1]. Este algoritmo ingenuo cuenta coincidencias exactas de palabras sin considerar la estructura interna del PDF ni la equivalencia semántica de los términos (ej. no comprende que *"Software Engineer"* y *"Desarrollador de Software"* son equivalentes)[cite: 1].

### Métricas Objetivas de Éxito
Para superar al baseline, el modelo de IA debe cumplir con las siguientes métricas estadísticas[cite: 1]:
* **Extracción de Entidades (NER):** $F1\text{-}Score \ge 0.80$ en la clasificación de secciones y habilidades clave.
* **Similitud Semántica:** Correlación de orden de Spearman $r_s \ge 0.75$ evaluada frente a pares de (CV, Vacante) calificados por expertos.
* **Desempeño Operativo:** Cobertura de parseabilidad correcta en al menos el $90\%$ de los formatos de PDF testeados.

---

## 5. Límites del Alcance (Out of Scope - MVP)

En concordancia con los lineamientos de la modalidad grupal, el esfuerzo inicial se concentra de manera exclusiva en la ingeniería de datos, el modelado de IA y la API de inferencia[cite: 1]:

[ PDF del CV ] + [ Texto de Vacante ] ==> (│    Core CV-Decoder    │ ◄── Extracción + NER + Embeddings) ==> [ JSON con Diagnóstico ]

### Incluido en el MVP[cite: 1]:
* API REST funcional desarrollada en **FastAPI**.
* Endpoint `POST /api/v1/analyze-cv` que recibe el archivo PDF del CV y un string con la oferta laboral.
* Pipeline de NLP que procesa el texto, identifica entidades y calcula embeddings semánticos multilingües (`Sentence-Transformers`)[cite: 1].
* Retorno de un JSON estandarizado con 4 dimensiones de diagnóstico: *Match Semántico*, *Parseabilidad*, *Completitud de Secciones* y *Gaps de Palabras Clave*[cite: 1].

### Fuera del Alcance (Out of Scope)[cite: 1]:
* Frontend web o interfaces complejas en React/Angular (las pruebas se realizan vía Swagger/Postman).
* Módulos de autenticación, login de usuarios o bases de datos relacionales persistentes.
* Reescritura, edición o generación automática del archivo PDF resultante.
* Scraping en tiempo real de portales de empleo.

---

## 6. Arquitectura Técnica y Stack Tecnológico

* **Lenguaje Principal:** Python $\ge 3.10$[cite: 1]
* **Extracción de Texto PDF:** `pdfplumber`, `pypdf`
* **Procesamiento de Lenguaje Natural (NLP):** `spaCy` (NER multilingüe)[cite: 1]
* **Vectorización y Embeddings:** `sentence-transformers` (Modelo: `paraphrase-multilingual-mpnet-base-v2`)
* **Modelo Predictivo / Classifier:** `scikit-learn` / `xgboost`[cite: 1]
* **Servicio y API REST:** `FastAPI`, `pydantic`[cite: 1]

---

## 7. Estructura del Repositorio

El proyecto cumple con la separación modular exigida por la cátedra[cite: 1]:

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
├── notebooks/              # Cuadernos Jupyter exploratorios
│   ├── 01_eda_and_cleaning.ipynb
│   ├── 02_ner_model_training.ipynb
│   └── 03_embeddings_and_scoring.ipynb
│
├── src/                    # Código fuente modularizado
│   ├── __init__.py
│   ├── api/                # Definición de endpoints FastAPI y esquemas Pydantic
│   │   └── main.py
│   ├── data_loader/        # Módulos para parseo de PDFs y lectura de JSONs
│   ├── models/             # Lógica de inferencia, NER y embeddings
│   └── utils/              # Funciones auxiliares y fijación de semillas
│
└── models/                 # Artefactos y pesos guardados de los modelos entrenados