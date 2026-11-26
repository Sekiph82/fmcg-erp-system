# M47.S01.T003 — read-only audit (2026-11-26)

Scope: working tree of `C:\Users\sekip\Desktop\fmcg-erp-system` on `main` (including other agents' uncommitted WIP at audit time).
No repository file was edited; no git write command was run; no DB or external service was contacted (route probes ran with
`DATABASE_URL` pointing at a dead port `127.0.0.1:1`).

Evidence files (all in this folder):
- `routes.py` — enumerator (walks FastAPI 0.139 `_IncludedRouter` tree, collects every dependency incl. router-level ones)
- `routes2.json` — final snapshot: 3,611 (route, method) pairs; `stale2.json` — PUBLIC_ROUTES entries with no route (empty)
- `login_only_refined.json`, `login_only_final.txt` — staff routes with login but no permission dependency
- `money.py`, `money.json` — money tables vs currency / company columns
- `metrics_probe.txt` — live TestClient probes (dead DB)

Classification of the 3,611 routes (current registry, after another agent added 3 PUBLIC_ROUTES entries mid-audit):
staff + permission check 3,116 · staff login only (no permission *dependency*) 350 · portal/supplier realm 35 · no auth dependency 110.

---

## 1. Route protection

### 1a. Reachable without auth but NOT in PUBLIC_ROUTES
| Route | Where | Finding |
|---|---|---|
| `GET /metrics` | backend/app/main.py:303 | **Defect (high).** Unauthenticated, outside `/api/v1`, so PUBLIC_ROUTES never covers it. `record_request()` (main.py:242, observability.py:95-97) keys counters by the *raw* URL path and `metrics_snapshot()` returns them (observability.py:134). Every capability-token URL hit by a customer is therefore published: `/api/v1/public/pay/{token}`, `/public/documents/{token}`, `/public/docs/{token}`, `/public/calendar/{token}.ics`, `/public/book/manage/{token}`, `/public/nps/{token}`, `/public/survey/{token}`, `/public/deal-plans/{token}`, `/public/t/c/{token}`, `/public/assets/{doc_id}/{sig}`. Probe: `GET /api/v1/public/no-such-route/SECRET-TOKEN-abc123` then `GET /metrics` → 200 and the key `GET /api/v1/public/no-such-route/SECRET-TOKEN-abc123` is listed (metrics_probe.txt). Prod compose publishes `8000:8000` directly (docker-compose.prod.yml:77-78), and DEPLOYMENT.md:246 documents `/metrics` as public. Scenario: anyone polls `/metrics`, picks up a payment-link or quotation-signing token, and opens or accepts the customer's document. The counter dict also grows without bound (one key per distinct URL, incl. 404 probes), so memory grows until the process restarts. |
| `GET /docs`, `GET /redoc`, `GET /api/v1/openapi.json` | main.py:145-147 | Always enabled, including production (probe: openapi 200, 4.7 MB). Reveals all 3,611 endpoints. Document or disable when ENVIRONMENT=production. |
| `GET /live`, `GET /ready`, `GET /` | main.py:282-310 | Intended probes. OK. |
| `POST /api/v1/public/lead-forms/{slug}/known` | crm_lead_forms_public.py:54 (uncommitted WIP, M47.S01.T010) | **Opposite problem:** the route is meant to be public (frontend/src/app/forms/[slug]/page.tsx:33 calls it anonymously) but it is missing from PUBLIC_ROUTES, so the split puts it behind `get_current_user`. Probe: anonymous call → 401 "Not authenticated". Form shortening never works for visitors. When it is added, it also needs a per-IP limit: it reveals which fields are on file for any visitor id (field names only, per its docstring). |

### 1b. PUBLIC_ROUTES entries that no longer exist
None. All 107 entries (including the 3 the other agent added during the audit: `/public/cms/media/{media_id}/poster`, `/public/crm-workflow-hooks/{workflow_id}`, `/public/web/tags`) match a registered route (`stale2.json` = `[]`). All realm routes (`/portal-self/*`, `/supplier-self/*`) have a realm dependency. No route under `/public/` is staff-protected except the WIP `/known` route above.

Structural note (not a live defect): `_split_public_routes` / the MODULE_GUARDS loop (module_registry.py:785-840) only look at direct `APIRoute`s. If a module router ever does `router.include_router(sub)`, the sub-routes land in `protected` without the module baseline guard (the `else: guarded.routes.append(route)` branch). The current walk found 0 nested routes, so this is latent only.

### 1c. Staff routes that need a login but no permission
350 routes have no permission *dependency*. 211 of them use a router-level custom gate (`_staff_access` 64, `_need._check` 28, `_gate` 21, `_guard` 16, `_manage_access` 7) or an inline helper (`_require_*_action`, `_admin`, `_editor`, `_may_run`, `_superuser`, …). These checks are real, but my first-pass regex did not recognise them (the same blind spot as `route_guard._OWN_CHECK`). 64 more pass `current_user` to a helper. I did not read every one of those 64. The rest are self-service (my notifications, my devices, 2FA, ESS). The ones that **do expose or change business data with no check** (handler read):

| # | Route(s) | File:line | Scenario |
|---|---|---|---|
| 1 | `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject` | approvals.py:146-171 → approval_service.py:143-165 | **Defect (high).** `approve_request()` never checks that the caller holds the step's `required_role` or is not the requester. Any signed-in user (a picker or a field rep, say) can approve every pending multi-level approval request, including their own, level by level. The Slack path does both checks (messaging_service.py:260-266), so web and Slack behave differently. |
| 2 | `GET /chatter/activities`, `/activities/{id}`, `/feed`, `/timeline`, `/stats`, `/sla/breached`; `POST /chatter/activities`, `/{id}/pin`, `/{id}/comment`, `/{id}/attach` | chatter.py:19-130 | **Defect (medium-high).** No permission check and no record scope: any user reads the activity and comment stream of every record type (sales, HR, finance references) by `reference_type`/`reference_id`. Author spoofing: `ActivityCreate.created_by` (schemas/chatter.py:77) and `CommentCreate.user_id/user_name` (schemas/chatter.py:83-84) come from the request body. Only comment edit/delete check ownership (chatter.py:100-118). |
| 3 | `GET /service-desk/tickets/{tid}`, `POST /service-desk/tickets/{tid}/{pause\|resume\|route}`, `POST /service-desk/tickets/{tid}/macro/{mid}` | service_desk.py:112, 128, 160 (`_ticket` :28 is a bare `db.get`) | **Defect (medium).** `/helpdesk` is module-guarded (route_guard.py:46), but `/service-desk` is not. Any user can read any ticket's hand-off summary and QA reviews, pause a ticket's SLA clock (which hides breaches), re-route it, or post a macro as a **customer-visible** reply (`is_internal=False`) that also changes the ticket status. |
| 4 | `GET /calendar/events` | calendar.py:60 → calendar_service.py:180 | **Defect (medium, privacy).** Returns every user's events with participants, description and location. There is no owner or visibility filter. |
| 5 | `GET /data-sync`, `GET /data-sync/quality` | data_sync.py:51, 173 | Low-medium. Any user sees every sync definition, including `source_url`, field mapping, run counts and data-quality trends. Writes are gated (`_admin`, `_may_run`). |
| 6 | `POST /calls/scripts`, `POST /calls/dialer`, `GET /calls/ivr` | voip.py:297, 449, 402 | Low. Any user can create call scripts, or a dialer session over arbitrary customer/CRM ids and phones. |
| 7 | `POST /email/templates` | email_integration.py:338 | Low. Any user can create shared e-mail templates. |

Routes cleared on inspection (so they can be skipped): inventory adjust/delete/movement (`_require_warehouse_action`), finance journal create/post/reverse and purchase-invoice post (`_require_finance_action`), expenses (router `_gate` plus `_approver`), loyalty/nps (`_guard`), portal and supplier-portal staff (`_staff_access`), quality-enterprise (`_need`), config-bundles and warehouse-exports (`_admin`), sso/config (`_superuser`), data-sync writes (`_may_run`/`_admin`), crm-playbooks (`_editor`), sales-quotas (`_visible`/`_get`), graphql (per-resolver `has_any_permission`, graphql_api.py:44).
Not verified: what `imp.start` (impersonation.py:29) checks inside the service; the 64 "delegated" routes listed in `login_only_final.txt`.

---

## 2. Secrets / real data in tracked files (4,163 files, `git grep`)
- Private keys, AWS/Google/Stripe/GitHub/Slack/Anthropic keys, JWTs, DB URLs with real passwords: **none found**. The only `sk-ant-` hits are the placeholders `sk-ant-...` in TASKS_HISTORY.md:176,187 and the legacy tracker copy.
- `.env*` tracked: only `.env.example`, `.env.development.example` and `.env.production.example`, all with placeholders.
- `INITIAL_ADMIN_PASSWORD=Admin1234!` appears in .env.development.example:24, README.md:59 and CI (.github/workflows/ci.yml:38, `CiAdmin1234!`). These are documented dev defaults. **But** the production guard (config.py:406) only rejects empty or `CHANGE_ME*`, so `Admin1234!` (or `change-me-dev-admin123` from .env.example:30) is accepted in production. Small fix.
- `SECRET_KEY="changeme"` default (config.py:19) is rejected only when `ENVIRONMENT == "production"` (config.py:356). Staging is not guarded, though scripts/make_staging_env.py generates random secrets. Document.
- **Real-looking third-party data** (not POVU / .test / example):
  - demo-data/1_suppliers.csv: real company names and real-looking domains (`Solvay Chemicals`, `ibrahim@solvay-local.com`, `ali@chemsource.com`, `david@polypack.co.ke`, …) and KRA-PIN-shaped values (`A100234567B`, …).
  - demo-data/5_employees.csv: `@company.com` addresses (a registered domain), bank-account-shaped strings (`Garanti-1234567890`).
  - backend/app/db/seed.py:18-54: demo C-suite users at `@erp.com` (a registered domain). If SMTP is configured, notifications to these users go to a real third party.
  - bulk_import.py:164 (`john@abc.com`) and :3743 (`utilities@plant.com`) in import templates.
  - The policy says to use POVU, `example.com` or `.test`. Phones in app code are Safaricom sandbox `254712345678` or `+2547000000xx` (fine).
- Plaintext provider secret: `WhatsAppConfig.api_token` is stored unencrypted (models/whatsapp.py:43 even says "store encrypted in prod"; whatsapp.py:128 `WhatsAppConfig(**body.model_dump())`). Mailbox secrets are encrypted (`secret_enc`), so this one is inconsistent.

---

## 3. Privacy / consent on outbound channels
| Sender | Where | Consent / suppression | Gap |
|---|---|---|---|
| CRM outbox (sequences, campaigns, manual CRM mail) | crm_outbound_service.py:98-114 (`queue`, the only insert of `CRMOutboundMessage`), :134-160 `deliver_due` | SUBSCRIBED required for SEQUENCE/CAMPAIGN; suppression re-checked before send; signed unsubscribe link and List-Unsubscribe header | OK |
| Staff mailbox send `POST /email/send` | email_integration.py:235 → email_mailbox_service.py:464-501 | **None.** No check against UNSUBSCRIBED/BOUNCED/COMPLAINED | The outbox rule (crm_outbound_service.py:4-5: suppressed addresses are blocked "for every purpose except MANUAL one-to-one mail to non-suppressed addresses") is bypassed. Staff can keep mailing a complained or bounced address from the ERP mailbox. Fix: call `_blocked_reason(..., "MANUAL")`. |
| WhatsApp `POST /whatsapp/send/text`, `/send/template` | whatsapp.py:161, 205 | **None.** No opt-in record and no opt-out list; any number | The demo template footer says "Reply STOP to unsubscribe" (whatsapp.py:466), but no STOP keyword is handled anywhere in the inbound webhook. Kenya DPA and Meta policy both need opt-in for business-initiated messages. |
| Ad-platform customer lists | ads_adapters.py:526-545 `upload_audience` | Consent only when `audience.require_consent` is true (default true, models/crm.py:1269) | With `require_consent=False`, every member's hashed e-mail and phone, **including UNSUBSCRIBED/COMPLAINED**, goes to Meta or Google. Marketing uploads should always need SUBSCRIBED, or at least drop suppressed addresses. |
| Trip notice SMS/WhatsApp | customer_messaging.py:57+ (`notify_customer`, called from field_app.py:532) | None (transactional "order on the way") | Document: transactional, but there is no per-customer opt-out. |
| Meeting recap: audio → transcription engine, transcript → cloud LLM | sales_depth.py:100-130 (untracked WIP) → meeting_service.py:327-328 → sales_ai_service.py:36 | **No recording-consent attestation** | Calls need `recording_consent` before AI analysis (conversation_intel_service.py:61-62), but uploaded meeting recordings and transcripts go to the transcription HTTP engine and the LLM with no consent flag and no masking. |
| Quote drafting | cpq_service.py:212 (modified WIP) | No masking | Deal notes (free text, may contain personal data) go to the LLM unmasked. `ai_service` uses `mask_sensitive_context` (ai_service.py:257); `sales_ai_service`, `conversation_intel_service`, `agent_service` and `content_studio_service` do not. Budget-gated, so off by default. Document, or mask. |
| Signer code e-mail, OTP e-mail/SMS, web push | documents_public.py:103, email_sender.py, sms_sender.py, web_push_service.py | Transactional / staff | OK |
| Web analytics identify | web_analytics_service.py:98-108 | Marketing consent of the *visitor id* | Low. The caller attests consent and the e-mail itself, so anyone can bind their visitor id to someone else's e-mail and pollute that person's CRM web-activity timeline. Document. |

---

## 4. Multi-company / currency / locale
Money tables (243 with money-named Numeric columns, money.json). Only 10 tables have `company_id`, so company scoping is mostly absent. The concrete sibling inconsistencies:
| Table | File:line | currency | company/branch | Sibling that has it |
|---|---|---|---|---|
| invoices | models/sales.py:268 | yes (default **USD**, :278) | **no** | sales_orders (company_id+branch_id, sales.py:148) |
| payments (customer) | models/sales.py:314 | **no** | **no** | supplier_payments has company_id |
| purchase_invoices | models/finance.py:733 | yes | **no** | purchase_orders has company_id+branch_id |
| purchase_payments | models/finance.py:778 | **no** | **no** | — |
| supplier_payments | models/procurement.py:278 | **no** | yes | — |
| pos_sales | models/pos.py:55 | **no** | **no** | van_sales_txns has currency |
| van_payments | models/van_sales.py:225 | **no** | **no** | — |
| payment_allocations | models/finance.py:794 | **no** | **no** | — |
| commission_payouts / commission_txns | — | no | no | — |
| journal_entries | models/finance.py:184 | header has none (lines have currency, :231) | yes | OK by design |
Default-currency inconsistency: customers, sales_orders, invoices and purchase_orders default to **"USD"** (sales.py:106,153,278; procurement.py:122), while chart_of_accounts, journal_lines, cash_accounts and budgets default to **"KES"** (finance.py:145,231,440,571). Scenario: an invoice row created without an explicit currency is USD and its GL lines are KES. I did not check whether every API path sets the currency explicitly.

Hard-coded KES / en-KE in customer-facing frontend paths (`portal chat kb book nps survey pay site forms lp d docs kartvizit unsubscribe verify`): **no `"KES"` or `en-KE` literals found**. Portal uses `formatters(locale)` (`f.money`, portal/page.tsx:136-283). Bypasses:
- frontend/src/app/d/[token]/page.tsx: the customer quotation and e-signature page has **zero i18n**. It has its own `money()` with `toLocaleString(undefined, …)` (:18), English-only strings ("Accepted"/"Declined", :124; "This private link works until", :165), and browser-locale dates.
- frontend/src/app/docs/[token]/page.tsx: zero i18n, English strings, browser-locale date.
- site/[key]/[locale]/blog/page.tsx:35 uses `toLocaleDateString(locale)`. This is fine because it takes the route locale.
Backend customer paths: no hard-coded KES except payment_link_service.py:117 (M-Pesa is KES-only, which is correct).

---

## 5. Import / export / backup
- Backup/restore documentation: docs/DEPLOYMENT.md:212-235. It describes a `pg_dump` (plain SQL) and a restore with `cat backup.sql | psql`. Gaps: (1) **only the DB**. The `documents_data` volume (docker-compose.prod.yml:80, documents, DAM, attachments) is not mentioned. (2) The restore goes into the existing DB with no `--clean`, no `ON_ERROR_STOP` and no post-restore checks. (3) It says nothing about keeping `SECRET_KEY` / `WEBHOOK_SECRET_ENCRYPTION_KEY` with the backup. Without them, the encrypted columns (webhook secrets, mailbox `secret_enc`) cannot be recovered. (4) No schedule, retention or off-site copy.
- **Defect (high, data loss):** CMS media are stored under `MEDIA_STORAGE_PATH` (default `data/media`, config.py:84, used at cms_media_service.py:51), i.e. `/app/data/media` inside the container (Dockerfile.prod:3). Prod and staging compose set no `MEDIA_STORAGE_PATH` and mount no volume for it, so every uploaded video, audio file, poster and caption is lost when the backend container is recreated, and no backup captures them.
- Tested restore: the only rehearsal is coordination/sessions/M01.S03.T004/run_disposable_rehearsal.ps1:97-104 (custom-format `pg_dump`, `pg_restore --list`, `pg_restore --exit-on-error` into a disposable DB). That is evidence from M01. It does not match the documented plain-SQL procedure, and there is no current or repeatable restore script in scripts/ or backend/scripts/.
- Export endpoints (47 routes with export/csv/xlsx/download in the path): 41 have a permission dependency. The other 6 (`/sales-quotas/export.csv`, `/config-bundles/export`, `/warehouse-exports*`) check inline (`_visible`, `_admin`). **No unprotected export found.**

---

## 6. Operational limits on public unauthenticated POSTs
- **No global request-body limit.** `InputSanitizerMiddleware` (core/input_sanitizer.py:55-75) does `await request.body()` and `json.loads` on every JSON POST/PUT/PATCH with no size cap, before routing. `DocumentUploadBodyLimitMiddleware` only covers document uploads. Probe: a 5 MB JSON body to `POST /public/chat/sessions` is read fully and rejected only by validation (422). Scenario: unauthenticated multi-MB to hundreds-of-MB JSON bodies to any public POST tie up worker memory and CPU (gunicorn runs 2 workers, Dockerfile.prod CMD). Fix: a global Content-Length/stream cap (e.g. 1 MB, larger only for upload paths).
- Public POSTs with **no rate limit found** in the endpoint or its service:
  - `/public/web/consent`, `/collect`, `/identify`, `/forget` (web_analytics_public.py:77-105). The docstring at :4 says "Per-connection limits apply", but there is none in the endpoint or in web_analytics_service.py. There is a 32 KB body cap (:69). Scenario: an unthrottled write per request floods `web_events`. **Defect.**
  - `/auth/2fa/use-recovery-code` (two_factor.py:500-530): no attempt counter, while login-verify caps attempts (two_factor.py:400-401, `MAX_ATTEMPTS`→429). Recovery codes have about 41 bits of entropy (core/totp.py:73-79), so the brute-force risk is low, but each guess runs a passlib verify against up to 10 hashes (a CPU cost per request). Small fix: reuse the session `attempt_count`.
  - `/auth/2fa/required-setup`, `/auth/refresh`, `/portal-self/auth/activate`, `/supplier-self/auth/activate`: token-gated, no limit. Low.
  - Token-gated customer actions with no limit: `/public/documents/{token}/view` and `/decision`, `/public/docs/{token}/view`, `/public/deal-plans/{token}/steps`, `/public/nps/{token}`, `/public/survey/{token}`, `/public/book/manage/{token}/cancel` and `/reschedule`, `/public/unsubscribe`, `/public/t/optout`. The token is the credential and most writes are one-shot. Low; document.
  - Provider callbacks (`/integrations/mpesa/callback`, `/sales/mpesa/callback`, `/moto-sales/mpesa/callback`, `/whatsapp/webhook`, `/public/social/meta`, `/public/mail-events/{provider}`, `/calls/provider/callback`, `/webhooks/inbound/*`): signature- or secret-verified, no rate limit. Acceptable; document.
  - Rate-limited (verified 429 paths): auth/login, 2FA login-verify/resend, portal/supplier login (`login_guard`), portal signup-request, lead-form submit, LP convert, KB feedback, CMS convert/click/view, booking create, chat sessions and messages (crm_chat_service.py:55-103), payment-link STK push (payment_link_service.py:107), signer-code (documents_public.py).
- Limiter design caveats (document): several limiters are in-process dicts (e.g. business_cards_public.py:48-51), so they are per gunicorn worker. All per-IP keys use `request.client.host`, and gunicorn trusts `X-Forwarded-For` only from `FORWARDED_ALLOW_IPS` (default 127.0.0.1). Behind a proxy container, every visitor shares the proxy IP, so per-IP limits become global (one abuser triggers "Chat is busy" or a lockout for everyone) unless FORWARDED_ALLOW_IPS is set.
- WIP not verified: `/public/crm-workflow-hooks/{workflow_id}` (added to PUBLIC_ROUTES mid-audit; its comment claims a rate limit) and `/public/web/tags`.

---

## Prioritised list

### Fix now (software defects)
1. **/metrics is public and leaks capability tokens** (main.py:303, 242; observability.py:95-134). Require auth or an internal bind, and key counters by the route template, not the raw path. That also fixes the unbounded memory growth.
2. **Generic approvals: any user can approve or reject any request, including their own** (approval_service.py:143-165 via approvals.py:146-171). Enforce `required_role` and second-person as the Slack path does (messaging_service.py:260-266).
3. **CMS media on ephemeral container storage** (config.py:84; docker-compose.prod.yml/staging have no MEDIA_STORAGE_PATH or volume). Media are lost on redeploy and missed by backups.
4. **No global request-body cap** (input_sanitizer.py:64). Unauthenticated large JSON bodies are fully buffered.
5. **Chatter unscoped, with author spoofing** (chatter.py:19-130; schemas/chatter.py:77, 83-84).
6. **Service desk bypasses the helpdesk guard** (service_desk.py:112, 128, 160): SLA pause, re-route and customer-visible macro replies for any user.
7. **WhatsApp sends without opt-in/opt-out; "Reply STOP" is not handled** (whatsapp.py:161, 205, 466).
8. **Staff mailbox send ignores suppression** (email_mailbox_service.py:464). Add the outbox MANUAL check.
9. **Ad audience upload ignores suppression when require_consent=False** (ads_adapters.py:536).
10. **Public web analytics endpoints have no rate limit** (web_analytics_public.py:77-105), although the docstring says they do.
11. **WIP M47.S01.T010 `/public/lead-forms/{slug}/known` missing from PUBLIC_ROUTES** (anonymous → 401). Add it, with a per-IP limit.
12. **Calendar events list exposes all users' events** (calendar.py:60 / calendar_service.py:180).
13. **Meeting-recap upload sends recordings and transcripts to the transcription engine and LLM with no consent attestation** (sales_depth.py:100-130, WIP).
14. Production accepts `Admin1234!` as INITIAL_ADMIN_PASSWORD (config.py:406). Use the same placeholder/weak-value guard as SECRET_KEY.
15. Recovery-code endpoint has no attempt cap (two_factor.py:500). Reuse `attempt_count`.
16. WhatsApp `api_token` stored in plaintext (models/whatsapp.py:43). Encrypt it like `secret_enc`.
17. Customer quotation and signing pages `d/[token]`, `docs/[token]` have no i18n and their own formatters (d/[token]/page.tsx:18, 124, 165).

### Document only
- `/docs`, `/redoc`, openapi enabled in production (main.py:145-147); decide whether to keep them.
- Backup doc covers the DB only. Add the documents volume, the encryption-key escrow, a `--clean`/`ON_ERROR_STOP` restore, a schedule and retention, and a repeatable restore drill (the only rehearsal is M01's script).
- Money-model gaps: invoices, payments, purchase_invoices, purchase_payments, pos_sales, van_payments and payment_allocations lack currency and/or company. USD defaults on customers, orders and invoices vs KES on the ledger (I did not check whether the APIs always set it). This needs a multi-company/currency design decision before a fix.
- Demo and seed data use real-looking third-party names and registered domains (demo-data/1_suppliers.csv, 5_employees.csv, seed.py `@erp.com`, bulk_import.py `abc.com`/`plant.com`). Replace them with POVU / `.test`.
- Staging skips the SECRET_KEY guards (config.py:356).
- Per-worker in-memory limiters and the `FORWARDED_ALLOW_IPS` requirement for correct per-IP limits behind a proxy.
- Token-gated public POSTs and signed provider callbacks have no rate limits (acceptable; record the rationale).
- Trip-notice SMS/WhatsApp is transactional with no opt-out. LLM calls outside `ai_service` are not masked (budget-gated, off by default).
- Web-analytics `identify` is self-attested and can link a visitor to someone else's e-mail.
- Latent: nested sub-routers would skip the MODULE_GUARDS baseline (module_registry.py:820-840). The `_OWN_CHECK` regex does not recognise `_require_*_action`, `_gate`, `_staff_access`, etc. (route_guard.py:87-92). Harmless today because those routes check themselves.
- Not verified: the 64 delegated-check login-only routes in `login_only_final.txt`, impersonation service checks, and the new crm-workflow-hooks and web/tags public routes.
