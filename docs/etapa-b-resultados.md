# Etapa B — Resultados (parseabilidad + similitud) — CIERRE

Fecha: 2026-10-25 · Semilla: **42** · Datos: 221 PDFs reales + 60 PDFs sintéticos + 50 pares calificados a mano

Este documento reemplaza la versión parcial anterior. Todos los números salen de
los reportes guardados en `models/` y se reproducen con los comandos del final.

---

## 1. Parseabilidad (dimensión 1)

### 1.1 Qué se mide

Un ATS primero tiene que poder **sacar texto** del PDF. Si el PDF es una foto
(escaneo) no hay texto adentro: sin OCR no se puede diagnosticar. La decisión es
binaria: *parseable* (hay texto usable) o *no parseable* (escaneado/roto).

Definición operativa (en `src/parsing/quality.py`): un texto es parseable si tiene
**≥ 30 palabras** y **≥ 50% de sus caracteres visibles son letras o números**.
El ratio se mide sobre caracteres no-espacios: un PDF a dos columnas deja muchos
espacios de relleno y eso no es "texto roto".

### 1.2 PDFs sintéticos (control)

60 PDFs generados desde 20 CVs, en 3 maquetas (simple, dos columnas, escaneado):

| Métrica | Resultado |
|---|---|
| Decisiones correctas | **60/60 (100%)** |
| Legibles recuperados | 40/40 (cobertura de palabras 1,000 en simple y 0,999 en columnas) |
| Escaneados detectados | 20/20 (cobertura 0,000) |

### 1.3 PDFs reales (la medición que importa)

El equipo juntó **221 PDFs reales** de CVs (profesiones variadas, casi todos en
inglés). Se etiquetaron con evidencia objetiva:

| Categoría | Archivos | Evidencia |
|---|---|---|
| Legibles (con capa de texto) | **195** | texto extraíble, 69–1.976 palabras |
| Escaneados | **26** | 0 caracteres: 23 con imágenes y 3 sin páginas legibles (2 dicen literalmente "Scanned by CamScanner") |
| Duplicados exactos | 11 | mismo archivo o mismo texto que otro |
| A revisar a ojo | 0 | — |

> **Corrección importante:** se creía que había 8 escaneados. Son **26**: ninguno
> tiene capa de texto. De ellos, 23 tienen imágenes (22 con 1–9 imágenes y 1 con
> 351, porque el escaneo está armado en partes) y 3 no declaran páginas legibles.
> No es una suposición: se verificó página por página (0 caracteres extraídos).

Resultado sobre los **210 archivos únicos**:

| Métrica | Resultado |
|---|---|
| Decisiones correctas | **210/210 (100%)** |
| Legibles recuperados (sensibilidad) | **187/187 (100%)** — objetivo ≥ 90% |
| Escaneados detectados (especificidad) | **23/23 (100%)** |
| F1 (clase "legible") | **1,000** |

### 1.4 Calidad más allá de "tiene texto"

El benchmark binario es fácil (un escaneo da 0 palabras). Para no maquillar el
resultado se miden también los problemas parciales:

| Indicador | Resultado |
|---|---|
| Palabras por CV legible | mínimo 69 · mediana 418 · máximo 1.976 |
| CVs con alguna página sin texto | 14/187 (7,5%) |
| CVs con > 2% de palabras pegadas | 6/187 (3,2%) |
| Escaneados con texto residual | 2/23 (sólo "Scanned by CamScanner") |
| Tiempo de lectura por PDF | mediana 0,40 s en reposo (1,5 s con el equipo cargado) |

**Palabras pegadas**: el PDF no tiene espacios explícitos y el extractor devuelve
`Lookingforapromising&challengingcareer`. Se detectan 6 casos (peor caso: 36% de
las palabras). Rompen el matcheo de habilidades aunque el texto "se lea".

### 1.5 Decisión técnica: dos lectores de PDF

Se compararon dos librerías sobre 40 PDFs reales:

