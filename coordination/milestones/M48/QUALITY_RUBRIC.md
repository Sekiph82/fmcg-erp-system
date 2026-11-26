# M48 quality rubric — local software readiness (definition only)

Prepared 2026-11-26 for M48.S00.T002. The source is the quality-rubric paragraph in TASKS.md (section "M48–M52", "Binding scope and gate rules").

This file defines how scores are calculated. **It contains no scores.** Scores are produced only at a consolidated milestone gate, from recorded evidence, and an independent reviewer checks them.

Inventory basis, counted on source `6ac96f1`:
- 219 backend endpoint modules in `backend/app/api/v1/endpoints/`;
- 113 top-level dashboard directories in `frontend/src/app/dashboard/`;
- 602 second-level page directories.

Every module and directory is assigned to exactly one category in §4. A module that appears in no category is a rubric defect and must be fixed before scoring.

## 1. Categories and thresholds

| # | Category | Threshold |
|---|---|---|
| 1 | Core CRM | ≥ 9.0 |
| 2 | Sales / communication | ≥ 9.0 |
| 3 | Sales automation | ≥ 9.0 |
| 4 | **Advertising** | **≥ 9.5** |
| 5 | **Audience management** | **≥ 9.5** |
| 6 | **Social automation** | **≥ 9.5** |
| 7 | Marketing / e-mail / analytics | ≥ 9.0 |
| 8 | Service | ≥ 9.0 |
| 9 | Data / integration | ≥ 9.0 |
| 10 | AI | ≥ 9.0 |
| 11 | CPQ / finance | ≥ 9.0 |
| 12 | CMS / SEO / AEO | ≥ 9.0 |
| 13 | Manufacturing / MES | ≥ 9.0 |
| 14 | Stock / warehouse | ≥ 9.0 |
| 15 | Quality | ≥ 9.0 |
| 16 | Procurement | ≥ 9.0 |
| 17 | Logistics / field / distribution | ≥ 9.0 |
| 18 | HR / payroll | ≥ 9.0 |
| 19 | Localization / mobile | ≥ 9.0 |
| 20 | Security / reliability / performance | ≥ 9.0 |

Each category is scored and judged on its own. Averaging across categories is not allowed and has no meaning under this rubric.

## 2. Dimensions and weights

| Dimension | Weight | What it measures |
|---|---|---|
| W — Supported workflow completeness | 40 % | Every inventory action in the category works end to end in the local app, within what the public API and the domain support. |
| U — Real UI usability / accessibility | 20 % | A real browser click-through of the action on desktop (1440 px) and phone (390 px). |
| C — Correctness / security / permissions | 20 % | Results are right, permissions and company isolation hold, and the input/consent rules apply. |
| R — Reliability / recovery | 10 % | Idempotency, retries, async status, and a defined failure path. |
| E — Test / docs / evidence | 10 % | An automated test exists and passed at the gate, the evidence path exists, and the docs match the code. |

## 3. Scoring formula

Each criterion *i* in a category is assigned to one dimension *d(i)*. It gets a result r_i:
- PASS = 1;
- PARTIAL = 0.5, allowed only where the criterion defines what partial means;
- FAIL = 0;
- N/A = excluded.

```
achieved_d = Σ r_i            over eligible criteria i in dimension d
eligible_d = count of eligible criteria in dimension d
score      = 10 × Σ_d ( w_d × achieved_d / eligible_d ) / Σ_d w_d     (w = 40, 20, 20, 10, 10; a dimension with eligible_d = 0 is dropped from both sums)
```

Rounding: one decimal place, rounded down. A category passes only if its score is ≥ its threshold **and** every hard gate in §5 holds.

### Eligibility rules

- **Activation-only criteria are not eligible.** These need a real account, key, domain, device or factory, and live in `[D]` rows. Example: a live Meta Ads spend.
- **Proprietary or unavailable API operations are N/A** only when all three hold:
  1. an official doc URL is recorded in `CAPABILITY_MATRIX.md`;
  2. the UI shows a safe disabled state with the exact reason, plus a manual or alternative path;
  3. an independent reviewer signs off.

  Example: text-only Instagram posts.
