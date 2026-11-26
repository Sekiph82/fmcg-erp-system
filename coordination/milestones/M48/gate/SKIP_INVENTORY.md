# M48.S01.T012 — Skipped-test inventory

Prepared 2026-11-26 at source SHA `6ac96f1` plus the uncommitted M48 working tree (other agents were still editing ads code). Regenerate at the frozen gate SHA:

- Static part: `python coordination/milestones/M48/gate/skip_inventory.py`.
- Runtime part: `cd backend && DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:9/no_db_unreachable python -m pytest -q -p no:cacheprovider -rs`.

Classes:

- **DB_FLAG**: the test is gated on a disposable-database flag or a PostgreSQL `DATABASE_URL`. `run_all_db_tests.py` executes these on a fresh database cloned from the template.
- **SERVICE**: needs a disposable DB *and* a local container. The gate starts the container and exports the env var, then the runner executes the file.
- **PROVIDER_LIVE**: needs a real provider account. Must be justified.
- **PLATFORM**: OS or local-tool dependent.
- **UNEXPLAINED**: no defensible reason. Must be zero at the gate.

## Summary

| class | static skip sites | runtime skips (no-DB suite) | disposition |
|---|---|---|---|
| DB_FLAG | 253 | 567 | executed by `run_all_db_tests.py` (224 files RUN) |
| SERVICE | 4 | 5 | 4 files SERVICE_REQUIRED: SMTP_TEST_SERVER (Mailpit) ×2, MQTT_TEST_BROKER_URL ×1, CLAMAV_TEST_HOST ×1 |
| PROVIDER_LIVE | 0 | 0 | none: every provider adapter test runs against the local provider simulators |
| PLATFORM | 1 | 0 | `test_m47_s01_t007_content_hub_depth.py:338` skips only if `ffmpeg` is not on PATH (it is installed on this host, so the test ran) |
| UNEXPLAINED | 0 | 0 | — |

`importorskip`, `mark.skip` and `xfail`: none in backend/tests.

## Runtime: full suite without a database

Command: `cd backend && DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:9/no_db_unreachable python -m pytest -q -p no:cacheprovider -rs`.

The settings default `DATABASE_URL` points at the dev compose DB on localhost:5432. The run therefore pointed `DATABASE_URL` at a closed loopback port, so no test could reach the dev DB.

Exact final line:

```
5 failed, 1886 passed, 572 skipped, 127 warnings in 205.05s (0:03:25)
```

**The 5 failures.** All five are `ConnectionRefusedError` against the deliberately unreachable URL. They are not app defects. They are the PostgreSQL-only tests gated only on `"postgresql" in settings.DATABASE_URL`, not on an opt-in flag:

- `test_m20_auth_transaction_boundary.py:51`
- `test_m20_postgres_scenario_savepoint.py:45`
- `test_m20_s01_t001_v03_mps_remediation.py:174`
- `test_m20_strict_findings.py:46`
- `test_m20_strict_findings.py:122`

With the default settings URL, these tests would write to the dev DB (the M47 baseline "0 failed" most likely came from that).

- **Recommended remediation:** gate them on an explicit flag, like every other DB test.
- **Runner coverage:** the runner already covers them; their class is `DATABASE_URL=postgresql`.
- **Verified:** `test_m20_auth_transaction_boundary.py` gave `1 passed` on a disposable DB.

### -rs skip reasons (count, files, class, reason)

