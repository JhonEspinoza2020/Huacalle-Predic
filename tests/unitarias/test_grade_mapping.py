import pytest

from app_loader import load_app_module


@pytest.mark.unitaria
def test_grade_mapping_peru_scale():
    app_module = load_app_module()

    assert app_module._normalize_grade("AD") == 4
    assert app_module._normalize_grade("A") == 3
    assert app_module._normalize_grade("B") == 2
    assert app_module._normalize_grade("C") == 1
    assert app_module._normalize_grade(" ad ") == 4
    assert app_module._normalize_grade(None) is None
