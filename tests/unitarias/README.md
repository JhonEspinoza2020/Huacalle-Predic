# Pruebas unitarias

Funciones y módulos **aislados**, sin cliente HTTP ni flujo completo de API.

| Archivo | Qué valida |
|---------|------------|
| `test_validators.py` | Reglas de validación (`validators.py`) |
| `test_risk_engine.py` | Matriz pedagógica de riesgo (`risk_engine.py`) |
| `test_grade_mapping.py` | Conversión de notas literales AD/A/B/C |

```powershell
venv\Scripts\python.exe -m pytest tests/unitarias -v
```