- **Simulated provider criteria are eligible.** The real adapter must build the exact documented request and call the local simulator in `backend/tests/provider_sim/`.
  - A path that returns `NOT_CONFIGURED`, or never builds a request, is a **FAIL**, not N/A.
- **No evidence means FAIL.** Every result cites a gate artefact: a test log line, a screenshot path, a click-log entry, or file:line.

## 4. Per-category criterion inventories

Every category includes the following **generic criteria**, in addition to its specific list. Each generic criterion is counted once per inventory action.

| Generic ID | Dim | PASS when | FAIL when |
|---|---|---|---|
| G-W1 | W | The action completes on the running local app with synthetic POVU data, and the DB row or state change is verified. | Any step needs an API-only call, a seed hack or a manual SQL fix. |
| G-U1 | U | The action can be done by clicking on desktop and phone. The page has no sideways scroll, no console errors, and no failed XHR other than an intended 4xx. | A control is missing, off-screen or dead, or the page crashes. |
| G-U2 | U | Loading, empty and error states render, and labels are translated (EN/SW/TR). | Raw keys show, error text is untranslated, or the page is blank on error. |
| G-U3 | U | Controls are keyboard reachable, form inputs have labels, and contrast is AA on the action's primary controls (axe or manual check). | Any of these is violated on the primary controls. |
| G-C1 | C | A role without the right gets 403 from the API and the UI hides the control; the allowed role succeeds. | The UI hides the control but the API allows the action, or the reverse. |
| G-C2 | C | Cross-company and cross-scope access is refused (tested). | A record from another company or scope is readable or writable. |
| G-C3 | C | Calculated values reconcile with the source rows (totals, currency never summed across currencies, tax). | A number is wrong or mixes currencies. |
| G-R1 | R | A replay or double submit has no duplicate effect (idempotency key, unique index or row lock). | A duplicate effect occurs. |
| G-R2 | R | A provider or dependency failure leaves a recoverable state with a visible reason and a retry. | A silent failure, a stuck state or a fake success occurs. |
| G-E1 | E | An automated test covering the action passed in the gate log. | The test is missing, skipped without a recorded reason, or failed. |
| G-E2 | E | The docs and user guide describe the current behaviour, and the evidence path exists. | The docs are stale or the evidence is missing. |

Each specific criterion below adds to the W, C or R dimension as tagged. The modules listed are the inventory scope: every endpoint module and dashboard page named must be exercised by at least one criterion.

### 4.1 Core CRM
**Scope:**
- Backend: `crm_contacts`, `crm_pipeline`, `crm_workspace`, `custom_fields`, `custom_objects`, `dedupe`, `crm_teams`, `lookup`, `chatter`, `crm_addin`, `products`, `master_lifecycle`.
- Pages: `crm/{contacts,customers,leads,opportunities,pipeline,stages,records,objects,views,duplicates,workspace,activities,territory}`, `custom-fields`, `chatter`.

| ID | Dim | Criterion (PASS/FAIL) |
|---|---|---|
| CRM-1 | W | Lead → qualify → opportunity → won → customer chain, with stage history recorded. |
| CRM-2 | W | Custom fields and custom objects can be created, edited and filtered, and appear in list views. |
| CRM-3 | W | Duplicate detection and merge keep every activity, association and audit row. |
| CRM-4 | C | Own / team / all record scope is enforced on list, detail and export. |
| CRM-5 | R | Merge and bulk edit are atomic (all or nothing). |

### 4.2 Sales / communication
**Scope:**
- Backend: `email_integration`, `meetings`, `meetings_public`, `booking_pages`, `booking_public`, `calendar`, `voip`, `messaging`, `whatsapp`, `crm_channels`, `sales_docs`, `sales_docs_public`.
- Pages: `crm/{inbox,messages,messaging-channels,sales-docs,outbox}`, `email`, `meetings`, `calendar`, `calls`, `communication`, `messages`, `whatsapp`; backend also `messaging_public`.

