import importlib
import sys
from pathlib import Path

import pytest

from database import db_setup
from database import repository as repo




def load_app_with_db(monkeypatch, isolated_db):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    monkeypatch.setattr(db_setup, "get_db_path", lambda: str(isolated_db))

    module_name = "edge_pride_backend_app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        from app_loader import load_app_module

        return load_app_module()

    return sys.modules[module_name]


def test_predict_persists_with_student_name(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)

    class FakeModel:
        def predict(self, features):
            return [1]

        def predict_proba(self, features):
            return [[0.12, 0.88]]

    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    response = client.post(
        "/api/predict",
        json={
            "nombre": "Pedro Ramirez",
            "dni": "87654321",
            "asistencias": 70,
            "nota_matematica": "C",
            "nota_lenguaje": "B",
            "participacion": 4,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["storage"]["persisted"] is True
    assert data["storage"]["prediccion_id"] > 0

    estudiantes = repo.listar_estudiantes()
    assert any(item["nombres"] == "Pedro" for item in estudiantes)


def test_predict_without_name_or_dni_returns_error(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(
        app_module,
        "model",
        type(
            "FakeModel",
            (),
            {
                "predict": lambda self, features: [0],
                "predict_proba": lambda self, features: [[0.91, 0.09]],
            },
        )(),
    )

    client = app_module.app.test_client()
    response = client.post(
        "/api/predict",
        json={
            "asistencias": 90,
            "nota_matematica": "A",
            "nota_lenguaje": "A",
            "participacion": 8,
        },
    )

    data = response.get_json()
    assert response.status_code == 400
    assert "error" in data


def test_api_estudiantes_list(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(
        app_module,
        "model",
        type(
            "FakeModel",
            (),
            {
                "predict": lambda self, features: [1],
                "predict_proba": lambda self, features: [[0.1, 0.9]],
            },
        )(),
    )

    client = app_module.app.test_client()
    client.post(
        "/api/predict",
        json={
            "nombre": "Maria Lopez",
            "dni": "11223344",
            "asistencias": 55,
            "nota_matematica": "C",
            "nota_lenguaje": "C",
            "participacion": 3,
        },
    )

    response = client.get("/api/estudiantes")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] >= 1
    assert any(item["nombre"] == "Maria Lopez" for item in body["estudiantes"])


def test_api_resumen_reflects_persisted_data(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(
        app_module,
        "model",
        type(
            "FakeModel",
            (),
            {
                "predict": lambda self, features: [1],
                "predict_proba": lambda self, features: [[0.1, 0.9]],
            },
        )(),
    )

    client = app_module.app.test_client()
    client.post(
        "/api/predict",
        json={
            "nombre": "Maria Lopez",
            "dni": "11223344",
            "asistencias": 55,
            "nota_matematica": "C",
            "nota_lenguaje": "C",
            "participacion": 3,
        },
    )

    resumen = client.get("/api/resumen")
    assert resumen.status_code == 200
    body = resumen.get_json()
    assert body["has_data"] is True
    assert body["total_predicciones"] == 1
    assert body["ultima_prediccion"] is not None
    assert body["summary"]["alto"] >= 1
