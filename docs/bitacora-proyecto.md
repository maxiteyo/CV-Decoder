# Bitácora del proyecto CV-Decoder

**Qué es este documento.** El recorrido completo del trabajo: qué hicimos, en qué
orden, qué problemas aparecieron, qué decidimos y por qué, con los números finales.
Sirve para tres cosas: que la otra persona del equipo entienda el estado sin leer
todo el código, que podamos estudiar para la exposición, y que quede registro de
las decisiones (no solo del resultado).

Última actualización: 2026-10-25 · Semilla de todo el proyecto: **42**.

---

## 1. El problema en una página

Cuando alguien se postula a un trabajo, antes que una persona lo lee un programa
llamado **ATS** (*Applicant Tracking System*). Ese programa abre el PDF, intenta
sacar el texto y lo filtra por palabras clave. Si el PDF es una imagen escaneada,
o si el texto sale desordenado, el CV se descarta aunque la persona sea idónea.

**CV-Decoder** recibe un CV en PDF y el texto de una oferta, y devuelve un JSON
con un diagnóstico en 4 dimensiones:

| # | Dimensión | Pregunta que responde | Peso |
|---|---|---|---|
| 1 | Parseabilidad | ¿Se puede leer el texto del PDF? | 0,15 |
| 2 | Secciones | ¿Tiene Contacto, Experiencia, Educación y Habilidades? | 0,25 |
| 3 | Brecha de habilidades | ¿Qué pide la oferta y no está en el CV? | 0,20 |
| 4 | Similitud | ¿Qué tan parecido es el CV a la oferta? | 0,40 |

El puntaje global (0–100) es una **suma ponderada** de esas cuatro dimensiones.
No es una probabilidad ni una nota de "apto/no apto": es un diagnóstico relativo.

**Alcance del MVP (lo que sí y lo que no):**

- Sí: API `POST /api/v1/analyze-cv` con FastAPI, motor de NLP, JSON de salida.
- No: frontend, login, base de datos, reescritura del PDF, scraping en vivo, OCR.

---

## 2. Línea de tiempo del proyecto

### Hito 0 — Definición (Project Charter)

- Se eligió el problema y se describió el agente con el modelo **PEAS**
  (Performance, Environment, Actuators, Sensors).
- Se fijaron las métricas de éxito antes de programar: F1 de secciones ≥ 0,80,
  Spearman ≥ 0,75, menos de 3 segundos por PDF y parseabilidad ≥ 90%.
- Se decidió usar **NLP + Machine Learning**, en CPU, sin entrenar transformers
  (no hay hardware para eso en el contexto de la materia).
- Se definió la modalidad **grupal (MVP funcional)** y el techo académico
  "promoción con coloquio".

**Decisión importante:** la métrica oficial no es "F1 de todas las etiquetas"
sino **F1 de detección de secciones**. Motivo: es lo que el producto realmente
usa y es medible con los datos disponibles.

### Etapa A — Datos y modelo de entidades (commits `9887dfa` → `0b3d9d3`)

**Qué se hizo**

1. Se aplanaron y limpiaron los datasets (JSON jerárquico → tablas con `pandas`).
2. Se tradujeron las 10 etiquetas de DataTurks al esquema propio
   (`PERSONA`, `CORREO`, `UBICACION`, `EMPRESA`, `PUESTO`, `TITULO`,
   `INSTITUCION`, `ANIO_EGRESO`, `ANIOS_EXPERIENCIA`, `HABILIDAD`).
3. Se separó DataTurks (220 CVs) en **153 / 32 / 34** (entrenamiento,
   validación, prueba) con semilla 42, sin filtración.
4. Se entrenó un modelo de NER sobre `en_core_web_sm` de spaCy.
5. Se construyó un **diccionario curado de habilidades** (gazetteer) y un
   detector de secciones que combina modelo + reglas + diccionario.

**Problemas encontrados y qué hicimos**

