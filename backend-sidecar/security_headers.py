"""Cabeceras HTTP de endurecimiento (ISO/IEC 27001 — controles técnicos)."""

from __future__ import annotations

from flask import Flask, Response


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _apply_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        return response
