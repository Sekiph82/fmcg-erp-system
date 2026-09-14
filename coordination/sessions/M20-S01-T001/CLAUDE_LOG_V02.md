# M20-S01-T001 — Claude Remediation Log V02

Factual remediation log for M20.S01.T001 V02, addressing the frozen finding
set in `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md`. Contains
no audit verdict.

## Commit SHAs

- `origin/main` SHA at the start of this V02 pass: `e8f3018`
- Synchronized to (fast-forward, adding V02 audit/prompt docs): `598741a`
- Implementation commit: `826891b`
- Current `main` HEAD after push: `826891b`

## Synchronization performed

1. `git status --short` — clean except the untracked `.hiveai/EVENT_INDEX.json`
   leftover (unchanged, not tracked, not touched).
2. `git fetch origin && git status --short --branch` — local was behind by 3
   commits (`e8f3018..598741a`).
3. `git pull --ff-only origin main` — fast-forwarded cleanly. The 3 new
   commits added `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V02.md`,
   `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md`,
   `coordination/sessions/M20-S01-T001/CHATGPT_PROMPT_V02.md`.
4. No stash, no conflict, no discarded local work.
5. `git push origin main` for the implementation commit succeeded on the
   first attempt (no concurrent remote advance this time).

No force push, `git reset --hard`, `git clean`, or destructive
`git checkout`/`restore` was used at any point.

## Instructions read

`coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md` (the frozen
finding set F-V01-001 through F-V01-009) and
`coordination/sessions/M20-S01-T001/CHATGPT_PROMPT_V02.md` (this pass's
execution instructions). Also re-read, as part of remediation, the current
source of `backend/app/services/mps_service.py`,
`backend/app/models/recipe.py`, `backend/app/models/master.py`
(`Warehouse`, `Product`, `UnitOfMeasure`), `backend/app/models/production.py`
(`ProductionOrder`), `backend/app/models/mrp.py` (`MRPRun`, `MRPResult`),
and `backend/app/core/deps.py` / `backend/app/core/access_control.py`.

## Files changed (exact)

`826891b` — `fix(mps): remediate V01 audit findings F-V01-001..007 (M20.S01.T001 V02)`:

- `backend/app/services/mps_service.py` (74 lines changed)
- `backend/tests/test_m20_s01_t001_mps_hardening.py` (16 lines changed —
  updated mock wiring to match the new call sequence, not a weakened
  assertion)
- `backend/tests/test_m20_s01_t001_v02_mps_remediation.py` (new file, 407
  lines, 16 tests)

No other file was modified by this pass.

## Remediation performed, by finding

### F-V01-001 — real auth/RBAC negative+positive proof

Before: the only proof was `inspect.getsource()` checking that
`_SYSTEM_USER` was absent and `require_permission`/`current_user.id` were
present as text in `api/v1/endpoints/mps.py`.

After: `backend/tests/test_m20_s01_t001_v02_mps_remediation.py` adds 4 tests
using `fastapi.testclient.TestClient(app)` against the actual running app
object (`app.main.app`), with `app.dependency_overrides` substituting only
`get_current_user` (and, for the 2 tests that need a full 200 response,
`get_db`) — `require_permission`, `has_permission`, and the real route
wiring are exercised unmodified:
- `test_unauthenticated_mps_dashboard_request_is_rejected`: no dependency
  override at all, real cookie-based auth path, asserts `401` /
  `"Not authenticated"`.
- `test_authenticated_user_without_permission_cannot_approve_plan`: fake
  user with zero granted permission codes, asserts `403` and that the
  `forbidden_detail` payload names `mps.approve`.
- `test_authenticated_user_with_permission_reaches_protected_path`: fake
  user granted `mps.view`, fake `get_db` returning an empty plan list,
  asserts `200` and `[]`.
- `test_superuser_bypasses_permission_check_and_reaches_protected_path`:
  fake `is_superuser=True` user with no explicit permission codes, same
  fake `get_db`, asserts `200`.

This repository has no pre-existing test that does this (confirmed by
searching `backend/tests/` for `TestClient`/`AsyncClient` usage against the
app's own routes before writing these — the only 2 hits use `AsyncClient`
to mock *outbound* third-party HTTP calls, not inbound routes; there is no
`conftest.py` anywhere in the suite).

### F-V01-002 — MRP run context lineage

