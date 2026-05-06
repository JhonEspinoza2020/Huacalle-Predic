# Matriz de trazabilidad — Requisitos funcionales ↔ Casos de prueba

Los **RF** (requisitos funcionales) describen comportamiento esperado del sistema PredictEdu. Los **CP** enlazan a `casos-de-prueba.md`.

| ID RF | Descripción breve | Casos de prueba |
|-------|-------------------|-----------------|
| RF-01 | El sistema debe exponer un endpoint de estado que indique si el modelo ML está cargado. | CP-001, CP-002 |
| RF-02 | El sistema debe aceptar predicción unitaria con asistencia (%), notas literales (AD/A/B/C) y participación. | CP-003, CP-010 |
| RF-03 | El sistema debe rechazar notas que no sean literales válidas con error claro. | CP-004 |
| RF-04 | Si el modelo no está disponible, las operaciones de predicción deben fallar con mensaje orientativo. | CP-005, CP-011 |
| RF-05 | El sistema debe procesar archivos Excel SIAGIE-like y devolver resumen por niveles de riesgo y top de estudiantes. | CP-006, CP-012 |
| RF-06 | El sistema debe validar la presencia del archivo en la carga masiva. | CP-007 |
| RF-07 | El sistema debe manejar archivos ilegibles o vacíos sin colgar el servicio. | CP-008, CP-009 |
| RF-08 | La interfaz debe permitir disparar predicción desde formulario y mostrar resultado y mensaje motivacional. | CP-010, CP-014 |
| RF-09 | La interfaz debe permitir cargar Excel y reflejar resumen y alertas. | CP-012 |
| RF-10 | La interfaz debe permitir re-analizar un estudiante desde la lista de alertas. | CP-013 |

---

## Cobertura por área

| Área | RF cubiertos | Observación |
|------|--------------|-------------|
| API estado | RF-01 | Base para diagnóstico antes de E2E. |
| API predict | RF-02, RF-03, RF-04 | Núcleo del producto. |
| API upload | RF-05, RF-06, RF-07 | Integración con datos institucionales. |
| UI | RF-08, RF-09, RF-10 | Tabs no navegables quedan fuera de alcance en plan maestro. |
