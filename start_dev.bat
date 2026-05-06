@echo off
setlocal

cd /d "%~dp0"

echo Iniciando motor de Python...
start "Edge-PRIDE Python Engine" cmd /k "cd /d "%~dp0backend-sidecar" && pip install -r requirements.txt && python app.py"

echo Iniciando interfaz de Tauri/React...
npm install
if errorlevel 1 (
    echo Error: fallo npm install.
    exit /b 1
)

npm run tauri dev

