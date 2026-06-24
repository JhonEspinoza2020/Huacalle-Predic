"""Criterios pedagogicos de riesgo — complementa el modelo de ML."""

from __future__ import annotations

GRADE_TO_SCORE = {"C": 1, "B": 2, "A": 3, "AD": 4}


def nota_a_puntaje(nota: str) -> int:
    return GRADE_TO_SCORE.get(str(nota or "").strip().upper(), 1)


def nivel_riesgo_desde_probabilidad(probabilidad_alto: float) -> str:
    if probabilidad_alto >= 0.7:
        return "alto"
    if probabilidad_alto >= 0.45:
        return "medio"
    return "bajo"


def etiqueta_desde_nivel(nivel: str) -> str:
    if nivel == "alto":
        return "Alto Riesgo"
    if nivel == "medio":
        return "Riesgo Moderado"
    return "Bajo Riesgo"


def _riesgo_por_notas(mat: int, leng: int, prom_notas: float) -> tuple[float, list[str]]:
    factores: list[str] = []
    riesgo = 0.0

    if mat == 1 and leng == 1:
        riesgo = 0.72
        factores.append("Logro en inicio (C) en Matemática y Comunicación.")
    elif mat == 1 or leng == 1:
        riesgo = 0.52
        area = "Matemática" if mat == 1 else "Comunicación"
        factores.append(f"Logro en inicio (C) en {area}.")
    elif prom_notas <= 2.0:
        riesgo = 0.48
        factores.append("Promedio de logros en proceso (B): requiere seguimiento.")

    return riesgo, factores


def _riesgo_por_asistencia(asistencias: float, prom_notas: float) -> tuple[float, list[str]]:
    factores: list[str] = []
    riesgo = 0.0

    if asistencias < 60:
        riesgo = 0.85
        factores.append(f"Asistencia muy baja ({asistencias:.0f}%): alto riesgo de deserción.")
    elif asistencias < 70:
        riesgo = 0.78
        factores.append(f"Asistencia baja ({asistencias:.0f}%).")
    elif asistencias < 80:
        riesgo = 0.50
        factores.append(f"Asistencia regular ({asistencias:.0f}%).")

    if asistencias >= 80 and prom_notas <= 1.5:
        riesgo = max(riesgo, 0.68)
        factores.append(
            "Asiste al colegio pero el rendimiento es bajo: posible rezago de aprendizajes."
        )

    if asistencias < 75 and prom_notas >= 3.0:
        riesgo = max(riesgo, 0.46)
        factores.append(
            "Buen rendimiento académico pero inasistencias frecuentes: vigilar continuidad."
        )

    return riesgo, factores


def _riesgo_por_participacion(participacion: float) -> tuple[float, list[str]]:
    factores: list[str] = []
    riesgo = 0.0

    if participacion < 3:
        riesgo = 0.72
        factores.append("Participación casi nula en clase.")
    elif participacion < 4:
        riesgo = 0.65
        factores.append("Participación muy baja en actividades de clase.")
    elif participacion < 6:
        riesgo = 0.45
        factores.append("Participación limitada en clase.")

    return riesgo, factores


def _reforzar_por_combinacion(
    riesgo_academico: float,
    riesgo_asistencia: float,
    riesgo_participacion: float,
    mat: int,
    leng: int,
    asistencias: float,
    participacion: float,
    factores: list[str],
) -> float:
    """Sube el riesgo cuando coinciden varios indicadores debiles."""
    riesgo = max(riesgo_academico, riesgo_asistencia, riesgo_participacion)
    indicadores = sum(
        1
        for valor in (riesgo_academico, riesgo_asistencia, riesgo_participacion)
        if valor >= 0.45
    )

    if mat == 1 and leng == 1 and asistencias < 70:
        riesgo = max(riesgo, 0.88)
        if not any("desercion" in f.lower() for f in factores):
            factores.append("Doble alerta: bajo rendimiento y baja asistencia.")

    if mat == 1 and leng == 1 and participacion < 5:
        riesgo = max(riesgo, 0.80)
        if not any("participación" in f.lower() or "participacion" in f.lower() for f in factores):
            factores.append("Bajo rendimiento con poca participación en clase.")

    if indicadores >= 2:
        riesgo = min(0.95, riesgo + 0.06)
        if not any("varios indicadores" in f.lower() for f in factores):
            factores.append("Varios indicadores de seguimiento requieren atencion.")

    return riesgo


def evaluar_riesgo_pedagogico(
    asistencias: float,
    nota_matematica: str,
    nota_lenguaje: str,
    participacion: float,
    probabilidad_ml: float,
) -> dict:
    """
    Combina probabilidad del Random Forest con reglas de seguimiento escolar.

    Casos contemplados:
    - Rezago: alta asistencia + notas C
    - Una sola area en C
    - Promedio B (en proceso)
    - Asistencia critica, baja o regular
    - Buen rendimiento con inasistencias
    - Participacion muy baja
    - Combinaciones (C+C + baja asistencia, C+C + baja participacion, 2+ indicadores)
    """
    mat = nota_a_puntaje(nota_matematica)
    leng = nota_a_puntaje(nota_lenguaje)
    prom_notas = (mat + leng) / 2
    factores: list[str] = []

    riesgo_academico, factores_acad = _riesgo_por_notas(mat, leng, prom_notas)
    riesgo_asistencia, factores_asist = _riesgo_por_asistencia(asistencias, prom_notas)
    riesgo_participacion, factores_part = _riesgo_por_participacion(participacion)
    factores.extend(factores_acad)
    factores.extend(factores_asist)
    factores.extend(factores_part)

    riesgo_pedagogico = _reforzar_por_combinacion(
        riesgo_academico,
        riesgo_asistencia,
        riesgo_participacion,
        mat,
        leng,
        asistencias,
        participacion,
        factores,
    )

    probabilidad_final = max(float(probabilidad_ml), riesgo_pedagogico)
    nivel = nivel_riesgo_desde_probabilidad(probabilidad_final)

    if nivel == "bajo" and not factores:
        factores.append("Indicadores dentro del rango esperado para el bimestre.")

    return {
        "probabilidad_alto": round(probabilidad_final, 4),
        "probabilidad_ml": round(float(probabilidad_ml), 4),
        "nivel_riesgo": nivel,
        "etiqueta": etiqueta_desde_nivel(nivel),
        "factores": factores,
    }