Before: `generate_mps_from_mrp` checked only that the referenced `MRPRun`
exists and is `COMPLETED`; nothing prevented attaching a run unrelated to a
plan that had already been generated from a different run.

After: added a check, before the MRP run lookup, that if
`plan.mrp_run_id is not None and plan.mrp_run_id != req.mrp_run_id`, raise
`ValueError`. Investigated whether a stronger (warehouse/plant) check is
possible: `MPSPlan` has `plant_code` (a free-text `String`, no foreign key)
and no `warehouse_id`/`company_id`/`branch_id` column at all; `MRPRun` has
`warehouse_id` (a real FK to `Warehouse`, nullable). There is no existing
relation between the two that a query could join or compare — run identity
is the only deterministic lineage check the current schema supports. This
is stated directly in a code comment at the check site.

While writing the test for this (`test_generate_from_mrp_allows_regenerating_from_the_same_run`),
found and fixed a separate, real, pre-existing defect: the MRP-results
query used `MRPResult.mrp_run_id`, but `MRPResult`'s actual foreign-key
column (per `backend/app/models/mrp.py`) is named `run_id`. `MRPResult` has
no `mrp_run_id` attribute at all, so `select(MRPResult).where(MRPResult.mrp_run_id
== ...)` raised `AttributeError` at query-construction time — meaning
`generate_mps_from_mrp` would fail on *every* call that got past the
run-existence/status checks, i.e. every real successful generation attempt.
This was not caught by any V01 test because both V01 tests for this
function intentionally short-circuit on `ValueError` before reaching that
line (missing run / non-`COMPLETED` run) — neither exercised the success
path. Fixed by changing `MRPResult.mrp_run_id` to `MRPResult.run_id`.
Searched the rest of the codebase (`grep -rn "MRPResult\.mrp_run_id" app/`)
for the same mistake elsewhere: no other occurrences.

### F-V01-003 — target warehouse validated before release

Before: `target_warehouse_id` was written directly into every created
`ProductionOrder` with no existence or status check.

After: `release_mps_plan` now does `warehouse = await db.get(Warehouse,
target_warehouse_id)` before the release loop; raises `ValueError` if not
found, and a second `ValueError` if `not warehouse.is_active`. Both checks
happen before any `ProductionOrder` is constructed or added, so an invalid
warehouse fails the whole call with zero partial orders created (the
existing `async with db.begin():` transaction wrapper in the endpoint layer
was already relied on elsewhere in this codebase for atomic rollback and
required no change).

### F-V01-004 — deterministic lifecycle-correct recipe selection

Before: `select(Recipe).where(Recipe.product_id == line.product_id,
Recipe.is_active == True).limit(1)`, no ordering.

After: new function `_select_release_recipe(db, product_id)` filters on
`Recipe.status == RecipeStatus.APPROVED` (in addition to `is_active`) and
an effective-date window (`valid_from <= today` or null,
`valid_to >= today` or null), ordered by `Recipe.valid_from.desc().nulls_last(),
Recipe.created_at.desc()` before `limit(1)`, so selection among multiple
currently-effective `APPROVED` recipes for one product is deterministic
(most recently effective, then most recently created) rather than
whatever order the database happens to return. Uses only pre-existing
`Recipe` columns (`status`, `is_active`, `valid_from`, `valid_to`,
`created_at`); no new field or parallel lifecycle was introduced.

### F-V01-005 — UOM derived from product

Before: every `ProductionOrder` was created with the literal `uom="KG"`.

After: `product = await db.get(Product, line.product_id)` is fetched per
line, and `uom=product.uom.value if product and product.uom else "KG"`
(`Product.uom` is `Enum(UnitOfMeasure)`; `"KG"` remains only as the
defensive fallback if a product record is somehow missing, which cannot
normally happen given the `Product` FK on `MPSLine.product_id`, but is kept
so this can never raise on a null product rather than silently producing an
invalid order).

### F-V01-006 — truthful RELEASED state

Before: `plan.status = MPSStatus.RELEASED` and `plan.released_at = ...`
were set unconditionally after the per-line loop, regardless of whether any
`ProductionOrder` was actually created.