| ID | Dim | Criterion |
|---|---|---|
| COM-1 | W | Two-way mail sync works through the IMAP/SMTP, Gmail and Graph adapters against the simulator: send, receive, thread, and incremental history. |
| COM-2 | W | Meetings: create, time-zone/DST handling, no double booking, ICS feed, booking page, and two-way calendar sync with the Google and Graph simulators. |
| COM-3 | W | Calls: click-to-call, consent before recording, retention expiry. |
| COM-4 | C | Mailbox and call visibility is own-only unless the user holds `view_all`. |
| COM-5 | R | A webhook or push channel renews before expiry; a missed notification is recovered by a delta or history sync. |

### 4.3 Sales automation
**Scope:**
- Backend: `crm_workflows`, `crm_workflow_hooks_public`, `crm_routing`, `crm_playbooks`, `sales_quotas`, `sales`, `sales_depth`, `sales_depth_public`, `deal_plans_public`, `approvals`.
- Pages: `crm` (hub), `sales`, `crm/{sequences,automation,workflows,routing,playbooks,quotas,forecast,funnel,scoring,win-loss,qualify,overdue}`, `my-approvals`.

| ID | Dim | Criterion |
|---|---|---|
| SA-1 | W | A sequence stops on reply, unsubscribe, bounce or a closed record (all four tested). |
| SA-2 | W | Workflow designer: validate, simulate, publish, roll back. Each event runs exactly once. |
| SA-3 | W | Routing: round-robin, weighted, fixed; an unavailable owner is skipped. |
| SA-4 | C | Stage approval cannot be self-approved (enforced by a DB CHECK and the API). |
| SA-5 | R | Workflow runs are claimed with SKIP LOCKED; a crash mid-run resumes without a duplicate action. |

### 4.4 Advertising — threshold 9.5
**Scope:**
- Backend: `ads`, `marketing` (spend parts).
- Pages: `crm/ads`, `marketing/{ads,ai-optimizer,brand-spend}`.
- Providers: Meta Marketing API, Google Ads API, LinkedIn Marketing API, TikTok API for Business (see CAPABILITY_MATRIX).

| ID | Dim | Criterion |
|---|---|---|
| AD-1 | W | For each of the 4 providers: create campaign → ad set/ad group → ad/creative as DRAFT/PAUSED. The adapter builds the documented request; the simulator records it. |
| AD-2 | W | Edit budget and schedule, pause and resume. A versioned budget history is kept. The read-back shows the provider's state, not the local intent. |
| AD-3 | W | Every creative format that the matrix marks as API-supported can be created, per provider. An unsupported format shows a disabled control with the documented reason and an alternative. |
| AD-4 | W | Reporting/insights pull for each provider, reconciled to the stored daily rows (currency kept as returned). |
| AD-5 | C | Live mutation is off by default. Activation needs an explicit switch, a spend cap and an approver who is not the creator. A request beyond the cap is refused before any provider call. |
| AD-6 | C | Tokens are stored encrypted, never logged and never returned to the UI. Scopes are least-privilege as listed in the matrix. |
| AD-7 | R | Async jobs (video upload, review status, offline batch) are polled to their final state. A provider rejection maps to a visible reason. Idempotent retry creates no duplicate campaign. |
| AD-8 | R | Rate limits: a 429 or throttle response leads to back-off and a retry time shown in the UI. |
| AD-9 | E | Contract tests run per provider against the simulator, including partial failure (Google), review rejection (Meta/TikTok) and version-header use (LinkedIn). |

### 4.5 Audience management — threshold 9.5
**Scope:**
- Backend: `audiences`, `customer_data`, `customer_intel`, `sensitive_data`.
- Pages: `crm/{audiences,data-hub,sensitive,success,insights}`, `marketing/segments`.

| ID | Dim | Criterion |
|---|---|---|
| AU-1 | W | A segment is built from CRM/ERP data with a member preview and a count. |
| AU-2 | W | Customer-list sync to Meta, Google (through the Data Manager API path where Customer Match is closed), LinkedIn (DMP segments) and TikTok, against the simulator. Members are normalised and SHA-256 hashed client-side. |
| AU-3 | W | Incremental add and remove. A consent withdrawal removes the member from every synced audience in the next run. |
| AU-4 | C | Only consented contacts are sent. Raw PII never leaves the system, and a hashed field is never logged in clear text. |
| AU-5 | C | The provider's minimum audience size is respected, with a clear message below it. |
| AU-6 | R | Upload sessions are resumable or retryable. The match/processing status is polled and shown. |
| AU-7 | E | The hash normalisation test vectors match each provider's documented examples. |

