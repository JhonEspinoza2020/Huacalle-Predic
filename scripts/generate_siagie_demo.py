"""
Genera un Excel de ejemplo compatible con POST /api/upload_siagie

Uso:
  venv\\Scripts\\python.exe scripts\\generate_siagie_demo.py
"""

from pathlib import Path

import pandas as pd

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "siagie_demo_5toA.xlsx"

STUDENTS = [
    {
        "nombre": "Luis Mendoza Quispe",
        "dni": "72345601",
        "asistencias": 42,
        "nota_matematica": "C",
        "nota_lenguaje": "B",
        "participacion": 3,
    },
    {
        "nombre": "Camila Rojas Huaman",
        "dni": "72345602",
        "asistencias": 58,
        "nota_matematica": "B",
        "nota_lenguaje": "B",
        "participacion": 4,
    },
    {
        "nombre": "Diego Huaman Torres",
        "dni": "72345603",
        "asistencias": 63,
        "nota_matematica": "B",
        "nota_lenguaje": "C",
        "participacion": 5,
    },
    {
        "nombre": "Ana Garcia Lopez",
        "dni": "72345604",
        "asistencias": 88,
        "nota_matematica": "A",
        "nota_lenguaje": "AD",
        "participacion": 8,
    },
    {
        "nombre": "Pedro Ramirez Soto",
        "dni": "72345605",
        "asistencias": 35,
        "nota_matematica": "C",
        "nota_lenguaje": "C",
        "participacion": 2,
    },
    {
        "nombre": "Maria Torres Vega",
        "dni": "72345606",
        "asistencias": 72,
        "nota_matematica": "B",
        "nota_lenguaje": "A",
        "participacion": 6,
    },
    {
        "nombre": "Jorge Castillo Paredes",
        "dni": "72345607",
        "asistencias": 91,
        "nota_matematica": "AD",
        "nota_lenguaje": "A",
        "participacion": 9,
    },
    {
        "nombre": "Sofia Quispe Mamani",
        "dni": "72345608",
        "asistencias": 48,
        "nota_matematica": "C",
        "nota_lenguaje": "B",
        "participacion": 3,
    },
]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(STUDENTS)
    df.to_excel(OUTPUT, index=False)
    print(f"Archivo generado: {OUTPUT}")
    print(f"Filas: {len(df)}")


if __name__ == "__main__":
    main()
