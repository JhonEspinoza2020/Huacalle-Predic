import io
import sys
from pathlib import Path

from database import repository as repo
from database.reforzamiento import (
    crear_material_reforzamiento,
    inferir_area_curso,
    inferir_motivo_inscripcion,
    listar_sesiones_curso,
)
from api_helpers import auth_headers, load_app_with_db, login_as


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_listar_cursos_con_cupos(isolated_db, monkeypatch):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    cursos = __import__("database.reforzamiento", fromlist=["listar_cursos_reforzamiento"]).listar_cursos_reforzamiento()
    assert len(cursos) >= 2
    assert "cupos_disponibles" in cursos[0]


def test_inscripcion_sesion_y_material(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    cursos = client.get("/api/cursos-reforzamiento", headers=headers).get_json()["cursos"]
    curso_id = cursos[0]["id"]

    estudiante = repo.registrar_estudiante(
        nombre_completo="Taller Reforzamiento",
        dni="44556611",
    )

    inscripcion = client.post(
        f"/api/cursos-reforzamiento/{curso_id}/inscripciones",
        json={
            "estudiante_id": estudiante["id"],
            "motivo": "riesgo_alto",
            "prediccion_id": None,
        },
        headers=headers,
    )
    assert inscripcion.status_code == 201
    body = inscripcion.get_json()
    assert body["inscripcion"]["motivo"] == "riesgo_alto"

    sesion = client.post(
        f"/api/cursos-reforzamiento/{curso_id}/sesiones",
        json={
            "fecha_sesion": "2026-06-10",
            "tema": "Operaciones basicas",
            "modalidad": "presencial",
            "asistencia_registrada": 3,
        },
        headers=headers,
    )
    assert sesion.status_code == 201
    assert len(listar_sesiones_curso(curso_id)) == 1

    material = client.post(
        f"/api/cursos-reforzamiento/{curso_id}/materiales",
        json={"titulo": "Video explicativo", "url": "https://example.com/video"},
        headers=headers,
    )
    assert material.status_code == 201

    detalle = client.get(f"/api/cursos-reforzamiento/{curso_id}", headers=headers).get_json()
    assert len(detalle["inscripciones"]) == 1
    assert len(detalle["sesiones"]) == 1
    assert len(detalle["materiales"]) == 1


def test_patch_inscripcion_resultado(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    curso_id = client.get("/api/cursos-reforzamiento", headers=headers).get_json()["cursos"][0]["id"]
    estudiante = repo.registrar_estudiante(nombre_completo="Patch Taller", dni="33221100")
    created = client.post(
        f"/api/cursos-reforzamiento/{curso_id}/inscripciones",
        json={"estudiante_id": estudiante["id"], "motivo": "bajo_rendimiento"},
        headers=headers,
    ).get_json()

    patched = client.patch(
        f"/api/inscripciones/{created['inscripcion']['id']}",
        json={"resultado": "mejoro"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.get_json()["inscripcion"]["resultado"] == "mejoro"


def test_inferir_motivo_y_area():
    assert inferir_motivo_inscripcion("alto", None, "C", "A") == "riesgo_alto"
    assert inferir_motivo_inscripcion("medio", None, "B", "B") == "riesgo_medio"
    assert inferir_area_curso("C", "A") == "matematica"


def test_rechaza_archivo_invalido_en_material(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)
    curso_id = client.get("/api/cursos-reforzamiento", headers=headers).get_json()["cursos"][0]["id"]

    response = client.post(
        f"/api/cursos-reforzamiento/{curso_id}/materiales",
        data={"titulo": "Archivo malo", "file": (io.BytesIO(b"fake"), "virus.exe")},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Formato no permitido" in response.get_json()["error"]
    assert inferir_area_curso("A", "C") == "comunicacion"