### 4.6 Social automation — threshold 9.5
**Scope:**
- Backend: `social`, `social_webhook_public`, `social_tiktok_webhook_public`, `content_studio`, `marketing_assets`, `marketing_assets_public`.
- Pages: `crm/social`, `marketing/{social-media,content-studio,influencers,members-media}`.
- Providers: Facebook Pages, Instagram, LinkedIn, TikTok, YouTube, X.

| ID | Dim | Criterion |
|---|---|---|
| SO-1 | W | Every format cell marked Yes or Partial in CAPABILITY_MATRIX can be composed, approved, scheduled and published through the simulator, for each platform: text, link, image, multi-image/carousel, video, reels/shorts, stories. |
| SO-2 | W | Each unsupported cell shows a disabled control with the official reason and a manual alternative (download or share). |
| SO-3 | W | Metrics and comments are read back where the API supports it; a reply works where it is allowed. |
| SO-4 | C | A post is never marked PUBLISHED until the provider confirms the final state. For TikTok this is a `publish_id` that reaches PUBLISH_COMPLETE; for Instagram, a container FINISHED and then published. |
| SO-5 | C | An approval is required before publishing, and the approver is not the author. A restricted user cannot publish. |
| SO-6 | R | Upload is resumable or chunked where documented; a failed or expired container leads to a retry with a clear status. Each provider's publishing quota is read and enforced. |
| SO-7 | R | Webhook signatures (Meta `X-Hub-Signature-256`, TikTok signature) are verified; a replay is ignored. |
| SO-8 | E | The state-machine test per provider covers success, pending, fail, retry and delete. |

### 4.7 Marketing / e-mail / analytics
**Scope:**
- Backend: `marketing`, `email_designs`, `deliverability`, `mail_events_public`, `crm_unsubscribe_public`, `crm_engagement`, `crm_tracking_public`, `web_analytics`, `web_analytics_public`, `analytics`, `report_builder`, `report_datasets`, `surveys`, `nps`, `nps_public`, `loyalty`, `promotions`, `tpm`, `crm_abm`, `crm_landing`, `crm_landing_public`, `crm_lead_forms_public`.
- Pages: `crm/{email-campaigns,email-designer,engagement,web-analytics,attribution,abm,landing,lead-forms}`, `marketing/{campaigns,analytics,promotions,trade-spend,surveys,visits,ecommerce}`, `analytics`, `reports`, `report-builder`, `surveys`, `nps`, `loyalty`, `promotions`, `tpm`.

| ID | Dim | Criterion |
|---|---|---|
| MK-1 | W | A campaign goes from send through the consent check and the Mailpit simulator to open, click and bounce events, and the metrics are shown. |
| MK-2 | W | One-click List-Unsubscribe works and is honoured on every channel. |
| MK-3 | W | Attribution (first-touch, last-touch, linear) reconciles with the source rows. |
| MK-4 | C | An unsubscribed, bounced or complained contact is never mailed; this is checked at queue time and again at send time. |
| MK-5 | R | Send is idempotent per message key. |

### 4.8 Service
**Scope:**
- Backend: `helpdesk`, `service_desk`, `service_desk_public`, `knowledge_base`, `kb_public`, `chat_public`, `conversation_intel`, `consumer_complaints`, `returns_mgmt`.
- Pages: `helpdesk`, `knowledge-base`, `crm/chats`.

| ID | Dim | Criterion |
|---|---|---|
| SV-1 | W | Ticket → assignment → SLA → resolution → CSAT/NPS; portal reply re-opens the ticket. |
| SV-2 | W | KB editorial flow: draft → review → publish, with public search. |
| SV-3 | W | Website chat → bot answer from published articles → hand-off to a person. |
| SV-4 | C | Internal notes are never shown in the portal; attachments are malware-scanned before they are shared. |
| SV-5 | R | An SLA timer survives a restart; escalation fires once. |

