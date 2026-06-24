# Carpeta de pruebas — PredictEdu / PredictHuacalle

Estructura alineada con **ISO/IEC/IEEE 29119** y con los tipos de prueba del plan maestro.

## Estructura

```
tests/
├── caja-negra/      # Comportamiento externo (API HTTP, casos manuales)
├── caja-blanca/     # Implementación interna (BD, repositorio, seguridad)
├── unitarias/       # Funciones y módulos aislados
├── plan-de-pruebas.md
├── matriz-trazabilidad.md
└── registro-de-ejecucion.md
```

| Carpeta | Técnica | README |
|---------|---------|--------|
| [caja-negra/](./caja-negra/) | Caja negra — entradas/salidas sin detalle interno | Casos CP + `pytest` API |
| [caja-blanca/](./caja-blanca/) | Caja blanca — esquema, repositorio, cabeceras | Tests de estructura |
| [unitarias/](./unitarias/) | Unitarias — validadores, motor de riesgo, notas | Funciones puras |

## Documentación de planificación

| Archivo | Propósito |
|--------|-----------|
| [plan-de-pruebas.md](./plan-de-pruebas.md) | Plan maestro: objetivos, alcance, entorno, criterios de salida. |
| [caja-negra/casos-de-prueba.md](./caja-negra/casos-de-prueba.md) | Casos detallados (ID, pasos, resultado esperado). |
| [matriz-trazabilidad.md](./matriz-trazabilidad.md) | Relación requisitos ↔ casos de prueba. |
| [registro-de-ejecucion.md](./registro-de-ejecucion.md) | Bitácora de corridas. |
| [caja-negra/ejemplos-curl.md](./caja-negra/ejemplos-curl.md) | Verificación manual del API Flask. |

## Ejecutar pytest

```powershell
# Suite completa
venv\Scripts\python.exe -m pytest tests -v

# Por tipo
venv\Scripts\python.exe -m pytest tests/unitarias -v
venv\Scripts\python.exe -m pytest tests/caja-blanca -v
venv\Scripts\python.exe -m pytest tests/caja-negra -v
```

CI: `.github/workflows/ci.yml` · SonarQube: `run_sonar.bat`

## Sistema bajo prueba

- **Frontend:** Tauri + React (Vite) — `src/`
- **Backend:** Flask — `backend-sidecar/app.py` (`http://127.0.0.1:5000`)
- **Modelo:** `backend-sidecar/ml_models/modelo_rf.pkl`
