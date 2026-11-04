import io
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app_module.app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def png_bytes():
    img = np.zeros((20, 20, 3), dtype=np.uint8)
    img[:, :, 2] = 200
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def upload(client, data, name="a.png"):
    return client.post("/", data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_get_index(client):
    assert client.get("/").status_code == 200


def test_valid_upload_preview_download(client, tmp_path):
    r = upload(client, png_bytes())
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "/uploads/grayscale_" in html and "/download/grayscale_" in html
    name = [f for f in os.listdir(tmp_path) if f.startswith("grayscale_")][0]
    p = client.get(f"/uploads/{name}")
    assert p.status_code == 200 and p.mimetype == "image/png"
    d = client.get(f"/download/{name}")
    assert "attachment" in d.headers["Content-Disposition"]
    gray = cv2.imread(os.path.join(tmp_path, name), cv2.IMREAD_UNCHANGED)
    assert gray.ndim == 2


def test_no_file(client):
    assert client.post("/", data={}, content_type="multipart/form-data").status_code == 400


def test_empty_filename(client):
    assert upload(client, b"x", "").status_code == 400


def test_bad_extension(client):
    assert upload(client, b"x", "a.txt").status_code == 400


def test_invalid_image(client):
    assert upload(client, b"not an image", "a.png").status_code == 400


def test_too_large(client):
    assert upload(client, b"0" * (5 * 1024 * 1024 + 10)).status_code == 413


def test_unique_names(client, tmp_path):
    upload(client, png_bytes())
    upload(client, png_bytes())
    assert len([f for f in os.listdir(tmp_path) if f.startswith("grayscale_")]) == 2


def test_traversal(client):
    assert client.get("/uploads/../app.py").status_code == 404
    assert client.get("/uploads/%2e%2e/app.py").status_code == 404
    assert client.get("/download/..%2fapp.py").status_code == 404
