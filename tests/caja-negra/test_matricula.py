from database import repository as repo

from api_helpers import auth_headers, load_app_with_db, login_as


def test_registrar_estudiante_con_matricula(isolated_db):
    secciones = repo.listar_secciones_activas()
    assert len(secciones) >= 1

    estudiante = repo.registrar_estudiante(
        nombre_completo="Luz Ana Torres Vega",
        dni="99887766",
        seccion_id=secciones[0]["id"],
    )

    assert estudiante["matricula_id"] is not None
    assert estudiante["seccion_etiqueta"] is not None

    with repo.get_connection() as connection:
        anio_id = repo.get_active_anio_escolar_id(connection)
    matricula_id = repo.obtener_matricula_id_activa(estudiante["id"], anio_id)
    assert matricula_id == estudiante["matricula_id"]


def test_matricula_unica_por_ano(isolated_db):
    secciones = repo.listar_secciones_activas()
    estudiante = repo.registrar_estudiante(
        nombre_completo="Pedro Ramos Diaz",
        dni="88776655",
        seccion_id=secciones[0]["id"],
    )

    nueva_matricula = repo.matricular_estudiante(
        estudiante["id"],
        secciones[1]["id"] if len(secciones) > 1 else secciones[0]["id"],
    )
    assert nueva_matricula == estudiante["matricula_id"]


def test_listar_estudiantes_por_seccion(isolated_db):
    secciones = repo.listar_secciones_activas()
    repo.registrar_estudiante(
        nombre_completo="Alumno Seccion A",
        dni="11112222",
        seccion_id=secciones[0]["id"],
    )

    filtrados = repo.listar_estudiantes_detallado(seccion_id=secciones[0]["id"])
    assert any(item["dni"] == "11112222" for item in filtrados)
    assert all(item.get("seccion_id") == secciones[0]["id"] for item in filtrados if item["dni"])


def test_docente_ve_solo_sus_secciones(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    secciones_res = client.get("/api/secciones", headers=headers).get_json()
    assert len(secciones_res["mis_secciones"]) >= 2

    seccion_id = secciones_res["mis_secciones"][0]["id"]
    mis_ids = {item["id"] for item in secciones_res["mis_secciones"]}
    repo.registrar_estudiante(
        nombre_completo="Alumno Tutor Uno",
        dni="33445566",
        seccion_id=seccion_id,
    )
    otra_seccion = next(
        item for item in secciones_res["secciones"] if item["id"] not in mis_ids
    )
    repo.registrar_estudiante(
        nombre_completo="Alumno Otra Seccion",
        dni="44556677",
        seccion_id=otra_seccion["id"],
    )

    lista_docente = client.get("/api/estudiantes", headers=headers).get_json()
    dnis = {item["dni"] for item in lista_docente["estudiantes"]}
    assert "33445566" in dnis
    assert "44556677" not in dnis


def test_api_secciones_docente(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")

    response = client.get("/api/secciones", headers=auth_headers(token))
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] >= 4
    assert len(body["mis_secciones"]) >= 2


def test_buscar_asigna_matricula_si_falta(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db)
    client = app_module.app.test_client()
    token = login_as(client, "mquispe", "tutor2026")
    headers = auth_headers(token)

    repo.registrar_estudiante(
        nombre_completo="Alumno Sin Seccion",
        dni="71272388",
    )

    response = client.get("/api/estudiantes/buscar?dni=71272388", headers=headers)
    assert response.status_code == 200

    lista = client.get("/api/estudiantes", headers=headers).get_json()
    assert any(item["dni"] == "71272388" for item in lista["estudiantes"])
