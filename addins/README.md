# CRM add-ins for Outlook and Gmail (M45.S01.T012)

Both add-ins call the same ERP API: `/api/v1/public/crm-addin`. The source for each host is:

- **Outlook:** `outlook/manifest.xml`, an XML manifest for a MailApp with a message-read task pane. The pane is the ERP page `/addin/sidebar.html?host=outlook`, served from `frontend/public/addin/`.
- **Gmail:** `gmail/`, an Apps Script Gmail add-on built with CardService.

## How a user signs in

1. In the ERP, the user goes to **My profile → Access tokens** and creates a token with the `crm.addin` scope. The token is shown only once.
2. The user pastes the token into the add-in.
   - The add-in then acts with that user's own CRM rights.
   - Revoking the token in the ERP stops the add-in right away.

## What the add-in does

- Shows the sender's CRM contact, linked deals and recent activities.
- Logs the open e-mail to a deal. The same message is logged only once.
- Adds a note or a follow-up task.
- Inserts an e-mail template into the reply.

## Local harness (no Microsoft or Google account)

Open the sidebar page directly, for example:

`http://localhost:3000/addin/sidebar.html?email=buyer@povu-demo.test&subject=Order&api=http://localhost:8000`

The query string stands in for the mail host context. `tests/test_m45_s01_t012_t022_tokens_addin_mcp.py` checks the following:
- both manifests are well-formed and declare the required elements;
- the shared API works with a real token, including scope, revocation and row-level visibility.

## Activation (owner, M47)

**Outlook**
1. Replace `https://erp.povu.example` with the ERP's public HTTPS origin.
2. Generate a new `<Id>`.
3. Either sideload the add-in (Outlook → Get Add-ins → My add-ins → Add from file), or have a Microsoft 365 admin deploy it through Integrated Apps.

**Gmail**
1. Create an Apps Script project and paste in `appsscript.json` and `Code.gs`.
2. Set `ERP_ORIGIN` and `urlFetchWhitelist`.
3. Test it through Deploy → Test deployments.
4. Publishing to Google Workspace Marketplace needs a Google Cloud project and OAuth verification.

None of these steps has been done. Both hosts are runtime-only and are deferred to M47.
