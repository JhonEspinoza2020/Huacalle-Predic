"""Carga el módulo Flask de prueba compartido por la suite."""
import importlib.util

from paths import PROJECT_ROOT


def load_app_module():
    app_path = PROJECT_ROOT / "backend-sidecar" / "app.py"
    spec = importlib.util.spec_from_file_location("edge_pride_backend_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
