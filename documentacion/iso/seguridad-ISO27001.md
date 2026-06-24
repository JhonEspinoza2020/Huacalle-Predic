# Seguridad de la información — ISO/IEC 27001 (familia 27000)

**Alcance:** datos de alumnos, apoderados, evaluaciones y predicciones en instalación **local** (colegio / equipo docente).

---

## 1. Política de seguridad

1. Los datos personales **no se envían a servidores externos** en el flujo normal (motor y BD locales).
2. El acceso al sistema requiere **autenticación** cuando `PREDICTEDU_AUTH=1` (producción recomendada).
3. Las acciones sensibles (admin, borrado demo, año escolar) exigen rol **`admin`**.
4. Las contraseñas se almacenan con **hash** (no texto plano en BD).
5. Los tokens JWT tienen **caducidad**; la UI solicita reingreso al expirar.

---

## 2. Inventario de activos

| Activo | Clasificación | Ubicación |
|--------|---------------|-----------|
| Base SQLite (`colegio.db`) | Confidencial | `backend-sidecar/` |
| Modelo ML | Integridad | `ml_models/modelo_rf.pkl` |
| Tokens de sesión | Confidencial | Memoria cliente / `localStorage` |
| Archivos SIAGIE / materiales | Confidencial | `uploads/`, imports temporales |
| Código fuente | Integridad | Repositorio Git |

---

## 3. Controles implementados (Anexo A — resumen)

| Control ISO 27001:2022 | Implementación PredictEdu |
|------------------------|---------------------------|
| A.5 Políticas de seguridad | Este documento + README |
| A.8 Gestión de activos | Inventario §2 |
| A.9 Control de acceso | JWT + `require_roles` (`auth_guard.py`) |
| A.9.4 Gestión de secretos | Variables de entorno; no commitear `.env` |
| A.10 Criptografía | Hash de contraseñas; HTTPS recomendado si API expuesta en red |
| A.12 Seguridad en operaciones | CI, logs de error en Flask |
| A.14 Seguridad en desarrollo | Revisión de código, SonarQube, validación de entrada |
| A.8.11 Enmascaramiento | DNI visible solo a usuarios autenticados |
| A.8.3 Restricción de acceso | Roles: docente, tutor, admin |

---

## 4. Controles técnicos en código

| Medida | Archivo |
|--------|---------|
| Rutas API protegidas | `auth_guard.py`, `app.py` `@require_roles` |
| Validación de entrada | `validators.py`, `validators.js` |
| Límite tamaño archivo reforzamiento | `app.py` (50 MB, extensiones permitidas) |
| Cabeceras de seguridad HTTP | `security_headers.py` |
| CORS acotado al cliente local | `CORS(app)` en desarrollo |
| Eliminación alumnos demo | Solo rol admin, filtros explícitos |

---

## 5. Gestión de incidentes (resumen)

| Fase | Acción |
|------|--------|
| Detección | Fallos de login, errores 401/403, alertas de integridad BD |
| Contención | Desactivar cuenta comprometida; rotar `SECRET_KEY` JWT |
| Recuperación | Restaurar `colegio.db` desde respaldo institucional |
| Lecciones | Actualizar este documento y tests de regresión |

---

## 6. Evaluación de riesgos (residual)

| Amenaza | Probabilidad | Impacto | Tratamiento |
|---------|--------------|---------|-------------|
| Robo de laptop con BD | Media | Alto | Cifrado de disco OS; política de bloqueo |
| Token JWT robado | Baja | Medio | Caducidad corta; HTTPS en red |
| Inyección SQL | Baja | Alto | Consultas parametrizadas en `repository.py` |
| Carga de malware vía Excel | Media | Medio | Validación columnas; sin macros ejecutadas |

---

## 7. Conformidad

La implementación satisface los controles aplicables a un **sistema escolar local**. Para certificación ISO 27001 formal se requiere auditoría externa, SOA completo y alcance organizacional de la IEI.
