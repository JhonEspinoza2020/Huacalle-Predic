import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS

_SIDECAR_ROOT = Path(__file__).resolve().parent
REFORZAMIENTO_UPLOAD_DIR = _SIDECAR_ROOT / "uploads" / "reforzamiento"
REFORZAMIENTO_ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".mp4"}
REFORZAMIENTO_MAX_BYTES = 50 * 1024 * 1024


def _validar_archivo_reforzamiento(archivo) -> str:
    nombre_seguro = Path(archivo.filename or "material.pdf").name
    extension = Path(nombre_seguro).suffix.lower()
    if extension not in REFORZAMIENTO_ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Formato no permitido ({extension or 'sin extensión'}). Use PDF, DOC, DOCX o MP4."
        )

    archivo.seek(0, 2)
    tamano = archivo.tell()
    archivo.seek(0)
    if tamano > REFORZAMIENTO_MAX_BYTES:
        raise ValueError("Archivo demasiado grande (máximo 50 MB).")
    return nombre_seguro
if str(_SIDECAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIDECAR_ROOT))

from auth_guard import auth_is_public, get_current_user, require_roles
from auth_tokens import create_access_token
from security_headers import register_security_headers
from risk_engine import evaluar_riesgo_pedagogico, nivel_riesgo_desde_probabilidad
from validators import (
    normalizar_dni,
    validar_asistencias,
    validar_bimestre,
    validar_nombre_completo,
    validar_nota_literal,
    validar_parentesco,
    validar_participacion,
    validar_telefono,
    validar_dni_opcional,
    validar_username,
)
from database.reforzamiento import (
    actualizar_inscripcion_reforzamiento,
    crear_material_reforzamiento,
    inscribir_estudiante_reforzamiento,
    listar_cursos_reforzamiento,
    listar_inscripciones_curso,
    listar_materiales_curso,
    listar_sesiones_curso,
    obtener_curso_reforzamiento,
    registrar_sesion_reforzamiento,
)
from database.convivencia import (
    actualizar_derivacion,
    crear_derivacion_externa,
    crear_incidencia_convivencia,
    listar_derivaciones,
    listar_incidencias,
)
from database.indicadores import (
    calcular_indicadores_mensuales,
    guardar_competencias_notas,
    listar_competencias_evaluacion,
    listar_indicadores,
    registrar_asistencias_diarias,
)
from database.repository import (
    autenticar_usuario,
    buscar_estudiante_por_dni,
    buscar_o_crear_estudiante,
    contar_estudiantes_filtrados,
    activar_anio_escolar,
    eliminar_estudiantes_demo,
    get_active_anio_escolar_id,
    listar_anios_escolares,
    get_connection,
    get_database_status,
    guardar_alerta_riesgo,
    guardar_apoderado_principal,
    guardar_evaluacion,
    guardar_prediccion,
    init_database,
    listar_cargas_siagie,
    listar_docentes,
    listar_estudiantes_detallado,
    listar_intervenciones,
    listar_secciones_activas,
    listar_secciones_institucional,
    listar_usuarios_sistema,
    matricular_estudiante,
    atender_alertas_estudiante,
    consolidar_alertas_duplicadas,
    actualizar_estado_alerta,
    listar_seguimiento_alerta,
    obtener_alerta_por_id,
    registrar_seguimiento_alerta,
    obtener_conteo_tablas,
    obtener_apoderado_principal,
    obtener_estudiante,
    obtener_matricula_id_activa,
    obtener_resumen_dashboard,
    obtener_seccion_ids_tutor,
    reparar_matriculas_pendientes_tutor,
    registrar_carga_siagie,
    registrar_estudiante,
    registrar_intervencion,
    actualizar_estado_intervencion,
    seccion_pertenece_tutor,
)

app = Flask(__name__)
CORS(app)
register_security_headers(app)

init_database()


@app.before_request
def protect_api_routes():
    if request.method == "OPTIONS":
        return None
    if not request.path.startswith("/api/"):
        return None
    if auth_is_public():
        return None
    if get_current_user() is None:
        return jsonify({"error": "No autorizado. Inicia sesión."}), 401
    return None


GRADE_TO_SCORE = {"C": 1, "B": 2, "A": 3, "AD": 4}
MODEL_PATH = Path(__file__).resolve().parent / "ml_models" / "modelo_rf.pkl"
model = None


def _normalize_grade(value):
    if value is None:
        return None
    grade = str(value).strip().upper()
    return GRADE_TO_SCORE.get(grade)


def _build_features(payload):
    asistencias = validar_asistencias(payload.get("asistencias"))
    participacion = validar_participacion(payload.get("participacion"))
    nota_mat = validar_nota_literal(payload.get("nota_matematica"), "Matemática")
    nota_len = validar_nota_literal(payload.get("nota_lenguaje"), "Comunicación")
    nota_matematica = _normalize_grade(nota_mat)
    nota_lenguaje = _normalize_grade(nota_len)

    return [[asistencias, float(nota_matematica), float(nota_lenguaje), participacion]]


def _validar_payload_predict(payload: dict) -> dict:
    if not payload.get("dni"):
        raise ValueError("El DNI del estudiante es obligatorio.")
    dni = normalizar_dni(str(payload["dni"]))
    bimestre = validar_bimestre(payload.get("bimestre") or 1)
    asistencias = validar_asistencias(payload.get("asistencias"))
    participacion = validar_participacion(payload.get("participacion"))
    nota_matematica = validar_nota_literal(payload.get("nota_matematica"), "Matemática")
    nota_lenguaje = validar_nota_literal(payload.get("nota_lenguaje"), "Comunicación")
    return {
        **payload,
        "dni": dni,
        "bimestre": bimestre,
        "asistencias": asistencias,
        "participacion": participacion,
        "nota_matematica": nota_matematica,
        "nota_lenguaje": nota_lenguaje,
    }


def _load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


model = _load_model()


def _resolve_seccion_scope():
    """Devuelve (seccion_id, tutor_docente_id) segun rol y query params."""
    user = get_current_user()
    seccion_id = request.args.get("seccion_id", type=int)
    tutor_docente_id = None

    if user and user.get("rol") == "docente" and user.get("docente_id"):
        docente_id = int(user["docente_id"])
        if seccion_id is not None:
            if not seccion_pertenece_tutor(seccion_id, docente_id):
                return None, None, (
                    jsonify({"error": "No tienes acceso a esa sección."}),
                    403,
                )
        else:
            tutor_docente_id = docente_id

    return seccion_id, tutor_docente_id, None


