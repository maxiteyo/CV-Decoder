# Trabajo final

## Qué es esto

El trabajo final se entrega como un **repositorio propio** (no una carpeta dentro de este repo de la materia). Acá encontrás:

- La consigna y los criterios de evaluación (este archivo).
- [`plantilla/`](plantilla/) — la estructura de carpetas y el `README.md` que **todos** los proyectos deben usar como punto de partida.

## Consigna

El trabajo final consiste en desarrollar un proyecto de Inteligencia Artificial aplicado a un problema real, a elección, que recorra el ciclo completo: desde el planteo del problema y los datos (o el estado inicial, si se trata de un proyecto de búsqueda u optimización en lugar de uno basado en datos) hasta una solución evaluada y una demo funcionando.

Puede resolverse de forma individual o en grupos de hasta 3 personas. No alcanza con reutilizar sin cambios sustanciales un ejercicio visto en clase: el proyecto tiene que aportar algo propio, ya sea en el problema elegido, en los datos o en el enfoque de la solución.

### Requisitos mínimos

- [ ] Repositorio propio en GitHub. Se recomienda que sea público (así funciona como pieza de portfolio), salvo que el tema involucre datos sensibles o restricciones de uso — en ese caso puede mantenerse privado, agregando al cuerpo docente como colaborador.
- [ ] Código funcional, ejecutable siguiendo las instrucciones del propio README del proyecto.
- [ ] `README.md` que siga la [plantilla](plantilla/README.md) (ver más abajo).
- [ ] Al menos una notebook o script que muestre el flujo completo del proyecto (por ejemplo, para un enfoque de datos: carga → procesamiento → modelo → evaluación).
- [ ] Demo o interfaz de presentación (ver sección siguiente).
- [ ] Dataset propio o público citando la fuente; si es público, debe estar debidamente referenciado en el README.
- [ ] Al menos una métrica cuantitativa que permita evaluar objetivamente el resultado obtenido (no alcanza con una descripción cualitativa de "funcionó").

### Demo / interfaz de presentación

El proyecto tiene que poder **mostrarse** sin que quien lo evalúa tenga que leer código. La forma recomendada es una **página estática publicada con GitHub Pages**, usando la carpeta `docs/` que ya trae la plantilla:

1. Completá `plantilla/docs/index.html` con el pitch del proyecto, capturas/gráficos de resultados y los links al repo y al informe.
2. En GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / carpeta `/docs`**.
3. La página queda publicada en `https://<usuario>.github.io/<repositorio>/`.

No hace falta backend ni servidor: es HTML/CSS estático, pensado para mostrarse como pieza de portfolio. Si el proyecto necesita una demo *interactiva* (por ejemplo, correr el modelo con una imagen nueva), documentá en el README cómo levantarla localmente (Streamlit, Gradio, un notebook, etc.) — GitHub Pages no puede correr backend/Python.

### Instancias de entrega

La nota final es **acumulativa** y se compone de tres instancias:

| Instancia | Qué se entrega | Peso en la nota final |
|---|---|---|
| **MVP** | Una primera versión en la que el modelo central funciona, procesa datos reales y devuelve un resultado útil. Recibe una devolución con puntos a mejorar. | 30% |
| **Trabajo final** | La versión completa del proyecto: las mejoras que se marcaron en la devolución del MVP y las features nuevas que decidas incorporar. Se evalúa lo incorporado desde el MVP. | 50% |
| **Defensa oral** | Exposición de 10 a 15 minutos en la que se presenta el proyecto y se responden preguntas sobre las decisiones tomadas. | 20% |

La entrega se hace enviando el link del repositorio por el canal oficial de la materia, antes de la fecha límite anunciada en el cronograma de la cursada. La nota que recibas tras el MVP es provisoria: la nota final se calcula recién cuando están las tres instancias.

## Criterios de evaluación

### MVP y trabajo final

Ambas instancias se evalúan con los mismos seis ítems. Las ponderaciones son relativas entre sí (suman 100% dentro de cada instancia).

