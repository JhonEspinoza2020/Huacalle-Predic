# Diseño de interfaz con Figma

**Proyecto:** PredictEdu — I.E.I. N° 32857 Huacalle  
**Herramienta:** [Figma](https://www.figma.com/) (diseño UI/UX)

---

## Qué se hizo en Figma

El diseño visual de PredictEdu se elaboró en **Figma** antes y durante la implementación. En el archivo de diseño se definieron:

- **Pantallas principales:** inicio de sesión, panel docente (resumen, estudiantes, alertas, intervenciones, reforzamiento) y panel de administración.
- **Jerarquía y navegación:** pestañas, formularios por pasos y tablas de listado.
- **Estilo visual:** tema oscuro institucional, tipografía legible, contraste para uso en aula y paleta de acentos (azul, ámbar, esmeralda) para estados de riesgo y acciones.
- **Componentes reutilizables:** campos de formulario, tarjetas de indicadores, badges de riesgo y botones primarios/secundarios.

Figma sirvió como **referencia de diseño** para traducir las pantallas a código en React.

---

## Implementación en código

| Figma (diseño) | Código (implementación) |
|----------------|-------------------------|
| Marcos y componentes visuales | Componentes React en `src/` |
| Espaciado, color y tipografía | **Tailwind CSS 4** (`src/index.css` y clases en JSX) |
| Aplicación de escritorio | **Tauri 2** (`src-tauri/`) |

Archivos de referencia en el repositorio: `LoginScreen.jsx`, `DocenteApp.jsx`, `AdminApp.jsx`, `docenteForm.jsx`, `IndicadoresPanel.jsx`.

---

## Archivo Figma

> Añadir aquí el enlace al proyecto o archivo Figma del equipo cuando esté disponible para compartir en la entrega:
>
> `https://www.figma.com/design/...`

---

## Relación con la documentación de calidad

La coherencia estética de la interfaz se evalúa en [calidad-software-ISO25010.md](./iso/calidad-software-ISO25010.md) (característica *apropiación* / estética). El diseño en Figma es la base visual; la verificación final es la aplicación en ejecución (`npm run tauri dev`).
