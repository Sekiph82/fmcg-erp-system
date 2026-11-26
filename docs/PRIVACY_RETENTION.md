# CRM privacy: retention, consent and erasure

This document covers M48.S01.T022, which fixes audit finding F7 and parts of F1 and F2.

## Retention

The daily purge job deletes old rows. The job is `crm_chat_service.run_purge`, which the API lifespan starts. Each purge runs in its own transaction.

| Data | Table | Setting (days) | Default | Counted from |
|---|---|---|---|---|
| Closed or idle website chats and their messages | crm_chat_sessions, crm_chat_messages | `RETENTION_DAYS` in crm_chat_service | 365 (7 days for chats with only the bot) | last message or close time |
| Call recordings | (link removed) | `CALL_RECORDING_RETENTION_DAYS` | 90 | recording |
| Website analytics events | web_events | `WEB_ANALYTICS_RETENTION_DAYS` | 395 | event |
| Lead form submissions | crm_lead_submissions | `CRM_LEAD_SUBMISSION_RETENTION_DAYS` | 730 | received_at |
| E-mail open and click events | crm_email_events | `CRM_EMAIL_EVENT_RETENTION_DAYS` | 395 | occurred_at |
| Landing page view and conversion events | crm_landing_events | `CRM_LANDING_EVENT_RETENTION_DAYS` | 395 | created_at |
| Shared-document views | crm_document_views | `CRM_DOCUMENT_VIEW_RETENTION_DAYS` | 730 | last_seen_at |
| Quote signer one-time codes | crm_quote_signer_codes | `CRM_SIGNER_CODE_RETENTION_DAYS` | 30 | expires_at |
| Unconfirmed double opt-in requests | crm_contact_consents (status PENDING) | `CRM_CONSENT_PENDING_RETENTION_DAYS` | 30 | updated_at |
| Mailgun webhook tokens | mail_webhook_tokens | none (fixed) | 10 minutes | signature timestamp |

The purge keeps the following:

- the leads themselves;
- the consent register, other than PENDING rows;
- signed quote decisions, which are evidence.

Engagement and A/B statistics only count events that are still stored, so reports on older periods shrink after the purge.

## Double opt-in

1. A web form or chat consent records a **PENDING** row.
2. It also queues a `CONSENT` e-mail through the CRM outbox. This e-mail is transactional: it has no unsubscribe footer, no tracking and is not counted against the frequency cap. At most one is sent per address per day.
3. The e-mail links to `/consent-confirm?t=…`. The token is signed and expires after `CRM_CONSENT_CONFIRM_TTL_HOURS` (default 72).
4. Opening the link changes nothing. Only the Confirm button does: it calls `POST /api/v1/public/consent-confirm`, which sets the row to **SUBSCRIBED** and stores `confirmed_at` and `confirm_ip_hash` (a keyed hash, never the raw IP).

PENDING never overwrites an existing status. Addresses that are UNSUBSCRIBED, BOUNCED or COMPLAINED stay suppressed; only an authorised staff member recording proof can lift an unsubscribe. Sequences and campaigns still require SUBSCRIBED.

## Link signing keys

Unsubscribe and confirmation links are signed with `UNSUBSCRIBE_SECRET`. If it is blank, they are signed with `SECRET_KEY`, so links that are already delivered keep working. Tokens are also verified against every key in `UNSUBSCRIBE_PREVIOUS_SECRETS` (a comma-separated list).

To rotate the key:

1. Put the old value into `UNSUBSCRIBE_PREVIOUS_SECRETS`. On the first switch this is the old `SECRET_KEY`.
2. Set a new `UNSUBSCRIBE_SECRET` of at least 32 bytes.
3. Remove the old value after about a year, when old e-mails no longer matter.

In production, `CRM_OUTBOUND_EMAIL_ENABLED=true` is refused unless both `PUBLIC_APP_URL` and `PUBLIC_API_URL` are public https URLs (not localhost).

## Anonymising the consent register (erasure requests)

The consent register is evidence of what a person agreed to and when, and it also keeps their unsubscribe effective. Rows are therefore anonymised, not deleted.

1. Verify the requester's identity, and record the request in the ticket or DPO log.
2. An administrator runs `crm_outbound_service.anonymise_consent(db, email, actor)` and then commits. This function:
   - replaces the address on the `crm_contact_consents` row with `erased-<keyed hash>@invalid`, and clears `confirm_ip_hash`;
   - keeps the status, `source`, `consent_text`, `updated_at` and `confirmed_at`;
   - clears `contact_email` on that address's `crm_lead_submissions`;
   - writes a `CONSENT_ANONYMISED` audit-log entry.
3. Delete or anonymise the person's other records (CRM contact, leads and chats) through their own screens.

Because the stored hash is keyed and deterministic, a suppression survives: if an erased person was UNSUBSCRIBED and someone later types their address into a form, the address is still treated as unsubscribed, and no confirmation e-mail is sent. The address itself cannot be read back from the hash.
