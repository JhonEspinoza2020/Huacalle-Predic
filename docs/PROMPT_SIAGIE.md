# Prompt para generar Excel SIAGIE (PredictEdu)

Copia y pega este texto en ChatGPT, Claude, Gemini u otra IA. Pide el archivo en formato **.xlsx**.

---

## Prompt (copiar desde aquí)

```
Genera un archivo Excel (.xlsx) para importar en un sistema de predicción de riesgo escolar (PredictEdu / SIAGIE).

Contexto:
- Institución: I.E.I. N° 32857 — Huacalle, Perú
- Nivel: 5° grado primaria, sección A
- Bimestre: 1
- Son datos ficticios pero realistas para una demo académica

Columnas obligatorias (exactamente estos nombres en la primera fila):
1. nombre          → texto, nombre completo del estudiante
2. dni             → 8 dígitos, únicos, sin repetir
3. asistencias     → número entero de 0 a 100 (porcentaje)
4. nota_matematica → solo uno de: AD, A, B, C
5. nota_lenguaje   → solo uno de: AD, A, B, C
6. participacion   → número de 0 a 10

Genera exactamente 25 filas de estudiantes con nombres peruanos (apellidos como Quispe, Huaman, Mamani, Rojas, etc.).

Distribución sugerida de riesgo (para que el modelo muestre variedad):
- 5 alumnos con asistencia baja (<55%), notas C/B y participación baja (2-4) → riesgo alto
- 8 alumnos con datos intermedios → riesgo medio
- 12 alumnos con buena asistencia (>75%) y notas A/AD → bajo riesgo

Reglas:
- No dejes celdas vacías en las columnas obligatorias
- DNI de 8 dígitos, todos diferentes, empezando en 72345601
- Notas solo con las letras AD, A, B o C (mayúsculas)

Entrega el archivo Excel listo para descargar.
```

---

## Alternativa rápida (sin IA)

En la raíz del proyecto ejecuta:

```powershell
venv\Scripts\python.exe scripts\generate_siagie_demo.py
```

Eso crea `docs/siagie_demo_5toA.xlsx` con 8 alumnos de ejemplo.

---

## Cómo cargarlo en PredictEdu

1. Arranca Flask: `venv\Scripts\python.exe backend-sidecar\app.py`
2. Abre la app (Tauri o navegador)
3. Clic en **+ Cargar SIAGIE**
4. Selecciona el archivo `.xlsx`
5. Revisa el dashboard y la pestaña **Estudiantes**

---

## Flujo recomendado (registro vs carga masiva)

| Caso | Qué hacer |
|------|-----------|
| **Un alumno nuevo** | Pestaña Resumen → **Registrar alumno** (DNI + nombre) → Buscar por DNI → Analizar |
| **Muchos alumnos** | Generar Excel con el prompt de arriba → **Cargar SIAGIE** |
| **Alumno ya en BD** | Escribir DNI → **Buscar** → completar notas → **Analizar y guardar** |

No uses DNIs inventados en "Analizar" sin registrar antes: el sistema ahora exige que el alumno exista o que registres nombre + DNI juntos.
