# Frontend — PredictEdu

Documentación de la capa de presentación del sistema **PredictEdu**.

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [arquitectura-frontend.md](./arquitectura-frontend.md) | Estructura del proyecto, componentes, rutas y comunicación con el backend |

## Resumen

| Aspecto | Tecnología |
|---------|------------|
| Framework | React 19 |
| Build | Vite 7 |
| Estilos | Tailwind CSS 4 |
| Escritorio | Tauri 2 (WebView2 en Windows) |
| Enrutamiento | Por rol y pestañas internas (sin React Router) |
| API | `fetch` + JWT en `localStorage` |
| Backend | Flask en `http://127.0.0.1:5000` |