def _resolve_seccion_scope_from_payload(payload: dict):
    user = get_current_user()
    seccion_id = payload.get("seccion_id")
    if seccion_id is not None:
        seccion_id = int(seccion_id)

    if user and user.get("rol") == "docente" and user.get("docente_id") and seccion_id:
        if not seccion_pertenece_tutor(seccion_id, int(user["docente_id"])):
            return None, (jsonify({"error": "No puedes matricular en esa sección."}), 403)

    return seccion_id, None


def _reparar_matriculas_docente_actual() -> None:
    consolidar_alertas_duplicadas()
    user = get_current_user()
    if user and user.get("rol") == "docente" and user.get("docente_id"):
        reparar_matriculas_pendientes_tutor(int(user["docente_id"]))


def _asegurar_matricula_docente(
    estudiante_id: int,
    anio_escolar_id: int,
    payload: dict,
) -> int | None:
    """Asigna matricula si el alumno no tiene y el docente tiene seccion."""
    matricula_id = obtener_matricula_id_activa(estudiante_id, anio_escolar_id)
    if matricula_id is not None:
        return matricula_id

    seccion_id = payload.get("seccion_id")
    if seccion_id is not None:
        return matricular_estudiante(estudiante_id, int(seccion_id), anio_escolar_id)

    user = get_current_user()
    if user and user.get("rol") == "docente" and user.get("docente_id"):
        secciones = obtener_seccion_ids_tutor(int(user["docente_id"]))
        if secciones:
            return matricular_estudiante(estudiante_id, secciones[0], anio_escolar_id)
    return None


def _user_secciones_payload(user: dict | None) -> list[dict]:
    secciones = listar_secciones_activas()
    if user and user.get("docente_id"):
        docente_id = int(user["docente_id"])
        mis = [item for item in secciones if item.get("tutor_id") == docente_id]
        for item in secciones:
            item["es_mi_seccion"] = item.get("tutor_id") == docente_id
        return mis
    for item in secciones:
        item["es_mi_seccion"] = False
    return secciones


def _normalize_column_name(column_name):
    return str(column_name).strip().lower().replace(" ", "_")


def _risk_level_from_probability(high_risk_probability):
    return nivel_riesgo_desde_probabilidad(high_risk_probability)


def _analizar_riesgo(payload: dict, features: list) -> dict:
    proba = model.predict_proba(features)[0]
    prediction_raw = int(model.predict(features)[0])
    confidence = float(proba[prediction_raw])
    proba_ml = float(proba[1])
    evaluacion = evaluar_riesgo_pedagogico(
        float(payload["asistencias"]),
        str(payload["nota_matematica"]),
        str(payload["nota_lenguaje"]),
        float(payload["participacion"]),
        proba_ml,
    )
    return {
        "prediction_raw": prediction_raw,
        "confidence": confidence,
        **evaluacion,
    }


def _extract_field(row, options):
    for key in options:
        if key in row and pd.notna(row[key]):
            return row[key]
    return None


def _split_nombre_completo(nombre: str) -> tuple[str, str, str]:
    parts = [part for part in nombre.strip().split() if part]
    if not parts:
        return "Sin nombre", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " ".join(parts[2:])


def _extract_student_name(payload: dict, fallback: str = "") -> str:
    for key in ("nombre", "estudiante_nombre", "estudiante"):
        value = payload.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return fallback.strip()


def _resolve_student_identity(payload: dict) -> tuple[int | None, str, str | None]:
    """Devuelve (estudiante_id o None, nombre_completo, dni)."""
    if payload.get("estudiante_id"):
        student = obtener_estudiante(int(payload["estudiante_id"]))
        if student is None:
            raise ValueError("Estudiante no encontrado.")
        nombre = " ".join(
            part
            for part in [
                student["nombres"],
                student.get("apellido_paterno", ""),
                student.get("apellido_materno", ""),
            ]
            if part
        )
        return student["id"], nombre, student.get("dni")

    dni = str(payload.get("dni") or "").strip() or None
    if dni:
        dni = normalizar_dni(dni)
    nombre = _extract_student_name(payload)

    if dni:
        found = buscar_estudiante_por_dni(dni)
        if found:
            return found["id"], found["nombre"], dni
        if not nombre:
            raise ValueError(
                f"No hay alumno con DNI {dni}. Registralo primero en Registrar alumno."
            )

    if not nombre and not dni:
        raise ValueError("Ingresa el DNI del alumno o registra uno nuevo antes de analizar.")

    if not nombre:
        raise ValueError("Ingresa el nombre completo junto con el DNI para registrar al alumno.")

    return None, nombre, dni


def _persist_prediction_record(
    nombre_completo: str,
    payload: dict,
    prediction_label: str,
    confidence: float,
    proba_high_risk: float,
    origen: str = "manual",
    carga_siagie_id: int | None = None,
    estudiante_id: int | None = None,
) -> dict:
    if not nombre_completo:
        return {"persisted": False, "reason": "sin_nombre"}

    nombres, apellido_paterno, apellido_materno = _split_nombre_completo(nombre_completo)

    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
    if anio_escolar_id is None:
        return {"persisted": False, "reason": "sin_anio_escolar"}

    if estudiante_id is None:
        estudiante_id = buscar_o_crear_estudiante(
            nombres=nombres,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            dni=str(payload.get("dni")).strip() if payload.get("dni") else None,
        )
    bimestre = int(payload.get("bimestre") or 1)
    matricula_id = _asegurar_matricula_docente(estudiante_id, anio_escolar_id, payload)
    evaluacion_id = guardar_evaluacion(
        estudiante_id=estudiante_id,
        anio_escolar_id=anio_escolar_id,
        asistencias=float(payload.get("asistencias", 0)),
        nota_matematica=str(payload.get("nota_matematica", "C")),
        nota_lenguaje=str(payload.get("nota_lenguaje", "C")),
        participacion=float(payload.get("participacion", 0)),
        bimestre=bimestre,
        origen=origen,
        matricula_id=matricula_id,
        carga_siagie_id=carga_siagie_id,
    )
    nivel_riesgo = _risk_level_from_probability(proba_high_risk)
    prediccion_id = guardar_prediccion(
        estudiante_id=estudiante_id,
        probabilidad_alto=proba_high_risk,
        nivel_riesgo=nivel_riesgo,
        etiqueta=prediction_label,
        confianza=confidence,
        evaluacion_id=evaluacion_id,
    )
    alerta_id = guardar_alerta_riesgo(
        estudiante_id=estudiante_id,
        prediccion_id=prediccion_id,
        nivel_riesgo=nivel_riesgo,
        motivo=f"Predicción {origen}: {prediction_label}",
    )

    competencias_guardadas: list[dict] = []
    competencias_payload = payload.get("competencias")
    if isinstance(competencias_payload, dict) and competencias_payload:
        try:
            competencias_guardadas = guardar_competencias_notas(evaluacion_id, competencias_payload)
        except ValueError:
            pass

    return {
        "persisted": True,
        "estudiante_id": estudiante_id,
        "evaluacion_id": evaluacion_id,
        "prediccion_id": prediccion_id,
        "alerta_id": alerta_id,
        "nivel_riesgo": nivel_riesgo,
        "nombre": nombre_completo,
        "competencias_guardadas": len(competencias_guardadas),
    }


