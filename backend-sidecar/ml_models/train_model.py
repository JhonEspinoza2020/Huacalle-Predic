import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

GRADE_TO_SCORE = {"C": 1, "B": 2, "A": 3, "AD": 4}


def build_dataset() -> pd.DataFrame:
    data = [
        {"asistencias": 95, "nota_matematica": "AD", "nota_lenguaje": "A", "participacion": 9, "riesgo_desercion": 0},
        {"asistencias": 88, "nota_matematica": "A", "nota_lenguaje": "A", "participacion": 8, "riesgo_desercion": 0},
        {"asistencias": 72, "nota_matematica": "B", "nota_lenguaje": "B", "participacion": 5, "riesgo_desercion": 1},
        {"asistencias": 65, "nota_matematica": "C", "nota_lenguaje": "C", "participacion": 4, "riesgo_desercion": 1},
        {"asistencias": 98, "nota_matematica": "AD", "nota_lenguaje": "AD", "participacion": 10, "riesgo_desercion": 0},
        {"asistencias": 55, "nota_matematica": "C", "nota_lenguaje": "B", "participacion": 3, "riesgo_desercion": 1},
        {"asistencias": 80, "nota_matematica": "B", "nota_lenguaje": "A", "participacion": 6, "riesgo_desercion": 0},
        {"asistencias": 60, "nota_matematica": "C", "nota_lenguaje": "C", "participacion": 2, "riesgo_desercion": 1},
        {"asistencias": 90, "nota_matematica": "A", "nota_lenguaje": "A", "participacion": 8, "riesgo_desercion": 0},
        {"asistencias": 70, "nota_matematica": "B", "nota_lenguaje": "B", "participacion": 5, "riesgo_desercion": 1},
        {"asistencias": 84, "nota_matematica": "A", "nota_lenguaje": "B", "participacion": 7, "riesgo_desercion": 0},
        {"asistencias": 68, "nota_matematica": "B", "nota_lenguaje": "C", "participacion": 4, "riesgo_desercion": 1},
        {"asistencias": 100, "nota_matematica": "C", "nota_lenguaje": "C", "participacion": 7, "riesgo_desercion": 1},
        {"asistencias": 95, "nota_matematica": "C", "nota_lenguaje": "C", "participacion": 6, "riesgo_desercion": 1},
        {"asistencias": 87, "nota_matematica": "C", "nota_lenguaje": "C", "participacion": 5, "riesgo_desercion": 1},
        {"asistencias": 92, "nota_matematica": "C", "nota_lenguaje": "B", "participacion": 6, "riesgo_desercion": 1},
        {"asistencias": 88, "nota_matematica": "B", "nota_lenguaje": "C", "participacion": 5, "riesgo_desercion": 1},
        {"asistencias": 58, "nota_matematica": "A", "nota_lenguaje": "A", "participacion": 6, "riesgo_desercion": 1},
        {"asistencias": 72, "nota_matematica": "A", "nota_lenguaje": "AD", "participacion": 7, "riesgo_desercion": 1},
        {"asistencias": 85, "nota_matematica": "C", "nota_lenguaje": "A", "participacion": 7, "riesgo_desercion": 1},
        {"asistencias": 82, "nota_matematica": "B", "nota_lenguaje": "B", "participacion": 6, "riesgo_desercion": 1},
    ]
    return pd.DataFrame(data)


def train_and_save_model() -> str:
    df = build_dataset()
    df["nota_matematica"] = df["nota_matematica"].map(GRADE_TO_SCORE)
    df["nota_lenguaje"] = df["nota_lenguaje"].map(GRADE_TO_SCORE)

    feature_columns = ["asistencias", "nota_matematica", "nota_lenguaje", "participacion"]

    x_train = df[feature_columns]
    y_train = df["riesgo_desercion"]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)

    model_path = os.path.join(os.path.dirname(__file__), "modelo_rf.pkl")
    joblib.dump(model, model_path)
    return model_path


if __name__ == "__main__":
    saved_path = train_and_save_model()
    print(f"Modelo entrenado y guardado en: {saved_path}")