### 4.9 Data / integration
**Scope:**
- Backend: `data_sync`, `data_sync_public`, `integrations`, `oauth_connections`, `webhooks`, `bulk_import`, `warehouse_exports`, `graphql_api`, `api_portal`, `mcp_server`, `config_bundles`, `access_tokens`, `bank_api`, `iot`, `documents`, `documents_public`, `project`.
- Pages: `integrations`, `webhooks`, `developer`, `import-history`, `crm/{data-sync}`, `bank-api`, `iot`, `documents`, `projects`, `products`.

| ID | Dim | Criterion |
|---|---|---|
| DI-1 | W | Snowflake writer through SQL API v2: statement submit, async polling of the handle, partitioned result. A MERGE upsert is verified against the simulator. |
| DI-2 | W | BigQuery writer: load job, or Storage Write with job polling, plus an incremental watermark. Verified against the simulator. |
| DI-3 | W | Parquet export (pyarrow) with schema evolution; CSV, LOCAL_DIR, S3 and Postgres writers keep passing. |
| DI-4 | W | Search Console pull (searchanalytics.query, paging past 25 000 rows). |
| DI-5 | C | Credentials encrypted; each OAuth token is limited to its scope; outbound webhooks are HMAC-signed. |
| DI-6 | R | Sync resumes from the last watermark after a failure, with no duplicate rows (MERGE keys). |

### 4.10 AI
**Scope:**
- Backend: `ai`, `ai_agents`, `production_ai`, `market_intelligence`, `receipt_ocr`.
- Pages: `ai`, `crm/{ai,ai-access}`, `market-intelligence`.

| ID | Dim | Criterion |
|---|---|---|
| AI-1 | W | Every AI feature works with `AI_PROVIDER=mock` (deterministic fallback) and through the real adapter path against an HTTP simulator for Anthropic, OpenAI and Gemini. |
| AI-2 | W | Prospect research cites evidence with recency and confidence, lists unknowns, and uses the canonical POVU product context (no beverage placeholders). |
| AI-3 | C | PII is masked before external calls (settings `AI_SEND_*`); an AI action needs the user's click and an approval for outreach. |
| AI-4 | C | Uncited claims are dropped; structured output is validated against a schema. |
| AI-5 | R | Provider timeouts and 429 responses fall back with a visible notice; per-user rate limits apply. |
| AI-6 | W | OCR (tesseract) and transcription (faster-whisper) run locally on fixtures. |

### 4.11 CPQ / finance
**Scope:**
- Backend: `cpq`, `quotation`, `price_list`, `pricing`, `dynamic_pricing`, `finance`, `bank_reconciliation`, `dunning`, `collections`, `commissions`, `fixed_assets`, `dimensions`, `tax_regulatory`, `invoice_match`, `landed_cost`, `payment_links`, `payment_links_public`, `card_payments_public`, `esign`, `contracts`, `subscription`, `expenses`, `receipt`.
- Pages: `finance`, `bank-reconciliation`, `dunning`, `commissions`, `fixed-assets`, `dimensions`, `tax`, `invoice-match`, `landed-cost`, `price-lists`, `dynamic-pricing`, `esign`, `contracts`, `expenses`, `recurring-orders`.

| ID | Dim | Criterion |
|---|---|---|
| FI-1 | W | Quote with discount approval → signature through the native path or the DocuSign/Acrobat Sign simulator. The envelope or agreement status is polled and the webhook is verified. |
| FI-2 | W | Card and hosted checkout through the Pesapal, Flutterwave and M-Pesa simulators: success, pending, decline, late callback and refund, each reconciled exactly once to the invoice. |
| FI-3 | W | Order → invoice → receipt → GL posting balanced; KES and USD kept separate. |
| FI-4 | C | Approver ≠ creator; the credit limit is enforced; the payment amount and currency must match the invoice. |
| FI-5 | R | Callback replay is idempotent, and the status query resolves a missing callback. |

### 4.12 CMS / SEO / AEO
**Scope:**
- Backend: `cms`, `cms_public`, `cms_poster_public`, `brand_assets`, `business_cards`, `business_cards_public`, `search`.
- Pages: `marketing/website`, `brand-assets`.

