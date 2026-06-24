import sys
from pathlib import Path

import pytest

from validators import (
    normalizar_dni,
    validar_asistencias,
    validar_nombre_completo,
    validar_participacion,
    validar_telefono,
    validar_username,
)


def test_normalizar_dni_ok():
    assert normalizar_dni("71272388") == "71272388"
    assert normalizar_dni(" 71272388 ") == "71272388"


def test_normalizar_dni_rechaza():
    with pytest.raises(ValueError):
        normalizar_dni("123")
    with pytest.raises(ValueError):
        normalizar_dni("123456789")


def test_validar_rangos():
    assert validar_asistencias(85) == 85.0
    assert validar_participacion(7) == 7.0
    with pytest.raises(ValueError):
        validar_asistencias(101)
    with pytest.raises(ValueError):
        validar_participacion(11)


def test_validar_nombre():
    assert validar_nombre_completo("Juan Perez Garcia") == "Juan Perez Garcia"
    with pytest.raises(ValueError):
        validar_nombre_completo("Jo")


def test_validar_telefono_y_usuario():
    assert validar_telefono("987654321") == "987654321"
    assert validar_username("mquispe") == "mquispe"
    with pytest.raises(ValueError):
        validar_telefono("12345")
    with pytest.raises(ValueError):
        validar_username("ab")
