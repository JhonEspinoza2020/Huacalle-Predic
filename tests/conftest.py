import os
import sys

from paths import BACKEND_DIR, TESTS_DIR

pytest_plugins = ["fixtures_db"]

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Desactiva login obligatorio en la suite de pytest (salvo tests que lo activen).
os.environ.setdefault("PREDICTEDU_AUTH", "0")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "caja_negra: prueba de comportamiento externo (API, sin detalle de implementación)",
    )
    config.addinivalue_line(
        "markers",
        "caja_blanca: prueba con conocimiento de estructura interna (BD, módulos)",
    )
    config.addinivalue_line(
        "markers",
        "unitaria: prueba de función o módulo aislado",
    )
