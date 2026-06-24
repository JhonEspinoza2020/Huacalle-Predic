"""Capa de acceso a datos SQLite para PredictHuacalle."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from database.db_setup import SCHEMA_VERSION, get_db_path, list_tables, setup_database


def init_database(seed: bool = True) -> str:
    """Crea o actualiza colegio.db y devuelve la ruta del archivo."""
    return setup_database(seed=seed)


@contextmanager
def get_connection():
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def get_active_anio_escolar_id(connection: sqlite3.Connection) -> int | None:
    row = connection.execute(
        "SELECT id FROM configuracion_anio_escolar WHERE activo = 1 LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def listar_anios_escolares() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, anio, fecha_inicio, fecha_fin, activo, created_at
            FROM configuracion_anio_escolar
            ORDER BY anio DESC
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def activar_anio_escolar(anio_escolar_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, anio FROM configuracion_anio_escolar WHERE id = ?",
            (anio_escolar_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Año escolar no encontrado.")
        connection.execute("UPDATE configuracion_anio_escolar SET activo = 0")
        connection.execute(
            "UPDATE configuracion_anio_escolar SET activo = 1 WHERE id = ?",
            (anio_escolar_id,),
        )
        return {"id": row[0], "anio": row[1], "activo": 1}


def format_seccion_etiqueta(
    nivel_educativo: str,
    grado: int,
    seccion: str,
    turno: str | None = None,
) -> str:
    nivel = "Primaria" if nivel_educativo == "primaria" else "Secundaria"
    turno_label = ""
    if turno == "tarde":
        turno_label = " · Tarde"
    elif turno == "manana":
        turno_label = " · Mañana"
    return f"{grado}° {seccion} · {nivel}{turno_label}"


def _seccion_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["tutor_nombre"] = _format_nombre_completo(
        item.pop("tutor_nombres", None) or "",
        item.pop("tutor_apellido_paterno", None) or "",
        item.pop("tutor_apellido_materno", None) or "",
    )
    if not item["tutor_nombre"]:
        item["tutor_nombre"] = None
    item["etiqueta"] = format_seccion_etiqueta(
        item["nivel_educativo"],
        item["grado"],
        item["seccion"],
        item.get("turno"),
    )
    return item


def listar_secciones_activas() -> list[dict[str, Any]]:
    with get_connection() as connection:
        anio_id = get_active_anio_escolar_id(connection)
        if anio_id is None:
            return []
        rows = connection.execute(
            """
            SELECT
                s.id,
                s.anio_escolar_id,
                s.nivel_educativo,
                s.grado,
                s.seccion,
                s.turno,
                s.tutor_id,
                ae.anio AS anio_escolar,
                d.nombres AS tutor_nombres,
                d.apellido_paterno AS tutor_apellido_paterno,
                d.apellido_materno AS tutor_apellido_materno,
                (
                    SELECT COUNT(*)
                    FROM matriculas m
                    WHERE m.seccion_id = s.id AND m.estado = 'matriculado'
                ) AS alumnos_matriculados
            FROM secciones s
            JOIN configuracion_anio_escolar ae ON ae.id = s.anio_escolar_id
            LEFT JOIN docentes d ON d.id = s.tutor_id
            WHERE s.anio_escolar_id = ?
            ORDER BY s.nivel_educativo, s.grado, s.seccion, s.turno
            """,
            (anio_id,),
        ).fetchall()
    return [_seccion_row_to_dict(row) for row in rows]


def obtener_seccion_ids_tutor(docente_id: int) -> list[int]:
    with get_connection() as connection:
        anio_id = get_active_anio_escolar_id(connection)
        if anio_id is None:
            return []
        rows = connection.execute(
            """
            SELECT id FROM secciones
            WHERE anio_escolar_id = ? AND tutor_id = ?
            ORDER BY nivel_educativo, grado, seccion
            """,
            (anio_id, docente_id),
        ).fetchall()
    return [row[0] for row in rows]


def seccion_pertenece_tutor(seccion_id: int, docente_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM secciones
            WHERE id = ? AND tutor_id = ?
            LIMIT 1
            """,
            (seccion_id, docente_id),
        ).fetchone()
    return row is not None


