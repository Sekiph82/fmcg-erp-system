# CRM add-ins for Outlook and Gmail (M45.S01.T012, M50.S01.T011)

Both add-ins call the same ERP API: `/api/v1/public/crm-addin`. The source for each host is:

- **Outlook:** `outlook/manifest.xml` (a template; `build.py` turns it into a real manifest), an XML manifest for a MailApp with a message-read task pane. The pane is the ERP page `/addin/sidebar.html?host=outlook`, served from `frontend/public/addin/`. Office.js is used for the host context: sender, subject, message id, conversation id, body, reply form, dialog.
- **Gmail:** `gmail/`, an Apps Script Gmail add-on built with CardService (`Code.gs`, `appsscript.json`).

## Build the files for an ERP

```
python addins/build.py --app-origin https://erp.example.com [--api-origin https://api.erp.example.com] --out dist/addins
```

This writes `outlook/manifest.xml`, `gmail/appsscript.json`, `gmail/Code.gs` and `build-manifest.json` (origins, Outlook id, SHA-256 of every file). It refuses (exit 1, writes nothing) when:
- an origin is not https (`--allow-local` permits `http://localhost` for harness builds), has a path, query, credentials or wildcard, or is still the template placeholder;
- the Outlook permission is broader than `ReadItem`, or any manifest URL or `AppDomain` is outside the ERP origins;
- a Gmail OAuth scope is outside the reviewed list, or the fetch allow-list is not exactly the API origin;
- `Code.gs` builds a URL carrying a token, code or verifier, or uses dynamic code execution.

The Outlook `<Id>` is derived from the origin, so a redeploy updates the same add-in.

## How a user signs in (no pasted tokens)

The ERP is its own OAuth 2.0 server for the add-ins: authorization code with PKCE (S256).

1. The add-in makes a code verifier and opens the ERP consent page `/addin/authorize` (Outlook: an Office dialog; Gmail: a browser tab opened from the card).
2. A signed-in ERP user presses **Allow** (and may untick "log e-mails, notes and tasks" to give look-up only).
3. The one-time code (60 seconds) goes to the add-in: Outlook by `messageParent` to the exact origin that asked; Gmail is shown on the page and typed into the card. It is useless without the add-in's verifier.
4. The add-in exchanges code + verifier for a 15-minute access token and a rotating 8-hour refresh token (`povua_...`, `povur_...`; only hashes are stored). Tokens travel only in the `Authorization` header and JSON bodies, never in a URL.

Controls: every request must carry `X-Addin-Host: gmail|outlook` equal to the grant's host; an Outlook grant is also bound to its origin; a refresh token used twice revokes the whole grant; the user can revoke any sign-in under **CRM -> Add-in sign-ins** (a superuser can revoke anyone's); signing out in the add-in revokes it; a disabled user's tokens stop at once; scopes are `addin.read` and `addin.write` and write is only granted to users who may edit the CRM. Mail text is cleaned (markup and control characters removed, lengths capped) before it is stored and rendered only as text. A personal access token with the `crm.addin` scope still works for scripts but is no longer how the add-ins sign in.

## What the add-in does

- Shows the sender's CRM contact, linked deals, recent activities and what was already logged from the same conversation.
- Logs the open e-mail to a deal (the same message is logged once). Adds a note or a follow-up task.
- Opens a reply (Outlook) or creates a reply draft (Gmail) with an e-mail template, as plain text.

## Local host harness (no Microsoft or Google account)

- **Outlook:** with the ERP running locally, open `http://localhost:3000/addin/harness.html?host=harness`. It stands in for Outlook (a fake open e-mail on the left, the real sidebar on the right). **Sign in** opens the real consent page in a window. The harness only runs on localhost.
- **Gmail:** `node addins/harness/gmail_host.js <built Code.gs> <scenario.json>` runs the real `Code.gs` with stand-ins for CardService, PropertiesService, GmailApp and Utilities; `UrlFetchApp` makes real loopback HTTP requests to a running ERP. `backend/tests/test_m50_s01_t011_addin.py` drives it end to end: sign-in, contact card, log, note, reply draft, token refresh, sign-out.

## Activation (owner, later)

Not done and not needed for the harness: sideloading the built Outlook manifest (Outlook -> Get Add-ins -> My add-ins -> Add from file) or a Microsoft 365 admin deployment; creating the Apps Script project from the built Gmail files and a Test deployment; any marketplace listing (needs a Google Cloud project and OAuth verification, Microsoft partner validation). The ERP origin must be public https and must be in the consent page's allow-list (`PUBLIC_APP_URL`, plus `ADDIN_ALLOWED_ORIGINS` if different).
