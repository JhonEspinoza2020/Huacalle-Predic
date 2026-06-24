import sys
from pathlib import Path

import pytest

from risk_engine import evaluar_riesgo_pedagogico, nivel_riesgo_desde_probabilidad


@pytest.mark.parametrize(
    "asistencias,mat,leng,part,ml,min_nivel,min_prob,keyword",
    [
        # Rezago: asiste pero no aprende
        (87, "C", "C", 7, 0.24, "medio", 0.45, "rendimiento"),
        (100, "C", "C", 8, 0.15, "alto", 0.70, "inicio"),
        # Una sola area en C
        (85, "C", "A", 7, 0.20, "medio", 0.45, "Matemática"),
        (90, "AD", "C", 8, 0.18, "medio", 0.45, "Comunicación"),
        # Promedio B
        (82, "B", "B", 6, 0.20, "medio", 0.45, "proceso"),
        # Asistencia critica / baja
        (55, "A", "A", 6, 0.10, "alto", 0.70, "deserción"),
        (65, "B", "B", 5, 0.15, "alto", 0.70, "baja"),
        (75, "A", "B", 7, 0.12, "medio", 0.45, "regular"),
        # Combinacion fuerte
        (62, "C", "C", 3, 0.30, "alto", 0.85, "asistencia"),
        # Buen alumno
        (95, "AD", "A", 9, 0.10, "bajo", 0.0, "esperado"),
        (88, "A", "A", 8, 0.12, "bajo", 0.0, "esperado"),
        # Buen rendimiento pero falta
        (72, "A", "AD", 7, 0.10, "medio", 0.45, "inasistencias"),
    ],
)
def test_matriz_casos_pedagogicos(
    asistencias, mat, leng, part, ml, min_nivel, min_prob, keyword
):
    resultado = evaluar_riesgo_pedagogico(asistencias, mat, leng, part, ml)
    niveles = {"bajo": 0, "medio": 1, "alto": 2}
    assert niveles[resultado["nivel_riesgo"]] >= niveles[min_nivel]
    assert resultado["probabilidad_alto"] >= min_prob
    assert any(keyword.lower() in f.lower() for f in resultado["factores"])


def test_nivel_desde_probabilidad():
    assert nivel_riesgo_desde_probabilidad(0.75) == "alto"
    assert nivel_riesgo_desde_probabilidad(0.5) == "medio"
    assert nivel_riesgo_desde_probabilidad(0.2) == "bajo"
