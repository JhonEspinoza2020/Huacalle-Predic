@echo off
setlocal

cd /d "%~dp0"

echo Generando reportes de pruebas y cobertura...
call venv\Scripts\python.exe -m pip install pytest pytest-cov -q
call venv\Scripts\python.exe -m pytest tests --junitxml=pytest-report.xml --cov=backend-sidecar --cov-report=xml:coverage.xml -q
if errorlevel 1 (
    echo Error: fallaron las pruebas.
    exit /b 1
)

if "%SONAR_TOKEN%"=="" (
    echo.
    echo Falta la variable SONAR_TOKEN.
    echo 1. Abre http://localhost:9000 ^(admin / admin^)
    echo 2. Crea un proyecto y genera un token en My Account ^> Security
    echo 3. Ejecuta: set SONAR_TOKEN=tu_token
    echo 4. Vuelve a correr run_sonar.bat
    exit /b 1
)

echo Ejecutando Sonar Scanner via Docker...
docker run --rm ^
  -e SONAR_HOST_URL=http://host.docker.internal:9000 ^
  -e SONAR_TOKEN=%SONAR_TOKEN% ^
  -v "%cd%:/usr/src" ^
  sonarsource/sonar-scanner-cli
