import importlib
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend-sidecar"
sys.path.insert(0, str(BACKEND_DIR))

from database import db_setup
from database import repository as repo


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "colegio.db"

    def _db_path():
        return str(db_file)

    monkeypatch.setattr(db_setup, "get_db_path", _db_path)
    monkeypatch.setattr(repo, "get_db_path", _db_path)
    repo.init_database(seed=True)
    return db_file


def load_app_with_db(monkeypatch, isolated_db, auth_enabled: bool = True):
    monkeypatch.setenv("PREDICTEDU_AUTH", "1" if auth_enabled else "0")
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    monkeypatch.setattr(db_setup, "get_db_path", lambda: str(isolated_db))

    module_name = "edge_pride_backend_app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        from test_logic import load_app_module

        return load_app_module()

    return sys.modules[module_name]


def login_as(client, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    body = response.get_json()
    token = body["token"]
    return token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_admin_ok(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin2026"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["user"]["rol"] == "admin"
    assert "token" in body


def test_login_docente_ok(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "mquispe", "password": "tutor2026"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["user"]["rol"] == "docente"


def test_login_invalid_credentials(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401


def test_protected_route_requires_auth(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()

    response = client.get("/api/resumen")

    assert response.status_code == 401


def test_docente_cannot_access_admin(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")

    response = client.get(
        "/api/admin/docentes",
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_admin_can_access_admin_panel(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "admin", "admin2026")

    response = client.get(
        "/api/admin/docentes",
        headers=auth_headers(token),
    )
    body = response.get_json()

    assert response.status_code == 200
    assert len(body["docentes"]) >= 2

    secciones = client.get(
        "/api/admin/secciones",
        headers=auth_headers(token),
    ).get_json()

    assert len(secciones["secciones"]) >= 4


def test_intervencion_saves_docente_id(isolated_db, monkeypatch):
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
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    client.post(
        "/api/estudiantes",
        json={"dni": "55667788", "nombre": "Interv Test"},
        headers=headers,
    )
    client.post(
        "/api/predict",
        json={
            "dni": "55667788",
            "nombre": "Interv Test",
            "asistencias": 40,
            "nota_matematica": "C",
            "nota_lenguaje": "C",
            "participacion": 2,
        },
        headers=headers,
    )

    estudiantes = client.get("/api/estudiantes", headers=headers).get_json()
    estudiante_id = estudiantes["estudiantes"][0]["id"]

    response = client.post(
        "/api/intervenciones",
        json={"estudiante_id": estudiante_id, "titulo": "Llamada apoderado"},
        headers=headers,
    )

    assert response.status_code == 201

    with repo.get_connection() as connection:
        row = connection.execute(
            "SELECT docente_id FROM intervenciones ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row[0] == 1


def test_auth_recuperar_public(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()

    response = client.post(
        "/api/auth/recuperar",
        json={"telefono": "987654321", "username": "mquispe"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["pendiente"] is True
