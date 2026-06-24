# Matriz de doble entrada — Procesos ↔ Código

Matriz **detallada** que cruza la dimensión **organizacional** (macroproceso → procedimiento → actividad) con la dimensión **técnica** (frontend, controlador API, servicio/modelo, tabla BD, prueba).

**Leyenda de capas técnicas:**

| Símbolo | Capa |
|---------|------|
| **FE** | Frontend React (`src/`) |
| **CTL** | Controlador Flask (`app.py`) |
| **SVC** | Servicio (`risk_engine`, `validators`, `auth_*`) |
| **MDL** | Modelo / repositorio (`database/`) |
| **BD** | Tabla SQLite |
| **TST** | Caso de prueba / RF |

---

## 1. Matriz principal (vista consolidada)

| MP | PROC | ACT | FE | CTL | SVC / MDL | BD | TST |
|----|------|-----|----|----|-----------|-----|-----|
| MP-SOP | PROC-SOP-01 | ACT-SOP-01-01 Iniciar sesión | `LoginScreen` | `POST /api/auth/login` | `autenticar_usuario`, `create_access_token` | `usuarios_sistema` | CP-auth |
| MP-SOP | PROC-SOP-01 | ACT-SOP-01-02 Validar sesión | `App.jsx` | `GET /api/auth/me` | `get_current_user`, `decode_access_token` | `usuarios_sistema` | — |
| MP-SOP | PROC-SOP-01 | ACT-SOP-01-03 Cerrar sesión | `DocenteApp` / `AdminApp` | — | `clearSession` (cliente) | — | — |
| MP-MIS | PROC-MIS-01 | ACT-MIS-01-01 Registrar alumno | `DocenteApp` (Estudiantes) | `POST /api/estudiantes` | `registrar_estudiante`, `matricular_estudiante` | `estudiantes`, `matriculas` | test_matricula |
| MP-MIS | PROC-MIS-01 | ACT-MIS-01-02 Registrar apoderado | `DocenteApp` | `POST .../apoderado` | `guardar_apoderado_principal` | `apoderados`, `estudiante_apoderado` | — |
| MP-MIS | PROC-MIS-01 | ACT-MIS-01-03 Buscar por DNI | `DocenteApp` (Resumen) | `GET /api/estudiantes/buscar` | `buscar_estudiante_por_dni` | `estudiantes` | — |
| MP-MIS | PROC-MIS-01 | ACT-MIS-01-04 Listar con filtros | `DocenteApp` (Estudiantes) | `GET /api/estudiantes` | `listar_estudiantes_detallado` | `estudiantes`, `matriculas`, `evaluaciones` | — |
| MP-MIS | PROC-MIS-02 | ACT-MIS-02-01 Ingresar evaluación | `docenteForm.jsx` | — | `validators` (cliente) | — | RF-02 |
| MP-MIS | PROC-MIS-02 | ACT-MIS-02-02 Ejecutar predicción | `DocenteApp` (Resumen) | `POST /api/predict` | `_analizar_riesgo`, `evaluar_riesgo_pedagogico`, `guardar_evaluacion` | `evaluaciones`, `predicciones_riesgo` | CP-003, RF-02 |
| MP-MIS | PROC-MIS-02 | ACT-MIS-02-03 Guardar competencias | `DocenteApp` | `POST /api/predict` | `guardar_competencias_notas` | `competencias_notas` | — |
| MP-MIS | PROC-MIS-02 | ACT-MIS-02-04 Registrar asistencia diaria | — | `POST /api/asistencias-diarias` | `registrar_asistencias_diarias` | `asistencias_diarias` | — |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-01 Generar alerta | — | `POST /api/predict` | `guardar_alerta_riesgo` | `alertas_riesgo` | — |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-02 Ver alertas prioritarias | `DocenteApp` (Alertas) | `GET /api/resumen` | `obtener_alertas_prioritarias` | `alertas_riesgo` | RF-10 |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-03 Cambiar estado alerta | `DocenteApp` | `PATCH /api/alertas/:id` | `actualizar_estado_alerta` | `alertas_riesgo` | — |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-04 Registrar seguimiento | `DocenteApp` | `POST .../seguimiento` | `registrar_seguimiento_alerta` | `seguimiento_alertas` | — |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-05 Crear intervención | `DocenteApp` | `POST /api/intervenciones` | `registrar_intervencion` | `intervenciones` | — |
| MP-MIS | PROC-MIS-03 | ACT-MIS-03-06 Cerrar intervención | `DocenteApp` | `PATCH /api/intervenciones/:id` | `actualizar_estado_intervencion` | `intervenciones` | — |
| MP-MIS | PROC-MIS-04 | ACT-MIS-04-01 Listar talleres | `DocenteApp` (Reforzamiento) | `GET /api/cursos-reforzamiento` | `listar_cursos_reforzamiento` | `cursos_reforzamiento` | — |
| MP-MIS | PROC-MIS-04 | ACT-MIS-04-02 Inscribir desde alerta | `DocenteApp` | `POST .../inscripciones` | `inscribir_estudiante_reforzamiento` | `inscripciones_reforzamiento` | — |
| MP-MIS | PROC-MIS-04 | ACT-MIS-04-03 Registrar sesión | `DocenteApp` | `POST .../sesiones` | `registrar_sesion_reforzamiento` | `sesiones_reforzamiento` | — |
| MP-MIS | PROC-MIS-04 | ACT-MIS-04-04 Subir material | `DocenteApp` | `POST .../materiales` | `crear_material_reforzamiento` | `materiales_reforzamiento` | — |
| MP-MIS | PROC-MIS-05 | ACT-MIS-05-01 Registrar incidencia | `DocenteApp` (Convivencia) | `POST /api/incidencias` | `crear_incidencia_convivencia` | `incidencias_convivencia` | — |
| MP-MIS | PROC-MIS-05 | ACT-MIS-05-02 Crear derivación | `DocenteApp` | `POST /api/derivaciones` | `crear_derivacion_externa` | `derivaciones_externas` | — |
| MP-MIS | PROC-MIS-05 | ACT-MIS-05-03 Ver ficha convivencia | `DocenteApp` (Estudiantes) | `GET .../incidencias` | `listar_incidencias` | `incidencias_convivencia` | — |
| MP-EST | PROC-EST-01 | ACT-EST-01-01 Consultar indicadores | `IndicadoresPanel` | `GET /api/indicadores` | `listar_indicadores` | `indicadores_mensuales` | — |
| MP-EST | PROC-EST-01 | ACT-EST-01-02 Calcular indicadores mes | `IndicadoresPanel` | `POST /api/indicadores/calcular` | `calcular_indicadores_mensuales` | `indicadores_mensuales` | — |
| MP-EST | PROC-EST-02 | ACT-EST-02-01 Exportar reporte Excel | `DocenteApp` | `GET /api/reportes/exportar` | `_build_reporte_dataframe` | múltiples | — |
| MP-EST | PROC-EST-02 | ACT-EST-02-02 Ver dashboard resumen | `DocenteApp` (Resumen) | `GET /api/resumen` | `obtener_resumen_dashboard` | agregados | — |
| MP-SOP | PROC-SOP-02 | ACT-SOP-02-01 Cargar Excel SIAGIE | `DocenteApp` / `AdminApp` | `POST /api/upload_siagie` | `registrar_carga_siagie`, predict por fila | `cargas_siagie`, `evaluaciones` | CP-006, RF-05 |
| MP-SOP | PROC-SOP-02 | ACT-SOP-02-02 Auditar cargas | `AdminApp` (SIAGIE) | `GET /api/admin/cargas-siagie` | `listar_cargas_siagie` | `cargas_siagie` | — |
| MP-SOP | PROC-SOP-03 | ACT-SOP-03-01 Ver estado sistema | `AdminApp` | `GET /api/status` | `get_database_status` | `schema_version` | CP-001, RF-01 |
| MP-SOP | PROC-SOP-03 | ACT-SOP-03-02 Activar año escolar | `AdminApp` (Mantenimiento) | `POST /api/admin/anio-escolar` | `activar_anio_escolar` | `configuracion_anio_escolar` | — |
| MP-SOP | PROC-SOP-03 | ACT-SOP-03-03 Limpiar datos demo | `AdminApp` | `DELETE /api/admin/estudiantes/demo` | `eliminar_estudiantes_demo` | `estudiantes` | — |
| MP-SOP | PROC-SOP-03 | ACT-SOP-03-04 Limpiar registros inválidos | — (auto al login) | `DELETE /api/estudiantes/invalidos` | `eliminar_estudiantes_demo` | `estudiantes` | — |
| MP-SOP | PROC-SOP-04 | ACT-SOP-04-01 Gestionar usuarios | `AdminApp` (Usuarios) | `GET /api/admin/usuarios` | `listar_usuarios_sistema` | `usuarios_sistema` | — |
| MP-SOP | PROC-SOP-04 | ACT-SOP-04-02 Gestionar docentes/secciones | `AdminApp` | `GET /api/admin/docentes`, `secciones` | `listar_docentes`, `listar_secciones_institucional` | `docentes`, `secciones` | — |

