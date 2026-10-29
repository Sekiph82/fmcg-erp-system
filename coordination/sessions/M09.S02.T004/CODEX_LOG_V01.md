# M09.S02.T004 — Codex implementation evidence

**Status:** COMPLETE

**Scope:** Standardize Advanced BOM version identifiers and inclusive effective-date windows across API validation, cloning, the user-facing create flow, and PostgreSQL.

## Implemented

- Kept BOM versions opaque: trim surrounding whitespace, reject blank values, cap the API value at the existing 20-character column limit, and do not infer a numbering or uniqueness policy.
- Kept the existing revision default (`0`) and clone behavior; PostgreSQL rejects blank revision values and the existing `VARCHAR(20)` column bounds length.
- Treat `effective_from` and `effective_to` as inclusive bounds. Either may be null to leave that side open; equal dates represent a valid one-day window. Reject reversed windows on create, merged partial update, and clone.
- Added equivalent PostgreSQL check constraints and an idempotent Alembic migration. The migration does not rewrite legacy rows; it will fail rather than silently change any pre-existing row that violates the new checks.
- Exposed optional effectivity dates in the BOM creation dialog, with an inline reversed-range message. Clone version identifiers are URL-encoded before sending.

## Verification

- `python -m compileall -q ...` on the changed backend modules, migration, and tests — passed.
- Focused regression run for M09 BOM governance, M03 recipe date governance, M21 conversion profile dates, M21 expected yield, and M21 conversion API contract — **53 passed, 3 skipped**. The skipped cases require their own named task databases.
- Disposable loopback PostgreSQL 16 database named `fmcg_m09_s02_t004_<random hex>`: `alembic upgrade head` — passed; BOM PostgreSQL constraint tests — **2 passed**. The container was removed afterward.
- `npm run type-check` in `frontend` — passed.
- `git diff --check` — passed.
- Independent read-only review by `/root/m08_transition_review` found one minor UX issue: a blank version produced an unhelpful failed submission. The create form now blocks blank/overlength values and shows a failed-create alert; the reviewer confirmed the fix. No reviewer edits, tests, or database operations occurred.

An initial PostgreSQL test run exposed pooled async connections crossing pytest event loops in the new test module. The test fixture was corrected to dispose the async engine after each test; the final isolated PostgreSQL run then passed both tests.

## Limits

- No live or owner database was read or modified. If a deployed legacy database contains blank identifiers or reversed date windows, the additive validated migration will stop; resolve those records under the database owner's data policy before deploying the migration.
- No GitHub Actions, production deployment, merge, or production approval is claimed.
