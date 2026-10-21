# M20 STRICT REMEDIATION MASTER PROMPT V01 — CONTINUOUS ALL-SPRINT EXECUTION
Repository: https://github.com/Sekiph82/fmcg-erp-system
Branch: main ONLY.
Original master: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_MASTER_PROMPT_V04.md
STRICT criteria: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md
FAIL audit: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V01.md
Submitted builder log: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md
Canonical tracker READ ONLY: https://github.com/Sekiph82/fmcg-erp-system/blob/main/TASKS.md

EXECUTION: Read all links. Resolve ALL F01–F10 across ALL M20 tasks without stopping after each task or sprint. Implement and locally verify everything feasible, no superficial fixture-only PASS. Do not rewrite accepted T001/T002, preserve owner dirty changes and prior source. No new branch, no destructive git operation. Never edit TASKS.md, TASKS_HISTORY.md or ChatGPT audit files.
1. Build PostgreSQL test environment if possible without Docker using authorized existing tools; if genuinely unavailable, preserve BLOCKED_DB_PROOF, DO NOT fabricate tests or call it PASS. Do not spend time endlessly on environment. Provide reproducible DB test scripts and run all possible non-DB tests.
2. Resolve S02.T003 nested BOM/subassembly explosion where supported by current domain; protect cycles, depth, effective dates, UOM, substitutions, and negative cases. If architecture requires M21, document exact boundary and fail-closed M20 contract with tests; do not claim full implementation.
3. Implement configured-data scenario material/changeover/cost resimulation with transparent unknown states where inputs truly absent; test changes against baseline and candidate, including negative cases and no mutation of live MPS.
4. Test finite capacity/campaign/locks/changeover, permissions/tenant/warehouse boundaries, release rollback/concurrency/idempotency, diagnostics/snapshot persistence and schema migration with actual database where available.
5. Add backend service/API tests and frontend component/integration tests with existing harness; test errors, empty/loading, permissions and contracts. Re-run historical MPS tests on current SHA.
6. Run local py_compile, pytest, typecheck/build, Alembic heads and actual DB upgrade/downgrade if available. Never treat these as equivalent proofs.
7. Maintain a 20-task requirement-to-test-to-commit traceability table and F01–F10 closure table. Every evidence reference must use a FULL GitHub URL including 40-character commit SHA.
8. GitHub Actions and remote CI suspended through 2026-10-30 inclusive, resume only with owner authorization. No dispatch, reruns or accidental triggers; inspect push safety, use [skip ci] only when verified, otherwise retain local commits. Do not disable workflows/protections.
9. Continue through ALL feasible remediation, then publish ONE final factual consolidated remediation log with full GitHub URL, test outputs, remaining blocked gates, exact SHA and no self-acceptance. Return AWAITING_CHATGPT_MILESTONE_AUDIT only at end.
Acceptance authority: ChatGPT. Do not claim milestone PASS while any critical gate remains FAIL/BLOCKED_EVIDENCE.