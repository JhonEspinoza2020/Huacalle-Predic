# Verificación de cabeceras de seguridad (ISO 27001)

import sys
from pathlib import Path

from api_helpers import load_app_with_db


def test_security_headers_on_status(isolated_db, monkeypatch):
    app_module = load_app_with_db(monkeypatch, isolated_db, auth_enabled=False)
    client = app_module.app.test_client()
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