| skips | files | class | reason |
|---|---|---|---|
| 206 | 96 | DB_FLAG | requires the task-owned disposable PostgreSQL |
| 130 | 49 | DB_FLAG | requires the task-owned disposable PostgreSQL runner |
| 29 | 10 | DB_FLAG | requires the task-owned disposable PostgreSQL at the M43 head |
| 17 | 2 | DB_FLAG | Set M20_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database. |
| 15 | 2 | DB_FLAG | Set M02_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database. |
| 15 | 1 | DB_FLAG | Set M25_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 11 | 1 | DB_FLAG | Set M13_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 10 | 6 | DB_FLAG | Run only with the task-owned disposable PostgreSQL database. |
| 10 | 4 | DB_FLAG | requires the disposable M48 PostgreSQL |
| 9 | 1 | DB_FLAG | requires the M34.S04.T004 task-owned disposable PostgreSQL database |
| 8 | 1 | DB_FLAG | Set M05_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database. |
| 7 | 1 | DB_FLAG | Set M25_S03_T002_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 7 | 7 | DB_FLAG | requires task-owned disposable PostgreSQL |
| 7 | 1 | DB_FLAG | requires the M34.S04.T002 task-owned disposable PostgreSQL database |
| 6 | 1 | DB_FLAG | Set M25_S03_T003_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 6 | 1 | DB_FLAG | requires the task-owned disposable PostgreSQL at head 20261125_0072 |
| 5 | 4 | DB_FLAG | Set M03_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database. |
| 5 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S02_T001_DISPOSABLE_TEST_DATABASE=1) |
| 5 | 1 | DB_FLAG | requires the M34.S04.T001 task-owned disposable PostgreSQL database |
| 5 | 1 | DB_FLAG | requires the M34.S04.T003 task-owned disposable PostgreSQL database |
| 4 | 1 | DB_FLAG | Set M13_S03_T004_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 4 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S03_T003_DISPOSABLE_TEST_DATABASE=1) |
| 4 | 4 | DB_FLAG | requires this task's disposable PostgreSQL database |
| 3 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S02_T002_DISPOSABLE_TEST_DATABASE=1) |
| 3 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S02_T003_DISPOSABLE_TEST_DATABASE=1) |
| 3 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S02_T004_DISPOSABLE_TEST_DATABASE=1) |
| 3 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S03_T001_DISPOSABLE_TEST_DATABASE=1) |
| 3 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S03_T002_DISPOSABLE_TEST_DATABASE=1) |
| 3 | 1 | DB_FLAG | Set M31_S01_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 3 | 2 | SERVICE | requires the task-owned disposable PostgreSQL and a local test SMTP server |
| 2 | 1 | DB_FLAG | Set M23_S04_T003_DISPOSABLE_TEST_DATABASE=1 only for its task-owned disposable PostgreSQL database. |
| 2 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S03_T004_DISPOSABLE_TEST_DATABASE=1) |
| 2 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S04_T001_DISPOSABLE_TEST_DATABASE=1) |
| 2 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S04_T002_DISPOSABLE_TEST_DATABASE=1) |
| 2 | 1 | DB_FLAG | requires this task's disposable PostgreSQL database (M24_S04_T003_DISPOSABLE_TEST_DATABASE=1) |
| 2 | 1 | DB_FLAG | requires the task-owned disposable PostgreSQL database |
| 2 | 1 | DB_FLAG | Set M37_S04_DISPOSABLE_TEST_DATABASE=1 only for its task-owned disposable PostgreSQL database. |
| 2 | 2 | DB_FLAG | requires two task-owned disposable PostgreSQL databases |
| 1 | 1 | DB_FLAG | Requires an explicitly opted-in M01.S02.T005 disposable PostgreSQL database. |
| 1 | 1 | DB_FLAG | Set M03_DISPOSABLE_TEST_DATABASE=1 only for the task-owned disposable PostgreSQL database. |
| 1 | 1 | SERVICE | requires the task-owned disposable PostgreSQL and a local test MQTT broker |
| 1 | 1 | DB_FLAG | Set M19_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database. |
| 1 | 1 | DB_FLAG | requires the exact task-owned disposable PostgreSQL database |
| 1 | 1 | DB_FLAG | Set M31_S01_T002_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 1 | 1 | DB_FLAG | Set M31_S01_T003_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 1 | 1 | DB_FLAG | Set M31_S01_T004_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. |
| 1 | 1 | DB_FLAG | requires this task's explicitly guarded disposable PostgreSQL database |
| 1 | 1 | SERVICE | requires the task-owned disposable PostgreSQL and a local ClamAV daemon |

