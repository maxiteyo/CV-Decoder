# Etapa C — API REST del MVP

**Fecha de cierre:** 2026-10-25
**Estado:** terminada y probada (16 pruebas automáticas en verde).
**Punto de entrada:** `src.api.main:app`
**Endpoint principal:** `POST /api/v1/analyze-cv`

---

## 1. Qué resuelve esta etapa

Hasta la Etapa B todo se probaba con scripts de consola. Eso sirve para medir,
pero no para que otra persona use el producto. La Etapa C agrega una **API REST**:
un programa que queda escuchando en una dirección local y recibe pedidos por HTTP.

El flujo es siempre el mismo:

```text
PDF del CV  +  texto de la oferta
        │
        ▼
   POST /api/v1/analyze-cv
        │
        ▼
   JSON con puntaje global (0–100) y 4 dimensiones
```

Ventajas concretas para la demo y para el equipo:

- Se prueba **desde el navegador**, sin escribir código (`http://127.0.0.1:8000/docs`).
- Cualquier lenguaje o herramienta (curl, Postman, Python) puede consumirla.
- El JSON tiene un contrato fijo: si mañana cambia el motor interno, la respuesta
  sigue siendo la misma.
- **No guarda nada**: el PDF se escribe en un archivo temporal, se procesa y se
  borra. No hay base de datos ni historial.

Fuera de alcance, igual que en el Project Charter: frontend propio, login,
persistencia, reescritura del PDF, scraping en vivo y OCR.

---

## 2. Cómo levantarla (paso a paso)

### 2.1 Requisitos previos

1. Estar en la carpeta del repositorio:
   ```bash
   cd /home/maximo/Escritorio/CV-Decoder
   ```
2. Tener el entorno virtual creado y las dependencias instaladas:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Si el entorno ya existía, alcanza con activarlo. Las dependencias nuevas de
   esta etapa (`fastapi`, `uvicorn`, `python-multipart`, `pytest`, `httpx2`) ya
   están fijadas en `requirements.txt`.
3. Tener el modelo de entidades entrenado en `models/ner_dataturks_sm/`.
   Ese modelo **no se versiona** porque es un artefacto binario. Si falta, la API
   no arranca y muestra este mensaje:
   ```text
   No se encontró el modelo de entidades en .../models/ner_dataturks_sm.
   Entrenalo con: .venv/bin/python scripts/train_ner.py (ver README).
   ```
   En esta máquina ya está entrenado; en una copia nueva hay que correr
   `build_ner_dataset.py` y `train_ner.py` (unos 10 minutos en CPU).

### 2.2 Arrancar el servidor

```bash
source .venv/bin/activate
uvicorn src.api.main:app --reload
```

Qué significa cada cosa:

- `uvicorn`: servidor web que ejecuta la API.
- `src.api.main:app`: archivo `src/api/main.py`, variable `app`.
- `--reload`: reinicia solo cuando cambia el código. Es cómodo mientras se
  programa; para la demo se puede omitir (arranca más rápido y no vigila archivos).

La primera vez tarda unos **8 segundos** porque carga el modelo de spaCy, el
diccionario de 790 habilidades y "calienta" scikit-learn. Es una sola vez. Cuando
esté listo se ve:

```text
INFO cv_decoder.api: Modelos cargados y calentados en 8.29 s
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Dejá esa terminal abierta**: mientras el servidor corre, no devuelve el prompt.
Para cortarlo: `Ctrl+C`.

### 2.3 Comprobar que está viva

En otra terminal (o en el navegador):

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"estado":"ok","version":"0.1.0","modelo_entidades":"ner_dataturks_sm","motor_oficial":"tfidf"}
```

---

## 3. Probarla desde el navegador (recomendado para la primera vez)

FastAPI genera sola una página de documentación interactiva (**Swagger UI**).

1. Abrí <http://127.0.0.1:8000/docs>.
2. Buscá la tarjeta **POST /api/v1/analyze-cv** y hacé clic para desplegarla.
3. Clic en **Try it out**.
4. En **cv**, clic en **Choose File** y elegí un PDF de CV.
   - Ideal: un CV con capa de texto (se puede seleccionar texto al abrirlo).
   - Los PDFs reales del equipo están en `data/benchmarks/pdfs_reales/`.
