import os

import pytest

import app as app_module


@pytest.fixture(autouse=True)
def isolated_uploads(tmp_path, monkeypatch):
    """Point every test at its own temporary uploads dir; restored automatically."""
    monkeypatch.setitem(app_module.app.config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setitem(app_module.app.config, "TESTING", True)
    real = app_module.UPLOAD_FOLDER
    before = set(os.listdir(real)) if os.path.isdir(real) else set()
    yield
    after = set(os.listdir(real)) if os.path.isdir(real) else set()
    assert before == after, "test modified the real uploads/ folder"


@pytest.fixture
def client():
    return app_module.app.test_client()
