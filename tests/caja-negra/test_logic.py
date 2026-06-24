import importlib.util

import pytest

from app_loader import load_app_module


@pytest.mark.caja_negra
def test_predict_endpoint_with_valid_payload(monkeypatch):
    app_module = load_app_module()

    class FakeModel:
        def predict(self, features):
            return [1]

        def predict_proba(self, features):
            return [[0.12, 0.88]]

    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    payload = {
        "dni": "99887766",
        "nombre": "Alumno Prueba",
        "asistencias": 80,
        "nota_matematica": "A",
        "nota_lenguaje": "B",
        "participacion": 7,
    }
    response = client.post("/api/predict", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["prediction"] == "Alto Riesgo"
    assert data["confidence"] == 0.88
    assert data["model"] == "Random Forest + criterios pedagógicos"


@pytest.mark.caja_negra
def test_predict_endpoint_missing_data_returns_controlled_error(monkeypatch):
    app_module = load_app_module()

    class FakeModel:
        def predict(self, features):
            return [0]

        def predict_proba(self, features):
            return [[0.91, 0.09]]

    monkeypatch.setattr(app_module, "model", FakeModel())
    client = app_module.app.test_client()

    invalid_payload = {
        "dni": "71272388",
        "asistencias": 77,
        "nota_matematica": "A",
        "participacion": 6,
    }
    response = client.post("/api/predict", json=invalid_payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "AD, A, B o C" in data["error"]


@pytest.mark.caja_negra
def test_api_status_model_loaded(monkeypatch):
    """CP-001 — Estado del servicio con modelo cargado."""
    app_module = load_app_module()
    monkeypatch.setattr(app_module, "model", object())
    monkeypatch.setattr(
        app_module,
        "get_database_status",
        lambda: {
            "ready": True,
            "path": "/tmp/colegio.db",
            "schema_version": 4,
            "table_count": 24,
            "tables": [],
        },
    )

    client = app_module.app.test_client()
    response = client.get("/api/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


@pytest.mark.caja_negra
def test_api_status_without_model(monkeypatch):
    """CP-002 — Estado del servicio sin modelo."""
    app_module = load_app_module()
    monkeypatch.setattr(app_module, "model", None)
    monkeypatch.setattr(
        app_module,
        "get_database_status",
        lambda: {
            "ready": True,
            "path": "/tmp/colegio.db",
            "schema_version": 4,
            "table_count": 24,
            "tables": [],
        },
    )

    client = app_module.app.test_client()
    response = client.get("/api/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["model_loaded"] is False


@pytest.mark.caja_negra
def test_predict_without_model_returns_500(monkeypatch):
    """CP-005 — Modelo no disponible en predicción."""
    app_module = load_app_module()
    monkeypatch.setattr(app_module, "model", None)
    client = app_module.app.test_client()

    response = client.post(
        "/api/predict",
        json={
            "dni": "12345678",
            "nombre": "Prueba",
            "asistencias": 80,
            "nota_matematica": "A",
            "nota_lenguaje": "B",
            "participacion": 7,
        },
    )
    data = response.get_json()

    assert response.status_code == 500
    assert "modelo" in data["error"].lower()


@pytest.mark.caja_negra
def test_api_status_includes_database(monkeypatch):
    app_module = load_app_module()
    monkeypatch.setattr(
        app_module,
        "get_database_status",
        lambda: {
            "ready": True,
            "path": "/tmp/colegio.db",
            "schema_version": 4,
            "table_count": 24,
            "tables": [],
        },
    )

    client = app_module.app.test_client()
    response = client.get("/api/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["database"]["ready"] is True
    assert data["database"]["table_count"] == 24
