# Cómo probar CV-Decoder

Guía corta para verificar que el MVP funciona en tu máquina.

Todos los comandos se ejecutan desde la raíz del proyecto:

```bash
cd /home/sofia/CV-Decoder
```

> Podés usar `.venv/bin/python` directamente o activar el entorno con
> `source .venv/bin/activate`.

---

## 1. Tests automáticos

```bash
.venv/bin/python -m pytest -q
```

Resultado esperado:

```text
33 passed
```

Si falla algún test, no sigas con las otras pruebas: primero hay que revisar el
error.

---

## 2. Demo con un CV y una oferta del benchmark

No necesita levantar la API.

```bash
.venv/bin/python scripts/demo_diagnostico.py --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" --par par_005
```

Resultado esperado:

```text
"puntaje_global": 25.0,
"puntaje_ats": 87.5,
"puntaje_match": 25.0,
"nivel_match": "medio",
"requisitos": {
  "cap_match": 25.0,
  "cobertura_obligatorios": 0.0
},
"seniority": {
  "anos_cv": 7,
  "anos_pedidos": null,
  "nivel_cv": null,
  "nivel_oferta": null,
  "ajuste": 1.0
},
"similitud": {
  "puntaje": 38.9,
  "crudo": 0.0623,
  "fuente": "texto_completo",
  "detalle": {}
}
```

Si ves esos valores, el motor de diagnóstico funciona.

> Si copiás un comando en varias líneas, la barra `\` tiene que ser el último
> carácter, sin espacios después. Si no, bash intenta ejecutar `--pdf` como un
> comando aparte. Lo más simple es pegar todo en una sola línea.

---

## 3. Probar la API desde Swagger

Terminal 1:

```bash
.venv/bin/uvicorn src.api.main:app --reload
```

Abrí en el navegador:

```text
http://127.0.0.1:8000/docs
```

Pasos:

1. Buscá `POST /api/v1/analyze-cv`.
2. Hacé clic en **Try it out**.
3. En `cv`, subí un PDF legible de menos de **5 MB**.
4. En `oferta`, pegá el texto de la propuesta (mínimo **20 palabras**).
5. Hacé clic en **Execute**.

También podés verificar que la API esté viva en:

```text
http://127.0.0.1:8000/health
```

---

## 4. Probar la API desde la consola

Con la API corriendo en otra terminal:

```bash
.venv/bin/python scripts/cliente_api.py --pdf "data/benchmarks/pdfs_reales/cv (5).pdf" --par par_005
```

O con tu propio CV y una oferta escrita directamente:

```bash
.venv/bin/python scripts/cliente_api.py --pdf ~/mi_cv.pdf --oferta "Buscamos analista de datos con Python, SQL y Power BI..."
```

Si la oferta es larga, guardala en un archivo de texto y usá:

```bash
.venv/bin/python scripts/cliente_api.py --pdf ~/mi_cv.pdf --oferta-archivo oferta.txt
```

---

## 5. Probar con tu propio CV y tu propia oferta

La forma más cómoda es Swagger:

1. Levantá la API:
   ```bash
   .venv/bin/uvicorn src.api.main:app --reload
   ```
2. Abrí `http://127.0.0.1:8000/docs`.
3. Subí tu CV y pegá la oferta.
4. Revisá el JSON de respuesta.

### Cómo leer el resultado

| Campo | Qué significa |
|---|---|
| `puntaje_ats` | Calidad del CV como documento, de 0 a 100. |
| `puntaje_match` | Compatibilidad con la oferta, de 0 a 100. |
| `puntaje_global` | Alias de `puntaje_match` (compatibilidad). |
| `nivel_match` | Etiqueta: bajo, medio, bueno o muy bueno. |
| `requisitos` | Requisitos obligatorios/deseables, cobertura y cap aplicado. |
| `dimensiones.parseabilidad` | Si el PDF se pudo leer correctamente. |
| `dimensiones.secciones` | Qué secciones detectó (experiencia, educación, habilidades, etc.). |
| `dimensiones.keyword_gap` | Skills de la oferta que no aparecen en el CV. |
| `dimensiones.similitud` | Qué tan parecido es el CV a la oferta. |

El resultado es **relativo**: 100 significa “coincidencia total” según el corpus
del proyecto, no una probabilidad.

---

## 6. Casos de error que conviene probar

| Caso | Resultado esperado |
|---|---|
| PDF escaneado o imagen sin texto | `422` con `PDF_SIN_TEXTO` |
| Oferta de menos de 20 palabras | `422` con `OFERTA_MUY_CORTA` |
| Archivo que no es PDF | `415` con `FORMATO_NO_SOPORTADO` |
| PDF de más de 5 MB | `413` con `PDF_MUY_GRANDE` |

---

## 7. Recomendaciones

- Para una prueba representativa, usá CV y oferta **en inglés**. En español
  funciona, pero el modelo NER y el diccionario de skills están más orientados
  al inglés.
- El PDF tiene que tener texto seleccionable. Los escaneos se rechazan porque el
  MVP no incluye OCR.
- Si el servidor no está corriendo, `cliente_api.py` falla con un error de
  conexión. En ese caso, primero levantá `uvicorn`.
- Si `demo_diagnostico.py` dice que falta el modelo, verificá que exista
  `models/ner_dataturks_sm/` o entrenalo con:
  ```bash
  .venv/bin/python scripts/train_ner.py --sources dataturks --schema fine --output ner_dataturks_sm
  ```
