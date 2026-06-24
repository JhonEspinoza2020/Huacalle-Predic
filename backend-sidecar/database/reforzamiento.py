"""Operaciones de cursos de reforzamiento escolar."""

from __future__ import annotations

from typing import Any

from database.repository import (
    _format_nombre_completo,
    get_active_anio_escolar_id,
    get_connection,
    obtener_estudiante,
)

MOTIVOS_INSCRIPCION = frozenset(
    {"riesgo_alto", "riesgo_medio", "bajo_rendimiento", "baja_asistencia", "otro"}
)
RESULTADOS_INSCRIPCION = frozenset({"mejoro", "sin_cambio", "deserto", "en_proceso"})
MODALIDADES_SESION = frozenset({"presencial", "virtual", "mixta"})
TIPOS_MATERIAL = frozenset({"archivo", "enlace"})

AREA_LABELS = {
    "matematica": "Matematica",
    "comunicacion": "Comunicacion",
    "ciencias": "Ciencias",
    "personal_social": "Personal social",
    "integral": "Integral",
}


def _validar_motivo_inscripcion(motivo: str) -> str:
    limpio = str(motivo or "otro").strip().lower()
    if limpio not in MOTIVOS_INSCRIPCION:
        raise ValueError("Motivo de inscripción no válido.")
    return limpio


def _curso_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    inscritos = int(item.pop("inscritos", 0) or 0)
    cupo_max = int(item.get("cupo_max") or 0)
    item["inscritos"] = inscritos
    item["cupos_disponibles"] = max(cupo_max - inscritos, 0)
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
    item["area_label"] = AREA_LABELS.get(item.get("area"), item.get("area"))
    return item


