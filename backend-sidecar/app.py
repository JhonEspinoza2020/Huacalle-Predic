from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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


@app.get("/api/status")
def api_status():
    return jsonify(
        {
            "status": "ok",
            "message": "El motor de Edge-PRIDE está funcionando.",
            "model_loaded": model is not None,
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
        features = _build_features(payload)
        prediction_raw = int(model.predict(features)[0])
        confidence = float(model.predict_proba(features)[0][prediction_raw])
    except ValueError as validation_error:
        return jsonify({"error": str(validation_error)}), 400
    except Exception as model_error:
        return jsonify({"error": f"Error en inferencia: {model_error}"}), 500

    prediction_label = "Alto Riesgo" if prediction_raw == 1 else "Bajo Riesgo"

    return jsonify(
        {
            "received": payload,
            "prediction": prediction_label,
            "confidence": round(confidence, 4),
            "model": "Random Forest",
            "scale": "Notas literales peruanas: AD, A, B, C",
        }
    )


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

    processed_students = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        nombre = _extract_field(row_dict, ["nombre", "estudiante", "alumno", "nombres_apellidos"]) or "Sin nombre"

        payload = {
            "asistencias": _extract_field(row_dict, ["asistencias", "asistencia", "porcentaje_asistencia"]),
            "nota_matematica": _extract_field(row_dict, ["nota_matematica", "matematica", "competencia_matematica"]),
            "nota_lenguaje": _extract_field(row_dict, ["nota_lenguaje", "lenguaje", "comunicacion"]),
            "participacion": _extract_field(row_dict, ["participacion", "participación"]),
        }

        try:
            features = _build_features(payload)
            proba_high_risk = float(model.predict_proba(features)[0][1])
        except Exception:
            continue

        risk_level = _risk_level_from_probability(proba_high_risk)
        processed_students.append(
            {
                "nombre": str(nombre),
                "asistencias": float(payload["asistencias"]),
                "nota_matematica": str(payload["nota_matematica"]).upper(),
                "nota_lenguaje": str(payload["nota_lenguaje"]).upper(),
                "participacion": float(payload["participacion"]),
                "risk_level": risk_level,
                "risk_score": round(proba_high_risk, 4),
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

    summary = {"alto": 0, "medio": 0, "bajo": 0}
    for student in processed_students:
        summary[student["risk_level"]] += 1

    top_5_high_risk = sorted(
        processed_students,
        key=lambda item: item["risk_score"],
        reverse=True,
    )[:5]

    return jsonify(
        {
            "summary": summary,
            "total_students": len(processed_students),
            "top_5_high_risk": top_5_high_risk,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
