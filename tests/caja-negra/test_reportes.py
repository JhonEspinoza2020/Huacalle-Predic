import importlib
import sys
from pathlib import Path

import pytest

from database import db_setup
from database import repository as repo




def load_app_with_db(monkeypatch, isolated_db):
    monkeypatch.setattr(repo, "get_db_path", lambda: str(isolated_db))
    monkeypatch.setattr(db_setup, "get_db_path", lambda: str(isolated_db))

    module_name = "edge_pride_backend_app"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        from app_loader import load_app_module

        return load_app_module()

    return sys.modules[module_name]


def seed_student_with_prediction(isolated_db, monkeypatch, dni, nombre, riesgo):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    monkeypatch.setattr(
        app_module,
        "model",
        type(
            "FakeModel",
            (),
            {
                "predict": lambda self, features: [1 if riesgo == "alto" else 0],
                "predict_proba": lambda self, features: (
                    [[0.2, 0.8]] if riesgo == "alto" else [[0.85, 0.15]]
                ),
            },
        )(),
    )
    client = app_module.app.test_client()
    client.post(
        "/api/estudiantes",
        json={"dni": dni, "nombre": nombre},
    )
    client.post(
        "/api/predict",
        json={
            "dni": dni,
            "asistencias": 40 if riesgo == "alto" else 90,
            "nota_matematica": "C" if riesgo == "alto" else "A",
            "nota_lenguaje": "B",
            "participacion": 3 if riesgo == "alto" else 8,
        },
    )
    return client


def test_filter_estudiantes_by_riesgo(isolated_db, monkeypatch):
    seed_student_with_prediction(isolated_db, monkeypatch, "71111111", "Alto Uno", "alto")
    seed_student_with_prediction(isolated_db, monkeypatch, "72222222", "Bajo Dos", "bajo")

    client = load_app_with_db(monkeypatch, isolated_db).app.test_client()
    response = client.get("/api/estudiantes?riesgo=alto")
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["estudiantes"][0]["ultimo_nivel_riesgo"] == "alto"

    repo.buscar_o_crear_estudiante("Sin Prediccion", dni="83333333")
    response_bajo = client.get("/api/estudiantes?riesgo=bajo")
    body_bajo = response_bajo.get_json()

    assert response_bajo.status_code == 200
    assert body_bajo["total"] == 2
    dnies = {item["dni"] for item in body_bajo["estudiantes"]}
    assert dnies == {"72222222", "83333333"}


def test_exportar_reporte_xlsx(isolated_db, monkeypatch):
    seed_student_with_prediction(isolated_db, monkeypatch, "73333333", "Export Test", "alto")

    client = load_app_with_db(monkeypatch, isolated_db).app.test_client()
    response = client.get("/api/reportes/exportar?formato=xlsx")

    assert response.status_code == 200
    assert (
        response.headers["Content-Type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(response.data) > 100
