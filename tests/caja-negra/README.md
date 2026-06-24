# Pruebas de caja negra

Pruebas del **comportamiento observable** del sistema (entradas/salidas HTTP) sin depender del detalle interno de cada función.

| Archivo | Qué valida |
|---------|------------|
| `test_logic.py` | `/api/status`, `/api/predict` (CP-001 … CP-005) |
| `test_auth.py` | Login, sesión y permisos |
| `test_admin.py` | Endpoints de administración |
| `test_siagie.py` | Carga masiva SIAGIE |
| `test_reportes.py` | Filtros y exportación |
| `test_matricula.py` | Matrícula y secciones |
| `test_apoderados.py` | Contactos de apoderados |
| `test_intervenciones.py` | Intervenciones docentes |
| `test_alertas_seguimiento.py` | Alertas y seguimiento |
| `test_convivencia.py` | Derivaciones e incidencias |
| `test_reforzamiento.py` | Talleres de reforzamiento |
| `test_indicadores.py` | Indicadores mensuales |

### Casos manuales (E2E / checklist)

- [casos-de-prueba.md](./casos-de-prueba.md)
- [ejemplos-curl.md](./ejemplos-curl.md)

```powershell
venv\Scripts\python.exe -m pytest tests/caja-negra -v
```