| Problema | Evidencia | Solución |
|---|---|---|
| Las habilidades están anotadas como **bloques**, no una por una | F1 de HABILIDAD = 0,205 (mide mal la realidad) | Usar diccionario curado para habilidades |
| Pocos datos para 10 etiquetas finas | F1 micro del NER = **0,47** | Aceptar 0,4–0,6 como métrica secundaria realista |
| El dataset de refuerzo (5.029 CVs) es muy ruidoso | Entrenar con refuerzo tardaba > 40 min en CPU | Se limpió a 4.788 CVs / 37.807 marcas, pero el modelo final se entrenó solo con DataTurks (~10 min) |
| `ANIOS_EXPERIENCIA` casi no aparece | F1 = 0,000 | Se reemplaza por reglas/diccionario; el NER no se usa para eso |

**Resultado de la Etapa A (actualizado al cerrar la Etapa B)**

| Métrica | Valor |
|---|---|
| F1 macro detección de secciones | **0,9532** |
| F1 micro detección de secciones | **0,9538** |
| Exactitud por sección | 0,9118 |
| Habilidades en 34 CVs de prueba | 830 (24,4 por CV, 149 distintas) |
| Diccionario | 790 términos |

Detalle por etiqueta del NER (F1): PERSONA 0,853 · CORREO 0,737 · TITULO 0,549 ·
UBICACION 0,489 · PUESTO 0,436 · ANIO_EGRESO 0,429 · EMPRESA 0,392 ·
INSTITUCION 0,374 · HABILIDAD 0,205 · ANIOS_EXPERIENCIA 0,000.

### Etapa B, parte 1 — Leer PDFs (commit `ac74f47`)

Se construyó `src/parsing/`:

- `pdf_reader.py`: abre el PDF y extrae el texto (primero con `pdfminer.six`,
  con `pdfplumber` como respaldo).
- `quality.py`: decide si el texto es usable (≥ 30 palabras y ≥ 50% de
  caracteres visibles alfanuméricos) y mide palabras pegadas.

**Prueba de control:** 20 CVs reales maquetados de 3 formas (una columna, dos
columnas, escaneado) → 60 PDFs. Resultado: **60/60 decisiones correctas**;
cobertura de palabras 1,000 en una columna, 0,999 en dos columnas y 0,000 en
escaneados.

Esto valida el lector, pero **no alcanza**: son PDFs generados por nosotros. Por
eso la Etapa B se cerró con PDFs reales.

### Etapa B, parte 2 — Motor de diagnóstico y similitud (commit `9ed6a5c`)

- `src/models/similarity.py`: dos familias de motores, TF-IDF y embeddings.
- `src/core/diagnostico.py`: combina las 4 dimensiones en un JSON.
- `scripts/demo_diagnostico.py`: demo por consola.
- `scripts/eval_similarity.py`: mide correlación contra notas humanas.

Se calificaron **50 pares (CV, oferta) a mano** de 1 a 100. Fue la parte más
lenta del proyecto: leer dos documentos y decidir cuánto se parecen.

**Primer resultado:** TF-IDF daba Spearman **0,803**. Cumplía el objetivo (≥ 0,75)
pero quedaba margen de mejora. Además la escala estaba rota: el coseno máximo era
0,072, así que el mejor par sacaba **7,2/100** y hundía el puntaje global.

### Etapa B, parte 3 — Cierre con PDFs reales (esta etapa)

El equipo juntó **221 PDFs reales** de CVs (37 MB, profesiones variadas, casi
todos en inglés, algunos escaneados). Con eso se hizo:

1. **Etiquetado objetivo de los PDFs** (`scripts/build_pdf_labels.py`):
   página por página, cuántos caracteres, cuántas imágenes y cuántas palabras.
2. **Parseabilidad real** (`scripts/eval_parseability.py --reales`):
   210 archivos únicos → **100% de decisiones correctas**.
