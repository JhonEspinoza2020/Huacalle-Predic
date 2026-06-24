# Cumplimiento normativo ISO — PredictEdu

Documentación del **Sistema de Gestión de Calidad (SGC)** y controles técnicos alineados con las normas solicitadas para el proyecto **PredictEdu** (I.E.I. N° 32857 Huacalle).

| Norma | Enfoque en PredictEdu | Documento |
|-------|----------------------|-----------|
| **ISO 9001** | Gestión de calidad, procesos, mejora continua | [SGC-ISO9001.md](./SGC-ISO9001.md) |
| **ISO/IEC 25000** (modelo **25010**) | Calidad del producto software | [calidad-software-ISO25010.md](./calidad-software-ISO25010.md) |
| **ISO/IEC/IEEE 29119** | Política, planificación y ejecución de pruebas | [pruebas-ISO29119.md](./pruebas-ISO29119.md) |
| **ISO/IEC 27000** (referencia **27001**) | Seguridad de la información | [seguridad-ISO27001.md](./seguridad-ISO27001.md) |

## Artefactos vinculados

| Artefacto | Ubicación | Norma |
|-----------|-----------|-------|
| Plan de pruebas | [tests/plan-de-pruebas.md](../../tests/plan-de-pruebas.md) | ISO 29119-3 |
| Casos de prueba | [tests/caja-negra/casos-de-prueba.md](../../tests/caja-negra/casos-de-prueba.md) | ISO 29119-4 |
| Matriz de trazabilidad | [tests/matriz-trazabilidad.md](../../tests/matriz-trazabilidad.md) | ISO 29119 / 9001 |
| Registro de ejecución | [tests/registro-de-ejecucion.md](../../tests/registro-de-ejecucion.md) | ISO 29119-3 |
| CI automatizada | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | ISO 9001 / 29119 |
| Cobertura y calidad estática | `pytest-cov`, SonarQube (`sonar-project.properties`) | ISO 25010 / 9001 |
| Control documental | [control-documental.md](./control-documental.md) | ISO 9001 §7.5 |

## Declaración de conformidad

PredictEdu implementa **controles documentados y evidencias técnicas** alineadas con las normas anteriores. La certificación oficial ISO corresponde a una auditoría externa por un organismo acreditado; este repositorio provee la **base de cumplimiento** exigible en proyectos académicos e institucionales.

**Versión del paquete ISO:** 1.0  
**Fecha:** 2026-06-03  
**Responsable:** Equipo PredictEdu / I.E.I. Huacalle
