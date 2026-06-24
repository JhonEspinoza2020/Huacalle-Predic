# Pruebas de caja blanca

Pruebas con **conocimiento de la implementación**: esquema SQLite, repositorio, cabeceras de seguridad y carga del modelo.

| Archivo | Qué valida |
|---------|------------|
| `test_repository.py` | Capa `database/repository.py` |
| `test_persistence.py` | Persistencia tras `/api/predict` |
| `test_security_headers.py` | Middleware de cabeceras HTTP |
| `test_model_loading.py` | Carga de `modelo_rf.pkl` |

```powershell
venv\Scripts\python.exe -m pytest tests/caja-blanca -v
```
