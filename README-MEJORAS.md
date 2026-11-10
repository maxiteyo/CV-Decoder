# Plan de mejoras del scoring — CV-Decoder

Este documento describe **todas las fases** para que el puntaje del MVP sea más
realista. La idea central es dejar de mezclar dos preguntas distintas:

1. **¿El CV está bien armado para pasar un filtro ATS?**
2. **¿El CV se adecúa a esta oferta en particular?**

Hoy el sistema las mezcla en un único `puntaje_global`. Eso hace que un CV de
docente, perfectamente formateado, saque **47,4** contra una oferta de QA Mobile
aunque no tenga nada que ver.

---

## 0. Diagnóstico del problema actual

La fórmula vigente es:

```text
puntaje_global =
    0,15 × parseabilidad
  + 0,25 × secciones
  + 0,20 × keyword_gap
  + 0,40 × similitud
```

Para el CV de Laura contra la oferta de QA Mobile:

```text
0,15 × 100 + 0,25 × 100 + 0,20 × 8,3 + 0,40 × 14,3 = 47,4
```

El problema no es la similitud: **14,3 es bajo** y la brecha de skills
**8,3 también es baja**. El problema es que **40 puntos salen de “PDF legible +
tiene las cuatro secciones”**, algo que cualquier CV ordenado cumple.

Evidencia con los 50 pares calificados a mano:

| Fórmula | Rango | Spearman vs notas humanas |
|---|---:|---:|
| Actual | 41–65 | 0,61 |
| Compatibilidad 90% similitud + 10% brecha | 2–44 | 0,87 |

Conclusión: el motor léxico detecta bastante bien el desajuste; el agregado lo
esconde.

---

## 1. Principios de diseño

1. **ATS y match son dimensiones separadas.** Un CV puede ser 100 ATS y 10 match.
2. **El ATS no suma al match.** Es un prerrequisito o advertencia, no un
   componente de adecuación.
3. **El match se explica.** Tiene que mostrar requisitos cumplidos, faltantes y
   evidencia, no solo un número.
4. **Primero reglas y evaluación; después modelos más caros.** No se agrega un
   LLM o embeddings sin un set de evaluación que demuestre mejora.
5. **Nada de categorías absolutas sin evidencia.** El sistema no dirá “profesión
   equivocada” salvo que haya una taxonomía de roles que lo respalde. Dirá
   “compatibilidad baja” y mostrará por qué.
6. **Backward compatibility.** `puntaje_global` se conserva como alias de
   `puntaje_match` para no romper la API actual.

---

## 2. Fase 1 — Separar ATS y Match

**Objetivo:** que un CV bien formateado pero de otra área deje de sacar 40–50
puntos. Es la fase de mayor impacto y menor esfuerzo.

### 2.1. Puntaje ATS

Mide la calidad del CV como documento, **sin mirar la oferta**.

Fórmula inicial:

```text
puntaje_ats = 0,50 × parseabilidad + 0,50 × secciones
```

Notas:

- La sección `Contacto` ya está dentro de `secciones`, así que en esta fase no se
  cuenta dos veces.
- En fases posteriores se puede refinar con fechas, estructura, tablas, imágenes
  y formato de archivo.
- Para un PDF legible y completo, el ATS debe dar cerca de **100**.
- Si el PDF no se puede leer, la API ya lo rechaza antes de puntuar.

### 2.2. Puntaje Match

Mide la adecuación al puesto. Fórmula inicial:

```text
puntaje_match = 0,90 × similitud + 0,10 × keyword_gap
```

Notas:

- En esta fase se usan las dimensiones que ya existen.
- La similitud pesa más porque es la señal que mejor ordenó los 50 pares
  humanos.
- La brecha de skills sigue aportando, pero no puede inflar el puntaje.
- En fases posteriores se reemplaza parte de esta fórmula por cobertura de
  requisitos obligatorios, deseables, seniority y similitud por secciones.

### 2.3. Niveles de match

```text
  0–19,9  → bajo
 20–49,9  → medio
 50–74,9  → bueno
 75–100   → muy bueno
```

Estos cortes son provisorios y se recalibran en la Fase 4.

### 2.4. Respuesta de la API

Se agregan campos sin romper los existentes:

```json
{
  "puntaje_global": 13.7,
  "puntaje_ats": 100.0,
  "puntaje_match": 13.7,
  "nivel_match": "bajo",
  "metadatos": {},
  "dimensiones": {}
}
```

