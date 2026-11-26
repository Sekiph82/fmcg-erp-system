# POVU ERP vs HubSpot — final feature-by-feature comparison (M47.S01.T004, 2026-11-26)

## Basis

**HubSpot side:**
- Official product & services catalog, re-fetched 2026-11-26: HTTP 200, 483 hub-feature rows, 11 Agent Hub agents, 9 AEO items.
- Unchanged since the 2026-11-25 snapshot (`HUBSPOT_CATALOG_DIFF_2026-11-26.md`).

**ERP side:**
- Matrix v2 (M43): `coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md`, row by row with code evidence.
- v3 re-audit (M47): `HUBSPOT_PARITY_MATRIX_v3_2026-11-26.md`.
- Implementation evidence: TASKS.md rows M43–M47 and the gate reports `coordination/milestones/M4x/gate/`.

**Rules:**
- No percentage parity score and no market-size or live-accuracy claim.
- "Local parity" means the software capability exists and is tested with synthetic data and local simulators.
- Anything that needs a vendor account, a licence, a dataset or an approval is listed as an activation prerequisite (TASKS.md M47.S02), not as done.

## 1. Capability-by-capability result

Each hub lists its capabilities and the ERP evidence (milestone in brackets). Activation-only items are flagged per hub.

### Smart CRM / platform

**Data model**
- Contacts and companies with M:N associations and labels; lifecycle stages (M43).
- Multiple pipelines (M43).
- Required and calculated properties; tags; saved and team views (list and calendar) (M43).
- Custom objects and associations, also usable as a report source (M45, M46).

**Teams and access**
- Teams with hierarchy (M43).
- Field-level permissions: HIDDEN or READ_ONLY per role, enforced in the APIs (M47.T010).
- Sensitive-data masking (M45).
- SSO with OIDC + PKCE (M45). SAML is library-only: M47.S02.T010.
- Audited login-as-user and admin notification policies (M45).

**Data quality**
- Duplicate management with merge and undo (M45).
- Data-quality overview and trend (M45).

**Configuration**
- Configuration sandbox with bundles. They now include CMS content (M45, M47.T007).

**Smart properties and forms**
- Rule-filled smart properties (M47.T010).
- Form shortening for recognised consented visitors (M47.T010).

**Custom events**
- Custom web events with typed definitions, used as workflow triggers and audience conditions (M47.T008).
- Point-and-click tagger (M47.T011).

**AI**
- CRM copilot with a rule fallback (M36, M45).
- Agent builder (M45).

**Integrations**
- Slack notices with per-event routing and signed interactive approvals (M44, M47.T010).
- Mobile/PWA, developer API, GraphQL, versioned webhooks and an MCP server (earlier milestones, M45).

**Activation only:**
- Licensed enrichment and intent data.
- SAML libraries.
- Real Slack app credentials.

### Sales Hub

**E-mail and messaging**
- 1-to-1 e-mail through Gmail / Microsoft Graph adapters (M43).
- Templates, snippets, signatures, frequency caps, rule-based send time, tracking (M43).
- 1-to-1 video messages: recorded or uploaded, tracked and expiring links, views on the timeline (M47.T009).

**Calling**
- Voice adapter, IVR, recording with consent, transcription adapter, coaching playlists, conversation intelligence (M43, M44).

**Pipeline management**
- Routing and lead rotation (M43). Form and chat leads are routed too (M47.T002).
- Sequences, ABM, lead scoring.
- Deal score: factor rules (M43) plus a trained deal-win model with holdout metrics and a cold-start label (M47.T009).
- Buying groups, playbooks, deal plans, stage gates, approvals, splits, handoffs (M43).
- Goals and forecasting.

**Meetings and tasks**
- Meeting scheduling and calendar sync (M43).
- CRM tasks pushed to calendars (M47.T009).
- Meeting recap from the transcript (verbatim-quoted, consent-gated) and a pre-meeting brief from stored facts (M47.T009, T003).

