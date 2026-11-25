# HubSpot parity-plus capability matrix — M43.S00.T003

- **Date:** 2026-11-25. The ERP side was audited at main `5ecd56f`.
- **HubSpot sources (all fetched 2026-11-25, HTTP 200):**
  - Edition catalog: legal.hubspot.com/hubspot-product-and-services-catalog (+ /products)
  - Product pages: hubspot.com/products, /products/crm/ai-crm, /products/marketing, /products/sales, /products/service, /products/content, /products/data
  - /products/commerce (now served as Revenue Hub)
  - /products/artificial-intelligence (now served as Agent Hub / Breeze)
  - /products/aeo
- **Limits of the sources:**
  - Per-feature edition matrices could be read only for Smart CRM and part of Marketing Hub.
  - For the other hubs, the tier information comes from each hub's pricing block.
- **Method:** each capability is matched to actual ERP models, services, endpoints and screens, not to feature names. Evidence paths are relative to `backend/app` (`models/`, `services/`, `api/v1/endpoints/`) and `frontend/src/app/dashboard/`.
- **Classification:**
  - COMPLETE: implemented, with tests or evidence recorded in TASKS.md. Not yet re-accepted under the 2026-11-25 gate.
  - DEPTH_GAP: a native capability exists but is shallower than HubSpot.
  - MISSING: no implementation.
  - EXTERNAL_ACTIVATION: the software exists or is planned; only an account, approval or data is missing.
  - NOT_APPLICABLE: not relevant to this ERP.
- **No percentages are given.** "COMPLETE" means only that the code exists. Every row is re-verified at the milestone gates.

## 1. Smart CRM / platform

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Contacts, companies, deals, pipeline | `models/crm.py` (crm_records, crm_pipeline_stages, crm_stage_history), `services/crm_pipeline_service.py`, `dashboard/crm` | COMPLETE | M36 |
| Multiple pipelines (15–350 per edition) | Single stage set: `crm_pipeline_stages` has no pipeline key | DEPTH_GAP | **M43.S01.T011 (new)** |
| Custom objects and associations (Enterprise) | Custom fields only (`services/custom_fields_service.py`); no custom object definitions | MISSING | **M45.S01.T015 (new)** |
| Duplicate detection and merge | `services/master_duplicate_detection.py` (master data); no CRM contact/company merge | DEPTH_GAP | M45.S01.T010 |
| Data enrichment and smart properties | none | MISSING | M45.S01.T002/T003 |
| Data quality overview | `services/master_stewardship.py` (master data) | DEPTH_GAP | M45.S01.T011 |
| Audit log | `api/v1/endpoints/audit.py`, audit hooks | COMPLETE | — |
| 2FA and session security | `services/auth_2fa_policy.py`, `api/v1/endpoints/two_factor.py`, refresh tokens | COMPLETE | — |
| Single sign-on (SAML/OIDC) for staff | none (no SAML/OIDC code) | MISSING | **M45.S01.T016 (new)** |
| Teams and permission sets | roles/permissions (`api/v1/endpoints/roles.py`), CRM territories and commercial scope | COMPLETE | — |
| Sensitive-data properties | No field-level sensitivity classification | MISSING | **M45.S01.T017 (new)** |
| Multi-currency | KES/USD price lists, CBK rates (`services/cbk_rates.py`) | COMPLETE | — |
| Reporting dashboards and custom reports | `services/report_builder_service.py` (rb_reports, dashboards, schedules, RLS) | COMPLETE | — |
| Workflows | `services/crm_automation_service.py`, `services/crm_workflow_service.py` (visual designer) | COMPLETE | M36 |
| Two-way data sync and integration marketplace | `services/integration_console_service.py`, webhooks, GraphQL, Shopify | DEPTH_GAP | M45.S01.T011 |
| Sandbox test account | Local staging rehearsal only; no in-app sandbox copy | DEPTH_GAP | **M45.S01.T018 (new)** |
| Project management | `api/v1/endpoints/project.py`, `dashboard/projects` | COMPLETE | — |
| Breeze assistant / CRM copilot | `services/crm_copilot_service.py` | COMPLETE | M36 |
| Mobile CRM app | PWA (M37), field app (M38) | COMPLETE | — |
| Multi-account management, UI extensibility | Multi-company (`api/v1/endpoints/company.py`) | COMPLETE / NOT_APPLICABLE (no app ecosystem) | — |