@app.post("/api/auth/login")
def api_auth_login():
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password") or "")

    try:
        username = validar_username(str(payload.get("username") or ""))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if not password:
        return jsonify({"error": "La contraseña es obligatoria."}), 400
    if len(password) < 4:
        return jsonify({"error": "La contraseña debe tener al menos 4 caracteres."}), 400

    user = autenticar_usuario(username, password)
    if user is None:
        return jsonify({"error": "Credenciales inválidas."}), 401

    token = create_access_token(user)
    mis_secciones = _user_secciones_payload(user)
    return jsonify(
        {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "rol": user["rol"],
                "docente_id": user.get("docente_id"),
                "nombre_completo": user.get("nombre_completo"),
                "cargo": user.get("cargo"),
                "secciones": mis_secciones,
            },
        }
    )


@app.post("/api/auth/recuperar")
def api_auth_recuperar():
    payload = request.get_json(silent=True) or {}
    username_raw = str(payload.get("username") or "").strip()

    try:
        telefono = validar_telefono(str(payload.get("telefono") or ""))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if username_raw:
        try:
            validar_username(username_raw)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "pendiente": True,
            "message": (
                "Solicitud registrada. Próximamente recibirás un código SMS "
                f"al teléfono {telefono[-4:].rjust(len(telefono), '*')} "
                "para restablecer tu contraseña."
            ),
        }
    )


@app.get("/api/auth/me")
def api_auth_me():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "No autorizado."}), 401
    return jsonify(
        {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "rol": user["rol"],
                "docente_id": user.get("docente_id"),
                "nombre_completo": user.get("nombre_completo"),
                "cargo": user.get("cargo"),
                "secciones": _user_secciones_payload(user),
            }
        }
    )


@app.get("/api/secciones")
def api_secciones():
    user = get_current_user()
    secciones = listar_secciones_activas()
    mis_secciones = _user_secciones_payload(user)
    anio_escolar = secciones[0]["anio_escolar"] if secciones else None
    for item in secciones:
        item["es_mi_seccion"] = bool(
            user
            and user.get("docente_id")
            and item.get("tutor_id") == user.get("docente_id")
        )
    return jsonify(
        {
            "secciones": secciones,
            "mis_secciones": mis_secciones,
            "anio_escolar": anio_escolar,
            "total": len(secciones),
        }
    )


@app.get("/api/admin/resumen-bd")
@require_roles("admin")
def api_admin_resumen_bd():
    return jsonify({"tablas": obtener_conteo_tablas()})


@app.get("/api/admin/cargas-siagie")
@require_roles("admin")
def api_admin_cargas_siagie():
    cargas = listar_cargas_siagie()
    return jsonify({"cargas": cargas, "total": len(cargas)})


@app.get("/api/admin/usuarios")
@require_roles("admin")
def api_admin_usuarios():
    usuarios = listar_usuarios_sistema()
    return jsonify({"usuarios": usuarios, "total": len(usuarios)})


@app.get("/api/admin/docentes")
@require_roles("admin")
def api_admin_docentes():
    docentes = listar_docentes()
    return jsonify({"docentes": docentes, "total": len(docentes)})


@app.get("/api/admin/secciones")
@require_roles("admin")
def api_admin_secciones():
    secciones = listar_secciones_institucional()
    return jsonify({"secciones": secciones, "total": len(secciones)})


@app.delete("/api/admin/estudiantes/demo")
@require_roles("admin")
def api_admin_eliminar_demo():
    eliminados = eliminar_estudiantes_demo()
    return jsonify({"ok": True, "eliminados": eliminados})


@app.get("/api/admin/anio-escolar")
@require_roles("admin")
def api_admin_anio_escolar_get():
    anios = listar_anios_escolares()
    activo = next((item for item in anios if item.get("activo")), None)
    return jsonify({"anios": anios, "activo": activo})


@app.post("/api/admin/anio-escolar")
@require_roles("admin")
def api_admin_anio_escolar_post():
    payload = request.get_json(silent=True) or {}
    anio_escolar_id = payload.get("anio_escolar_id") or payload.get("id")
    if anio_escolar_id is None:
        return jsonify({"error": "Falta anio_escolar_id."}), 400
    try:
        anio_id = int(anio_escolar_id)
    except (TypeError, ValueError):
        return jsonify({"error": "anio_escolar_id inválido."}), 400
    try:
        activo = activar_anio_escolar(anio_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"ok": True, "activo": activo})


@app.get("/api/status")
def api_status():
    database = get_database_status()
    return jsonify(
        {
            "status": "ok",
            "message": "El motor de Edge-PRIDE está funcionando.",
            "model_loaded": model is not None,
            "database": {
                "ready": database["ready"],
                "schema_version": database["schema_version"],
                "table_count": database["table_count"],
            },
        }
    )


@app.get("/api/resumen")
def api_resumen():
    _reparar_matriculas_docente_actual()
    seccion_id, tutor_docente_id, error_response = _resolve_seccion_scope()
    if error_response:
        return error_response

    dashboard = obtener_resumen_dashboard(
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )
    ultima = dashboard["ultima_prediccion"]
    return jsonify(
        {
            "summary": dashboard["summary"],
            "total_estudiantes": dashboard["total_estudiantes"],
            "total_predicciones": dashboard["total_predicciones"],
            "alertas_activas": dashboard["alertas_activas"],
            "has_data": dashboard["total_predicciones"] > 0,
            "ultima_prediccion": ultima,
            "alertas_prioritarias": dashboard["alertas_prioritarias"],
        }
    )