## Static inventory (AST scan of every skipif / pytest.skip / importorskip / mark.skip / xfail)

Reasons are grouped with task ids normalised to `<TASK>`. A skip inside a guard helper is shown with its enclosing `if` condition.

Static skip sites: 258 in 225 files. DB_FLAG=253, PLATFORM=1, SERVICE=4

### PLATFORM (1 sites)

| sites | files | reason (task ids normalised) | kinds | example |
|---|---|---|---|---|
| 1 | 1 | ffmpeg is not installed: the real poster/trim run is skipped (NOT_AVAILABLE path tested above) | skip | test_m47_s01_t007_content_hub_depth.py:338 `not real_ffmpeg` |

### SERVICE (4 sites)

| sites | files | reason (task ids normalised) | kinds | example |
|---|---|---|---|---|
| 2 | 2 | requires the task-owned disposable PostgreSQL and a local test SMTP server | skipif | test_m36_outbound_consent_db.py:25 `os.environ.get(TASK_DB_ENV) != '1' or not SMTP.startswith('127.0.0.1:')` |
| 1 | 1 | requires the task-owned disposable PostgreSQL and a local test MQTT broker | skipif | test_m17_s02_t005_mqtt_db.py:27 `os.environ.get(TASK_DB_ENV) != '1' or not BROKER.startswith('mqtt://127.0.0.1:')` |
| 1 | 1 | requires the task-owned disposable PostgreSQL and a local ClamAV daemon | skipif | test_m38_clamav_scan_db.py:31 `os.environ.get(TASK_DB_ENV) != '1' or not CLAMAV.startswith('127.0.0.1')` |

### DB_FLAG (253 sites)

