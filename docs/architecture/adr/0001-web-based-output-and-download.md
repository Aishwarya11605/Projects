# ADR 0001 - Web-based output and download for grayscale conversion
Date: 2026-11-03

Status: Approved (implementation plan approved by user); amended 2026-11-04 (see Amendment)

## Context
Originally, the app performed the grayscale conversion on the server and called `cv2.imshow` / `cv2.waitKey` inside the HTTP handler. This blocks the request thread and does not work in headless environments. The user could not view the result in the browser or download it.

## Decision
We replace desktop GUI display with a web-based flow:

- On POST to `/`, the app:
  - validates the multipart upload
  - stores the file under a sanitized and unique name
  - reads and converts it to grayscale
  - writes the grayscale file to `uploads/`
  - renders the template with a result preview URL and a download URL

- Add two Flask routes:
  - `/uploads/<filename>` (browser preview; returns the image with `Content-Type` set)
  - `/download/<filename>` (returns the grayscale file with `as_attachment=True`)

## Consequences
Positive:
- Works in headless/server environments
- No request thread blocking
- User can view and download the output file from the browser

Negative:
- Requires us to serve generated files from the Flask app (must be done safely)
- Files accumulate on disk unless a retention policy is added (out of scope)

## Alternatives Considered
- Return the grayscale image bytes directly in the POST response, non-HTML (not chosen since the app is a browser UI)
- Store files in object storage (S3/GCS) (out of scope)

## Implementation Notes
- Use `werkzeug.utils.secure_filename` and a UUID to avoid collisions
- Use `__file__`-relative path resolution for `uploads/`
- Add basic validation for missing/empty filename and `cv2.imread` failure

## Amendment 2026-11-04 (code review findings)
- The original upload is a temporary file: it is deleted after conversion (success or failure) and is never served. Only generated grayscale files remain in `uploads/`.
- `/uploads/<filename>` and `/download/<filename>` serve only filenames matching `grayscale_<32 hex chars>_<safe name>.<allowed extension>`; anything else returns 404. Responses carry `X-Content-Type-Options: nosniff`, and image responses carry `Cache-Control: no-store`.
- Validation is strengthened: extension whitelist (png, jpg, jpeg, bmp, webp), declared MIME type check, content/extension match via Pillow header inspection, and a maximum of 8000 px per side and 40 megapixels (checked before OpenCV decodes the image). Upload size limit is 5 MB.
- Filesystem and OpenCV failures (save, imwrite, remove) are handled: partial files are removed and a generic error (HTTP 500) is shown.
- Flask debug mode is off by default (enable with `FLASK_DEBUG=1`).