- `puntaje_global`: alias de `puntaje_match` por compatibilidad.
- `puntaje_ats`: calidad del CV como documento.
- `puntaje_match`: adecuación a la oferta.
- `nivel_match`: etiqueta cualitativa.

### 2.5. Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `src/core/diagnostico.py` | Nuevas fórmulas y campos de salida. |
| `src/api/schemas.py` | Nuevos campos y ejemplo de respuesta. |
| `src/api/main.py` | Copiar los campos nuevos a la respuesta HTTP. |
| `tests/test_diagnostico.py` | Tests de separación ATS/match y caso Laura. |
| `tests/test_api.py` | Verificar el contrato nuevo. |
| `README.md`, `docs/*` | Explicar la separación y actualizar ejemplos. |

### 2.6. Resultado medido

Implementado en esa fase y verificado con **28 tests en verde**:

| Caso | Match | ATS | Nivel |
|---|---:|---:|---|
| Laura real (docente) vs QA Mobile | 13,7 | 100,0 | bajo |
| CV docente de prueba vs oferta docente | 72,6 | 96,7 | bueno |
| `cv (5).pdf` vs `par_005` | 25,0 | 87,5 | medio |
| 10 pares buenos del benchmark | 24,8–66,1 | 100,0 | medio/bueno |
| 10 pares del banco de calificación | 2,4–22,7 | 100,0 | bajo/medio |

El `par_005` bajó de 35,0 a 25,0 porque el gate de Fase 2 detecta que faltan
requisitos centrales (`.net`, `asp.net`, `database design`, `oop`,
`problem-solving`). Los pares buenos siguen solapando con algunos flojos
(24,8 vs 22,7): eso se ataca en la Fase 3, no cambiando más pesos a mano.

> Estos números son el cierre histórico de Fase 2. La Fase 3 los actualiza:
> Laura y el arquitecto bajan por debajo de 10 y el match usa secciones y
> seniority. Ver la tabla de 4.5.

### 2.7. Criterios de aceptación

- [x] Laura vs QA Mobile: `puntaje_match < 20` y `puntaje_ats >= 80`.
- [x] CV docente de prueba vs oferta docente: `puntaje_match` alto (72,6).
- [x] Par bueno del benchmark: `puntaje_match` claramente mayor que un par
      aleatorio.
- [x] `puntaje_global == puntaje_match`.
- [x] Todos los tests existentes siguen pasando.
- [x] La documentación no menciona una “suma de cuatro dimensiones”.

---

## 3. Fase 2 — Requisitos obligatorios, deseables y sinónimos

**Objetivo:** que el match entienda qué pide realmente la oferta, en vez de
tratar todas las skills por igual.

### 3.1. Parsear la oferta por secciones

Detectar, con encabezados y heurísticas:

- `Responsibilities` / `Responsabilidades`
- `Requirements` / `Requisitos`
- `Nice to have` / `Deseables`
- `Benefits` / `Ofrecemos` (se ignora para el match)

Si la oferta no tiene secciones claras, usar todo el texto como fallback y bajar
la confianza del resultado.

### 3.2. Requisitos obligatorios vs deseables

- Skills de `Requirements`: peso alto.
- Skills de `Nice to have`: peso bajo.
- Skills de `Responsibilities`: se usan para comparar experiencia, no como
  checklist.

### 3.3. Normalización de sinónimos

Crear un mapa explícito y testeado:

```text
QA ↔ Quality Assurance
JS ↔ JavaScript
TS ↔ TypeScript
communication ↔ communication skills
mobile ↔ iOS / Android
CI ↔ continuous integration
```

Además, normalizar frases:

- `communication skills` en la oferta debe matchear `communication` en el CV.
- `software engineer` y `software developer` deberían compartir familia.

### 3.4. Gate por requisitos centrales

Si faltan requisitos obligatorios centrales:

```text
cobertura_obligatorios < 30%  → cap del match en 25
cobertura_obligatorios < 50%  → cap del match en 50
```

El cap evita que la similitud léxica “tape” la ausencia de lo esencial.

### 3.5. Nuevos campos

```json
{
  "requisitos": {
    "obligatorios_cumplidos": ["java", "sql"],
    "obligatorios_faltantes": ["swift", "xcuitest", "espresso"],
    "deseables_cumplidos": ["agile"],
    "deseables_faltantes": ["swift"]
  }
}
```

### 3.6. Resultado medido

Implementado en esa fase con **28 tests en verde** (16 API + 4 parseabilidad + 8 diagnóstico):

