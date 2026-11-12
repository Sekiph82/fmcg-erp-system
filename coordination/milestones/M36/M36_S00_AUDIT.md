# M36.S00 — Native CRM source-to-screen audit

Audited at main `70d3fdf` (owner M36 plan) on 2026-11-12 by Claude (implementer; **not** an independent review —
see M36.S00.T005 for the separate reviewer). Classification follows TASKS.md M36 contract:
EXISTS_COMPLETE / PARTIAL / MISSING / BLOCKED / NOT_APPLICABLE.

## T001 — Inventory (what already exists; reuse, do not duplicate)

| Area | Models (`backend/app/models/`) | API (`/api/v1/...`, `endpoints/`) | UI (`frontend/src/app/dashboard/`) |
|---|---|---|---|
| Customer master + commercial scope | `sales.Customer` (company/branch/region/team/group scope, channel, distributor, route, GPS) | `/sales/customers` | `sales/customers` |
| Leads / opportunities pipeline | `crm.CRMRecord`, `CRMPipelineStage`, `CRMInterestLine`, `CRMActivity`, `CRMCompetitor`, `CRMWinLoss`, `CRMTerritory`, `CRMAIRecommendation` | `crm_pipeline.py` (40 routes: stages, leads, opportunities, qualify/convert/close-won/lost, activities, duplicates, dashboard, forecast, pipeline + win-loss reports, AI runs, territories, 360) | `crm/{leads,opportunities,pipeline,forecast,win-loss,activities,ai,territory,stages,qualify,overdue,records/[id]}` |
| CRM profiles, interactions, visits, segments, campaigns | `marketing.CRMProfile`, `CustomerInteraction`, `CustomerVisit`, `CustomerSegment`, `Campaign`, `TradeSpend`, `Survey`, attribution tables | `marketing.py` (93 routes) | `marketing/{crm,campaigns,segments,visits,analytics,...}` |
| Shopify buyers → native customers | `integrations.CrmCustomerMapping` (provider SHOPIFY) | `/integrations/ecommerce/*` | `integrations/sync` |
| Email | `email_integration.EmailAccount/EmailThread/EmailMessage/EmailTemplate` (threads linkable to any module object) | `email_integration.py` (accounts, threads, link, send, templates, `sync/{id}`) | surfaced in `communication` (no dedicated email route) |
| Chat / WhatsApp | `messaging.ChatChannel/ChannelMessage`; `whatsapp.WhatsAppConfig/Message/Template` | `messaging.py`, `whatsapp.py` (signed webhook) | `communication`, `whatsapp` |
| Calendar / meetings | `calendar.CalendarEvent/ResourceBooking/RecurrenceRule/...`; `meetings.MeetingRecord` | `calendar.py` (events, bookings, availability check/slots), `meetings.py` | `calendar/*` |
| Activity feed / chatter | `chatter.Activity/ActivityComment/Mention` | `chatter.py` (feed, timeline, SLA, AI follow-up assistant) | `chatter/*` |
| Support | `helpdesk.HelpdeskTicket/TicketComment`; `nps.*`; `consumer_complaints.ConsumerComplaint` | `helpdesk.py`, `nps.py` | `helpdesk/*` |
| Knowledge base | `knowledge_base.KBCategory/KBArticle/KBArticleRevision` (status, view_count) | `knowledge_base.py` (CRUD, revisions, search) | `knowledge-base/*` |
| Quotes / e-sign / approvals | `quotation.Quotation/QuotationLine`; `esign.SignatureRequest/SignatureRecord` (document + evidence SHA-256); `workflow.ApprovalRule/Request/Step` | `quotation.py` (send/accept/reject/revise/convert), `esign.py`, `approvals.py` | `sales/quotes`, `approvals` |
| Telephony | `voip.CallLog/CallScript` (recording_url, CRM record link) | `voip.py` (logs, scripts, stats) | `calls` |
| Distributor/customer portal | `portal.*` (accounts, users, orders, invoices, statement, claims, draft orders) | `portal.py` (35 routes, own auth) | `portal/*` |
| Rules / automation | `custom_fields.WorkflowTriggerRule` (entity, trigger_event, condition, action) | listed only — **no executor** | custom fields admin |
| Notifications | `notifications.*` (templates, preferences, schedules, delivery reports) | `notifications.py` (28 routes) | notification center |
| Integrations catalog | `integrations.ConnectorRegistry/PluginInstallation`, capability registry (`core/integration_capabilities.py`) | `/integrations/capabilities`, logs | `integrations/{marketplace,sync,logs}` |

