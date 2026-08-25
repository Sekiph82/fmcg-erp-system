---
hiveaiDashboardSchema: hiveai-project-dashboard/v1
projectKey: fmcg-erp-system
repository: Sekiph82/fmcg-erp-system
branchPolicy: main
dashboardMode: source-map
refreshPolicy: watcher-driven source invalidation; no generated status commits
---

# H!veAI Project Dashboard Manifest

This file is a pointer map for H!veAI. It is not a task ledger and must not duplicate task checkboxes.

## Project identity

Project: FMCG ERP System
Repository: `Sekiph82/fmcg-erp-system`
Default branch: `main`

## Source authorities

Canonical task source: `TASKS.md`
Handoff source: none verified
Roadmap/plan source: `PLANS.md`
Progress/history source: primarily historical sections inside `TASKS.md`
Architecture source: none verified at repository root
Decision source: none verified at repository root
Agent instruction sources: `AGENTS.md`, `CLAUDE.md`
Security source: none verified at repository root
Build/test metadata: `Makefile`, backend/frontend package manifests, Docker configuration, CI configuration

## Authority notes

`TASKS.md` is the task authority. `PLANS.md` is planning context and must not silently become a second canonical task ledger.

Because both files are large and can contain overlapping planning language, H!veAI should prefer explicit task identity/state from `TASKS.md` and use `PLANS.md` as supporting context.

Instruction files are never task authority.

## Refresh model

H!veAI should derive live state from Registry/Git/watcher evidence plus the canonical sources above. This manifest should remain pointer-only and should not be rewritten as a generated status snapshot.