| Caso | Resultado |
|---|---|
| Arquitecto (Carlos Rossi) vs QA Mobile | match **19,8** · ATS **100** · nivel **bajo** |
| Requisitos obligatorios faltantes de Carlos | `android`, `ios`, `java`, `espresso`, `xcuitest`, `regression`, `agile` |
| Falsos positivos eliminados | `design` (estaba en Responsibilities) y `healthcare` (Benefits) |
| `QA` vs `Quality Assurance` | matchea como `qa` |
| `communication` vs `communication skills` | matchea como `communication` |
| Gate | cobertura <30% → cap 25; <50% → cap 50 |

En los 10 pares buenos, 3 quedaron topeados por el gate (25 o 50) porque el
diccionario no reconoce todos sus sinónimos. Es una limitación conocida de esta
fase: la Fase 3 compara por secciones y la Fase 4 recalibra los cortes.

### 3.7. Criterios de aceptación

- [x] Laura vs QA Mobile: faltantes incluyen `android`, `ios`, `java`, `swift`,
      `espresso`, `xcuitest`, `regression`.
- [x] Un CV de QA con `QA` en vez de `Quality Assurance` matchea igual.
- [x] Un CV con `communication` matchea `communication skills`.
- [x] El cap se aplica cuando faltan requisitos centrales.

---

## 4. Fase 3 — Match por secciones y seniority

**Objetivo:** comparar las partes correctas del CV con las partes correctas de
la oferta, y considerar experiencia/nivel.

### 4.1. Similitud por secciones

En vez de comparar todo el CV contra toda la oferta:

| CV | Oferta |
|---|---|
| Experiencia | Responsibilities |
| Habilidades | Requirements |
| Educación | Requirements (solo si aplica) |

Fórmula sugerida:

```text
similitud_match =
    0,60 × similitud(experiencia, responsabilidades)
  + 0,40 × similitud(habilidades, requisitos)
```

### 4.2. Seniority y años

Extraer:

- años pedidos en la oferta (`7+ years`, `3+ years`);
- años trabajados en el CV (fechas de experiencia);
- nivel del título (`Junior`, `Senior`, `Lead`, `Staff`).

Regla:

```text
si anos_cv < anos_pedidos → penalización moderada
si anos_cv >= anos_pedidos → sin penalización
si el título es muy superior → no penalizar fuerte
```

**Cuidado:** Laura tiene muchos años de experiencia, pero no en mobile QA. El
seniority nunca debe compensar la falta de skills centrales.

### 4.3. Refinar el ATS

Se agregó una regla conservadora: una lista de habilidades cuenta como sección
solo si hay encabezado o un bloque dedicado con al menos 3 ítems separados y 2
skills del diccionario. Así un CV sin sección “Habilidades” pero con skills
mencionadas dentro de una frase de experiencia no infla el ATS. Contacto
completo, fechas, tablas/columnas y tamaño de archivo quedan para la Fase 4.

### 4.4. Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `src/core/diagnostico.py` | Segmentación del CV, similitud por secciones, años/nivel y ajuste de seniority. |
| `src/api/schemas.py` | `seniority`, `similitud.fuente` y `similitud.detalle`. |
| `src/api/main.py` | Copia `seniority` a la respuesta HTTP. |
| `tests/test_diagnostico.py` | Laura, estudiante junior/senior, déficit de años y CV sin Habilidades. |
| `tests/test_api.py` | Contrato de `seniority` y fórmula con ajuste. |
| `README.md`, `docs/*` | Documentar la Fase 3 y los valores medidos. |

### 4.5. Resultado medido

Implementado con **33 tests en verde** (16 API + 4 parseabilidad + 13 diagnóstico):

| Caso | Resultado |
|---|---|
| Laura (docente) vs QA Mobile | match **0,0** · ATS **96,7** · bajo; cap 25; ajuste 0,943 |
| Arquitecto (Carlos Rossi) vs QA Mobile | match **9,8** · ATS **100** · bajo; cap 25 |
| Estudiante de informática vs junior | match **92,7** · ATS **93,3** · muy bueno |
| Estudiante de informática vs Senior | match **39,9** · ATS **93,3** · medio |
| CV con experiencia relevante sin sección Habilidades | match **75,2** · ATS **77,5** · muy bueno |
| `cv (5).pdf` vs `par_005` | match **25,0** · ATS **87,5** · medio |
| 10 pares buenos del benchmark | **24,8–59,5** (mediana 48,9) |
| 50 pares del banco de calificación | **1,1–43,9** (mediana 14,0) |