RBAC: `crm.*` permissions incl. scoped `*_all` / `*_own_region` (`db/seed.py:319-486`); record list/detail/create/edit use
`can_view_record` / `ensure_commercial_action_allowed`.

## T002 — Runtime screens (synthetic non-admin CRM tester, local dev stack)

Script: logs in through the API as `m36-crm-tester` (synthetic, non-finance, non-admin, local dev DB only), opens each page,
records console errors and failing API calls. Evidence: `screenshots/S00/*.png`, `screenshots/S00/report.json`.

- Render OK, no console/API errors: CRM dashboard, leads, opportunities, pipeline, forecast, win-loss, activities, AI,
  territory, marketing CRM, customers, knowledge base, calendar, chatter, communication, integrations sync.
- **Defect D1:** `sales/quotes` showed "No quotes found" while every API call returned 404 — `lib/quotations.ts` used a
  relative `fetch`, so requests went to the Next.js origin. Same defect in `lib/helpdesk.ts`, `lib/pos.ts`,
  `lib/projects.ts` (missed by the earlier client conversion). Fixed in batch 1 (shared `apiFetch`).
- `marketing/campaigns` returns 403 for the tester (needs `marketing_campaigns`-level permission the synthetic role lacks) —
  correct enforcement, recorded so it is not mistaken for a defect.

## T003 — Capability matrix (25 tasks)

| Task | Class | Evidence / what exists | Bounded gap |
|---|---|---|---|
| S01.T001 Two-way email | PARTIAL + live BLOCKED | Email models + thread↔record links; `send` only stores a message (nothing is sent); `sync/{id}` **inserts fabricated demo threads** | Provider adapters (Gmail/Graph OAuth), real outbound, dedupe, unsubscribe; remove fake sync from non-demo use. Live = [!] credentials |
| S01.T002 Sales sequences | MISSING | — | Needs T004 engine + consent/suppression + outbound channel |
| S01.T003 Unified inbox | PARTIAL | Email threads, WhatsApp messages, helpdesk tickets, chat channels exist separately | Unified scoped inbox view, assignment, unread/SLA |
| S01.T004 Workflow automation | PARTIAL | `cf_workflow_rules` stored; approvals engine; notification schedules | Rule executor on CRM events (durable, idempotent, recursion limit) |
| S01.T005 Calendar/meetings | PARTIAL + live BLOCKED | Native events, bookings, availability check/slots, meetings | Google/Microsoft sync = [!] credentials; CRM meeting history link |
| S02.T001 Web lead forms | MISSING | — | Public form endpoint, rate limit, honeypot, consent, UTM, dedupe |
| S02.T002 Lead scoring | PARTIAL | Fixed formula `crm_pipeline_service.update_lead_score`; AI lead prioritisation. **Bug:** source bonus compares `str(enum)` to raw names, never matches | Configurable rules, history, explanation, fix bug |
| S02.T003 Weighted forecast | PARTIAL | `/crm/forecast` monthly expected/weighted | Owner/territory/stage/currency filters, snapshots |
| S02.T004 Funnel analytics | PARTIAL | `/reports/pipeline` (by stage), `/reports/win-loss` | Stage conversion, aging, rep drill-down |
| S02.T005 Email campaigns | PARTIAL | Trade-marketing campaigns, segments, ROI | Consent-aware email sends, suppression, bounce, metrics |
| S03.T001 Doc engagement | MISSING | — | Signed expiring share links, view events |
| S03.T002 Customer timeline | PARTIAL | CRM activities timeline, record 360, chatter timeline | One customer-wide ordered view (CRM, visits, calls, meetings, quotes, orders, invoices, tickets, email) |
| S03.T003 Mobile CRM | PARTIAL | Responsive shell; field-sales/van-sales modules | Mobile viewport audit + quick capture |
| S03.T004 Visual workflow designer | MISSING | — | After T004 engine |
| S03.T005 Live chat/chatbot | MISSING | — | Public widget, handoff, lead creation |
| S04.T001 AI copilot | PARTIAL | CRM AI recs (deterministic), chatter follow-up assistant | Scoped summary/draft with human approval; live model = [!] |
| S04.T002 Telephony | PARTIAL + live BLOCKED | Call logs, scripts, stats, recording URL | Consent/retention fields, click-to-call provider = [!] |
| S04.T003 Quote approval + e-sign | PARTIAL | Quote lifecycle, e-sign with hashes, approvals engine — not linked | Link quote→approval→e-sign→convert; external signer provider = [!] |
| S04.T004 Customer self-service | PARTIAL | Distributor portal (orders, invoices, claims) | Ticket history/replies in portal |
| S04.T005 Knowledge base | PARTIAL | Articles, categories, revisions, search, status | Public/private visibility, approval, feedback |
| S05.T001 Journey attribution | PARTIAL | CRMProfile first/last touch, CRMRecord source, influencer attribution | Source→lead→opportunity→order join report |
| S05.T002 Landing pages/A-B | MISSING | — | After S02.T001 forms |
| S05.T003 Integration console | PARTIAL | Capability registry, connector registry, sync page, logs | Mapping health, retries, credential status view |
| S05.T004 Conversation intelligence | MISSING | — | Needs transcripts (email/telephony) |
| S05.T005 ABM | MISSING | Segments, customers, CRM records | Target-account groups, buying committee |

