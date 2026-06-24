"""Rutas del proyecto usadas por la suite pytest."""
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend-sidecar"
DOCS_DIR = PROJECT_ROOT / "docs"
