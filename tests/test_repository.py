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


def test_init_database_creates_schema(isolated_db):
    status = repo.get_database_status()

    assert isolated_db.exists()
    assert status["ready"] is True
    assert status["schema_version"] == db_setup.SCHEMA_VERSION
    assert status["table_count"] == 23


def test_guardar_prediccion_y_consultas(isolated_db):
    with repo.get_connection() as connection:
        anio_id = repo.get_active_anio_escolar_id(connection)

    assert anio_id is not None
    estudiante_id = repo.buscar_o_crear_estudiante("Ana", "Garcia", "Lopez")
    evaluacion_id = repo.guardar_evaluacion(
        estudiante_id=estudiante_id,
        anio_escolar_id=anio_id,
        asistencias=78.5,
        nota_matematica="B",
        nota_lenguaje="A",
        participacion=6.0,
        origen="manual",
    )
    prediccion_id = repo.guardar_prediccion(
        estudiante_id=estudiante_id,
        probabilidad_alto=0.82,
        nivel_riesgo="alto",
        etiqueta="Alto Riesgo",
        confianza=0.82,
        evaluacion_id=evaluacion_id,
    )

    estudiante = repo.obtener_estudiante(estudiante_id)
    evaluaciones = repo.obtener_evaluaciones(estudiante_id)
    predicciones = repo.obtener_predicciones(estudiante_id)
    estudiantes = repo.listar_estudiantes()

    assert prediccion_id > 0
    assert estudiante["nombres"] == "Ana"
    assert len(evaluaciones) == 1
    assert evaluaciones[0]["nota_matematica"] == "B"
    assert len(predicciones) == 1
    assert predicciones[0]["nivel_riesgo"] == "alto"
    assert any(item["id"] == estudiante_id for item in estudiantes)


def test_registrar_carga_siagie(isolated_db):
    carga_id = repo.registrar_carga_siagie(
        nombre_archivo="siagie_ejemplo.xlsx",
        total_filas=30,
        filas_procesadas=28,
        filas_error=2,
    )

    assert carga_id > 0


def test_buscar_o_crear_estudiante_no_duplica(isolated_db):
    first_id = repo.buscar_o_crear_estudiante("Luis", "Mendoza")
    second_id = repo.buscar_o_crear_estudiante("Luis", "Mendoza")

    assert first_id == second_id