5. En **oferta**, pegá el texto completo de una búsqueda laboral. Por ejemplo:

   ```text
   We are looking for a Data Analyst with strong Python and SQL skills.
   You will build dashboards, clean data and communicate findings to the team.
   Experience with Excel is required. Knowledge of Docker is a plus.
   Project management experience is valued.
   ```

6. En **motor**, dejá `tfidf` (es el oficial y el más rápido).
7. Clic en **Execute**.

Abajo aparecen tres cosas:

- **Request URL**: la dirección exacta que se llamó.
- **Server response / Code 200**: el JSON del diagnóstico.
- **Download**: botón para guardar la respuesta.

### 3.1 Cómo leer la respuesta

> El JSON de abajo es de un par distinto (`par_005`). Con la oferta de ejemplo de
> arriba el global da **54,6** (similitud 35,5; brecha 33,3), porque todo depende
> de la oferta que se pegue. Lo importante es la estructura, no memorizar el
> número.

```json
{
  "puntaje_global": 58.7,
  "metadatos": {
    "archivo": "cv (5).pdf",
    "paginas": 1,
    "palabras": 151,
    "motor_similitud": "tfidf",
    "tiempo_ms": 1100
  },
  "dimensiones": {
    "parseabilidad": { "puntaje": 100.0 },
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
      "puntaje": 0.0,
      "coincidencias": [],
      "faltantes": [".net", "agile", "asp.net", "design"],
      "total_oferta": 9,
      "total_cv": 8
    },
    "similitud": { "puntaje": 62.3, "motor": "tfidf", "crudo": 0.0623 }
  }
}
```

| Campo | Qué significa |
|---|---|
| `puntaje_global` | Suma ponderada de las 4 dimensiones (0–100). **No** es una probabilidad ni un "apto/no apto". |
| `metadatos.paginas` | Páginas con estructura legible que encontró el lector. |
| `metadatos.palabras` | Palabras de texto extraídas del PDF. |
| `metadatos.tiempo_ms` | Lo que tardó el procesamiento: lectura del PDF + NLP, en milisegundos. |
| `parseabilidad.puntaje` | 100 si el texto es usable; si no, la API rechaza el PDF con error 422. |
| `secciones.detalle` | Si se detectó cada una de las 4 secciones. |
| `secciones.faltantes` | Las que no se detectaron (candidatas a agregar en el CV). |
| `keyword_gap.coincidencias` | Habilidades que pide la oferta **y** están en el CV. |
| `keyword_gap.faltantes` | Habilidades que pide la oferta y **no** están en el CV. |
| `keyword_gap.puntaje` | Porcentaje de habilidades de la oferta cubiertas por el CV. |
| `similitud.puntaje` | Parecido CV–oferta en escala 0–100 (calibrada). |
| `similitud.crudo` | Coseno TF-IDF sin calibrar (0–1), para auditoría. |

Los pesos del puntaje global son los mismos de todo el proyecto:
**similitud 0,40 · secciones 0,25 · brecha de habilidades 0,20 · parseabilidad 0,15**.

### 3.2 Probar los errores desde Swagger

No hace falta que todo salga bien: los errores también son parte del contrato.

| Prueba | Qué hacer | Qué debe pasar |
|---|---|---|
| PDF escaneado | Subir `data/benchmarks/pdfs_reales/cv (1764).pdf` | `422` con código `PDF_SIN_TEXTO` |
| Oferta muy corta | Poner solo `Data Analyst` en `oferta` | `422` con código `OFERTA_MUY_CORTA` |
| Archivo que no es PDF | Subir un `.txt` renombrado o una imagen | `415` con código `FORMATO_NO_SOPORTADO` o `NO_ES_PDF` |
| Sin oferta | Dejar `oferta` vacía | `422` con código `VALIDACION` |

El cuerpo de error siempre tiene la misma forma:

```json
{
  "error": {
    "codigo": "PDF_SIN_TEXTO",
    "mensaje": "El PDF no tiene texto usable (3 palabras y 1 imágenes detectadas).",
    "sugerencia": "Es un escaneo o una foto. Subí un PDF con capa de texto (no una imagen) o pasalo primero por un OCR."
  }
}
```

