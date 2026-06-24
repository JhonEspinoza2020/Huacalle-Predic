# Modelo de calidad de software — ISO/IEC 25010 (serie 25000)

Evaluación de **PredictEdu** según las características de calidad del modelo **SQuaRE**.

---

## 1. Características funcionales

| Subcaracterística | Cumplimiento en PredictEdu | Evidencia |
|-------------------|---------------------------|-----------|
| Completitud funcional | Fases 6–13: matrícula, alertas, reforzamiento, convivencia, indicadores, admin | `docs/ROADMAP-FASES.md` |
| Corrección funcional | Validación de entrada API y UI | `validators.py`, `validators.js` |
| Pertinencia funcional | Orientado a deserción y acción docente, no solo nota | `risk_engine.py`, alertas |

---

## 2. Eficiencia de desempeño

| Aspecto | Implementación |
|---------|----------------|
| Tiempo de respuesta | Motor local Flask; predicción en memoria (Random Forest) |
| Uso de recursos | App de escritorio Tauri; BD SQLite en disco local |
| Escalabilidad | Diseño para una IEI (~cientos de alumnos), no nube masiva |

---

## 3. Compatibilidad

| Subcaracterística | Detalle |
|-------------------|---------|
| Coexistencia | Backend en `127.0.0.1:5000`; no interfiere con otros puertos por defecto |
| Interoperabilidad | Importación SIAGIE (Excel); export XLSX de reportes |

---

## 4. Usabilidad

| Subcaracterística | Detalle |
|-------------------|---------|
| Reconocibilidad | UI por pestañas (Resumen, Estudiantes, Intervenciones…) |
| Aprendizaje | Cuentas demo en README; formulario guiado por pasos |
| Operabilidad | Mensajes de error en español con tildes; estados de carga |
| Protección ante errores | Validación antes de enviar; confirmación en acciones destructivas (admin) |
| Estética | Interfaz oscura consistente; diseño base en **Figma**, implementación con **Tailwind** |

---

## 5. Fiabilidad

| Subcaracterística | Detalle |
|-------------------|---------|
| Madurez | Manejo de modelo ausente, archivo SIAGIE inválido, sesión expirada |
| Disponibilidad | Modo offline local; indicador `systemReady` en UI |
| Recuperabilidad | BD transaccional SQLite; sin borrado masivo sin rol admin |

---

## 6. Seguridad

Ver [seguridad-ISO27001.md](./seguridad-ISO27001.md). Resumen: autenticación, autorización por rol, cabeceras HTTP de endurecimiento, datos en local.

---

## 7. Mantenibilidad

| Subcaracterística | Detalle |
|-------------------|---------|
| Modularidad | `repository.py`, módulos por dominio (`indicadores.py`, `convivencia.py`) |
| Reusabilidad | Componentes React (`docenteForm.jsx`, `IndicadoresPanel.jsx`) |
| Analizabilidad | `MAPEO.md`, SonarQube, tipado en validadores |
| Modificabilidad | Roadmap por fases; tests por módulo |
| Capacidad de prueba | `tests/caja-negra/`, `tests/caja-blanca/`, `tests/unitarias/`, fixture `isolated_db` |

---

## 8. Portabilidad

| Subcaracterística | Detalle |
|-------------------|---------|
| Adaptabilidad | Variables de entorno (`PREDICTEDU_AUTH`) |
| Instalabilidad | README, `start_dev.bat`, `requirements.txt` |
| Reemplazabilidad | Modelo ML intercambiable (`modelo_rf.pkl`) |

---

## 9. Resumen de conformidad 25010

PredictEdu cubre de forma **documentada y verificable** las ocho características del modelo ISO/IEC 25010. Las brechas conocidas (p. ej. pruebas de carga) quedan fuera de alcance institucional y se registran en el plan de pruebas.
