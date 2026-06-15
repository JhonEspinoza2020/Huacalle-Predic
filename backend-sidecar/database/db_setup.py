import os
import sqlite3
from datetime import date

SCHEMA_VERSION = 4
DB_FILENAME = "colegio.db"


def get_db_path() -> str:
    return os.path.join(os.path.dirname(__file__), DB_FILENAME)


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def _get_schema_version(cursor: sqlite3.Cursor) -> int:
    if not _table_exists(cursor, "schema_version"):
        return 0
    cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else 0


def _migrate_legacy_estudiantes(cursor: sqlite3.Cursor) -> None:
    if not _table_exists(cursor, "estudiantes"):
        return

    columns = _table_columns(cursor, "estudiantes")
    if "asistencias" not in columns:
        return

    cursor.execute("ALTER TABLE estudiantes RENAME TO estudiantes_legacy")

    cursor.execute(
        """
        CREATE TABLE estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellido_paterno TEXT NOT NULL DEFAULT '',
            apellido_materno TEXT NOT NULL DEFAULT '',
            dni TEXT UNIQUE,
            codigo_estudiante TEXT UNIQUE,
            fecha_nacimiento TEXT,
            genero TEXT CHECK (genero IN ('M', 'F', 'otro')),
            estado TEXT NOT NULL DEFAULT 'activo'
                CHECK (estado IN ('activo', 'inactivo', 'egresado', 'trasladado')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    anio_row = cursor.execute(
        "SELECT id FROM configuracion_anio_escolar WHERE activo = 1 LIMIT 1"
    ).fetchone()
    if anio_row is None:
        current_year = date.today().year
        cursor.execute(
            """
            INSERT INTO configuracion_anio_escolar
                (anio, fecha_inicio, fecha_fin, activo)
            VALUES (?, ?, ?, 1)
            """,
            (current_year, f"{current_year}-03-01", f"{current_year}-12-15"),
        )
        anio_id = cursor.lastrowid
    else:
        anio_id = anio_row[0]

    legacy_rows = cursor.execute(
        """
        SELECT id, nombre, asistencias, nota_matematica, nota_lenguaje, participacion
        FROM estudiantes_legacy
        """
    ).fetchall()

    for row in legacy_rows:
        _, nombre, asistencias, nota_mat, nota_len, participacion = row
        cursor.execute(
            """
            INSERT INTO estudiantes (nombres, apellido_paterno, estado)
            VALUES (?, '', 'activo')
            """,
            (nombre,),
        )
        estudiante_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO evaluaciones (
                estudiante_id,
                anio_escolar_id,
                bimestre,
                asistencias,
                nota_matematica,
                nota_lenguaje,
                participacion,
                origen
            )
            VALUES (?, ?, 1, ?, ?, ?, ?, 'migracion_legacy')
            """,
            (
                estudiante_id,
                anio_id,
                asistencias,
                str(nota_mat).upper() if nota_mat is not None else "C",
                str(nota_len).upper() if nota_len is not None else "C",
                participacion,
            ),
        )

    cursor.execute("DROP TABLE estudiantes_legacy")
    _repair_broken_estudiantes_foreign_keys(cursor)


_TABLES_WITH_ESTUDIANTE_FK = [
    "seguimiento_alertas",
    "alertas_riesgo",
    "competencias_notas",
    "predicciones_riesgo",
    "evaluaciones",
    "intervenciones",
    "inscripciones_reforzamiento",
    "asistencias_diarias",
    "derivaciones_externas",
    "incidencias_convivencia",
    "estudiante_apoderado",
    "matriculas",
]


