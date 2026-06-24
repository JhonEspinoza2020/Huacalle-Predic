import pytest

from app_loader import load_app_module


@pytest.mark.caja_blanca
def test_model_file_is_loaded_correctly(monkeypatch, tmp_path):
    app_module = load_app_module()

    fake_model_path = tmp_path / "modelo_rf.pkl"
    fake_model_path.write_text("fake", encoding="utf-8")

    sentinel_model = object()

    monkeypatch.setattr(app_module, "MODEL_PATH", fake_model_path)
    monkeypatch.setattr(app_module.joblib, "load", lambda _: sentinel_model)

    loaded = app_module._load_model()
    assert loaded is sentinel_model