@app.post("/api/estudiantes")
def api_registrar_estudiante():
    payload = request.get_json(silent=True) or {}
    try:
        dni = normalizar_dni(str(payload.get("dni") or ""))
        nombre = validar_nombre_completo(str(payload.get("nombre") or ""))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    seccion_id, error_response = _resolve_seccion_scope_from_payload(payload)
    if error_response:
        return error_response

    user = get_current_user()
    if (
        user
        and user.get("rol") == "docente"
        and user.get("docente_id")
        and not seccion_id
    ):
        secciones = obtener_seccion_ids_tutor(int(user["docente_id"]))
        if secciones:
            return jsonify({"error": "Selecciona la sección del alumno."}), 400

    try:
        estudiante = registrar_estudiante(
            nombre_completo=nombre,
            dni=dni,
            codigo_estudiante=payload.get("codigo_siagie"),
            seccion_id=seccion_id,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    apoderado_payload = payload.get("apoderado")
    apoderado = None
    if isinstance(apoderado_payload, dict):
        try:
            apoderado_nombre = validar_nombre_completo(
                str(apoderado_payload.get("nombre") or "").strip()
            )
            apoderado_telefono = validar_telefono(str(apoderado_payload.get("telefono") or ""))
            apoderado = guardar_apoderado_principal(
                estudiante_id=int(estudiante["id"]),
                nombre_completo=apoderado_nombre,
                telefono=apoderado_telefono,
                parentesco=validar_parentesco(apoderado_payload.get("parentesco")),
                dni=validar_dni_opcional(apoderado_payload.get("dni")),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    response_body = {"ok": True, "estudiante": estudiante}
    if apoderado:
        response_body["apoderado"] = apoderado
    return jsonify(response_body), 201


@app.get("/api/estudiantes/buscar")
def api_buscar_estudiante():
    dni_raw = (request.args.get("dni") or "").strip()
    if not dni_raw:
        return jsonify({"error": "Parámetro dni requerido."}), 400

    try:
        dni = normalizar_dni(dni_raw)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    estudiante = buscar_estudiante_por_dni(dni)
    if estudiante is None:
        return jsonify({"found": False, "dni": dni}), 404

    user = get_current_user()
    if user and user.get("rol") == "docente" and user.get("docente_id"):
        with get_connection() as connection:
            anio_id = get_active_anio_escolar_id(connection)
        if anio_id and not obtener_matricula_id_activa(estudiante["id"], anio_id):
            secciones = obtener_seccion_ids_tutor(int(user["docente_id"]))
            if secciones:
                matricular_estudiante(estudiante["id"], secciones[0], anio_id)
                estudiante = buscar_estudiante_por_dni(dni) or estudiante

    apoderado = obtener_apoderado_principal(estudiante["id"])
    if apoderado:
        estudiante["apoderado_nombre"] = apoderado["nombre"]
        estudiante["apoderado_telefono"] = apoderado["telefono"]
        estudiante["apoderado_parentesco"] = apoderado["parentesco"]
        estudiante["apoderado_dni"] = apoderado.get("dni")

    return jsonify({"found": True, "estudiante": estudiante})


@app.get("/api/estudiantes")
def api_estudiantes():
    _reparar_matriculas_docente_actual()
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    busqueda = (request.args.get("busqueda") or "").strip() or None
    riesgo = (request.args.get("riesgo") or "").strip() or None
    if riesgo and riesgo not in ("alto", "medio", "bajo"):
        return jsonify({"error": "riesgo debe ser alto, medio o bajo."}), 400

    seccion_id, tutor_docente_id, error_response = _resolve_seccion_scope()
    if error_response:
        return error_response

    estudiantes = listar_estudiantes_detallado(
        limit=limit,
        offset=offset,
        busqueda=busqueda,
        riesgo=riesgo,
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )
    total = contar_estudiantes_filtrados(
        busqueda=busqueda,
        riesgo=riesgo,
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )
    return jsonify({"estudiantes": estudiantes, "total": total, "mostrando": len(estudiantes)})


@app.get("/api/estudiantes/<int:estudiante_id>/apoderado")
def api_obtener_apoderado(estudiante_id: int):
    estudiante = obtener_estudiante(estudiante_id)
    if estudiante is None:
        return jsonify({"error": "Estudiante no encontrado."}), 404

    apoderado = obtener_apoderado_principal(estudiante_id)
    return jsonify({"apoderado": apoderado})


@app.post("/api/estudiantes/<int:estudiante_id>/apoderado")
def api_guardar_apoderado(estudiante_id: int):
    estudiante = obtener_estudiante(estudiante_id)
    if estudiante is None:
        return jsonify({"error": "Estudiante no encontrado."}), 404

    payload = request.get_json(silent=True) or {}
    try:
        nombre = validar_nombre_completo(str(payload.get("nombre") or ""))
        telefono = validar_telefono(str(payload.get("telefono") or ""))
        parentesco = validar_parentesco(payload.get("parentesco"))
        dni = validar_dni_opcional(payload.get("dni"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        apoderado = guardar_apoderado_principal(
            estudiante_id=estudiante_id,
            nombre_completo=nombre,
            telefono=telefono,
            parentesco=parentesco,
            dni=dni,
            telefono_alterno=payload.get("telefono_alterno"),
            email=payload.get("email"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "apoderado": apoderado}), 201


@app.delete("/api/estudiantes/invalidos")
def api_eliminar_estudiantes_invalidos():
    user = get_current_user()
    if not user or user.get("rol") not in ("admin", "docente"):
        return jsonify({"error": "No tienes permiso para esta acción."}), 403

    eliminados = eliminar_estudiantes_demo()
    return jsonify({"ok": True, "eliminados": eliminados})


def _build_indicadores_dataframe(indicadores: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Año": item.get("anio"),
                "Mes": item.get("mes"),
                "Sección": item.get("seccion_etiqueta") or "",
                "Total_Estudiantes": item.get("total_estudiantes"),
                "Promedio_Asistencia_%": item.get("promedio_asistencia"),
                "Pct_Riesgo_Alto": item.get("porcentaje_riesgo_alto"),
                "Pct_Riesgo_Medio": item.get("porcentaje_riesgo_medio"),
                "Pct_Riesgo_Bajo": item.get("porcentaje_riesgo_bajo"),
                "Total_Intervenciones": item.get("total_intervenciones"),
                "Total_Derivaciones": item.get("total_derivaciones"),
            }
            for item in indicadores
        ]
    )


def _build_reporte_dataframe(estudiantes: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "DNI": item.get("dni") or "",
                "Estudiante": item.get("nombre") or "",
                "Sección": item.get("seccion_etiqueta") or "",
                "Asistencia_%": item.get("asistencias"),
                "Nota_Matemática": item.get("nota_matematica"),
                "Nota_Comunicación": item.get("nota_lenguaje"),
                "Participación": item.get("participacion"),
                "Bimestre": item.get("bimestre"),
                "Nivel_Riesgo": item.get("ultimo_nivel_riesgo") or "sin_prediccion",
                "Etiqueta": item.get("ultima_etiqueta") or "",
                "Probabilidad_Alto": item.get("risk_score"),
                "Confianza": item.get("confianza"),
                "Última_predicción": item.get("ultima_prediccion") or "",
                "Origen_Datos": item.get("origen") or "",
            }
            for item in estudiantes
        ]
    )


