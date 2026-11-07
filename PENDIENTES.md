# Estado y pendientes (Sofía)

Fecha: 2026-11-06 · Semilla: 42 · Checklist para no perder el hilo entre el
equipo (Maxi), lo reproducido en esta máquina y lo que falta.

---

## 1. Datos del equipo (todos recibidos)

- [x] **`labels.csv`** → en `data/benchmarks/pdfs_reales/labels.csv`.
  Trae los 221 con nombres `cv (1).pdf`, `cv (10).pdf`… → son descargas
  manuales, **NO están en mis datasets**.
- [x] **`pares_para_calificar.csv` con `puntaje_humano`** (50/50 cargados) →
  en `data/benchmarks/pares_para_calificar.csv`.
- [x] **Zip de los 221 PDFs** → extraído en `data/benchmarks/pdfs_reales/`
  (221/221 coinciden con `labels.csv`).
- [x] **Paquete `datos_para_maxi/`** (2,0 GB) + `verificar.py` → `TODO OK`.

Métricas de la bitácora §3 — **todas reproducidas**:

| Métrica | Bitácora | Acá |
|---|---|---|
| Parseabilidad reales (210 únicos) | 100% | ✅ sin errores de decisión |
| Texto: páginas vacías / palabras pegadas | 7,5% / 3,2% | ✅ 7,5% / 3,2% |
| Tiempo por PDF | ~0,5 s | ✅ lectura 0,48 s + NLP 0,07 s |
| Spearman TF-IDF | 0,9521 [0,899–0,974] | ✅ 0,9521 con techo 0,16 |
| F1 secciones macro / micro | 0,9532 / 0,9538 | ✅ idéntico |
| NER F1 micro | 0,47 | ✅ **0,4679** (Python 3.12.3) |
| CVs con las 4 secciones (informativo) | 59,9% (112/187) | ✅ **59,9%** |
| Techo TF-IDF (opcional) | 0,16 | ✅ máximo de 10 pares: 0,1174 |

---

## 2. Lo que ya está

| Paso | Resultado |
|---|---|
| `git fetch origin` | ✅ aparecieron los 3 commits de Etapa C de Maxi (`2bcdb5c`, `da5a514`, `f73dff6`) |
| API oficial | ✅ la de Maxi (`src/api/main.py`): `/api/v1/analyze-cv`, `/health`, `/`, Swagger, 5 MB, errores con `codigo/mensaje/sugerencia` |
| Implementación duplicada | ⚠️ descartada; quedó en `respaldo-etapa-c-sofia` + stash `etapa-c-sofia-antes-de-integrar` |
| Rama de integración | ✅ `etapa-c-integrada`, creada desde `origin/main` (`f73dff6`) |
| Opcional — 10 pares buenos | ✅ `scripts/build_ceiling_pairs.py`; máximo coseno **0,1174** → techo **0,16** |
| `TECHO_TFIDF` | ✅ `0.16` en `src/models/similarity.py` |
| Tests | ✅ 16 de API (Maxi) + 4 de parseabilidad + 2 de diagnóstico = **22** |
| `requirements.txt` | ✅ fix `httpx2==2.16.0` → `2.14.0` + `httpx==0.28.1`; nota de Python 3.12 |
| `.gitignore` | ✅ se volvió a ignorar `datos_para_maxi/` y `.zip` |
| Docs | ✅ `README`, `docs/bitacora-proyecto.md`, `docs/etapa-b-resultados.md`, `docs/etapa-c-api.md`, `docs/guia-de-uso.md` con techo 0,16, Spearman 0,9521 y `--schema fine` |
| Handoff | ✅ `README-MAXI.md` reescrito para la API oficial de Maxi |

> Ojo con el entrenamiento: el default de `train_ner.py` es `--schema coarse`
> (6 etiquetas), pero `diagnostico.py` y las métricas usan el esquema **fine**
> (10 etiquetas). Siempre pasar `--schema fine --sources dataturks`.

---

## 3. Qué queda hacer (en orden de prioridad)

1. [ ] **Calificar a mano los 10 pares buenos** de
   `data/benchmarks/pares_buenos.csv` (`puntaje_humano`, 0 a 100). Si un par no
   es del mismo oficio, borrarlo/aclararlo y volver a correr el script.
2. [ ] **Commitear y pushear** la rama `etapa-c-integrada`.
3. [ ] Decidir qué hacer con la `main` local: está en `8979aa5` (1 adelante y 3
   atrás de `origin/main`). Ese commit tiene los scripts de datos y
   `docs/metodologia-datos.md`; si se quieren conservar, hay que rebasear o
   cherry-pickear sobre `origin/main`.
4. [ ] Decidir si se conserva `respaldo-etapa-c-sofia` / el stash o se borran.
5. [ ] **Landing en github.io** (10% de la rúbrica): arquitectura de IA + demo.
6. [ ] **Directorio `/notebooks`** — lo pide el lineamiento §2.1 y no existe.
7. [ ] Decidir si `pares_buenos.csv` se versiona o queda local (hoy `data/` está
   ignorado).
8. [ ] Revisar que la guía de Maxi use `--schema fine` (ya corregido acá) y
   `httpx2==2.14.0` (ya corregido en `requirements.txt`).

> **Reproducción exacta**: con Python 3.12.3 y los pins del equipo, TODAS las
> métricas de la bitácora coinciden (0,47 · 0,9532 · 0,9521 · 59,9% · 100%).
> El techo TF-IDF quedó en 0,16 tras validar 10 pares nuevos del mismo oficio.
