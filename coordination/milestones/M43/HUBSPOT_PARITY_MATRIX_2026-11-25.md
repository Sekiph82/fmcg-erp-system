# HubSpot parity-plus capability matrix — M43.S00.T003 (v2, final for the M43.S00 baseline)

## Scope and method

- **Date:** 2026-11-25. The ERP side was audited at main `99a8a13`, plus the uncommitted M43.S00.T004 harness.
- **HubSpot side:** the full official edition catalog, legal.hubspot.com/hubspot-product-and-services-catalog/products, read completely in the built-in browser: 17 sections, about 600 feature rows (see `HUBSPOT_CATALOG_FEATURES_2026-11-25.md`). This was cross-checked against the 2026-11-25 product pages: /products, crm/ai-crm, marketing, sales, service, content, data, commerce (Revenue Hub), artificial-intelligence (Agent Hub) and aeo.
- **Verification:**
  - v1 was checked row by row against models, services, endpoints and pages by a separate read-only explorer agent.
  - It found 13 wrong classes, 9 wrong evidence citations and 11 gaps missing from v1.
  - All of these are corrected here. A "v1 →" note marks every changed row.
- **Paths:** `backend/app/...` is shortened to `models/`, `services/`, `endpoints/`. Line numbers are as verified on 2026-11-25.
- **Classes:**
  - COMPLETE: implemented, with evidence in TASKS.md. Not yet re-accepted under the 2026-11-25 gate.
  - DEPTH_GAP: a native capability exists but is shallower than HubSpot.
  - MISSING: not implemented.
  - EXTERNAL_ACTIVATION: the software exists or is planned; only an account, approval or dataset is missing.
  - NOT_APPLICABLE: deliberately not built, with the reason given.
- **No percentage scores.** M47.S01.T001 re-audits this matrix against the running application.

## 1. Smart CRM / platform