---

## 2. Matriz inversa — Componente técnico → Proceso

### 2.1 Controladores críticos (`app.py`)

| Endpoint | MP | PROC | Actores |
|----------|-----|------|---------|
| `POST /api/predict` | MP-MIS | PROC-MIS-02 | Docente |
| `POST /api/estudiantes` | MP-MIS | PROC-MIS-01 | Docente |
| `GET /api/resumen` | MP-EST / MP-MIS | PROC-EST-02 / PROC-MIS-03 | Docente, Admin |
| `POST /api/upload_siagie` | MP-SOP | PROC-SOP-02 | Admin, Docente |
| `POST /api/indicadores/calcular` | MP-EST | PROC-EST-01 | Admin, Docente |
| `GET /api/reportes/exportar` | MP-EST | PROC-EST-02 | Docente |
| `POST /api/auth/login` | MP-SOP | PROC-SOP-01 | Todos |

### 2.2 Módulos de modelo (`database/`)

| Módulo | Macroprocesos atendidos |
|--------|-------------------------|
| `repository.py` | MP-MIS, MP-SOP, MP-EST (núcleo) |
| `convivencia.py` | MP-MIS (PROC-MIS-05) |
| `reforzamiento.py` | MP-MIS (PROC-MIS-04) |
| `indicadores.py` | MP-EST (PROC-EST-01) |
| `db_setup.py` | MP-SOP (esquema y seed) |