@app.get("/api/reportes/exportar")
def api_exportar_reporte():
    busqueda = (request.args.get("busqueda") or "").strip() or None
    riesgo = (request.args.get("riesgo") or "").strip() or None
    formato = (request.args.get("formato") or "xlsx").lower()

    if riesgo and riesgo not in ("alto", "medio", "bajo"):
        return jsonify({"error": "riesgo debe ser alto, medio o bajo."}), 400
    if formato not in ("xlsx", "csv"):
        return jsonify({"error": "formato debe ser xlsx o csv."}), 400

    seccion_id, tutor_docente_id, error_response = _resolve_seccion_scope()
    if error_response:
        return error_response

    estudiantes = listar_estudiantes_detallado(
        limit=5000,
        busqueda=busqueda,
        riesgo=riesgo,
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )
    df = _build_reporte_dataframe(estudiantes)

    indicador_anio = request.args.get("anio", type=int)
    indicador_mes = request.args.get("mes", type=int)
    if indicador_anio is None or indicador_mes is None:
        hoy = datetime.now()
        indicador_anio = indicador_anio or hoy.year
        indicador_mes = indicador_mes or hoy.month

    seccion_ids_ind, incluir_institucion = _indicadores_scope_for_user()
    indicadores = listar_indicadores(
        anio=indicador_anio,
        mes=indicador_mes,
        seccion_ids=seccion_ids_ind,
        incluir_institucion=incluir_institucion,
    )["items"]
    df_indicadores = _build_indicadores_dataframe(indicadores)
    buffer = BytesIO()

    if formato == "csv":
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        if not df_indicadores.empty:
            buffer.write("\n\n")
            df_indicadores.to_csv(buffer, index=False, encoding="utf-8-sig")
        mimetype = "text/csv"
        filename = "reporte_estudiantes_predictedu.csv"
    else:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Estudiantes", index=False)
            if not df_indicadores.empty:
                df_indicadores.to_excel(writer, sheet_name="Indicadores", index=False)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "reporte_estudiantes_predictedu.xlsx"

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


def _indicadores_scope_for_user() -> tuple[list[int] | None, bool]:
    """Devuelve (seccion_ids, incluir_institucion). None en seccion_ids = todas las secciones."""
    user = get_current_user()
    if user and user.get("rol") == "admin":
        return None, True
    if user and user.get("docente_id"):
        return obtener_seccion_ids_tutor(int(user["docente_id"])), False
    return [], False


@app.get("/api/indicadores")
def api_indicadores_list():
    anio = request.args.get("anio", type=int)
    mes = request.args.get("mes", type=int)
    seccion_id = request.args.get("seccion_id", type=int)
    seccion_ids, incluir_institucion = _indicadores_scope_for_user()

    if seccion_id is not None and seccion_ids is not None and seccion_id not in seccion_ids:
        return jsonify({"error": "No tienes acceso a esa sección."}), 403

    resultado = listar_indicadores(
        anio=anio,
        mes=mes,
        seccion_id=seccion_id,
        seccion_ids=None if seccion_id is not None else seccion_ids,
        incluir_institucion=incluir_institucion and seccion_id is None,
    )
    return jsonify(
        {
            "indicadores": resultado["items"],
            "total": resultado["total"],
            "anio": anio,
            "mes": mes,
            "seccion_id": seccion_id,
            "alcance": "institucion" if incluir_institucion else "mis_secciones",
        }
    )


@app.post("/api/indicadores/calcular")
def api_indicadores_calcular():
    payload = request.get_json(silent=True) or {}
    anio = payload.get("anio")
    mes = payload.get("mes")
    seccion_ids, incluir_institucion = _indicadores_scope_for_user()

    try:
        indicadores = calcular_indicadores_mensuales(
            anio=int(anio) if anio is not None else None,
            mes=int(mes) if mes is not None else None,
            seccion_ids=seccion_ids,
            incluir_institucion=incluir_institucion,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "indicadores": indicadores,
            "total": len(indicadores),
            "alcance": "institucion" if incluir_institucion else "mis_secciones",
        }
    ), 201


@app.post("/api/asistencias-diarias")
def api_asistencias_diarias_create():
    payload = request.get_json(silent=True) or {}
    registros = payload.get("registros") or payload.get("asistencias")
    if not isinstance(registros, list) or not registros:
        return jsonify({"error": "registros debe ser una lista no vacía."}), 400

    user = get_current_user()
    if user and user.get("rol") == "docente" and user.get("docente_id"):
        docente_id = int(user["docente_id"])
        for item in registros:
            estudiante_id = int(item["estudiante_id"])
            estudiante = obtener_estudiante(estudiante_id)
            if estudiante is None:
                return jsonify({"error": f"Estudiante {estudiante_id} no encontrado."}), 400
            matricula_id = item.get("matricula_id")
            if matricula_id:
                with get_connection() as connection:
                    row = connection.execute(
                        """
                        SELECT s.id AS seccion_id
                        FROM matriculas m
                        JOIN secciones s ON s.id = m.seccion_id
                        WHERE m.id = ?
                        """,
                        (int(matricula_id),),
                    ).fetchone()
                if row and not seccion_pertenece_tutor(int(row["seccion_id"]), docente_id):
                    return jsonify({"error": "No puedes registrar asistencia de otra sección."}), 403

    try:
        resultado = registrar_asistencias_diarias(registros)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, **resultado}), 201


@app.get("/api/evaluaciones/<int:evaluacion_id>/competencias")
def api_evaluacion_competencias(evaluacion_id: int):
    return jsonify({"competencias": listar_competencias_evaluacion(evaluacion_id)})


def _parse_fecha_iso(value: str | None, campo: str) -> str | None:
    if not value:
        return None
    fecha = str(value).strip()
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(f"{campo} debe tener formato AAAA-MM-DD.") from error
    return fecha


