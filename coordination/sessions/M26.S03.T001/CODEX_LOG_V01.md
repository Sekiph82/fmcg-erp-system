# M26.S03.T001 — Detect performance anomalies

## Status

Implemented; pending consolidated M26 milestone verification and acceptance.

## Change summary

- Added a read-only authenticated endpoint and performance-page panel for deterministic machine downtime anomaly signals.
- A target downtime interval is flagged only when its duration exceeds that machine's prior-30-day median plus three median absolute deviations, with at least five valid, non-overlapping prior downtime events. The response returns the observed value, baseline values, exact source IDs, and unavailable/overlapping evidence.
- Open/invalid intervals, overlapping downtime records, and machines with insufficient history do not generate anomaly flags. No predictive, live-IoT, OEE, schedule, or causal claim is made.
- Added the calculation rule to the M26 execution plan so the threshold is explicit and reproducible.

## Focused evidence

- `python -m pytest tests/test_m26_s03_t001_performance_anomalies.py -q`: **1 passed**. Covers a flagged event with a zero-MAD baseline, insufficient history, overlapping records, and an open interval.
- `python -m compileall -q app/schemas/machine_operator.py app/services/machine_operator_service.py app/api/v1/endpoints/machine_operator.py`: passed.
- API route/service import check: passed.
- Focused ESLint on `src/app/dashboard/machine-ops/performance/page.tsx` and `src/lib/machineOperator.ts`: passed.
- `git diff --check`: passed (Git emitted existing line-ending normalization warnings for unrelated dirty files).

## Acceptance boundary

M26 milestone PostgreSQL/regression/frontend/E2E validation and consolidated independent code/security review remain pending. This task is not marked DONE.