| HubSpot capability (catalog row) | ERP evidence | Class | Task |
|---|---|---|---|
| Contacts, companies, deals, pipeline | `models/crm.py` crm_records (contact fields inline :176-178), crm_account_contacts (:737-750), stage history; `dashboard/crm` | DEPTH_GAP (v1 → COMPLETE): no standalone contact object, no M:N associations, no lifecycle stage | **M43.S01.T015** |
| Pipelines (15–350) | One global stage set: `CRMPipelineStage` has no pipeline key (`models/crm.py:151-164`) | DEPTH_GAP | M43.S01.T011 |
| Custom properties, required fields, calculated properties | `models/custom_fields.py` (12 fixed entity types; REFERENCE and COMPUTED field types); no required-per-stage rule | DEPTH_GAP | **M43.S01.T016** |
| Object tags, presets, saved/team views, board/calendar index views | none | MISSING | **M43.S01.T016** |
| Teams, organize teams | Roles and permissions (`models/role.py:27-55`), `sales_team` access scope (`core/access_control.py:64,86`); `sales_team_id` is free text (`models/crm.py:188`) | DEPTH_GAP (v1 → COMPLETE) | **M43.S01.T016** |
| Permission sets | Custom roles and permission codes (`endpoints/roles.py`) | COMPLETE | — |
| Field-level permissions, Sensitive Data | `cf_definitions.sensitive_flag` exists (`models/custom_fields.py:115`) but is not enforced; AI prompt PII redaction (`core/ai_safety.py:111-122`) | DEPTH_GAP (v1 → MISSING) | M45.S01.T017 |
| Custom objects, data model builder, association labels | none (fixed EntityType list) | MISSING | M45.S01.T015 (after M43.S01.T015 associations) |
| Duplicate management | Exact-key checks only (`services/master_duplicate_detection.py:1-6`); `merge_master` exists for company, material, product, recipe, supplier and warehouse, not for customers or CRM records | DEPTH_GAP | M45.S01.T010 |
| Data enrichment (6 rows), smart properties, form shortening | none | MISSING | M45.S01.T002/T003 |
| Intent signals (12 rows) | none (landing and document views only) | MISSING | M45.S01.T004 |
| Data quality overview, AI formatting recommendations | `services/master_stewardship.py` is a change audit, not data quality | MISSING (v1 → DEPTH_GAP) | M45.S01.T011 |
| Multiple currencies | CBK rates, FX revaluation (`models/finance.py:629-658`), KES/USD price lists | COMPLETE | — |
| Product library | Products and price lists | COMPLETE | — |
| Record timeline | `services/customer_timeline_service.py`, `endpoints/crm_pipeline.py:663` | COMPLETE (v1 omitted it) | — |
| Reporting dashboards, custom reporting | `models/report_builder.py:91-279` (definitions, dashboards, schedules, RLS) | COMPLETE | — |
| Revenue analytics suite, custom revenue reporting | Finance reports and report builder | COMPLETE | — |
| Shared inbox | `services/crm_inbox_service.py:75-148` (e-mail, WhatsApp, tickets, chat) | COMPLETE | — |
| Tasks and activities, repeating tasks, task queues | `crm_activities`; no repeat rules, no queues | DEPTH_GAP | **M43.S01.T013** |
| Projects, Gantt chart | `endpoints/project.py`, `dashboard/projects`, kanban boards | COMPLETE (Gantt to be verified at M47.S01.T001) | — |
| Single sign-on, social logins | Password + 2FA only (`endpoints/auth.py:63`) | MISSING | M45.S01.T016 |
| Log in as another user, admin notification management | Notification centre with preferences exists; no audited impersonation | MISSING / DEPTH_GAP | **M45.S01.T023** |
| Standard sandbox account | API apps can be tagged development/sandbox (`models/api_portal.py:78-90`); no data/config sandbox | DEPTH_GAP | M45.S01.T018 |
| Custom events | Landing events only | DEPTH_GAP | M44.S01.T009 |
| Audit log, 2FA | `models/audit_log.py`, 2FA routes | COMPLETE | — |
| Multi-account management | Multi-company with `user_company_access` (`models/company.py:70`) | COMPLETE (native equivalent) | — |
| CRM import | Bulk import per module (`endpoints/bulk_import.py`) | COMPLETE | — |
| Slack integration | none | MISSING | **M44.S01.T013** |
| Salesforce integration and custom object sync | Optional external CRM connector | NOT_APPLICABLE (native CRM is the system of record, owner 2026-11-11); optional connector stays M17.S02.T006 [D] | — |
| Breeze Assistant / data agent | `services/crm_copilot_service.py` (rules + redaction) | DEPTH_GAP | M45.S01.T008 |
| Mobile app | PWA (M37), field app (M38) | COMPLETE | — |
| Developer platform (app objects, UI extensibility) | API portal: keys, OAuth client apps, usage, GraphQL, webhooks (`endpoints/api_portal.py:294-1116`) | COMPLETE (v1 omitted it); no third-party UI extension marketplace (NOT_APPLICABLE) | — |

