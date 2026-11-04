import os
import uuid

import cv2
from flask import Flask, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def render_error(message, status=400):
    return render_template("index.html", error=message), status


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

    folder = app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    unique = uuid.uuid4().hex
    original_name = f"{unique}_{safe_name}"
    gray_name = f"grayscale_{unique}_{safe_name}"
    original_path = os.path.join(folder, original_name)
    uploaded_file.save(original_path)

    img = cv2.imread(original_path)
    if img is None:
        os.remove(original_path)
        return render_error("The uploaded file is not a valid image.")

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if not cv2.imwrite(os.path.join(folder, gray_name), gray_img):
        return render_error("Failed to save the grayscale image.", 500)

    return render_template(
        "index.html",
        preview_url=url_for("serve_upload", filename=gray_name),
        download_url=url_for("download_file", filename=gray_name),
        original_url=url_for("serve_upload", filename=original_name),
    )


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
