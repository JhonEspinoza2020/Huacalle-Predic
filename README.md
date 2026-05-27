# PredictEdu / Edge-PRIDE

Sistema de predicción de **riesgo de deserción escolar** para la I.E.I. N° 32857 — Huacalle.

**Stack:** Tauri 2 + React + Vite (interfaz) · Flask + scikit-learn (motor local) · SQLite (preparado)

---

## Documentación principal

| Documento | Descripción |
|-----------|-------------|
| **[MAPEO.md](./MAPEO.md)** | **Mapeo completo de todos los procesos** del software (arquitectura, APIs, ML, SIAGIE, BD, diagramas) |
| [documentacion/](./documentacion/) | Marco del proyecto y estado del arte |
| [tests/ejemplos-curl.md](./tests/ejemplos-curl.md) | Pruebas del API con curl/PowerShell |

---

## Requisitos

- [Node.js](https://nodejs.org/) (LTS)
- [Python](https://www.python.org/) 3.10+
- [Rust](https://rustup.rs/) (`rustup`)
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) — carga de trabajo **Desarrollo para el escritorio con C++**
- WebView2 (suele venir en Windows 11)

---

## Inicio rápido

### Opción A — Script automático

```powershell
cd c:\Users\Luz\Desktop\PredictHuacalle-main
.\start_dev.bat
```

### Opción B — Dos terminales (recomendado)

**Terminal 1 — Motor Python (puerto 5000):**

```powershell
.\venv\Scripts\Activate.ps1
python .\backend-sidecar\app.py
```

**Terminal 2 — App de escritorio:**

```powershell
npm install
npm run tauri dev
```

### Modelo de IA (primera vez o si falta el `.pkl`)

```powershell
python .\backend-sidecar\ml_models\train_model.py
```

### Base de datos (opcional, creación del archivo)

```powershell
python .\backend-sidecar\database\db_setup.py
```

---

## Verificar que todo funciona

| Comprobación | URL / acción |
|--------------|--------------|
| Motor Flask | [http://127.0.0.1:5000/api/status](http://127.0.0.1:5000/api/status) → `"model_loaded": true` |
| Interfaz | Ventana **edge-pride** / PredictEdu (Tauri) |
| Raíz `/` en navegador | 404 — **normal** (solo hay rutas `/api/*`) |

---

## Análisis con SonarQube

El proyecto ya incluye `sonar-project.properties`.

1. Genera reportes de pruebas/cobertura Python (opcional pero recomendado):

```powershell
pip install pytest pytest-cov
python -m pytest tests --junitxml=pytest-report.xml --cov=backend-sidecar --cov-report=xml:coverage.xml
```

2. Ejecuta Sonar Scanner desde la raíz:

```powershell
sonar-scanner `
  -Dsonar.host.url=http://localhost:9000 `
  -Dsonar.token=TU_TOKEN
```

> Si no usas cobertura por ahora, Sonar igual corre; solo no mostrará métricas de coverage.

---

## Estructura breve

```
src/                 → React (UI)
src-tauri/           → Tauri (ventana de escritorio)
backend-sidecar/     → Flask + ML + SQLite
MAPEO.md             → Mapeo de procesos (léelo primero para entender el sistema)
```

---

## Exportar MAPEO a PDF (opcional)

Con [Pandoc](https://pandoc.org/) instalado:

```powershell
pandoc MAPEO.md -o MAPEO.pdf --from markdown
```

O abre `MAPEO.md` en GitHub / Cursor / VS Code con vista previa Markdown (los diagramas Mermaid se renderizan en GitHub y en muchos visores).

---

## IDE recomendado

- [VS Code](https://code.visualstudio.com/) o Cursor
- Extensiones: [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode), [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

---

## Licencia y créditos

Proyecto académico — PredictHuacalle / Huacalle-Predic.