## 2. Sales Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| 1-to-1 email, Gmail/Outlook connection | IMAP/SMTP app password (`services/email_mailbox_service.py`); OAuth boundary (M43.S00.T004) | DEPTH_GAP | M43.S01.T001/T002 |
| Email templates, scheduling | `email_templates` (`models/email_integration.py:102`); campaign `scheduled_at` (`models/crm.py:573`) | COMPLETE (v1 evidence corrected) | — |
| Canned snippets, multiple signatures, sales e-mail frequency controls, smart send times | none | MISSING | **M43.S01.T013** |
| Email tracking and notifications | No open/click tracking; quote link views only (`models/crm.py:617-642`) | DEPTH_GAP | M43.S01.T006 |
| 1-to-1 video messaging | none | MISSING | **M43.S01.T013** (uses M46.S01.T006 video assets) |
| Calling, phone numbers | tel: click-to-call (`endpoints/voip.py:189-201`), call logs, call scripts (`models/voip.py:55-65`) | DEPTH_GAP | M43.S01.T008; number = M47.S02.T003 |
| Call recording and transcription, AI transcript enrichment, coaching playlists | Recording URL with consent and retention; pasted transcript on `call_logs.transcript` (`endpoints/voip.py:121-133,209-214`) | DEPTH_GAP (v1 evidence corrected) | M43.S01.T009 |
| Conversation intelligence | `services/conversation_intel_service.py:107-123` (rules, optional AI) | COMPLETE (text) | — |
| Interactive voice response | none | MISSING | M43.S01.T008 |
| Conversation routing, automatic lead rotation, lead form routing | Automation rules exist (`services/crm_automation_service.py`); no round-robin or rotation | DEPTH_GAP | **M43.S01.T014** |
| Sales automation, workflow extensions | CRM automation and visual workflows (`models/crm.py:819-859`) | COMPLETE | — |
| Sequences | `services/crm_sequence_service.py` | COMPLETE | — |
| ABM tools, target accounts, account overview | `services/crm_abm_service.py` | COMPLETE | — |
| Lead scoring | `crm_score_rules` (`services/crm_intelligence_service.py:34-44`) | COMPLETE | — |
| Predictive deal score | Stage probability + override (`models/crm.py:158,198-199`), health and risk flag (`services/crm_pipeline_service.py:900-912`); no factor/trend score | DEPTH_GAP (v1 → MISSING) | M43.S01.T012 |
| Buying groups | `committee_role` DECISION_MAKER/BUYER/INFLUENCER/CHAMPION/USER/BLOCKER (`services/crm_abm_service.py:19-20`, `models/crm.py:749`); not linked to deals | DEPTH_GAP (v1 evidence corrected) | M43.S01.T012 |
| Deal progression, deal plans, guided actions, playbooks | Call scripts, AI pipeline-risk and lead-priority recommendations (`models/crm.py:114-117,304-318`) | DEPTH_GAP (v1 → MISSING) | M43.S01.T010 |
| Deal summaries, meeting prep/recap, notetaker | none | MISSING | M43.S01.T009 (recap), **M43.S01.T013** (deal summaries) |
| Deal approvals, deal splits, handoffs | Discount approvals (M41); commissions (`models/commissions.py`); no deal-stage approvals, split credit or handoff briefing | DEPTH_GAP | **M43.S01.T014** |
| Goals | `commission_targets` (`models/commissions.py:126-138`), field `daily_targets` (`models/field_sales.py:92-110`) | DEPTH_GAP (v1 → MISSING) | M43.S01.T007 |
| Forecasting | Deal forecast `crm_pipeline_service.get_forecast` (:490), `crm_intelligence_service.forecast_detail` (:218) with snapshots. (`forecast_service.py` is demand forecasting.) | COMPLETE (v1 evidence corrected); quota/hierarchy depth in M43.S01.T007 | — |
| Meeting scheduling | `services/meeting_service.py`, ICS feed; no public booking page | DEPTH_GAP | M43.S01.T003–T005 |
| Task calendar sync | none | MISSING | M43.S01.T003/T004 |
| Documents, sales content analytics | `crm_document_links/views` | COMPLETE / DEPTH_GAP | M45.S01.T013 |
| Sales analytics, rep productivity, deal journeys | Funnel (`services/crm_intelligence_service.py:288`), report builder; no rep-activity productivity or deal-journey report | DEPTH_GAP | **M43.S01.T013** (rep productivity), M44.S01.T009 (journeys) |
| Sales extensions (Gmail/Outlook) | none | MISSING | M45.S01.T012 |
| Prospecting agent | none | MISSING | M45.S01.T001 |
| LinkedIn Sales Navigator | Partner-only API | EXTERNAL_ACTIVATION | M47.S02.T004 |
| Business-card scanner (mobile app) | Receipt OCR exists; `business_card_service.py` is outgoing e-cards | DEPTH_GAP | M45.S01.T003 (scope extended) |

