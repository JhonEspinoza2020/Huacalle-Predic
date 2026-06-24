"""Indicadores mensuales, competencias curriculares y asistencias diarias."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from database.repository import (
    get_active_anio_escolar_id,
    get_connection,
    obtener_estudiante,
)

AREAS_COMPETENCIA = frozenset(
    {
        "personal_social",
        "ciencia_tecnologia",
        "arte_cultura",
        "educacion_fisica",
        "ingles",
        "religion",
        "matematica",
        "comunicacion",
    }
)

NOTAS_LITERALES = frozenset({"AD", "A", "B", "C"})
ESTADOS_ASISTENCIA = frozenset({"presente", "falta", "tardanza", "justificada"})

AREA_COMPETENCIA_LABELS = {
    "personal_social": "Personal social",
    "ciencia_tecnologia": "Ciencia y tecnologia",
    "arte_cultura": "Arte y cultura",
    "educacion_fisica": "Educacion fisica",
    "ingles": "Ingles",
    "religion": "Religion",
    "matematica": "Matematica",
    "comunicacion": "Comunicacion",
}


def _validar_nota_competencia(nota: str) -> str:
    limpia = str(nota or "").strip().upper()
    if limpia not in NOTAS_LITERALES:
        raise ValueError(f"Nota no válida para competencia: {nota}")
    return limpia


def _validar_estado_asistencia(estado: str) -> str:
    limpio = str(estado or "presente").strip().lower()
    if limpio not in ESTADOS_ASISTENCIA:
        raise ValueError("Estado de asistencia no válido.")
    return limpio


def _bimestre_para_fecha(fecha: str) -> int:
    mes = int(str(fecha)[5:7])
    if mes <= 4:
        return 1
    if mes <= 6:
        return 2
    if mes <= 8:
        return 3
    return 4


def _meses_bimestre(bimestre: int) -> tuple[int, ...]:
    if bimestre == 1:
        return (3, 4)
    if bimestre == 2:
        return (5, 6)
    if bimestre == 3:
        return (7, 8)
    return (9, 10, 11, 12)


def _rango_mes(anio: int, mes: int) -> tuple[str, str]:
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return f"{anio}-{mes:02d}-01", f"{anio}-{mes:02d}-{ultimo_dia:02d}"


def _estudiantes_seccion_ids(
    connection,
    anio_escolar_id: int,
    seccion_id: int | None,
) -> list[int]:
    if seccion_id is None:
        rows = connection.execute(
            """
            SELECT DISTINCT estudiante_id
            FROM matriculas
            WHERE anio_escolar_id = ? AND estado = 'matriculado'
            """,
            (anio_escolar_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT estudiante_id
            FROM matriculas
            WHERE anio_escolar_id = ? AND seccion_id = ? AND estado = 'matriculado'
            """,
            (anio_escolar_id, seccion_id),
        ).fetchall()
    return [int(row[0]) for row in rows]


