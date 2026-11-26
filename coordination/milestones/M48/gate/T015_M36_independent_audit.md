# T015: Independent security, privacy and migration audit of M36 (CRM)

| Item | Detail |
|---|---|
| Repo state | HEAD 60e360a |
| Method | Read-only static review. No database was touched and no tests were run. |
| Reviewer | A separate review agent, not the author of M36. The agent had no write tool, so the coordinator saved this report verbatim from its message. |
| Covers | TASKS.md M36.S06.T003 and M48.S01.T015 |

## Verdict: ACCEPT_WITH_FIXES

There are no critical issues and no authentication bypass on the public routes. Remediation is tracked as M48.S01.T022 and T023.

## Findings

| ID | Severity | Area | Defect | Where | Fix |
|---|---|---|---|---|---|
| F1 | Medium/High | Privacy, consent | Marketing consent has no double opt-in, so anyone can subscribe a stranger through the lead form or chat. | crm_lead_capture_service.py:165-168; crm_chat_service.py:106-108, 154 | Add a PENDING state; set SUBSCRIBED only after a signed confirmation link is clicked. |
| F2 | Medium | Privacy, consent | Production does not check that PUBLIC_APP_URL and PUBLIC_API_URL are https and not localhost when outbound mail is enabled. The unsubscribe HMAC is keyed with the global SECRET_KEY, so rotating that key breaks every link already delivered. | crm_outbound_service.py:45-58, 124-131; config.py | Validate the URLs in production; use a dedicated UNSUBSCRIBE_SECRET that also accepts previous keys. |
| F3 | Medium | Migrations | Downgrades of 0041, 0042, 0043, 0051, 0052 and 0055 drop the consent register, outbox suppression and signed quote decisions. Their DDL is built from the live models. | alembic versions listed | Make downgrades of evidence tables no-ops or archive them; freeze the DDL. |
| F4 | Medium | Authorization, control bypass | ABM group campaigns and `/email-designs/{id}/send` skip MARKETING_EMAIL_APPROVAL_REQUIRED. ABM mixes companies, and neither path has a cap. | crm_abm_service.py:103-136; crm_abm.py:137-144; email_designs.py:128-144 | Route both through one shared approval guard; add company scope and a cap. |
| F5 | Medium | IDOR, privilege | Contact and add-in writes use the view scope, so `crm.view_all` plus `crm.edit_own_scope` can edit any contact or deal. | crm_contacts.py:26-44; crm_addin.py:38-43, 83-93 | Use edit-scope checks for all writes. |
| F6 | Medium | Privacy | Conversation intelligence sends unredacted transcripts (up to 12,000 chars) to the AI provider, and insights with verbatim quotes outlive purged sources. | conversation_intel_service.py:78-88, 110-123; 0064 | Redact before the provider call; purge or cascade insights with their source. |
| F7 | Low/Medium | Privacy | No retention for lead submissions, e-mail events, landing events, document views or signer codes; no erasure path for consent records. | various | Set retention per table; document anonymisation of the consent register. |
| F8 | Low | Functional | A marketing unsubscribe also suppresses INVOICE (payment-link) mail. | crm_outbound_service._blocked_reason :88-92 | Exempt INVOICE from UNSUBSCRIBED; keep BOUNCED and COMPLAINED suppression. |
| F9 | Low | Robustness | Landing convert does not catch MissingField and returns HTTP 500. | crm_landing_public.py:55-60 | Return 422. |
| F10 | Low | Deployment | Per-IP limits depend on FORWARDED_ALLOW_IPS and are kept in per-worker memory. | crm_lead_forms_public.py:54-69 | Add a production warning; move limits to a shared store. |
| F11 | Low | Webhooks | The Mailgun signature covers only timestamp and token, so one captured signature can be replayed within MAX_AGE. | deliverability_service.py:53-71 | Reject tokens already seen. |

## Checked and found sound

**Public routes and tokens**
- Quote share links: 192-bit tokens stored hashed, expiry and revocation, separate view POST, password limiter.
- Signer codes: HMAC-hashed, 15-minute lifetime, 5 tries, single use, 10 tries per link per day, re-checked under row lock.
- Unsubscribe tokens: HMAC compared in constant time; GET only shows the page, POST unsubscribes.
- Tracking: HMAC tokens, no open redirect, opt-out respected, no raw IPs stored.
- Chat: visitor token hashed, honeypot, rate limits and caps.
- Mail-event webhooks: fail closed, timestamp checks, replay dedupe, SendGrid ECDSA verification.
- Workflow hooks: tokens stored as digests, rate limits, body cap.
- Lead forms: honeypot, database-backed limits, consent text snapshot, company-scoped dedupe, uniform 202 response.
- Knowledge-base search escapes wildcards.

**Staff routes and outbound mail**
- Pipeline scope and child-object scope checks; config routes need edit_all; customer scope enforced.
- Outbound mail:
  - MANUAL mail is limited to the contact on record, with a daily cap.
  - Mail headers are protected against injection.
  - Suppression is checked again at send time.
  - Sends use SKIP LOCKED claims with no automatic retry, and a frequency cap applies.

**Injection and XSS**
- Designed e-mails are HTML-escaped and validated.
- The knowledge-base markdown renderer escapes its input first.
- The SQL table name in contact associations comes from a fixed dict.

**Privacy design and secrets**
- The copilot redacts personal data, and IP addresses are stored only as keyed hashes.
- The production secret validator is in place.

**Migrations**
- 0040–0067 form a linear chain; 0056, 0066 and 0067 use IF NOT EXISTS; downgrades of 0056, 0064 and 0066 are clean; 0064 has its constraints.
