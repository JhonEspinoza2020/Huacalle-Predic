"""Derivaciones externas e incidencias de convivencia escolar."""

from __future__ import annotations

from typing import Any

from database.repository import (
    _format_nombre_completo,
    get_connection,
    obtener_estudiante,
)

ENTIDADES_DESTINO = frozenset({"ugel", "demuna", "salud", "psicologia", "defensoria", "otro"})
ESTADOS_DERIVACION = frozenset({"pendiente", "aceptada", "en_proceso", "cerrada", "rechazada"})
TIPOS_INCIDENCIA = frozenset(
    {
        "bullying",
        "violencia",
        "falta_disciplina",
        "inasistencia_reiterada",
        "afectacion_emocional",
        "otro",
    }
)
SEVERIDADES_INCIDENCIA = frozenset({"baja", "media", "alta", "critica"})

ENTIDAD_LABELS = {
    "ugel": "UGEL",
    "demuna": "DEMUNA",
    "salud": "Salud / ESSALUD",
    "psicologia": "Psicologia escolar",
    "defensoria": "Defensoria del Pueblo",
    "otro": "Otra entidad",
}

ESTADO_DERIVACION_LABELS = {
    "pendiente": "Pendiente",
    "aceptada": "Aceptada",
    "en_proceso": "En proceso",
    "cerrada": "Cerrada",
    "rechazada": "Rechazada",
}

TIPO_INCIDENCIA_LABELS = {
    "bullying": "Bullying",
    "violencia": "Violencia",
    "falta_disciplina": "Falta de disciplina",
    "inasistencia_reiterada": "Inasistencia reiterada",
    "afectacion_emocional": "Afectacion emocional",
    "otro": "Otro",
}

SEVERIDAD_LABELS = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "critica": "Critica",
}


def _validar_entidad(entidad: str) -> str:
    limpia = str(entidad or "").strip().lower()
    if limpia not in ENTIDADES_DESTINO:
        raise ValueError("Entidad de destino no válida.")
    return limpia


def _validar_estado_derivacion(estado: str) -> str:
    limpio = str(estado or "").strip().lower()
    if limpio not in ESTADOS_DERIVACION:
        raise ValueError("Estado de derivación no válido.")
    return limpio


def _validar_tipo_incidencia(tipo: str) -> str:
    limpio = str(tipo or "").strip().lower()
    if limpio not in TIPOS_INCIDENCIA:
        raise ValueError("Tipo de incidencia no válido.")
    return limpio


def _validar_severidad(severidad: str) -> str:
    limpia = str(severidad or "media").strip().lower()
    if limpia not in SEVERIDADES_INCIDENCIA:
        raise ValueError("Severidad no válida.")
    return limpia


def _nombre_estudiante_desde_row(item: dict[str, Any]) -> str:
    return _format_nombre_completo(
        item.pop("estudiante_nombres"),
        item.pop("estudiante_apellido_paterno", "") or "",
        item.pop("estudiante_apellido_materno", "") or "",
    )


def _derivacion_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["estudiante_nombre"] = _nombre_estudiante_desde_row(item)
    item["entidad_label"] = ENTIDAD_LABELS.get(item.get("entidad_destino"), item.get("entidad_destino"))
    item["estado_label"] = ESTADO_DERIVACION_LABELS.get(item.get("estado"), item.get("estado"))
    return item


def _incidencia_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["estudiante_nombre"] = _nombre_estudiante_desde_row(item)
    if item.get("docente_nombres"):
        item["docente_nombre"] = _format_nombre_completo(
            item.pop("docente_nombres"),
            item.pop("docente_apellido_paterno", "") or "",
            item.pop("docente_apellido_materno", "") or "",
        )
    else:
        item["docente_nombre"] = None
        item.pop("docente_nombres", None)
        item.pop("docente_apellido_paterno", None)
        item.pop("docente_apellido_materno", None)
    item["tipo_label"] = TIPO_INCIDENCIA_LABELS.get(item.get("tipo_incidencia"), item.get("tipo_incidencia"))
    item["severidad_label"] = SEVERIDAD_LABELS.get(item.get("severidad"), item.get("severidad"))
    return item


