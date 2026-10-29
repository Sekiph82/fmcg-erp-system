# M01.S02.T005 — CODEX implementation evidence

**Task:** Complete production document binary storage/upload pipeline
**Evidence date:** 2026-10-29
**Status:** Implementation and focused verification complete; no production deployment or human approval is claimed.

## Implemented

- Added a local binary-storage adapter that generates opaque keys, streams uploads to an atomic temporary file, checks the configured size limit, validates the filename/type/content pairing, computes SHA-256, and stores files with restrictive permissions where supported.
- Added a persistent `documents_data` volume for development and production Compose configurations. The default remains local storage; no cloud account, external credentials, or scanner service is fabricated.
- Added configurable optional ClamAV INSTREAM scanning. Missing/unavailable scanners and scan errors fail closed. A rescan persists `SCANNING` while the scanner runs; attached files remain unavailable for download and approval until the result is `CLEAN`.
- Added authenticated, permission-gated upload, scan, and attachment download endpoints. Client create/update payloads cannot set storage keys, URLs, checksums, scan results, or lifecycle status. API responses omit local paths, storage keys, and raw file URLs.
- Added row-lock/reload checks to serialize file upload, rescan, and approval transitions. A concurrently approved document cannot gain an attachment after the scan, competing uploads cannot overwrite each other, and approval cannot proceed during a rescan.
- Added a pre-multipart ASGI request-body cap for document uploads, in addition to the streaming file-size cap, so oversized bodies are rejected before unlimited multipart spooling.
- Updated document creation/detail pages to save a draft first, attach files from its detail page, expose scan state, and show download only after `CLEAN`.
- Updated the GAP-012 implementation notes with the completed storage pipeline and its operating limits.

## Verification evidence

- Python compile check for the touched backend modules and focused tests: passed.
- `python -m pytest tests/test_document_upload_body_limit.py tests/test_document_storage_pipeline.py -q -k 'not postgresql'`: **18 passed, 1 deselected**.
- PostgreSQL check used a uniquely named, passwordless, task-owned container published only to `127.0.0.1` and a database matching `fmcg_m01_s02_t005_<random hex>`. `python -m alembic upgrade head` passed. With `M01_S02_T005_DISPOSABLE_TEST_DATABASE=1`, `python -m pytest tests/test_document_storage_pipeline.py -q`: **16 passed**. The database container was removed after the run. Test users/documents and scanner responses were synthetic; the route test verified database selection before writes.
- `npm run type-check` in `frontend`: passed.
- `docker compose config -q` and `docker compose -f docker-compose.prod.yml config -q`: passed. Compose printed the existing warning that `REDIS_PASSWORD` is unset; the configuration check still exited successfully.
- Independent read-only review: no remaining concrete findings in the final review. The reviewer made no edits and ran no tests or database operations.

## Limits

- A production ClamAV service was not configured or claimed. Until one is configured and returns `CLEAN`, attachments remain quarantined and cannot be downloaded or used to approve their document.
- Local-volume backup/restore and multi-host replication are operational follow-ups. The document volume and database need coordinated backups.
- The full application test suite and GitHub Actions were not run for this task.