| Ítem | Qué se evalúa | Ponderación |
|---|---|---|
| Problema y datos | Claridad del problema planteado, justificación de la elección del dataset, calidad del EDA | 15% |
| Metodología | Preprocesamiento aplicado, elección y justificación del/los modelo(s), validez del enfoque | 20% |
| Resultados | Métricas apropiadas al tipo de problema, comparación contra una línea de base, análisis crítico de lo obtenido (no alcanza con "funcionó") | 20% |
| Código | Organización del repositorio, reproducibilidad (`pyproject.toml` funcional end-to-end), legibilidad | 15% |
| README | Completo según la plantilla, profesional, sin secciones vacías ni placeholders sin completar | 10% |
| Demo | Funcional y que muestre el proyecto sin necesidad de leer código. En el MVP alcanza con una inferencia ejecutable; en el trabajo final se espera una demo publicada | 10% |

*(Las ponderaciones de esta tabla suman 90; se normalizan al calcular la nota de cada instancia.)*

### Defensa oral

| Criterio | Qué se evalúa | Ponderación |
|---|---|---|
| Claridad de la exposición | Estructura, lenguaje y orden al presentar el problema, el enfoque y los resultados | 25% |
| Dominio técnico y decisiones | Capacidad de justificar las decisiones tomadas y de explicar el funcionamiento del modelo | 30% |
| Respuesta a preguntas | Precisión y honestidad al responder, incluidas las limitaciones del trabajo | 25% |
| Tiempo y material de apoyo | Ajuste al tiempo asignado y calidad del material usado | 10% |
| Aporte individual | En trabajos grupales, participación y dominio de cada integrante (se califica por separado) | 10% |

### Niveles de desempeño

Para cada ítem de la tabla, una referencia de qué distingue un nivel del otro:

- **Insuficiente** — el ítem falta, está incompleto, o no se puede verificar (ej.: el código no corre, el README tiene secciones vacías).
- **Aceptable** — cumple lo mínimo pedido, pero sin profundidad: decisiones no justificadas, análisis superficial, demo que funciona pero no comunica bien el proyecto.
- **Bueno** — cumple lo pedido con justificación clara de las decisiones tomadas y un análisis crítico real de los resultados (no solo reportar números).
- **Sobresaliente** — además de lo anterior, hay algo que excede lo mínimo exigido: comparación entre enfoques, atención a casos límite, una demo particularmente cuidada, etc.

## Cómo usar la plantilla

1. Creá un repositorio nuevo y vacío en GitHub (fuera de este repo de la materia).
2. Copiá el contenido de [`plantilla/`](plantilla/) a ese repositorio nuevo.
3. Completá [`plantilla/README.md`](plantilla/README.md) — es la plantilla obligatoria para todos los proyectos, ver el detalle de cada sección ahí mismo.
4. (Opcional, recomendado) Si vas a usar un asistente de IA (Claude Code, GitHub Copilot, Cursor, etc.) para ayudarte a armar el esqueleto del proyecto, decile que lea [`plantilla/AGENTS.md`](plantilla/AGENTS.md) antes de tocar nada — tiene las instrucciones de cómo adaptar la estructura a tu proyecto puntual.

## Estructura de la plantilla

```text
plantilla/
├── README.md              ← plantilla de README profesional (obligatoria)
├── AGENTS.md               ← instrucciones para que un agente de IA arme el esqueleto
├── pyproject.toml          ← dependencias (mismo flujo con uv que usamos toda la cursada)
├── .gitignore
├── LICENSE
├── src/                     ← código fuente (funciones, módulos propios)
├── notebooks/               ← notebooks de exploración/experimentación
├── data/
│   ├── raw/                 ← datos sin procesar (no versionar si son pesados/privados)
│   └── processed/           ← datos ya procesados, listos para el modelo
├── models/                  ← modelos entrenados (no versionar los pesados)
├── tests/                   ← tests, si corresponde
└── docs/                    ← demo estática para GitHub Pages
    ├── index.html
    ├── img/                  ← capturas/gráficos para el README y la demo
    └── assets/               ← css/js de la demo, si hace falta
```