| Extractor | Palabras (media) | Palabras pegadas | Tiempo |
|---|---|---|---|
| pdfplumber | 461 | 3,00% | 242 ms |
| pdfminer.six | **482** | **2,37%** | **158 ms** |

`pdfminer.six` respeta mejor los espacios (en un CV recuperó 1.119 palabras contra
442). **Decisión:** pdfminer.six extrae el texto; pdfplumber se usa para la
estructura (páginas e imágenes, necesarias para detectar escaneos). Ambos vienen
en el mismo entorno, no agrega dependencias nuevas.

También se probó `pdfplumber` con `layout=True`: devuelve exactamente lo mismo,
no aporta nada.

### 1.6 Robustez

- PDFs con 0 páginas legibles (3 archivos): `read_pdf` devuelve texto vacío y
  `error=None`, nunca una excepción. El diagnóstico los trata como escaneados.
- PDF corrupto: `read_pdf` captura la excepción y la devuelve en `error` (la API
  de la Etapa C podrá responder 422 con un mensaje claro).
- Un escaneo no entra al pipeline: el demo corta con
  "El PDF no tiene texto: es un escaneo o está roto".

---

## 2. Detección de secciones (dimensión 2) — mejora aplicada

Se agregó una tercera señal: **encabezados visibles** (`WORK EXPERIENCE`,
`EDUCATION`, `SKILLS`...). Antes se dependía sólo de las entidades del modelo;
en CVs reales el modelo no siempre reconoce la empresa o el puesto, pero el
título de la sección está a la vista.

| Sección | F1 | Precisión | Recall | Exactitud |
|---|---|---|---|---|
| Contacto | 0,985 | 0,971 | 1,000 | 0,971 |
| Experiencia | **0,970** | 0,941 | 1,000 | 0,941 |
| Educación | 0,921 | 0,853 | 1,000 | 0,853 |
| Habilidades | 0,938 | 0,882 | 1,000 | 0,882 |
| **Macro** | **0,9532** | — | — | 0,9118 |
| **Micro** | **0,9538** | — | — | — |

Antes: F1 macro 0,945. **Ahora: 0,9532**, con recall 1,000 en las 4 secciones.

Impacto en CVs reales (187 legibles): los CVs con las 4 secciones detectadas
pasaron de **31,6% a 59,9%**; "Experiencia" faltante bajó de **58,8% a 25,1%**.

> Nota metodológica: el F1 se mide sobre los 34 CVs de prueba de DataTurks, donde
> la "verdad" es la presencia de entidades anotadas. Es la métrica oficial del
> proyecto; se reporta junto con el efecto medido en CVs reales.

---

## 3. Similitud CV–oferta (dimensión 4)

### 3.1 Motores comparados

50 pares (CV, oferta) calificados a mano de 1 a 100 (notas reales del equipo,
completadas con ayuda de IA; se verificó que estuvieran en rango y sin
inversiones evidentes). La métrica es **Spearman** (¿coincide el orden?).

| Motor | Spearman | IC 95% | Pearson | Veredicto |
|---|---|---|---|---|
| **TF-IDF con stopwords ES+EN** | **0,9523** | [0,899 · 0,974] | 0,9407 | **Oficial** ✅ |
| Embeddings (documento entero) | 0,2779 | [0,011 · 0,513] | 0,2118 | Descartado ❌ |
| Embeddings por fragmentos | 0,5003 | [0,256 · 0,686] | 0,5429 | Descartado ❌ |

p < 0,001 para TF-IDF (p = 2,2·10⁻²⁶). El intervalo se calculó por bootstrap
(5.000 remuestreos, semilla 42).

> **Precisión del intervalo:** los 50 pares salen de **25 CVs distintos** (cada CV
> se calificó contra 2 ofertas), así que no son 50 observaciones independientes.
> Al remuestrear **CVs completos** en vez de pares, el IC de TF-IDF queda en
> [0,900 · 0,969]: el resultado no depende de ese supuesto.

### 3.2 Por qué gana TF-IDF y fallan los embeddings

