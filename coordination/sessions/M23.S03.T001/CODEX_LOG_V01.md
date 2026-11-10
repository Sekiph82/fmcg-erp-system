# M23.S03.T001 — Validate responsive shop-floor UX

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S03.T001`.
- Milestone plan: `coordination/milestones/M23/EXECUTION_PLAN_V01.md`; M23.S03 covers responsive acceptance, the offline decision, safe retry/idempotency, and exception escalation. M23.S04 is the consolidated API/UI/E2E and independent review checkpoint.
- Existing responsive-work baseline: `coordination/sessions/M23.S01.T001/CODEX_LOG_V01.md`.
- Latest applicable quality boundary reviewed: `coordination/sessions/M27.S04.T004/CODEX_LOG_V01.md`. It distinguishes synthetic/local evidence from production and physical-device acceptance.

## Implemented

- Kept the work-order terminal's quantity, materials, QC, and finish forms mobile-first; repaired narrow-width wrapping for long work-order labels and authenticated QC user IDs.
- Made the downtime log table horizontally scrollable at narrow widths instead of compressing all seven columns into the viewport.
- Changed the downtime creation form to one column on narrow screens and two columns at `sm` widths; bounded its height and enabled vertical scrolling so it remains reachable on short viewports.
- Preserved existing touch-sized controls and the terminal's horizontally scrollable action tabs.

## Evidence and limits

- Targeted ESLint passed for `terminal/page.tsx` and `downtime/page.tsx`.
- `git diff --check` passed for those files.
- Source inspection confirmed responsive breakpoints, narrow-screen table scrolling, touch-sized controls, and wrapping for long identifiers.
- No browser/device visual run or test suite was performed. Physical tablet, real shop-floor, and production acceptance remain unverified and belong to the consolidated M23.S04 validation; this record does not claim them.
- The canonical checkout was fetched before work; `HEAD` and `origin/main` were equal (0/0 divergence). The worktree already contained broad owner/local modifications, so no commit or push was made in this task.
