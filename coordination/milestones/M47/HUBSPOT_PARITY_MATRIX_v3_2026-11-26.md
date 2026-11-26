# HubSpot parity-plus capability matrix — v3 re-audit (M47.S01.T001, 2026-11-26)

## Method

- **HubSpot side:** the official edition catalog was fetched again on 2026-11-26. It returned HTTP 200 and was read in full: 483 hub-feature rows, 11 Agent Hub agents and 9 AEO items.
  - It was compared section by section with `M43/HUBSPOT_CATALOG_FEATURES_2026-11-25.md`.
  - Result: 0 new, 0 removed and 0 renamed features. The page's dateModified is 2026-11-05.
  - Evidence: `HUBSPOT_CATALOG_DIFF_2026-11-26.md`.
- **ERP side:**
  - A separate read-only explorer agent re-checked every v2 row against the code at `681ac61`.
  - It confirmed the cited model, service, endpoint and page files with `ls` and grep.
  - It used the M43–M46 notes in TASKS.md for what each milestone delivered.
- **Classes:** as in v2. No percentage scores.
- **Scope of this file:** rows not listed below keep the class of v2 (`M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md`). Every v2 MISSING / DEPTH_GAP row was re-checked; those that changed are listed here.

## Rows that moved to COMPLETE (with M43–M46 evidence)

**Smart CRM**
- Contacts and companies: `crm_contact_service`.
- Pipelines.
- Required and calculated properties.
- Tags and views: `crm_saved_views`.
- Teams.
- Custom objects: `custom_object_service`, plus the report source.
- Duplicates: `dedupe_service`.
- Enrichment and first-party intent: `customer_data_service`, `customer_intel_service`.
- Data quality: `dq_snapshots`.
- Task queues and repeating tasks: `crm_workspace_service`.
- SSO with OIDC: `sso_service`.
- Login-as-user: `impersonation_service`.
- Configuration sandbox: `config_bundle_service`.
- Copilot and agents.

**Sales**
- Gmail and Outlook: `mail_api_adapters`.
- Snippets, signatures, frequency caps, send time.
- Tracking.
- Calling.
- Recording, transcription, coaching.
- IVR.
- Routing.
- Buying groups.
- Playbooks and deal plans.
- Approvals, splits, handoffs.
- Goals and forecasting.
- Scheduling: `booking_service`.
- Documents.
- Analytics and journeys.
- Sales extensions (add-ins).
- Prospecting.

**Marketing**
- E-mail designer, A/B, smart content.
- Deliverability.
- CTAs: `cms_ctas`.
- Segments: `audience_service`.
- Social.
- Messenger.
- Chat for logged-in visitors.
- Attribution and journeys.
- Cookie consent.
- SEO and the Search Console adapter.
- AEO readiness.

**Service**
- SLAs, routing, capacity, presence: `service_desk_service`.
- Macros, views, QA.
- Surveys.
- Knowledge-base access groups.
- Customer success and health.
- Customer and KB agents.
- Channels API.

**Content**
- Adaptive testing: `cms_personalize`.
- Website: tree, staging, multisite, embeds, URL mappings, HubDB-like tables, dynamic pages (`cms_service`).
- Blog and SEO.
- Memberships and gated content.
- Multi-language content.
- AI content and brand voice: `content_studio_service`.
- Podcasts.
- Content approvals.

**Data**
- Generic data sync: `data_sync_service`.
- Data quality.
- Duplicates.
- Warehouse export: `warehouse_export_service`.

**Revenue**
- Quotes and multi-level approvals: `cpq_service`.
- Templates, price books, password links.
- Local e-signature.
- Invoicing, credit notes, dunning priority.
- Contracts and renewals.
- Subscription billing.
- Payment links: `payment_link_service`.
- Revenue and closing agent templates.
- MCP server.

**Agent Hub**
- Agent builder: `agent_service`.
- Credits and governance.

Many of these also carry EXTERNAL_ACTIVATION for the account or credential they need. See TASKS.md M47.S02.

## Rows corrected or still open (software buildable now → new tasks)

| Capability | v2 → v3 | Remaining software gap | Task |
|---|---|---|---|
| Multi-language content, AI translation | MISSING → COMPLETE / DEPTH_GAP | A new translation is a plain copy; there is no AI-drafted translation | M47.S01.T007 |
| Post narration | MISSING → MISSING | No narration of posts into audio | M47.S01.T007 |
| AI image | DEPTH_GAP → MISSING | No image-generation adapter feeding the DAM | M47.S01.T007 |
| Content remix | DEPTH_GAP → DEPTH_GAP | One source draft yields only one other channel | M47.S01.T007 |
| Content sync | MISSING → MISSING (v2 wrongly said bundles cover it) | CMS content is not in config bundles | M47.S01.T007 |
| Video | MISSING → DEPTH_GAP | No poster frame and no trim | M47.S01.T007 |
| Workflows: scheduled and webhook triggers | DEPTH_GAP → DEPTH_GAP | CRM workflows run only on record events | M47.S01.T008 |
| Custom events | DEPTH_GAP → DEPTH_GAP | No event definitions; events are not workflow triggers or audience conditions | M47.S01.T008 |
| Web-visitor segments | MISSING → DEPTH_GAP | Audiences cannot use pages visited, web events or intent | M47.S01.T008 |
| Product usage tracking | MISSING → DEPTH_GAP | Portal and shop usage is not part of health or churn | M47.S01.T008 |
| Task calendar sync | MISSING → MISSING | CRM tasks are not pushed to calendars | M47.S01.T009 |
| 1-to-1 video messages | MISSING → DEPTH_GAP | Tracked links only; no recorded video | M47.S01.T009 |
| Meeting recap / prep | MISSING → DEPTH_GAP | Not tied to a meeting record | M47.S01.T009 |
| AI quotes | → MISSING | No drafted quote lines | M47.S01.T009 |
| Contract import | → MISSING | No bulk import of signed contracts | M47.S01.T009 |
| Predictive deal score | DEPTH_GAP → DEPTH_GAP | Rules only; no model trained on outcomes | M47.S01.T009 |
| Field-level permissions | DEPTH_GAP → DEPTH_GAP | Masking only; no per-role hidden or read-only rule on any property | M47.S01.T010 |
| Smart properties, form shortening | MISSING → MISSING | — | M47.S01.T010 |
| Ticket pipelines | COMPLETE → DEPTH_GAP (correction: the status enum is fixed) | No configurable pipelines or stages | M47.S01.T010 |
| Slack | MISSING → DEPTH_GAP | Outbound webhook only; no routing or interactive approvals | M47.S01.T010 |
| Campaign / nurture agents | MISSING → DEPTH_GAP | No such agent templates | M47.S01.T010 |
| Ads audiences / conversions | DEPTH_GAP → DEPTH_GAP | No audience or conversion upload adapters (simulator-tested) | M47.S01.T010 |
| Editors' drag-and-drop, event tagger, data-studio blending, staff-screen i18n | DEPTH_GAP | Usability depth | M47.S01.T011 |

## Library-only items (not account-bound, but they need a package that is not installed)

These need explicit owner consent to download, so they go to the activation register (M47.S02.T010):
- SAML: python3-saml / xmlsec.
- Parquet export: pyarrow.
- Business-card OCR: tesseract.

## Kept as NOT_APPLICABLE

- Serverless and custom-coded modules: no tenant code execution, by design.
- Programmable automation.
- Salesforce sync, QuickBooks/Xero, HubSpot Capital and BNPL: out of the ERP's role.

The reasons are as in v2.
