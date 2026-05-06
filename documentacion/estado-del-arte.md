# Estado del arte

Síntesis elaborada a partir de los artículos en `articulos-cientificos/` (Artículos 3, 9, 11, 12 y 13). Si se incorporan más PDFs, extender este documento con el mismo esquema: problema, datos, método, resultados y aporte.

---

## 1. Panorama del problema

Los trabajos coinciden en que la deserción es **multicausal** (factores económicos, sociales, de rendimiento, contexto pandémico, infraestructura, entre otros) y que los sistemas educativos necesitan **herramientas de alerta temprana** que articulen datos con acción institucional.

---

## 2. Aprendizaje automático con datos de hogar (Perú)

**Jacha Rojas, Yataco Cañari y Ospina Galindez** publican en *Rev. Iden* (2024) un modelo de ML que utiliza la **Encuesta Nacional de Hogares** para predecir deserción en Perú, enfatizando **variables sociodemográficas** y el vacío que ello llena frente a estudios previos. Subrayan la utilidad de la **detección temprana** para intervenciones y proponen líneas futuras (aprendizaje profundo, modelos híbridos, métodos de conjunto).

**DOI:** https://doi.org/10.46276/rifce.v10i2.2308

**Aporte al estado del arte:** diversificación de fuentes (no solo registros escolares); relevancia para política social y educativa nacional.

---

## 3. Política pública y ML con datos administrativos (Perú)

El documento **«ALERTA ESCUELA: Metodología para el cálculo del riesgo de deserción interanual en el Perú con machine learning»** (Ministerio de Educación, Oficina de Seguimiento y Evaluación Estratégica, primera edición digital, octubre 2024) describe un modelo de **riesgo de deserción interanual** en **Educación Básica Regular (EBR)** usando principalmente **datos administrativos del MINEDU**, con resultados satisfactorios en **precisión y sensibilidad** por niveles (inicial, primaria, secundaria), e integración en el sistema **Alerta Escuela**.

**ISBN:** 978-9972-246-90-6  
**Depósito Legal:** Biblioteca Nacional del Perú N.° 2024-11568

**Aporte al estado del arte:** referencia institucional para validar que el ML sobre datos de gestión es una línea reconocida en Perú; útil para contrastar una propuesta local con el marco nacional.

---

## 4. Instrumentos psicométricos frente a ML

**Rojas-Fernández y Cortés-Sotres** (*Sinéctica*, 2025) desarrollan y validan un **cuestionario de autodetección** del riesgo de abandono en **educación media superior**, aplicado en línea a una muestra de conveniencia de **1.006** estudiantes de escuelas públicas. Reportan **alta consistencia interna** (alfa de Cronbach **0,9187**) y **tres factores** principales en análisis factorial. Sitúan el panorama desde la **observación directa** hasta técnicas de **aprendizaje automático**.

**DOI:** https://doi.org/10.31391/YPQX3872

**Cómo citar:** Rojas-Fernández, G. T., y Cortés-Sotres, J. F. (2025). Desarrollo y validación de un instrumento para identificar al estudiante en riesgo. *Sinéctica, Revista Electrónica de Educación*, (65), e1683.

**Aporte al estado del arte:** el riesgo puede medirse también con **autopercepción estructurada**; complementa, sin reemplazar, modelos basados en registros académicos.

---

## 5. Comparación de modelos predictivos en contexto universitario peruano

**Rivera Vergaray** (*Revista Innovación y Software*, 2021) compara **regresión logística, árboles de decisión, KNN y red neuronal** para predecir deserción académica en la **Universidad Nacional Intercultural de la Amazonia (UNIA)**, usando datos del sistema de gestión académica, procesamiento con **one-hot encoding**, y herramientas como **KNIME** y **Python (Google Colab)**. Los cuatro modelos superan **80% de accuracy**; se concluye la viabilidad de despliegue para apoyar decisiones de gestión.

**Revista:** Innovación y Software, ISSN 2708-0935.

**Aporte al estado del arte:** evidencia de que **varias familias de modelos** pueden ser útiles; destaca **preprocesamiento** y **comparación sistemática** antes de producción.

---

## 6. Escalamiento de modelos e importancia de variables (educación superior)

**Espinoza Melgarejo** implementa modelos de aprendizaje automático para predecir deserción en **Tecsup** (datos **2019–2022**, **38.835** registros). Tras análisis exploratorio, **dummificación** y manejo de correlaciones (p. ej. eliminación de variables redundantes), compara **ocho clasificadores**: regresión logística, k-NN, árbol de decisión, random forest, XGBoost, LightGBM, CatBoost y red neuronal multicapa. Se selecciona **LightGBM** por alto desempeño en conjunto de prueba y brecha moderada frente al entrenamiento.

**Aporte al estado del arte:** refuerza **benchmark de múltiples algoritmos**, **ingeniería de variables** y control de **redundancia** entre predictores.

---

## 7. Síntesis y vacíos

- **Convergencia:** ML y/o instrumentos validados son vías consolidadas para **alerta temprana**; los datos **administrativos** tienen respaldo institucional en Perú (Alerta Escuela).
- **Diversidad de niveles:** hay fuerte énfasis en **educación superior** (artículos 12 y 13) y en **EBR y política nacional** (artículo 9). Un proyecto centrado en **educación inicial** o en un contexto escolar concreto puede argumentar **especificidad contextual** y la necesidad de **validación local** con datos propios.
- **Vacíos frecuentes:** equidad entre subgrupos, explicabilidad para docentes, evaluación longitudinal fuera del conjunto de prueba, y gobernanza de datos.

---

## 8. Posicionamiento del proyecto PredictHuacalle / PredictEdu

El sistema combina **predicción en uso** (API Flask + interfaz) con variables **interpretables en el aula** (asistencia, notas, participación), en la línea de acción temprana que la literatura asocia a mejores resultados cuando se acompaña de intervenciones. Es **coherente** con la lógica de alertas sobre señales académicas del marco nacional (Alerta Escuela), a **escala institucional local** y con un **algoritmo concreto** (Random Forest en el repositorio), comparable en espíritu con los benchmarks de Rivera y Espinoza, los cuales pueden citarse en discusión y trabajos futuros de comparación de modelos.

---

## 9. Referencias rápidas (para completar según norma institucional)

1. Candela Rojas, E. C., et al. (2024). *ALERTA ESCUELA: Metodología para el cálculo del riesgo de deserción interanual en el Perú con machine learning.* MINEDU, OSEE. ISBN 978-9972-246-90-6.
2. Espinoza Melgarejo, J. L. (2025). Implementación de modelos de aprendizaje automático para predecir la deserción estudiantil en Tecsup, 2024. *(Revista según ejemplar completo del PDF.)*
3. Jacha Rojas, J. P., Yataco Cañari, W., y Ospina Galindez, J. A. (2024). Modelo de aprendizaje automático para la predicción del abandono escolar mediante encuestas de hogares. *Rev. Iden*, 10(2), 24-33. https://doi.org/10.46276/rifce.v10i2.2308
4. Rivera Vergaray, K. (2021). Modelo predictivo para la detección temprana de estudiantes con alto riesgo de deserción académica. *Innovación y Software*, 2(2), 6-13. ISSN 2708-0935.
5. Rojas-Fernández, G. T., y Cortés-Sotres, J. F. (2025). Desarrollo y validación de un instrumento para identificar al estudiante en riesgo. *Sinéctica*, (65), e1683. https://doi.org/10.31391/YPQX3872