def _calcular_metricas_seccion(
    connection,
    anio_escolar_id: int,
    seccion_id: int | None,
    anio: int,
    mes: int,
) -> dict[str, Any]:
    estudiante_ids = _estudiantes_seccion_ids(connection, anio_escolar_id, seccion_id)
    total = len(estudiante_ids)
    if total == 0:
        return {
            "total_estudiantes": 0,
            "promedio_asistencia": None,
            "porcentaje_riesgo_alto": 0.0,
            "porcentaje_riesgo_medio": 0.0,
            "porcentaje_riesgo_bajo": 0.0,
            "total_intervenciones": 0,
            "total_derivaciones": 0,
        }

    placeholders = ",".join("?" * total)
    riesgo_rows = connection.execute(
        f"""
        SELECT p.nivel_riesgo
        FROM estudiantes e
        JOIN (
            SELECT estudiante_id, nivel_riesgo,
                   ROW_NUMBER() OVER (PARTITION BY estudiante_id ORDER BY created_at DESC) AS rn
            FROM predicciones_riesgo
        ) p ON p.estudiante_id = e.id AND p.rn = 1
        WHERE e.id IN ({placeholders})
        """,
        estudiante_ids,
    ).fetchall()

    alto = medio = bajo = 0
    for row in riesgo_rows:
        nivel = row["nivel_riesgo"]
        if nivel == "alto":
            alto += 1
        elif nivel == "medio":
            medio += 1
        else:
            bajo += 1

    asist_row = connection.execute(
        f"""
        SELECT AVG(ev.asistencias) AS promedio
        FROM estudiantes e
        JOIN (
            SELECT estudiante_id, asistencias,
                   ROW_NUMBER() OVER (PARTITION BY estudiante_id ORDER BY fecha_registro DESC) AS rn
            FROM evaluaciones
            WHERE anio_escolar_id = ?
        ) ev ON ev.estudiante_id = e.id AND ev.rn = 1
        WHERE e.id IN ({placeholders})
        """,
        [anio_escolar_id, *estudiante_ids],
    ).fetchone()
    promedio_asistencia = float(asist_row["promedio"]) if asist_row and asist_row["promedio"] is not None else None

    desde, hasta = _rango_mes(anio, mes)
    interv_row = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM intervenciones
        WHERE estudiante_id IN ({placeholders})
          AND date(created_at) BETWEEN date(?) AND date(?)
        """,
        [*estudiante_ids, desde, hasta],
    ).fetchone()
    deriv_row = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM derivaciones_externas
        WHERE estudiante_id IN ({placeholders})
          AND date(fecha_derivacion) BETWEEN date(?) AND date(?)
        """,
        [*estudiante_ids, desde, hasta],
    ).fetchone()

    con_riesgo = alto + medio + bajo
    if con_riesgo == 0:
        pct_alto = pct_medio = pct_bajo = 0.0
    else:
        pct_alto = round(alto / con_riesgo * 100, 2)
        pct_medio = round(medio / con_riesgo * 100, 2)
        pct_bajo = round(bajo / con_riesgo * 100, 2)

    return {
        "total_estudiantes": total,
        "promedio_asistencia": round(promedio_asistencia, 2) if promedio_asistencia is not None else None,
        "porcentaje_riesgo_alto": pct_alto,
        "porcentaje_riesgo_medio": pct_medio,
        "porcentaje_riesgo_bajo": pct_bajo,
        "total_intervenciones": int(interv_row["total"]) if interv_row else 0,
        "total_derivaciones": int(deriv_row["total"]) if deriv_row else 0,
    }


def _limpiar_duplicados_institucionales(
    connection,
    anio_escolar_id: int,
    anio: int,
    mes: int,
) -> None:
    """SQLite trata NULL como distinto en UNIQUE; conserva solo el registro mas reciente."""
    connection.execute(
        """
        DELETE FROM indicadores_mensuales
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM indicadores_mensuales
            WHERE anio_escolar_id = ?
              AND seccion_id IS NULL
              AND anio = ?
              AND mes = ?
        )
          AND anio_escolar_id = ?
          AND seccion_id IS NULL
          AND anio = ?
          AND mes = ?
        """,
        (anio_escolar_id, anio, mes, anio_escolar_id, anio, mes),
    )


