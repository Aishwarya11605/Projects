# Grayscale Image Converter

A simple Flask web application that lets users upload an image, converts it to grayscale with OpenCV, shows the result in the browser, and offers it for download.

## Features
- Upload an image from your device.
- Convert it to grayscale using OpenCV (works headless; no desktop window is opened).
- Preview the grayscale image directly in the browser.
- Download the grayscale image.
- Validation with clear error messages: missing/empty file, unsupported type, unreadable image, file too large.
- Safe file handling: sanitized filenames with a UUID prefix, so uploads never collide or escape the uploads folder.

## Routes
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Upload form |
| `/` | POST | Validates and converts the upload, then renders the preview and download link |
| `/uploads/<filename>` | GET | Serves a generated grayscale image for in-browser preview |
| `/download/<filename>` | GET | Serves a generated grayscale image as a download (attachment) |

Only generated grayscale files (`grayscale_<id>_<name>`) are served; any other filename returns 404. Responses include `X-Content-Type-Options: nosniff`, and images are sent with `Cache-Control: no-store`.

## Upload limits
- Allowed extensions: png, jpg, jpeg, bmp, webp
- Maximum size: 5 MB (larger uploads return HTTP 413)
- Declared MIME type must be an image type, and the file content must match its extension (checked with Pillow)
- Maximum dimensions: 8000 px per side and 40 megapixels (HTTP 413)
- Invalid input returns HTTP 400 with an error message on the page.

## Project Structure
```
Image_converter/
|-- app.py
|-- requirements.txt
|-- static/
|   `-- styles.css
|-- templates/
|   `-- index.html
|-- tests/
|   `-- test_app.py
`-- uploads/          (original and grayscale images are stored here)
docs/architecture/    (architecture doc, ADR 0001, sequence diagram)
```

## Technologies Used
- Python, Flask, OpenCV (opencv-python), Pillow, NumPy
- HTML, CSS (Bootstrap 3.4.1 via CDN with SRI)

## How to run
1. Install dependencies:
   ```
   cd Image_converter
   pip install -r requirements.txt
   ```
2. Start the app:
   ```
   python app.py
   ```
   Debug mode is off by default; set `FLASK_DEBUG=1` to enable it for local development.
3. Open http://127.0.0.1:5000/ in your browser, choose an image and click Upload.

## Run the tests
```
cd Image_converter
python -m pytest -q tests
```

## Notes
- Uploaded and generated files accumulate in `Image_converter/uploads/`; no retention policy is implemented.
- The original upload is deleted right after conversion; only the grayscale file is kept and served.

## Author
* Aishwarya
* GitHub - Aishwarya11605
