# Almacenamiento de datos — PredictEdu

Documentación del modelo de datos del sistema **PredictEdu** (I.E.I. N° 32857 Huacalle).

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [modelo-datos.md](./modelo-datos.md) | Modelo entidad–relación, tablas, claves primarias y relaciones |

## Resumen técnico

| Aspecto | Detalle |
|---------|---------|
| **Motor** | SQLite 3 |
| **Archivo** | `backend-sidecar/database/colegio.db` |
| **Esquema** | Definido en `backend-sidecar/database/db_setup.py` |
| **Versión actual** | 5 (`schema_version`) |
| **Tablas** | 24 tablas de negocio + control de versión |
| **Integridad** | Claves foráneas con `PRAGMA foreign_keys = ON` |
| **Acceso** | Capa `repository.py` desde el backend Flask |

## Dominios del modelo

1. **Configuración y control** — año escolar, versión de esquema
2. **Identidad y acceso** — docentes, usuarios del sistema
3. **Organización escolar** — secciones, matrículas
4. **Población estudiantil** — estudiantes, apoderados
5. **Evaluación académica** — evaluaciones, competencias, asistencias diarias
6. **Predicción e intervención** — predicciones ML, alertas, seguimiento, intervenciones
7. **Reforzamiento** — cursos, inscripciones, sesiones, materiales
8. **Convivencia** — incidencias, derivaciones externas
9. **Indicadores y carga masiva** — indicadores mensuales, cargas SIAGIE
