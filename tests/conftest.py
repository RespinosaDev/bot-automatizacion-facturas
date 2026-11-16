import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ejemplos.generar_facturas import generar  # noqa: E402


@pytest.fixture(scope="session")
def facturas_ejemplo(tmp_path_factory):
    """Las facturas de ejemplo, generadas una vez por sesión de tests."""
    carpeta = tmp_path_factory.mktemp("ejemplos")
    generar(carpeta)
    return carpeta
