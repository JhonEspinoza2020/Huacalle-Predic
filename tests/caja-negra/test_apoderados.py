import sys
from pathlib import Path

from database import db_setup
from database import repository as repo
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_guardar_apoderado_principal_unico(isolated_db, monkeypatch):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    estudiante = repo.registrar_estudiante(
        nombre_completo="Ana Perez Lopez",
        dni="33445566",
    )

    apoderado = repo.guardar_apoderado_principal(
        estudiante_id=estudiante["id"],
        nombre_completo="Rosa Lopez Vega",
        telefono="987111222",
        parentesco="madre",
        dni="11223344",
    )

    assert apoderado["nombre"] == "Rosa Lopez Vega"
    assert apoderado["telefono"] == "987111222"
    assert apoderado["parentesco"] == "madre"

    actualizado = repo.guardar_apoderado_principal(
        estudiante_id=estudiante["id"],
        nombre_completo="Rosa Lopez Vega",
        telefono="987333444",
        parentesco="madre",
    )
    assert actualizado["telefono"] == "987333444"

    with repo.get_connection() as connection:
        count = connection.execute(
            """
            SELECT COUNT(*) FROM estudiante_apoderado
            WHERE estudiante_id = ? AND es_principal = 1
            """,
            (estudiante["id"],),
        ).fetchone()[0]
    assert count == 1


def test_api_apoderado_get_y_post(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    estudiante = repo.registrar_estudiante(
        nombre_completo="Luis Castro Ruiz",
        dni="22334455",
    )

    get_empty = client.get(f"/api/estudiantes/{estudiante['id']}/apoderado", headers=headers)
    assert get_empty.status_code == 200
    assert get_empty.get_json()["apoderado"] is None

    post = client.post(
        f"/api/estudiantes/{estudiante['id']}/apoderado",
        json={
            "nombre": "Maria Castro",
            "telefono": "987654321",
            "parentesco": "madre",
        },
        headers=headers,
    )
    assert post.status_code == 201
    body = post.get_json()
    assert body["apoderado"]["telefono"] == "987654321"

    get_ok = client.get(f"/api/estudiantes/{estudiante['id']}/apoderado", headers=headers)
    assert get_ok.get_json()["apoderado"]["nombre"] == "Maria Castro"


def test_registrar_estudiante_con_apoderado(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    secciones = repo.listar_secciones_activas()
    seccion_tutor = next(item for item in secciones if item.get("tutor_id") == 1)

    response = client.post(
        "/api/estudiantes",
        json={
            "dni": "77889900",
            "nombre": "Pedro Apoderado Test",
            "seccion_id": seccion_tutor["id"],
            "apoderado": {
                "nombre": "Juana Apoderado",
                "telefono": "912345678",
                "parentesco": "apoderado",
            },
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["apoderado"]["telefono"] == "912345678"


def test_alertas_incluyen_telefono_apoderado(isolated_db, monkeypatch):
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

    secciones = repo.listar_secciones_activas()
    seccion_tutor = next(item for item in secciones if item.get("tutor_id") == 1)

    registro = client.post(
        "/api/estudiantes",
        json={
            "dni": "66778899",
            "nombre": "Alerta Apoderado",
            "seccion_id": seccion_tutor["id"],
            "apoderado": {
                "nombre": "Papa Alerta",
                "telefono": "911223344",
                "parentesco": "padre",
            },
        },
        headers=headers,
    )
    estudiante_id = registro.get_json()["estudiante"]["id"]

    client.post(
        "/api/predict",
        json={
            "dni": "66778899",
            "nombre": "Alerta Apoderado",
            "asistencias": 55,
            "nota_matematica": "C",
            "nota_lenguaje": "C",
            "participacion": 2,
        },
        headers=headers,
    )

    resumen = client.get("/api/resumen", headers=headers).get_json()
    alerta = next(
        item for item in resumen["alertas_prioritarias"] if item["estudiante_id"] == estudiante_id
    )
    assert alerta["apoderado_telefono"] == "911223344"
    assert alerta["apoderado_nombre"] == "Papa Alerta"
