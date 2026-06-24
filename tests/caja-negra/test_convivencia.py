import sys
from pathlib import Path

from database import repository as repo
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_crear_derivacion_e_incidencia(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    estudiante = repo.registrar_estudiante(
        nombre_completo="Convivencia Test",
        dni="55667788",
    )

    intervencion_id = repo.registrar_intervencion(
        estudiante_id=estudiante["id"],
        titulo="Seguimiento previo",
        tipo="contacto_familia",
        descripcion="Llamada a apoderado",
    )

    derivacion = client.post(
        "/api/derivaciones",
        json={
            "estudiante_id": estudiante["id"],
            "intervencion_id": intervencion_id,
            "entidad_destino": "ugel",
            "motivo": "Derivacion por riesgo academico persistente",
        },
        headers=headers,
    )
    assert derivacion.status_code == 201
    body = derivacion.get_json()
    assert body["derivacion"]["entidad_destino"] == "ugel"
    assert body["derivacion"]["intervencion_id"] == intervencion_id
    assert body["derivacion"]["estado"] == "pendiente"

    incidencia = client.post(
        "/api/incidencias",
        json={
            "estudiante_id": estudiante["id"],
            "tipo_incidencia": "bullying",
            "severidad": "alta",
            "descripcion": "Agresion verbal repetida en el recreo durante la semana",
            "acciones_tomadas": "Entrevista con ambas partes y apoderados",
        },
        headers=headers,
    )
    assert incidencia.status_code == 201
    assert incidencia.get_json()["incidencia"]["severidad"] == "alta"

    lista_deriv = client.get("/api/derivaciones?estado=pendiente", headers=headers).get_json()
    assert lista_deriv["total"] >= 1

    lista_inc = client.get("/api/incidencias?severidad=alta", headers=headers).get_json()
    assert lista_inc["total"] >= 1

    ficha = client.get(
        f"/api/estudiantes/{estudiante['id']}/incidencias?severidad=alta",
        headers=headers,
    ).get_json()
    assert ficha["total"] == 1
    assert ficha["incidencias"][0]["tipo_incidencia"] == "bullying"


def test_actualizar_estado_derivacion(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    estudiante = repo.registrar_estudiante(nombre_completo="Derivacion Patch", dni="66778899")
    created = client.post(
        "/api/derivaciones",
        json={
            "estudiante_id": estudiante["id"],
            "entidad_destino": "demuna",
            "motivo": "Situacion de vulnerabilidad familiar reportada",
        },
        headers=headers,
    ).get_json()

    patched = client.patch(
        f"/api/derivaciones/{created['derivacion']['id']}",
        json={"estado": "en_proceso", "fecha_respuesta": "2026-06-03"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.get_json()["derivacion"]["estado"] == "en_proceso"


def test_rechaza_derivacion_con_intervencion_incorrecta(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    alumno_a = repo.registrar_estudiante(nombre_completo="Alumno A", dni="11112222")
    alumno_b = repo.registrar_estudiante(nombre_completo="Alumno B", dni="33334444")
    intervencion_id = repo.registrar_intervencion(
        estudiante_id=alumno_a["id"],
        titulo="Solo alumno A",
        tipo="otro",
    )

    response = client.post(
        "/api/derivaciones",
        json={
            "estudiante_id": alumno_b["id"],
            "intervencion_id": intervencion_id,
            "entidad_destino": "salud",
            "motivo": "Derivacion con intervencion de otro alumno",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "no corresponde" in response.get_json()["error"].lower()
