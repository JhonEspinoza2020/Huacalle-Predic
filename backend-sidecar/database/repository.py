"""Capa de acceso a datos SQLite para PredictHuacalle."""

from __future__ import annotations

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
    dni_limpio = dni.strip()
    if not dni_limpio:
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
) -> dict[str, Any]:
    dni_limpio = dni.strip()
    if not dni_limpio:
        raise ValueError("El DNI es obligatorio para registrar un alumno.")
    if not nombre_completo.strip():
        raise ValueError("El nombre completo es obligatorio.")

    nombres, apellido_paterno, apellido_materno = _split_nombre_completo(nombre_completo)

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

    return {
        "id": estudiante_id,
        "dni": dni_limpio,
        "nombre": _format_nombre_completo(nombres, apellido_paterno, apellido_materno),
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


def obtener_resumen_dashboard() -> dict[str, Any]:
    """Conteos para el dashboard desde la última predicción por estudiante."""
    summary = {"alto": 0, "medio": 0, "bajo": 0}
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT nivel_riesgo, COUNT(*) AS total
            FROM (
                SELECT p.estudiante_id, p.nivel_riesgo,
                       ROW_NUMBER() OVER (
                           PARTITION BY p.estudiante_id
                           ORDER BY p.created_at DESC
                       ) AS rn
                FROM predicciones_riesgo p
            )
            WHERE rn = 1
            GROUP BY nivel_riesgo
            """
        ).fetchall()
        for row in rows:
            summary[row[0]] = row[1]

        total_estudiantes = connection.execute(
            "SELECT COUNT(*) FROM estudiantes"
        ).fetchone()[0]
        total_predicciones = connection.execute(
            "SELECT COUNT(*) FROM predicciones_riesgo"
        ).fetchone()[0]
        total_alertas = connection.execute(
            """
            SELECT COUNT(*) FROM alertas_riesgo
            WHERE estado IN ('nueva', 'en_revision')
            """
        ).fetchone()[0]

    return {
        "summary": summary,
        "total_estudiantes": total_estudiantes,
        "total_predicciones": total_predicciones,
        "alertas_activas": total_alertas,
        "ultima_prediccion": obtener_ultima_prediccion(),
        "alertas_prioritarias": obtener_alertas_prioritarias(),
    }


def obtener_ultima_prediccion() -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
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
            ORDER BY p.created_at DESC
            LIMIT 1
            """
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


def obtener_alertas_prioritarias(limit: int = 5) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                a.id AS alerta_id,
                a.nivel_riesgo AS risk_level,
                a.prioridad,
                a.estado,
                p.id AS prediccion_id,
                p.probabilidad_alto AS risk_score,
                p.confianza,
                e.id AS estudiante_id,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                ev.asistencias,
                ev.nota_matematica,
                ev.nota_lenguaje,
                ev.participacion
            FROM alertas_riesgo a
            JOIN predicciones_riesgo p ON p.id = a.prediccion_id
            JOIN estudiantes e ON e.id = a.estudiante_id
            LEFT JOIN evaluaciones ev ON ev.id = p.evaluacion_id
            WHERE a.estado IN ('nueva', 'en_revision')
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
            (limit,),
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
        alertas.append(item)
    return alertas


def listar_estudiantes_detallado(
    limit: int = 100,
    offset: int = 0,
    busqueda: str | None = None,
    riesgo: str | None = None,
) -> list[dict[str, Any]]:
    conditions = ["1=1"]
    params: list[Any] = []

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
    params.extend([limit, offset])

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
            WHERE {where_clause}
            ORDER BY COALESCE(p.created_at, e.created_at) DESC
            LIMIT ? OFFSET ?
            """,
            params,
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
        estudiantes.append(item)
    return estudiantes


def contar_estudiantes_filtrados(
    busqueda: str | None = None,
    riesgo: str | None = None,
) -> int:
    conditions = ["1=1"]
    params: list[Any] = []

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
    if nivel_riesgo == "bajo":
        return None

    prioridad = "critica" if nivel_riesgo == "alto" else "media"

    with get_connection() as connection:
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


def listar_intervenciones(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
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
            FROM intervenciones i
            JOIN estudiantes e ON e.id = i.estudiante_id
            ORDER BY i.created_at DESC
            LIMIT ?
            """,
            (limit,),
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
    return items


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


def eliminar_estudiantes_demo() -> int:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id FROM estudiantes
            WHERE nombres LIKE 'Simulacion%'
               OR nombres LIKE 'Debug%'
               OR nombres = 'Alumno Prueba'
               OR nombres = 'Export Test'
               OR nombres = 'Alto Uno'
               OR nombres = 'Bajo Dos'
            """
        ).fetchall()
        ids = [row[0] for row in rows]
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
