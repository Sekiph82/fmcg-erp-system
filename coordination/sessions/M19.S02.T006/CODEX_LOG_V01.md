# M19.S02.T006 — Residual repository anomaly/dead-code cleanup

## Scope and audit

The canonical task row had no linked acceptance checklist. Şekip approved a narrow scope: remove only code proven unused; preserve page redirects and performance warnings. I reviewed the 2026-05-17 `docs/FULL_REPOSITORY_REVIEW.md`, which reports an `AUTO_CREATE_TABLES` dead path in `main.py`. That specific lifespan branch had already been removed in a later change, but the unused `Settings.AUTO_CREATE_TABLES` field and the matching development-template entry remained. A repository-wide source/config search found no runtime consumers.

## Changes

- Removed the orphaned `AUTO_CREATE_TABLES` setting from `Settings` and `.env.development.example`.
- Updated the README to state the live schema-change rule directly: use Alembic migrations.
- Added a regression assertion that the setting is no longer a `Settings` field.
- Preserved the historical repository audit, page redirects, and performance findings.

## Verification

- `rg` across backend application code, tests, the development template, and README found no remaining setting reference except the regression assertion.
- Focused tests: `test_auto_create_tables_setting_is_removed` and `test_production_config_rejects_security_landmines` — **2 passed**.
- Full `tests/test_hardening.py` — **24 passed, 2 failed**. Both failures are existing test-fixture drift: the tests monkeypatch `app.core.deps.decode_token`, while current production code imports and calls `decode_access_token`. The cleanup did not change auth code; these failures are reported and were not altered because they are outside the approved dead-code scope.
- `git diff --check` passed.
- No Docker database, production data, or GitHub Actions were used.