- El CV y la oferta son documentos largos. El modelo de embeddings corta a 512
  tokens y resume todo en un vector: ambos terminan pareciéndose a "un
  currículum" y "una búsqueda laboral" genéricos.
- Partir en fragmentos mejora (0,28 → 0,50) pero sigue lejos: el modelo prioriza
  el tema general, no las habilidades concretas.
- TF-IDF con stopwords se enfoca en las palabras que discriminan
  ("python", "sap", "enfermería") y no en el relleno ("and", "with", "para").
  Sacar las stopwords subió el Spearman de 0,80 a 0,95.
- El tokenizador conserva términos técnicos (`c++`, `c#`, `asp.net`, `node.js`)
  en vez de partirlos; eso subió el Spearman de 0,926 a 0,952.

### 3.3 Calibración de la escala 0–100

El coseno de TF-IDF nunca llega a 1 en documentos largos. Medido sobre **los 1.225
pares posibles** (25 CVs × 49 ofertas del banco de calificación): mediana **0,025**,
percentil 99 **0,058** y máximo **0,072**. Multiplicar por 100 dejaba al mejor par
con **7,2/100**, hundiendo el puntaje global (la similitud pesa 0,40).

**Solución:** cada motor define un techo (coseno = 100 puntos):

| Motor | Techo | Justificación |
|---|---|---|
| TF-IDF | 0,10 | 38% arriba del máximo observado (0,072): deja margen a un CV escrito a medida |
| Embeddings | 0,60 | ~0,2 entre textos no relacionados, ~0,6 entre textos del mismo tema |
| Embeddings por fragmentos | 0,70 | mismo criterio, distribución más alta |

El mapeo es lineal y monótono: **no cambia el orden** (el Spearman es idéntico),
sólo hace interpretable la escala. El puntaje es una medida **relativa**: 100 =
coincidencia total según lo observado en este corpus, no una probabilidad.

### 3.4 Verificación de punta a punta

| Caso | Resultado |
|---|---|
| CV real de software (cv 5) vs oferta .NET | global **58,7** · parseabilidad 100 · secciones 75 · similitud 62,3 |
| CV real sin relación (cv 92) vs la misma oferta | global **36,4** · parseabilidad 100 · secciones 75 · similitud **6,5** |
| CV escaneado | rechazado con mensaje claro (sin OCR no hay diagnóstico) |

Tiempo del motor de diagnóstico (texto ya extraído): **0,05 s** de mediana con el
equipo en reposo (0,20 s con otras aplicaciones abiertas).
Tiempo total por PDF (lectura + NLP): **~0,5 s** en reposo y **~1,8 s** con el
equipo cargado → en ambos casos por debajo del límite de 3 s.

---

## 4. Diccionario de habilidades (dimensión 3) — limpieza aplicada

El diccionario tenía ruido que en CVs reales generaba falsos positivos:
"qualification" aparecía en 96 CVs, "ms" en 80, "word" en 54, "planning" en 45.
Se agregó una lista de exclusión documentada (`RUIDO_CVS_REALES`) con 20 términos
del inglés general y abreviaturas ambiguas, conservando las formas específicas
("ms office", "ms word", "communication skills", "graphic design"). También se
corrigió un doble conteo: si "communication" estaba dentro de "communication
skills", ahora se cuenta una sola vez (se queda el término más largo).

| Métrica | Antes | Ahora |
|---|---|---|
| Términos del diccionario | 808 | **790** |
| Habilidades en los 34 CVs de prueba | 920 | **830** |
| Promedio por CV | 27,1 | **24,4** |
| CVs con al menos 1 habilidad | 34/34 | **34/34** |

En los 187 CVs reales: mediana de **4 habilidades** por CV (p10 0, p90 10). Es
bajo porque el diccionario es fuerte en tecnología y débil en oficios
(enfermería, mecánica, derecho). **Limitación conocida y documentada.**

---

## 5. Limitaciones (para decir en la defensa)

1. **Sin OCR**: los 26 escaneados se detectan, pero no se pueden diagnosticar.
   Fuera del alcance del MVP; se propone como trabajo futuro.