def listar_cursos_reforzamiento(
    anio_escolar_id: int | None = None,
    incluir_finalizados: bool = False,
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        anio_id = anio_escolar_id or get_active_anio_escolar_id(connection)
        if anio_id is None:
            return []

        estados = ("planificado", "activo", "finalizado", "cancelado")
        if not incluir_finalizados:
            estados = ("planificado", "activo")

        placeholders = ",".join("?" * len(estados))
        rows = connection.execute(
            f"""
            SELECT
                c.id,
                c.nombre,
                c.area,
                c.nivel_educativo,
                c.grado_min,
                c.grado_max,
                c.docente_id,
                c.cupo_max,
                c.fecha_inicio,
                c.fecha_fin,
                c.estado,
                c.descripcion,
                c.created_at,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno,
                (
                    SELECT COUNT(*)
                    FROM inscripciones_reforzamiento ir
                    WHERE ir.curso_id = c.id
                ) AS inscritos
            FROM cursos_reforzamiento c
            LEFT JOIN docentes d ON d.id = c.docente_id
            WHERE c.anio_escolar_id = ?
              AND c.estado IN ({placeholders})
            ORDER BY c.estado, c.nombre
            """,
            (anio_id, *estados),
        ).fetchall()

    return [_curso_row_to_dict(dict(row)) for row in rows]


def obtener_curso_reforzamiento(curso_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                c.id,
                c.anio_escolar_id,
                c.nombre,
                c.area,
                c.nivel_educativo,
                c.grado_min,
                c.grado_max,
                c.docente_id,
                c.cupo_max,
                c.fecha_inicio,
                c.fecha_fin,
                c.estado,
                c.descripcion,
                c.created_at,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno,
                (
                    SELECT COUNT(*)
                    FROM inscripciones_reforzamiento ir
                    WHERE ir.curso_id = c.id
                ) AS inscritos
            FROM cursos_reforzamiento c
            LEFT JOIN docentes d ON d.id = c.docente_id
            WHERE c.id = ?
            """,
            (curso_id,),
        ).fetchone()

    if row is None:
        return None
    return _curso_row_to_dict(dict(row))


def listar_inscripciones_curso(curso_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                ir.id,
                ir.curso_id,
                ir.estudiante_id,
                ir.prediccion_id,
                ir.motivo,
                ir.fecha_inscripcion,
                ir.asistencias_taller,
                ir.resultado,
                ir.observaciones,
                ir.created_at,
                e.dni,
                e.nombres,
                e.apellido_paterno,
                e.apellido_materno,
                p.nivel_riesgo AS ultimo_nivel_riesgo
            FROM inscripciones_reforzamiento ir
            JOIN estudiantes e ON e.id = ir.estudiante_id
            LEFT JOIN predicciones_riesgo p ON p.id = ir.prediccion_id
            WHERE ir.curso_id = ?
            ORDER BY ir.fecha_inscripcion DESC, ir.id DESC
            """,
            (curso_id,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["estudiante_nombre"] = _format_nombre_completo(
            item.pop("nombres"),
            item.pop("apellido_paterno", "") or "",
            item.pop("apellido_materno", "") or "",
        )
        items.append(item)
    return items


def inscribir_estudiante_reforzamiento(
    curso_id: int,
    estudiante_id: int,
    prediccion_id: int | None = None,
    motivo: str = "otro",
    observaciones: str | None = None,
) -> dict[str, Any]:
    motivo_limpio = _validar_motivo_inscripcion(motivo)
    if obtener_estudiante(estudiante_id) is None:
        raise ValueError("Estudiante no encontrado.")

    curso = obtener_curso_reforzamiento(curso_id)
    if curso is None:
        raise ValueError("Curso de reforzamiento no encontrado.")
    if curso["estado"] not in ("planificado", "activo"):
        raise ValueError("El curso no acepta nuevas inscripciones.")
    if curso["cupos_disponibles"] <= 0:
        raise ValueError("No hay cupos disponibles en este taller.")

    with get_connection() as connection:
        duplicado = connection.execute(
            """
            SELECT id FROM inscripciones_reforzamiento
            WHERE curso_id = ? AND estudiante_id = ?
            """,
            (curso_id, estudiante_id),
        ).fetchone()
        if duplicado:
            raise ValueError("El alumno ya está inscrito en este taller.")

        cursor = connection.execute(
            """
            INSERT INTO inscripciones_reforzamiento (
                curso_id,
                estudiante_id,
                prediccion_id,
                motivo,
                observaciones,
                resultado
            )
            VALUES (?, ?, ?, ?, ?, 'en_proceso')
            """,
            (curso_id, estudiante_id, prediccion_id, motivo_limpio, observaciones),
        )
        inscripcion_id = cursor.lastrowid

    inscripciones = listar_inscripciones_curso(curso_id)
    inscripcion = next(item for item in inscripciones if item["id"] == inscripcion_id)
    return inscripcion


def actualizar_inscripcion_reforzamiento(
    inscripcion_id: int,
    resultado: str | None = None,
    observaciones: str | None = None,
    asistencias_taller: int | None = None,
) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, curso_id FROM inscripciones_reforzamiento WHERE id = ?",
            (inscripcion_id,),
        ).fetchone()
        if row is None:
            return None

        updates: list[str] = []
        params: list[Any] = []
        if resultado is not None:
            resultado_limpio = str(resultado).strip().lower()
            if resultado_limpio not in RESULTADOS_INSCRIPCION:
                raise ValueError("Resultado de inscripción no válido.")
            updates.append("resultado = ?")
            params.append(resultado_limpio)
        if observaciones is not None:
            updates.append("observaciones = ?")
            params.append(observaciones)
        if asistencias_taller is not None:
            updates.append("asistencias_taller = ?")
            params.append(int(asistencias_taller))

        if updates:
            params.append(inscripcion_id)
            connection.execute(
                f"UPDATE inscripciones_reforzamiento SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        curso_id = row["curso_id"]

    inscripciones = listar_inscripciones_curso(curso_id)
    return next((item for item in inscripciones if item["id"] == inscripcion_id), None)


def registrar_sesion_reforzamiento(
    curso_id: int,
    fecha_sesion: str,
    tema: str,
    modalidad: str = "presencial",
    asistencia_registrada: int = 0,
    observaciones: str | None = None,
) -> dict[str, Any]:
    if obtener_curso_reforzamiento(curso_id) is None:
        raise ValueError("Curso de reforzamiento no encontrado.")

    tema_limpio = str(tema or "").strip()
    if len(tema_limpio) < 3:
        raise ValueError("El tema de la sesión debe tener al menos 3 caracteres.")

    fecha_limpia = str(fecha_sesion or "").strip()
    if not fecha_limpia:
        raise ValueError("La fecha de sesión es obligatoria.")

    modalidad_limpia = str(modalidad or "presencial").strip().lower()
    if modalidad_limpia not in MODALIDADES_SESION:
        raise ValueError("Modalidad de sesión no válida.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sesiones_reforzamiento (
                curso_id,
                fecha_sesion,
                tema,
                modalidad,
                asistencia_registrada,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                curso_id,
                fecha_limpia,
                tema_limpio,
                modalidad_limpia,
                max(0, int(asistencia_registrada or 0)),
                observaciones,
            ),
        )
        sesion_id = cursor.lastrowid

    sesiones = listar_sesiones_curso(curso_id)
    return next(item for item in sesiones if item["id"] == sesion_id)


def listar_sesiones_curso(curso_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                curso_id,
                fecha_sesion,
                tema,
                modalidad,
                asistencia_registrada,
                observaciones,
                created_at
            FROM sesiones_reforzamiento
            WHERE curso_id = ?
            ORDER BY fecha_sesion DESC, id DESC
            """,
            (curso_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def crear_material_reforzamiento(
    curso_id: int,
    tipo: str,
    titulo: str,
    docente_id: int | None = None,
    url: str | None = None,
    ruta_archivo: str | None = None,
    nombre_archivo: str | None = None,
) -> dict[str, Any]:
    if obtener_curso_reforzamiento(curso_id) is None:
        raise ValueError("Curso de reforzamiento no encontrado.")

    tipo_limpio = str(tipo or "").strip().lower()
    if tipo_limpio not in TIPOS_MATERIAL:
        raise ValueError("Tipo de material no válido.")

    titulo_limpio = str(titulo or "").strip()
    if len(titulo_limpio) < 3:
        raise ValueError("El título del material debe tener al menos 3 caracteres.")

    if tipo_limpio == "enlace" and not str(url or "").strip():
        raise ValueError("La URL del enlace es obligatoria.")
    if tipo_limpio == "archivo" and not ruta_archivo:
        raise ValueError("El archivo es obligatorio.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO materiales_reforzamiento (
                curso_id,
                docente_id,
                tipo,
                titulo,
                url,
                ruta_archivo,
                nombre_archivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                curso_id,
                docente_id,
                tipo_limpio,
                titulo_limpio,
                url,
                ruta_archivo,
                nombre_archivo,
            ),
        )
        material_id = cursor.lastrowid

    materiales = listar_materiales_curso(curso_id)
    return next(item for item in materiales if item["id"] == material_id)


def listar_materiales_curso(curso_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                m.id,
                m.curso_id,
                m.docente_id,
                m.tipo,
                m.titulo,
                m.url,
                m.ruta_archivo,
                m.nombre_archivo,
                m.created_at,
                d.nombres AS docente_nombres,
                d.apellido_paterno AS docente_apellido_paterno,
                d.apellido_materno AS docente_apellido_materno
            FROM materiales_reforzamiento m
            LEFT JOIN docentes d ON d.id = m.docente_id
            WHERE m.curso_id = ?
            ORDER BY m.created_at DESC, m.id DESC
            """,
            (curso_id,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
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
        items.append(item)
    return items


def inferir_motivo_inscripcion(
    nivel_riesgo: str | None,
    asistencias: float | int | None = None,
    nota_matematica: str | None = None,
    nota_lenguaje: str | None = None,
) -> str:
    if nivel_riesgo == "alto":
        return "riesgo_alto"
    if nivel_riesgo == "medio":
        return "riesgo_medio"
    if asistencias is not None and float(asistencias) < 70:
        return "baja_asistencia"
    notas = {str(nota_matematica or "").upper(), str(nota_lenguaje or "").upper()}
    if "C" in notas:
        return "bajo_rendimiento"
    return "otro"


def inferir_area_curso(
    nota_matematica: str | None = None,
    nota_lenguaje: str | None = None,
) -> str:
    mat = str(nota_matematica or "").upper()
    leng = str(nota_lenguaje or "").upper()
    if mat == "C" and leng != "C":
        return "matematica"
    if leng == "C" and mat != "C":
        return "comunicacion"
    if mat == "C":
        return "matematica"
    if leng == "C":
        return "comunicacion"
    return "matematica"
