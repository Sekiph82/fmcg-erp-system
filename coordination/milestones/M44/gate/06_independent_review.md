# M44 gate — step 6: independent review (2026-11-26)

- **Reviewer:** a separate code-review agent with read-only access. It did not see the implementer's conclusions.
- **Scope:** M44.S01.T001–T014: services, endpoints, the 0074 migration against the models, public webhooks, the analytics SDK, and the frontend API paths.
- **Verdict:** ACCEPT_WITH_FIXES.

## Confirmed good

- The 0074 SQL matches the ORM models. Unique-constraint names exist for every `ON CONFLICT`.
- Webhooks:
  - Meta, Mailgun, SendGrid and generic all use constant-time compare.
  - All of them fail closed without a secret.
  - There is a replay window and the events are deduplicated.
- Live ad publishing always returns 403. Social publishing needs both the flag and a token.
- All egress goes through `provider_client`.
- Ads, social and campaigns need a second-person approval.
- The designer escapes HTML and allows only http(s) links.

## Findings and disposition

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | high | Messaging UI paths missed `/api/v1`, so it returned 404 | **Fixed**: paths corrected; verified in the browser |
| 2 | med | Custom-channel dedupe was global: two channels with the same message_id lose a message | **Fixed**: `external_id = in-<key>:<id>`, `message_id` ≤ 70; regression test (second channel, same id, stored) |
| 3 | med | Audience export did not re-check consent after an unsubscribe | **Fixed**: export intersects with current SUBSCRIBED; regression test |
| 4 | med | Withdrawing marketing consent kept the visitor↔e-mail link; identities and consents never expired | **Fixed**: withdrawal deletes the identity; retention purge removes stale identities and consents; regression test |
| 5 | med | `publish_due` could double-post with several workers (locks released by per-post commit) | **Fixed**: one post per transaction (`FOR UPDATE SKIP LOCKED LIMIT 1`, then publish, then commit) |
| 6 | med | Slack approval notices forwarded free-text titles (possible PII) | **Fixed**: only the item kind plus "Open My Approvals" |
| 7 | low | Custom outbox marks DELIVERED before the client acks | Deferred to M45 (ack endpoint); documented |
| 8 | low | FK→422 message misleading for a blocked DELETE | **Fixed**: message covers both cases |
| 9 | low | Export allowed from CANCELLED; listening items without id deduped as "None" | **Fixed**: export only APPROVED/FAILED/EXPORTED (not "may have posted"); `_store` skips missing ids |
| 10 | low | Mailgun list body → 500; Meta verify with non-ASCII token → TypeError | **Fixed**: 400 on a bad payload; bytes compare |
| 11 | low | Concurrent identical idempotency keys → 500; stale `approved_by` on re-request | Deferred to M45 (IntegrityError → return existing row) |
| 12 | low | DMs stored for registered channels regardless of the listening opt-in; Meta paging without a page cap | Documented: DMs are direct messages to the business, not listening. Paging cap deferred to M45 |
| 13 | low | Variant B skipped the placeholder check | **Fixed**: variant B subject and body are checked too |

After the fixes:
- The DB-gated M44 files pass 9/9, and the touched files including M43 pass 5/5.
- The full backend suite is green.
