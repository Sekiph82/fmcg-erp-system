# M19.S02.T001 — Production-like penetration/security verification

## Result

Completed local security hardening and verification for the production configuration and bulk-import upload routes. The task row has no linked acceptance checklist or task-specific audit. I reviewed the repository's historical `docs/SECURITY_REVIEW.md` and `backend/tests/SECURITY_REPORT.md`; their dates are 2026-05-17 and 2026-05-02, so they are context rather than evidence of current production security.

## Changes

- Both bulk-import HTTP routes now use the shared upload validator before parsing/importing files.
- Import uploads fail closed unless the declared MIME type is CSV or plain text, are capped at 50 MiB, reject NUL/binary and invalid UTF-8 content, and pass a sanitized filename to the import engine. The allowlist is CSV/text because the current parser reads UTF-8 CSV; it does not parse XLS/XLSX despite those formats appearing in the previous allowlist.
- Production configuration now rejects HS256 secret keys shorter than 32 UTF-8 bytes, placeholder/example markers, and short repeated patterns. This is a weak-key guard, not proof that a key has sufficient randomness; production secrets should be securely generated and stored in a secret manager.
- Added ASGI multipart tests for both routes covering MIME rejection, missing MIME, binary and invalid UTF-8 payloads, size limits, and Windows path traversal in filenames.

## Verification evidence

- `backend`: `python -m pytest -q tests/test_bulk_import_upload_security.py tests/test_security.py tests/test_attack_simulation.py tests/test_hardening.py::test_production_config_rejects_security_landmines` — **155 passed**, 9 warnings, 3.46 seconds. The warnings are existing PyJWT test-secret-length warnings (8-byte and 23-byte keys); they remain visible and are not reported as clean.
- `frontend`: `npm audit --omit=dev --audit-level=high` — **0 vulnerabilities found**.
- An independent read-only review of the final changes found no remaining local code blocker.
- `pip-audit` produced no audit result: the tool attempted to use a protected AppData cache location and was stopped. No AppData path was inspected or changed.
- No external penetration test, deployed production/staging verification, or ingress-level request-body limit verification was performed. FastAPI's multipart parser may spool the request before route-level file-size validation; server/proxy request-body limits remain a deployment control.
- No production data was used and no GitHub Actions were dispatched.

## Remaining limits

The secret-key heuristic cannot prove entropy and may accept a long, human-chosen key that avoids the rejected markers/patterns. The 50 MiB cap applies to file processing after multipart parsing, not the total request body at ingress. Production deployment and independent external penetration testing remain outside the evidence collected for this local task.
