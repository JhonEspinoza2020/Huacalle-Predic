import sys
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS

_SIDECAR_ROOT = Path(__file__).resolve().parent
if str(_SIDECAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIDECAR_ROOT))

from auth_guard import auth_is_public, get_current_user, require_roles
from auth_tokens import create_access_token
from database.repository import (
    autenticar_usuario,
    buscar_estudiante_por_dni,
    buscar_o_crear_estudiante,
    contar_estudiantes_filtrados,
    eliminar_estudiantes_demo,
    get_active_anio_escolar_id,
    get_connection,
    get_database_status,
    guardar_alerta_riesgo,
    guardar_evaluacion,
    guardar_prediccion,
    init_database,
    listar_cargas_siagie,
    listar_docentes,
    listar_estudiantes_detallado,
    listar_intervenciones,
    listar_secciones_institucional,
    listar_usuarios_sistema,
    obtener_conteo_tablas,
    obtener_estudiante,
    obtener_resumen_dashboard,
    registrar_carga_siagie,
    registrar_estudiante,
    registrar_intervencion,
)

app = Flask(__name__)
CORS(app)

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
        return jsonify({"error": "No autorizado. Inicia sesion."}), 401
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
    nota_matematica = _normalize_grade(payload.get("nota_matematica"))
    nota_lenguaje = _normalize_grade(payload.get("nota_lenguaje"))

    if nota_matematica is None or nota_lenguaje is None:
        raise ValueError("Las notas deben ser literales: AD, A, B o C.")

    return [[
        float(payload.get("asistencias", 0)),
        float(nota_matematica),
        float(nota_lenguaje),
        float(payload.get("participacion", 0)),
    ]]


def _load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


model = _load_model()


def _normalize_column_name(column_name):
    return str(column_name).strip().lower().replace(" ", "_")


def _risk_level_from_probability(high_risk_probability):
    if high_risk_probability >= 0.7:
        return "alto"
    if high_risk_probability >= 0.45:
        return "medio"
    return "bajo"


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
    evaluacion_id = guardar_evaluacion(
        estudiante_id=estudiante_id,
        anio_escolar_id=anio_escolar_id,
        asistencias=float(payload.get("asistencias", 0)),
        nota_matematica=str(payload.get("nota_matematica", "C")),
        nota_lenguaje=str(payload.get("nota_lenguaje", "C")),
        participacion=float(payload.get("participacion", 0)),
        bimestre=bimestre,
        origen=origen,
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
        motivo=f"Prediccion {origen}: {prediction_label}",
    )

    return {
        "persisted": True,
        "estudiante_id": estudiante_id,
        "evaluacion_id": evaluacion_id,
        "prediccion_id": prediccion_id,
        "alerta_id": alerta_id,
        "nivel_riesgo": nivel_riesgo,
        "nombre": nombre_completo,
    }


@app.post("/api/auth/login")
def api_auth_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")

    if not username or not password:
        return jsonify({"error": "Usuario y contrasena son obligatorios."}), 400

    user = autenticar_usuario(username, password)
    if user is None:
        return jsonify({"error": "Credenciales invalidas."}), 401

    token = create_access_token(user)
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
            },
        }
    )


