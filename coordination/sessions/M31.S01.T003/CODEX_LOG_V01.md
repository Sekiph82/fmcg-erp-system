# M31.S01.T003 — Scope/rate-limit policy

## Implementation

- API-key scope values are normalized to lowercase, whitespace-trimmed canonical order (`read`, `write`) and reject empty, duplicate, unknown, or mixed `admin` scopes.
- `read` and `write` are defined as future key-authenticated access ceilings; `admin` is standalone and may be issued or rotated only by a superuser.
- Per-key rate metadata defaults to 60 requests per minute and accepts 1–1,000. Policy can be changed only during key rotation, which deactivates the old key and returns the replacement raw key once.
- Developer resources and both developer pages disclose that API-key authentication is not enabled, so stored scopes and rate values are not enforced on requests.
- No schema migration was needed. No API-key authentication or rate-limiting enforcement was claimed or added.

## Verification

- Task-owned disposable PostgreSQL integration runner: `run_scope_policy_tests.ps1`.
- PostgreSQL image: `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Database/container suffix: `e27586a2ebdc4303be69`; database name was task-prefixed and random. Loopback-only port mapping, no volume, no password, synthetic fixtures only. Runner confirmed migration head `20261029_0043` and removed the task-labeled container.
- Final integration result: 2 passed, 75 existing project/dependency warnings. The first run exposed a mismatch between test wording and the API's accurate but indirect disclosure; the wording was made explicit and the test passed on rerun.
- Backend Python syntax compilation passed.
- Frontend TypeScript `--noEmit` and targeted ESLint passed.
- `git diff --check` passed before final evidence/log changes.
- Independent read-only reviewer rechecked the final wording and the non-superuser admin-rotation denial test; no concrete blockers were reported.

## Scope boundary

These are simulated credential policies. They do not authenticate external API requests or impose request quotas until a separately implemented API-key authentication layer consumes these values.