def _upsert_indicador(
    connection,
    anio_escolar_id: int,
    seccion_id: int | None,
    anio: int,
    mes: int,
    metricas: dict[str, Any],
) -> int:
    if seccion_id is None:
        _limpiar_duplicados_institucionales(connection, anio_escolar_id, anio, mes)
        existing = connection.execute(
            """
            SELECT id FROM indicadores_mensuales
            WHERE anio_escolar_id = ? AND seccion_id IS NULL AND anio = ? AND mes = ?
            LIMIT 1
            """,
            (anio_escolar_id, anio, mes),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE indicadores_mensuales
                SET total_estudiantes = ?,
                    promedio_asistencia = ?,
                    porcentaje_riesgo_alto = ?,
                    porcentaje_riesgo_medio = ?,
                    porcentaje_riesgo_bajo = ?,
                    total_intervenciones = ?,
                    total_derivaciones = ?,
                    created_at = datetime('now')
                WHERE id = ?
                """,
                (
                    metricas["total_estudiantes"],
                    metricas["promedio_asistencia"],
                    metricas["porcentaje_riesgo_alto"],
                    metricas["porcentaje_riesgo_medio"],
                    metricas["porcentaje_riesgo_bajo"],
                    metricas["total_intervenciones"],
                    metricas["total_derivaciones"],
                    existing["id"],
                ),
            )
            return int(existing["id"])

    connection.execute(
        """
        INSERT INTO indicadores_mensuales (
            anio_escolar_id,
            seccion_id,
            anio,
            mes,
            total_estudiantes,
            promedio_asistencia,
            porcentaje_riesgo_alto,
            porcentaje_riesgo_medio,
            porcentaje_riesgo_bajo,
            total_intervenciones,
            total_derivaciones
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(anio_escolar_id, seccion_id, anio, mes) DO UPDATE SET
            total_estudiantes = excluded.total_estudiantes,
            promedio_asistencia = excluded.promedio_asistencia,
            porcentaje_riesgo_alto = excluded.porcentaje_riesgo_alto,
            porcentaje_riesgo_medio = excluded.porcentaje_riesgo_medio,
            porcentaje_riesgo_bajo = excluded.porcentaje_riesgo_bajo,
            total_intervenciones = excluded.total_intervenciones,
            total_derivaciones = excluded.total_derivaciones,
            created_at = datetime('now')
        """,
        (
            anio_escolar_id,
            seccion_id,
            anio,
            mes,
            metricas["total_estudiantes"],
            metricas["promedio_asistencia"],
            metricas["porcentaje_riesgo_alto"],
            metricas["porcentaje_riesgo_medio"],
            metricas["porcentaje_riesgo_bajo"],
            metricas["total_intervenciones"],
            metricas["total_derivaciones"],
        ),
    )
    row = connection.execute(
        """
        SELECT id FROM indicadores_mensuales
        WHERE anio_escolar_id = ? AND anio = ? AND mes = ?
          AND (
            (seccion_id IS NULL AND ? IS NULL)
            OR seccion_id = ?
          )
        """,
        (anio_escolar_id, anio, mes, seccion_id, seccion_id),
    ).fetchone()
    return int(row["id"]) if row else 0


def _indicador_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    if item.get("nivel_educativo") and item.get("grado") and item.get("seccion"):
        item["seccion_etiqueta"] = (
            f"{item['nivel_educativo']} {item['grado']}° {item['seccion']}"
        )
    elif item.get("seccion_id") is None:
        item["seccion_etiqueta"] = "Toda la institución"
    else:
        item["seccion_etiqueta"] = f"Sección #{item.get('seccion_id')}"
    return item


def calcular_indicadores_mensuales(
    anio: int | None = None,
    mes: int | None = None,
    anio_escolar_id: int | None = None,
    seccion_ids: list[int] | None = None,
    incluir_institucion: bool = False,
) -> list[dict[str, Any]]:
    hoy = date.today()
    anio_calc = anio or hoy.year
    mes_calc = mes or hoy.month
    if mes_calc < 1 or mes_calc > 12:
        raise ValueError("El mes debe estar entre 1 y 12.")

    with get_connection() as connection:
        anio_id = anio_escolar_id or get_active_anio_escolar_id(connection)
        if anio_id is None:
            raise ValueError("No hay año escolar activo configurado.")

        secciones = connection.execute(
            """
            SELECT id FROM secciones
            WHERE anio_escolar_id = ?
            ORDER BY nivel_educativo, grado, seccion
            """,
            (anio_id,),
        ).fetchall()

        todas_seccion_ids = [int(row["id"]) for row in secciones]
        if seccion_ids is not None:
            permitidas = set(todas_seccion_ids)
            ids_objetivo = [sid for sid in seccion_ids if sid in permitidas]
        else:
            ids_objetivo = todas_seccion_ids

        calculados: list[dict[str, Any]] = []
        scopes: list[int | None] = []
        if incluir_institucion:
            scopes.append(None)
        scopes.extend(ids_objetivo)

        for seccion_id in scopes:
            metricas = _calcular_metricas_seccion(connection, anio_id, seccion_id, anio_calc, mes_calc)
            indicador_id = _upsert_indicador(connection, anio_id, seccion_id, anio_calc, mes_calc, metricas)
            calculados.append(
                {
                    "id": indicador_id,
                    "anio_escolar_id": anio_id,
                    "seccion_id": seccion_id,
                    "anio": anio_calc,
                    "mes": mes_calc,
                    **metricas,
                }
            )

    return listar_indicadores(
        anio=anio_calc,
        mes=mes_calc,
        seccion_ids=seccion_ids,
        incluir_institucion=incluir_institucion,
    )["items"]


def listar_indicadores(
    anio: int | None = None,
    mes: int | None = None,
    seccion_id: int | None = None,
    seccion_ids: list[int] | None = None,
    incluir_institucion: bool = False,
) -> dict[str, Any]:
    conditions = ["1=1"]
    params: list[Any] = []

    if anio is not None:
        conditions.append("i.anio = ?")
        params.append(anio)
    if mes is not None:
        conditions.append("i.mes = ?")
        params.append(mes)
    if seccion_id is not None:
        conditions.append("i.seccion_id = ?")
        params.append(seccion_id)
    elif seccion_ids is not None:
        if not seccion_ids:
            return {"items": [], "total": 0}
        placeholders = ",".join("?" * len(seccion_ids))
        if incluir_institucion:
            conditions.append(f"(i.seccion_id IN ({placeholders}) OR i.seccion_id IS NULL)")
        else:
            conditions.append(f"i.seccion_id IN ({placeholders})")
        params.extend(seccion_ids)
    elif not incluir_institucion:
        conditions.append("i.seccion_id IS NOT NULL")

    where_clause = " AND ".join(conditions)
    base_from = """
            FROM indicadores_mensuales i
            LEFT JOIN secciones s ON s.id = i.seccion_id
        """

    with get_connection() as connection:
        total_row = connection.execute(
            f"SELECT COUNT(*) {base_from} WHERE {where_clause}",
            params,
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        rows = connection.execute(
            f"""
            SELECT
                i.id,
                i.anio_escolar_id,
                i.seccion_id,
                i.anio,
                i.mes,
                i.total_estudiantes,
                i.promedio_asistencia,
                i.porcentaje_riesgo_alto,
                i.porcentaje_riesgo_medio,
                i.porcentaje_riesgo_bajo,
                i.total_intervenciones,
                i.total_derivaciones,
                i.created_at,
                s.nivel_educativo,
                s.grado,
                s.seccion
            {base_from}
            WHERE {where_clause}
            ORDER BY i.anio DESC, i.mes DESC, i.seccion_id IS NOT NULL, s.grado, s.seccion
            """,
            params,
        ).fetchall()

    items = [_indicador_row_to_dict(dict(row)) for row in rows]
    return {"items": items, "total": total}


def guardar_competencias_notas(
    evaluacion_id: int,
    competencias: dict[str, str] | None,
) -> list[dict[str, Any]]:
    if not competencias:
        return []

    guardadas: list[dict[str, Any]] = []
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM evaluaciones WHERE id = ?",
            (evaluacion_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Evaluación no encontrada.")

        for area, nota in competencias.items():
            area_limpia = str(area or "").strip().lower()
            if area_limpia not in AREAS_COMPETENCIA:
                continue
            nota_limpia = str(nota or "").strip()
            if not nota_limpia:
                continue
            nota_valida = _validar_nota_competencia(nota_limpia)
            connection.execute(
                """
                INSERT INTO competencias_notas (evaluacion_id, area, nota_literal)
                VALUES (?, ?, ?)
                ON CONFLICT(evaluacion_id, area) DO UPDATE SET
                    nota_literal = excluded.nota_literal
                """,
                (evaluacion_id, area_limpia, nota_valida),
            )
            guardadas.append(
                {
                    "evaluacion_id": evaluacion_id,
                    "area": area_limpia,
                    "nota_literal": nota_valida,
                    "area_label": AREA_COMPETENCIA_LABELS.get(area_limpia, area_limpia),
                }
            )

    return guardadas


def listar_competencias_evaluacion(evaluacion_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT evaluacion_id, area, nota_literal
            FROM competencias_notas
            WHERE evaluacion_id = ?
            ORDER BY area
            """,
            (evaluacion_id,),
        ).fetchall()

    items = []
    for row in rows:
        item = dict(row)
        item["area_label"] = AREA_COMPETENCIA_LABELS.get(item["area"], item["area"])
        items.append(item)
    return items


def _puntaje_asistencia(estado: str) -> float:
    if estado in ("presente", "justificada"):
        return 1.0
    if estado == "tardanza":
        return 0.5
    return 0.0


def recalcular_asistencia_evaluacion(
    estudiante_id: int,
    anio_escolar_id: int,
    bimestre: int,
    anio_calendario: int | None = None,
) -> float | None:
    meses = _meses_bimestre(bimestre)
    anio_ref = anio_calendario or date.today().year

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT estado_asistencia
            FROM asistencias_diarias
            WHERE estudiante_id = ?
              AND CAST(strftime('%m', fecha) AS INTEGER) IN ({})
              AND CAST(strftime('%Y', fecha) AS INTEGER) = ?
            """.format(",".join("?" * len(meses))),
            [estudiante_id, *meses, anio_ref],
        ).fetchall()

        if not rows:
            return None

        puntajes = [_puntaje_asistencia(row["estado_asistencia"]) for row in rows]
        porcentaje = round(sum(puntajes) / len(puntajes) * 100, 2)

        connection.execute(
            """
            UPDATE evaluaciones
            SET asistencias = ?, fecha_registro = datetime('now')
            WHERE estudiante_id = ? AND anio_escolar_id = ? AND bimestre = ?
            """,
            (porcentaje, estudiante_id, anio_escolar_id, bimestre),
        )
        return porcentaje


def registrar_asistencias_diarias(
    registros: list[dict[str, Any]],
    anio_escolar_id: int | None = None,
) -> dict[str, Any]:
    if not registros:
        raise ValueError("Debe enviar al menos un registro de asistencia.")

    procesados = 0
    pendientes_recalculo: set[tuple[int, int, int]] = set()

    with get_connection() as connection:
        anio_id = anio_escolar_id or get_active_anio_escolar_id(connection)
        if anio_id is None:
            raise ValueError("No hay año escolar activo configurado.")

        for item in registros:
            estudiante_id = int(item["estudiante_id"])
            if obtener_estudiante(estudiante_id) is None:
                raise ValueError(f"Estudiante {estudiante_id} no encontrado.")

            fecha = str(item.get("fecha") or date.today().isoformat())
            estado = _validar_estado_asistencia(item.get("estado_asistencia", "presente"))
            matricula_id = item.get("matricula_id")
            observacion = item.get("observacion")

            connection.execute(
                """
                INSERT INTO asistencias_diarias (
                    estudiante_id,
                    matricula_id,
                    fecha,
                    estado_asistencia,
                    observacion
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(estudiante_id, fecha) DO UPDATE SET
                    estado_asistencia = excluded.estado_asistencia,
                    matricula_id = excluded.matricula_id,
                    observacion = excluded.observacion
                """,
                (estudiante_id, matricula_id, fecha, estado, observacion),
            )
            procesados += 1
            bimestre = int(item.get("bimestre") or _bimestre_para_fecha(fecha))
            anio_cal = int(str(fecha)[:4])
            pendientes_recalculo.add((estudiante_id, bimestre, anio_cal))

    recalculados: list[dict[str, Any]] = []
    for estudiante_id, bimestre, anio_cal in pendientes_recalculo:
        with get_connection() as connection:
            anio_id = anio_escolar_id or get_active_anio_escolar_id(connection)
        if anio_id is None:
            continue
        pct = recalcular_asistencia_evaluacion(estudiante_id, anio_id, bimestre, anio_cal)
        if pct is not None:
            recalculados.append(
                {
                    "estudiante_id": estudiante_id,
                    "bimestre": bimestre,
                    "asistencias": pct,
                }
            )

    return {"procesados": procesados, "recalculados": recalculados}
