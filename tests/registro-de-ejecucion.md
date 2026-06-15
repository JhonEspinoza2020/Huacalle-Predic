# Registro de ejecución de pruebas

**Proyecto:** PredictEdu / PredictHuacalle  
**Versión bajo prueba:** commit `c69d93e` (Fase 5 — QA)  
**Ejecutado por:** Automatizado (pytest) + revisión local  
**Fecha:** 2026-06-03  

## Entorno

| Ítem | Valor |
|------|-------|
| SO y versión | Windows 10 (build 26200) |
| Rama / commit Git | `c69d93e` |
| Python | 3.12.7 |
| Node.js | v24.15.0 |
| Modelo `modelo_rf.pkl` presente (Sí/No) | Sí |
| Comando de prueba | `venv\Scripts\python.exe -m pytest tests -v` |
| Resultado global | **24 passed** en 6.37 s |

---

## Resultados por caso

Copie los IDs desde `casos-de-prueba.md`. Marque: **P** = Pasado, **F** = Fallido, **B** = Bloqueado, **N** = No ejecutado.

| ID caso | Resultado (P/F/B/N) | Evidencia (captura, log, nota) | Incidencia # |
|---------|---------------------|--------------------------------|--------------|
| CP-001 | P | `test_api_status_model_loaded` | |
| CP-002 | P | `test_api_status_without_model` | |
| CP-003 | P | `test_predict_endpoint_with_valid_payload` | |
| CP-004 | P | `test_predict_endpoint_missing_data_returns_controlled_error` | |
| CP-005 | P | `test_predict_without_model_returns_500` | |
| CP-006 | P | `test_upload_siagie_valid_excel`, `test_upload_siagie_demo_file` | |
| CP-007 | P | `test_upload_siagie_missing_file` | |
| CP-008 | P | `test_upload_siagie_invalid_excel` | |
| CP-009 | P | `test_upload_siagie_unprocessable_rows` | |
| CP-010 | N | Prueba manual UI — requiere Tauri + backend en ejecución | |
| CP-011 | N | Prueba manual UI — Flask detenido | |
| CP-012 | N | Prueba manual UI — API cubierta por CP-006 | |
| CP-013 | N | Prueba manual UI — pestaña Intervenciones | |
| CP-014 | N | Prueba manual UI — estados de carga en botones | |

### Cobertura adicional (fuera de CP-001…014)

| Área | Tests | Resultado |
|------|-------|-----------|
| Persistencia BD | `test_persistence.py` (4) | P |
| Repositorio | `test_repository.py` (4) | P |
| Reportes / filtros | `test_reportes.py` (2) | P |
| Mapeo notas / carga modelo | `test_logic.py` (2) | P |

---

## Incidencias abiertas

| # | Descripción | Severidad | Estado |
|---|-------------|-----------|--------|
| — | Sin incidencias bloqueantes en ciclo automatizado | — | — |

---

## Conclusión del ciclo

- **¿Criterios de salida cumplidos?** Sí (API y persistencia cubiertas; UI pendiente de corrida manual con docente)
- **Comentarios del evaluador / docente:**  
  - Todos los casos API (CP-001 a CP-009) pasan vía pytest.  
  - CI configurado en `.github/workflows/ci.yml` (push/PR a `main` o `master`).  
  - Casos CP-010 a CP-014 quedan para validación en escritorio con `npm run tauri dev` + Flask.

---

*Adjuntar a la entrega académica si se requiere evidencia formal.*