@app.get("/api/intervenciones")
def api_intervenciones_list():
    limit = max(1, min(request.args.get("limit", default=50, type=int) or 50, 200))
    try:
        fecha_desde = _parse_fecha_iso(request.args.get("desde"), "desde")
        fecha_hasta = _parse_fecha_iso(request.args.get("hasta"), "hasta")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        return jsonify({"error": "La fecha desde no puede ser posterior a hasta."}), 400

    resultado = listar_intervenciones(
        limit=limit,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return jsonify(
        {
            "intervenciones": resultado["items"],
            "total": resultado["total"],
            "desde": fecha_desde,
            "hasta": fecha_hasta,
            "limit": limit,
        }
    )


@app.post("/api/intervenciones")
def api_intervenciones_create():
    payload = request.get_json(silent=True) or {}
    estudiante_id = payload.get("estudiante_id")
    if not estudiante_id:
        return jsonify({"error": "estudiante_id es requerido."}), 400

    titulo = str(payload.get("titulo") or "Seguimiento registrado desde PredictEdu").strip()
    user = get_current_user()
    docente_id = user.get("docente_id") if user and user.get("docente_id") else None
    try:
        intervencion_id = registrar_intervencion(
            estudiante_id=int(estudiante_id),
            titulo=titulo,
            tipo=str(payload.get("tipo") or "contacto_familia"),
            descripcion=payload.get("descripcion"),
            prediccion_id=payload.get("prediccion_id"),
            docente_id=docente_id,
        )
        alertas_atendidas = atender_alertas_estudiante(
            int(estudiante_id),
            accion="registro_intervencion",
            detalle=str(payload.get("descripcion") or titulo),
            docente_id=docente_id,
            alerta_id=payload.get("alerta_id"),
        )
    except Exception as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "intervencion_id": intervencion_id,
            "alertas_atendidas": alertas_atendidas,
        }
    ), 201


@app.patch("/api/intervenciones/<int:intervencion_id>")
def api_intervenciones_update(intervencion_id: int):
    payload = request.get_json(silent=True) or {}
    estado = str(payload.get("estado") or "").strip()
    if not estado:
        return jsonify({"error": "estado es requerido."}), 400

    try:
        updated = actualizar_estado_intervencion(intervencion_id, estado)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if not updated:
        return jsonify({"error": "Intervención no encontrada."}), 404

    return jsonify({"ok": True, "intervencion_id": intervencion_id, "estado": estado})


@app.get("/api/alertas/<int:alerta_id>/historial")
def api_alerta_historial(alerta_id: int):
    alerta = obtener_alerta_por_id(alerta_id)
    if alerta is None:
        return jsonify({"error": "Alerta no encontrada."}), 404

    seguimiento = listar_seguimiento_alerta(alerta_id)
    return jsonify({"alerta": alerta, "seguimiento": seguimiento})


@app.post("/api/alertas/<int:alerta_id>/seguimiento")
def api_alerta_seguimiento(alerta_id: int):
    alerta = obtener_alerta_por_id(alerta_id)
    if alerta is None:
        return jsonify({"error": "Alerta no encontrada."}), 404

    payload = request.get_json(silent=True) or {}
    accion = str(payload.get("accion") or "").strip()
    if not accion:
        return jsonify({"error": "acción es requerida."}), 400

    detalle = payload.get("detalle")
    resultado = payload.get("resultado")
    nuevo_estado = str(payload.get("estado") or "").strip() or None
    if nuevo_estado and nuevo_estado not in ("en_revision", "atendida", "cerrada"):
        return jsonify({"error": "estado debe ser en_revision, atendida o cerrada."}), 400

    user = get_current_user()
    docente_id = user.get("docente_id") if user and user.get("docente_id") else None

    try:
        seguimiento_id = registrar_seguimiento_alerta(
            alerta_id=alerta_id,
            accion=accion,
            detalle=detalle,
            docente_id=docente_id,
            resultado=resultado,
            nuevo_estado=nuevo_estado,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "seguimiento_id": seguimiento_id,
            "alerta": obtener_alerta_por_id(alerta_id),
        }
    ), 201


@app.patch("/api/alertas/<int:alerta_id>")
def api_alerta_actualizar(alerta_id: int):
    alerta = obtener_alerta_por_id(alerta_id)
    if alerta is None:
        return jsonify({"error": "Alerta no encontrada."}), 404

    payload = request.get_json(silent=True) or {}
    estado = str(payload.get("estado") or "").strip()
    if not estado:
        return jsonify({"error": "estado es requerido."}), 400

    accion = str(payload.get("accion") or f"cambio_estado_{estado}").strip()
    detalle = payload.get("detalle")
    user = get_current_user()
    docente_id = user.get("docente_id") if user and user.get("docente_id") else None

    try:
        registrar_seguimiento_alerta(
            alerta_id=alerta_id,
            accion=accion,
            detalle=detalle,
            docente_id=docente_id,
            nuevo_estado=estado,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "alerta": obtener_alerta_por_id(alerta_id)})


@app.get("/api/cursos-reforzamiento")
def api_cursos_reforzamiento_list():
    cursos = listar_cursos_reforzamiento()
    return jsonify({"cursos": cursos, "total": len(cursos)})


@app.get("/api/cursos-reforzamiento/<int:curso_id>")
def api_curso_reforzamiento_detalle(curso_id: int):
    curso = obtener_curso_reforzamiento(curso_id)
    if curso is None:
        return jsonify({"error": "Curso no encontrado."}), 404

    return jsonify(
        {
            "curso": curso,
            "inscripciones": listar_inscripciones_curso(curso_id),
            "sesiones": listar_sesiones_curso(curso_id),
            "materiales": listar_materiales_curso(curso_id),
        }
    )


@app.post("/api/cursos-reforzamiento/<int:curso_id>/inscripciones")
def api_curso_inscripciones(curso_id: int):
    payload = request.get_json(silent=True) or {}
    estudiante_id = payload.get("estudiante_id")
    if not estudiante_id:
        return jsonify({"error": "estudiante_id es requerido."}), 400

    try:
        inscripcion = inscribir_estudiante_reforzamiento(
            curso_id=curso_id,
            estudiante_id=int(estudiante_id),
            prediccion_id=payload.get("prediccion_id"),
            motivo=str(payload.get("motivo") or "otro"),
            observaciones=payload.get("observaciones"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "inscripcion": inscripcion}), 201