3. **Comparación de extractores**: `pdfminer.six` vs `pdfplumber` en 40 PDFs.
4. **Mejora de la similitud**: stopwords en inglés y español, acentos
   normalizados y calibración de la escala.
5. **Medición de calidad sobre CVs reales** (`scripts/eval_cv_reales.py`):
   secciones, habilidades, entidades y tiempos.
6. **Mejoras que aparecieron de rebote** (ver §4): secciones por encabezados,
   limpieza del diccionario y corrección de doble conteo.

---

## 3. Los números finales (tabla para memorizar)

| Qué | Resultado | Objetivo | Estado |
|---|---|---|---|
| Secciones (F1 macro, 34 CVs de prueba) | **0,9532** | ≥ 0,80 | ✅ |
| Secciones (F1 micro) | **0,9538** | — | — |
| Similitud (Spearman, 50 pares sobre 25 CVs) | **0,9523** [IC 95%: 0,899–0,974] | ≥ 0,75 | ✅ |
| Parseabilidad PDFs reales (210 únicos) | **100%** (187/187 legibles, 23/23 escaneados) | ≥ 90% | ✅ |
| Parseabilidad PDFs sintéticos (60) | **100%** (60/60) | ≥ 90% | ✅ |
| Tiempo por PDF (lectura + NLP) | **0,5 s** en reposo · **1,8 s** con el equipo cargado | < 3 s | ✅ |
| Tiempo del motor con texto ya extraído | **0,05–0,20 s** | — | — |
| NER entidades (métrica secundaria) | F1 micro **0,47** | realista 0,4–0,6 | ✅ |
| CVs reales con las 4 secciones detectadas | **59,9%** (112/187) | — | informativo |

**Composición del banco de PDFs reales**

| Categoría | Archivos |
|---|---|
| Legibles (capa de texto) | 195 |
| Escaneados (sin texto) | 26 |
| Duplicados exactos | 11 |
| **Únicos evaluados** | **210** (187 legibles + 23 escaneados) |

---

## 4. Decisiones importantes y por qué

### 4.1 La métrica oficial es F1 de secciones

Con 220 CVs y 10 etiquetas finas, un F1 de 0,80 en entidades no es alcanzable
(0,47 es lo realista). En cambio, saber si están las 4 secciones se mide bien,
es lo que el producto usa y supera el objetivo con margen. El F1 de entidades se
reporta como métrica secundaria, sin maquillarlo.

### 4.2 TF-IDF es el motor oficial, no los embeddings

Se midieron tres motores contra las 50 notas humanas:

| Motor | Spearman | Veredicto |
|---|---|---|
| TF-IDF con stopwords ES+EN | **0,9523** | Oficial |
| Embeddings (documento entero) | 0,2779 | Descartado |
| Embeddings por fragmentos | 0,5003 | Descartado |

El modelo multilingüe entiende sinónimos e idiomas, pero **ordena mal** estos
pares: un CV de recursos humanos contra una oferta de programador quedaba mejor
puntuado que pares realmente buenos. TF-IDF, que solo mira palabras, ordena mucho
mejor porque las ofertas y los CVs comparten términos concretos.

### 4.3 La escala 0–100 se calibra con un "techo"

Se define qué coseno equivale a 100 puntos (TF-IDF: 0,10; embeddings: 0,60). El
mapeo es lineal y monótono: **no cambia el orden** (el Spearman queda igual), solo
hace que la escala sea interpretable. Sin esto, el mejor par real sacaba 7,2/100.
El techo de 0,10 es **38% más alto que el coseno máximo de los 1.225 pares
medidos** (0,072): deja margen para que un CV escrito a medida para una oferta
puntúe más que cualquier par del banco.

### 4.4 Dos lectores de PDF, no uno

`pdfminer.six` respeta mejor los espacios (recuperó 1.119 palabras donde
`pdfplumber` devolvía 442) y es más rápido (158 ms vs 242 ms). Pero `pdfplumber`
expone páginas e imágenes, que hacen falta para detectar escaneos. Se usan los dos
con roles distintos; no agrega dependencias porque `pdfminer` ya venía con
`pdfplumber`.

