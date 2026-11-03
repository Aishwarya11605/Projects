# Architecture — Grayscale Image Converter (Flask + OpenCV)

This document translates the approved implementation plan into actionable architecture guidance for the existing project in ``Image_converter/``.

- Repo: `Aishwaya11605/Projects`
- Module: ``Image_converter/``
- Stack: Python, Flask, OpenCV (opencv-python), Bootstrap for basic UI
- Scope: architecture documentation only (does not implement app code)

> GOAL: Make the app behave as a web app: image upload → convert to grayscale → return result in browser with a download option, with basic validation and safe file handling.

---

# 1. Architecture Overview

The project is a single-service Flask web app. It currently handles an HTTP file upload and then runs OpenCV processing on the server. The enhancements remove server-desktop GUI usage (`cv2.imshow` / `waitKey`) and instead return results to the browser.

Core building blocks:
- Web UI: Single page upload form (HTML + Bootstrap)
- Web App: Flask routes for upload, result preview, and download
- Processing: OpenCV grayscale conversion on server
- Storage: Local filesystem folder `Image_converter/uploads`

# Non-goals
- No new cloud storage, database, or containerization is introduced.