### 2.3 Componentes frontend

| Componente | Macroprocesos |
|------------|---------------|
| `LoginScreen.jsx` | MP-SOP |
| `AdminApp.jsx` | MP-EST, MP-SOP |
| `DocenteApp.jsx` | MP-MIS, MP-EST (exportación, indicadores propios) |
| `docenteForm.jsx` | MP-MIS (PROC-MIS-02) |
| `IndicadoresPanel.jsx` | MP-EST |
| `validators.js` | Transversal (MP-MIS, MP-SOP) |
| `downloadFile.js` | MP-EST, MP-MIS (exportación, materiales) |

---

## 3. Matriz doble entrada — Requisitos ↔ Implementación

Cruce entre **requisitos funcionales** ([matriz-trazabilidad](../../tests/matriz-trazabilidad.md)) y **procedimientos**:

| RF | PROC | Implementación principal | CP |
|----|------|--------------------------|-----|
| RF-01 | PROC-SOP-03 | `GET /api/status`, `get_database_status` | CP-001 |
| RF-02 | PROC-MIS-02 | `POST /api/predict`, `_build_features` | CP-003 |
| RF-03 | PROC-MIS-02 | `validar_nota_literal` | CP-004 |
| RF-04 | PROC-MIS-02 | `_load_model`, error 500 predict | CP-005 |
| RF-05 | PROC-SOP-02 | `api_upload_siagie` | CP-006 |
| RF-06 | PROC-SOP-02 | validación campo `file` | CP-007 |
| RF-07 | PROC-SOP-02 | manejo Excel vacío/ilegible | CP-008 |
| RF-08 | PROC-MIS-02 | `DocenteApp` + `docenteForm` | CP-010 |
| RF-09 | PROC-SOP-02 | UI resumen post-SIAGIE | CP-012 |
| RF-10 | PROC-MIS-03 | re-análisis desde alertas | CP-013 |

---

## 4. Matriz persistencia — Actividad ↔ Tablas (lectura/escritura)

| ACT | Lectura | Escritura |
|-----|---------|-----------|
| ACT-MIS-02-02 Predicción | `estudiantes`, modelo `.pkl` | `evaluaciones`, `predicciones_riesgo`, `alertas_riesgo` |
| ACT-MIS-01-01 Registro | `secciones` | `estudiantes`, `matriculas` |
| ACT-SOP-02-01 SIAGIE | Excel usuario | `estudiantes`, `evaluaciones`, `cargas_siagie`, `predicciones_riesgo` |
| ACT-EST-01-02 Calcular KPIs | `estudiantes`, `evaluaciones`, `predicciones_riesgo`, `intervenciones` | `indicadores_mensuales` |
| ACT-MIS-04-02 Inscripción taller | `cursos_reforzamiento`, `predicciones_riesgo` | `inscripciones_reforzamiento` |

---

## 5. Cobertura por macroproceso (resumen numérico)

| Macroproceso | Procedimientos | Actividades en matriz | Endpoints API | Tablas |
|--------------|----------------|----------------------|-------------|--------|
| MP-EST | 2 | 4 | 4 | 2 + agregados |
| MP-MIS | 5 | 18 | 25+ | 16 |
| MP-SOP | 4 | 10 | 12+ | 6 |
| **Total** | **11** | **32** | **~45** | **24** |

---

## 6. Uso de esta matriz

- **Informe de tesis:** copiar sección 1 como tabla anexo; referenciar MP/PROC/ACT.
- **Auditoría ISO 9001:** demostrar trazabilidad proceso → evidencia en código y pruebas.
- **Mantenimiento:** al agregar una feature, añadir fila con el mismo esquema de columnas.

---

*Actualizar esta matriz cuando se incorporen fases 14+ del [ROADMAP](../../docs/ROADMAP-FASES.md).*