**Documents and insight**
- Sales documents with view and download tracking (M45).
- Productivity reports and deal journeys (M43, M44).

**Extensions and prospecting**
- Outlook and Gmail add-ins (M45).
- Prospecting from licensed or own data (M45).

**Activation only:**
- Mailbox OAuth verification.
- Voice carrier and number.
- Transcription engine.
- Marketplace listing for the add-ins.
- LinkedIn Sales Navigator.
- Business-card OCR (library, M47.S02.T010).

### Marketing Hub

**E-mail**
- Visual e-mail designer with drag-and-drop ordering, A/B, smart content and approvals (M44, M47.T011).
- Deliverability monitoring (M44).

**Capture**
- Forms, landing pages and CTAs (M36, M46).

**Audiences**
- Rule-based audiences: CRM fields plus web behaviour (pages, events, intent), always consent-aware (M44, M47.T008).
- Ads reporting (M44).
- Audience and conversion uploads to Meta and Google: hashed, consent-only, simulator-tested (M47.T010).

**Social and channels**
- Social publishing with approvals; Instagram DM, Messenger, WhatsApp with STOP opt-out (M44, M47.T003).
- Live chat and bots, including logged-in portal visitors (M36, M45).

**Analytics and consent**
- First-party analytics, funnels, journeys, attribution (M44).
- Cookie consent manager (M44).

**Content and search**
- SEO suite and AEO readiness (M46).
- Video hosting with captions, poster and trim (M46, M47.T007).
- Campaign and nurture agent templates, draft-only (M47.T010).
- Content studio with brand voice (M46).

**Activation only:**
- Meta/Google/LinkedIn/TikTok business accounts and app review.
- Search Console.
- Answer-engine measurement.
- Mail relay and DNS.

### Service Hub

**Tickets**
- Helpdesk tickets with configurable pipelines and stages (M47.T010, corrected in v3).
- SLAs, conditional SLAs, skills routing, capacity, presence (M45).
- Macros, views, QA reviews, CSAT/CES and post-chat surveys (M45).

**Self-service**
- Knowledge base with access groups (M46).
- Customer portal (M38).
- Service, customer and KB agents (M45).
- Channels API.

**Customer success**
- Health scores using order and product-usage signals, with churn alerts (M45, M47.T008).

**Activation only:**
- Real messaging channels.
- Voice.

### Content Hub

**Website**
- Website builder: site tree, block editor with drag-and-drop, staging and two-person publish, versions and rollback, multisite, embeds, redirects (M46, M47.T011).
- HubDB-like tables and dynamic pages (M46).
- Blog (M46).
- Memberships and gated content (M46).
- Podcasts with RSS (M46).

**Personalisation and testing**
- Personalisation and adaptive (bandit) testing (M46).

**Languages**
- Multi-language content (EN/SW/TR) with hreflang and translation workflow, plus AI-drafted translations within budget (M46, M47.T007).

**AI**
- Brand voice and claims review (M46).
- One-to-many remix (M47.T007).
- Narration via a TTS adapter (M47.T007).
- AI image adapter producing drafts that need approval (M47.T007).

**Operations**
- Content approvals and audit (M46).
- Content sync through config bundles (M47.T007).

**Activation only:**
- Custom domain, DNS and HTTPS.
- An image-generation provider.
- A TTS engine (espeak or a provider).

### Data Hub

- Generic data sync: CSV, JSON and webhook, with dry run, conflicts, rollback and replay (M45).
- Data quality (M45).
- Duplicates (M45).
- Warehouse export: folder, S3 and PostgreSQL targets (M45).
- Report-builder datasets: upload a table and blend it with any ERP source (M47.T011).
- Workflows with record, scheduled, inbound-webhook and web-event triggers (M36, M47.T008).
- Custom objects (M45).

**Activation only:**
- Snowflake and BigQuery accounts.
- Named SaaS connectors.
- Parquet (library).

### Revenue Hub

**Quoting**
- CPQ: price books, promotions, templates, password links, multi-level approvals tied to discount (M45).
- AI-drafted quote lines, draft-only (M47.T009).