@app.post("/api/auth/recuperar")
def api_auth_recuperar():
    payload = request.get_json(silent=True) or {}
    telefono = str(payload.get("telefono") or "").strip()
    if not telefono:
        return jsonify({"error": "Ingresa el numero de telefono registrado."}), 400

    return jsonify(
        {
            "ok": True,
            "pendiente": True,
            "message": (
                "Solicitud registrada. Proximamente recibiras un codigo SMS "
                f"al telefono {telefono[-4:].rjust(len(telefono), '*')} "
                "para restablecer tu contrasena."
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
            }
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
    dashboard = obtener_resumen_dashboard()
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
    nombre = str(payload.get("nombre") or "").strip()
    dni = str(payload.get("dni") or "").strip()

    if not nombre or not dni:
        return jsonify({"error": "nombre y dni son obligatorios."}), 400

    try:
        estudiante = registrar_estudiante(
            nombre_completo=nombre,
            dni=dni,
            codigo_estudiante=payload.get("codigo_siagie"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "estudiante": estudiante}), 201


@app.get("/api/estudiantes/buscar")
def api_buscar_estudiante():
    dni = (request.args.get("dni") or "").strip()
    if not dni:
        return jsonify({"error": "Parametro dni requerido."}), 400

    estudiante = buscar_estudiante_por_dni(dni)
    if estudiante is None:
        return jsonify({"found": False, "dni": dni}), 404

    return jsonify({"found": True, "estudiante": estudiante})


@app.get("/api/estudiantes")
def api_estudiantes():
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    busqueda = (request.args.get("busqueda") or "").strip() or None
    riesgo = (request.args.get("riesgo") or "").strip() or None
    if riesgo and riesgo not in ("alto", "medio", "bajo"):
        return jsonify({"error": "riesgo debe ser alto, medio o bajo."}), 400

    estudiantes = listar_estudiantes_detallado(
        limit=limit,
        offset=offset,
        busqueda=busqueda,
        riesgo=riesgo,
    )
    total = contar_estudiantes_filtrados(busqueda=busqueda, riesgo=riesgo)
    return jsonify({"estudiantes": estudiantes, "total": total, "mostrando": len(estudiantes)})


def _build_reporte_dataframe(estudiantes: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "DNI": item.get("dni") or "",
                "Estudiante": item.get("nombre") or "",
                "Asistencia_%": item.get("asistencias"),
                "Nota_Matematica": item.get("nota_matematica"),
                "Nota_Lenguaje": item.get("nota_lenguaje"),
                "Participacion": item.get("participacion"),
                "Bimestre": item.get("bimestre"),
                "Nivel_Riesgo": item.get("ultimo_nivel_riesgo") or "sin_prediccion",
                "Etiqueta": item.get("ultima_etiqueta") or "",
                "Probabilidad_Alto": item.get("risk_score"),
                "Confianza": item.get("confianza"),
                "Ultima_Prediccion": item.get("ultima_prediccion") or "",
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

    estudiantes = listar_estudiantes_detallado(
        limit=5000,
        busqueda=busqueda,
        riesgo=riesgo,
    )
    df = _build_reporte_dataframe(estudiantes)
    buffer = BytesIO()

    if formato == "csv":
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        mimetype = "text/csv"
        filename = "reporte_estudiantes_predictedu.csv"
    else:
        df.to_excel(buffer, index=False, engine="openpyxl")
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "reporte_estudiantes_predictedu.xlsx"

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


@app.get("/api/intervenciones")
def api_intervenciones_list():
    limit = request.args.get("limit", default=50, type=int)
    intervenciones = listar_intervenciones(limit=limit)
    return jsonify({"intervenciones": intervenciones, "total": len(intervenciones)})


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
    except Exception as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "intervencion_id": intervencion_id}), 201


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
        features = _build_features(payload)
        prediction_raw = int(model.predict(features)[0])
        proba = model.predict_proba(features)[0]
        confidence = float(proba[prediction_raw])
        proba_high_risk = float(proba[1])
    except ValueError as validation_error:
        return jsonify({"error": str(validation_error)}), 400
    except Exception as model_error:
        return jsonify({"error": f"Error en inferencia: {model_error}"}), 500

    prediction_label = "Alto Riesgo" if prediction_raw == 1 else "Bajo Riesgo"

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
        "model": "Random Forest",
        "scale": "Notas literales peruanas: AD, A, B, C",
        "nivel_riesgo": _risk_level_from_probability(proba_high_risk),
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
        return jsonify({"error": "No se envio archivo en el campo 'file'."}), 400

    excel_file = request.files["file"]
    if not excel_file.filename:
        return jsonify({"error": "Archivo invalido."}), 400

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
            proba_high_risk = float(model.predict_proba(features)[0][1])
            prediction_raw = int(model.predict(features)[0])
            confidence = float(model.predict_proba(features)[0][prediction_raw])
        except Exception:
            filas_error += 1
            continue

        risk_level = _risk_level_from_probability(proba_high_risk)
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
                "_prediction_label": "Alto Riesgo" if prediction_raw == 1 else "Bajo Riesgo",
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
