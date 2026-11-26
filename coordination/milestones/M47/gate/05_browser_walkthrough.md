# M47 final gate — browser walkthrough (2026-11-26)

## Setup

- **Backend:** uvicorn on :8046, on a fresh disposable DB `m46_walk` cloned from the head template (migration 0077).
- **Frontend:** `next dev` on :3246.
- **Data and providers:** synthetic POVU data built through the real API (the same seed as M46), plus a non-finance persona `synth-m47`. `PROVIDER_EGRESS=local`, no provider keys, the owner's dev DB not used.
- **Not repeated here:** the M46 walkthrough (public site, members, video, shop SW/TR at 375 px, author→approver publish) was done on M46 code; its screens are unchanged except for the review fixes.

## Results

- **Staff login and dashboard in Swahili** (`?lang=sw`):
  - Login page fully Swahili.
  - Dashboard: "Dashibodi ya Uongozi", "Mauzo ya leo", "Ksh 0" sw-KE money (`01_staff_dashboard_sw.jpg`).
  - Bounded delta: the shared widget link "View details" is still English.
- **Report datasets** (`/dashboard/report-builder/datasets`): renders, with all 15 catalog sources offered for blending (all now query cleanly).
- **Helpdesk → Pipelines:**
  - The default pipeline was created lazily: New → In progress → Waiting on customer (SLA paused) → Escalated → Resolved → Closed.
  - Board loads.
- **CRM → Platform settings:** form shortening, Slack routes and the Slack link render.
- **Network:** every M47 API call made by these screens answered 200 (report-datasets, catalog, helpdesk pipelines and board, platform-depth Slack, lead forms). The 401s in the console come from other CRM tabs this persona is not allowed to use.

## Not clicked through (covered by DB/HTTP tests instead)

- Public `/v/<token>` and `/d/<token>` pages: they need minted tokens. Covered by:
  - test_m47_s01_t009 (video);
  - test_m47_s01_t003_audit_fixes (quote page i18n keys, via the missing-key report).
- WhatsApp STOP flow: covered by the signed-webhook test.
