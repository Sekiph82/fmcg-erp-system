# M20.S01.T001 — Codex Remediation V06

Repository `Sekiph82/fmcg-erp-system`, branch `main` ONLY. Read `CHATGPT_AUDIT_V05.md` and root `TASKS.md` (READ ONLY). Preserve owner dirty work. Do not edit tracker, history, auditor files or old .hiveai control-plane; no new branches, reset, clean or force push.

1. Inspect GitHub Actions runs `39285256727` and `39284832263`, especially backend job `118169258946` logs. GitHub PostgreSQL 16 **did run**, and pytest ended `640 passed, 8 failed, 1 skipped`. Extract and classify all eight failures by exact test ID, traceback and whether pre-existing.
2. Fix real PostgreSQL fixture setup: `MPSLine.mps_id` is NULL in concurrent release fixture because plan ID is referenced before flush. Correct Product→Recipe, Plan→Line and Warehouse FK ordering and session boundaries in BOTH rollback and concurrency tests. Do not turn exceptions into skips. Test must run on PostgreSQL in CI and assert actual persisted rollback, distinct parallel PO numbers, and monotonic deletion-gap behavior.
3. Verify `20261019_0010` sequence migration on fresh database and on seeded pre-existing PO-MPS numbers, and test collision/rollback/retry semantics. Keep minimal architecture-compatible fixes.
4. Diagnose frontend dependency audit failure (separate CI job). Fix only safely in-scope issues; otherwise document exact separate baseline issue, without claiming frontend PASS.
5. Execute clean-head focused and broad tests, migration heads/upgrade, compile/import, diff checks. Supply GitHub Actions run URL and job/test evidence with actual non-skipped PostgreSQL results. Do not claim acceptance from queued, failed or skipped tests. Do not weaken unrelated tests.
6. Commit implementation and factual log `coordination/sessions/M20-S01-T001/CODEX_LOG_V06.md` to `main`. Include exact SHA, test IDs/results, CI links, remaining failures and protected-file check. Finish `AWAITING_CHATGPT_AUDIT`; do not start T002.
