"""Utilidades compartidas para pruebas de API con BD aislada."""
import importlib
import sys

from database import db_setup
from database import repository as repo


def load_app_with_db(monkeypatch, isolated_db, auth_enabled: bool = True):
    monkeypatch.setenv("PREDICTEDU_AUTH", "1" if auth_enabled else "0")
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    monkeypatch.setattr(db_setup, "get_db_path", lambda: str(isolated_db))

    module_name = "edge_pride_backend_app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        from app_loader import load_app_module

        return load_app_module()

    return sys.modules[module_name]


def login_as(client, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.get_json()["token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
