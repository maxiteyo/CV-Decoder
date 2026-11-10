# CV-Decoder — Nota de integración para Maxi

> **Base:** `origin/main` (`f73dff6`, tu Etapa C).  
> **Ramas locales:** `main` y `etapa-c-integrada`, con commits de datos, integración y docs sobre `origin/main` (sin push).
> **Fecha:** 2026-11-06 · **Python verificado:** 3.12.3.

**Resumen:** tu API (`src/api/main.py`, Swagger, 16 pruebas) es la oficial. Sofía
había hecho una implementación paralela porque el `origin/main` local estaba
viejo; esa versión quedó descartada. Sobre tu base se portó **solo lo que no
estaba**: la validación del techo TF-IDF, los 10 pares nuevos y algunos fixes.

---

## 1. Qué había pasado

Al hacer `git fetch` aparecieron tus commits:

| Commit | Contenido |
|---|---|
| `2bcdb5c` | Etapa C: API REST con `POST /api/v1/analyze-cv` |
| `da5a514` | Documentación de la Etapa C |
| `f73dff6` | Guía de uso y reproducción desde cero |

La rama local `etapa-c-api` había salido de `8979aa5` (un commit de Sofía que no
estaba en `origin/main`), así que no incluía tu API. Se creó otra API en paralelo
sin saber que ya existía. Esa implementación duplicada quedó guardada en:

- Rama `respaldo-etapa-c-sofia` (base `8979aa5`, sin los cambios sin commitear).
- Stash `etapa-c-sofia-antes-de-integrar` (incluye los archivos sin commitear).

La rama de trabajo nueva es **`etapa-c-integrada`**, creada desde `origin/main`.
Después se integraron las fases 1–4 del scoring, que sí tocan `diagnostico.py`,
`schemas.py` y los tests.

---

## 2. Cambios agregados sobre tu Etapa C

| Archivo | Cambio |
|---|---|
| `src/models/similarity.py` | `TECHO_TFIDF` pasó de **0,10 a 0,16** con la justificación. |
| `scripts/build_ceiling_pairs.py` | Nuevo: arma 10 pares CV↔oferta del mismo oficio y valida el techo. |
| `tests/test_quality.py` | Nuevo: 4 pruebas de parseabilidad (no necesitan el modelo). |
| `tests/test_diagnostico.py` | Nuevo: 2 pruebas del motor de 4 dimensiones. |
| `requirements.txt` | Fix: `httpx2==2.16.0` no existe → `httpx2==2.14.0` + `httpx==0.28.1`. |
| `.gitignore` | Se volvió a ignorar `datos_para_maxi/` y `datos_para_maxi.zip` (~2 GB). |
| `README.md`, `docs/*` | Techo 0,16, Spearman 0,9521, `--schema fine` y conteo real de pruebas. |

### Por qué el techo pasó a 0,16

Los 1.225 pares aleatorios tenían coseno máximo **0,0722**, por eso el techo
original era 0,10 (38% de margen). Pero en los **10 pares nuevos del mismo
oficio** el máximo fue **0,1174**:

- Con techo 0,10, el mejor par bueno saturaba en 100 y se perdía información.
- Con techo **0,16** (36% de margen, mismo criterio):
  - el máximo aleatorio (0,0722) queda en **45,1/100**;
  - el mejor par bueno (0,1174) queda en **73,4/100**.
- El Spearman de los 50 pares pasa de 0,9523 a **0,9521** solo por el redondeo
  a 1 decimal; el orden no cambia.

Los 10 pares quedan en `data/benchmarks/pares_buenos.csv` con `puntaje_humano`
**vacío**: hay que revisarlos y calificarlos a mano. El reporte automático está
en `models/techo_pares_buenos.json` (ambos ignorados por Git).

---

## 3. Qué tenés que hacer

### 3.1 Traer e instalar

La instalación desde cero ya está completa en **`docs/guia-de-uso.md`**. En
resumen: Python **3.12.3**, torch CPU, `pip install -r requirements.txt`,
`python -m spacy download en_core_web_sm` y los datos (`datos_para_maxi` +
benchmarks del equipo).

```bash
git fetch origin
git switch etapa-c-integrada      # cuando Sofía la pushee
python --version                  # 3.12.x
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

El fix de `httpx2` es importante: la versión `2.16.0` **no existe en PyPI** y
hacía fallar la instalación limpia.

### 3.2 Modelo NER

Si no tenés `models/ner_dataturks_sm/`, copialo o entrenalo:

```bash
python scripts/build_ner_dataset.py
python scripts/train_ner.py --sources dataturks --schema fine --output ner_dataturks_sm
```

`--schema fine` es obligatorio: el default de `train_ner.py` es `coarse` (6
etiquetas) y el motor de diagnóstico usa el esquema fino (10 etiquetas).

### 3.3 Verificar

```bash
python -m pytest -q
# esperado: 35 passed (16 de API + 4 de parseabilidad + 15 de diagnóstico)

uvicorn src.api.main:app --reload
# Swagger: http://127.0.0.1:8000/docs
# Salud:   http://127.0.0.1:8000/health
```

### 3.4 Reproducir el techo (opcional)

```bash
python scripts/build_ceiling_pairs.py
# 10 pares, máximo coseno 0,1174, techo sugerido 0,16
```

### 3.5 Calificar los 10 pares

Abrir `data/benchmarks/pares_buenos.csv`, leer cada par y completar
`puntaje_humano` (0 a 100). Si un par no es del mismo oficio, borrarlo o
aclararlo en `comentario`. Con esas notas se puede volver a validar la escala.

---

## 4. Estado de Git

- Ramas actuales: **`main` y `etapa-c-integrada`**, ambas en el mismo commit.
- Historia lineal sobre tu Etapa C: `origin/main` (`f73dff6`) → `05f7b4e`
  (scripts de datos de Sofía, rebaseados) → `40a0ae8` (integración + techo) →
  commit de docs con el estado final.
- **Sin push todavía**: los commits están sólo en la máquina de Sofía.
- El `main` viejo (`8979aa5`) quedó en `respaldo-etapa-c-sofia`,
  `etapa-c-api` y en el stash; el commit previo al rebase quedó en
  `respaldo-etapa-c-integrada-pre-rebase` (`42f428e`).
- No se tocaron tus archivos de API ni tus 16 pruebas.

**Pendiente:** push de la rama, calificación humana de los 10 pares y decidir si
`pares_buenos.csv` se versiona (hoy `data/` está ignorado).