## 3. Marketing Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| Email marketing, templates, drag-and-drop builder, mobile optimization | Campaigns with plain-text body (`models/crm.py:563-582`) | DEPTH_GAP | M44.S01.T001 |
| Email A/B testing, smart content, advanced personalization, send-time optimization, approvals, frequency cap, single-send API | Outbox rate limits only | MISSING | **M44.S01.T012** |
| Email health reporting, deliverability | Consent, bounce and unsubscribe in outbox (`services/crm_outbound_service.py:31,67`) | DEPTH_GAP | M44.S01.T011 |
| Forms, form automation | Lead forms and capture rules | COMPLETE | — |
| CTAs | Landing variants only | DEPTH_GAP | M46.S01.T001 |
| CRM segments | `mkt_customer_segments` with criteria_json (`models/marketing.py:285-299`) targeted by campaigns | DEPTH_GAP (v1 evidence corrected) | M44.S01.T010 |
| Web visitor segments, AI segment suggestions, lookalike segments | none | MISSING | M44.S01.T009/T010 |
| Ad management, retargeting, conversion events, ad goals | Manual ad performance log + ROI optimizer (`endpoints/marketing.py:1177-1214,1837-1904`); no ads API | DEPTH_GAP (v1 → MISSING) | M44.S01.T002–T005, T010 |
| Social media, approvals, Instagram DM | Manual social log + influencer management (`models/marketing.py:435-517`); no publishing | DEPTH_GAP (v1 → MISSING) | M44.S01.T006–T008, **T013** (DMs) |
| Facebook Messenger | none | MISSING | **M44.S01.T013** |
| WhatsApp integration | `endpoints/whatsapp.py` | COMPLETE (account = activation) | M47.S02.T004 |
| Live chat, bots, logged-in visitor identification | `services/crm_chat_service.py:88-135` (KB bot + handoff); portal users not identified in chat | COMPLETE / DEPTH_GAP | M44.S01.T009 (scope extended) |
| Website traffic analytics, filtered views, custom events, event visualizer | Landing events only | DEPTH_GAP | M44.S01.T009 |
| Contact-create / multi-touch attribution, customer journey analytics | `services/crm_attribution_service.py` | COMPLETE / DEPTH_GAP (journeys) | M44.S01.T009 |
| Cookie management tools | none | MISSING | M44.S01.T009 (scope extended) |
| SEO recommendations, SEO analytics, Search Console | none | MISSING | M46.S01.T002 |
| ABM, campaign reporting, collaboration tools | ABM, campaigns, chatter (`services/chatter_service.py`) | COMPLETE | — |
| Omni-channel automation | Workflows and sequences (e-mail, WhatsApp, SMS) | COMPLETE | — |
| Video hosting and editing | none | MISSING | M46.S01.T006 |
| Campaign, nurture and content agents; marketing studio | none | MISSING | M45.S01.T008, M46.S01.T003 |
| AEO | none | MISSING / EXTERNAL_ACTIVATION | M46.S01.T005 |

## 4. Service Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| Ticketing, help desk, pipelines | `models/helpdesk.py`, `endpoints/helpdesk.py` | COMPLETE | — |
| SLAs | Fixed hours per priority + breach (`models/helpdesk.py:45-50,72`) | COMPLETE | — |
| Conditional SLAs, skills-based routing, conversation routing, capacity limits, agent presence | Manual assignment only (`endpoints/helpdesk.py:253-268`) | MISSING | M45.S01.T019 |
| Macros, reply recommendations, help desk spaces, custom views, QA score, CX score, handoff summaries, coaching | none | MISSING | M45.S01.T019 (scope extended) |
| Customer feedback surveys | Ticket CSAT 1–5 in portal (`endpoints/portal_self.py:609-626`); NPS with one-time links; no CES; no post-chat survey | DEPTH_GAP (v1 claimed "NPS only", corrected) | M45.S01.T019 |
| Knowledge base, KB SSO/access groups | Public KB; no access groups | COMPLETE / DEPTH_GAP | M46.S01.T006 (gated content) |
| Customer portal | `endpoints/portal_self.py` | COMPLETE | — |
| Customer success workspace, health scores, product usage tracking | Placeholder `churn_risk_score` only (`models/marketing.py:322-324`) | MISSING | M45.S01.T005/T006 |
| Customer agent, KB agent | KB bot | DEPTH_GAP | M45.S01.T007/T008 |
| IVR, calling | see Sales | — | M43.S01.T008 |
| Service analytics, insights | Helpdesk reports, report builder | COMPLETE | — |
| WhatsApp, Messenger, custom channels API | WhatsApp yes; others no | DEPTH_GAP | **M44.S01.T013** |

