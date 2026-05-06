# Casos de prueba — PredictEdu

Convenciones:

- **ID:** identificador único.
- **Prioridad:** Alta (bloqueante para demo), Media, Baja.
- **Tipo:** API, UI, Integración.

---

## API — Estado y salud

### CP-001 — Estado del servicio con modelo cargado

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | API |
| **Precondiciones** | Flask ejecutándose; `modelo_rf.pkl` presente. |
| **Pasos** | 1. Enviar `GET http://127.0.0.1:5000/api/status`. |
| **Resultado esperado** | HTTP 200. Cuerpo JSON con `"status": "ok"`, `"model_loaded": true`. |

### CP-002 — Estado del servicio sin modelo

| Campo | Valor |
|--------|--------|
| **Prioridad** | Media |
| **Tipo** | API |
| **Precondiciones** | Flask ejecutándose; archivo del modelo renombrado o ausente temporalmente. |
| **Pasos** | 1. `GET /api/status`. |
| **Resultado esperado** | HTTP 200 (el endpoint de estado puede seguir respondiendo); `"model_loaded": false`. |

---

## API — Predicción unitaria (`POST /api/predict`)

### CP-003 — Predicción válida (notas literales)

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. |
| **Pasos** | 1. POST JSON: `{"asistencias": 85, "nota_matematica": "A", "nota_lenguaje": "B", "participacion": 7}`. |
| **Resultado esperado** | HTTP 200. Campos: `prediction` en {"Alto Riesgo","Bajo Riesgo"}, `confidence` numérico, `model`, `scale`. |

### CP-004 — Notas inválidas

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. |
| **Pasos** | 1. POST JSON con `nota_matematica`: `"X"` o vacío. |
| **Resultado esperado** | HTTP 400. JSON con `error` que indique literales AD, A, B o C. |

### CP-005 — Modelo no disponible

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | API |
| **Precondiciones** | Sin archivo de modelo (misma condición que CP-002). |
| **Pasos** | 1. POST `/api/predict` con payload válido. |
| **Resultado esperado** | HTTP 500. Mensaje sobre modelo no encontrado / ejecutar `train_model.py`. |

---

## API — Carga SIAGIE (`POST /api/upload_siagie`)

### CP-006 — Excel válido con columnas estándar

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. Archivo `.xlsx` con al menos una fila de datos y columnas: `asistencias`, `nota_matematica`, `nota_lenguaje`, `participacion`, `nombre` (opcional). |
| **Pasos** | 1. POST `multipart/form-data` con campo `file` = Excel. |
| **Resultado esperado** | HTTP 200. JSON con `summary` (alto/medio/bajo), `total_students` ≥ 1, `top_5_high_risk` (lista ≤ 5). |

### CP-007 — Sin archivo en la petición

| Campo | Valor |
|--------|--------|
| **Prioridad** | Media |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. |
| **Pasos** | 1. POST sin campo `file`. |
| **Resultado esperado** | HTTP 400. Mensaje sobre falta de archivo. |

### CP-008 — Archivo no legible como Excel

| Campo | Valor |
|--------|--------|
| **Prioridad** | Media |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. |
| **Pasos** | 1. Subir un `.txt` renombrado a `.xlsx` o archivo corrupto. |
| **Resultado esperado** | HTTP 400. Error de lectura de Excel. |

### CP-009 — Excel sin filas procesables

| Campo | Valor |
|--------|--------|
| **Prioridad** | Media |
| **Tipo** | API |
| **Precondiciones** | Modelo cargado. Excel con columnas incorrectas o datos que fallen en todas las filas. |
| **Pasos** | 1. Subir archivo. |
| **Resultado esperado** | HTTP 400. Mensaje de no poder procesar filas / verificar columnas. |

---

## UI + Integración (Tauri + React)

### CP-010 — Análisis desde formulario

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | Integración |
| **Precondiciones** | Backend y app Tauri en ejecución; modelo presente. |
| **Pasos** | 1. Completar asistencia, notas y participación. 2. Clic en “Analizar”. |
| **Resultado esperado** | Panel “Resultado del motor” muestra riesgo y confianza; contadores de resumen se incrementan; sin mensaje de error rojo. |

### CP-011 — Backend apagado (formulario)

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | Integración |
| **Precondiciones** | Solo frontend Tauri; Flask detenido. |
| **Pasos** | 1. Enviar formulario “Analizar”. |
| **Resultado esperado** | Mensaje de error en UI (fallo de red / no se pudo obtener predicción). |

### CP-012 — Carga SIAGIE exitosa

| Campo | Valor |
|--------|--------|
| **Prioridad** | Alta |
| **Tipo** | Integración |
| **Precondiciones** | Backend con modelo; archivo Excel válido (CP-006). |
| **Pasos** | 1. Clic “+ Cargar SIAGIE”. 2. Elegir `.xlsx`. |
| **Resultado esperado** | Tarjetas de resumen actualizadas; lista de alertas puede mostrar top riesgo; sin error. |

### CP-013 — Botón “Registrar acción” en alerta

| Campo | Valor |
|--------|--------|
| **Prioridad** | Media |
| **Tipo** | Integración |
| **Precondiciones** | CP-012 ejecutado o datos de alerta visibles. |
| **Pasos** | 1. Clic en “Registrar acción” para un estudiante. |
| **Resultado esperado** | Se dispara predicción unitaria con datos de ese estudiante; panel de resultado actualizado. |

### CP-014 — Estados de carga

| Campo | Valor |
|--------|--------|
| **Prioridad** | Baja |
| **Tipo** | UI |
| **Precondiciones** | Backend lento o red local estable. |
| **Pasos** | 1. Observar botones durante “Analizar” y “Procesando SIAGIE…”. |
| **Resultado esperado** | Botones deshabilitados o texto de carga visible; no doble envío accidental evidente. |

---

## Resumen de prioridades

| Prioridad | Cantidad | IDs |
|-----------|----------|-----|
| Alta | 8 | CP-001, CP-003, CP-004, CP-005, CP-006, CP-010, CP-011, CP-012 |
| Media | 5 | CP-002, CP-007, CP-008, CP-009, CP-013 |
| Baja | 1 | CP-014 |