### 4.5 Los escaneos son 26, no 8

El dato inicial del equipo decía 8. La medición página por página encontró **26**
archivos sin capa de texto (0 caracteres, con imágenes o sin páginas legibles).
Dos de ellos dicen literalmente "Scanned by CamScanner". No es una suposición: es
evidencia estructural. Los otros 18 estaban mezclados entre los "legibles".

### 4.6 Se excluyen los duplicados de la métrica

Hay 11 archivos repetidos (mismo archivo o mismo texto). Contarlos inflaría el
resultado y haría creer que hay más variedad de la que hay. Se identifican por
hash y se excluyen del cálculo (quedan listados en `labels.csv` con la columna
`duplicado_de`).

### 4.7 Las secciones usan tres señales, no una

Antes: solo entidades del NER. En CVs reales el modelo no siempre reconoce la
empresa o el puesto (se entrenó con 153 CVs de un dataset de la India), pero el
encabezado `WORK EXPERIENCE` está a la vista. Se agregó la señal de encabezados
(líneas cortas) y el F1 **subió** de 0,945 a 0,9532, con recall 1,000.
En CVs reales, los que tienen las 4 secciones pasaron de 31,6% a 59,9%.

### 4.8 El diccionario se limpia con evidencia

Al medir sobre CVs reales aparecieron falsos positivos: "qualification" en 96
CVs, "ms" en 80, "word" en 54. Se agregó una lista de exclusión documentada
(`RUIDO_CVS_REALES`) con términos del inglés general y abreviaturas ambiguas.
También se corrigió un doble conteo: si "communication" estaba dentro de
"communication skills", se contaba dos veces.

### 4.9 Qué queda afuera a propósito

- **OCR** para escaneos: se detectan, no se leen. Fuera del MVP.
- **Español real**: el lote es 100% inglés. TF-IDF no cruza idiomas.
- **4.000 PDFs adicionales**: sin etiquetas no mejoran métricas; sirven para
  medir la tasa real de escaneos y para análisis de errores futuros.
- **Reescribir el PDF**: el producto diagnostica, no corrige.

---

## 5. Errores y sorpresas (sirven para mostrar rigor en la defensa)

1. **8 vs 26 escaneos.** El dato inicial era impreciso. Se resolvió midiendo,
   no preguntando.
2. **Falsos duplicados.** Los escaneos comparten el texto "Scanned by CamScanner"
   y el primer detector los marcaba como duplicados entre sí. Se corrigió: el
   hash de texto solo se aplica a CVs con texto real.
3. **El ratio alfanumérico castigaba PDFs a dos columnas.** `pdfminer` devuelve
   muchos espacios de relleno; medir sobre todos los caracteres hacía parecer
   "roto" un CV legible. Se mide sobre caracteres no-espacios.
4. **Bug en embeddings por fragmentos.** Se fragmentaba el texto ya limpiado, y
   la limpieza borraba los saltos de línea: todo quedaba en un solo bloque (daba
   idéntico al documento entero). Se corrigió y el resultado real fue 0,50.
5. **El diccionario contaba "qualification" como habilidad.** Se detectó recién
   al mirar los términos más frecuentes en CVs reales. Sin esa medición, el
   keyword gap habría sido ruido.
6. **"Excel" como verbo.** "To excel in..." se cuenta como la herramienta Excel.
   Limitación conocida: el detector no distingue mayúsculas/contexto.

---

## 6. Preguntas probables del jurado (y respuesta corta)

- **¿Por qué no usaron un transformer para la similitud?**
  Lo probamos: embeddings multilingües dieron Spearman 0,28 y por fragmentos
  0,50, contra 0,95 de TF-IDF. Además el enunciado pedía CPU y sin fine-tuning.
