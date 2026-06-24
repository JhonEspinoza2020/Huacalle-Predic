import sys
from pathlib import Path

from database import repository as repo
from database.indicadores import guardar_competencias_notas
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_calcular_y_listar_indicadores(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    estudiante = repo.registrar_estudiante(nombre_completo="Indicador Test", dni="90909090")
    secciones = repo.listar_secciones_activas()
    if secciones:
        repo.matricular_estudiante(estudiante_id=estudiante["id"], seccion_id=secciones[0]["id"])
    with repo.get_connection() as connection:
        anio_id = repo.get_active_anio_escolar_id(connection)
    repo.guardar_evaluacion(
        estudiante_id=estudiante["id"],
        anio_escolar_id=anio_id,
        asistencias=88.0,
        nota_matematica="B",
        nota_lenguaje="A",
        participacion=7.0,
    )
    repo.guardar_prediccion(
        estudiante_id=estudiante["id"],
        probabilidad_alto=0.2,
        nivel_riesgo="bajo",
        etiqueta="Bajo Riesgo",
        confianza=0.8,
    )

    response = client.post(
        "/api/indicadores/calcular",
        json={"anio": 2026, "mes": 6},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["total"] >= 1

    lista = client.get("/api/indicadores?anio=2026&mes=6", headers=headers).get_json()
    assert lista["total"] >= 1
    assert any(item["total_estudiantes"] >= 1 for item in lista["indicadores"])


def test_asistencias_diarias_recalcula_evaluacion(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    estudiante = repo.registrar_estudiante(nombre_completo="Asistencia Diaria", dni="80808080")
    with repo.get_connection() as connection:
        anio_id = repo.get_active_anio_escolar_id(connection)
    repo.guardar_evaluacion(
        estudiante_id=estudiante["id"],
        anio_escolar_id=anio_id,
        asistencias=50.0,
        nota_matematica="A",
        nota_lenguaje="A",
        participacion=8.0,
        bimestre=2,
    )

    response = client.post(
        "/api/asistencias-diarias",
        json={
            "registros": [
                {
                    "estudiante_id": estudiante["id"],
                    "fecha": "2026-06-02",
                    "estado_asistencia": "presente",
                    "bimestre": 2,
                },
                {
                    "estudiante_id": estudiante["id"],
                    "fecha": "2026-06-03",
                    "estado_asistencia": "falta",
                    "bimestre": 2,
                },
            ]
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["procesados"] == 2
    assert len(body["recalculados"]) == 1
    assert body["recalculados"][0]["asistencias"] == 50.0


def test_guardar_competencias_en_evaluacion(isolated_db, monkeypatch):
    estudiante = repo.registrar_estudiante(nombre_completo="Competencias", dni="70707070")
    with repo.get_connection() as connection:
        anio_id = repo.get_active_anio_escolar_id(connection)
    evaluacion_id = repo.guardar_evaluacion(
        estudiante_id=estudiante["id"],
        anio_escolar_id=anio_id,
        asistencias=90.0,
        nota_matematica="A",
        nota_lenguaje="B",
        participacion=8.0,
    )

    guardadas = guardar_competencias_notas(
        evaluacion_id,
        {"personal_social": "A", "arte_cultura": "B"},
    )
    assert len(guardadas) == 2

    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    competencias = client.get(
        f"/api/evaluaciones/{evaluacion_id}/competencias",
        headers=auth_headers(token),
    ).get_json()
    assert len(competencias["competencias"]) == 2


def test_export_incluye_hoja_indicadores(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    client.post("/api/indicadores/calcular", json={"anio": 2026, "mes": 6}, headers=headers)
    response = client.get("/api/reportes/exportar?formato=xlsx&anio=2026&mes=6", headers=headers)

    assert response.status_code == 200
    assert len(response.data) > 100
