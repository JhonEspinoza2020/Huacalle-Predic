# Carpeta de pruebas — PredictEdu / PredictHuacalle

Esta carpeta concentra el **plan de pruebas** y los artefactos que el docente suele solicitar en proyectos de software: estrategia, casos de prueba, trazabilidad y registro de ejecución.

## Contenido

| Archivo | Propósito |
|--------|-----------|
| [plan-de-pruebas.md](./plan-de-pruebas.md) | Plan maestro: objetivos, alcance, tipos de prueba, entorno, criterios de salida. |
| [casos-de-prueba.md](./casos-de-prueba.md) | Casos detallados (ID, precondiciones, pasos, resultado esperado). |
| [matriz-trazabilidad.md](./matriz-trazabilidad.md) | Relación entre requisitos funcionales y casos de prueba. |
| [registro-de-ejecucion.md](./registro-de-ejecucion.md) | Plantilla para documentar corridas (fecha, responsable, resultado). |
| [ejemplos-curl.md](./ejemplos-curl.md) | Comandos para verificar el API Flask sin la interfaz gráfica. |

## Sistema bajo prueba (resumen)

- **Frontend:** aplicación de escritorio **Tauri + React (Vite)**; pantalla principal en `src/App.jsx`.
- **Backend:** **Flask** en `backend-sidecar/app.py`, puerto por defecto `http://127.0.0.1:5000`.
- **Modelo:** Random Forest cargado desde `backend-sidecar/ml_models/modelo_rf.pkl`.

Para ejecutar pruebas manuales de punta a punta, el backend debe estar en ejecución y el modelo presente; véanse precondiciones en cada caso.