- **¿El 100% de parseabilidad no es sospechoso?**
  La decisión binaria es fácil: un escaneo da 0 palabras. Por eso medimos también
  calidad parcial: 7,5% de CVs con páginas vacías y 3,2% con palabras pegadas.
- **¿Cómo saben que no hay sobreajuste?**
  Split fijo 153/32/34 con semilla 42, sin filtración entre entrenamiento y
  prueba, y las métricas de similitud se midieron en pares que no se usaron para
  construir nada.
- **¿Qué significa el puntaje global?**
  Es una suma ponderada de cuatro dimensiones, no una probabilidad. Sirve para
  comparar y priorizar mejoras.
- **¿Qué pasa con un CV en español?**
  El NER es inglés y TF-IDF no cruza idiomas. Los embeddings sí, pero ordenan
  mal. Es una limitación declarada; el lote real es inglés.
- **¿Qué pasa con un CV escaneado?**
  Se detecta y se rechaza con un mensaje claro. Sin OCR no hay texto que
  diagnosticar, y el OCR está fuera del alcance.
- **¿Por qué el techo de calibración es 0,10?**
  Porque está 38% arriba del coseno máximo observado en 1.225 pares CV×oferta
  (0,072): deja margen a un CV hecho a medida sin inventar una escala. Es una
  decisión empírica, documentada y fácil de recalibrar con más datos.
- **¿Qué harían con más tiempo?**
  OCR, etiquetas de CVs reales para medir F1 real, ampliar el diccionario a
  oficios, y la API de la Etapa C.

---

## 7. Glosario

- **ATS**: sistema automático que filtra CVs antes de que los lea una persona.
- **API REST**: interfaz por HTTP que recibe una petición y devuelve datos (acá,
  un JSON).
- **JSON**: formato de texto con pares clave–valor; es lo que devuelve el motor.
- **NLP**: procesamiento de lenguaje natural; enseñarle a un programa a trabajar
  con texto.
- **NER**: reconocimiento de entidades nombradas; marcar qué es cada cosa en el
  texto (nombre, empresa, título).
- **Parseabilidad**: si se puede extraer texto usable de un PDF.
- **Capa de texto**: el texto invisible seleccionable que el PDF guarda adentro.
- **PDF escaneado**: una foto del CV; no tiene capa de texto, requiere OCR.
- **OCR**: convertir una imagen en texto (fuera del alcance del MVP).
- **Gazetteer / diccionario**: buscar términos conocidos en el texto.
- **Stopwords**: palabras vacías ("and", "de", "para") que no aportan
  significado y se descartan.
- **TF-IDF**: mide qué palabras son importantes en un documento comparándolas con
  el resto del corpus.
- **Embeddings**: representar el significado del texto como vectores numéricos.
- **Coseno**: medida de parecido entre dos vectores (0 = nada, 1 = idéntico).
- **Spearman**: correlación de **orden** entre dos rankings (-1 a 1).
- **Pearson**: correlación de **magnitud** entre dos series (lineal).
- **F1**: media armónica de precisión y recall (0 a 1).
- **Precisión**: de lo que el sistema marcó, cuánto era correcto.
- **Recall**: de lo que realmente estaba, cuánto encontró.
- **F1 macro / micro**: macro promedia por etiqueta; micro mezcla todo en una
  cuenta (pesa más la etiqueta más frecuente).
- **Bootstrap**: remuestrear los datos muchas veces para estimar un rango de
  confianza (IC 95%).
- **Semilla (42)**: número que fija el azar para que los resultados se puedan
  repetir.
- **Calibración**: transformar una medida cruda (coseno) a una escala
  interpretable (0–100) sin cambiar el orden.
- **Baseline**: solución simple de referencia con la que se compara el modelo.
- **`RUIDO_CVS_REALES`**: lista negra de términos genéricos que parecían
  habilidades pero no lo son.

---

## 8. Mapa de archivos importantes

