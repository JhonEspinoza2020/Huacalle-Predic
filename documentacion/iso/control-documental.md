# Control documental — ISO 9001 §7.5

## 1. Identificación de documentos

| Código | Título | Versión | Ubicación |
|--------|--------|---------|-----------|
| DOC-ISO-00 | Índice ISO | 1.0 | `documentacion/iso/README.md` |
| DOC-ISO-9001 | SGC Calidad | 1.0 | `documentacion/iso/SGC-ISO9001.md` |
| DOC-ISO-25010 | Calidad software | 1.0 | `documentacion/iso/calidad-software-ISO25010.md` |
| DOC-ISO-29119 | Pruebas | 1.0 | `documentacion/iso/pruebas-ISO29119.md` |
| DOC-ISO-27001 | Seguridad | 1.0 | `documentacion/iso/seguridad-ISO27001.md` |
| DOC-TEST-01 | Plan de pruebas | 1.1 | `tests/plan-de-pruebas.md` |
| DOC-TEST-02 | Casos de prueba | 1.0 | `tests/caja-negra/casos-de-prueba.md` |
| DOC-TEST-03 | Matriz trazabilidad | 1.0 | `tests/matriz-trazabilidad.md` |
| DOC-ARQ-01 | Mapeo procesos | — | `MAPEO.md` |
| DOC-REQ-01 | Roadmap fases | — | `docs/ROADMAP-FASES.md` |

## 2. Control de cambios

1. Los cambios se versionan en **Git** (historial, autor, fecha).
2. Cambios en API o requisitos: actualizar roadmap y, si aplica, matriz RF↔CP.
3. Cambios en seguridad: actualizar `seguridad-ISO27001.md` y tests relacionados.
4. Incrementar versión del documento en el encabezado al modificar sustancialmente.

## 3. Distribución

- **Desarrollo:** repositorio completo.
- **Tesis / informe:** carpeta `documentacion/iso/` + `tests/plan-de-pruebas.md`.
- **Operación colegio:** README principal y guía de inicio.

## 4. Retención

- Código y documentación: vida útil del proyecto académico + archivo institucional.
- Registros de prueba: conservar reportes CI y `registro-de-ejecucion.md` por ciclo de entrega.