def matricular_estudiante(
    estudiante_id: int,
    seccion_id: int,
    anio_escolar_id: int | None = None,
) -> int:
    with get_connection() as connection:
        if anio_escolar_id is None:
            anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            raise ValueError("No hay año escolar activo configurado.")

        seccion = connection.execute(
            """
            SELECT id FROM secciones
            WHERE id = ? AND anio_escolar_id = ?
            """,
            (seccion_id, anio_escolar_id),
        ).fetchone()
        if seccion is None:
            raise ValueError("La sección seleccionada no es válida para el año escolar activo.")

        existing = connection.execute(
            """
            SELECT id FROM matriculas
            WHERE estudiante_id = ? AND anio_escolar_id = ?
            """,
            (estudiante_id, anio_escolar_id),
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE matriculas
                SET seccion_id = ?, estado = 'matriculado', fecha_matricula = date('now')
                WHERE id = ?
                """,
                (seccion_id, existing[0]),
            )
            return existing[0]

        cursor = connection.execute(
            """
            INSERT INTO matriculas (
                estudiante_id, seccion_id, anio_escolar_id, fecha_matricula, estado
            )
            VALUES (?, ?, ?, date('now'), 'matriculado')
            """,
            (estudiante_id, seccion_id, anio_escolar_id),
        )
        return cursor.lastrowid


def reparar_matriculas_pendientes_tutor(docente_id: int) -> int:
    """Matricula alumnos con evaluaciones del ano activo pero sin seccion asignada."""
    secciones = obtener_seccion_ids_tutor(docente_id)
    if not secciones:
        return 0

    seccion_id = secciones[0]
    reparados = 0

    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return 0

        rows = connection.execute(
            """
            SELECT DISTINCT e.id AS estudiante_id
            FROM estudiantes e
            WHERE EXISTS (
                SELECT 1 FROM evaluaciones ev
                WHERE ev.estudiante_id = e.id
                  AND ev.anio_escolar_id = ?
            )
            AND NOT EXISTS (
                SELECT 1 FROM matriculas m
                WHERE m.estudiante_id = e.id
                  AND m.anio_escolar_id = ?
                  AND m.estado = 'matriculado'
            )
            """,
            (anio_escolar_id, anio_escolar_id),
        ).fetchall()

        for row in rows:
            estudiante_id = int(row["estudiante_id"])
            matricula_id = matricular_estudiante(
                estudiante_id,
                seccion_id,
                anio_escolar_id,
            )
            connection.execute(
                """
                UPDATE evaluaciones
                SET matricula_id = ?
                WHERE estudiante_id = ?
                  AND anio_escolar_id = ?
                  AND matricula_id IS NULL
                """,
                (matricula_id, estudiante_id, anio_escolar_id),
            )
            reparados += 1

    return reparados


def obtener_matricula_id_activa(
    estudiante_id: int,
    anio_escolar_id: int | None = None,
) -> int | None:
    with get_connection() as connection:
        if anio_escolar_id is None:
            anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return None
        row = connection.execute(
            """
            SELECT id FROM matriculas
            WHERE estudiante_id = ?
              AND anio_escolar_id = ?
              AND estado = 'matriculado'
            LIMIT 1
            """,
            (estudiante_id, anio_escolar_id),
        ).fetchone()
    return row[0] if row else None


def _append_filtro_seccion(
    conditions: list[str],
    params: list[Any],
    *,
    anio_escolar_id: int,
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> None:
    if seccion_id is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM matriculas m_f
                WHERE m_f.estudiante_id = e.id
                  AND m_f.anio_escolar_id = ?
                  AND m_f.estado = 'matriculado'
                  AND m_f.seccion_id = ?
            )
            """
        )
        params.extend([anio_escolar_id, seccion_id])
    elif tutor_docente_id is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM matriculas m_f
                JOIN secciones s_f ON s_f.id = m_f.seccion_id
                WHERE m_f.estudiante_id = e.id
                  AND m_f.anio_escolar_id = ?
                  AND m_f.estado = 'matriculado'
                  AND s_f.tutor_id = ?
            )
            """
        )
        params.extend([anio_escolar_id, tutor_docente_id])


def _append_filtro_seccion_estudiante_id(
    conditions: list[str],
    params: list[Any],
    *,
    estudiante_alias: str,
    anio_escolar_id: int,
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> None:
    if seccion_id is not None:
        conditions.append(
            f"""
            EXISTS (
                SELECT 1 FROM matriculas m_f
                WHERE m_f.estudiante_id = {estudiante_alias}
                  AND m_f.anio_escolar_id = ?
                  AND m_f.estado = 'matriculado'
                  AND m_f.seccion_id = ?
            )
            """
        )
        params.extend([anio_escolar_id, seccion_id])
    elif tutor_docente_id is not None:
        conditions.append(
            f"""
            EXISTS (
                SELECT 1 FROM matriculas m_f
                JOIN secciones s_f ON s_f.id = m_f.seccion_id
                WHERE m_f.estudiante_id = {estudiante_alias}
                  AND m_f.anio_escolar_id = ?
                  AND m_f.estado = 'matriculado'
                  AND s_f.tutor_id = ?
            )
            """
        )
        params.extend([anio_escolar_id, tutor_docente_id])


def get_database_status() -> dict[str, Any]:
    """Estado de la base para health checks y /api/status."""
    db_path = Path(get_db_path())
    exists = db_path.exists()

    if not exists:
        return {
            "ready": False,
            "path": str(db_path),
            "schema_version": 0,
            "table_count": 0,
        }

    with get_connection() as connection:
        version_row = connection.execute(
            "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
        ).fetchone()
        schema_version = version_row[0] if version_row else 0
        table_count = connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchone()[0]

    return {
        "ready": schema_version >= SCHEMA_VERSION and table_count >= 23,
        "path": str(db_path),
        "schema_version": schema_version,
        "table_count": table_count,
        "tables": list_tables(),
    }


def buscar_estudiante_por_dni(dni: str) -> dict[str, Any] | None:
    from validators import normalizar_dni

    try:
        dni_limpio = normalizar_dni(dni)
    except ValueError:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                e.id,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                e.dni,
                e.estado,
                ev.asistencias,
                ev.nota_matematica,
                ev.nota_lenguaje,
                ev.participacion,
                ev.bimestre,
                p.nivel_riesgo AS ultimo_nivel_riesgo,
                p.etiqueta AS ultima_etiqueta,
                p.confianza,
                p.created_at AS ultima_prediccion
            FROM estudiantes e
            LEFT JOIN evaluaciones ev ON ev.id = (
                SELECT ev2.id
                FROM evaluaciones ev2
                WHERE ev2.estudiante_id = e.id
                ORDER BY ev2.fecha_registro DESC
                LIMIT 1
            )
            LEFT JOIN predicciones_riesgo p ON p.id = (
                SELECT p2.id
                FROM predicciones_riesgo p2
                WHERE p2.estudiante_id = e.id
                ORDER BY p2.created_at DESC
                LIMIT 1
            )
            WHERE e.dni = ?
            LIMIT 1
            """,
            (dni_limpio,),
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["nombre"] = _format_nombre_completo(
        data["nombres"],
        data["apellido_paterno"],
        data["apellido_materno"],
    )
    return data


