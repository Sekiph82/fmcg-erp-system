# M43 gate — step 1: database migration (2026-11-25)

- **Environment:** disposable `postgres:16-alpine`, container `m43-gate-pg`, port 127.0.0.1:25432, trust auth, synthetic data only.
- **Code:** main at `a64f06a`, plus the backfill fix in this commit.

| Check | Result |
|---|---|
| Empty → head (`20261125_0073`) | PASS |
| Downgrade head → `20261124_0071`, then upgrade → head | PASS |
| Seeded `20261124_0071` (`seed_prev_head.sql`) → head, run first | **FAIL**: `NotNullViolation crm_teams.active_flag` in the team backfill |
| Same, after the fix (explicit `active_flag` in the backfill INSERT) | PASS, 14/14 expectations in `check_backfill.sql` |

## Root cause of the failure

- The squashed baseline and the orphan-table migrations call `create_all` from the *current* models.
- So on any database built by this repository, the M43 tables already exist when 0073 runs.
- In that case 0073's `CREATE TABLE IF NOT EXISTS` is skipped, and with it the SQL server defaults.
- The fix: backfill INSERTs now name every NOT NULL column.

## Residual note for the reviewer

- On databases bootstrapped this way, CHECK constraints written inside 0073's `CREATE TABLE` bodies are not added.
- These are:
  - stage-approval no-self-approval
  - team not its own parent
  - value-range checks
- Enforcement still happens in the application:
  - `crm_routing_service.decide`
  - `crm_team_service.check_no_cycle`
  - pydantic bounds
- Partial unique indexes are created separately and are present.
