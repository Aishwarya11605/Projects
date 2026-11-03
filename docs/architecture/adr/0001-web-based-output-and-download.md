# ADR 0001 - Web-based output and download for grayscale conversion
Date: 2026-11-03

Status: Approved (implementation plan approved by user)

## Context
Currently, the app performs the grayscale conversion on the server and calls `cv2.imshow`/``cv2.waitKey` inside the HTTP andler. This blocks the request thread and does not work in headless environments. The user cannot view the result in the browser or download it.

## Decision
We replace desktop GUI display with a web-based flow:

- On POST to `/`, the app:
  - validates the multipart upload
  - stores file under a sanitized and unique name
  - reads and converts to grayscale
  - writes the grayscale file to `uploads/`
  - renders the template with a result preview URL and a download URL

- Add two Flask routes:
  - `e/r/uploads/<:filename>` (for browser preview, returns the image with `Content-Type` set)
  - `/download/<:filename>` (returns the grayscale file with `as_attachment=True`)

## Consequences
Positive:
- Works in headless/server environments
- No request thread blocking
- User can view and download the output file from the browser
Negative:
- Requires us to serve uploaded/generated files from the Flask app (must be done safely)
- Files accumulate on disk unless a retention policy is added (out of scope)

## Alternatives Considered
- Return the grayscale image bytes directly in the POST response non-html (not chosen since the app is a browser UI)
- Store files in object storage (s3/gcs) (out of scope)

## Implementation Notes
- Use `workzeug.utils.secure_filename` and a UUID to avoid collisions
* Use `__file__`-relative path resolution for `uploads/`
* Add basic validation for missing/empty filename and `cv2.imread` failure
