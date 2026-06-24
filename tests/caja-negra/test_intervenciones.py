import sys
from pathlib import Path

from database import db_setup
from database import repository as repo
from api_helpers import load_app_with_db


def _crear_estudiante_demo() -> int:
    estudiante_id = repo.buscar_o_crear_estudiante(
        dni="44556677",
        nombres="Filtro",
        apellido_paterno="Intervencion",
        apellido_materno="Test",
    )
    return estudiante_id


def _insertar_intervencion(estudiante_id: int, created_at: str) -> None:
    with repo.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO intervenciones (
                estudiante_id,
                tipo,
                titulo,
                estado,
                created_at
            )
            VALUES (?, 'contacto_familia', 'Seguimiento prueba', 'pendiente', ?)
            """,
            (estudiante_id, created_at),
        )


def test_listar_intervenciones_filtra_por_fechas(isolated_db, monkeypatch):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    estudiante_id = _crear_estudiante_demo()
    _insertar_intervencion(estudiante_id, "2026-05-10 10:00:00")
    _insertar_intervencion(estudiante_id, "2026-06-02 11:00:00")
    _insertar_intervencion(estudiante_id, "2026-06-15 12:00:00")

    mayo = repo.listar_intervenciones(fecha_desde="2026-05-01", fecha_hasta="2026-05-31")
    junio = repo.listar_intervenciones(fecha_desde="2026-06-01", fecha_hasta="2026-06-30")
    todo = repo.listar_intervenciones()

    assert mayo["total"] == 1
    assert junio["total"] == 2
    assert todo["total"] == 3


def test_api_intervenciones_acepta_filtro_fechas(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db, auth_enabled=False)
    client = app_module.app.test_client()
    estudiante_id = _crear_estudiante_demo()
    _insertar_intervencion(estudiante_id, "2026-04-01 09:00:00")
    _insertar_intervencion(estudiante_id, "2026-06-03 09:00:00")

    response = client.get("/api/intervenciones?desde=2026-06-01&hasta=2026-06-30")
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["desde"] == "2026-06-01"
    assert body["hasta"] == "2026-06-30"
    assert len(body["intervenciones"]) == 1


def test_api_intervenciones_rechaza_rango_invalido(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db, auth_enabled=False)
    client = app_module.app.test_client()

    response = client.get("/api/intervenciones?desde=2026-06-10&hasta=2026-06-01")
    body = response.get_json()

    assert response.status_code == 400
    assert "desde" in body["error"].lower()