## 5. Content Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| Landing pages, A/B testing | `services/crm_landing_service.py` | COMPLETE | — |
| Adaptive testing | none | MISSING | M46.S01.T004 (scope extended) |
| Website pages, site tree, content staging, multisites, content embed, URL mappings, HubDB, dynamic pages | none | MISSING | M46.S01.T001 (scope extended) |
| Blog, SEO | none | MISSING | M46.S01.T002 |
| Member blog, memberships, password-protected pages, limit access to content | Portal auth realm exists | MISSING | M46.S01.T006 |
| Multi-language content, AI translation | **No UI or content i18n.** Only notification templates have `language` (`models/notifications.py:109`) | MISSING (v1 → DEPTH_GAP "UI i18n" was wrong) | M46.S01.T005 (content), **M46.S01.T007** (portal/shop/staff UI) |
| AI content, AI image, content remix, brand identity | Brand assets only | DEPTH_GAP | M46.S01.T003 |
| Podcasts, post narration, video | none | MISSING | M46.S01.T006 (scope extended) |
| Content approvals, activity logging | Approval engine (`services/approval_service.py`), audit log | COMPLETE (engine) / DEPTH_GAP (content workflow) | M46.S01.T001 |
| Premium hosting, custom domain, SSL | Deployment | EXTERNAL_ACTIVATION | M47.S02.T001 |
| Serverless functions, custom-coded modules, code alerts | — | NOT_APPLICABLE: no tenant code execution, by security design. Typed configurable modules instead. | — |
| Content sync | none | MISSING (low value; covered by the config bundles of M45.S01.T018) | M45.S01.T018 |

## 6. Data Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| Data sync, custom field mappings | Shopify/bank connectors, import engine; integration console health, retry and manual sync (`services/integration_console_service.py`); most catalog connectors are "coming_soon" (`endpoints/integrations.py:820-860`) | DEPTH_GAP | M45.S01.T011 |
| Data quality overview, health trends, quality automation, formatting recommendations | none | MISSING (v1 → DEPTH_GAP) | M45.S01.T011 (scope extended) |
| Duplicate / bulk duplicate management | Exact-key only | DEPTH_GAP | M45.S01.T010 |
| Data warehouse integrations | none | MISSING | M45.S01.T020 |
| Data studio | Report builder datasets | DEPTH_GAP | M45.S01.T011 |
| Workflows, webhooks, scheduled and webhook triggers | Workflows; outgoing and inbound webhooks (`models/webhook.py`); no scheduled or webhook-triggered CRM workflows | DEPTH_GAP | M45.S01.T011 (scope extended) |
| Programmable automation | — | NOT_APPLICABLE (no arbitrary code); typed transformations in M45.S01.T011 | — |
| Custom objects | none | MISSING | M45.S01.T015 |

## 7. Revenue Hub

| Capability | ERP evidence | Class | Task |
|---|---|---|---|
| Quotes, quote tracking, approvals | Quotations, share links and views, discount approvals (M36/M41) | COMPLETE / DEPTH_GAP (multi-step approval) | M45.S01.T014 |
| Quote templates, password protection, single-page editor, AI quotes, quote rules, price books, tiered pricing, quote reporting | Price lists; promotions with BUNDLE/MIX_AND_MATCH/TIERED (`models/promotions.py:24-34`) apply to orders, not quotes | DEPTH_GAP (v1 "no bundles" corrected) | M45.S01.T014 (scope extended) |
| E-signature, signable attachments | Native typed-name signature + e-mail OTP (`models/crm.py:649-678`) | DEPTH_GAP (provider adapter) | M45.S01.T014 |
| Tax rates, automated sales tax, e-invoices | VAT and eTIMS (`services/etims_connector.py`, `services/tax_service.py`) | COMPLETE (Kenya native) | — |
| Invoices, credit memos, invoice reminders, AI invoice prioritization | Invoices; dunning (`services/dunning_service.py`); credit notes to be verified at M47.S01.T001 | COMPLETE / DEPTH_GAP (prioritization) | M45.S01.T014 (scope extended) |
| Contracts, contract imports | `services/contracts_service.py` | DEPTH_GAP | M45.S01.T014 |
| Orders | Native sales orders (full O2C) | COMPLETE (exceeds) | — |
| Subscriptions, subscription retries, billing portal, stored payment methods | Recurring order templates (`services/subscription_service.py:332`); no recurring charge | DEPTH_GAP (v1 → COMPLETE) | M45.S01.T014 + T021 (scope extended) |
| Payment links, B2B checkout, payments | M-Pesa STK (`services/mpesa_daraja_service.py`), portal ordering; no payment link | DEPTH_GAP / MISSING | M45.S01.T021 |
| Revenue agent, closing agent | Rule-based dunning; no agent | DEPTH_GAP | M45.S01.T008 (templates) |
| QuickBooks / Xero | — | NOT_APPLICABLE (native general ledger); exports via M45.S01.T020 | — |
| Capital financing, Affirm/Klarna | — | NOT_APPLICABLE (US/EU provider products; no Kenya equivalent requested) | — |
| MCP connectors | none | MISSING | M45.S01.T022 |

