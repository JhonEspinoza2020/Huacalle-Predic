# Plan de pruebas — PredictEdu (I.E.I. N° 32857 Huacalle)

**Versión:** 1.0  
**Proyecto:** PredictHuacalle — aplicación PredictEdu con predicción de riesgo académico.  
**Alcance:** Backend Flask (`backend-sidecar`), cliente Tauri + React (`src/`, `src-tauri/`).

---

## 1. Objetivo

Definir la estrategia y el alcance de las pruebas para **validar el comportamiento funcional y la estabilidad** del sistema: comprobación del motor de predicción, integración frontend–backend y manejo de errores previsible (validación de datos, archivo SIAGIE, modelo ausente).

---

## 2. Alcance

### 2.1 Incluido

- Endpoint `GET /api/status` (estado del servicio y carga del modelo).
- Endpoint `POST /api/predict` (predicción unitaria con JSON: asistencias, notas literales AD/A/B/C, participación).
- Endpoint `POST /api/upload_siagie` (carga de Excel con columnas compatibles).
- Interfaz: formulario “Simular análisis”, botón “Cargar SIAGIE”, lista de alertas y panel “Resultado del motor”.
- Mensajes de error visibles en UI cuando el servidor responde con error o no está disponible.

### 2.2 Fuera de alcance (versión actual)

- Pruebas de carga y estrés (miles de peticiones concurrentes).
- Pruebas de seguridad profunda (pentesting); solo comprobaciones básicas de validación de entrada en API.
- Automatización continua en CI (puede añadirse en una fase posterior).
- Pestañas “Estudiantes” e “Intervenciones” (en la UI actual son elementos visuales sin navegación implementada).

---

## 3. Referencias técnicas

| Componente | Ubicación |
|------------|-----------|
| API Flask | `backend-sidecar/app.py` |
| Modelo ML | `backend-sidecar/ml_models/modelo_rf.pkl` |
| Cliente web embebido en Tauri | `src/App.jsx` |
| URL base API (desarrollo) | `http://127.0.0.1:5000` |

Reglas de negocio relevantes para pruebas:

- Notas aceptadas en predicción unitaria: **AD, A, B, C** (mapeo numérico interno 4–1).
- Si el modelo no existe: API responde **500** con mensaje indicando ejecutar entrenamiento.
- Carga masiva: columnas pueden tener nombres alternativos (p. ej. `asistencia`, `matematica`); filas inválidas se omiten; si ninguna fila es válida, respuesta **400**.

---

## 4. Tipos de prueba

| Tipo | Descripción | Responsable sugerido |
|------|-------------|----------------------|
| **Pruebas unitarias (API)** | Verificar respuestas HTTP y cuerpo JSON de cada endpoint con herramientas como curl, Postman o script. | Desarrollador / tester |
| **Pruebas de integración** | Cliente Tauri llamando al Flask real en la misma máquina; flujos completos de formulario y subida de archivo. | Tester |
| **Pruebas de sistema** | Escenario end-to-end: iniciar backend, iniciar `npm run tauri dev`, ejecutar todos los casos de **prioridad Alta** en `casos-de-prueba.md`. | Tester / docente |
| **Pruebas de regresión** | Repetir casos marcados como “críticos” tras cada cambio en `app.py` o `App.jsx`. | Desarrollador |
| **Pruebas de usabilidad (ligera)** | Claridad de mensajes, estados de carga (“Analizando…”, “Procesando SIAGIE…”). | Usuario piloto / docente |

---

## 5. Entorno de pruebas

| Ítem | Valor recomendado |
|------|-------------------|
| SO | Windows 10/11 (alineado con el entorno del proyecto) |
| Python | Versión compatible con dependencias en `backend-sidecar` |
| Node.js | Compatible con Vite/Tauri del `package.json` |
| Navegador | No obligatorio para Tauri; opcional para depuración si se usa `vite` en modo web |
| Datos | Excel de prueba con columnas: asistencias, nota_matematica, nota_lenguaje, participacion (y variante de nombres según casos) |

---

## 6. Criterios de entrada

- Código sincronizado con la versión a probar.
- Dependencias instaladas (`npm install`, entorno virtual Python con Flask, pandas, joblib, etc.).
- Archivo `modelo_rf.pkl` presente si se prueban predicciones exitosas (casos positivos).

---

## 7. Criterios de salida

- Todos los casos **críticos** (ver `casos-de-prueba.md`, columna Prioridad **Alta**) ejecutados y **Pasado** o con incidencia registrada y plan de corrección.
- Sin bloqueos que impidan predicción unitaria ni carga SIAGIE en escenario feliz.
- Registro de ejecución completado en `registro-de-ejecucion.md` (o anexo).

---

## 8. Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Backend apagado mientras se usa la UI | Alto | Verificar `GET /api/status` antes de pruebas E2E; documentar orden de arranque. |
| Modelo `.pkl` ausente | Alto | Caso CP-005; entrenar con `train_model.py` según documentación del proyecto. |
| Excel con columnas incorrectas | Medio | Casos CP-008–CP-009; plantilla de columnas en documentación de casos. |
| CORS o firewall bloqueando localhost | Bajo | Uso de `127.0.0.1` y puerto 5000 explícito en código. |

---

## 9. Cronograma sugerido (académico)

| Fase | Actividad | Duración orientativa |
|------|-----------|----------------------|
| 1 | Revisión del plan y preparación de datos (.xlsx de prueba) | 1 sesión |
| 2 | Pruebas API (curl / Postman) | 1 sesión |
| 3 | Pruebas integradas en Tauri | 1–2 sesiones |
| 4 | Registro de resultados y retrospectiva | 0.5 sesión |

---

## 10. Documentos relacionados

- `casos-de-prueba.md` — especificación ejecutable de cada caso.
- `matriz-trazabilidad.md` — trazabilidad requisito ↔ caso.
- `registro-de-ejecucion.md` — bitácora de corridas.
- `ejemplos-curl.md` — verificación rápida del backend.