| ID | Dim | Criterion |
|---|---|---|
| CMS-1 | W | Page/blog draft → review → publish, with sitemap, canonical, meta and structured data (schema.org) output. |
| CMS-2 | W | An AEO/FAQ block renders valid JSON-LD; Search Console data is shown per page. |
| CMS-3 | C | Public pages expose no unpublished or personal data; noindex is applied where required. |
| CMS-4 | R | Media upload is size- and type-checked and malware-scanned. |

### 4.13 Manufacturing / MES
**Scope:**
- Backend: `production`, `production_advanced`, `production_execution`, `production_costing`, `shop_floor`, `machine_operator`, `machine_utility`, `bom`, `recipes`, `mps`, `mrp`, `planning`, `copacking`, `subcontracting`, `npd_workflow`, `maintenance`, `kanban`, `material_flow`, `materials`, and the utilities group (`compressor`, `electricity`, `steam`, `water`, `soft_water`, `solar`, `wastewater`, `chemical_treatment`, `utilities*`, `utility_*`).
- Pages: `production`, `production-execution`, `shop-floor`, `machine-ops`, `bom`, `recipes`, `mps`, `mrp`, `planning`, `copacking`, `subcontracting`, `npd`, `maintenance`, `kanban`, `material-flow`, `materials`, `utilities`, `utility-management`.

| ID | Dim | Criterion |
|---|---|---|
| MF-1 | W | Plan → work order → dispense with scan → consume → QC release → FG stock → WIP/FG journal. |
| MF-2 | W | MRP shortfall → PR/PO suggestion. |
| MF-3 | C | Operator line scope; a wrong lot, an expired lot or a non-recipe material is refused. |
| MF-4 | R | Scan-consume is idempotent per key; the prepared lot is consumed atomically. |

### 4.14 Stock / warehouse
**Scope:**
- Backend: `inventory`, `warehouses`, `wms`, `cycle_count`, `serial_tracking`, `shelf_life`, `gs1`, `containers`, `traceability`.
- Pages: `inventory`, `warehouses`, `wms`, `warehouse-floor`, `putaway`, `movements`, `cycle-count`, `shelf-life`, `gs1`, `containers`, `traceability`.

| ID | Dim | Criterion |
|---|---|---|
| WH-1 | W | GRN → putaway → pick (FEFO) → dispatch, all by scan; cycle count with variance approval. |
| WH-2 | W | Lot/serial traceability forward and back; recall. |
| WH-3 | C | Stock never goes negative unless configured; valuation reconciles (FIFO, weighted average or standard cost). |
| WH-4 | R | A concurrent pick or putaway on the same task is locked; there is no over-pick. |

### 4.15 Quality
**Scope:**
- Backend: `quality`, `quality_enterprise`, `qms`, `allergen`, `regulatory_certs`, `training`, `esg`.
- Pages: `quality`, `qms`, `allergen`, `compliance`, `training`, `esg`.

| ID | Dim | Criterion |
|---|---|---|
| QA-1 | W | Inspection → hold/release → NCR/CAPA; complaint → recall chain. |
| QA-2 | C | The release approver holds the quality approve right; a self-release is refused. |
| QA-3 | R | A quarantined lot can never be issued. |

### 4.16 Procurement
**Scope:**
- Backend: `procurement`, `procurement_suggestion`, `suppliers`, `supplier_portal`, `supplier_self`.
- Pages: `procurement`, `procurement-suggestion`, `suppliers`, `supplier-portal`.

| ID | Dim | Criterion |
|---|---|---|
| PR-1 | W | PR → approval → PO → supplier portal acknowledge or ETA → GRN → 3-way match → payment. |
| PR-2 | C | A supplier sees only its own released POs; uploads are scanned. |
| PR-3 | R | PO acknowledge is idempotent. |

### 4.17 Logistics / field / distribution
**Scope:**
- Backend: `logistics`, `delivery`, `fleet`, `field_app`, `field_sales`, `moto_sales`, `van_sales`, `distributors`, `secondary_sales`, `portal`, `portal_self`, `pos`.
- Pages: `logistics`, `fleet`, `field`, `van-sales`, `secondary-sales`, `portal`, `pos`.