def _validar_intervencion_estudiante(connection, intervencion_id: int, estudiante_id: int) -> None:
    row = connection.execute(
        "SELECT estudiante_id FROM intervenciones WHERE id = ?",
        (intervencion_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Intervención no encontrada.")
    if int(row["estudiante_id"]) != estudiante_id:
        raise ValueError("La intervención no corresponde al estudiante indicado.")


def crear_derivacion_externa(
    estudiante_id: int,
    entidad_destino: str,
    motivo: str,
    intervencion_id: int | None = None,
    observaciones: str | None = None,
    fecha_derivacion: str | None = None,
) -> dict[str, Any]:
    if obtener_estudiante(estudiante_id) is None:
        raise ValueError("Estudiante no encontrado.")

    entidad = _validar_entidad(entidad_destino)
    motivo_limpio = str(motivo or "").strip()
    if len(motivo_limpio) < 5:
        raise ValueError("El motivo debe tener al menos 5 caracteres.")

    with get_connection() as connection:
        if intervencion_id is not None:
            _validar_intervencion_estudiante(connection, int(intervencion_id), estudiante_id)

        cursor = connection.execute(
            """
            INSERT INTO derivaciones_externas (
                estudiante_id,
                intervencion_id,
                entidad_destino,
                motivo,
                observaciones,
                fecha_derivacion
            )
            VALUES (?, ?, ?, ?, ?, COALESCE(?, date('now')))
            """,
            (
                estudiante_id,
                intervencion_id,
                entidad,
                motivo_limpio,
                observaciones,
                fecha_derivacion,
            ),
        )
        derivacion_id = int(cursor.lastrowid)

    derivacion = obtener_derivacion(derivacion_id)
    if derivacion is None:
        raise RuntimeError("No se pudo recuperar la derivacion creada.")
    return derivacion


def obtener_derivacion(derivacion_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                d.id,
                d.estudiante_id,
                d.intervencion_id,
                d.entidad_destino,
                d.motivo,
                d.estado,
                d.fecha_derivacion,
                d.fecha_respuesta,
                d.observaciones,
                d.created_at,
                e.nombres AS estudiante_nombres,
                e.apellido_paterno AS estudiante_apellido_paterno,
                e.apellido_materno AS estudiante_apellido_materno
            FROM derivaciones_externas d
            JOIN estudiantes e ON e.id = d.estudiante_id
            WHERE d.id = ?
            """,
            (derivacion_id,),
        ).fetchone()

    if row is None:
        return None
    return _derivacion_row_to_dict(dict(row))


def listar_derivaciones(
    estado: str | None = None,
    estudiante_id: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    conditions = ["1=1"]
    params: list[Any] = []

    if estado:
        conditions.append("d.estado = ?")
        params.append(_validar_estado_derivacion(estado))
    if estudiante_id is not None:
        conditions.append("d.estudiante_id = ?")
        params.append(estudiante_id)

    where_clause = " AND ".join(conditions)
    base_from = """
            FROM derivaciones_externas d
            JOIN estudiantes e ON e.id = d.estudiante_id
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
                d.id,
                d.estudiante_id,
                d.intervencion_id,
                d.entidad_destino,
                d.motivo,
                d.estado,
                d.fecha_derivacion,
                d.fecha_respuesta,
                d.observaciones,
                d.created_at,
                e.nombres AS estudiante_nombres,
                e.apellido_paterno AS estudiante_apellido_paterno,
                e.apellido_materno AS estudiante_apellido_materno
            {base_from}
            WHERE {where_clause}
            ORDER BY d.fecha_derivacion DESC, d.created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    items = [_derivacion_row_to_dict(dict(row)) for row in rows]
    return {"items": items, "total": total}


def actualizar_derivacion(
    derivacion_id: int,
    estado: str,
    fecha_respuesta: str | None = None,
    observaciones: str | None = None,
) -> dict[str, Any] | None:
    estado_limpio = _validar_estado_derivacion(estado)

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM derivaciones_externas WHERE id = ?",
            (derivacion_id,),
        ).fetchone()
        if row is None:
            return None

        connection.execute(
            """
            UPDATE derivaciones_externas
            SET estado = ?,
                fecha_respuesta = COALESCE(?, fecha_respuesta),
                observaciones = COALESCE(?, observaciones)
            WHERE id = ?
            """,
            (estado_limpio, fecha_respuesta, observaciones, derivacion_id),
        )

    return obtener_derivacion(derivacion_id)


def crear_incidencia_convivencia(
    estudiante_id: int,
    tipo_incidencia: str,
    descripcion: str,
    severidad: str = "media",
    acciones_tomadas: str | None = None,
    fecha_incidencia: str | None = None,
    docente_reporta_id: int | None = None,
) -> dict[str, Any]:
    if obtener_estudiante(estudiante_id) is None:
        raise ValueError("Estudiante no encontrado.")

    tipo = _validar_tipo_incidencia(tipo_incidencia)
    severidad_limpia = _validar_severidad(severidad)
    descripcion_limpia = str(descripcion or "").strip()
    if len(descripcion_limpia) < 10:
        raise ValueError("La descripción debe tener al menos 10 caracteres.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO incidencias_convivencia (
                estudiante_id,
                docente_reporta_id,
                tipo_incidencia,
                severidad,
                descripcion,
                acciones_tomadas,
                fecha_incidencia
            )
            VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, date('now')))
            """,
            (
                estudiante_id,
                docente_reporta_id,
                tipo,
                severidad_limpia,
                descripcion_limpia,
                acciones_tomadas,
                fecha_incidencia,
            ),
        )
        incidencia_id = int(cursor.lastrowid)

    incidencia = obtener_incidencia(incidencia_id)
    if incidencia is None:
        raise RuntimeError("No se pudo recuperar la incidencia creada.")
    return incidencia


def obtener_incidencia(incidencia_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                i.id,
                i.estudiante_id,
                i.docente_reporta_id,
                i.tipo_incidencia,
                i.severidad,
                i.descripcion,
                i.acciones_tomadas,
                i.fecha_incidencia,
                i.created_at,
                e.nombres AS estudiante_nombres,
                e.apellido_paterno AS estudiante_apellido_paterno,
                e.apellido_materno AS estudiante_apellido_materno,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno
            FROM incidencias_convivencia i
            JOIN estudiantes e ON e.id = i.estudiante_id
            LEFT JOIN docentes d ON d.id = i.docente_reporta_id
            WHERE i.id = ?
            """,
            (incidencia_id,),
        ).fetchone()

    if row is None:
        return None
    return _incidencia_row_to_dict(dict(row))


