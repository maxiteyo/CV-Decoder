# Etapa A — Resultados (limpieza de datos + modelo de entidades)

Fecha: 2026-10-11 · Semilla de reproducibilidad: **42**

Este documento resume qué se hizo en la Etapa A, con qué datos y qué resultados
se obtuvieron. Los números salen de los reportes guardados en `models/`.

---

## 1. Qué se construyó

| Pieza | Archivo | Qué hace |
|---|---|---|
| Configuración y rutas | `src/config.py` | Centraliza rutas y la semilla 42. |
| Semilla global | `src/utils/seeds.py` | Hace reproducible todo lo que usa azar. |
| Esquema de etiquetas | `src/data_loader/labels.py` | Traduce etiquetas y define secciones. |
| Limpieza | `src/data_loader/cleaning.py` | Valida textos, arregla solapamientos y bordes. |
| Lectura DataTurks | `src/data_loader/dataturks.py` | 220 CVs anotados (dato principal). |
| Lectura refuerzo | `src/data_loader/mehyarmlaweh.py` | 5029 CVs ruidosos (solo HABILIDAD). |
| Diccionario de habilidades | `src/data_loader/skills_lexicon.py` | 808 habilidades curadas. |
| Armado del dataset | `scripts/build_ner_dataset.py` | Limpia, separa y guarda en formato spaCy. |
| Entrenamiento | `scripts/train_ner.py` | Entrena y mide el modelo de entidades. |
| Secciones | `scripts/eval_sections.py` | Mide la detección de secciones. |
| Habilidades | `scripts/eval_skills_gazetteer.py` | Extrae habilidades con diccionario. |

---

## 2. Datos y limpieza

- **Dato principal:** DataTurks, *Entity Recognition in Resumes* → **220 CVs**, 10 etiquetas.
- **Refuerzo (opcional):** *NER Annotated CVs* → 5029 CVs ruidosos. Tras limpieza
  estricta (solo términos del diccionario curado): **4.788 CVs** con **37.807**
  marcas de habilidad. Se usa **solo para entrenar** (nunca para validar/probar).
- **Sin filtración de datos:** se eliminó del refuerzo cualquier CV que ya estuviera
  en DataTurks.
- **Separación (semilla 42):** DataTurks en 70/15/15 →
  **153 entrenamiento / 32 validación / 34 prueba**.

---

## 3. Resultado del modelo de entidades (esquema detallado, 10 etiquetas)

Entrenado solo con DataTurks (base `en_core_web_sm`). Conjunto de **prueba (34 CVs)**:

| Etiqueta | F1 |
|---|---|
| PERSONA (nombre) | 0,853 |
| CORREO | 0,737 |
| TITULO (título académico) | 0,549 |
| UBICACION | 0,489 |
| PUESTO (cargo) | 0,436 |
| ANIO_EGRESO | 0,429 |
| EMPRESA | 0,392 |
| INSTITUCION | 0,374 |
| HABILIDAD | 0,205 |
| ANIOS_EXPERIENCIA | 0,000 |

**F1 micro global: 0,47.**

### Hallazgo clave sobre HABILIDAD
En el dataset original las habilidades **no** están marcadas una por una, sino como
**bloques enteros** (toda la lista de habilidades junta, por ejemplo
`"EXCEL, HTML, JAVASCRIPT, MS EXCEL, SQL, ..."` como un único fragmento). Por eso:
- el modelo no puede aprender a separar habilidad por habilidad,
- y el F1 de esa clase mide mal la realidad.

La solución práctica es detectar habilidades con el **diccionario curado** (ver §4),
que es justo lo que el producto necesita para el "keyword gap".

---

## 4. Resultado por secciones (lo que usa el producto)

El diagnóstico necesita saber si el CV tiene cada sección. Medido sobre los 34 CVs
de prueba, combinando el modelo de entidades + reglas (email/teléfono) + diccionario:

| Sección | F1 | Precisión | Recall | Aciertos |
|---|---|---|---|---|
| Contacto | 0,985 | 0,971 | 1,000 | 0,971 |
| Experiencia | 0,938 | 0,938 | 0,938 | 0,882 |
| Educación | 0,921 | 0,853 | 1,000 | 0,853 |
| Habilidades | 0,938 | 0,882 | 1,000 | 0,882 |

**F1 macro: 0,945 · F1 micro: 0,946.**

Extracción de habilidades con diccionario: **34/34 CVs** con al menos 1 habilidad,
**920 habilidades** encontradas (**27,1 por CV**, 161 distintas).

---

## 5. Conclusión de la Etapa A

- El sistema **sí** detecta correctamente las 4 secciones (F1 ≈ 0,95).
- El modelo de entidades detallado da F1 ≈ 0,47: es un problema **difícil** con
  pocos datos (220 CVs) y muchas etiquetas finas, corriendo en CPU.
- Perseguir F1 ≥ 0,80 en las 10 etiquetas finas **no es realista** con los datos
  disponibles y el hardware previsto.
- Propuesta: medir el objetivo como **F1 de detección de secciones** (que sí
  supera 0,80 holgadamente) y reportar el F1 de entidades como métrica secundaria.
- Habilidades: usar el diccionario curado (necesario para el keyword gap), no el NER.

---

## Glosario

- **NER**: modelo que marca en el texto *qué es cada cosa* (nombre, empresa, etc.).
- **F1**: número entre 0 y 1 que combina aciertos y errores. 1 es perfecto.
- **F1 micro**: mezcla todas las etiquetas en una sola cuenta (pesa más la que más aparece).
- **F1 macro**: promedia el F1 de cada etiqueta por igual.
- **Baseline (línea base)**: solución simple de referencia con la que se compara el modelo.
- **Gazetteer / diccionario**: buscar habilidades directamente en una lista conocida.
- **Filtración de datos**: cuando un dato de prueba aparece por error en el entrenamiento.
