"""Validaciones de entrada para la API."""

from __future__ import annotations

import re

VALID_GRADES = frozenset({"AD", "A", "B", "C"})


def normalizar_dni(dni: str) -> str:
    limpio = re.sub(r"\D", "", str(dni or "").strip())
    if len(limpio) != 8:
        raise ValueError("El DNI debe tener exactamente 8 dígitos.")
    return limpio


def validar_nombre_completo(nombre: str) -> str:
    limpio = " ".join(str(nombre or "").split())
    if len(limpio) < 3:
        raise ValueError("El nombre completo debe tener al menos 3 caracteres.")
    if len(limpio) > 120:
        raise ValueError("El nombre completo es demasiado largo.")
    return limpio


def validar_asistencias(valor) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError("La asistencia debe ser un número entre 0 y 100.") from None
    if numero < 0 or numero > 100:
        raise ValueError("La asistencia debe estar entre 0 y 100.")
    return numero


def validar_participacion(valor) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError("La participación debe ser un número entre 0 y 10.") from None
    if numero < 0 or numero > 10:
        raise ValueError("La participación debe estar entre 0 y 10.")
    return numero


def validar_bimestre(valor) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError("El bimestre debe ser un número entre 1 y 4.") from None
    if numero < 1 or numero > 4:
        raise ValueError("El bimestre debe estar entre 1 y 4.")
    return numero


def validar_nota_literal(nota: str, campo: str = "nota") -> str:
    limpia = str(nota or "").strip().upper()
    if limpia not in VALID_GRADES:
        raise ValueError(f"{campo}: usa AD, A, B o C.")
    return limpia


def validar_telefono(telefono: str) -> str:
    limpio = re.sub(r"\D", "", str(telefono or "").strip())
    if len(limpio) != 9:
        raise ValueError("El teléfono debe tener 9 dígitos (ej. 987654321).")
    if not limpio.startswith("9"):
        raise ValueError("El teléfono móvil peruano debe comenzar con 9.")
    return limpio


def validar_username(username: str) -> str:
    limpio = str(username or "").strip()
    if len(limpio) < 3:
        raise ValueError("El usuario debe tener al menos 3 caracteres.")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", limpio):
        raise ValueError(
            "El usuario solo puede contener letras, números, punto, guion o guion bajo."
        )
    return limpio


PARENTESCOS_VALIDOS = frozenset({"padre", "madre", "apoderado", "tutor", "otro"})


def validar_parentesco(parentesco: str) -> str:
    limpio = str(parentesco or "apoderado").strip().lower()
    if limpio not in PARENTESCOS_VALIDOS:
        raise ValueError("Parentesco no válido. Usa padre, madre, apoderado, tutor u otro.")
    return limpio


def validar_dni_opcional(dni: str | None) -> str | None:
    limpio = re.sub(r"\D", "", str(dni or "").strip())
    if not limpio:
        return None
    if len(limpio) != 8:
        raise ValueError("El DNI del apoderado debe tener 8 dígitos.")
    return limpio