def listar_incidencias(
    severidad: str | None = None,
    tipo_incidencia: str | None = None,
    estudiante_id: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    conditions = ["1=1"]
    params: list[Any] = []

    if severidad:
        conditions.append("i.severidad = ?")
        params.append(_validar_severidad(severidad))
    if tipo_incidencia:
        conditions.append("i.tipo_incidencia = ?")
        params.append(_validar_tipo_incidencia(tipo_incidencia))
    if estudiante_id is not None:
        conditions.append("i.estudiante_id = ?")
        params.append(estudiante_id)

    where_clause = " AND ".join(conditions)
    base_from = """
            FROM incidencias_convivencia i
            JOIN estudiantes e ON e.id = i.estudiante_id
            LEFT JOIN docentes d ON d.id = i.docente_reporta_id
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
                i.estudiante_id,
                i.docente_reporta_id,
                i.tipo_incidencia,
                i.severidad,
                i.descripcion,
                i.acciones_tomadas,
                i.fecha_incidencia,
                i.created_at,
                e.nombres AS estudiante_nombres,
                e.apellido_paterno AS estudiante_apellido_paterno,
                e.apellido_materno AS estudiante_apellido_materno,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno
            {base_from}
            WHERE {where_clause}
            ORDER BY i.fecha_incidencia DESC, i.created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    items = [_incidencia_row_to_dict(dict(row)) for row in rows]
    return {"items": items, "total": total}
