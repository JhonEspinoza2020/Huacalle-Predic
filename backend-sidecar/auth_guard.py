"""Decoradores y helpers de autorización."""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, request

from auth_tokens import decode_access_token, extract_bearer_token

AUTH_DISABLED = os.environ.get("PREDICTEDU_AUTH", "1") == "0"


def auth_is_disabled() -> bool:
    return os.environ.get("PREDICTEDU_AUTH", "1") == "0"

PUBLIC_ROUTES = {
    ("GET", "/api/status"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/recuperar"),
}


def auth_is_public() -> bool:
    return (request.method, request.path) in PUBLIC_ROUTES


def get_current_user() -> dict[str, Any] | None:
    if hasattr(g, "current_user"):
        return g.current_user

    if auth_is_disabled():
        g.current_user = {
            "id": 0,
            "username": "test",
            "rol": "admin",
            "docente_id": 1,
            "nombre_completo": "Usuario de prueba",
            "cargo": "admin",
        }
        return g.current_user

    token = extract_bearer_token(request)
    if not token:
        g.current_user = None
        return None

    payload = decode_access_token(token)
    if not payload:
        g.current_user = None
        return None

    from database.repository import obtener_usuario_por_id

    user = obtener_usuario_por_id(int(payload["user_id"]))
    if user is None or not user.get("activo"):
        g.current_user = None
        return None

    g.current_user = user
    return user


def require_auth(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if auth_is_public():
            return view(*args, **kwargs)
        user = get_current_user()
        if user is None:
            return jsonify({"error": "No autorizado. Inicia sesion."}), 401
        return view(*args, **kwargs)

    return wrapper


def require_roles(*roles: str):
    def decorator(view: Callable):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({"error": "No autorizado. Inicia sesion."}), 401
            if user["rol"] not in roles and user["rol"] != "admin":
                return jsonify({"error": "No tienes permiso para esta accion."}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


def user_can_write(user: dict[str, Any] | None) -> bool:
    if user is None:
        return False
    return user["rol"] in ("admin", "director", "docente")


def user_is_admin(user: dict[str, Any] | None) -> bool:
    return user is not None and user["rol"] == "admin"
