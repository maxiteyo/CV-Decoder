<!--
PLANTILLA DE README — TRABAJO FINAL

Cómo usar este archivo:
1. Reemplazá cada [placeholder entre corchetes] por el contenido real de tu proyecto.
2. Las líneas que empiezan con "> 📝" son guía para vos: decime qué va en esa sección.
   Borralas todas antes de entregar — no deben quedar en la versión final.
3. No borres secciones porque "no tenés nada que poner": si una sección no aplica
   a tu proyecto, dejala igual y escribí una línea explicando por qué no aplica.
   Un README con huecos sin explicar se lee como que faltó terminarlo.
4. Las imágenes van en docs/img/ y se referencian con rutas relativas, ej:
   ![Demo](docs/img/demo.gif)
-->

<div align="center">

# [Nombre del Proyecto]

### [Una frase de una línea que resuma qué hace el proyecto y para quién]

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-en%20desarrollo-orange.svg)]()

[Demo en vivo](https://TU-USUARIO.github.io/TU-REPOSITORIO/) · [Reportar un bug](../../issues) · [Pedir una funcionalidad](../../issues)

</div>

> 📝 El banner/logo es opcional. Los badges sí son muy recomendados: dan una idea
> inmediata del estado del proyecto. En [shields.io](https://shields.io/) podés generar
> los tuyos (versión de Python, licencia, estado del build, cobertura de tests, etc.).
> No inventes badges que no sean ciertos (ej. no pongas "tests: passing" si no hay tests).

---

## 📋 Tabla de contenidos

- [Demo](#-demo)
- [Sobre el proyecto](#-sobre-el-proyecto)
  - [Contexto académico](#contexto-académico)
  - [Construido con](#construido-con)
- [El dataset](#-el-dataset)
- [Metodología](#-metodología)
- [Resultados](#-resultados)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Roadmap](#-roadmap)
- [Autores](#-autores)
- [Licencia](#-licencia)
- [Agradecimientos y referencias](#-agradecimientos-y-referencias)

> 📝 Si tu README termina quedando corto (todo en una pantalla), podés borrar esta tabla de contenidos.
> Si es largo (como este), dejala — es lo primero que lee alguien para saber si le interesa seguir.

---

## 🎬 Demo

> 📝 Esta sección va **antes** de explicar nada técnico. Quien entra al repo por primera
> vez tiene que poder ver en 10 segundos qué hace el proyecto, sin leer una palabra.
> Poné como mínimo una de estas dos cosas (idealmente ambas):
> - Un GIF o captura del proyecto funcionando.
> - El link a la demo publicada (ver la sección "Demo / interfaz de presentación"
>   del [README del trabajo final](../README.md)).
>
> Para grabar un GIF rápido: [ScreenToGif](https://www.screentogif.com/) (Windows),
> [Kap](https://getkap.co/) (Mac) o `peek` (Linux).

![Demo del proyecto](docs/img/demo.gif)

**🔗 Demo en vivo:** https://TU-USUARIO.github.io/TU-REPOSITORIO/

---

## 📖 Sobre el proyecto

> 📝 2 a 4 párrafos. Respondé, en este orden: ¿qué problema resuelve el proyecto?
> ¿por qué es un problema que vale la pena resolver (o interesante de explorar)?
> ¿qué enfoque elegiste? ¿cuál es el resultado principal, en una frase?
> Escribilo para alguien que no cursó la materia — nada de dar por sentado jerga del curso.

[Descripción del proyecto en 2 a 4 párrafos.]

### Contexto académico

> 📝 Completá con los datos reales. Esto le da marco al proyecto para quien lo lee
> desde afuera (por ejemplo, un reclutador mirando tu portfolio).

- **Asignatura:** [Nombre de la materia]
- **Institución:** [Nombre de la institución]
- **Cohorte / año:** [Año]
- **Docente:** [Nombre del/la docente]

### Construido con

> 📝 Lista corta de las librerías/frameworks principales, no de *todas* las dependencias
> (esas ya están en `pyproject.toml`). Pensalo como las 4-8 piezas que alguien necesita
> conocer para entender de qué está hecho el proyecto.

- [Python 3.11+](https://www.python.org/)
- [pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/)
- [scikit-learn](https://scikit-learn.org/) [u otra librería de modelado]
- [matplotlib](https://matplotlib.org/) / [seaborn](https://seaborn.pydata.org/)
- [uv](https://docs.astral.sh/uv/) — gestión de dependencias y entorno

---

## 📊 El dataset

> 📝 Completá:
> - **Fuente:** de dónde salió el dataset (link si es público; si es propio, cómo lo recolectaste).
> - **Tamaño:** cantidad de registros/filas, columnas, peso en disco.
> - **Variables:** las más relevantes, en una lista o tabla corta (no listes las 40 columnas si no aportan).
> - **Licencia/uso:** si el dataset tiene restricciones de uso o redistribución, decilo acá.
> - Si el dataset es pesado o privado, **no lo subas al repo** — documentá acá cómo conseguirlo
>   o regenerarlo (script de descarga, link, etc.) y agregalo a `.gitignore`.

| Campo | Detalle |
|---|---|
| Fuente | [link o descripción] |
| Registros | [cantidad] |
| Variables | [cantidad] |
| Variable objetivo | [nombre y qué representa] |
| Período / cobertura | [si aplica] |
| Licencia del dataset | [si aplica] |

---

## 🔬 Metodología

> 📝 Explicá el "cómo" del proyecto, a alto nivel — el detalle fino va en el código/notebooks,
> acá va el resumen que le permite a alguien entender las decisiones sin leer una línea de código.
> Como mínimo cubrí:
> - **Análisis exploratorio (EDA):** qué encontraste en los datos (distribución, faltantes,
>   outliers, correlaciones relevantes) y qué decisiones tomaste a partir de eso.
> - **Preprocesamiento:** limpieza, imputación, codificación, normalización/estandarización,
>   balanceo de clases, etc. — lo que hayas aplicado.
> - **Modelo(s):** qué algoritmo(s) probaste y **por qué** (no solo cuál usaste al final).
>   Si compararon varios, una tabla rápida ayuda mucho acá.
> - **Validación:** cómo separaste train/test (o hiciste cross-validation), y por qué así.
>
> Un diagrama simple (aunque sea un dibujo escaneado o hecho en draw.io) vale más que
> tres párrafos para explicar el flujo del pipeline.

![Diagrama del pipeline](docs/img/pipeline.png)

### Análisis exploratorio

[Resumen de los hallazgos principales del EDA.]

### Preprocesamiento

[Qué se hizo y por qué.]

### Modelo(s)

[Qué se entrenó, con qué hiperparámetros relevantes, y por qué se eligió ese enfoque.]

---

## 📈 Resultados

> 📝 Esta es la sección que más se lee. No alcanza con "funcionó" — mostrá:
> - Las **métricas** apropiadas al problema (accuracy no siempre es la correcta —
>   si las clases están desbalanceadas, por ejemplo, justificá por qué usás F1/AUC/etc.).
> - Una comparación contra algo (un baseline simple, u otro modelo que hayas probado).
> - Al menos un gráfico (matriz de confusión, curva ROC, importancia de features,
>   predicho vs. real — lo que corresponda a tu problema).
> - Un párrafo de **análisis crítico**: ¿dónde falla el modelo? ¿qué harías distinto
>   con más tiempo/datos? Esto demuestra más entendimiento que mostrar solo números altos.

| Métrica | Baseline | Modelo final |
|---|---|---|
| [Métrica 1] | [valor] | [valor] |
| [Métrica 2] | [valor] | [valor] |

![Resultados](docs/img/resultados.png)

[Análisis crítico de los resultados: fortalezas, limitaciones, posibles mejoras.]

---

## 📂 Estructura del proyecto

```text
.
├── README.md
├── pyproject.toml
├── src/                  # Código fuente (funciones y módulos propios)
├── notebooks/            # Notebooks de exploración y experimentación
├── data/
│   ├── raw/               # Datos originales, sin procesar
│   └── processed/         # Datos ya procesados, listos para el modelo
├── models/                # Modelos entrenados (serializados)
├── tests/                 # Tests (si aplica)
└── docs/                  # Demo estática (GitHub Pages) e imágenes del README
```

> 📝 Ajustá este árbol a como quedó tu proyecto realmente — borrá lo que no uses
> y agregá lo que sí. No dejes carpetas vacías listadas si no existen.

---

## ⚙️ Instalación

> 📝 Tiene que poder seguir estos pasos alguien que nunca vio tu proyecto y terminar
> con todo funcionando. Si usaste un flujo distinto a `uv` (pip, conda, poetry), adaptá
> esta sección — pero no la dejes genérica, tiene que ser el comando real que funciona.

### Prerrequisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

### Pasos

```bash
# 1. Cloná el repositorio
git clone https://github.com/TU-USUARIO/TU-REPOSITORIO.git
cd TU-REPOSITORIO

# 2. Creá el entorno virtual
uv venv --python 3.11

# 3. Activalo
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Instalá las dependencias
uv pip install -e .
```

[Agregá acá cualquier paso extra: descargar el dataset, variables de entorno, un archivo `.env`, etc.]

---

## ▶️ Uso

> 📝 Mostrá cómo correr el proyecto de punta a punta, con comandos reales y, si corresponde,
> un ejemplo de salida esperada (texto o captura). Si el "uso" es abrir una notebook, decí
> cuál y con qué kernel.

```bash
jupyter notebook notebooks/01_eda.ipynb
```

[Ejemplo de uso del modelo/script principal, con input y output de ejemplo.]

---

## 🗺️ Roadmap

> 📝 Opcional, pero suma: muestra que pensaste más allá del entregable. Lista corta
> de 2-4 cosas que harías con más tiempo.

- [ ] [Mejora futura 1]
- [ ] [Mejora futura 2]

---

## 👥 Autores

> 📝 Nombre, y al menos un link de contacto/portfolio por persona (GitHub, LinkedIn, email).

- **[Nombre Apellido]** — [GitHub](https://github.com/usuario) · [LinkedIn](https://linkedin.com/in/usuario)

---

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE) — ver el archivo `LICENSE` para más detalle.

> 📝 MIT es una buena opción por defecto para un proyecto de portfolio (permisiva, estándar
> en la industria). Si tu dataset tiene una licencia distinta a la del código, aclaralo
> en la sección "El dataset".

---

## 🙏 Agradecimientos y referencias

> 📝 Citá lo que corresponda: papers o artículos en los que te basaste, datasets de terceros,
> librerías o tutoriales puntuales que te resolvieron algo no trivial, compañeros/docentes
> que te ayudaron. Es una práctica académica estándar dar crédito a las fuentes que usaste.

- [Referencia 1]
- [Referencia 2]