## 2. Sales Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Sequences | `services/crm_sequence_service.py` | COMPLETE | M36 |
| Email tracking (opens and clicks) | Document views only (`crm_document_views`) | DEPTH_GAP | M43.S01.T006 |
| Email templates and scheduling | Outbox templates in `services/crm_outbound_service.py` | COMPLETE | — |
| Gmail/Outlook connection | IMAP/SMTP app password (`services/email_mailbox_service.py`) | DEPTH_GAP | M43.S01.T001/T002 |
| Gmail/Outlook sales extensions | none | MISSING | M45.S01.T012 |
| Meetings scheduler | `services/meeting_service.py`, ICS feeds | DEPTH_GAP (no public booking page, no two-way sync) | M43.S01.T003–T005 |
| Calling, power dialer, voicemail drop | `api/v1/endpoints/voip.py` (click-to-call, logging) | DEPTH_GAP | M43.S01.T008 (scope extended) |
| Call recording and transcription, Notetaker | `recording_url` field; `services/conversation_intel_service.py` (manual notes) | DEPTH_GAP | M43.S01.T009 |
| Conversation intelligence | `services/conversation_intel_service.py` | COMPLETE (text) | M36 |
| Forecasting | `services/forecast_service.py`, `crm_forecast_snapshots` | COMPLETE | M36 |
| Quotas/goals | none | MISSING | M43.S01.T007 |
| Playbooks, AI guided selling, deal plans | none | MISSING | M43.S01.T010 (scope includes deal plans) |
| Deal scoring and win probability | Lead scoring only (`crm_score_rules`) | MISSING | **M43.S01.T012 (new)** |
| Buying groups / stakeholder roles | `crm_account_contacts` (ABM) without buying roles | DEPTH_GAP | **M43.S01.T012 (new)** |
| Document tracking | `crm_document_links` and `crm_document_views` | COMPLETE | M36; library in M45.S01.T013 |
| Prospecting agent | none | MISSING | M45.S01.T001 |
| Business-card scanner | Receipt OCR exists (`api/v1/endpoints/receipt_ocr.py`); no card-to-contact flow | DEPTH_GAP | **M45.S01.T003 (scope extended)** |
| Sales analytics | Funnel analytics (M36.S02.T004), report builder | COMPLETE | — |

## 3. Marketing Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Email marketing and drag-and-drop builder | Campaigns (`crm_email_campaigns`, `services/crm_campaign_service.py`); no block editor | DEPTH_GAP | M44.S01.T001 |
| Forms and lead capture | `services/crm_lead_capture_service.py`, public lead forms | COMPLETE | M36 |
| Landing pages and A/B tests | `services/crm_landing_service.py` (variants, events) | COMPLETE | M36 |
| Lead scoring | `crm_score_rules` and `crm_score_history` | COMPLETE | M36 |
| Segments and lists | ABM account groups, campaign audiences | DEPTH_GAP | M44.S01.T010 |
| Ads management | none | MISSING | M44.S01.T002–T005 |
| Social media management | none | MISSING | M44.S01.T006–T008 |
| WhatsApp and SMS | `api/v1/endpoints/whatsapp.py`, `services/sms_sender.py` | COMPLETE (keys = activation) | M47.S02.T004 |
| Attribution and journey | `services/crm_attribution_service.py` | COMPLETE | M36 |
| Website behavioural analytics | Landing events only | DEPTH_GAP | M44.S01.T009 |
| Lookalike lists | none | MISSING | M44.S01.T010 |
| ABM | `services/crm_abm_service.py` | COMPLETE | M36 |
| Deliverability and complaints | Consent, unsubscribe and bounce in outbox | DEPTH_GAP | M44.S01.T011 |
| Transactional email | `services/email_sender.py`, invoice delivery | COMPLETE | — |
| Personalization | none | MISSING | M46.S01.T004 |
| Campaign, nurture and content agents | none | MISSING | M45.S01.T008/T009 (agent builder), M46.S01.T003 |

## 4. Service Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Ticketing and help desk | `models/helpdesk.py`, `api/v1/endpoints/helpdesk.py` (SLA hours) | COMPLETE | — |
| Shared/omnichannel inbox | `services/crm_inbox_service.py` | COMPLETE | M36 |
| Skill-based routing and conditional SLAs | Fixed SLA hours, manual assignment | DEPTH_GAP | **M45.S01.T019 (new)** |
| CSAT/CES surveys | NPS only (`models/nps.py`, `mkt_surveys`) | DEPTH_GAP | **M45.S01.T019 (new)** |
| Customer success workspace and health | none | MISSING | M45.S01.T006 |
| Knowledge base | `services/knowledge_base_service.py`, public KB | COMPLETE | M36 |
| Customer portal | Portal (M36/M38/M39) | COMPLETE | — |
| Customer agent (AI) | Public KB bot (`services/crm_chat_service.py`) | DEPTH_GAP | M45.S01.T007 |
| IVR phone trees and team routing | none | MISSING | M43.S01.T008 (scope extended) |
| Service analytics | Helpdesk reports, report builder | COMPLETE | — |

## 5. Content Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Landing pages | `services/crm_landing_service.py` | COMPLETE | M36 |
| Website builder and CMS | none | MISSING | M46.S01.T001 |
| Blog, AI blog writer and SEO | none | MISSING | M46.S01.T002/T003 |
| Brand voice | Brand assets endpoint (`api/v1/endpoints/brand_assets.py`) | DEPTH_GAP | M46.S01.T003 |
| Multi-language content | UI i18n only | DEPTH_GAP | M46.S01.T005 |
| Memberships (gated content) and video | none | MISSING | **M46.S01.T006 (new)** |
| Dynamic content (HubDB) | none | MISSING | M46.S01.T001/T004 |
| Custom domain and SSL | Deployment config | EXTERNAL_ACTIVATION | M47.S02.T001 |
| Content approvals | Generic approvals (`services/approval_service.py`) | DEPTH_GAP | M44.S01.T007 / M46.S01.T001 |

