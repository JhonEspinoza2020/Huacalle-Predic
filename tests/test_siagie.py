import importlib
import io
import sys
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend-sidecar"
sys.path.insert(0, str(BACKEND_DIR))

from database import db_setup
from database import repository as repo

DEMO_XLSX = Path(__file__).resolve().parents[1] / "docs" / "siagie_demo_5toA.xlsx"


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "colegio.db"

    def _db_path():
        return str(db_file)

    monkeypatch.setattr(db_setup, "get_db_path", _db_path)
    monkeypatch.setattr(repo, "get_db_path", _db_path)
    repo.init_database(seed=True)
    return db_file


def load_app_with_db(monkeypatch, isolated_db):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    monkeypatch.setattr(db_setup, "get_db_path", lambda: str(isolated_db))

    module_name = "edge_pride_backend_app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        from test_logic import load_app_module

        return load_app_module()

    return sys.modules[module_name]


class FakeModel:
    def predict(self, features):
        return [1]

    def predict_proba(self, features):
        return [[0.25, 0.75]]


def _excel_bytes(rows):
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


def test_upload_siagie_valid_excel(isolated_db, monkeypatch):
    """CP-006 — Excel válido con columnas estándar."""
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    excel = _excel_bytes(
        [
            {
                "nombre": "Ana Demo",
                "dni": "80123456",
                "asistencias": 45,
                "nota_matematica": "C",
                "nota_lenguaje": "B",
                "participacion": 4,
            },
            {
                "nombre": "Luis Demo",
                "dni": "80123457",
                "asistencias": 90,
                "nota_matematica": "A",
                "nota_lenguaje": "AD",
                "participacion": 8,
            },
        ]
    )

    response = client.post(
        "/api/upload_siagie",
        data={"file": (excel, "siagie_test.xlsx")},
        content_type="multipart/form-data",
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["total_students"] == 2
    assert set(body["summary"].keys()) == {"alto", "medio", "bajo"}
    assert len(body["top_5_high_risk"]) <= 5
    assert body["storage"]["persisted"] is True
    assert body["storage"]["carga_siagie_id"] > 0


@pytest.mark.skipif(not DEMO_XLSX.is_file(), reason="demo xlsx no generado")
def test_upload_siagie_demo_file(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    with DEMO_XLSX.open("rb") as handle:
        response = client.post(
            "/api/upload_siagie",
            data={"file": (handle, DEMO_XLSX.name)},
            content_type="multipart/form-data",
        )

    body = response.get_json()
    assert response.status_code == 200
    assert body["total_students"] >= 8


def test_upload_siagie_missing_file(isolated_db, monkeypatch):
    """CP-007 — Sin archivo en la petición."""
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    response = client.post("/api/upload_siagie")
    body = response.get_json()

    assert response.status_code == 400
    assert "file" in body["error"].lower()


def test_upload_siagie_invalid_excel(isolated_db, monkeypatch):
    """CP-008 — Archivo no legible como Excel."""
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    response = client.post(
        "/api/upload_siagie",
        data={"file": (io.BytesIO(b"no es un excel"), "corrupto.xlsx")},
        content_type="multipart/form-data",
    )
    body = response.get_json()

    assert response.status_code == 400
    assert "excel" in body["error"].lower()


def test_upload_siagie_unprocessable_rows(isolated_db, monkeypatch):
    """CP-009 — Excel sin filas procesables."""
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    excel = _excel_bytes([{"columna_a": 1, "columna_b": "x"}])
    response = client.post(
        "/api/upload_siagie",
        data={"file": (excel, "sin_columnas.xlsx")},
        content_type="multipart/form-data",
    )
    body = response.get_json()

    assert response.status_code == 400
    assert "procesar" in body["error"].lower()


def test_upload_siagie_without_model(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(app_module, "model", None)
    client = app_module.app.test_client()

    excel = _excel_bytes(
        [
            {
                "nombre": "Sin modelo",
                "dni": "90909090",
                "asistencias": 50,
                "nota_matematica": "B",
                "nota_lenguaje": "B",
                "participacion": 5,
            }
        ]
    )
    response = client.post(
        "/api/upload_siagie",
        data={"file": (excel, "test.xlsx")},
        content_type="multipart/form-data",
    )
    body = response.get_json()

    assert response.status_code == 500
    assert "modelo" in body["error"].lower()
