# POVU ERP — CRM guide (M36, updated 2026-11-21)

The CRM is part of the ERP: customers, sales orders, invoices, the distributor/shop portal and the field app share
one database. External CRMs (HubSpot, Salesforce, Zoho) are optional future connectors, never required.

## Feature matrix

| Area | Screen | Who | Live provider needed? |
|---|---|---|---|
| Pipeline, leads, opportunities, quotes | CRM → Pipeline / Quotes | sales | no |
| Unified inbox (e-mail, WhatsApp, tickets, website chat) | CRM → Inbox | sales, support | WhatsApp: Meta keys |
| Two-way e-mail (IMAP/SMTP per mailbox) | Communication → Email | everyone with a mailbox | a mailbox (Gmail/Microsoft 365 app password); OAuth sign-in is a live gate |
| Meetings + calendar invites + ICS feed | Communication → Meetings | sales | Google/Microsoft calendar sync is a live gate |
| Lead forms (public) | CRM → Lead forms; `/forms/<slug>` | marketing | no |
| Landing pages + A/B tests (public) | CRM → Landing pages; `/lp/<slug>` | marketing | no |
| Sequences, segment campaigns (consent-aware outbox) | CRM → Sequences / Campaigns | marketing | SMTP for delivery |
| Account-based marketing (key accounts) | CRM → Key accounts | key-account / marketing | SMTP for delivery |
| Automation rules + visual workflow designer | CRM → Automation / Workflows | CRM admins (publish: `crm.approve`) | no |
| AI copilot (customer brief, next steps) | Customer page | sales | AI key (Claude) — set |
| Attribution report | CRM → Attribution | managers | no |
| Quote share links + e-signature (accept/decline) | Quotes → Share | sales | third-party e-sign provider is optional |
| Website live chat + help-article bot | `/chat` (embed), CRM → Inbox | support | no |
| Telephony: click-to-call, call log, consent, retention | Communication → Calls | sales | a voice provider for server-side dialling/recording |
| Conversation insights (calls with consent, staff chats) | CRM → Conversation insights | reps (own), managers (all + review) | optional AI key; switch `CONVERSATION_INTELLIGENCE_ENABLED` |
| Customer NPS + loyalty points | Portal → Feedback / My points; NPS → "Send to a customer" | customers, CRM | no |
| Integration console | Integrations → Console | admins | each connector's own keys |

## Consent and privacy policy (what the code enforces)

- Marketing e-mail goes only through the outbox, which checks the contact's consent and suppression list; contacts
  without consent are recorded as suppressed, never sent. Unsubscribe links are honoured.
- Lead forms and landing pages store consent text and time; bots (honeypot) are discarded and never counted.
- Landing-page visitors are identified only by a keyed hash of a random browser id; raw ids/IPs are not stored.
- Calls: a recording link is accepted only with the other party's consent, kept 90 days
  (`CALL_RECORDING_RETENTION_DAYS`) and purged daily; transcripts need `CALL_TRANSCRIPTION_ENABLED` and consent.
- Conversation insights are off by default; findings are verbatim quotes from the conversation, no scores.
- Website chats are kept 12 months after they end; bot-only chats are removed after a week of silence.
- Copilot redacts e-mails, phone numbers, KRA PINs and national ids before anything reaches the AI provider.

## Provider setup (administrators)

| Provider | Where | Settings |
|---|---|---|
| Outgoing e-mail (SMTP) | Integrations → Provider keys → Outgoing e-mail | host, port, user, password, from |
| Mailboxes (IMAP/SMTP) | Communication → Email → Connect | per user; Gmail/Microsoft need an app password |
| WhatsApp Business | Integrations → Provider keys → WhatsApp | Meta phone number id, token, verify token |
| SMS | Integrations → Provider keys → SMS | Twilio or Africa's Talking |
| M-Pesa (Daraja) | Integrations → Provider keys → M-Pesa | shortcode, consumer key/secret, passkey, environment |
| AI (Claude) | backend `.env.development` / production env | `ANTHROPIC_API_KEY` |
| Web Push (phones) | automatic | VAPID key is generated once and stored encrypted |
| Shopify | backend env | `SHOPIFY_SHOP_DOMAIN`, `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_CUSTOMER_ID` |

The Integration console shows for every connector whether credentials are set (never the values), the last
successful run, failures in a row with the next retry time, and lets administrators run a manual sync.

## Live gates (need the owner's accounts — not testable locally)

Gmail / Microsoft OAuth mailbox sign-in · Google / Microsoft calendar sync · a third-party e-signature provider ·
a voice provider (server-side dialling, recording, transcription) · Meta WhatsApp keys · SMTP relay for production ·
ClamAV on the deployment host (`DOCUMENT_CLAMAV_HOST`) · `FORWARDED_ALLOW_IPS` behind the production proxy.

## Release notes — 2026-11-21

- Security: every API module without its own checks now needs a right in that module; approve/post/pay actions need an
  approval right; customer payments need finance; appraisals, approvals, chatter and calendar follow ownership.
- New: integration console, customer NPS + loyalty in the portal, one-time survey links, loyalty points on paid
  invoices, technician "My Jobs", warehouse scanning (goods receipt, stock moves, counts), merchandiser shelf checks,
  Web Push to installed phones, account-based marketing, landing pages with A/B tests, conversation insights,
  visual workflow designer, record pickers instead of pasted ids on ~90 form fields.