## 6. Data Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Data sync and field mappings | Shopify/bank/import engine (`services/import_engine.py`) | DEPTH_GAP | M45.S01.T011 |
| Data Studio datasets | Report builder datasets | DEPTH_GAP | M45.S01.T011 |
| Data warehouse / cloud storage connectors | none | MISSING | **M45.S01.T020 (new)** |
| Programmable automation (custom code) | Deliberately not provided (no arbitrary code execution) | NOT_APPLICABLE (safer typed transformations) | M45.S01.T011 |
| Data quality automation | Master stewardship | DEPTH_GAP | M45.S01.T011 |

## 7. Revenue Hub (formerly Commerce Hub)

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Quotes, CPQ and approvals | Quotations, `services/discount_approval_service.py` | DEPTH_GAP (no bundles or rules engine) | M45.S01.T014 |
| E-signature | Native typed-name signature with tamper evidence (M36/M41); `services/esignature_service.py` | DEPTH_GAP (no provider adapter) | M45.S01.T014 |
| Contracts | `services/contracts_service.py` | DEPTH_GAP | M45.S01.T014 |
| Invoices | Sales invoices plus eTIMS (`services/etims_connector.py`) | COMPLETE (plus native e-invoicing) | — |
| Subscriptions | `services/subscription_service.py` | COMPLETE | — |
| Payment links | M-Pesa STK only (`services/mpesa_daraja_service.py`); no shareable payment link | MISSING | **M45.S01.T021 (new)** |
| Revenue agent (overdue chase) | `services/dunning_service.py` | COMPLETE (rule-based) | — |
| Revenue reporting | Finance reports | COMPLETE | — |
| MCP connectors | none | MISSING | **M45.S01.T022 (new)** |

## 8. Breeze AI / Agent Hub

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| Agent builder | Workflow designer only; no AI agents | MISSING | M45.S01.T008 |
| Data agent (Q&A over CRM) | Copilot (`services/crm_copilot_service.py`) | DEPTH_GAP | M45.S01.T008 |
| Prospecting, customer, content, nurture and campaign agents | none | MISSING | M45.S01.T001/T007, M46.S01.T003 |
| Credits, governance and kill switch | M30 AI governance (risk tier, approvals) | DEPTH_GAP | M45.S01.T009 |

## 9. AEO

| HubSpot capability | ERP evidence | Class | Task |
|---|---|---|---|
| AEO readiness: structured data and FAQ schema | none | MISSING | M46.S01.T005 |
| Brand visibility across ChatGPT, Gemini and Perplexity; share of voice; citation and sentiment analysis | none | EXTERNAL_ACTIVATION — needs live answer-engine querying and an approved budget; locally the ERP shows NOT_AVAILABLE and accepts imported measurements | M46.S01.T005, M47.S02.T008 |

## Native FMCG/ERP advantages beyond HubSpot (evidence exists)

1. **Quote to production:** the quote becomes a sales order, which drives MRP and production (`services/mrp_service.py`, `services/production_service.py`). Production then flows to QC release, stock and ledger posting (M39.S03.T004).
2. **Delivery to cash:** distributor portal, van/moto sales and field app run with route POD, then M-Pesa collection, then invoice and eTIMS (M38/M39).
3. **Complaint to recall:** a complaint is traced through lot traceability to a recall (`services/traceability_service.py`, `services/recall_service.py`). This is linked to helpdesk, NPS and loyalty.
4. **Health score from finance:** the customer health score can include credit, overdue invoices and order frequency from the native ledger (M45.S01.T006).
5. **Kenya compliance:** KES/CBK rates, Kenyan payroll and eTIMS are built in.

## New tasks added to TASKS.md from this audit

These eleven rows are beyond the original 40 recommendations. All are new IDs; the scope extensions to M43.S01.T008, M43.S01.T010 and M45.S01.T003 are listed after them.

| New ID | Task |
|---|---|
| M43.S01.T011 | Multiple deal pipelines |
| M43.S01.T012 | Deal scoring and buying groups |
| M45.S01.T015 | Custom objects and associations |
| M45.S01.T016 | Staff SSO (OIDC/SAML) |
| M45.S01.T017 | Sensitive-data field classification |
| M45.S01.T018 | Configuration sandbox |
| M45.S01.T019 | Skill routing, conditional SLAs and CSAT/CES |
| M45.S01.T020 | Data warehouse export connectors |
| M45.S01.T021 | Payment links |
| M45.S01.T022 | MCP server for ERP/CRM tools |
| M46.S01.T006 | Memberships, gated content and video assets |

Scope extensions to existing tasks:
- M43.S01.T008: power dialer, voicemail drop and IVR.
- M43.S01.T010: deal plans.
- M45.S01.T003: business-card scanning.