After: `release_complete = created > 0`; the `RELEASED` status transition
and `released_at` timestamp are now inside `if release_complete:` — if zero
orders were created (e.g. every `FEASIBLE` line was skipped for lack of an
approved effective recipe, or an invalid warehouse was caught before any
line was processed), the plan is left at `APPROVED` so a retry can succeed
once the underlying issue (missing recipe, wrong warehouse) is fixed. The
return dict gained an explicit `"release_complete": bool` key alongside the
existing `released_orders`/`skipped_no_recipe`/`skipped_ineligible` keys.

### F-V01-007 — behavioral repeated-release proof

Before: the only proof was `test_release_eligible_and_ineligible_queries_exclude_already_released_lines`,
which asserts the source text of `release_mps_plan` contains
`"MPSLine.production_order_id == None"` twice — a static text check, not an
executed behavior.

After: added `test_repeated_release_call_is_rejected_and_creates_no_second_order`,
which calls `svc.release_mps_plan(db, plan.id, ...)` twice against the same
mutable mocked `plan`/`line` objects. The first call succeeds and mutates
`plan.status` to `RELEASED` in place (as the real function does on a real
ORM object); the second call is asserted to raise `ValueError` matching
`"APPROVED"`, and `db.add.call_count` is asserted unchanged between the two
calls (no second `ProductionOrder` was ever constructed), and
`db.execute.await_count == 6` proves the second call issued only the one
plan-lookup query before rejecting (out of a 6-query side-effect list sized
for exactly: first-call plan lookup, eligible-lines, ineligible-count,
po-count, recipe lookup, second-call plan lookup — with nothing left over
for the second call to have run further). The pre-existing source-count
test was kept as supplementary evidence, not the primary proof.

### F-V01-008 — regression evidence

See "Commands executed and exact results" below for the full command list
and outputs. Summary: the new V02 file (16 tests) and the updated V01 file
(17 tests) both pass in full; a broader run across
`mps`/`mrp`/`module_registry`/`gap007`/`gap015`/`permission`/`recipe`/`warehouse`/`production`
keyword-matched tests produced 169 passed and the same 3 pre-existing
failures already identified and isolated in the V01 log
(`test_gap012_document_knowledge_access.py`,
`test_gap013_report_builder_access.py`,
`test_gap014_notification_center_access.py`, each
`..._routes_register_from_module_registry`, each failing with
`AttributeError: '_IncludedRouter' object has no attribute 'path'`) — the
exact same 3, with the exact same error, reproduced again after this pass's
code changes, which is further evidence (on top of the V01 log's
before/after `git stash` isolation) that they are unrelated to MPS/MRP
work. No frontend file was touched in this V02 pass, so frontend
type-check/build was not re-run (it was run and passed in V01, for the one
frontend file that pass did touch).

### F-V01-009 — migration ownership proof

No code or schema change was needed for any V02 remediation item — all
nine findings were addressed with Python-level query/logic changes in
`mps_service.py` and test changes; none require a migration. Re-confirmed
`python -m alembic heads` still returns a single head, `20260602_0001`,
unchanged.

