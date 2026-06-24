    # Macroprocesos institucionales — PredictEdu

    **Versión:** 2.0 (actualizada junio 2026)  
    **Sistema:** PredictEdu / Edge-PRIDE — I.E.I. N° 32857 Huacalle  
    **Esquema BD:** v5 · **Fases implementadas:** 1–13

    ---

    ## 1. Marco organizacional

    La institución educativa se modela en **tres macroprocesos** que interactúan en ciclo de mejora:

    ```mermaid
    flowchart LR
        E[MP-EST<br/>Estratégico] --> M[MP-MIS<br/>Misional]
        S[MP-SOP<br/>Soporte] --> M
        M --> R[Resultados<br/>aprendizaje y permanencia]
        R --> E
        S --> E
    ```

    | ID | Macroproceso | Propósito |
    |----|--------------|-----------|
    | **MP-EST** | Estratégico | Planificar, medir y mejorar con evidencia |
    | **MP-MIS** | Misional | Enseñar, evaluar, anticipar riesgo y acompañar al estudiante |
    | **MP-SOP** | Soporte | Sostener personas, datos, plataforma y cumplimiento |

    ---

    ## 2. MP-EST — Macroproceso estratégico

    Define rumbo, metas y control institucional.

    ### 2.1 Subprocesos

    | Subproceso | Descripción | Soporte en PredictEdu |
    |------------|-------------|------------------------|
    | Planificación institucional | PEI, PAT, metas de permanencia | Año escolar activo (`configuracion_anio_escolar`) |
    | Gestión de indicadores | Asistencia, riesgo, intervenciones, derivaciones | `indicadores_mensuales`, pestaña **Indicadores** (admin y docente) |
    | Gobierno de datos | Calidad de registro, trazabilidad | Validadores DNI, auditoría `cargas_siagie`, panel **Mantenimiento** |
    | Mejora continua | Revisión de resultados | Exportación Excel, SonarQube, suite pytest (82 tests) |

    ### 2.2 KPI vinculados al sistema

    | KPI | Fuente en PredictEdu |
    |-----|----------------------|
    | % estudiantes en riesgo alto/medio/bajo | `indicadores_mensuales`, resumen dashboard |
    | Promedio de asistencia institucional | `indicadores_mensuales.promedio_asistencia` |
    | Total intervenciones y derivaciones del mes | `indicadores_mensuales` |
    | Calidad de datos (alumnos sin DNI válido) | `DELETE /api/estudiantes/invalidos` |

    ### 2.3 Pantallas y APIs

    - **Admin:** pestañas Panel, Indicadores, Mantenimiento.
    - **API:** `GET/POST /api/indicadores`, `POST /api/indicadores/calcular`, `GET /api/reportes/exportar`, `GET /api/admin/*`.

    ---

    ## 3. MP-MIS — Macroproceso misional (núcleo educativo)

    Entrega valor directo al estudiante. **PredictEdu se centra aquí.**

    ### 3.1 Subprocesos y cobertura actual

    | Subproceso | Estado | Módulos principales |
    |------------|--------|---------------------|
    | Admisión y matrícula | ✅ Implementado | Registro alumno, sección, `matriculas` |
    | Gestión pedagógica | ✅ Implementado | Evaluaciones por bimestre, competencias, asistencia diaria |
    | Monitoreo de riesgo | ✅ Implementado | Formulario análisis, historial por alumno |
    | Predicción y alerta (IA) | ✅ Implementado | Random Forest + `risk_engine`, `alertas_riesgo` |
    | Intervención y acompañamiento | ✅ Implementado | Intervenciones, seguimiento alertas, contacto apoderado |
    | Reforzamiento académico | ✅ Implementado | Cursos, inscripciones, sesiones, materiales |
    | Convivencia y bienestar | ✅ Implementado | Incidencias, derivaciones externas, ficha convivencia |

    ### 3.2 Flujo misional en PredictEdu

    ```mermaid
    flowchart TD
        A[Registrar / matricular alumno] --> B[Registrar evaluación<br/>asistencia + notas + participación]
        B --> C[POST /api/predict<br/>ML + criterios pedagógicos]
        C --> D{¿Riesgo alto/medio?}
        D -->|Sí| E[alertas_riesgo]
        D -->|No| F[Seguimiento en listado]
        E --> G[Intervención / contacto familia]
        E --> H[Inscripción taller reforzamiento]
        E --> I[Incidencia o derivación]
        G --> J[indicadores_mensuales]
        H --> J
        I --> J
    ```

    ### 3.3 Pantallas docente

    | Pestaña | Subproceso misional |
    |---------|---------------------|
    | Resumen | Evaluación + predicción |
    | Alertas | Alerta temprana y acción |
    | Estudiantes | Matrícula, listado, exportación |
    | Intervenciones | Acompañamiento |
    | Reforzamiento | Talleres de refuerzo |
    | Convivencia | Bienestar e incidencias |
    | Indicadores | Vista por secciones del tutor |

    ---

    ## 4. MP-SOP — Macroproceso de soporte

    Sostiene la operación académica y administrativa.

    ### 4.1 Subprocesos

    | Subproceso | Descripción | Soporte en PredictEdu |
    |------------|-------------|------------------------|
    | Gestión de talento humano | Docentes, tutores, roles | `docentes`, `usuarios_sistema`, panel Admin |
    | Gestión TIC y plataforma | App escritorio, API, seguridad | Tauri + Flask, JWT, `security_headers` |
    | Gestión documental | SIAGIE, reportes UGEL | `cargas_siagie`, `upload_siagie`, export Excel |
    | Recursos educativos | Materiales de taller | `materiales_reforzamiento`, `uploads/reforzamiento/` |

    ### 4.2 Roles de acceso (Fase 6+)

    | Rol | Macroproceso principal | App |
    |-----|------------------------|-----|
    | `admin` | MP-EST + MP-SOP | `AdminApp` |
    | `docente` | MP-MIS | `DocenteApp` |
    | `director` | MP-EST (lectura ampliada) | *(fase posterior)* |
    | `lectura` | Solo consulta | *(fase posterior)* |

    Usuarios seed: `admin` / `mquispe` (ver `db_setup.py`).

    ---

    ## 5. Mapa macroproceso → tablas SQLite (v5)

    | Macroproceso | Tablas principales |
    |--------------|-------------------|
    | MP-EST | `indicadores_mensuales`, `configuracion_anio_escolar`, `cargas_siagie` |
    | MP-MIS | `estudiantes`, `matriculas`, `secciones`, `evaluaciones`, `predicciones_riesgo`, `alertas_riesgo`, `seguimiento_alertas`, `intervenciones`, `cursos_reforzamiento`, `inscripciones_reforzamiento`, `sesiones_reforzamiento`, `incidencias_convivencia`, `derivaciones_externas`, `apoderados`, `estudiante_apoderado`, `competencias_notas`, `asistencias_diarias` |
    | MP-SOP | `docentes`, `usuarios_sistema`, `schema_version`, `materiales_reforzamiento` |

    **24 tablas** operativas. Detalle ER: [../base-de-datos/modelo-datos.md](../base-de-datos/modelo-datos.md).

    ---

    ## 6. Mapa macroproceso → repositorio de código

    | Macroproceso | Backend | Frontend |
    |--------------|---------|----------|
    | MP-EST | `indicadores.py`, rutas admin, `api_exportar_reporte` | `AdminApp` (indicadores, mantenimiento), `IndicadoresPanel` |
    | MP-MIS | `repository.py`, `convivencia.py`, `reforzamiento.py`, `risk_engine.py`, `api_predict` | `DocenteApp` (7 pestañas), `docenteForm.jsx` |
    | MP-SOP | `auth_guard.py`, `auth_tokens.py`, `db_setup.py`, `api_upload_siagie` | `LoginScreen`, `AdminApp` (usuarios, SIAGIE) |

    ---

    ## 7. Evolución respecto a la versión anterior

    | Aspecto | Versión 1.0 (`README_MACROPROCESOS.md`) | Versión 2.0 (este documento) |
    |---------|----------------------------------------|------------------------------|
    | Persistencia | Referencia genérica a tablas | 24 tablas integradas en flujos reales |
    | Roles | Conceptual | Login JWT, AdminApp / DocenteApp |
    | Reforzamiento | Mencionado | Cursos, sesiones, materiales, inscripción desde alertas |
    | Convivencia | Mencionado | Incidencias + derivaciones + ficha |
    | Indicadores | `indicadores_mensuales` | Cálculo mensual + panel admin/docente |
    | IA | Predicciones | RF + `risk_engine` con factores explicativos |

    ---

    ## 8. Resumen ejecutivo

    PredictEdu materializa el **macroproceso misional** (alerta temprana y acción pedagógica) y alimenta el **estratégico** con indicadores mensuales. El **soporte** garantiza identidad, carga SIAGIE, mantenimiento de BD y operación Tauri + Flask.

    La trazabilidad código ↔ proceso se detalla en [matriz-doble-entrada.md](./matriz-doble-entrada.md).

    ---

    *Documento canónico de macroprocesos. El archivo raíz `README_MACROPROCESOS.md` redirige aquí.*