| ID | Dim | Criterion |
|---|---|---|
| LG-1 | W | Rep day: route → GPS check-in → order → collection. Driver: trip → POD (signature, photo, GPS) → invoice at delivery. |
| LG-2 | W | Shop or distributor portal order → ETA tracking → payment (M-Pesa simulator). |
| LG-3 | C | A field user sees only their own route, customers and collections; collection confirmation is by someone else with `finance.approve`. |
| LG-4 | R | Delivering the same stop twice is impossible; an offline note is kept per user and never sent as another user. |

### 4.18 HR / payroll
**Scope:**
- Backend: `hr`, `payroll_ke`, `ess`, `ess_self`, `timesheets`, `recruitment`, `appraisals`, `training`.
- Pages: `hr`, `payroll`, `ess`, `timesheets`, `recruitment`, `appraisals`.

| ID | Dim | Criterion |
|---|---|---|
| HR-1 | W | Payroll run with PAYE, NSSF (Feb 2025 phase), SHIF, housing levy and NITA → approve → GL → payslip in ESS. |
| HR-2 | W | Leave and attendance self-service with server time. |
| HR-3 | C | An employee sees only their own payslips and data; salary is never on public endpoints (business card). |

### 4.19 Localization / mobile
**Scope:** all dashboard pages; `mobile`, `notifications`; PWA (`frontend/public/sw.js`, `manifest.ts`).

| ID | Dim | Criterion |
|---|---|---|
| LM-1 | W | EN/SW/TR coverage is 100 % for staff page bodies, widgets, command palette and backend system text (i18n report shows 0 missing keys). |
| LM-2 | U | Every page at 390 px has no sideways scroll, no off-screen button, and 16 px inputs. |
| LM-3 | W | PWA install, Web Push and camera scan, with the iOS fallback. |
| LM-4 | C | The service worker never caches API data. |

### 4.20 Security / reliability / performance
**Scope:**
- Backend: `auth`, `two_factor`, `sso`, `impersonation`, `users`, `roles`, `company`, `audit`, `logs`, `security_monitor`, `health`, `modules`, `platform_depth`, `platform_depth_public`, `dashboard`.
- Pages: `admin`, `users`, `roles`, `permissions`, `security`, `logs`, `companies`, `help`, `notification-center`, `my-approvals` (shared with 4.3).

| ID | Dim | Criterion |
|---|---|---|
| SE-1 | W | SAML SP login (python3-saml or pysaml2) against a local IdP simulator; OIDC and 2FA keep passing. |
| SE-2 | C | Every API route requires auth unless it is on the allow-list; public routes are rate-limited. |
| SE-3 | C | Company isolation holds on every module (automated sweep). |
| SE-4 | R | Migration from empty, and from the previous populated head, upgrades and downgrades. Backup and restore are rehearsed. |
| SE-5 | R | The reproducible load benchmark meets the agreed thresholds. |
| SE-6 | E | `npm audit --omit=dev` and the Python dependency audit show no high or critical issues. |

## 5. Hard gates (independent of score)

A milestone cannot close, whatever its scores, unless all of these hold:

1. **All 60 audit recommendations** (M48–M52) are accepted with evidence, and so is each owner-selected original feature (03, 04, 08, 09, 12–16, 18, 20, 22–24, 28, 32, 33, 35–40). Each one is mapped to tested code and UI.
2. **No unresolved, known, confirmed software defect.**
3. **No mandatory test failure.** Every skip has a recorded reason; there is no unexplained skip.
4. **No unauthorised action.** No real post, ad, spend, e-mail outreach, payment or paid AI call was made, and SIMULATED is always distinguished from LIVE.
5. **The exhaustive role/persona matrix passed.** This covers every identity in `PERSONA_INVENTORY.md`, on desktop and phone.
6. **An independent reviewer signed off** on the exact candidate SHA.

## 6. Procedure

1. Freeze the candidate SHA. Run the gate commands.
2. Fill in one table per category: criterion ID, result, and evidence path.
3. Compute the score with §3.
4. A category below its threshold, or any failed hard gate, means: add remediation rows, fix, and rerun.
5. The reviewer checks a sample of at least 20 % of the criteria per category, and **all** criteria in Advertising, Audience management and Social automation.