| sites | files | reason (task ids normalised) | kinds | example |
|---|---|---|---|---|
| 96 | 96 | requires the task-owned disposable PostgreSQL | skipif | test_esign_user_signatures_db.py:27 `os.environ.get(TASK_DB_ENV) != '1'` |
| 49 | 49 | requires the task-owned disposable PostgreSQL runner | skipif | test_bom_explosion_nested_db.py:24 `os.environ.get('M21_DISPOSABLE_TEST_DATABASE') != '1'` |
| 11 | 11 | f"requires this task's disposable PostgreSQL database ({TASK_DB_ENV}=1) | skipif | test_m24_s02_t001_material_issue_db.py:32 `os.environ.get(TASK_DB_ENV) != '1'` |
| 10 | 6 | Run only with the task-owned disposable PostgreSQL database. | skipif | test_m31_s02_t002_event_schema_governance_db.py:56 `os.environ.get('M31_S02_T002_DISPOSABLE_TEST_DATABASE') != '1'` |
| 10 | 10 | requires the task-owned disposable PostgreSQL at the <TASK> head | skipif | test_m43_s01_t001_t002_oauth_mail_db.py:23 `os.environ.get('M43_S01_DB') != '1'` |
| 9 | 9 | Set <TASK>_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database. | skip | test_m02_refresh_token_rotation.py:44 `os.environ.get('M02_DISPOSABLE_TEST_DATABASE') != '1'` |
| 9 | 9 | Set <TASK>_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database. | skip | test_m13_landed_cost_posting.py:62 `os.environ.get('M13_S03_T001_DISPOSABLE_TEST_DATABASE') != '1'` |
| 7 | 7 | Set <TASK>_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database. | skip | test_m05_s03_t001_reservation_integrity_db.py:46 `os.environ.get('M05_S03_T001_DISPOSABLE_TEST_DATABASE') != '1'` |
| 7 | 7 | requires task-owned disposable PostgreSQL | skipif | test_m34_s01_t002_rfq_bids.py:83 `os.environ.get(TASK_DB_ENV) != '1'` |
| 6 | 6 | Run only against this task's explicitly named disposable PostgreSQL database. | skip | test_m31_s02_t002_event_schema_governance_db.py:40 `os.environ.get('M31_S02_T002_DISPOSABLE_TEST_DATABASE') != '1'` |
| 6 | 6 | f'Run only with {TASK_DB_ENV}=1 for the task-owned disposable PostgreSQL database. | skip | test_m34_s01_t001_sourcing_event.py:43 `os.environ.get(TASK_DB_ENV) != '1'` |
| 4 | 4 | f"Run only with {TASK_DB_ENV}=1 for this task's disposable PostgreSQL database. | skip | test_m34_s02_t003_bpa_release_orders.py:62 `os.environ.get(TASK_DB_ENV) != '1'` |
| 4 | 4 | requires this task's disposable PostgreSQL database | skipif | test_m34_s03_t003_supplier_governance_db.py:58 `os.environ.get(TASK_DB_ENV) != '1'` |
| 2 | 2 | Set <TASK>_DISPOSABLE_TEST_DATABASE=1 only for its task-owned disposable PostgreSQL database. | skip | test_m23_s04_t003_shop_floor_integration_db.py:36 `os.environ.get('M23_S04_T003_DISPOSABLE_TEST_DATABASE') != '1'` |
| 2 | 1 | requires the task-owned disposable PostgreSQL database | skipif | test_m34_s01_t001_sourcing_event.py:113 `os.environ.get(TASK_DB_ENV) != '1'` |
| 2 | 2 | f'Run only with {TASK_DB_ENV}=1 for this task-owned disposable PostgreSQL database. | skip | test_m34_s05_t001_sourcing_workflow_db.py:59 `os.environ.get(TASK_DB_ENV) != '1'` |
| 2 | 2 | requires two task-owned disposable PostgreSQL databases | skipif | test_m45_s01_t018_config_bundle.py:19 `os.environ.get('M45_DB') != '1' or not os.environ.get('M45_DB2_URL')` |
| 1 | 1 | requires the disposable <TASK> PostgreSQL | skipif | m48_ads_support.py:16 `os.environ.get('M48_DB') != '1'` |
| 1 | 1 | Requires an explicitly opted-in <TASK>.S02.T005 disposable PostgreSQL database. | skip | test_document_storage_pipeline.py:206 `os.environ.get('M01_S02_T005_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | Set <TASK>_DISPOSABLE_TEST_DATABASE=1 only for the task-owned disposable PostgreSQL database. | skip | test_m03_recipe_version_effective_dates.py:41 `os.environ.get('M03_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | <TASK> auth transaction regression requires PostgreSQL | skip | test_m20_auth_transaction_boundary.py:23 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | MPS material savepoint proof requires PostgreSQL | skip | test_m20_postgres_scenario_savepoint.py:25 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | V04 real rollback proof requires the PostgreSQL CI service | skip | test_m20_s01_t001_v03_mps_remediation.py:170 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | V04 concurrency proof requires the PostgreSQL CI service | skip | test_m20_s01_t001_v03_mps_remediation.py:244 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | <TASK> release-integrity proof requires PostgreSQL | skip | test_m20_strict_findings.py:28 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | <TASK> scenario status proof requires PostgreSQL | skip | test_m20_strict_findings.py:106 `'postgresql' not in str(settings.DATABASE_URL)` |
| 1 | 1 | requires the exact task-owned disposable PostgreSQL database | skipif | test_m23_s03_t003_execution_idempotency.py:40 `os.environ.get('M23_S03_T003_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | The isolated migration runner did not seed a pre-versioning event definition. | skip | test_m31_s02_t002_event_schema_governance_db.py:62 `not raw_id or not raw_code` |
| 1 | 1 | requires the <TASK>.S04.T001 task-owned disposable PostgreSQL database | skipif | test_m34_s04_t001_invoice_match_db.py:36 `os.environ.get('M34_S04_T001_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | requires the <TASK>.S04.T002 task-owned disposable PostgreSQL database | skipif | test_m34_s04_t002_tolerance_exception_db.py:38 `os.environ.get('M34_S04_T002_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | requires the <TASK>.S04.T003 task-owned disposable PostgreSQL database | skipif | test_m34_s04_t003_landed_cost_linkage_db.py:36 `os.environ.get('M34_S04_T003_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | requires the <TASK>.S04.T004 task-owned disposable PostgreSQL database | skipif | test_m34_s04_t004_purchase_invoice_posting_db.py:52 `os.environ.get('M34_S04_T004_DISPOSABLE_TEST_DATABASE') != '1'` |
| 1 | 1 | requires this task's explicitly guarded disposable PostgreSQL database | skipif | test_m34_s05_t003_three_way_finance_workflow_db.py:56 `os.environ.get(TASK_DB_ENV) != '1'` |
| 1 | 1 | requires the task-owned disposable PostgreSQL at head 20261125_0072 | skipif | test_m43_s00_t004_harness.py:67 `os.environ.get('M43_S00_T004_DB') != '1'` |


## Runner coverage (`run_all_db_tests.py --list`)

228 DB-gated files are discovered:

| flag type | files |
|---|---|
| legacy `<TASK>_DISPOSABLE_TEST_DATABASE` (incl. `ESIGN_SIG_…`, `M39_CBK_…`, `M38_AV_…`) | 159 |
| `M43_S01_DB`, `M43_S00_T004_DB`, `M44_DB`, `M45_DB`, `M46_DB`, `M48_DB` (M48 files via `m48_ads_support.DB` are detected through the helper import) | 66 |
| `DATABASE_URL` must be PostgreSQL (M20) | 3 |

Runner classes:

- **224 RUN.**
- **4 SERVICE_REQUIRED.** These run automatically once their env var is exported:
  - `test_m17_s02_t005_mqtt_db.py`: MQTT_TEST_BROKER_URL
  - `test_m36_outbound_consent_db.py`: SMTP_TEST_SERVER, plus optional MAILPIT_TEST_API
  - `test_m36_s02_t005_campaigns_db.py`: SMTP_TEST_SERVER
  - `test_m38_clamav_scan_db.py`: CLAMAV_TEST_HOST
- **0 UNPARSABLE.**

Special cases:

- **Second DB.** `test_m45_s01_t018_config_bundle.py` and `test_m45_s01_t020_warehouse_export.py` get a second database cloned from the template as `M45_DB2_URL`.
- **Legacy prep.** Three files get the prep copied from their original coordination/sessions/*.ps1 runners:
  - `test_m25_s02_t003_landed_cost_actuals.py`
  - `test_m25_s02_t004_currency_rates.py`
  - `test_m31_s02_t002_event_schema_governance_db.py`

  The prep is: downgrade to 20261029_0038 / 20261029_0043, seed the legacy rows, then upgrade to head.

**Genuine defect found by the prep (not fixed, not runner related).** The downgrade from head 20261128_0078 works. Re-upgrading fails at 20261119_0043:

```
UndefinedTableError: relation "mkt_email_designs" does not exist
[SQL: CREATE TABLE crm_email_campaigns ( ... FOREIGN KEY(design_id) REFERENCES mkt_email_designs (id) ...)]
```

- **Cause:** `alembic/versions/20261119_0043_crm_email_campaigns.py` creates the table from the *current* `CRMEmailCampaign` model. That model has since gained FKs to `mkt_email_designs`, which migration 20261125_0074 creates later.
- **Why fresh databases pass:** the squashed baseline `create_all` builds every table, so the bug stays hidden there.
- **Impact:** any database that replays the chain below 0043 fails.
- **Fix belongs to the coordinator/migration owner:** pin the 0043 table definition, or create it without the later columns.
- **Until fixed:** the legacy-prep files report `ERROR (prep upgrade head failed)`.
  - Observed for `test_m25_s02_t003_landed_cost_actuals.py` and `test_m31_s02_t002_event_schema_governance_db.py`.
  - Not yet run: `test_m25_s02_t004_currency_rates.py`. It takes the same downgrade-to-0038 path, so it is expected to fail the same way.