def registrar_estudiante(
    nombre_completo: str,
    dni: str,
    codigo_estudiante: str | None = None,
    seccion_id: int | None = None,
) -> dict[str, Any]:
    from validators import normalizar_dni, validar_nombre_completo

    dni_limpio = normalizar_dni(dni)
    nombre_limpio = validar_nombre_completo(nombre_completo)
    nombres, apellido_paterno, apellido_materno = _split_nombre_completo(nombre_limpio)

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM estudiantes WHERE dni = ?",
            (dni_limpio,),
        ).fetchone()
        if existing:
            raise ValueError(f"Ya existe un estudiante con DNI {dni_limpio}.")

        cursor = connection.execute(
            """
            INSERT INTO estudiantes (
                nombres, apellido_paterno, apellido_materno, dni, codigo_estudiante, estado
            )
            VALUES (?, ?, ?, ?, ?, 'activo')
            """,
            (
                nombres,
                apellido_paterno,
                apellido_materno,
                dni_limpio,
                codigo_estudiante.strip() if codigo_estudiante else None,
            ),
        )
        estudiante_id = cursor.lastrowid

    matricula_id = None
    seccion_etiqueta = None
    if seccion_id is not None:
        matricula_id = matricular_estudiante(estudiante_id, int(seccion_id))
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT s.nivel_educativo, s.grado, s.seccion, s.turno
                FROM secciones s
                WHERE s.id = ?
                """,
                (seccion_id,),
            ).fetchone()
        if row:
            seccion_etiqueta = format_seccion_etiqueta(row[0], row[1], row[2], row[3])

    return {
        "id": estudiante_id,
        "dni": dni_limpio,
        "nombre": _format_nombre_completo(nombres, apellido_paterno, apellido_materno),
        "seccion_id": seccion_id,
        "matricula_id": matricula_id,
        "seccion_etiqueta": seccion_etiqueta,
    }


def _split_nombre_completo(nombre: str) -> tuple[str, str, str]:
    parts = [part for part in nombre.strip().split() if part]
    if not parts:
        return "Sin nombre", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " ".join(parts[2:])


def buscar_o_crear_estudiante(
    nombres: str,
    apellido_paterno: str = "",
    apellido_materno: str = "",
    dni: str | None = None,
) -> int:
    nombre_limpio = nombres.strip()
    if not nombre_limpio:
        raise ValueError("El nombre del estudiante no puede estar vacío.")

    with get_connection() as connection:
        if dni:
            row = connection.execute(
                "SELECT id FROM estudiantes WHERE dni = ?",
                (dni.strip(),),
            ).fetchone()
            if row:
                return row[0]

        row = connection.execute(
            """
            SELECT id FROM estudiantes
            WHERE nombres = ?
              AND apellido_paterno = ?
              AND apellido_materno = ?
            LIMIT 1
            """,
            (nombre_limpio, apellido_paterno.strip(), apellido_materno.strip()),
        ).fetchone()
        if row:
            estudiante_id = row[0]
            if dni:
                connection.execute(
                    "UPDATE estudiantes SET dni = ? WHERE id = ? AND (dni IS NULL OR dni = '')",
                    (dni.strip(), estudiante_id),
                )
            return estudiante_id

        cursor = connection.execute(
            """
            INSERT INTO estudiantes (nombres, apellido_paterno, apellido_materno, dni, estado)
            VALUES (?, ?, ?, ?, 'activo')
            """,
            (
                nombre_limpio,
                apellido_paterno.strip(),
                apellido_materno.strip(),
                dni.strip() if dni else None,
            ),
        )
        return cursor.lastrowid


def guardar_evaluacion(
    estudiante_id: int,
    anio_escolar_id: int,
    asistencias: float,
    nota_matematica: str,
    nota_lenguaje: str,
    participacion: float,
    bimestre: int = 1,
    origen: str = "manual",
    matricula_id: int | None = None,
    carga_siagie_id: int | None = None,
) -> int:
    nota_mat = nota_matematica.strip().upper()
    nota_len = nota_lenguaje.strip().upper()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO evaluaciones (
                estudiante_id,
                matricula_id,
                anio_escolar_id,
                bimestre,
                asistencias,
                nota_matematica,
                nota_lenguaje,
                participacion,
                origen,
                carga_siagie_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(estudiante_id, anio_escolar_id, bimestre) DO UPDATE SET
                matricula_id = excluded.matricula_id,
                asistencias = excluded.asistencias,
                nota_matematica = excluded.nota_matematica,
                nota_lenguaje = excluded.nota_lenguaje,
                participacion = excluded.participacion,
                origen = excluded.origen,
                carga_siagie_id = excluded.carga_siagie_id,
                fecha_registro = datetime('now')
            """,
            (
                estudiante_id,
                matricula_id,
                anio_escolar_id,
                bimestre,
                asistencias,
                nota_mat,
                nota_len,
                participacion,
                origen,
                carga_siagie_id,
            ),
        )
        if cursor.lastrowid:
            return cursor.lastrowid

        row = connection.execute(
            """
            SELECT id FROM evaluaciones
            WHERE estudiante_id = ? AND anio_escolar_id = ? AND bimestre = ?
            """,
            (estudiante_id, anio_escolar_id, bimestre),
        ).fetchone()
        return row[0]


def _format_nombre_completo(
    nombres: str,
    apellido_paterno: str = "",
    apellido_materno: str = "",
) -> str:
    parts = [nombres.strip(), apellido_paterno.strip(), apellido_materno.strip()]
    return " ".join(part for part in parts if part)


def _student_initials(nombre_completo: str) -> str:
    return "".join(
        part[0].upper()
        for part in nombre_completo.split()
        if part
    )[:2] or "SN"


