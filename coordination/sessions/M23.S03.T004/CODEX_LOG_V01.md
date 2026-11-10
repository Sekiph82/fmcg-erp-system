# M23.S03.T004 — Exception/escalation workflow

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S03.T004`.
- The M23.S03.T002 policy keeps authoritative Shop Floor reads and writes online-only. A request without a confirmed response must be reconciled against refreshed server state before another action is submitted.
- M23.S04 is the planned consolidated UI/E2E and milestone acceptance checkpoint.

## Implemented

- Added a shared Shop Floor connectivity notice that distinguishes browser-offline, reconnected-but-not-yet-refreshed, and normal online states.
- Prevented Shop Floor writes while the browser reports offline, while recovery refresh is pending, or while the affected live queue/downtime state is unavailable.
- Added explicit server-state refresh controls to the operator terminal and downtime board. After recovery, the operator is told to check whether the prior action was recorded before continuing.
- Classified mutation failures for operators: authentication and permission failures explain the next step, conflicts require refresh, and network/server failures are marked unconfirmed. These ambiguous failures keep writes blocked until refresh; unchanged retries continue to reuse the T003 request key.
- No offline write queue, local mutation persistence, or automatic replay was introduced.

## Verification and limits

- Targeted ESLint passed for the Shop Floor client, connectivity notice, operator terminal, and downtime board.
- `git diff --check` passed for the task files.
- No UI/E2E test or manual browser acceptance was run; these are included in the M23.S04 consolidated validation plan.
- No live facility, employee, device, or production environment was used.
- The checkout was synchronized with `origin/main` before this task; local and remote commits matched. The existing 240-path worktree remains broad and includes overlapping local work, so no commit or push was made.
