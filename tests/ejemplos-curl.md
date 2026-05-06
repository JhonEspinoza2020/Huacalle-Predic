# Ejemplos de verificación del API (curl)

**Base URL:** `http://127.0.0.1:5000`  
Ejecutar desde PowerShell o terminal con el servidor Flask en marcha (`python app.py` desde `backend-sidecar` o según el proyecto).

---

## 1. Estado del servicio

```bash
curl -s http://127.0.0.1:5000/api/status
```

Esperado: JSON con `status`, `message`, `model_loaded`.

---

## 2. Predicción unitaria (JSON)

PowerShell (una línea):

```powershell
curl.exe -s -X POST http://127.0.0.1:5000/api/predict -H "Content-Type: application/json" -d "{\"asistencias\": 80, \"nota_matematica\": \"A\", \"nota_lenguaje\": \"B\", \"participacion\": 6}"
```

Esperado: HTTP 200 y cuerpo con `prediction`, `confidence`.

**Caso negativo (nota inválida):**

```powershell
curl.exe -s -w "\nHTTP_CODE:%{http_code}\n" -X POST http://127.0.0.1:5000/api/predict -H "Content-Type: application/json" -d "{\"asistencias\": 80, \"nota_matematica\": \"X\", \"nota_lenguaje\": \"A\", \"participacion\": 6}"
```

Esperado: código 400 y mensaje de error en JSON.

---

## 3. Carga SIAGIE (multipart)

Sustituya la ruta por un Excel real de prueba:

```powershell
curl.exe -s -X POST http://127.0.0.1:5000/api/upload_siagie -F "file=@C:\ruta\ejemplo_siagie.xlsx"
```

Esperado: HTTP 200 con `summary`, `total_students`, `top_5_high_risk`.

---

## Notas

- Si aparece **Connection refused**, el backend no está escuchando en el puerto 5000.
- Si aparece error de modelo, verificar `backend-sidecar/ml_models/modelo_rf.pkl` y el entrenamiento previo.
