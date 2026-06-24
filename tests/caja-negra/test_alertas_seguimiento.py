import sys
from pathlib import Path

from database import repository as repo
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _crear_alerta_abierta(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(
        app_module,
        "model",
        type(
            "FakeModel",
            (),
            {
                "predict": lambda self, features: [1],
                "predict_proba": lambda self, features: [[0.15, 0.85]],
            },
        )(),
    )
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    secciones = repo.listar_secciones_activas()
    seccion_tutor = next(item for item in secciones if item.get("tutor_id") == 1)
    client.post(
        "/api/estudiantes",
        json={
            "dni": "55443322",
            "nombre": "Alerta Seguimiento Test",
            "seccion_id": seccion_tutor["id"],
        },
        headers=headers,
    )
    predict = client.post(
        "/api/predict",
        json={
            "dni": "55443322",
            "nombre": "Alerta Seguimiento Test",
            "asistencias": 58,
            "nota_matematica": "C",
            "nota_lenguaje": "C",
            "participacion": 2,
        },
        headers=headers,
    )
    alerta_id = predict.get_json()["storage"]["alerta_id"]
    return client, headers, alerta_id


def test_registrar_seguimiento_y_cambiar_estado(isolated_db, monkeypatch):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    client, headers, alerta_id = _crear_alerta_abierta(isolated_db, monkeypatch)

    patch = client.patch(
        f"/api/alertas/{alerta_id}",
        json={
            "estado": "en_revision",
            "accion": "en_revision",
            "detalle": "Se reviso el caso en aula.",
        },
        headers=headers,
    )
    assert patch.status_code == 200
    assert patch.get_json()["alerta"]["estado"] == "en_revision"

    historial = client.get(f"/api/alertas/{alerta_id}/historial", headers=headers).get_json()
    assert len(historial["seguimiento"]) == 1
    assert historial["seguimiento"][0]["accion"] == "en_revision"


def test_intervencion_registra_seguimiento_en_alerta(isolated_db, monkeypatch):
    client, headers, alerta_id = _crear_alerta_abierta(isolated_db, monkeypatch)
    estudiante = repo.buscar_estudiante_por_dni("55443322")

    response = client.post(
        "/api/intervenciones",
        json={
            "estudiante_id": estudiante["id"],
            "alerta_id": alerta_id,
            "titulo": "Llamada apoderado",
            "descripcion": "Se contacto a la familia.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.get_json()["alertas_atendidas"] == 1

    historial = client.get(f"/api/alertas/{alerta_id}/historial", headers=headers).get_json()
    assert historial["alerta"]["estado"] == "atendida"
    assert any(item["accion"] == "registro_intervencion" for item in historial["seguimiento"])


def test_alerta_cerrada_no_aparece_en_prioritarias(isolated_db, monkeypatch):
    client, headers, alerta_id = _crear_alerta_abierta(isolated_db, monkeypatch)

    close = client.patch(
        f"/api/alertas/{alerta_id}",
        json={"estado": "cerrada", "accion": "cierre_manual"},
        headers=headers,
    )
    assert close.status_code == 200

    resumen = client.get("/api/resumen", headers=headers).get_json()
    ids = [item["alerta_id"] for item in resumen["alertas_prioritarias"]]
    assert alerta_id not in ids