No task is EXISTS_COMPLETE; nothing is marked [x] from this audit.

## T004 — Architecture and risk findings

1. **Security (fix first; corrected after independent review):** the `crm_pipeline.py` router requires a CRM view
   permission on every route (`router` dependency, line 29), but these routes stop there — no create/edit right and no
   record-scope check: stage create/patch/seed, interest-line add/delete, activity list/create/complete, competitor add,
   `update-score`, AI runs and recommendation acknowledgement, and `records/{id}/360`. So **view-only CRM users can
   mutate**, and **scoped (`*_own_region`) users can read out-of-scope records** (`/360`, activities) and company-wide
   aggregates (dashboard, forecast, reports, duplicates, territory performance). The service layer has no scope logic.
   The email endpoints use login only and are not owner-scoped: any user can list every mailbox, read any thread and
   "send" from any account.
2. **Fabricated data:** `POST /email/sync/{account_id}` creates fake supplier/customer threads; `POST /email/send` reports
   a sent message although nothing leaves the system. Must be gated/labelled (no fake success; M17 rule).
3. Tenant boundary = commercial scope (company/branch/region/team/group) on customers and CRM records; new CRM tables must
   carry the same scope or derive it from the linked customer/record.
4. Outbound communications: no consent/suppression store exists; required before any sequence/campaign send. No real
   provider credentials → outbound stays in a logged outbox (dry-run) until owner supplies provider + consent policy.
5. Background work: the API runs `webhook_dispatcher` and `mqtt_bridge` as lifespan tasks; an automation executor must be
   idempotent per (rule, event) and safe with several workers (DB uniqueness, not in-memory locks).
6. Migrations: append-only Alembic chain (head `20261112_0035`), idempotent guards required (baseline uses model metadata).

## Ordered batches (dependency graph)

1. Batch 1 — security + defects: CRM route RBAC/scope; D1 client fix; email fake-sync/send honesty.
2. Batch 2 — sales intelligence: S02.T002 scoring (rules, history, explain, bug), S02.T003 forecast filters + snapshots,
   S02.T004 funnel analytics.
3. Batch 3 — S03.T002 unified customer timeline; S02.T001 web lead capture.
4. Batch 4 — S01.T004 automation executor; then S01.T002 sequences, S02.T005 consent/suppression foundation.
5. Later — S04.T005 KB visibility/feedback, S04.T003 quote approval/e-sign link, S04.T004 portal tickets, S05.T003
   console, S05.T001 attribution, S01.T003 inbox; provider-bound items stay [!] for live acceptance.

## T005 — Independent review

- Reviewer: separate Claude sub-agent (`feature-dev:code-reviewer`), read-only, at main `70d3fdf` + uncommitted audit doc,
  2026-11-12.
- Verdict: **ACCEPT_WITH_CORRECTIONS.** Corrections applied above: (1) security finding overstated — router-level CRM
  view permission exists; reworded to view-only mutation + scope bypass; (2) `calls` page exists; (3) email surfaced in
  `communication`. Confirmed: scoring enum bug, fabricated email sync, logging-only send, all 8 MISSING rows (broad grep).
  Added risk: email endpoints login-only and not owner-scoped.
- Not verified in depth by the reviewer: 15 PARTIAL rows (no evidence their gaps already exist).
