# M20.S01.T002 Codex Execution Log V01

Status: `AWAITING_CHATGPT_AUDIT`
Builder: Codex
Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Implementation commit: `95176af0c1583d275c9d73e0135d34cfa4895c8a`
Published main tip after remote prompt merge: `3532f73178d76805da2714177243c36dc2f4c7b0`

## Scope

Preserve the existing MPS planning-board, capacity, campaign, and what-if
surfaces with bounded regression coverage. No new MPS product capability was
invented. The implementation closes two isolation regressions found while
exercising the existing surfaces:

- A line update now requires both the route MPS plan ID and line ID to match.
- A what-if scenario rejects line IDs that are not returned for its MPS plan.

The existing T001 protections for MPS ownership, seeded permissions, planner-
controlled line fields, and unsupported what-if change types were retained in
the working MPS source state.

## Evidence Matrix

| Feature | Model/service source | API surface | UI surface | Regression evidence | Observed limitation |
|---|---|---|---|---|---|
| Planning board | `MPSPlan`, `MPSLine`; `mps_service.py` | Plan and line list/update routes | `dashboard/mps/planning-board`; `mpsApi.listLines/updateLine` | Cross-plan line update rejection; T001 auth and planner-field tests | No new planning-board workflow was added. |
| Capacity | `MPSCapacitySlot`; `mps_capacity_service.py` | `run-capacity`, `capacity-heatmap`, reschedule suggestion | `dashboard/mps/capacity`; matching `mpsApi` methods | Infinite-capacity locked-line behavior and missing-plan negative case | Local PostgreSQL execution was unavailable; accepted T001 PG CI evidence is prior-run evidence. |
| Campaigns | `MPSCampaign`; `mps_campaign_service.py` | `run-campaigns`, campaign list | `dashboard/mps/campaigns`; matching `mpsApi` method | Empty-plan grouping is idempotent; route/API alignment check | Existing grouping behavior was preserved; no new campaign algorithm was introduced. |
| What-if | `MPSWhatIfScenario`; `mps_whatif_service.py` | create/list/get what-if routes | `dashboard/mps/whatif`; matching `mpsApi` methods | Foreign-plan line rejection plus T001 supported/unsupported change tests | `MERGE` and `SHIFT_ADD` remain explicitly unsupported; simulation does not mutate the live plan. |
| Approval/release integration | MPS status and release service paths | approve/release routes | Main MPS surface | T001 hardening suite covers status and release guards | Full PostgreSQL concurrency/sequence proof is deferred to CI quota availability. |

## Changed Files

- `backend/app/services/mps_service.py`: scope line update by `mps_id` and `line_id`.
- `backend/app/api/v1/endpoints/mps.py`: pass the route plan ID into the service.
- `backend/app/services/mps_whatif_service.py`: constrain affected-line query to the requested plan and reject missing IDs.
- `backend/tests/test_m20_s01_t002_mps_preservation.py`: six deterministic preservation tests for isolation, capacity, campaign, what-if, and API/UI surface alignment.

## Commands and Results

Passed:

```text
python -m pytest backend/tests/test_m20_s01_t002_mps_preservation.py backend/tests/test_m20_s01_t001_mps_hardening.py -q
23 passed

python -m pytest backend/tests/test_m20_s01_t002_mps_preservation.py -q
6 passed

python -m py_compile <touched MPS Python files>
PYCOMPILE_OK

python -m alembic heads
20261019_0010 (head)

npm.cmd run type-check
tsc --noEmit completed without reported errors

git diff --check <touched implementation files>
clean
```

The broad T001 V02/V03 local invocation did not complete within the local
fixture/process time window. It is not reported as passed. The focused T001
hardening suite completed independently with `17 passed`; the accepted V06
PostgreSQL CI evidence remains the source of truth for the previously verified
release/sequence behavior.

The application import smoke command emitted existing FastAPI deprecation
warnings and did not finish within the local command window. It is not claimed
as a successful import check.

## CI and Publication

GitHub Actions and remote CI are suspended for the quota window from 2026-10-20
through 2026-10-30. No workflow dispatch was performed. Remote CI evidence for
this revision is therefore:

`DEFERRED_CI_QUOTA`

The implementation was pushed to `main` after a normal fetch/merge of the
remote prompt update. No force-push was used. The implementation commit is
`95176af0c1583d275c9d73e0135d34cfa4895c8a`.

## Protected Paths and Owner Work

`TASKS.md`, `TASKS_HISTORY.md`, and `CHATGPT_AUDIT_*` files were not modified by
the implementation commit or this log commit. Existing dirty owner work was
preserved and was not reset, stashed, cleaned, or broadly formatted. The
remote prompt update was merged normally so the published branch remains
current.

## Audit Handoff

`AWAITING_CHATGPT_AUDIT`

ChatGPT should independently review the implementation commit, this factual
log, the six T002 tests, and the deferred CI status before accepting T002.