| Archivo | Para qué sirve |
|---|---|
| `src/parsing/pdf_reader.py` | Leer el PDF (texto + estructura), sin lanzar errores |
| `src/parsing/quality.py` | Decidir si el texto es usable y medir su calidad |
| `src/core/diagnostico.py` | Motor que combina las 4 dimensiones |
| `src/core/nlp_engine.py` | Cargar una sola vez el modelo y el diccionario |
| `src/models/similarity.py` | Motores de similitud + calibración 0–100 |
| `src/data_loader/skills_lexicon.py` | Diccionario curado y listas negras |
| `scripts/build_pdf_labels.py` | Generar `labels.csv` de los PDFs reales |
| `scripts/eval_parseability.py` | Medir parseabilidad (sintéticos y reales) |
| `scripts/eval_sections.py` | Medir F1 de detección de secciones |
| `scripts/eval_similarity.py` | Medir Spearman contra notas humanas |
| `scripts/eval_cv_reales.py` | Medir extracción sobre CVs reales |
| `scripts/demo_diagnostico.py` | Probar un par o un PDF real de punta a punta |
| `docs/etapa-a-resultados.md` | Resultados de datos y modelo de entidades |
| `docs/etapa-b-resultados.md` | Resultados de parseabilidad, secciones y similitud |

Los datos (`data/`) y los reportes (`models/*.json`) **no se versionan**: pesan
mucho y se regeneran con los scripts. El `.gitignore` los excluye a propósito.

---

## 9. Reproducibilidad

Todos los scripts usan la semilla 42. Para reproducir desde cero:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/build_ner_dataset.py     # dataset de entidades
python scripts/train_ner.py             # modelo de entidades (~10 min en CPU)
python scripts/build_test_pdfs.py       # 60 PDFs sintéticos
python scripts/build_pdf_labels.py      # etiquetas de los PDFs reales
python scripts/eval_parseability.py --reales
python scripts/eval_sections.py
python scripts/eval_similarity.py --motor tfidf
python scripts/eval_similarity.py --matriz
python scripts/eval_cv_reales.py
```

Los PDFs reales y la planilla de pares calificados son datos del equipo: no están
en el repositorio, pero `labels.csv` y los reportes quedan generados localmente
para auditoría.

---

## 10. Convención de commits

Cada commit debe decir **qué problema resuelve** y **cuánto tiempo insumió**. Es
parte del acuerdo de la materia y sirve para reconstruir el esfuerzo real:
`Etapa B: <problema resuelto> (~N h)`.

Commits del proyecto (los más importantes):

| Commit | Qué resolvió |
|---|---|
| `9887dfa` | Primer esqueleto del repositorio |
| `b1dec5b` | `.gitignore` y carpetas base |
| `0b3d9d3` | Etapa A: limpieza de datos y primer modelo de entidades |
| `2762117` | README: métrica de F1 a secciones y limpieza de artefactos |
| `ac74f47` | Etapa B: lectura de PDFs (parseabilidad) y similitud |
| `9ed6a5c` | Etapa B: motor de diagnóstico (4 dimensiones) y embeddings |

---

## 11. Estado actual y próximo paso

**Cerrado:** Etapa A (datos + NER + diccionario) y Etapa B (parseabilidad real,
secciones, similitud, calibración, mediciones y documentación).

**Siguiente:** Etapa C — API FastAPI con `POST /api/v1/analyze-cv`:

1. Esquema Pydantic de entrada (archivo PDF + texto de la oferta) y salida (JSON
   de 4 dimensiones).
2. Endpoint que use `read_pdf` + `analizar`, con respuestas 422 claras para PDF
   roto o escaneado.
3. Pruebas con Swagger/Postman y control de tamaño/tiempo.
4. Documentar la API y preparar la demo de la exposición.

**Pendiente opcional:** calificar 10 pares nuevos "buenos" (CV y oferta del mismo
oficio) para validar el techo de la escala; si se hacen, se recalibra con
evidencia.
