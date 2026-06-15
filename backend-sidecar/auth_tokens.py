"""Tokens de sesión para usuarios del colegio (admin / docente)."""

from __future__ import annotations

import os
from typing import Any

from flask import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 horas
SECRET_KEY = os.environ.get(
    "PREDICTEDU_SECRET_KEY",
    "predictedu-huacalle-local-dev-change-in-production",
)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SECRET_KEY, salt="predictedu-auth")


def create_access_token(user: dict[str, Any]) -> str:
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "rol": user["rol"],
        "docente_id": user.get("docente_id"),
    }
    return _serializer().dumps(payload)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None


def extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip() or None
    return request.headers.get("X-Auth-Token") or None
