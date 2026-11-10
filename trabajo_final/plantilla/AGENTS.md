# Instrucciones para el agente

Este repositorio es el **trabajo final** de una materia de Inteligencia Artificial. Tu tarea es ayudar a la persona que lo está armando a dejarlo con la estructura y el `README.md` completos, siguiendo esta plantilla al pie de la letra — no a inventar una estructura propia.

No toques nada todavía: primero hacé las preguntas de la sección siguiente.

## 1. Preguntas antes de empezar

Si todavía no lo sabés por el contexto de la conversación, preguntale a la persona:

1. **¿De qué trata el proyecto?** Problema que resuelve, en una frase.
2. **¿Qué dataset usa?** Fuente, tamaño aproximado, si es público o propio, si es pesado (>unos pocos MB) o contiene datos sensibles/privados.
3. **¿Qué tipo de modelo(s)?** (clasificación, regresión, clustering, deep learning, NLP, visión, etc.)
4. **¿Es individual o en grupo?** Nombres y, si los tiene, links de GitHub/LinkedIn de cada integrante.
5. **¿Contexto académico?** Materia, institución, cohorte, docente.
6. **¿Ya tiene código escrito** (notebooks sueltos, scripts) **o arrancan de cero?**
7. **¿Qué tipo de demo quieren?** Por defecto es una página estática (GitHub Pages, carpeta `docs/`). Si además quieren algo interactivo (Streamlit/Gradio corriendo el modelo), confirmalo — no es parte de esta plantilla por defecto.

No asumas respuestas a estas preguntas. Si el código que ya existe sugiere algo (por ejemplo, ya hay un dataset de audio), confirmá tu suposición en vez de decidir por tu cuenta.

## 2. Qué hacer con la estructura de carpetas

- Movés/organizás el código existente (si lo hay) dentro de `src/` y `notebooks/`, **sin reescribir lo que ya funciona** — solo reordenar, no refactorizar código que no te pidieron tocar.
- Si una carpeta de la plantilla no aplica al proyecto (por ejemplo, no hay `tests/`), dejala igual pero vacía, o quitala si la persona prefiere — nunca la borres sin preguntar.
- `data/raw/` y `models/` son para archivos que probablemente **no deban subirse al repo** si son pesados o privados. Si el dataset pesa poco (unos pocos MB) y no es sensible, se puede versionar sin problema. Agregá las entradas correspondientes a `.gitignore` según lo que decidan.
- No subas ni commitees datasets con información personal/sensible bajo ninguna circunstancia, aunque te lo pidan — documentá en el README cómo conseguir/regenerar esos datos en su lugar.

## 3. Qué hacer con `README.md`

- Partís del `README.md` de esta plantilla (ya está en la raíz del repo si copiaron la plantilla completa).
- Completás **cada** placeholder entre `[corchetes]` con información real, basada en lo que te contó la persona o en lo que encuentres en el código.
- Borrás **todas** las líneas que empiezan con `> 📝` (son guía para humanos, no para el README final).
- Si una sección no aplica (ej. no hay roadmap), no la borres — escribí una frase corta explicando por qué no aplica, en vez de dejarla vacía o eliminarla. Un README incompleto sin explicación se nota.
- No inventes resultados, métricas, ni capturas. Si todavía no hay resultados porque el modelo no está entrenado, dejá la sección con un placeholder explícito (`[pendiente de completar una vez entrenado el modelo]`), no inventes números.
- Los badges de la cabecera (versión de Python, licencia) ajustalos a lo que realmente usa el proyecto — no los dejes genéricos si, por ejemplo, usan Python 3.12 en vez de 3.11.

## 4. Qué hacer con `pyproject.toml`

- Agregá las dependencias reales del proyecto (lo que se importa en el código) — no dejes las de ejemplo si no se usan, y no te olvides de las que sí hacen falta.
- Si usan `uv`, el flujo es `uv venv --python 3.11` (o la versión que corresponda) seguido de `uv pip install -e .` — mismo flujo que se usó durante toda la cursada.

## 5. Qué hacer con `docs/index.html`

- Es una página estática simple, pensada para publicarse con GitHub Pages — sin backend, sin build step.
- Completá el título, el pitch de una línea, y agregá capturas/gráficos reales en `docs/img/` (no dejes las rutas de ejemplo apuntando a archivos que no existen).
- Si el proyecto tiene un GIF o video de demo, embebelo ahí también.
- No agregues frameworks de JS ni un build step (React, Vite, etc.) salvo que te lo pidan explícitamente — el objetivo es que funcione con solo subir el HTML.

## 6. Verificación final

Antes de darlo por terminado, revisá:

- [ ] No queda ningún `[placeholder entre corchetes]` sin completar.
- [ ] No queda ninguna línea `> 📝` de guía.
- [ ] Todos los links relativos del README apuntan a archivos que existen de verdad.
- [ ] Las imágenes referenciadas en `docs/img/` existen.
- [ ] `uv pip install -e .` (o el gestor de dependencias que corresponda) instala sin errores.
- [ ] El código corre de punta a punta siguiendo los pasos que vos mismo escribiste en la sección "Instalación"/"Uso" del README — si escribiste un comando, probalo.
