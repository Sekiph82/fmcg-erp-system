# M49 gate — manual browser walkthrough (real local app, 2026-11-26)

## Setup
- **Code:** candidate cf26b58 plus the walkthrough fixes listed below.
- **Database:** disposable DB `m49_walk` (clone of `m49_tmpl`, head 0079) in container `m49-gate-pg`. The DB was dropped afterwards.
- **Backend:** uvicorn :8049, started by scratchpad `m49_walk.py`. It restarts per phase (ads / social) because the simulators share provider URL settings. `PROVIDER_EGRESS=local`.
- **Frontend:** `next dev` :3249 with `NEXT_DIST_DIR=.next-m49walk`; deleted afterwards.
- **Simulators:** :8765, mounted as `/ads`, `/social` (incl. M49 formats), `/aud` and `/voice` (Twilio + transcription).
- **Personas** (synthetic, `m49_walk_seed.py`):
  - walk-mkt: marketing edit, plus campaigns view/create/edit (granted during the walk);
  - walk-fin1: finance approve, 2FA;
  - walk-crm: CRM supervisor;
  - walk-appr and walk-outsider.
- **Method:** every step was clicked in the browser pane. Only the signed Twilio webhook was posted by a script, because the caller is the carrier.

## Steps

| # | Persona | Action | Observed | Screenshot |
|---|---|---|---|---|
| 1 | walk-mkt | Marketing Studio, create campaign POVU-ALC-DEC | Before the persona had campaigns.create, the button showed "Needs campaigns.create" (disabled reason). Afterwards the campaign was created; the checklist showed brief, creative, audience, channels, budget and approval. | 01_studio_campaign_created.jpg |
| 2 | walk-mkt | Fill the brief, Save brief | "Brief saved." Version 1 · by walk-mkt | — |
| 3 | walk-mkt | Budget 80000 (cap 50000), Request finance approval | Pending request "waiting for finance". The requester's own Approve is disabled. | 02_studio_budget_over_cap_pending.jpg |
| 4 | walk-fin1 (2FA) | Opened Studio | Access denied: the Studio page needs marketing.view. Finance must decide from My Approvals. | — |
| 5 | walk-fin1 | My Approvals | **DEFECT A:** studio budget requests were not listed. Fixed: `studio_budget` entry in `approval_inbox_service.ENTRIES` plus the My Approvals action. After the fix, the request was listed. | — |
| 6 | walk-fin1 | Approve | **DEFECT B:** "Required permission is missing." The Studio router needed marketing read permissions. Fixed: the router allows `ms.READ + ms.FINANCE`; the decide rules are unchanged. | 03_defect_finance_403_before_fix.jpg |
| 7 | walk-fin1 | Approve (after fix) | "approved"; the inbox is empty | 04_finance_approved_in_my_approvals.jpg |
| 8 | walk-mkt, mobile 375 px | Studio | Budget 80000.00 applied; History (1); layout fits 375 px | 05_studio_mobile_budget_applied.jpg |
| 9 | walk-mkt | Ads lifecycle page and Audience sync page | Both render with honest state: "No ad accounts yet"; AUDIENCE_EXPORT_ENABLED off is explained; capability table includes UNVERIFIED notes | — |
| 10 | walk-crm | Meetings → + Recurring meeting: Europe/London, Mon 10:00 from 2027-03-15, 4 occurrences | Created 4. Shown in Nairobi time: 13:00, 13:00, then 12:00, 12:00 after the 28 Mar BST change, so 10:00 London local is kept. Honest notes: no calendar connected, mailbox needed for invitations. | 06_recurring_series_dst_london.jpg |
| 11 | walk-crm | Calls tab: contact center panel | Twilio capability matrix (8 SUPPORTED, with reasons), presence, queues, callbacks, transfer and outcome, coaching | — |
| 12 | (carrier) | Signed POST /api/v1/calls/cc/twilio/webhook (inbound) | 200 TwiML "Nobody can take your call right now…"; bad signature → 403. Before the gate fix, the live app returned **401** (DEFECT C, below). | — |
| 13 | walk-crm | Calls tab after the inbound call | Missed-call callback +254700000111 listed. **DEFECT D:** the call counted as ANSWERED (answer rate 100%). Fixed in `contact_center_service`: an unanswered inbound call is NO_ANSWER and keeps it after Twilio's final "completed". A regression test was added. | — |
| 14 | walk-crm | Social → Channels: add facebook POVU Kenya; Calendar: multi-photo post (2 https images + alt text), campaign tag POVU-ALC-DEC; Save draft; Request approval | draft v1, then pending, SIMULATED | — |
| 15 | walk-crm | Approve own post | Refused: "A second editor must approve." | 07_social_self_approval_refused.jpg |
| 16 | walk-mkt | Approve, then Submit now | Simulator `attached_media` album; published as confirmed by the (simulated) network. **DEFECT E:** the label said "Live" for a SIMULATED post. Fixed: "Simulated (local simulator only, not on the real network)". | 08_social_fb_album_simulated_published.jpg |
| 17 | walk-mkt | Studio, channels | Social shows "submitted (local)"; the post was picked up via campaign tag, PUBLISHED; analytics say "No data", nothing estimated | 09_studio_social_linked_by_tag.jpg |

## Defects found and fixed during the gate
- **A.** Studio budget requests were missing from My Approvals.
- **B.** Finance approvers got 403 on the Studio decide route.
- **C.** The public Twilio webhook returned 401 in the real app.
  - Cause: a nested `include_router` hid the route from the PUBLIC_ROUTES split, and the unit test used a mini app, so it did not catch this.
  - Found by `test_route_auth_coverage` and confirmed live.
  - Fix: `voice_cc` and `transcripts` are registered as their own modules at `/calls/cc` and `/calls/transcripts`.
- **D.** Missed inbound calls were counted as ANSWERED.
- **E.** A SIMULATED published social post was labelled "Live".

## Not clicked here (covered elsewhere)
These are covered by the DB tests on simulators (test_m49_s01_t001…t012). The exhaustive per-persona browser acceptance is M52:
- **Shared mailbox UI:** walk-crm had no email permission.
- **Transcript review.**
- **Audience-sync end to end:** needs a consented segment and an ad account.
- **Ad edits after creation:** the M48 walkthrough covered the ads lifecycle; T006 adds edits.
- **LinkedIn, YouTube and X formats; listening replies.**

## Cosmetic, noted
- The Studio section numbers did not follow the on-screen order (Budget, numbered 5, appeared before Channels, numbered 4). Renumbered: Budget is 4, Channels is 5.
