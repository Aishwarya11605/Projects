import logging
import os
import re
import uuid

import cv2
from flask import Flask, abort, render_template, request, send_from_directory, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}
ALLOWED_MIMETYPES = {"image/png", "image/jpeg", "image/bmp", "image/webp"}
# Pillow format name -> extensions it may legitimately have
FORMAT_EXTENSIONS = {
    "PNG": {"png"},
    "JPEG": {"jpg", "jpeg"},
    "BMP": {"bmp"},
    "WEBP": {"webp"},
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE_PX = 8000
MAX_PIXELS = 40_000_000

# Only generated grayscale files may be served.
SERVABLE_RE = re.compile(
    r"^grayscale_[0-9a-f]{32}_[A-Za-z0-9._-]+\.(png|jpg|jpeg|bmp|webp)$"
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class UploadError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_remove(path):
    """Remove a file, never raising."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning("Could not remove file %s", path, exc_info=True)


def render_error(message, status=400):
    return render_template("index.html", error=message), status


def check_image(path, extension):
    """Inspect header only (no full decode): format, extension match, dimensions."""
    try:
        with Image.open(path) as im:
            fmt = im.format
            width, height = im.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise UploadError("The uploaded file is not a valid image.")
    if fmt not in FORMAT_EXTENSIONS or extension not in FORMAT_EXTENSIONS[fmt]:
        raise UploadError("File content does not match its extension.")
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX or width * height > MAX_PIXELS:
        raise UploadError(
            "Image dimensions too large (max 8000 px per side and 40 megapixels).", 413
        )


def convert_to_grayscale(original_path, gray_path):
    img = cv2.imread(original_path)
    if img is None:
        raise UploadError("The uploaded file is not a valid image.")
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if not cv2.imwrite(gray_path, gray_img):
        raise OSError("cv2.imwrite failed")


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.errorhandler(413)
def too_large(_e):
    return render_error("File is too large. Maximum size is 5 MB.", 413)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "GET":
        return render_template("index.html")

    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return render_error("Please choose an image file to upload.")

    safe_name = secure_filename(uploaded_file.filename)
    if not safe_name or not allowed_file(safe_name):
        return render_error("Unsupported file type. Allowed: png, jpg, jpeg, bmp, webp.")
    if (uploaded_file.mimetype or "").lower() not in ALLOWED_MIMETYPES:
        return render_error("Unsupported content type. Please upload a real image.")

    extension = safe_name.rsplit(".", 1)[1].lower()
    folder = app.config["UPLOAD_FOLDER"]
    unique = uuid.uuid4().hex
    original_path = os.path.join(folder, f"original_{unique}_{safe_name}")
    gray_name = f"grayscale_{unique}_{safe_name}"
    gray_path = os.path.join(folder, gray_name)

    try:
        os.makedirs(folder, exist_ok=True)
        uploaded_file.save(original_path)
        check_image(original_path, extension)
        convert_to_grayscale(original_path, gray_path)
    except UploadError as exc:
        safe_remove(gray_path)
        return render_error(exc.message, exc.status)
    except (OSError, cv2.error):
        logger.exception("Image processing failed")
        safe_remove(gray_path)
        return render_error("Could not process the image. Please try again.", 500)
    finally:
        # The original is never served; always remove it.
        safe_remove(original_path)

    return render_template(
        "index.html",
        preview_url=url_for("serve_upload", filename=gray_name),
        download_url=url_for("download_file", filename=gray_name),
    )


def _serve(filename, **kwargs):
    if not SERVABLE_RE.match(filename):
        abort(404)
    response = send_from_directory(app.config["UPLOAD_FOLDER"], filename, **kwargs)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/uploads/<filename>")
def serve_upload(filename):
    return _serve(filename)


@app.route("/download/<filename>")
def download_file(filename):
    return _serve(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