La similitud por secciones se usa solo cuando existen Experiencia y Habilidades
en el CV y Responsibilities y Requirements en la oferta; si falta alguna, se
vuelve al texto completo. El ajuste de seniority es moderado (máximo 20% por
años y 20% por nivel), nunca bonifica y se aplica antes del cap. El Spearman del
`puntaje_match` contra las notas humanas quedó en **0,735**; la Fase 4 debe
recalibrar los cortes, no cambiar pesos a ojo.

### 4.6. Criterios de aceptación

- [x] Laura vs QA Mobile: match bajo aunque tenga muchos años.
- [x] Estudiante de informática vs puesto junior: match medio/alto.
- [x] Estudiante de informática vs Senior: match medio, no bajo extremo.
- [x] CV con experiencia relevante pero sin sección “Habilidades”: match alto,
      ATS menor.

---

## 5. Fase 4 — Evaluación y calibración

**Objetivo:** dejar de elegir pesos “a ojo” y demostrar que el sistema mejora.

### 5.1. Set de evaluación

| Caso | Esperado |
|---|---|
| Laura vs docente de biología | Match alto |
| Laura vs QA Mobile Senior | Match bajo, ATS alto |
| Estudiante de informática vs junior IT | Match medio/alto |
| Estudiante de informática vs Senior IT | Match medio |
| 10 pares buenos del benchmark | Match alto |
| 50 pares aleatorios | Match bajo/medio |

### 5.2. Métricas

- Spearman contra notas humanas (orden).
- MAE contra notas humanas (magnitud).
- Distribución de puntajes por categoría.
- Precisión/recall para “bajo”, “medio” y “alto”.
- Tasa de falsos positivos: CV de otra área con match alto.

### 5.3. Tests automáticos de calibración

```text
Laura vs QA Mobile      → match < 20
Laura vs docencia       → match > 60
Par bueno               → match > 50
Par aleatorio           → match < 30
```

Los umbrales se ajustan cuando el set esté calificado a mano.

### 5.4. Criterios de aceptación

- [ ] Spearman ≥ 0,85 sobre los pares con nota humana.
- [ ] Ningún CV de otra área supera 30 de match.
- [ ] Los pares buenos superan 50 de match.
- [ ] La documentación reporta la distribución y las limitaciones.

---

## 6. Fase 5 — Modelo semántico híbrido (opcional)

**Objetivo:** mejorar sinónimos, parafraseo y transferibilidad **solo si la
evaluación demuestra que vale la pena**.

### 6.1. Opciones

- TF-IDF + embeddings multilingües, con peso calibrado.
- Reranking de los mejores candidatos con un cross-encoder.
- Modelo local de embeddings específico para CV/ofertas.

### 6.2. Condiciones

- No reemplazar TF-IDF sin comparar contra el set de evaluación.
- Medir latencia y tamaño del modelo.
- Mantener explicabilidad: el usuario tiene que ver qué requisitos matchean.
- Si no mejora el Spearman/MAE, no se implementa.

### 6.3. Criterios de aceptación

- [ ] Mejora medible sobre Fase 4.
- [ ] Tiempo de respuesta aceptable para el MVP.
- [ ] El ATS y el match siguen separados.

---

## 7. Orden de implementación

| Fase | Impacto | Esfuerzo | Prioridad |
|---|---|---|---|
| 1. Separar ATS y match | Alto | Bajo | **Ahora** |
| 2. Requisitos y sinónimos | Alto | Medio | Después |
| 3. Secciones y seniority | Medio | Medio/alto | Después |
| 4. Evaluación y calibración | Alto | Medio | Transversal |
| 5. Modelo semántico | Medio | Alto | Opcional |

La Fase 4 no es solo una etapa final: se arma en paralelo desde la Fase 1 para
poder comparar.

---

## 8. Qué NO se va a hacer

- No se va a decir “la profesión del CV es incorrecta” sin una taxonomía de
  roles que lo respalde.
- No se va a usar un LLM como caja negra para el puntaje final.
- No se va a agregar OCR en esta iteración.
- No se va a mezclar ATS y match en una suma ponderada.
- No se van a elegir pesos nuevos sin tests de calibración.

---

## 9. Estado

- [x] Diagnóstico del problema actual.
- [x] Fase 1.
- [x] Fase 2.
- [x] Fase 3.
- [ ] Fase 4.
- [ ] Fase 5 (opcional).

Este documento se actualiza a medida que cada fase se implementa y se valida.