@app.post("/api/cursos-reforzamiento/<int:curso_id>/sesiones")
def api_curso_sesiones(curso_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        sesion = registrar_sesion_reforzamiento(
            curso_id=curso_id,
            fecha_sesion=str(payload.get("fecha_sesion") or ""),
            tema=str(payload.get("tema") or ""),
            modalidad=str(payload.get("modalidad") or "presencial"),
            asistencia_registrada=int(payload.get("asistencia_registrada") or 0),
            observaciones=payload.get("observaciones"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "sesion": sesion}), 201


@app.get("/api/cursos-reforzamiento/<int:curso_id>/materiales")
def api_curso_materiales_list(curso_id: int):
    if obtener_curso_reforzamiento(curso_id) is None:
        return jsonify({"error": "Curso no encontrado."}), 404
    return jsonify({"materiales": listar_materiales_curso(curso_id)})


@app.post("/api/cursos-reforzamiento/<int:curso_id>/materiales")
def api_curso_materiales_create(curso_id: int):
    if obtener_curso_reforzamiento(curso_id) is None:
        return jsonify({"error": "Curso no encontrado."}), 404

    user = get_current_user()
    docente_id = user.get("docente_id") if user and user.get("docente_id") else None

    if request.files and request.files.get("file"):
        archivo = request.files["file"]
        titulo = str(request.form.get("titulo") or archivo.filename or "Material").strip()
        if len(titulo) < 3:
            return jsonify({"error": "El título del material debe tener al menos 3 caracteres."}), 400

        try:
            nombre_seguro = _validar_archivo_reforzamiento(archivo)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        REFORZAMIENTO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        destino = REFORZAMIENTO_UPLOAD_DIR / f"curso_{curso_id}_{nombre_seguro}"
        archivo.save(destino)

        try:
            material = crear_material_reforzamiento(
                curso_id=curso_id,
                tipo="archivo",
                titulo=titulo,
                docente_id=docente_id,
                ruta_archivo=str(destino),
                nombre_archivo=nombre_seguro,
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"ok": True, "material": material}), 201

    payload = request.get_json(silent=True) or {}
    try:
        material = crear_material_reforzamiento(
            curso_id=curso_id,
            tipo="enlace",
            titulo=str(payload.get("titulo") or ""),
            docente_id=docente_id,
            url=str(payload.get("url") or "").strip(),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "material": material}), 201