`codigo` es estable (sirve para programar); `mensaje` y `sugerencia` son para
personas. En errores de validación se agrega `error.detalles` con el campo exacto
que falló.

---

## 4. Probarla sin navegador: script incluido

`scripts/cliente_api.py` hace el pedido por HTTP usando solo la biblioteca
estándar (no agrega dependencias). Requiere que el servidor esté corriendo.

### 4.1 Con un par de la planilla de calificación

```bash
.venv/bin/python scripts/cliente_api.py \
  --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" \
  --par par_005
```

### 4.2 Con una oferta escrita a mano

```bash
.venv/bin/python scripts/cliente_api.py \
  --pdf "ruta/al/cv.pdf" \
  --oferta "We are looking for a Data Analyst with Python and SQL. Experience with Excel and dashboards is required."
```

### 4.3 Con la oferta en un archivo de texto

```bash
.venv/bin/python scripts/cliente_api.py \
  --pdf "ruta/al/cv.pdf" \
  --oferta-archivo oferta.txt
```

### 4.4 Opciones

| Opción | Para qué |
|---|---|
| `--pdf` | Ruta del CV (obligatoria). |
| `--par` | ID de par de `data/benchmarks/pares_para_calificar.csv` (ej. `par_005`). |
| `--oferta` | Texto de la oferta entre comillas. |
| `--oferta-archivo` | Archivo `.txt` con la oferta. |
| `--motor` | `tfidf` (por defecto), `embeddings` o `embeddings_fragmentos`. |
| `--url` | URL base; por defecto `http://127.0.0.1:8000`. |

El script primero consulta `/health`. Si el servidor no está levantado, no falla
con un error críptico: avisa y muestra el comando para arrancarlo.

---

## 5. Probarla con curl

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze-cv \
  -F "cv=@data/benchmarks/pdfs_reales/cv (5).pdf;type=application/pdf" \
  -F "oferta=We are looking for a Data Analyst with strong Python and SQL skills. Experience with Excel is required. Knowledge of Docker is a plus."