## 8. Agent Hub (Breeze)

| Capability | Class | Task |
|---|---|---|
| Agent builder, custom agents, work agents | MISSING | M45.S01.T008/T009 |
| Data, prospecting, customer, KB, content, campaign, nurture, revenue, closing and customer-health agents | MISSING (copilot and KB bot are DEPTH_GAP) | M45.S01.T001/T007/T008 (template gallery covers revenue, closing, customer-health and KB agents), M46.S01.T003 |
| Credits and governance | DEPTH_GAP (M30 risk tiers and approvals) | M45.S01.T009 |

## 9. AEO

| Capability | Class | Task |
|---|---|---|
| AEO readiness (structured data, FAQ schema, recommendations) | MISSING: no JSON-LD in the frontend | M46.S01.T005 |
| Brand visibility, prompt tracking, competitor, citation and sentiment analysis across answer engines | EXTERNAL_ACTIVATION: live querying of ChatGPT/Gemini/Perplexity needs approved provider access and budget. Locally shown as NOT_AVAILABLE, with an import interface. | M46.S01.T005, M47.S02.T008 |

## ERP capabilities beyond HubSpot (verified; not in v1)

1. **Native operations:**
   - Quote becomes a sales order, which drives MRP, production, QC release, stock and ledger (M39.S03.T004).
   - Native order-to-cash, field sales, secondary sales, and van and moto sales with M-Pesa and eTIMS.
2. **Customer and trade marketing:**
   - Loyalty programme: tiers and points earned on paid invoices (`services/customer_feedback_service.py`).
   - Promotions auto-apply, dynamic pricing.
   - Market intelligence: competitor observations and market share.
   - Competitors and win/loss records.
3. **Service and compliance:**
   - Consumer complaints linked to lot traceability and recall.
   - Public NPS with one-time links.
   - Commissions with targets.
4. **Collaboration and internal tools:**
   - Chatter with @mentions.
   - Kanban boards.
   - Ctrl+K search.
   - Notification centre with web push.
   - Team messaging.
   - Generic approval engine.
   - Document management.
5. **Developer platform:**
   - API portal, GraphQL, outgoing webhooks with versioned event definitions.
6. **Kenya-specific and HR:**
   - Employee digital business cards (vCard/QR).
   - Kenya payroll.
   - CBK FX revaluation.

## Gap → task summary (adds to the original 40 recommendations)

| Task | Status | Scope |
|---|---|---|
| M43.S01.T011 | v1 | Multiple pipelines |
| M43.S01.T012 | v1, revised | Factor/trend deal score; deal-level buying groups on the existing committee roles |
| **M43.S01.T013** | new | Sales workspace and productivity: task queues, repeating tasks, snippets, signatures, frequency caps, send-time rules, 1-to-1 video links, deal summaries, rep productivity |
| **M43.S01.T014** | new | Lead rotation and routing, deal-stage approvals, deal splits, handoff briefings |
| **M43.S01.T015** | new | Standalone contacts, M:N associations with labels, lifecycle stage |
| **M43.S01.T016** | new | Team entity and hierarchy, object tags, required/calculated properties, saved views and presets, board/calendar views |
| **M44.S01.T012** | new | Email governance and smart content |
| **M44.S01.T013** | new | Messenger, Instagram DM, Slack, custom channels API |
| M45.S01.T015–T022 | v1 | — |
| **M45.S01.T023** | new | Audited impersonation, admin notification management |
| M46.S01.T006 | v1 | — |
| **M46.S01.T007** | new | Customer-facing and staff UI internationalization: EN/SW/TR |

Scope extensions:
- M43.S01.T008/T010
- M44.S01.T009 (cookie manager, logged-in visitor identification, journeys)
- M45.S01.T003, T008 (agent templates), T011 (data quality, triggers), T014 (quote rules, promotions on quotes, recurring billing), T019 (routing, macros, QA, CES, post-chat)
- M46.S01.T001 (site tree, staging, multisite, dynamic tables/pages), T004 (adaptive testing), T006 (podcasts, member blog)

Gaps that are NOT_APPLICABLE or EXTERNAL_ACTIVATION are recorded above with reasons. None of them hides a software gap.
