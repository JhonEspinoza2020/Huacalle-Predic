# Documentación del proyecto (marco general)

## 1. Problema

La **deserción o interrupción escolar** afecta resultados educativos, trayectorias laborales y cohesión social. En Perú y la región coexisten enfoques basados en **datos administrativos**, **encuestas de hogar**, **instrumentos psicométricos** y **modelos de aprendizaje automático** para anticipar el riesgo y orientar intervenciones.

## 2. Alineación con la implementación técnica

La aplicación **PredictEdu** (I.E.I. N° 32857 Huacalle) consume un backend Flask que expone predicción mediante un **modelo entrenado** (Random Forest serializado en `backend-sidecar/ml_models/modelo_rf.pkl`) usando variables operativas del aula y del registro:

- **Asistencia** (%).
- **Notas literales** en matemática y lenguaje (mapeadas a escala numérica en el backend).
- **Participación** (escala numérica).

Esto encaja con la línea de **detección temprana** y **gestión basada en evidencia** descrita en la literatura y en la política peruana (p. ej. Alerta Escuela, véase `estado-del-arte.md`).

## 3. Fuentes de datos en la literatura revisada

| Enfoque | Ejemplo en la biblioteca | Implicación para esta documentación |
|--------|---------------------------|-------------------------------------|
| Encuestas / sociodemografía | Artículo 3 (ENAHO, variables sociodemográficas) | Enriquece el marco teórico; el MVP del proyecto usa variables más cercanas al aula. |
| Datos administrativos MINEDU | Artículo 9 (Alerta Escuela) | Justifica el uso de señales académicas/administrativas y la integración con gestión. |
| Autoinforme / psicometría | Artículo 11 (cuestionario validado) | Complementa modelos predictivos con percepción del estudiante; es otro tipo de dato. |
| Rendimiento + ML en universidad | Artículos 12 y 13 | Muestran comparación de algoritmos e importancia de variables; útil para la sección de métodos y discusión. |

## 4. Alcance documental recomendado (informe o tesis)

- **Objetivos**: predicción de riesgo para apoyo oportuno (sin sustituir el criterio docente).
- **Datos y variables**: definición operacional de asistencia, notas y participación; origen (SIAGIE, formulario u otras fuentes).
- **Modelo**: familia de algoritmo, métricas (exactitud, sensibilidad, etc.), limitaciones y posibles sesgos.
- **Ética y uso**: transparencia con familias y estudiantes; evitar etiquetado perjudicial.
- **Referencias**: citar los trabajos listados en `estado-del-arte.md` según la norma que exija la institución (APA, Vancouver, etc.).

## 5. Limitación

La síntesis bibliográfica se basa en los artículos PDF actualmente referenciados en esta carpeta. Cualquier nuevo artículo añadido a `articulos-cientificos/` debería incorporarse explícitamente al estado del arte.