def obtener_resumen_dashboard(
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> dict[str, Any]:
    """Conteos para el dashboard desde la última predicción por estudiante."""
    summary = {"alto": 0, "medio": 0, "bajo": 0}
    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return {
                "summary": summary,
                "total_estudiantes": 0,
                "total_predicciones": 0,
                "alertas_activas": 0,
                "ultima_prediccion": None,
                "alertas_prioritarias": [],
            }

        scope_conditions = ["1=1"]
        scope_params: list[Any] = []
        _append_filtro_seccion_estudiante_id(
            scope_conditions,
            scope_params,
            estudiante_alias="latest.estudiante_id",
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        scope_where = " AND ".join(scope_conditions)

        rows = connection.execute(
            f"""
            SELECT nivel_riesgo, COUNT(*) AS total
            FROM (
                SELECT p_scope.estudiante_id, p_scope.nivel_riesgo,
                       ROW_NUMBER() OVER (
                           PARTITION BY p_scope.estudiante_id
                           ORDER BY p_scope.created_at DESC
                       ) AS rn
                FROM predicciones_riesgo p_scope
            ) latest
            WHERE rn = 1 AND {scope_where}
            GROUP BY nivel_riesgo
            """,
            scope_params,
        ).fetchall()
        for row in rows:
            summary[row[0]] = row[1]

        student_conditions = ["1=1"]
        student_params: list[Any] = []
        _append_filtro_seccion(
            student_conditions,
            student_params,
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        student_where = " AND ".join(student_conditions)

        total_estudiantes = connection.execute(
            f"SELECT COUNT(*) FROM estudiantes e WHERE {student_where}",
            student_params,
        ).fetchone()[0]

        prediction_conditions = ["1=1"]
        prediction_params: list[Any] = []
        _append_filtro_seccion_estudiante_id(
            prediction_conditions,
            prediction_params,
            estudiante_alias="p_count.estudiante_id",
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        prediction_where = " AND ".join(prediction_conditions)
        total_predicciones = connection.execute(
            f"""
            SELECT COUNT(*) FROM predicciones_riesgo p_count
            WHERE {prediction_where}
            """,
            prediction_params,
        ).fetchone()[0]

        alert_conditions = ["a.estado IN ('nueva', 'en_revision')"]
        alert_params: list[Any] = []
        _append_filtro_seccion_estudiante_id(
            alert_conditions,
            alert_params,
            estudiante_alias="a.estudiante_id",
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        alert_where = " AND ".join(alert_conditions)
        total_alertas = connection.execute(
            f"SELECT COUNT(DISTINCT a.estudiante_id) FROM alertas_riesgo a WHERE {alert_where}",
            alert_params,
        ).fetchone()[0]

    return {
        "summary": summary,
        "total_estudiantes": total_estudiantes,
        "total_predicciones": total_predicciones,
        "alertas_activas": total_alertas,
        "ultima_prediccion": obtener_ultima_prediccion(
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        ),
        "alertas_prioritarias": obtener_alertas_prioritarias(
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        ),
    }


def obtener_ultima_prediccion(
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> dict[str, Any] | None:
    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return None

        conditions = ["1=1"]
        params: list[Any] = []
        _append_filtro_seccion_estudiante_id(
            conditions,
            params,
            estudiante_alias="e.id",
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        where_clause = " AND ".join(conditions)

        row = connection.execute(
            f"""
            SELECT
                p.id AS prediccion_id,
                p.estudiante_id,
                p.etiqueta,
                p.confianza,
                p.nivel_riesgo,
                p.probabilidad_alto,
                p.created_at,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                ev.asistencias,
                ev.nota_matematica,
                ev.nota_lenguaje,
                ev.participacion,
                ev.origen
            FROM predicciones_riesgo p
            JOIN estudiantes e ON e.id = p.estudiante_id
            LEFT JOIN evaluaciones ev ON ev.id = p.evaluacion_id
            WHERE {where_clause}
            ORDER BY p.created_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    nombre = _format_nombre_completo(
        data["nombres"],
        data["apellido_paterno"],
        data["apellido_materno"],
    )
    data["nombre"] = nombre
    data["prediction"] = data["etiqueta"]
    return data


def obtener_alertas_prioritarias(
    limit: int = 50,
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return []

        conditions = ["a.estado IN ('nueva', 'en_revision')"]
        params: list[Any] = []
        _append_filtro_seccion_estudiante_id(
            conditions,
            params,
            estudiante_alias="e.id",
            anio_escolar_id=anio_escolar_id,
            seccion_id=seccion_id,
            tutor_docente_id=tutor_docente_id,
        )
        where_clause = " AND ".join(conditions)
        params.append(limit)

        rows = connection.execute(
            f"""
            SELECT
                a.id AS alerta_id,
                a.nivel_riesgo AS risk_level,
                a.prioridad,
                a.estado,
                p.id AS prediccion_id,
                p.probabilidad_alto AS risk_score,
                p.confianza,
                e.id AS estudiante_id,
                e.dni,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                ev.asistencias,
                ev.bimestre,
                ev.nota_matematica,
                ev.nota_lenguaje,
                ev.participacion,
                {APODERADO_SELECT_SQL}
            FROM alertas_riesgo a
            JOIN predicciones_riesgo p ON p.id = a.prediccion_id
            JOIN estudiantes e ON e.id = a.estudiante_id
            {APODERADO_JOIN_SQL}
            LEFT JOIN evaluaciones ev ON ev.id = p.evaluacion_id
            WHERE {where_clause}
              AND a.id = (
                  SELECT a2.id
                  FROM alertas_riesgo a2
                  WHERE a2.estudiante_id = a.estudiante_id
                    AND a2.estado IN ('nueva', 'en_revision')
                  ORDER BY a2.created_at DESC, a2.id DESC
                  LIMIT 1
              )
            ORDER BY
                CASE a.prioridad
                    WHEN 'critica' THEN 1
                    WHEN 'alta' THEN 2
                    WHEN 'media' THEN 3
                    ELSE 4
                END,
                p.probabilidad_alto DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    alertas: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        nombre = _format_nombre_completo(
            item["nombres"],
            item["apellido_paterno"],
            item["apellido_materno"],
        )
        item["nombre"] = nombre
        item["iniciales"] = _student_initials(nombre)
        _apply_apoderado_fields(item)
        alertas.append(item)
    return alertas


def listar_estudiantes_detallado(
    limit: int = 100,
    offset: int = 0,
    busqueda: str | None = None,
    riesgo: str | None = None,
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> list[dict[str, Any]]:
    conditions = ["1=1"]
    params: list[Any] = []

    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return []

    _append_filtro_seccion(
        conditions,
        params,
        anio_escolar_id=anio_escolar_id,
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )

    if busqueda:
        term = f"%{busqueda.strip()}%"
        conditions.append(
            """
            (
                e.dni LIKE ?
                OR e.nombres LIKE ?
                OR e.apellido_paterno LIKE ?
                OR e.apellido_materno LIKE ?
            )
            """
        )
        params.extend([term, term, term, term])

    if riesgo == "alto":
        conditions.append("p.nivel_riesgo = ?")
        params.append(riesgo)
    elif riesgo == "medio":
        conditions.append("p.nivel_riesgo = ?")
        params.append(riesgo)
    elif riesgo == "bajo":
        conditions.append("(p.nivel_riesgo = 'bajo' OR p.nivel_riesgo IS NULL)")

    where_clause = " AND ".join(conditions)
    query_params = [anio_escolar_id, *params, limit, offset]

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                e.id,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                e.dni,
                e.codigo_estudiante,
                e.estado,
                e.created_at,
                m.id AS matricula_id,
                m.seccion_id,
                s.nivel_educativo,
                s.grado,
                s.seccion,
                s.turno,
                ev.asistencias,
                ev.bimestre,
                ev.nota_matematica,
                ev.nota_lenguaje,
                ev.participacion,
                ev.origen,
                ev.fecha_registro,
                p.id AS prediccion_id,
                p.nivel_riesgo AS ultimo_nivel_riesgo,
                p.probabilidad_alto AS risk_score,
                p.etiqueta AS ultima_etiqueta,
                p.confianza,
                p.created_at AS ultima_prediccion,
                {APODERADO_SELECT_SQL}
            FROM estudiantes e
            {APODERADO_JOIN_SQL}
            LEFT JOIN matriculas m ON m.estudiante_id = e.id
                AND m.anio_escolar_id = ?
                AND m.estado = 'matriculado'
            LEFT JOIN secciones s ON s.id = m.seccion_id
            LEFT JOIN evaluaciones ev ON ev.id = (
                SELECT ev2.id
                FROM evaluaciones ev2
                WHERE ev2.estudiante_id = e.id
                ORDER BY ev2.fecha_registro DESC
                LIMIT 1
            )
            LEFT JOIN predicciones_riesgo p ON p.id = (
                SELECT p2.id
                FROM predicciones_riesgo p2
                WHERE p2.estudiante_id = e.id
                ORDER BY p2.created_at DESC
                LIMIT 1
            )
            WHERE {where_clause}
            ORDER BY COALESCE(p.created_at, e.created_at) DESC
            LIMIT ? OFFSET ?
            """,
            query_params,
        ).fetchall()

    estudiantes: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        nombre = _format_nombre_completo(
            item["nombres"],
            item["apellido_paterno"],
            item["apellido_materno"],
        )
        item["nombre"] = nombre
        item["iniciales"] = _student_initials(nombre)
        if item.get("nivel_educativo"):
            item["seccion_etiqueta"] = format_seccion_etiqueta(
                item["nivel_educativo"],
                item["grado"],
                item["seccion"],
                item.get("turno"),
            )
        else:
            item["seccion_etiqueta"] = None
        _apply_apoderado_fields(item)
        estudiantes.append(item)
    return estudiantes


def contar_estudiantes_filtrados(
    busqueda: str | None = None,
    riesgo: str | None = None,
    seccion_id: int | None = None,
    tutor_docente_id: int | None = None,
) -> int:
    conditions = ["1=1"]
    params: list[Any] = []

    with get_connection() as connection:
        anio_escolar_id = get_active_anio_escolar_id(connection)
        if anio_escolar_id is None:
            return 0

    _append_filtro_seccion(
        conditions,
        params,
        anio_escolar_id=anio_escolar_id,
        seccion_id=seccion_id,
        tutor_docente_id=tutor_docente_id,
    )

    if busqueda:
        term = f"%{busqueda.strip()}%"
        conditions.append(
            """
            (
                e.dni LIKE ?
                OR e.nombres LIKE ?
                OR e.apellido_paterno LIKE ?
                OR e.apellido_materno LIKE ?
            )
            """
        )
        params.extend([term, term, term, term])

    if riesgo == "alto":
        conditions.append("p.nivel_riesgo = ?")
        params.append(riesgo)
    elif riesgo == "medio":
        conditions.append("p.nivel_riesgo = ?")
        params.append(riesgo)
    elif riesgo == "bajo":
        conditions.append("(p.nivel_riesgo = 'bajo' OR p.nivel_riesgo IS NULL)")

    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) FROM estudiantes e
            LEFT JOIN predicciones_riesgo p ON p.id = (
                SELECT p2.id
                FROM predicciones_riesgo p2
                WHERE p2.estudiante_id = e.id
                ORDER BY p2.created_at DESC
                LIMIT 1
            )
            WHERE {where_clause}
            """,
            params,
        ).fetchone()
        return row[0] if row else 0


def guardar_alerta_riesgo(
    estudiante_id: int,
    prediccion_id: int,
    nivel_riesgo: str,
    motivo: str,
) -> int | None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE alertas_riesgo
            SET estado = 'cerrada', fecha_cierre = datetime('now')
            WHERE estudiante_id = ?
              AND estado IN ('nueva', 'en_revision')
            """,
            (estudiante_id,),
        )

        if nivel_riesgo == "bajo":
            return None

        prioridad = "critica" if nivel_riesgo == "alto" else "media"
        cursor = connection.execute(
            """
            INSERT INTO alertas_riesgo (
                estudiante_id,
                prediccion_id,
                nivel_riesgo,
                motivo,
                prioridad,
                estado
            )
            VALUES (?, ?, ?, ?, ?, 'nueva')
            """,
            (estudiante_id, prediccion_id, nivel_riesgo, motivo, prioridad),
        )
        return cursor.lastrowid


def atender_alertas_estudiante(
    estudiante_id: int,
    accion: str = "atencion_registrada",
    detalle: str | None = None,
    docente_id: int | None = None,
    alerta_id: int | None = None,
) -> int:
    """Marca alertas abiertas como atendidas y registra seguimiento."""
    if alerta_id is not None:
        alerta = obtener_alerta_por_id(alerta_id)
        if alerta is None or alerta["estudiante_id"] != estudiante_id:
            return 0
        if alerta["estado"] not in ("nueva", "en_revision"):
            return 0
        atender_alerta_con_seguimiento(
            alerta_id=alerta_id,
            accion=accion,
            detalle=detalle,
            docente_id=docente_id,
            nuevo_estado="atendida",
        )
        return 1

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM alertas_riesgo
            WHERE estudiante_id = ?
              AND estado IN ('nueva', 'en_revision')
            """,
            (estudiante_id,),
        ).fetchall()

    count = 0
    for row in rows:
        atender_alerta_con_seguimiento(
            alerta_id=row["id"],
            accion=accion,
            detalle=detalle,
            docente_id=docente_id,
            nuevo_estado="atendida",
        )
        count += 1
    return count


def consolidar_alertas_duplicadas() -> int:
    """Cierra alertas abiertas antiguas, dejando solo la mas reciente por alumno."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY estudiante_id
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM alertas_riesgo
            WHERE estado IN ('nueva', 'en_revision')
            """
        ).fetchall()
        ids = [row[0] for row in rows if row[1] > 1]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        connection.execute(
            f"""
            UPDATE alertas_riesgo
            SET estado = 'cerrada', fecha_cierre = datetime('now')
            WHERE id IN ({placeholders})
            """,
            ids,
        )
        return len(ids)


ALERTA_ESTADOS_VALIDOS = ("nueva", "en_revision", "atendida", "cerrada")
ALERTA_TRANSICIONES: dict[str, set[str]] = {
    "nueva": {"en_revision", "atendida", "cerrada"},
    "en_revision": {"atendida", "cerrada"},
    "atendida": {"cerrada"},
    "cerrada": set(),
}


def obtener_alerta_por_id(alerta_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                a.id,
                a.estudiante_id,
                a.prediccion_id,
                a.nivel_riesgo,
                a.motivo,
                a.estado,
                a.prioridad,
                a.fecha_alerta,
                a.fecha_cierre,
                a.created_at,
                e.dni,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno
            FROM alertas_riesgo a
            JOIN estudiantes e ON e.id = a.estudiante_id
            WHERE a.id = ?
            """,
            (alerta_id,),
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["estudiante_nombre"] = _format_nombre_completo(
        data["nombres"],
        data["apellido_paterno"],
        data["apellido_materno"],
    )
    for key in ("nombres", "apellido_paterno", "apellido_materno"):
        data.pop(key, None)
    return data


def _validar_transicion_alerta(estado_actual: str, estado_nuevo: str) -> None:
    if estado_nuevo not in ALERTA_ESTADOS_VALIDOS:
        raise ValueError("Estado de alerta no válido.")
    permitidos = ALERTA_TRANSICIONES.get(estado_actual, set())
    if estado_nuevo != estado_actual and estado_nuevo not in permitidos:
        raise ValueError(
            f"No se puede cambiar la alerta de '{estado_actual}' a '{estado_nuevo}'."
        )


def actualizar_estado_alerta(alerta_id: int, estado: str) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT estado FROM alertas_riesgo WHERE id = ?",
            (alerta_id,),
        ).fetchone()
        if row is None:
            return False

        estado_actual = row["estado"]
        _validar_transicion_alerta(estado_actual, estado)
        if estado_actual == estado:
            return True

        if estado in ("atendida", "cerrada"):
            connection.execute(
                """
                UPDATE alertas_riesgo
                SET estado = ?, fecha_cierre = datetime('now')
                WHERE id = ?
                """,
                (estado, alerta_id),
            )
        else:
            connection.execute(
                "UPDATE alertas_riesgo SET estado = ? WHERE id = ?",
                (estado, alerta_id),
            )
    return True


def registrar_seguimiento_alerta(
    alerta_id: int,
    accion: str,
    detalle: str | None = None,
    docente_id: int | None = None,
    resultado: str | None = None,
    nuevo_estado: str | None = None,
) -> int:
    accion_limpia = str(accion or "").strip()
    if not accion_limpia:
        raise ValueError("La acción del seguimiento es obligatoria.")

    if obtener_alerta_por_id(alerta_id) is None:
        raise ValueError("Alerta no encontrada.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO seguimiento_alertas (
                alerta_id,
                docente_id,
                accion,
                detalle,
                resultado
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (alerta_id, docente_id, accion_limpia, detalle, resultado),
        )
        seguimiento_id = cursor.lastrowid

    if nuevo_estado:
        actualizar_estado_alerta(alerta_id, nuevo_estado)

    return seguimiento_id


def listar_seguimiento_alerta(alerta_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.id,
                s.alerta_id,
                s.docente_id,
                s.accion,
                s.detalle,
                s.resultado,
                s.fecha_accion,
                s.created_at,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno
            FROM seguimiento_alertas s
            LEFT JOIN docentes d ON d.id = s.docente_id
            WHERE s.alerta_id = ?
            ORDER BY s.fecha_accion DESC, s.id DESC
            """,
            (alerta_id,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if item.get("docente_nombres"):
            item["docente_nombre"] = _format_nombre_completo(
                item["docente_nombres"],
                item.get("docente_apellido_paterno") or "",
                item.get("docente_apellido_materno") or "",
            )
        else:
            item["docente_nombre"] = None
        for key in ("docente_nombres", "docente_apellido_paterno", "docente_apellido_materno"):
            item.pop(key, None)
        items.append(item)
    return items


def atender_alerta_con_seguimiento(
    alerta_id: int,
    accion: str,
    detalle: str | None = None,
    docente_id: int | None = None,
    nuevo_estado: str = "atendida",
) -> bool:
    registrar_seguimiento_alerta(
        alerta_id=alerta_id,
        accion=accion,
        detalle=detalle,
        docente_id=docente_id,
        nuevo_estado=nuevo_estado,
    )
    return True


def guardar_prediccion(
    estudiante_id: int,
    probabilidad_alto: float,
    nivel_riesgo: str,
    etiqueta: str,
    confianza: float | None = None,
    evaluacion_id: int | None = None,
    modelo: str = "Random Forest",
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO predicciones_riesgo (
                estudiante_id,
                evaluacion_id,
                probabilidad_alto,
                nivel_riesgo,
                etiqueta,
                confianza,
                modelo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estudiante_id,
                evaluacion_id,
                probabilidad_alto,
                nivel_riesgo,
                etiqueta,
                confianza,
                modelo,
            ),
        )
        return cursor.lastrowid


def registrar_carga_siagie(
    nombre_archivo: str,
    total_filas: int,
    filas_procesadas: int,
    filas_error: int,
    anio_escolar_id: int | None = None,
    ruta_archivo: str | None = None,
    estado: str = "completado",
    subido_por_id: int | None = None,
) -> int:
    with get_connection() as connection:
        if anio_escolar_id is None:
            anio_escolar_id = get_active_anio_escolar_id(connection)

        cursor = connection.execute(
            """
            INSERT INTO cargas_siagie (
                nombre_archivo,
                ruta_archivo,
                anio_escolar_id,
                total_filas,
                filas_procesadas,
                filas_error,
                subido_por_id,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre_archivo,
                ruta_archivo,
                anio_escolar_id,
                total_filas,
                filas_procesadas,
                filas_error,
                subido_por_id,
                estado,
            ),
        )
        return cursor.lastrowid


def listar_estudiantes(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                e.id,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                e.dni,
                e.estado,
                e.created_at,
                (
                    SELECT p.nivel_riesgo
                    FROM predicciones_riesgo p
                    WHERE p.estudiante_id = e.id
                    ORDER BY p.created_at DESC
                    LIMIT 1
                ) AS ultimo_nivel_riesgo
            FROM estudiantes e
            ORDER BY e.nombres, e.apellido_paterno
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return _rows_to_dicts(rows)


def registrar_intervencion(
    estudiante_id: int,
    titulo: str,
    tipo: str = "contacto_familia",
    descripcion: str | None = None,
    prediccion_id: int | None = None,
    docente_id: int | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO intervenciones (
                estudiante_id,
                prediccion_id,
                docente_id,
                tipo,
                titulo,
                descripcion,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
            """,
            (estudiante_id, prediccion_id, docente_id, tipo, titulo, descripcion),
        )
        return cursor.lastrowid


def actualizar_estado_intervencion(intervencion_id: int, estado: str) -> bool:
    estados_validos = ("pendiente", "en_curso", "cerrada", "cancelada")
    if estado not in estados_validos:
        raise ValueError("Estado de intervención no válido.")

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM intervenciones WHERE id = ?",
            (intervencion_id,),
        ).fetchone()
        if row is None:
            return False

        if estado == "cerrada":
            connection.execute(
                """
                UPDATE intervenciones
                SET estado = ?, fecha_cierre = datetime('now')
                WHERE id = ?
                """,
                (estado, intervencion_id),
            )
        else:
            connection.execute(
                "UPDATE intervenciones SET estado = ? WHERE id = ?",
                (estado, intervencion_id),
            )
    return True


def listar_intervenciones(
    limit: int = 50,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> dict[str, Any]:
    conditions: list[str] = []
    params: list[Any] = []
    if fecha_desde:
        conditions.append("date(i.created_at) >= date(?)")
        params.append(fecha_desde)
    if fecha_hasta:
        conditions.append("date(i.created_at) <= date(?)")
        params.append(fecha_hasta)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    base_from = """
            FROM intervenciones i
            JOIN estudiantes e ON e.id = i.estudiante_id
        """

    with get_connection() as connection:
        total_row = connection.execute(
            f"SELECT COUNT(*) {base_from} {where_clause}",
            params,
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        list_params = [*params, limit]
        rows = connection.execute(
            f"""
            SELECT
                i.id,
                i.estudiante_id,
                i.prediccion_id,
                i.tipo,
                i.titulo,
                i.descripcion,
                i.estado,
                i.created_at,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno
            {base_from}
            {where_clause}
            ORDER BY i.created_at DESC
            LIMIT ?
            """,
            list_params,
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["nombre_estudiante"] = _format_nombre_completo(
            item["nombres"],
            item["apellido_paterno"],
            item["apellido_materno"],
        )
        items.append(item)
    return {"items": items, "total": total}


def _apply_apoderado_fields(item: dict[str, Any]) -> None:
    nombres = item.get("apoderado_nombres")
    if not nombres:
        item["apoderado_nombre"] = None
        item["apoderado_telefono"] = None
        item["apoderado_parentesco"] = None
        item["apoderado_dni"] = None
        item["apoderado_id"] = None
        return

    item["apoderado_nombre"] = _format_nombre_completo(
        nombres,
        item.get("apoderado_apellido_paterno") or "",
        item.get("apoderado_apellido_materno") or "",
    )
    for key in ("apoderado_nombres", "apoderado_apellido_paterno", "apoderado_apellido_materno"):
        item.pop(key, None)


APODERADO_JOIN_SQL = """
    LEFT JOIN estudiante_apoderado ea ON ea.estudiante_id = e.id AND ea.es_principal = 1
    LEFT JOIN apoderados ap ON ap.id = ea.apoderado_id
"""

APODERADO_SELECT_SQL = """
    ap.id AS apoderado_id,
    ap.dni AS apoderado_dni,
    ap.telefono AS apoderado_telefono,
    ap.parentesco AS apoderado_parentesco,
    ap.nombres AS apoderado_nombres,
    ap.apellido_paterno AS apoderado_apellido_paterno,
    ap.apellido_materno AS apoderado_apellido_materno
"""


def obtener_apoderado_principal(estudiante_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                ap.id,
                ap.nombres,
                ap.apellido_paterno,
                ap.apellido_materno,
                ap.dni,
                ap.telefono,
                ap.telefono_alterno,
                ap.email,
                ap.parentesco,
                ap.created_at
            FROM estudiante_apoderado ea
            JOIN apoderados ap ON ap.id = ea.apoderado_id
            WHERE ea.estudiante_id = ?
              AND ea.es_principal = 1
            LIMIT 1
            """,
            (estudiante_id,),
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["nombre"] = _format_nombre_completo(
        data["nombres"],
        data["apellido_paterno"],
        data["apellido_materno"],
    )
    return data


def guardar_apoderado_principal(
    estudiante_id: int,
    nombre_completo: str,
    telefono: str,
    parentesco: str = "apoderado",
    dni: str | None = None,
    telefono_alterno: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    from validators import validar_dni_opcional, validar_nombre_completo, validar_parentesco, validar_telefono

    nombre_limpio = validar_nombre_completo(nombre_completo)
    telefono_limpio = validar_telefono(telefono)
    parentesco_limpio = validar_parentesco(parentesco)
    dni_limpio = validar_dni_opcional(dni)
    telefono_alt_limpio = None
    if telefono_alterno:
        telefono_alt_limpio = validar_telefono(telefono_alterno)
    email_limpio = str(email).strip() if email else None

    nombres, apellido_paterno, apellido_materno = _split_nombre_completo(nombre_limpio)

    with get_connection() as connection:
        estudiante = connection.execute(
            "SELECT id FROM estudiantes WHERE id = ?",
            (estudiante_id,),
        ).fetchone()
        if estudiante is None:
            raise ValueError("Estudiante no encontrado.")

        principal = connection.execute(
            """
            SELECT apoderado_id
            FROM estudiante_apoderado
            WHERE estudiante_id = ? AND es_principal = 1
            LIMIT 1
            """,
            (estudiante_id,),
        ).fetchone()

        if principal:
            apoderado_id = principal["apoderado_id"]
            connection.execute(
                """
                UPDATE apoderados
                SET nombres = ?,
                    apellido_paterno = ?,
                    apellido_materno = ?,
                    dni = ?,
                    telefono = ?,
                    telefono_alterno = ?,
                    email = ?,
                    parentesco = ?
                WHERE id = ?
                """,
                (
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    dni_limpio,
                    telefono_limpio,
                    telefono_alt_limpio,
                    email_limpio,
                    parentesco_limpio,
                    apoderado_id,
                ),
            )
        else:
            cursor = connection.execute(
                """
                INSERT INTO apoderados (
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    dni,
                    telefono,
                    telefono_alterno,
                    email,
                    parentesco
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    dni_limpio,
                    telefono_limpio,
                    telefono_alt_limpio,
                    email_limpio,
                    parentesco_limpio,
                ),
            )
            apoderado_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO estudiante_apoderado (estudiante_id, apoderado_id, es_principal)
                VALUES (?, ?, 1)
                """,
                (estudiante_id, apoderado_id),
            )

        connection.execute(
            """
            UPDATE estudiante_apoderado
            SET es_principal = 0
            WHERE estudiante_id = ? AND apoderado_id != ?
            """,
            (estudiante_id, apoderado_id),
        )

    apoderado = obtener_apoderado_principal(estudiante_id)
    if apoderado is None:
        raise ValueError("No se pudo guardar el apoderado.")
    return apoderado


def obtener_estudiante(estudiante_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, nombres, apellido_paterno, apellido_materno, dni,
                   codigo_estudiante, fecha_nacimiento, genero, estado, created_at
            FROM estudiantes
            WHERE id = ?
            """,
            (estudiante_id,),
        ).fetchone()
        return _row_to_dict(row)


def obtener_evaluaciones(estudiante_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, estudiante_id, anio_escolar_id, bimestre, asistencias,
                   nota_matematica, nota_lenguaje, participacion, origen, fecha_registro
            FROM evaluaciones
            WHERE estudiante_id = ?
            ORDER BY anio_escolar_id DESC, bimestre DESC
            """,
            (estudiante_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def _usuario_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["nombre_completo"] = _format_nombre_completo(
        item.get("nombres") or "",
        item.get("apellido_paterno") or "",
        item.get("apellido_materno") or "",
    )
    item.pop("password_hash", None)
    return item


def obtener_usuario_por_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                u.id,
                u.docente_id,
                u.username,
                u.rol,
                u.activo,
                u.ultimo_acceso,
                d.nombres,
                d.apellido_paterno,
                d.apellido_materno,
                d.cargo
            FROM usuarios_sistema u
            LEFT JOIN docentes d ON d.id = u.docente_id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
        return _usuario_from_row(row)


def obtener_usuario_por_username(username: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                u.id,
                u.docente_id,
                u.username,
                u.password_hash,
                u.rol,
                u.activo,
                u.ultimo_acceso,
                d.nombres,
                d.apellido_paterno,
                d.apellido_materno,
                d.cargo
            FROM usuarios_sistema u
            LEFT JOIN docentes d ON d.id = u.docente_id
            WHERE u.username = ?
            """,
            (username.strip(),),
        ).fetchone()
        return _row_to_dict(row)


def autenticar_usuario(username: str, password: str) -> dict[str, Any] | None:
    from werkzeug.security import check_password_hash

    user = obtener_usuario_por_username(username)
    if user is None or not user.get("activo"):
        return None
    if not check_password_hash(user["password_hash"], password):
        return None

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE usuarios_sistema
            SET ultimo_acceso = datetime('now')
            WHERE id = ?
            """,
            (user["id"],),
        )

    user.pop("password_hash", None)
    user["nombre_completo"] = _format_nombre_completo(
        user.get("nombres") or "",
        user.get("apellido_paterno") or "",
        user.get("apellido_materno") or "",
    )
    return user


def listar_cargas_siagie(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.nombre_archivo,
                c.total_filas,
                c.filas_procesadas,
                c.filas_error,
                c.estado,
                c.created_at,
                u.username AS subido_por
            FROM cargas_siagie c
            LEFT JOIN usuarios_sistema u ON u.id = c.subido_por_id
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return _rows_to_dicts(rows)


def obtener_conteo_tablas() -> list[dict[str, Any]]:
    tables = list_tables()
    counts: list[dict[str, Any]] = []
    with get_connection() as connection:
        for table in tables:
            total = connection.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            counts.append({"tabla": table, "filas": total})
    return counts


def _estudiante_es_invalido(
    nombres: str,
    apellido_paterno: str,
    apellido_materno: str,
    dni: str | None,
) -> bool:
    nombre = _format_nombre_completo(
        nombres or "",
        apellido_paterno or "",
        apellido_materno or "",
    )
    if nombre.startswith("Simulacion") or nombre.startswith("Debug"):
        return True
    if nombre in {
        "Alumno Prueba",
        "Export Test",
        "Alto Uno",
        "Bajo Dos",
        "Juanito",
        "Carlos",
        "Junio",
        "Luis Mendoza",
    }:
        return True
    if (nombres or "").strip() == "Alumno" and (apellido_paterno or "").strip() == "Prueba":
        return True
    return not _dni_es_valido(dni)


def _dni_es_valido(dni: str | None) -> bool:
    limpio = re.sub(r"\D", "", str(dni or "").strip())
    return len(limpio) == 8


def eliminar_estudiantes_demo() -> int:
    """Elimina alumnos de prueba o sin DNI peruano valido (8 digitos)."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, nombres, apellido_paterno, apellido_materno, dni
            FROM estudiantes
            """
        ).fetchall()
        ids = [
            row[0]
            for row in rows
            if _estudiante_es_invalido(row[1], row[2], row[3], row[4])
        ]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        connection.execute(
            f"DELETE FROM estudiantes WHERE id IN ({placeholders})",
            ids,
        )
        return len(ids)


def listar_docentes() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                nombres,
                apellido_paterno,
                apellido_materno,
                dni,
                especialidad,
                cargo,
                telefono,
                email,
                activo
            FROM docentes
            ORDER BY apellido_paterno, apellido_materno, nombres
            """
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["nombre_completo"] = _format_nombre_completo(
            item.get("nombres") or "",
            item.get("apellido_paterno") or "",
            item.get("apellido_materno") or "",
        )
        items.append(item)
    return items


def listar_secciones_institucional() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.id,
                s.nivel_educativo,
                s.grado,
                s.seccion,
                s.turno,
                ae.anio AS anio_escolar,
                d.nombres AS tutor_nombres,
                d.apellido_paterno AS tutor_apellido_paterno,
                d.apellido_materno AS tutor_apellido_materno,
                (
                    SELECT COUNT(*)
                    FROM matriculas m
                    WHERE m.seccion_id = s.id AND m.estado = 'matriculado'
                ) AS alumnos_matriculados
            FROM secciones s
            JOIN configuracion_anio_escolar ae ON ae.id = s.anio_escolar_id
            LEFT JOIN docentes d ON d.id = s.tutor_id
            ORDER BY ae.anio DESC, s.nivel_educativo, s.grado, s.seccion
            """
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["tutor_nombre"] = _format_nombre_completo(
            item.pop("tutor_nombres", None) or "",
            item.pop("tutor_apellido_paterno", None) or "",
            item.pop("tutor_apellido_materno", None) or "",
        )
        if not item["tutor_nombre"]:
            item["tutor_nombre"] = None
        items.append(item)
    return items


def listar_usuarios_sistema() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                u.id,
                u.username,
                u.rol,
                u.activo,
                u.ultimo_acceso,
                d.nombres,
                d.apellido_paterno,
                d.apellido_materno,
                d.cargo
            FROM usuarios_sistema u
            LEFT JOIN docentes d ON d.id = u.docente_id
            ORDER BY u.username
            """
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["nombre_completo"] = _format_nombre_completo(
            item.get("nombres") or "",
            item.get("apellido_paterno") or "",
            item.get("apellido_materno") or "",
        )
        items.append(item)
    return items


def obtener_predicciones(estudiante_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, estudiante_id, evaluacion_id, probabilidad_alto,
                   nivel_riesgo, etiqueta, confianza, modelo, created_at
            FROM predicciones_riesgo
            WHERE estudiante_id = ?
            ORDER BY created_at DESC
            """,
            (estudiante_id,),
        ).fetchall()
        return _rows_to_dicts(rows)