```

Detalles de sintaxis:

- `-F` arma un formulario `multipart/form-data` (archivo + texto).
- `@` indica que el valor es un archivo.
- Si la ruta tiene espacios, va entre comillas dobles como en el ejemplo.
- Para ver el JSON "lindo", agregar `| python -m json.tool` al final.

También se puede probar con **Postman**: método `POST`, pestaña **Body →
form-data**, campo `cv` de tipo **File** y campo `oferta` de tipo **Text**.

---

## 6. Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| `POST` | `/api/v1/analyze-cv` | Diagnóstico completo (el endpoint del producto). |
| `GET` | `/health` | Estado del servicio y versión del modelo. |
| `GET` | `/` | Atajo con los enlaces principales (no aparece en Swagger). |
| `GET` | `/docs` | Swagger UI interactiva. |
| `GET` | `/redoc` | Documentación alternativa de solo lectura. |
| `GET` | `/openapi.json` | Contrato OpenAPI en JSON (para integrar). |

### 6.1 Pedido de `POST /api/v1/analyze-cv`

`multipart/form-data`:

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `cv` | archivo | Sí | Extensión `.pdf`, firma `%PDF`, tamaño ≤ **5 MB**, con texto usable. |
| `oferta` | texto | Sí | ≥ **20 palabras** y ≤ **20.000 caracteres**. |
| `motor` | texto | No | `tfidf` (por defecto), `embeddings`, `embeddings_fragmentos`. |

¿Por qué esos límites? Protegen el tiempo de respuesta y evitan pedidos sin
sentido (una oferta de dos palabras no permite calcular una brecha real). Están
documentados en el código (`src/api/main.py`) y en la tabla de errores.

### 6.2 Respuesta `200`

El esquema completo está en `src/api/schemas.py` y se puede ver en vivo en
`/docs` (sección **Schemas**). Todos los puntajes van de 0 a 100.

### 6.3 Motores de similitud

| Motor | Primera consulta | Consultas siguientes | Veredicto |
|---|---|---|---|
| `tfidf` | ~1,1 s | ~1,0–1,1 s | **Oficial** (Spearman 0,9523) |
| `embeddings` | ~35 s (carga el modelo) | ~2,4 s | Solo comparación (Spearman 0,2779) |
| `embeddings_fragmentos` | ~35 s | similar a embeddings | Solo comparación (Spearman 0,5003) |

La primera consulta con embeddings tarda porque carga
`paraphrase-multilingual-mpnet-base-v2` en memoria. Si el modelo no está en caché,
además necesita internet para descargarlo. Para la demo: **usar `tfidf`**.

---

## 7. Errores y qué hacer

| HTTP | Código | Cuándo aparece | Solución |
|---|---|---|---|
| `400` | `PDF_VACIO` | El archivo no tiene bytes. | Elegir un PDF con contenido. |
| `413` | `PDF_MUY_GRANDE` | Supera 5 MB. | Comprimir el PDF o bajar la calidad de las imágenes. |
| `415` | `FORMATO_NO_SOPORTADO` | El nombre no termina en `.pdf`. | Convertir el CV a PDF. |
| `415` | `NO_ES_PDF` | No empieza con `%PDF`. | Subir el PDF original, no una captura. |
| `422` | `PDF_ILEGIBLE` | Está dañado o protegido con contraseña. | Abrirlo en un lector, guardarlo de nuevo, quitar la contraseña. |
| `422` | `PDF_SIN_TEXTO` | Escaneado, foto o casi sin texto. | Subir un PDF con capa de texto o pasar por OCR. |
| `422` | `OFERTA_MUY_CORTA` | Menos de 20 palabras. | Pegar la descripción completa del puesto. |
| `422` | `OFERTA_MUY_LARGA` | Más de 20.000 caracteres. | Pegar solo la descripción, no un archivo entero. |
| `422` | `VALIDACION` | Falta `cv` u `oferta`, o `motor` inválido. | Revisar los nombres de los campos en `/docs`. |
| `500` | `ERROR_INTERNO` | Fallo inesperado. | Reintentar; si persiste, mirar la terminal del servidor. |

La API **no acepta** un PDF escaneado con puntaje 0: lo rechaza con 422 y explica
por qué. Es una decisión de producto: sin texto no hay nada que diagnosticar y el
OCR está fuera del alcance.

---

## 8. Decisiones de diseño

1. **Un solo endpoint productivo.** El alcance del MVP es diagnosticar; no hay
   CRUD ni historial. Menos superficie, menos cosas que explicar y romper.
2. **`multipart/form-data` en vez de base64.** Es lo que entienden el navegador,
   Swagger, curl y Postman sin conversiones. El PDF viaja como archivo.
3. **Nada se persiste.** El PDF se escribe en un archivo temporal con
   `tempfile`, se procesa y se borra en un `finally` (se cumple incluso si falla).
   El nombre original solo se devuelve como dato, nunca se usa como ruta.
4. **Trabajo pesado en un hilo aparte.** `read_pdf` y `analizar` son bloqueantes
   (CPU). Se ejecutan con `run_in_threadpool` para no congelar el bucle de la API
   mientras un pedido procesa un PDF.
5. **Calentamiento al arrancar.** La primera llamada a scikit-learn y a spaCy
   cuesta varios segundos (imports y compilación). Se pagan una vez en el
   `lifespan`, no en la primera consulta real. Sin esto, el primer pedido tardaba
   **7,2 s**; con esto, ~1,1 s.
6. **Errores con forma estable.** `{"error": {codigo, mensaje, sugerencia}}` para
   todas las respuestas 4xx/5xx, incluidas las de validación de Pydantic. Un
   cliente puede programar contra `codigo` sin leer el texto.
7. **Límites explícitos.** 5 MB, 20 palabras y 20.000 caracteres. No son
   arbitrarios: acotan el costo por pedido y descartan entradas incompletas.
8. **TF-IDF por defecto.** Es el motor con mejor ordenamiento medido (0,95 vs
   0,28) y el único que cumple el límite de 3 s sin cargar un transformer.
9. **Sin CORS, sin auth, sin base de datos.** Fuera del alcance declarado. Si
   mañana se agrega un frontend en otro puerto, CORS es una línea; no se agrega
   "por las dudas".

---

## 9. Pruebas automáticas

Archivo: `tests/test_api.py` (16 pruebas). Generan sus propios PDFs al vuelo con
`fpdf2` y `Pillow`, así que **no dependen de `data/`** (que no se versiona).

```bash
.venv/bin/python -m pytest -q       # resumen
.venv/bin/python -m pytest -v       # nombre por nombre
```

Resultado: **16 passed** en ~27 s (el modelo se carga una vez).

Qué cubren:

| Grupo | Pruebas |
|---|---|
| Sistema | `/health`, `/`, `/openapi.json`. |
| Camino feliz | Diagnóstico completo, rangos 0–100, las 4 secciones, coincidencias y faltantes de habilidades, suma ponderada del global, metadatos. |
| Privacidad | Que no queden archivos `cv_decoder_*.pdf` en el temporal después del pedido. |
| Errores | `.txt`, PDF falso, archivo vacío, PDF roto, PDF escaneado, oferta corta, oferta larga, PDF > 5 MB, falta de oferta, motor inválido. |

La prueba del PDF escaneado **genera una imagen real** dentro de un PDF (sin capa
de texto), no simula el error: verifica el mismo camino que un usuario.

> Nota técnica: `fastapi.testclient` con Starlette 1.10 pide `httpx2`; ya está en
> `requirements.txt` como dependencia de pruebas. Sin él aparece un warning de
> deprecación (no un fallo).

---

## 10. Rendimiento medido

Mediciones en este equipo, servidor local, después del calentamiento:

| Escenario | Tiempo |
|---|---|
| Arranque (carga + calentamiento) | **8,3 s** (una sola vez) |
| `POST` con TF-IDF (CV de 1 página) | **1,0–1,1 s** |
| `POST` con embeddings (ya cargado) | **~2,4 s** |
| Primera consulta con embeddings | **~34,8 s** (carga el transformer) |
| Rechazo de PDF escaneado | ~0,1 s (no llega al NLP) |

El límite del Project Charter es **< 3 s por PDF**: se cumple con TF-IDF y con
embeddings ya cargados. La primera consulta con embeddings no lo cumple, y por eso
el motor oficial y el valor por defecto es TF-IDF.

El costo dominante es la lectura del PDF (~0,8 s en este equipo); el motor de NLP
con el texto ya extraído tarda 0,05–0,20 s.

---

## 11. Limitaciones (declaradas)

- **Sin OCR:** un escaneo se detecta y se rechaza; no se lee.
- **Mejor en inglés:** el NER se entrenó en inglés y TF-IDF no cruza idiomas. Un
  CV en español puede analizarse, pero la similitud y las entidades pierden
  calidad.
- **Un proceso, CPU:** pedidos simultáneos comparten CPU y se serializan en
  buena medida. Para el MVP y la demo alcanza; no es un servicio de producción.
- **Modelo no versionado:** `models/` está en `.gitignore`; en otra máquina hay
  que entrenarlo (o copiar la carpeta).
- **Embeddings necesitan caché/Internet** la primera vez.
- **Sin autenticación:** cualquiera con acceso al puerto puede usarla. Es local.
- **El puntaje es relativo:** sirve para comparar y priorizar mejoras, no para
  decidir una contratación.

---

## 12. Checklist para la demo oral

1. `source .venv/bin/activate && uvicorn src.api.main:app` (sin `--reload`).
2. Esperar `Modelos cargados y calentados` y abrir `/docs`.
3. Mostrar `GET /health` → `estado: ok`.
4. `POST /api/v1/analyze-cv` con un CV bueno + oferta → mostrar el JSON y el
   puntaje global (ejemplo medido con `par_005`: **58,7**, similitud 62,3).
5. Subir el CV escaneado → mostrar el **422** con `PDF_SIN_TEXTO` y la sugerencia.
6. Poner una oferta de dos palabras → mostrar **422** `OFERTA_MUY_CORTA`.
7. Mostrar la pestaña **Schemas** de Swagger: el contrato es público.
8. Cerrar con `.venv/bin/python -m pytest -q` → **16 passed**.
9. (Opcional) Mostrar `scripts/cliente_api.py` para probar sin navegador.

Frase para el jurado: *"La API no guarda el CV, no requiere login y rechaza con
un mensaje claro lo que no puede analizar; el motor tarda alrededor de un segundo
y el contrato JSON es estable."*

---

## 13. Glosario de esta etapa

- **API REST:** interfaz por HTTP con rutas y métodos (`GET`, `POST`) que
  devuelve datos, normalmente JSON.
- **Endpoint:** cada ruta concreta de la API (por ejemplo
  `/api/v1/analyze-cv`).
- **JSON:** formato de texto con pares clave–valor.
- **`multipart/form-data`:** formato de pedido que permite mandar archivos y
  campos de texto en el mismo cuerpo.
- **Swagger / OpenAPI:** especificación de la API y página interactiva que se
  genera sola desde el código (`/docs`).
- **Uvicorn:** servidor que ejecuta la aplicación FastAPI.
- **Pydantic:** biblioteca que valida los datos de entrada y salida contra tipos.
- **HTTP 200 / 400 / 413 / 415 / 422 / 500:** código de estado; 2xx salió bien,
  4xx error del pedido, 5xx error del servidor.
- **422:** el pedido está bien formado pero el contenido no se puede procesar
  (PDF escaneado, oferta corta, campo inválido).
- **Threadpool:** hilos de trabajo para no bloquear el bucle principal mientras
  se hace una tarea pesada.
- **Archivo temporal:** archivo en el disco que se crea para procesar algo y se
  borra al terminar.
- **`lifespan`:** gancho de FastAPI que corre al arrancar y al apagar la app; acá
  se usa para cargar el modelo una sola vez.
- **CORS:** permiso para que una página web de otro origen llame a la API. No se
  usa porque no hay frontend.
- **Base64:** forma de meter un archivo dentro de un texto. Se descartó para no
  inflar el pedido ni complicar las pruebas.

---

## 14. Reproducir en otra máquina

La guía completa, pensada para alguien que clona el repositorio por primera vez,
está en [`docs/guia-de-uso.md`](guia-de-uso.md). Resumen:

1. Clonar el repositorio e instalar dependencias (`README` §7.1). PyTorch CPU se
   instala desde su índice propio y `en_core_web_sm` no viene en
   `requirements.txt`.
2. Descargar DataTurks y los dos repositorios de referencia del diccionario
   (las rutas exactas están en la guía, §B.3).
3. Generar el dataset y entrenar el modelo de entidades:
   ```bash
   python scripts/build_ner_dataset.py
   python scripts/train_ner.py --sources dataturks --output ner_dataturks_sm
   ```
   El nombre `ner_dataturks_sm` es el que espera la API; el valor por defecto de
   `--output` es otro y la API no lo encontraría.
4. (Opcional) Reproducir métricas de las etapas A y B:
   ```bash
   python scripts/build_test_pdfs.py
   python scripts/build_pdf_labels.py
   python scripts/eval_parseability.py --reales
   python scripts/eval_sections.py
   python scripts/eval_similarity.py --motor tfidf
   ```
5. Levantar la API y correr las pruebas:
   ```bash
   uvicorn src.api.main:app --reload
   .venv/bin/python -m pytest -q
   ```

Los PDFs reales del equipo no están en Git: son 221 archivos y 37 MB. La API
funciona igual con cualquier PDF que se suba desde Swagger.

---

## 15. Archivos de esta etapa

| Archivo | Para qué sirve |
|---|---|
| `src/api/main.py` | Aplicación FastAPI: endpoint, validaciones, errores, calentamiento. |
| `src/api/schemas.py` | Modelos Pydantic de entrada/salida y ejemplos para Swagger. |
| `src/api/__init__.py` | Marca el paquete. |
| `tests/conftest.py` | Permite importar `src` al correr pytest. |
| `tests/test_api.py` | 16 pruebas automáticas de la API. |
| `scripts/cliente_api.py` | Cliente de consola (sin dependencias extra). |
| `docs/etapa-c-api.md` | Este documento. |
| `requirements.txt` | Dependencias nuevas fijadas. |
| `README.md` | Actualizado con los comandos de la API. |
| `docs/bitacora-proyecto.md` | Etapa C agregada al recorrido. |