2. **Español**: el lote real es 100% inglés. TF-IDF no cruza idiomas
   (CV en español vs oferta en inglés no encuentra coincidencias léxicas). Los
   embeddings sí cruzan, pero su ordenamiento es malo (0,28).
3. **NER en CVs reales**: falta la entidad PERSONA en 56,1% de los CVs. El modelo
   se entrenó con 153 CVs de un dataset de la India; no generaliza bien. Por eso
   las secciones se apoyan también en encabezados y reglas.
4. **Habilidades**: el diccionario cubre tecnología mucho mejor que oficios.
5. **Notas humanas**: los 50 pares son al azar, sin ningún par realmente bueno
   (máximo 47/100). Validan el **orden** de los motores; el techo de la escala se
   fijó aparte, con el máximo observado en los 1.225 pares CV×oferta posibles.
6. **4.000 PDFs pendientes**: sin etiquetas no mejoran ninguna métrica. Sirven
   para medir la tasa real de escaneos en el mundo y para análisis de errores.

---

## 6. Cómo reproducir todo

```bash
# 1. Etiquetar los PDFs reales (genera labels.csv con evidencia)
.venv/bin/python scripts/build_pdf_labels.py

# 2. Parseabilidad: sintéticos y reales
.venv/bin/python scripts/eval_parseability.py
.venv/bin/python scripts/eval_parseability.py --reales

# 3. Secciones y habilidades (Etapa A, con las mejoras de la Etapa B)
.venv/bin/python scripts/eval_sections.py
.venv/bin/python scripts/eval_skills_gazetteer.py

# 4. Calidad de extracción sobre CVs reales (sin oferta)
.venv/bin/python scripts/eval_cv_reales.py

# 5. Similitud contra las notas humanas
.venv/bin/python scripts/eval_similarity.py --motor tfidf
.venv/bin/python scripts/eval_similarity.py --motor embeddings
.venv/bin/python scripts/eval_similarity.py --motor embeddings_fragmentos
.venv/bin/python scripts/eval_similarity.py --matriz   # justifica el techo 0-100

# 6. Demostración con un PDF real
.venv/bin/python scripts/demo_diagnostico.py --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" --par par_005
```

Reportes generados en `models/`: `parseability_report.json`,
`parseability_reales_report.json`, `sections_report.json`,
`skills_gazetteer_report.json`, `cv_reales_reporte.json`,
`similarity_tfidf_report.json`, `similarity_embeddings_report.json`,
`similarity_embeddings_fragmentos_report.json` y
`similarity_matriz_tfidf.json`.

---

## 7. Glosario

- **Parseabilidad**: si se puede extraer texto usable de un PDF.
- **PDF escaneado**: una foto del CV; no tiene capa de texto, requiere OCR.
- **Capa de texto**: el texto invisible seleccionable que el PDF guarda adentro.
- **Stopwords**: palabras vacías ("and", "de", "para") que no aportan significado.
- **TF-IDF**: mide qué palabras son importantes en un texto comparándolas con el
  resto del corpus; se combina con similitud coseno.
- **Embeddings**: convertir texto en vectores numéricos que representan su
  significado; sirven para sinónimos e idiomas distintos.
- **Coseno**: medida de parecido entre dos vectores (0 = nada, 1 = idéntico).
- **Spearman**: correlación de **orden** entre dos rankings (-1 a 1).
- **IC 95% (bootstrap)**: rango donde caería el valor si se repitiera el
  experimento con otras muestras; se calcula remuestreando los datos.
- **F1**: media armónica de precisión y recall (0 a 1).
- **Precisión**: de lo que el sistema marcó como presente, cuánto era correcto.
- **Recall**: de lo que realmente estaba, cuánto encontró.
- **Gazetteer**: diccionario de términos conocidos que se buscan en el texto.
- **RUIDO_CVS_REALES**: lista negra de términos genéricos que parecían habilidades
  pero no lo son (ej. "qualification").
- **Calibración**: transformar una medida cruda (coseno) a una escala
  interpretable (0–100) sin cambiar el orden.
