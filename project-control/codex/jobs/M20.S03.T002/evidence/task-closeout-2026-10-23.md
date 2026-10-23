# M20.S03.T002 Closeout

- Task: Harden campaign grouping/sequencing
- Status: COMPLETE
- Evidence date: 2026-10-23
- Acceptance: `coordination/milestones/M20/CODEX_M20_MASTER_PROMPT_V04.md`, M20.S03.T002
- Applicable strict audit: `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V05.md`

## Implemented

- Replaced inferred SKU-prefix grouping with exact product/work-center grouping, stable campaign identifiers, deterministic ordering, validated plan and line windows, and explicit invalid-input diagnostics.
- Preserved locked campaign assignments and locked line state. Unlocked campaigns are placed into per-work-center sequence slots around dated locked anchors. Missing, ambiguous, inconsistent, overlapping, or sequence-gap-exhausted lock data fails closed with diagnostics.
- Applied setup durations only from a unique active changeover matrix row. This includes an unlocked campaign immediately before a locked campaign while preserving the locked campaign itself. Negative or duplicate normalized rows are invalid; absent values remain `NOT_CONFIGURED`.
- Kept CIP duration and minimum-run quantity explicitly `NOT_CONFIGURED` because no authoritative source is configured. No owner data or process values were fabricated.
- Routed the compatibility grouping entry point through the validated implementation and made campaign listing deterministic when work centers have independent sequence numbers.

## Verification

- `python -m py_compile backend/app/services/mps_campaign_service.py backend/tests/test_m20_v03_acceptance.py`: passed.
- `backend/tests/test_mps_sequences.py backend/tests/test_m20_s01_t002_mps_preservation.py`: 19 passed.
- `backend/tests/test_m20_v03_acceptance.py`: 14 passed, 67 warnings. Ran after `alembic upgrade head` against a newly created loopback-only PostgreSQL 16 container/database with a unique task-owned name and `M20_DISPOSABLE_TEST_DATABASE=1`; the container and database were removed after the run. Test records used synthetic `M20-CAMP-*` identifiers. Coverage includes deterministic reruns, a campaign before a later lock with a configured 12-minute transition, missing/ambiguous lock anchors, and diagnostics tied to the all-locked invocation's run ID.
- `git diff --check`: passed.
- Independent read-only code review: no remaining concrete findings after fixes for locked sequence placement, incoming changeover accounting, missing/ambiguous locked anchors, all-locked diagnostics, and run-specific diagnostic assertions. Reviewer did not run tests or write files.
- GitHub Actions were not dispatched. No owner credentials or authoritative factory data were used.

The PostgreSQL acceptance run emitted 67 warnings; all reported tests passed.
