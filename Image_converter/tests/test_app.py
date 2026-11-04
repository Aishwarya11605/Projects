import io
import os

import cv2
import numpy as np
import pytest
from PIL import Image

import app as app_module


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


# ---- review-finding tests ----
def files(tmp_path):
    return sorted(os.listdir(tmp_path))


def test_nosniff_everywhere(client, tmp_path):
    assert client.get("/").headers["X-Content-Type-Options"] == "nosniff"
    assert upload(client, b"x", "a.txt").headers["X-Content-Type-Options"] == "nosniff"
    upload(client, png_bytes())
    name = files(tmp_path)[0]
    for url in (f"/uploads/{name}", f"/download/{name}"):
        r = client.get(url)
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["Cache-Control"] == "no-store"


def test_only_grayscale_served(client, tmp_path):
    (tmp_path / "secret.png").write_bytes(png_bytes())
    (tmp_path / ("original_" + "a" * 32 + "_x.png")).write_bytes(png_bytes())
    assert client.get("/uploads/secret.png").status_code == 404
    assert client.get("/download/secret.png").status_code == 404
    assert client.get("/uploads/original_" + "a" * 32 + "_x.png").status_code == 404


def test_success_leaves_only_grayscale(client, tmp_path):
    assert upload(client, png_bytes()).status_code == 200
    assert len(files(tmp_path)) == 1 and files(tmp_path)[0].startswith("grayscale_")
    assert "original" not in upload(client, png_bytes()).get_data(as_text=True)


def test_invalid_image_cleanup(client, tmp_path):
    assert upload(client, b"garbage").status_code == 400
    assert files(tmp_path) == []


def test_save_oserror(client, tmp_path, monkeypatch):
    from werkzeug.datastructures import FileStorage

    def boom(self, *a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(FileStorage, "save", boom)
    r = upload(client, png_bytes())
    assert r.status_code == 500
    assert "disk full" not in r.get_data(as_text=True)
    assert files(tmp_path) == []


def test_imwrite_false_cleanup(client, tmp_path, monkeypatch):
    real = cv2.imwrite

    def fake(path, img, *a):
        real(path, img)  # leave a partial/real file behind
        return False
    monkeypatch.setattr(app_module.cv2, "imwrite", fake)
    assert upload(client, png_bytes()).status_code == 500
    assert files(tmp_path) == []


def test_imwrite_raises_cleanup(client, tmp_path, monkeypatch):
    def fake(*a, **k):
        raise cv2.error("bad")
    monkeypatch.setattr(app_module.cv2, "imwrite", fake)
    assert upload(client, png_bytes()).status_code == 500
    assert files(tmp_path) == []


def test_remove_failure_does_not_crash(client, tmp_path, monkeypatch):
    def fail(path):
        raise OSError("locked")
    monkeypatch.setattr(app_module.os, "remove", fail)
    assert upload(client, png_bytes()).status_code == 200


def post_with_mime(client, data, name, mime):
    return client.post("/", data={"file": (io.BytesIO(data), name, mime)},
                       content_type="multipart/form-data")


def test_declared_mime_is_advisory_valid_content_accepted(client):
    assert post_with_mime(client, png_bytes(), "a.png", "text/html").status_code == 200


def test_declared_mime_does_not_rescue_garbage(client, tmp_path):
    assert post_with_mime(client, b"garbage", "a.png", "image/png").status_code == 400
    assert files(tmp_path) == []


def test_content_extension_mismatch(client, tmp_path):
    assert upload(client, png_bytes(), "a.jpg").status_code == 400
    assert files(tmp_path) == []


def test_dimension_limit(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_SIDE_PX", 10)
    assert upload(client, png_bytes()).status_code == 413
    assert files(tmp_path) == []


def test_pixel_limit(client, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_PIXELS", 100)
    assert upload(client, png_bytes()).status_code == 413


def test_debug_off_by_default():
    assert app_module.app.debug is False


# ---- second review round ----
def test_security_headers(client, tmp_path):
    upload(client, png_bytes())
    name = files(tmp_path)[0]
    responses = [client.get("/"), upload(client, b"x", "a.txt"),
                 client.get(f"/uploads/{name}"), client.get(f"/download/{name}"),
                 client.get("/uploads/nope.png")]
    for r in responses:
        csp = r.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp
        assert "https://maxcdn.bootstrapcdn.com" in csp
        assert "font-src https://maxcdn.bootstrapcdn.com" in csp
        assert "'unsafe-inline'" not in csp
        assert r.headers["Referrer-Policy"] == "no-referrer"
        assert r.headers["X-Frame-Options"] == "DENY"


def test_template_has_no_inline_script_or_style(client):
    html = client.get("/").get_data(as_text=True).lower()
    assert "<script" not in html and "<style" not in html and "style=" not in html


def test_friendly_download_name(client, tmp_path):
    upload(client, png_bytes(), "photo.png")
    name = files(tmp_path)[0]
    cd = client.get(f"/download/{name}").headers["Content-Disposition"]
    assert "attachment" in cd and "grayscale_photo.png" in cd
    assert name.split("_")[1] not in cd


def test_friendly_download_name_keeps_jpg_extension(client, tmp_path):
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    data = cv2.imencode(".jpg", img)[1].tobytes()
    upload(client, data, "Vacation Photo.JPG")
    name = files(tmp_path)[0]
    cd = client.get(f"/download/{name}").headers["Content-Disposition"]
    assert "grayscale_Vacation_Photo.jpg" in cd


@pytest.mark.parametrize("filename", [
    "a" * 300 + ".png",
    "\u00fcnic\u00f6de.png",
    "...png.png",
    "my file (1).png",
])
def test_generated_names_always_servable(client, tmp_path, filename):
    r = upload(client, png_bytes(), filename)
    assert r.status_code == 200
    name = files(tmp_path)[0]
    assert app_module.SERVABLE_RE.match(name)
    assert client.get(f"/uploads/{name}").status_code == 200
    assert client.get(f"/download/{name}").status_code == 200


def test_decompression_bomb_protection(client, tmp_path, monkeypatch):
    assert Image.MAX_IMAGE_PIXELS == app_module.MAX_PIXELS
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 300)  # warning path (400 px)
    assert upload(client, png_bytes()).status_code == 413
    assert files(tmp_path) == []
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)  # hard error path (> 2x)
    assert upload(client, png_bytes()).status_code == 413
    assert files(tmp_path) == []


def test_tests_do_not_touch_real_uploads(client):
    upload(client, png_bytes())
    assert os.path.realpath(app_module.app.config["UPLOAD_FOLDER"]) !=         os.path.realpath(app_module.UPLOAD_FOLDER)


@pytest.mark.parametrize("filename", [" .png", "..png", ".png", "///"])
def test_unusable_names_rejected_cleanly(client, tmp_path, filename):
    assert upload(client, png_bytes(), filename).status_code == 400
    assert files(tmp_path) == []
