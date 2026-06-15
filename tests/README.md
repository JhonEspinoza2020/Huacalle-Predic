# Carpeta de pruebas — PredictEdu / PredictHuacalle

Esta carpeta concentra el **plan de pruebas** y los artefactos que el docente suele solicitar en proyectos de software: estrategia, casos de prueba, trazabilidad y registro de ejecución.

## Contenido

| Archivo | Propósito |
|--------|-----------|
| [plan-de-pruebas.md](./plan-de-pruebas.md) | Plan maestro: objetivos, alcance, tipos de prueba, entorno, criterios de salida. |
| [casos-de-prueba.md](./casos-de-prueba.md) | Casos detallados (ID, precondiciones, pasos, resultado esperado). |
| [matriz-trazabilidad.md](./matriz-trazabilidad.md) | Relación entre requisitos funcionales y casos de prueba. |
| [registro-de-ejecucion.md](./registro-de-ejecucion.md) | Bitácora de corridas (fecha, responsable, resultado). |
| [ejemplos-curl.md](./ejemplos-curl.md) | Comandos para verificar el API Flask sin la interfaz gráfica. |

## Pruebas automatizadas (pytest)

```powershell
venv\Scripts\python.exe -m pytest tests -v
```

| Archivo | Cubre |
|---------|--------|
| `test_logic.py` | CP-001, CP-002, CP-003, CP-004, CP-005 |
| `test_siagie.py` | CP-006, CP-007, CP-008, CP-009 |
| `test_persistence.py` | Persistencia en SQLite tras `/api/predict` |
| `test_repository.py` | Capa `database/repository.py` |
| `test_reportes.py` | Filtros y exportación Excel |

CI en GitHub Actions: `.github/workflows/ci.yml` (push/PR a `main` o `master`).

## Sistema bajo prueba (resumen)

- **Frontend:** aplicación de escritorio **Tauri + React (Vite)**; pantalla principal en `src/App.jsx`.
- **Backend:** **Flask** en `backend-sidecar/app.py`, puerto por defecto `http://127.0.0.1:5000`.
- **Modelo:** Random Forest cargado desde `backend-sidecar/ml_models/modelo_rf.pkl`.

Para ejecutar pruebas manuales de punta a punta, el backend debe estar en ejecución y el modelo presente; véanse precondiciones en cada caso.
