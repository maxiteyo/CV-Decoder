"""Fijado de semillas aleatorias.

Una semilla fija hace que todos los procesos con azar (repartir los datos,
mezclar el orden de entrenamiento, inicializar pesos) den SIEMPRE el mismo
resultado. Es un requisito de la cátedra para que el proyecto sea reproducible.
"""

import os
import random

import numpy as np


def set_global_seed(seed: int = 42) -> None:
    """Fija la semilla en las librerías que la usan."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