Considered attempting a stronger, literal fresh-database proof (running
`alembic upgrade head` against a throwaway SQLite database and inspecting
the resulting schema for the six MPS tables) beyond the static-analysis
proof already given in `CLAUDE_LOG_V01.md`. Did not attempt it:
`grep -l "postgresql.UUID\|JSONB\|CREATE EXTENSION\|postgresql.ENUM"
backend/alembic/versions/*.py` matches 49 migration files, confirming the
entire migration chain (including the squashed baseline itself, which runs
`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`) depends on PostgreSQL-only
constructs and would not run to completion against SQLite for reasons
unrelated to MPS. No live PostgreSQL instance is available in this
environment. The static-analysis proof already on record in
`CLAUDE_LOG_V01.md` (exact revision `20260517_0000`, exact code —
`import app.models; Base.metadata.create_all(bind=bind, checkfirst=True)`
— and the exact `env.py` idempotent-DDL-patch mechanism that lets later
revisions' FK references to `mps_plans`/`mps_lines` succeed without erroring)
stands as the evidence for this finding.

## Commands executed and exact results

```
git status --short
git fetch origin
git status --short --branch                → "behind 3"
git pull --ff-only origin main              → fast-forward to 598741a

python -m py_compile app/services/mps_service.py \
    tests/test_m20_s01_t001_mps_hardening.py \
    tests/test_m20_s01_t001_v02_mps_remediation.py
    → exit 0, no output

python -m pytest tests/test_m20_s01_t001_v02_mps_remediation.py -v -p no:warnings
    → first run: 5 failed, 11 passed (see "Failures encountered" below)
    → after fixes: 16 passed in 14.69s

python -m pytest tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py -q -p no:warnings
    → first run: 2 failed, 31 passed (missing plan.mrp_run_id on 2 fixtures)
    → after fix: 33 passed in 14.76s

python -m pytest tests/ -k "mps or mrp or module_registry or gap007 or gap015 or permission or recipe or warehouse or production" -q -p no:warnings
    → 169 passed, 3 failed, 471 deselected
    failing (identical to V01, same error):
      tests/test_gap012_document_knowledge_access.py::test_document_knowledge_esign_routes_register_from_module_registry
      tests/test_gap013_report_builder_access.py::test_report_builder_routes_register_from_module_registry
      tests/test_gap014_notification_center_access.py::test_notification_routes_register_from_module_registry
    each: AttributeError: '_IncludedRouter' object has no attribute 'path'

python -m alembic heads
    → "20260602_0001 (head)"

grep -rn "MRPResult\.mrp_run_id" app/
    → no matches (confirms the fix removed the only occurrence)

grep -l "postgresql.UUID\|JSONB\|CREATE EXTENSION\|postgresql.ENUM" alembic/versions/*.py | wc -l
    → 49

git diff --check
    → clean (exit 0; only a CRLF line-ending advisory from git, no error)

git add backend/app/services/mps_service.py \
    backend/tests/test_m20_s01_t001_mps_hardening.py \
    backend/tests/test_m20_s01_t001_v02_mps_remediation.py
git diff --staged -- TASKS.md TASKS_HISTORY.md \
    coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md \
    coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V02.md
    → empty (0 lines) for all four files

git commit -m "fix(mps): remediate V01 audit findings F-V01-001..007 (M20.S01.T001 V02)" → 826891b
git push origin main → "598741a..826891b main -> main" (succeeded, no rejection)
```

## Failures encountered and corrections made

1. First draft of `test_authenticated_user_with_permission_reaches_protected_path`
   and `test_superuser_bypasses_permission_check_and_reaches_protected_path`
   failed with `500` because the faked `get_db` override yielded a bare
   `AsyncMock()`, and `list_plans` (like every MPS route) does
   `async with db.begin():` — an `AsyncMock`'s `.begin()` returns a
   coroutine by default, which does not support the async context-manager
   protocol (`TypeError: 'coroutine' object does not support the
   asynchronous context manager protocol`). Correction: added a
   `_fake_session()` helper that sets `db.begin = MagicMock(side_effect=
   <a contextlib.asynccontextmanager-wrapped no-op>)`, so `db.begin()`
   returns a real async context manager, matching how every MPS endpoint
   actually uses the session.
2. First draft of `test_generate_from_mrp_rejects_switching_to_an_unrelated_run`
   failed with `StopAsyncIteration` because the mocked `db.execute`
   side-effect list had only one entry (the plan lookup), but the lineage
   check was originally placed *after* the MRP-run lookup, so the code
   tried to execute a second query the mock wasn't configured for.
   Correction: moved the lineage check earlier (right after the
   `DRAFT`-status check, before the MRP-run lookup) since it needs no
   database query at all — this is also a genuine improvement (fails
   faster, one less query on the rejection path), not just a test
   convenience.
3. `test_generate_from_mrp_allows_regenerating_from_the_same_run` (the
   first test in this task to actually exercise `generate_mps_from_mrp`
   past its guard clauses into the MRP-results query) failed with
   `AttributeError: type object 'MRPResult' has no attribute 'mrp_run_id'`.
   This is the real, pre-existing bug described under F-V01-002 above.
   Correction: changed the query to use `MRPResult.run_id`.
4. `test_release_stays_approved_when_every_feasible_line_is_skipped` failed
   with `AttributeError: 'types.SimpleNamespace' object has no attribute
   'released_at'` because the plan fixture never set that attribute and the
   remediated code no longer touches it on the fail-closed path.
   Correction: added `released_at=None` to the shared `_plan()` test
   fixture factory.
5. After the above fixes, running the pre-existing V01 test file together
   with the new V02 file surfaced 2 more failures
   (`test_generate_from_mrp_rejects_missing_run`,
   `test_generate_from_mrp_rejects_non_completed_run`) with the same
   `AttributeError` on `plan.mrp_run_id`, because those two pre-existing
   fixtures (inline `SimpleNamespace` plans, not using the new `_plan()`
   factory) never set `mrp_run_id` either, and the new lineage-check line
   reads it unconditionally. Correction: added `mrp_run_id=None` to both
   inline fixtures in `test_m20_s01_t001_mps_hardening.py`.
6. The pre-existing V01 test `test_release_only_creates_orders_for_feasible_lines_and_counts_ineligible`
   needed updating (not weakening — its assertions are unchanged and one
   was added) because `release_mps_plan`'s call sequence grew two new
   `db.get()` calls (warehouse, then product) and its recipe fixture needed
   `status`/`valid_from`/`valid_to` fields to satisfy the new
   `_select_release_recipe` filter. Correction: extended `_mock_db()` with
   an optional `get_results` parameter and updated the fixture and
   assertions (added `assert result["release_complete"] is True`).

## Deviations from the execution prompt

None identified. All 9 required remediation items and the mandated output
(commit + push, `CLAUDE_LOG_V02.md` at the exact specified path, no
`CHATGPT_AUDIT_V02.md`, no `TASKS.md`/`TASKS_HISTORY.md` edit) were
completed as specified.

## Unresolved blockers

None specific to this V02 pass. The full 626-item `pytest tests/ -q` suite
was not re-attempted in this pass (already documented as impractically slow
in this environment in `CLAUDE_LOG_V01.md`, for reasons unrelated to MPS);
the targeted 169-test regression run above is the evidence produced for
this pass instead.

## Remaining technical risks

- `_select_release_recipe`'s effective-date and status filter assumes
  `Recipe.valid_from`/`valid_to` are used consistently as an effective-date
  window across the codebase; this was not independently verified beyond
  reading the `Recipe` model definition.
- The MRP run context-lineage check (F-V01-002) only compares run identity.
  It cannot detect a plan/run warehouse or plant mismatch, because
  `MPSPlan` has no `warehouse_id`/`company_id`/`branch_id` column to
  compare against `MRPRun.warehouse_id` — this is a schema limitation, not
  a code defect, and is documented at the check site and here rather than
  worked around by adding new schema (out of this task's scope per the V02
  prompt's scope boundary).
- `release_mps_plan`'s fail-closed behavior (F-V01-006) means a plan with
  FEASIBLE lines that all lack an approved recipe now stays `APPROVED`
  indefinitely until a recipe is fixed; there is no automatic notification
  or alert that release did not complete — the caller must inspect the
  returned `release_complete`/`skipped_no_recipe` fields.
- No live PostgreSQL database was used for any test in this task or this
  log pass; all service-level tests use a mocked `AsyncSession`, and the
  new endpoint-level tests use FastAPI's `TestClient` with `get_db`
  overridden to a mocked session rather than a real one. Runtime behavior
  against a real database instance has not been independently verified.
- The `MRPResult.run_id` fix (correcting the prior `mrp_run_id` typo) has
  only been exercised by this task's own new mocked test; it has not been
  verified against a real MRP run's actual result rows in a live database.

## Migration findings

No schema change was made or required by this V02 pass. `python -m alembic
heads` returns a single head, `20260602_0001`, unchanged from before this
pass. See "F-V01-009" above for the full migration-ownership evidence
(carried over from `CLAUDE_LOG_V01.md`, re-confirmed here) and the reasoning
for not attempting a literal fresh-SQLite-database proof.

## Tracker integrity

`TASKS.md` and `TASKS_HISTORY.md` were not modified by this pass:

```
git diff e8f3018 826891b -- TASKS.md TASKS_HISTORY.md    → empty
```

`coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md` and
`CHATGPT_AUDIT_CRITERIA_V02.md` were not modified by this pass:

```
git diff e8f3018 826891b -- coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md   → empty
git diff e8f3018 826891b -- coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V02.md   → empty
```

(`CHATGPT_AUDIT_CRITERIA_V02.md` was newly added to `origin/main` by
ChatGPT before this pass began, as part of the `e8f3018..598741a`
fast-forward described above — it was read but never written to by this
session.)

No `CHATGPT_AUDIT_V02.md` file was created by this pass.

AWAITING_AUDIT
