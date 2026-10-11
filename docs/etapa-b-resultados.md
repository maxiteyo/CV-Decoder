# Etapa B — Resultados parciales (parseabilidad + similitud)

Fecha: 2026-10-11 · Semilla: **42**

---

## 1. Parseabilidad (dimensión 1) — COMPLETADA (con datos sintéticos)

**Qué se hizo:** un lector de PDFs (`src/parsing/`) que extrae el texto y decide
si es utilizable. Se midió con un conjunto de control de 60 PDFs generados a
partir de 20 CVs reales del dataset, en 3 maquetas:

| Maqueta | Descripción | ¿Debería leerse? |
|---|---|---|
| `simple` | Una columna | Sí |
| `columnas` | Dos columnas | Sí |
| `escaneado` | Texto como imagen (sin capa de texto) | **No** |

**Resultado:**

| Métrica | Valor |
|---|---|
| Decisiones correctas | **60/60 (100%)** |
| PDFs legibles recuperados | **40/40** (cobertura de palabras ≈ 1,000) |
| PDFs escaneados detectados | **20/20** (cobertura 0,000) |

**Cumple** el objetivo de parseabilidad ≥ 90% y, además, **detecta correctamente**
los PDFs no legibles (que un ATS descartaría).

> **Pendiente importante:** faltan PDFs **reales** de candidatos (no sintéticos).
> Los sintéticos validan que el lector funciona, pero no capturan toda la
> variedad del mundo real (fuentes raras, tablas, fotos, firmas).

Script: `scripts/build_test_pdfs.py` + `scripts/eval_parseability.py`.

---

## 2. Similitud semántica (dimensión 4) — MOTORES LISTOS, falta calibración

**Qué se hizo:** un módulo con **dos motores** (`src/models/similarity.py`):
- `tfidf`: línea base clásica (cuenta palabras). Sin descargas, rapidísima.
- `embeddings`: modelo de lenguaje multilingüe `paraphrase-multilingual-mpnet-base-v2`
  (entiende sinónimos y frases en español/inglés/spanglish). **Probado y funcionando.**

**Motor unificado:** `src/core/diagnostico.py` combina las 4 dimensiones y devuelve
un JSON. Demo: `.venv/bin/python scripts/demo_diagnostico.py --motor embeddings`.

Ejemplo real (par_005, oferta "Dotnet Developer"): puntaje global 53,4 con
similitud 33,5 (embeddings) contra 5,2 (tfidf) — los embeddings captan mejor el
parecido aunque no coincidan las palabras exactas.

**Tiempo de inferencia (en caliente): 0,80 s** por CV+oferta → **cumple < 3 s**.
(La primera vez tarda ~2 min por la descarga del modelo, que luego queda en caché.)

**Medición (Spearman ≥ 0,75):** requiere **notas humanas**. Se generó la planilla
`data/benchmarks/pares_para_calificar.csv` con **50 pares (CV + oferta)**.
Los dos integrantes deben completar la columna `puntaje_humano` (0 a 100).

Pasos:
1. Abrir `data/benchmarks/pares_para_calificar.csv`.
2. En cada fila, poner en `puntaje_humano` cuánto encaja ese CV con esa oferta.
3. Correr `.venv/bin/python scripts/eval_similarity.py --motor embeddings`.
4. El script calcula la correlación de Spearman contra las notas humanas.

Script: `scripts/build_rating_pairs.py` + `scripts/eval_similarity.py`.

---

## 3. Pendientes de la Etapa B

- [ ] Conseguir **PDFs reales** de CVs (30–50) y repetir la medición de parseabilidad.
- [ ] Completar las **notas humanas** de los 50 pares y calcular Spearman.
- [ ] Confirmar que los embeddings multilingües entran en < 3 s por CV en CPU.

---

## Glosario

- **Parseabilidad**: si se puede sacar texto usable de un PDF.
- **PDF escaneado**: una foto del CV; no tiene texto adentro, hay que usar OCR.
- **Embeddings**: convertir texto en números que representan su significado.
- **Spearman**: número entre -1 y 1 que dice si dos ordenamientos coinciden.
