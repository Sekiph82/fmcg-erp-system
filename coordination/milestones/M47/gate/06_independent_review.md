# M47 final gate — independent review (2026-11-26)

**Reviewer:** a separate read-only reviewer agent (feature-dev:code-reviewer). It was given the scope and the security properties to check, not the author's conclusions.

**Scope:** commits 3077323 and ee79b2d (M47 T002, T003, T007–T011).

**Verdict:** ACCEPT_WITH_FIXES.

## Fixed in the gate

Regression tests: `backend/tests/test_m47_s01_t005_review_fixes.py`, 12 tests.

| # | Sev. | Finding | Fix |
|---|---|---|---|
| 1 | high | `/whatsapp/simulate-inbound` was live. Through it any crm/sales/marketing user could open the 24 h window and send "START" to re-opt-in a customer who had sent STOP. | Now needs roles.edit and is refused in production or outside demo mode. It no longer runs keyword handling. Simulated rows are excluded from the service window. |
| 2 | high | Form shortening and web-event workflows trusted an unverified e-mail link. That made an e-mail-existence oracle and allowed consent forgery. | `web_identities.verified_at` added (migration 0077). Only verified identities shorten forms or enrol. A signed-in portal user verifies their own e-mail (`POST /portal-self/web-identity`, called by the shop). Shortening only omits company and contact name, and never fills e-mail or phone. |
| 3 | med | CPQ draft copied the sales-order tax fraction (0.16) into a percentage field, understating tax 100×. | Converted to percent; validation allows 0..100. |
| 4 | med | Report-builder sales-order total divided a fractional discount by 100. | Uses `(1 - discount_pct)`. |
| 5 | med | Chatter scoping failed open; `/timeline`, `/stats`, AI routes and pin were unscoped. | More mappings. Unknown types need a staff right. Timeline items are filtered; stats, AI and pin are gated. |
| 6 | med | WhatsApp consent and config endpoints needed only the coarse module guard. | Needs crm.edit_all or roles.edit (read: also crm.view_all). |
| 7 | med | The JSON sanitizer re-serialised signed webhook bodies, so HMAC verification would fail in production and STOP would never arrive. | Signed webhook paths skip the sanitizer. A compact-JSON signature test passes. |
| 8 | low | Workflow-hook quota could be exhausted with a wrong token. | Per-workflow counting starts only after the token matches. |
| 12 | low | `/metrics` compare could raise on non-ASCII input. | Bytes compare. |
| 13 | low | A bundle import could switch `require_approval` off; site fields were not validated; ffmpeg input protocols were not restricted. | Approval stays on. Fields go through the CMS validators. `-protocol_whitelist file` added. |
| 15 | low | Hidden contact fields were still searchable. | Excluded from search when HIDDEN or masked. |

## Carried to the activation / follow-up register

- **9:** DMARC header trust for inbound unsubscribe/bounce. Should trust only our own authserv-id. Needs real mailbox headers to calibrate.
- **10:** recovery-code counter race under parallel requests. Should be an atomic increment.
- **11:** Slack link is self-declared; route webhook URLs are not encrypted.
- **14:** workflow enqueue caps (500/2000) drop the remainder silently.
- **16:** public video endpoints have no rate limit.
- The e-mailed one-time verification link for website visitors is not built. Only the portal sign-in verifies an identity, so anonymous website visitors get no form shortening (the safe default).

## Areas the reviewer confirmed hold

- **Allow-list:** the public route allow-list and each route's own authentication.
- **Video links:** token digest, expiry, revocation and media isolation.
- **Webhooks and Slack:** workflow-webhook token handling; Slack signature, user mapping, role and second-person rules.
- **Approvals:** `check_decider`.
- **Metrics:** labels.
- **WhatsApp and mailbox:** token encryption; STOP/START idempotency; mailbox suppression.
- **Ads:** hashing and consent.
- **Agents:** draft-only campaign agents.
- **CPQ and meetings:** CPQ draft-only quotes; meeting recap consent.
- **Imports:** contract import file handling.
- **SQL:** report-builder SQL (whitelisted fields, constant expressions).
- **Integration fixes:** bundle import never publishes; TTS stdin; POD idempotency; recall locking; service-desk guards; field rules.