@app.get("/api/materiales-reforzamiento/<int:material_id>/descargar")
def api_material_reforzamiento_descargar(material_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT titulo, ruta_archivo, nombre_archivo, tipo
            FROM materiales_reforzamiento
            WHERE id = ?
            """,
            (material_id,),
        ).fetchone()

    if row is None or row["tipo"] != "archivo" or not row["ruta_archivo"]:
        return jsonify({"error": "Material no encontrado."}), 404

    ruta = Path(row["ruta_archivo"])
    if not ruta.is_file():
        return jsonify({"error": "Archivo no disponible en el servidor."}), 404

    return send_file(
        ruta,
        as_attachment=True,
        download_name=row["nombre_archivo"] or ruta.name,
    )


@app.patch("/api/inscripciones/<int:inscripcion_id>")
def api_inscripcion_actualizar(inscripcion_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        inscripcion = actualizar_inscripcion_reforzamiento(
            inscripcion_id=inscripcion_id,
            resultado=payload.get("resultado"),
            observaciones=payload.get("observaciones"),
            asistencias_taller=payload.get("asistencias_taller"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if inscripcion is None:
        return jsonify({"error": "Inscripción no encontrada."}), 404

    return jsonify({"ok": True, "inscripcion": inscripcion})


@app.get("/api/derivaciones")
def api_derivaciones_list():
    limit = max(1, min(request.args.get("limit", default=50, type=int) or 50, 200))
    estado = request.args.get("estado")
    estudiante_id = request.args.get("estudiante_id", type=int)

    try:
        resultado = listar_derivaciones(
            estado=estado,
            estudiante_id=estudiante_id,
            limit=limit,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "derivaciones": resultado["items"],
            "total": resultado["total"],
            "estado": estado,
            "estudiante_id": estudiante_id,
            "limit": limit,
        }
    )


@app.post("/api/derivaciones")
def api_derivaciones_create():
    payload = request.get_json(silent=True) or {}
    estudiante_id = payload.get("estudiante_id")
    if not estudiante_id:
        return jsonify({"error": "estudiante_id es requerido."}), 400

    try:
        derivacion = crear_derivacion_externa(
            estudiante_id=int(estudiante_id),
            entidad_destino=str(payload.get("entidad_destino") or ""),
            motivo=str(payload.get("motivo") or ""),
            intervencion_id=payload.get("intervencion_id"),
            observaciones=payload.get("observaciones"),
            fecha_derivacion=payload.get("fecha_derivacion"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "derivacion": derivacion}), 201


@app.patch("/api/derivaciones/<int:derivacion_id>")
def api_derivaciones_update(derivacion_id: int):
    payload = request.get_json(silent=True) or {}
    estado = str(payload.get("estado") or "").strip()
    if not estado:
        return jsonify({"error": "estado es requerido."}), 400

    try:
        derivacion = actualizar_derivacion(
            derivacion_id=derivacion_id,
            estado=estado,
            fecha_respuesta=payload.get("fecha_respuesta"),
            observaciones=payload.get("observaciones"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if derivacion is None:
        return jsonify({"error": "Derivación no encontrada."}), 404

    return jsonify({"ok": True, "derivacion": derivacion})


@app.get("/api/incidencias")
def api_incidencias_list():
    limit = max(1, min(request.args.get("limit", default=50, type=int) or 50, 200))
    severidad = request.args.get("severidad")
    tipo_incidencia = request.args.get("tipo")
    estudiante_id = request.args.get("estudiante_id", type=int)

    try:
        resultado = listar_incidencias(
            severidad=severidad,
            tipo_incidencia=tipo_incidencia,
            estudiante_id=estudiante_id,
            limit=limit,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "incidencias": resultado["items"],
            "total": resultado["total"],
            "severidad": severidad,
            "tipo": tipo_incidencia,
            "estudiante_id": estudiante_id,
            "limit": limit,
        }
    )


@app.post("/api/incidencias")
def api_incidencias_create():
    payload = request.get_json(silent=True) or {}
    estudiante_id = payload.get("estudiante_id")
    if not estudiante_id:
        return jsonify({"error": "estudiante_id es requerido."}), 400

    user = get_current_user()
    docente_id = user.get("docente_id") if user and user.get("docente_id") else None

    try:
        incidencia = crear_incidencia_convivencia(
            estudiante_id=int(estudiante_id),
            tipo_incidencia=str(payload.get("tipo_incidencia") or ""),
            descripcion=str(payload.get("descripcion") or ""),
            severidad=str(payload.get("severidad") or "media"),
            acciones_tomadas=payload.get("acciones_tomadas"),
            fecha_incidencia=payload.get("fecha_incidencia"),
            docente_reporta_id=docente_id,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "incidencia": incidencia}), 201


@app.get("/api/estudiantes/<int:estudiante_id>/incidencias")
def api_estudiante_incidencias(estudiante_id: int):
    if obtener_estudiante(estudiante_id) is None:
        return jsonify({"error": "Estudiante no encontrado."}), 404

    severidad = request.args.get("severidad")
    limit = max(1, min(request.args.get("limit", default=50, type=int) or 50, 200))

    try:
        resultado = listar_incidencias(
            estudiante_id=estudiante_id,
            severidad=severidad,
            limit=limit,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "estudiante_id": estudiante_id,
            "incidencias": resultado["items"],
            "total": resultado["total"],
            "severidad": severidad,
        }
    )


@app.post("/api/predict")
def api_predict():
    payload = request.get_json(silent=True) or {}

    if model is None:
        return (
            jsonify(
                {
                    "error": "Modelo no encontrado. Ejecuta primero ml_models/train_model.py",
                }
            ),
            500,
        )

    try:
        payload = _validar_payload_predict(payload)
        features = _build_features(payload)
        analisis = _analizar_riesgo(payload, features)
        prediction_label = analisis["etiqueta"]
        confidence = analisis["confidence"]
        proba_high_risk = analisis["probabilidad_alto"]
    except ValueError as validation_error:
        return jsonify({"error": str(validation_error)}), 400
    except Exception as model_error:
        return jsonify({"error": f"Error en inferencia: {model_error}"}), 500

    try:
        estudiante_id, nombre, dni = _resolve_student_identity(payload)
        if dni:
            payload = {**payload, "dni": dni}
        storage = _persist_prediction_record(
            nombre_completo=nombre,
            payload=payload,
            prediction_label=prediction_label,
            confidence=confidence,
            proba_high_risk=proba_high_risk,
            origen="manual",
            estudiante_id=estudiante_id,
        )
    except ValueError as validation_error:
        return jsonify({"error": str(validation_error)}), 400
    except Exception as storage_error:
        storage = {
            "persisted": False,
            "error": f"No se pudo guardar en la base de datos: {storage_error}",
        }

    response = {
        "received": payload,
        "prediction": prediction_label,
        "confidence": round(confidence, 4),
        "probabilidad_alto": analisis["probabilidad_alto"],
        "probabilidad_ml": analisis["probabilidad_ml"],
        "model": "Random Forest + criterios pedagógicos",
        "scale": "Notas literales peruanas: AD, A, B, C",
        "nivel_riesgo": analisis["nivel_riesgo"],
        "factores": analisis["factores"],
        "storage": storage,
    }
    return jsonify(response)


@app.post("/api/upload_siagie")
def api_upload_siagie():
    if model is None:
        return (
            jsonify(
                {
                    "error": "Modelo no encontrado. Ejecuta primero ml_models/train_model.py",
                }
            ),
            500,
        )

    if "file" not in request.files:
        return jsonify({"error": "No se envió archivo en el campo 'file'."}), 400

    excel_file = request.files["file"]
    if not excel_file.filename:
        return jsonify({"error": "Archivo inválido."}), 400

    try:
        df = pd.read_excel(excel_file)
    except Exception as excel_error:
        return jsonify({"error": f"No se pudo leer el Excel: {excel_error}"}), 400

    if df.empty:
        return jsonify({"error": "El archivo Excel no contiene filas."}), 400

    df.columns = [_normalize_column_name(col) for col in df.columns]
    total_filas = len(df)

    processed_students = []
    filas_error = 0
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        dni = _extract_field(row_dict, ["dni", "documento", "numero_documento"])
        nombre = _extract_field(
            row_dict,
            ["nombre", "estudiante", "alumno", "nombres_apellidos"],
        ) or "Sin nombre"

        payload = {
            "dni": str(dni).strip() if dni is not None and pd.notna(dni) else None,
            "asistencias": _extract_field(
                row_dict, ["asistencias", "asistencia", "porcentaje_asistencia"]
            ),
            "nota_matematica": _extract_field(
                row_dict, ["nota_matematica", "matematica", "competencia_matematica"]
            ),
            "nota_lenguaje": _extract_field(
                row_dict, ["nota_lenguaje", "lenguaje", "comunicacion"]
            ),
            "participacion": _extract_field(row_dict, ["participacion", "participación"]),
        }

        try:
            features = _build_features(payload)
            analisis = _analizar_riesgo(payload, features)
        except Exception:
            filas_error += 1
            continue

        risk_level = analisis["nivel_riesgo"]
        proba_high_risk = analisis["probabilidad_alto"]
        confidence = analisis["confidence"]
        processed_students.append(
            {
                "nombre": str(nombre),
                "dni": payload.get("dni"),
                "asistencias": float(payload["asistencias"]),
                "nota_matematica": str(payload["nota_matematica"]).upper(),
                "nota_lenguaje": str(payload["nota_lenguaje"]).upper(),
                "participacion": float(payload["participacion"]),
                "risk_level": risk_level,
                "risk_score": round(proba_high_risk, 4),
                "_confidence": confidence,
                "_prediction_label": analisis["etiqueta"],
            }
        )

    if not processed_students:
        return (
            jsonify(
                {
                    "error": "No se pudieron procesar filas. Verifica columnas requeridas: asistencias, nota_matematica, nota_lenguaje, participacion.",
                }
            ),
            400,
        )

    current_user = get_current_user()
    subido_por_id = current_user.get("id") if current_user and current_user.get("id") else None
    carga_id = registrar_carga_siagie(
        nombre_archivo=excel_file.filename,
        total_filas=total_filas,
        filas_procesadas=len(processed_students),
        filas_error=filas_error,
        subido_por_id=subido_por_id,
    )

    persisted_count = 0
    for student in processed_students:
        try:
            row_payload = {
                "dni": student.get("dni"),
                "asistencias": student["asistencias"],
                "nota_matematica": student["nota_matematica"],
                "nota_lenguaje": student["nota_lenguaje"],
                "participacion": student["participacion"],
            }
            estudiante_id = None
            if student.get("dni"):
                found = buscar_estudiante_por_dni(student["dni"])
                if found:
                    estudiante_id = found["id"]
            result = _persist_prediction_record(
                nombre_completo=student["nombre"],
                payload=row_payload,
                prediction_label=student["_prediction_label"],
                confidence=student["_confidence"],
                proba_high_risk=student["risk_score"],
                origen="siagie",
                carga_siagie_id=carga_id,
                estudiante_id=estudiante_id,
            )
            if result.get("persisted"):
                persisted_count += 1
                student["estudiante_id"] = result["estudiante_id"]
                student["prediccion_id"] = result["prediccion_id"]
        except Exception:
            continue

    summary = {"alto": 0, "medio": 0, "bajo": 0}
    for student in processed_students:
        summary[student["risk_level"]] += 1

    top_5_high_risk = sorted(
        processed_students,
        key=lambda item: item["risk_score"],
        reverse=True,
    )[:5]

    for student in top_5_high_risk:
        student.pop("_confidence", None)
        student.pop("_prediction_label", None)

    return jsonify(
        {
            "summary": summary,
            "total_students": len(processed_students),
            "top_5_high_risk": top_5_high_risk,
            "storage": {
                "persisted": persisted_count > 0,
                "carga_siagie_id": carga_id,
                "filas_guardadas": persisted_count,
                "filas_error": filas_error,
            },
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
