# M31.S03.T004 — Webhook signing/secret rotation

## Scope and outcome

Implemented outbound and inbound webhook HMAC hardening, bounded key rotation, encrypted secret storage, and superuser-only secret management. Work used synthetic configurations only; no production credentials, owner data, external callbacks, or real factory data were used.

- Timestamped HMAC-SHA256 signs `<unix-timestamp>.<exact-request-body>`. Inbound timestamped signatures have a five-minute tolerance, require an idempotency key, and fail closed for malformed timestamps and unsupported authentication types. Existing raw-body HMAC signatures remain temporarily readable and are protected by delivery idempotency.
- HMAC secrets require at least 32 characters, including when changing an existing subscription's auth type. Rotation returns a generated 256-bit secret once, increments its key version, and accepts/sends both keys during a 24-hour overlap. Another rotation is rejected until that overlap expires.
- Secret configuration and rotation routes require superuser access. Secret values are absent from API output and audit records; custom header values and authentication/signature values are redacted from peer response bodies.
- New and rotated secrets are encrypted with Fernet under a domain-separated dedicated `WEBHOOK_SECRET_ENCRYPTION_KEY`; production requires a strong, distinct, stable value. The prior draft envelope and plaintext legacy records remain readable for compatibility. The production template and deployment guidance document key backup and the need for a planned re-encryption before changing this dedicated key.
- Added Alembic revision `20261030_0004` for secret versions and previous-key grace metadata.

## Verification

- Latest focused M31.S03 T001–T004 regression suite: **52 passed, 67 warnings** in 22.63 seconds.
- Latest T004 unit suite: **12 passed** in 9.85 seconds, including weak production-key rejection, application-key rotation compatibility, custom-header response redaction, weak existing HMAC key rejection, and oversized timestamp failure-closed behavior.
- Task-owned disposable PostgreSQL runner: **2 passed** in 7.23 seconds with `M31_S03_T004_DISPOSABLE_TEST_DATABASE=1`; Alembic upgraded and reported `20261030_0004 (head)`. Runner output records database `fmcg_m31_s03_t004_cc894556319f4951af26a721` and PostgreSQL image `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`. Its uniquely task-labeled container was removed on exit.
- `py_compile` passed for every changed Python module and T004 Python test. `alembic heads` reported only `20261030_0004 (head)`.
- Frontend `npm run type-check` passed. `git diff --check` passed for the task-owned tracked changes.
- Independent read-only review found no remaining blocker after remediation of response-body credential leakage, weak-key auth-type transition, encryption-key coupling/strength, and oversized timestamp handling.
- A repository-wide `compileall` attempt is not green due to an unrelated pre-existing syntax error in tracked `backend/tests/test_m27_s03_t001_hold_quarantine_db.py:145` (a literal `\\n` after the statement). That file is unchanged by this task; changed task files compile successfully.

Warnings in the M31 suite are existing Pydantic model deprecation warnings in adjacent schemas.
