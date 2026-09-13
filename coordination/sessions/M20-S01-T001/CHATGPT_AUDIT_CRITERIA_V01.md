# M20-S01-T001 V01 — Strict Audit Criteria

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Task: `M20.S01.T001 — Map existing MPS models/APIs/UI/services to enterprise requirements`

This revision is the first FMCG ERP task to use the versioned independent-audit session protocol. A green test count alone is insufficient. The audit will inspect source, exact diff, state-transition integrity, auth/RBAC, migration ownership, cross-module assumptions, test sensitivity and implementation evidence.

## A. Governance / synchronization / scope

- **M20S01-V01-001** Work only in `Sekiph82/fmcg-erp-system` on `main`.
- **M20S01-V01-002** Safely synchronize `C:\Users\sekip\Desktop\fmcg-erp-system` with `origin/main` before edits.
- **M20S01-V01-003** Preserve all pre-existing tracked/untracked owner work; no destructive reset/clean/restore and no force push.
- **M20S01-V01-004** GitHub `main` remains canonical current-state authority.
- **M20S01-V01-005** Root `TASKS.md` and `TASKS_HISTORY.md` are read but remain unmodified by Claude.
- **M20S01-V01-006** Read `AGENTS.md`, root `TASKS.md`, `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, the active prompt and these criteria before implementation.
- **M20S01-V01-007** Do not recreate `.hiveai` as a competing live tracker.
- **M20S01-V01-008** Do not rebuild the MPS subsystem; preserve existing MPS dashboard/planning-board/capacity/campaign/what-if architecture.
- **M20S01-V01-009** No unrelated refactor or drive-by module cleanup.
- **M20S01-V01-010** Exact changed-file list is recorded in `CLAUDE_LOG_V01.md`.

## B. Existing capability reconciliation

- **M20S01-V01-011** Existing MPS models, API, services, frontend pages, MRP linkage, capacity, campaign, what-if and AI recommendation surfaces are mapped in the log before modification.
- **M20S01-V01-012** Already-present capabilities are reused rather than duplicated with parallel models/services/pages.
- **M20S01-V01-013** Any claimed missing capability is supported by source evidence, not roadmap wording alone.
- **M20S01-V01-014** Immediate upstream dependencies include MRP/demand/forecast/inventory/BOM/work-center data as applicable.
- **M20S01-V01-015** Immediate downstream consumers include production orders/execution and relevant audit/permission behavior as applicable.

## C. Authentication / RBAC / actor truth

- **M20S01-V01-016** Production MPS endpoints use the repository's authenticated current-user dependency rather than a hard-coded/system UUID actor.
- **M20S01-V01-017** Privileged operations use the repository's existing permission pattern consistently.
- **M20S01-V01-018** At minimum create/edit/approve/release/AI-review mutation paths are not anonymously or system-user attributable when invoked by a real user.
- **M20S01-V01-019** Read paths remain protected consistently with repository architecture.
- **M20S01-V01-020** Negative tests prove unauthenticated and/or unauthorized mutation paths fail for the intended authorization reason.

## D. MPS state-machine invariants

- **M20S01-V01-021** `DRAFT -> APPROVED -> RELEASED` is enforced by code, not comments/error text only.
- **M20S01-V01-022** A DRAFT plan cannot be released.
- **M20S01-V01-023** An already RELEASED/CLOSED plan cannot be released again.
- **M20S01-V01-024** Approval is allowed only from the intended predecessor state.
- **M20S01-V01-025** Release creates production orders only from lines that satisfy the explicitly defined eligibility law.
- **M20S01-V01-026** If the intended law is FEASIBLE-only, non-FEASIBLE states (`PENDING`, `OVERLOADED`, `MATERIAL_SHORT`, `INFEASIBLE`, `ON_HOLD`) cannot create production orders.
- **M20S01-V01-027** Releasing a plan with ineligible/skipped lines cannot silently misrepresent those lines as successfully released.
- **M20S01-V01-028** Repeated release is idempotent/fail-closed and cannot duplicate production orders.

## E. System-owned vs planner-owned line state

- **M20S01-V01-029** Generic planner line editing cannot arbitrarily author engine-owned feasibility truth unless explicitly justified by architecture.
- **M20S01-V01-030** Planner-editable fields and system-derived fields are separated or guarded coherently.
- **M20S01-V01-031** Any manual override that locks a line preserves a truthful audit/state meaning.
- **M20S01-V01-032** A negative test directly proves the protected system-derived state cannot be bypassed through the generic PATCH contract.

## F. MRP / demand lineage integrity

- **M20S01-V01-033** MPS generation validates that the referenced MRP run exists and is appropriate for generation.
- **M20S01-V01-034** MPS generation does not silently accept an unrelated/stale/mismatched MRP result set where the service contract should reject it.
- **M20S01-V01-035** Existing demand decomposition fields remain traceable to current MRP result truth.
- **M20S01-V01-036** The task does not create a second independent demand engine when MRP already consolidates sales orders/forecast/safety stock/supply.

## G. Capacity / campaign / what-if reconciliation boundaries

- **M20S01-V01-037** Existing capacity/campaign/what-if services remain functional after hardening.
- **M20S01-V01-038** No new claim is made that current 8-hour/default-throughput capacity logic is enterprise-complete; deeper capacity work remains bounded to later M20 tasks unless required to fix a correctness defect here.
- **M20S01-V01-039** Existing campaign grouping/what-if/AI behavior is not casually redesigned in this V01 task.
- **M20S01-V01-040** What-if and AI recommendation paths remain non-destructive to live plan state unless an existing documented action explicitly authorizes mutation.

## H. Production-order creation integrity

- **M20S01-V01-041** Target warehouse existence/reference validity is enforced before creating production orders.
- **M20S01-V01-042** Active/approved recipe selection follows existing recipe lifecycle rules rather than choosing an arbitrary active record when stronger status/effective-date truth exists.
- **M20S01-V01-043** Production-order creation preserves existing model field semantics/UOM expectations and does not introduce a hard-coded assumption inconsistent with the selected product/recipe contract.
- **M20S01-V01-044** Partial failure cannot leave a misleading successful plan transition without truthful release result/state.
- **M20S01-V01-045** Created production orders remain linked back to their MPS lines exactly once.

## I. API / frontend contract

- **M20S01-V01-046** Existing frontend MPS pages remain API-compatible.
- **M20S01-V01-047** Frontend approval/release visibility remains aligned with backend state law.
- **M20S01-V01-048** Backend hardening does not rely on frontend hiding buttons for security or workflow correctness.
- **M20S01-V01-049** Any API response-shape changes are reflected in `frontend/src/lib/mps.ts` and relevant pages/tests.

## J. Schema / migration ownership

- **M20S01-V01-050** Before adding/changing schema, inspect Alembic ownership for all current MPS tables/columns.
- **M20S01-V01-051** No new migration is created merely because a model exists; migration change occurs only for an actual schema delta.
- **M20S01-V01-052** If schema changes are required, Alembic remains single-head and upgrade/downgrade discipline is preserved.
- **M20S01-V01-053** If no schema change is needed, the log explicitly records that conclusion and evidence.

## K. Tests / sensitivity / regression

- **M20S01-V01-054** Add focused backend tests for the corrected MPS invariants.
- **M20S01-V01-055** Illegal DRAFT release test is load-bearing and would fail if DRAFT release were re-enabled.
- **M20S01-V01-056** Non-FEASIBLE release test is load-bearing and would fail if eligibility filtering were removed.
- **M20S01-V01-057** Auth/RBAC test is load-bearing and would fail if the system-user bypass were restored.
- **M20S01-V01-058** Generic PATCH protection test is load-bearing if system-owned state is hardened.
- **M20S01-V01-059** Repeated release/duplicate-order behavior is explicitly tested.
- **M20S01-V01-060** Relevant existing MRP/production/MPS tests remain green.
- **M20S01-V01-061** Backend import/compile checks remain clean.
- **M20S01-V01-062** Frontend type-check/build or the repository's relevant frontend validation remains clean if frontend files are touched.
- **M20S01-V01-063** `git diff --check` is clean for the authorized implementation diff.
- **M20S01-V01-064** No existing strict test is deleted/disabled/weakened merely to obtain green.

## L. Evidence / log / handoff

- **M20S01-V01-065** Create `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md`.
- **M20S01-V01-066** Log records synchronized start HEAD, preserved local work, exact changed files, commands/results, failures/fixes, migration conclusion and implementation commit(s).
- **M20S01-V01-067** Prompt-mandated checks are individually recorded; aggregate pass count alone is insufficient.
- **M20S01-V01-068** Log explicitly confirms `TASKS.md` and `TASKS_HISTORY.md` were read but not modified.
- **M20S01-V01-069** All authorized work is pushed safely to `origin/main` without force.
- **M20S01-V01-070** Claude hands back `AWAITING_AUDIT` or `BLOCKED`; it does not assign an audit verdict or close the tracker task.

## M. Closure law

- **M20S01-V01-071** Claude green tests do not close M20.S01.T001 by themselves.
- **M20S01-V01-072** ChatGPT independently audits the matching prompt/log/commit/diff against these criteria.
- **M20S01-V01-073** ChatGPT updates root `TASKS.md` only after that audit.
- **M20S01-V01-074** If material defects or proof gaps remain, ChatGPT performs the whole-task attack-surface sweep, freezes the complete finding set, and issues V02 rather than advancing.
- **M20S01-V01-075** Because MPS release/auth/state mutation is critical ERP behavior, final task closure may require an auditor-authored adversarial validation revision even if V01 implementation audit finds no additional source defect.
