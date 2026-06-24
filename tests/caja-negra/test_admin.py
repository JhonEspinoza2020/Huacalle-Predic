import sys
from pathlib import Path

from database import repository as repo
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_resumen_bd(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "admin", "admin2026")

    response = client.get("/api/admin/resumen-bd", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.get_json()
    assert "tablas" in data
    assert any(item["tabla"] == "estudiantes" for item in data["tablas"])


def test_admin_anio_escolar_list_and_activate(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "admin", "admin2026")

    with repo.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO configuracion_anio_escolar (anio, fecha_inicio, fecha_fin, activo)
            VALUES (?, ?, ?, 0)
            """,
            (2099, "2099-03-01", "2099-12-15"),
        )

    list_response = client.get("/api/admin/anio-escolar", headers=auth_headers(token))
    assert list_response.status_code == 200
    list_data = list_response.get_json()
    assert list_data["anios"]
    assert list_data["activo"] is not None

    activo_id = list_data["activo"]["id"]
    otro = next(item for item in list_data["anios"] if item["id"] != activo_id)
    post_response = client.post(
        "/api/admin/anio-escolar",
        headers=auth_headers(token),
        json={"anio_escolar_id": otro["id"]},
    )
    assert post_response.status_code == 200
    post_data = post_response.get_json()
    assert post_data["activo"]["id"] == otro["id"]

    verify = client.get("/api/admin/anio-escolar", headers=auth_headers(token))
    assert verify.get_json()["activo"]["id"] == otro["id"]


def test_admin_eliminar_demo_requires_admin(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "admin", "admin2026")

    response = client.delete("/api/admin/estudiantes/demo", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