def _has_broken_estudiantes_foreign_keys(cursor: sqlite3.Cursor) -> bool:
    row = cursor.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE sql LIKE '%estudiantes_legacy%'
        LIMIT 1
        """
    ).fetchone()
    return row is not None


def _repair_broken_estudiantes_foreign_keys(cursor: sqlite3.Cursor) -> None:
    """Recrea tablas cuyas FK quedaron apuntando a estudiantes_legacy tras migracion."""
    if not _has_broken_estudiantes_foreign_keys(cursor):
        return

    cursor.execute("PRAGMA foreign_keys=OFF")
    for table_name in _TABLES_WITH_ESTUDIANTE_FK:
        if not _table_exists(cursor, table_name):
            continue
        table_sql = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if table_sql and table_sql[0] and "estudiantes_legacy" in table_sql[0]:
            cursor.execute(f"DROP TABLE {table_name}")

    _create_tables(cursor)
    cursor.execute("PRAGMA foreign_keys=ON")


def _create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS configuracion_anio_escolar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER NOT NULL UNIQUE,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            activo INTEGER NOT NULL DEFAULT 0 CHECK (activo IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS docentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellido_paterno TEXT NOT NULL DEFAULT '',
            apellido_materno TEXT NOT NULL DEFAULT '',
            dni TEXT UNIQUE,
            especialidad TEXT,
            cargo TEXT NOT NULL DEFAULT 'docente'
                CHECK (cargo IN ('docente', 'tutor', 'director', 'psicologo', 'admin')),
            telefono TEXT,
            email TEXT,
            activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS usuarios_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            docente_id INTEGER,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'docente'
                CHECK (rol IN ('admin', 'director', 'docente', 'lectura')),
            activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
            ultimo_acceso TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS secciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio_escolar_id INTEGER NOT NULL,
            nivel_educativo TEXT NOT NULL
                CHECK (nivel_educativo IN ('primaria', 'secundaria')),
            grado INTEGER NOT NULL CHECK (grado BETWEEN 1 AND 6),
            seccion TEXT NOT NULL DEFAULT 'A',
            turno TEXT NOT NULL DEFAULT 'manana'
                CHECK (turno IN ('manana', 'tarde')),
            tutor_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE CASCADE,
            FOREIGN KEY (tutor_id) REFERENCES docentes(id) ON DELETE SET NULL,
            UNIQUE (anio_escolar_id, nivel_educativo, grado, seccion, turno)
        );

        CREATE TABLE IF NOT EXISTS estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellido_paterno TEXT NOT NULL DEFAULT '',
            apellido_materno TEXT NOT NULL DEFAULT '',
            dni TEXT UNIQUE,
            codigo_estudiante TEXT UNIQUE,
            fecha_nacimiento TEXT,
            genero TEXT CHECK (genero IN ('M', 'F', 'otro')),
            estado TEXT NOT NULL DEFAULT 'activo'
                CHECK (estado IN ('activo', 'inactivo', 'egresado', 'trasladado')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS matriculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            seccion_id INTEGER NOT NULL,
            anio_escolar_id INTEGER NOT NULL,
            fecha_matricula TEXT,
            estado TEXT NOT NULL DEFAULT 'matriculado'
                CHECK (estado IN ('matriculado', 'retirado', 'trasladado')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE RESTRICT,
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE CASCADE,
            UNIQUE (estudiante_id, anio_escolar_id)
        );

        CREATE TABLE IF NOT EXISTS apoderados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellido_paterno TEXT NOT NULL DEFAULT '',
            apellido_materno TEXT NOT NULL DEFAULT '',
            dni TEXT,
            telefono TEXT,
            telefono_alterno TEXT,
            email TEXT,
            parentesco TEXT NOT NULL DEFAULT 'apoderado'
                CHECK (parentesco IN ('padre', 'madre', 'apoderado', 'tutor', 'otro')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS estudiante_apoderado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            apoderado_id INTEGER NOT NULL,
            es_principal INTEGER NOT NULL DEFAULT 0 CHECK (es_principal IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (apoderado_id) REFERENCES apoderados(id) ON DELETE CASCADE,
            UNIQUE (estudiante_id, apoderado_id)
        );

        CREATE TABLE IF NOT EXISTS cargas_siagie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_archivo TEXT NOT NULL,
            ruta_archivo TEXT,
            anio_escolar_id INTEGER,
            total_filas INTEGER NOT NULL DEFAULT 0,
            filas_procesadas INTEGER NOT NULL DEFAULT 0,
            filas_error INTEGER NOT NULL DEFAULT 0,
            subido_por_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'completado'
                CHECK (estado IN ('procesando', 'completado', 'error')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE SET NULL,
            FOREIGN KEY (subido_por_id) REFERENCES usuarios_sistema(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            matricula_id INTEGER,
            anio_escolar_id INTEGER NOT NULL,
            bimestre INTEGER NOT NULL CHECK (bimestre BETWEEN 1 AND 4),
            asistencias REAL NOT NULL CHECK (asistencias BETWEEN 0 AND 100),
            nota_matematica TEXT NOT NULL
                CHECK (nota_matematica IN ('AD', 'A', 'B', 'C')),
            nota_lenguaje TEXT NOT NULL
                CHECK (nota_lenguaje IN ('AD', 'A', 'B', 'C')),
            participacion REAL NOT NULL DEFAULT 0,
            fecha_registro TEXT NOT NULL DEFAULT (datetime('now')),
            origen TEXT NOT NULL DEFAULT 'manual'
                CHECK (origen IN ('manual', 'siagie', 'importacion', 'migracion_legacy')),
            carga_siagie_id INTEGER,
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (matricula_id) REFERENCES matriculas(id) ON DELETE SET NULL,
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE CASCADE,
            FOREIGN KEY (carga_siagie_id) REFERENCES cargas_siagie(id) ON DELETE SET NULL,
            UNIQUE (estudiante_id, anio_escolar_id, bimestre)
        );

        CREATE TABLE IF NOT EXISTS competencias_notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluacion_id INTEGER NOT NULL,
            area TEXT NOT NULL CHECK (
                area IN (
                    'personal_social',
                    'ciencia_tecnologia',
                    'arte_cultura',
                    'educacion_fisica',
                    'ingles',
                    'religion',
                    'matematica',
                    'comunicacion'
                )
            ),
            nota_literal TEXT NOT NULL CHECK (nota_literal IN ('AD', 'A', 'B', 'C')),
            FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones(id) ON DELETE CASCADE,
            UNIQUE (evaluacion_id, area)
        );

        CREATE TABLE IF NOT EXISTS asistencias_diarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            matricula_id INTEGER,
            fecha TEXT NOT NULL,
            estado_asistencia TEXT NOT NULL DEFAULT 'presente'
                CHECK (estado_asistencia IN ('presente', 'falta', 'tardanza', 'justificada')),
            observacion TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (matricula_id) REFERENCES matriculas(id) ON DELETE SET NULL,
            UNIQUE (estudiante_id, fecha)
        );

        CREATE TABLE IF NOT EXISTS predicciones_riesgo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            evaluacion_id INTEGER,
            probabilidad_alto REAL NOT NULL CHECK (probabilidad_alto BETWEEN 0 AND 1),
            nivel_riesgo TEXT NOT NULL CHECK (nivel_riesgo IN ('alto', 'medio', 'bajo')),
            etiqueta TEXT NOT NULL,
            confianza REAL,
            modelo TEXT NOT NULL DEFAULT 'Random Forest',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS intervenciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            prediccion_id INTEGER,
            docente_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'otro'
                CHECK (tipo IN (
                    'contacto_familia',
                    'tutoria',
                    'reforzamiento',
                    'derivacion_ugel',
                    'entrevista_psicologica',
                    'otro'
                )),
            titulo TEXT NOT NULL,
            descripcion TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente', 'en_curso', 'cerrada', 'cancelada')),
            fecha_programada TEXT,
            fecha_cierre TEXT,
            resultado TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (prediccion_id) REFERENCES predicciones_riesgo(id) ON DELETE SET NULL,
            FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS cursos_reforzamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio_escolar_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            area TEXT NOT NULL CHECK (
                area IN ('matematica', 'comunicacion', 'ciencias', 'personal_social', 'integral')
            ),
            nivel_educativo TEXT NOT NULL
                CHECK (nivel_educativo IN ('primaria', 'secundaria', 'mixto')),
            grado_min INTEGER CHECK (grado_min BETWEEN 1 AND 6),
            grado_max INTEGER CHECK (grado_max BETWEEN 1 AND 6),
            docente_id INTEGER,
            cupo_max INTEGER NOT NULL DEFAULT 30,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            estado TEXT NOT NULL DEFAULT 'planificado'
                CHECK (estado IN ('planificado', 'activo', 'finalizado', 'cancelado')),
            descripcion TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE CASCADE,
            FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS inscripciones_reforzamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id INTEGER NOT NULL,
            estudiante_id INTEGER NOT NULL,
            prediccion_id INTEGER,
            motivo TEXT NOT NULL DEFAULT 'otro'
                CHECK (motivo IN (
                    'riesgo_alto',
                    'riesgo_medio',
                    'bajo_rendimiento',
                    'baja_asistencia',
                    'otro'
                )),
            fecha_inscripcion TEXT NOT NULL DEFAULT (date('now')),
            asistencias_taller INTEGER NOT NULL DEFAULT 0,
            resultado TEXT CHECK (resultado IN ('mejoro', 'sin_cambio', 'deserto', 'en_proceso')),
            observaciones TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (curso_id) REFERENCES cursos_reforzamiento(id) ON DELETE CASCADE,
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (prediccion_id) REFERENCES predicciones_riesgo(id) ON DELETE SET NULL,
            UNIQUE (curso_id, estudiante_id)
        );

        CREATE TABLE IF NOT EXISTS alertas_riesgo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            prediccion_id INTEGER,
            nivel_riesgo TEXT NOT NULL CHECK (nivel_riesgo IN ('alto', 'medio', 'bajo')),
            motivo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'nueva'
                CHECK (estado IN ('nueva', 'en_revision', 'atendida', 'cerrada')),
            prioridad TEXT NOT NULL DEFAULT 'media'
                CHECK (prioridad IN ('baja', 'media', 'alta', 'critica')),
            fecha_alerta TEXT NOT NULL DEFAULT (datetime('now')),
            fecha_cierre TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (prediccion_id) REFERENCES predicciones_riesgo(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS seguimiento_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id INTEGER NOT NULL,
            docente_id INTEGER,
            accion TEXT NOT NULL,
            detalle TEXT,
            resultado TEXT,
            fecha_accion TEXT NOT NULL DEFAULT (datetime('now')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (alerta_id) REFERENCES alertas_riesgo(id) ON DELETE CASCADE,
            FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS sesiones_reforzamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id INTEGER NOT NULL,
            fecha_sesion TEXT NOT NULL,
            tema TEXT NOT NULL,
            modalidad TEXT NOT NULL DEFAULT 'presencial'
                CHECK (modalidad IN ('presencial', 'virtual', 'mixta')),
            asistencia_registrada INTEGER NOT NULL DEFAULT 0,
            observaciones TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (curso_id) REFERENCES cursos_reforzamiento(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS derivaciones_externas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            intervencion_id INTEGER,
            entidad_destino TEXT NOT NULL,
            motivo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente', 'aceptada', 'en_proceso', 'cerrada', 'rechazada')),
            fecha_derivacion TEXT NOT NULL DEFAULT (date('now')),
            fecha_respuesta TEXT,
            observaciones TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (intervencion_id) REFERENCES intervenciones(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS incidencias_convivencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            docente_reporta_id INTEGER,
            tipo_incidencia TEXT NOT NULL
                CHECK (tipo_incidencia IN (
                    'bullying',
                    'violencia',
                    'falta_disciplina',
                    'inasistencia_reiterada',
                    'afectacion_emocional',
                    'otro'
                )),
            severidad TEXT NOT NULL DEFAULT 'media'
                CHECK (severidad IN ('baja', 'media', 'alta', 'critica')),
            descripcion TEXT NOT NULL,
            acciones_tomadas TEXT,
            fecha_incidencia TEXT NOT NULL DEFAULT (date('now')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
            FOREIGN KEY (docente_reporta_id) REFERENCES docentes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS indicadores_mensuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio_escolar_id INTEGER NOT NULL,
            seccion_id INTEGER,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
            total_estudiantes INTEGER NOT NULL DEFAULT 0,
            promedio_asistencia REAL,
            porcentaje_riesgo_alto REAL,
            porcentaje_riesgo_medio REAL,
            porcentaje_riesgo_bajo REAL,
            total_intervenciones INTEGER NOT NULL DEFAULT 0,
            total_derivaciones INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (anio_escolar_id) REFERENCES configuracion_anio_escolar(id) ON DELETE CASCADE,
            FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE SET NULL,
            UNIQUE (anio_escolar_id, seccion_id, anio, mes)
        );

        CREATE INDEX IF NOT EXISTS idx_secciones_anio_nivel
            ON secciones (anio_escolar_id, nivel_educativo);

        CREATE INDEX IF NOT EXISTS idx_matriculas_estudiante
            ON matriculas (estudiante_id);

        CREATE INDEX IF NOT EXISTS idx_evaluaciones_estudiante_bimestre
            ON evaluaciones (estudiante_id, anio_escolar_id, bimestre);

        CREATE INDEX IF NOT EXISTS idx_predicciones_estudiante_fecha
            ON predicciones_riesgo (estudiante_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_intervenciones_estudiante_estado
            ON intervenciones (estudiante_id, estado);

        CREATE INDEX IF NOT EXISTS idx_inscripciones_curso
            ON inscripciones_reforzamiento (curso_id);

        CREATE INDEX IF NOT EXISTS idx_asistencias_estudiante_fecha
            ON asistencias_diarias (estudiante_id, fecha);

        CREATE INDEX IF NOT EXISTS idx_alertas_estudiante_estado
            ON alertas_riesgo (estudiante_id, estado, prioridad);

        CREATE INDEX IF NOT EXISTS idx_seguimiento_alerta_fecha
            ON seguimiento_alertas (alerta_id, fecha_accion DESC);

        CREATE INDEX IF NOT EXISTS idx_sesiones_curso_fecha
            ON sesiones_reforzamiento (curso_id, fecha_sesion DESC);

        CREATE INDEX IF NOT EXISTS idx_derivaciones_estudiante_estado
            ON derivaciones_externas (estudiante_id, estado);

        CREATE INDEX IF NOT EXISTS idx_incidencias_estudiante_fecha
            ON incidencias_convivencia (estudiante_id, fecha_incidencia DESC);

        CREATE INDEX IF NOT EXISTS idx_indicadores_periodo
            ON indicadores_mensuales (anio, mes, seccion_id);
        """
    )


