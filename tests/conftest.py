"""Configuración de pytest: permite importar `src` desde la raíz del repo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
