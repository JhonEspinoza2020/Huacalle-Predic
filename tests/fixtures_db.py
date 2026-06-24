"""Fixtures compartidas de base de datos para pytest."""
import pytest

from database import db_setup
from database import repository as repo


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "colegio.db"

    def _db_path():
        return str(db_file)

    monkeypatch.setattr(db_setup, "get_db_path", _db_path)
    monkeypatch.setattr(repo, "get_db_path", _db_path)
    repo.init_database(seed=True)
    return db_file