def _seed_reference_data(cursor: sqlite3.Cursor) -> None:
    current_year = date.today().year

    cursor.execute("SELECT id FROM configuracion_anio_escolar WHERE activo = 1 LIMIT 1")
    anio_row = cursor.fetchone()
    if anio_row is None:
        cursor.execute(
            """
            INSERT INTO configuracion_anio_escolar (anio, fecha_inicio, fecha_fin, activo)
            VALUES (?, ?, ?, 1)
            """,
            (current_year, f"{current_year}-03-01", f"{current_year}-12-15"),
        )
        anio_id = cursor.lastrowid
    else:
        anio_id = anio_row[0]

    cursor.execute("SELECT COUNT(*) FROM docentes")
    if cursor.fetchone()[0] > 0:
        return

    cursor.executemany(
        """
        INSERT INTO docentes (
            nombres, apellido_paterno, apellido_materno, dni, especialidad, cargo, telefono
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("María", "Quispe", "Huaman", "12345678", "Comunicación", "tutor", "987654321"),
            ("Carlos", "Mendoza", "Rojas", "87654321", "Matemática", "admin", "912345678"),
        ],
    )
    tutor_primaria_id = 1
    docente_matematica_id = 2

    cursor.executemany(
        """
        INSERT INTO secciones (
            anio_escolar_id, nivel_educativo, grado, seccion, turno, tutor_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (anio_id, "primaria", 5, "A", "manana", tutor_primaria_id),
            (anio_id, "primaria", 6, "B", "manana", tutor_primaria_id),
            (anio_id, "secundaria", 1, "A", "tarde", docente_matematica_id),
            (anio_id, "secundaria", 2, "A", "tarde", docente_matematica_id),
        ],
    )

    cursor.executemany(
        """
        INSERT INTO cursos_reforzamiento (
            anio_escolar_id, nombre, area, nivel_educativo,
            grado_min, grado_max, docente_id, cupo_max,
            fecha_inicio, fecha_fin, estado, descripcion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                anio_id,
                "Reforzamiento Matemática — Primaria",
                "matematica",
                "primaria",
                4,
                6,
                docente_matematica_id,
                25,
                f"{current_year}-05-01",
                f"{current_year}-07-15",
                "planificado",
                "Taller de recuperación en competencia matemática.",
            ),
            (
                anio_id,
                "Reforzamiento Comunicación — Secundaria",
                "comunicacion",
                "secundaria",
                1,
                3,
                tutor_primaria_id,
                20,
                f"{current_year}-05-01",
                f"{current_year}-07-15",
                "planificado",
                "Lectura comprensiva y producción textual.",
            ),
        ],
    )


def _seed_usuarios_sistema(cursor: sqlite3.Cursor) -> None:
    from werkzeug.security import generate_password_hash

    cursor.execute("SELECT COUNT(*) FROM usuarios_sistema")
    if cursor.fetchone()[0] > 0:
        return

    cursor.execute("SELECT id FROM docentes WHERE dni = '87654321' LIMIT 1")
    admin_docente = cursor.fetchone()
    cursor.execute("SELECT id FROM docentes WHERE dni = '12345678' LIMIT 1")
    tutor_docente = cursor.fetchone()

    if admin_docente is None or tutor_docente is None:
        return

    cursor.executemany(
        """
        INSERT INTO usuarios_sistema (docente_id, username, password_hash, rol, activo)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            (
                admin_docente[0],
                "admin",
                generate_password_hash("admin2026"),
                "admin",
            ),
            (
                tutor_docente[0],
                "mquispe",
                generate_password_hash("tutor2026"),
                "docente",
            ),
        ],
    )


def setup_database(seed: bool = True) -> str:
    db_path = get_db_path()
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    _create_tables(cursor)

    current_version = _get_schema_version(cursor)
    _migrate_legacy_estudiantes(cursor)
    _repair_broken_estudiantes_foreign_keys(cursor)

    if current_version < SCHEMA_VERSION:
        cursor.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )

    if seed:
        _seed_reference_data(cursor)
        _seed_usuarios_sistema(cursor)

    connection.commit()
    connection.close()
    return db_path


def list_tables() -> list[str]:
    db_path = get_db_path()
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [row[0] for row in cursor.fetchall()]
    connection.close()
    return tables


if __name__ == "__main__":
    path = setup_database()
    tables = list_tables()
    print(f"Base de datos creada/actualizada en: {path}")
    print(f"Esquema version: {SCHEMA_VERSION}")
    print(f"Tablas ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")