**Signing and contracts**
- Local e-signature with signer codes (M41).
- Contracts and renewals (M45).
- Contract bulk import (M47.T009).

**Billing and payments**
- Invoices with eTIMS, credit notes, dunning (earlier milestones).
- Subscription billing (M45).
- Payment links with M-Pesa STK and a test mode (M45).

**AI agents**
- Revenue and closing agent templates (M45).

**Activation only:**
- Daraja production credentials.
- A card provider.
- DocuSign or Adobe.
- eTIMS live.

### Agent Hub

- Agent builder with versions, two-person publish, budgets, emergency stop and an approval queue (M45).
- Named agents: prospecting, research, customer, KB, content, revenue, closing, health, campaign, nurture (M45, M47.T010).

**Activation only:** a real LLM provider budget.

### AEO

- AEO readiness audit, FAQ and BlogPosting structured data (M46).

**Activation only:** brand-visibility and prompt-tracking measurement. It reports NOT_AVAILABLE until then, never a made-up score.

## 2. Deliberate non-goals (NOT_APPLICABLE)

- **Serverless functions and custom-coded modules:** no tenant code execution, by security design. Typed configuration modules are used instead.
- **Salesforce sync, QuickBooks/Xero, HubSpot Capital, BNPL:** the ERP *is* the system of record for these domains.

## 3. Where POVU ERP goes beyond HubSpot (native FMCG advantages, measurable in the software)

1. **One record from lead to cash to factory.**
   - A website lead becomes a quote, then an order. The order drives MRP and production, QC release and lots, pick, dispatch and POD, then invoice, GL and payment.
   - All in one database. The integrated scenario test (M47.S01.T002) proves the chain.
   - HubSpot stops at the deal or invoice and needs an ERP integration for the rest.
2. **Lot-level product safety.**
   - A consumer complaint leads to forward and backward trace, then a recall reaching the affected customers, then NPS and loyalty.
3. **Kenyan go-to-market built in:**
   - M-Pesa (STK, callbacks, reconciliation);
   - KRA eTIMS;
   - distributor, shop and field-van sales with offline orders;
   - Swahili and Turkish UI;
   - Kenya payroll;
   - CBK FX revaluation.
4. **Trade marketing:** promotions and schemes, trade spend, TPM, market intelligence, loyalty tiers paid on settled invoices.
5. **Governance by default:**
   - Two-person rules for publishing content, agent versions, discount approvals and generic approvals.
   - Consent-gated personalisation, analytics, WhatsApp and ad uploads.
   - Honest NOT_CONFIGURED / NOT_AVAILABLE states instead of invented numbers.

## 4. Remaining limitations (honest)

- **Vendor-only or private data:**
  - licensed enrichment and intent data;
  - ad-platform lookalikes;
  - answer-engine visibility;
  - Search Console.
  These need accounts and data that do not exist before the business is live.
- **Bounded software depth (explicitly recorded, not hidden):**
  - The staff dashboard page bodies are English; the shell, navigation, login and home, plus every customer-facing screen, are EN/SW/TR.
  - The editors use block lists with drag-and-drop, not a free-form canvas.
  - Narration and AI images need an engine or provider before they produce output.
- **Library-only:** SAML, Parquet and OCR need an approved package install (M47.S02.T010).
- **Not yet proven at scale:** performance, concurrency and multi-worker rate limiting are only measured at commissioning (M47.S02.T009).

## 5. Exact future activation prerequisites

These are the rows M47.S02.T001–T010 in TASKS.md. Each lists its setup checklist, minimal live smoke test, rollback and audit:
1. Domain, DNS and HTTPS.
2. Mailboxes and OAuth.
3. Voice carrier.
4. Meta, Google and LinkedIn business accounts.
5. Online store.
6. Payments, bank, eTIMS and signature provider.
7. Real master data and users.
8. Licensed data and AI endpoints.
9. Commissioning UAT, performance and restore drill.
10. Library installs.
