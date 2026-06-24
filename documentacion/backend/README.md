# Backend — PredictEdu

Documentación de la capa de servicios del sistema **PredictEdu**.

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [arquitectura-backend.md](./arquitectura-backend.md) | Estructura, controladores, modelos (acceso a datos) y servicios |

## Resumen

| Aspecto | Tecnología |
|---------|------------|
| Framework | Flask 3 |
| Base de datos | SQLite (`database/colegio.db`) |
| ML | scikit-learn + joblib (`modelo_rf.pkl`) |
| Auth | JWT-like con `itsdangerous` (Bearer token) |
| Puerto | `127.0.0.1:5000` |
| Punto de entrada | `backend-sidecar/app.py` |

## Capas (mapeo conceptual)

| Capa solicitada | Ubicación en el proyecto |
|-----------------|--------------------------|
| **Controladores** | Rutas `@app.route` en `app.py` |
| **Modelos** | `database/` — acceso a datos y mapeo fila → dict |
| **Servicios** | `risk_engine.py`, `validators.py`, lógica en helpers de `app.py`, módulos de dominio |

> El proyecto no usa ORM (SQLAlchemy). Los “modelos” son funciones de repositorio sobre SQL directo.
