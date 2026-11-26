# M45 gate — step 5: real local app walkthrough (2026-11-26)

## Setup

- **Backend:** uvicorn on :8041 using the disposable DB `m45_walk` (head 0075 plus a synthetic POVU seed). The owner's dev DB was not used.
- **Frontend:** `next dev` on :3241 (distDir `.next-m45walk`).
- **Environment:** `PROVIDER_EGRESS=local`; no provider keys.
- **Personas (non-superusers):**
  - `synth-ops`: CRM admin, AI create/edit/approve, users.impersonate, roles.manage, sales approve, reports.admin. Finance rights were removed so that privileged 2FA does not apply.
  - `synth-rep`: crm.view/edit/create, sales.view.

## Results: synth-ops on desktop

- All 27 new GET endpoints return 200 with this session.
- **Customer success** (`01`): health 100 / healthy, missing-data labels, and the churn rule shown with low confidence while no model is trained.
- **Prospecting & data** (`02`): a city=Nairobi search ranks the trade-fair row. The evidence cites "row 1, column city". Existing customers are left out.
- **AI agents** (`03`):
  - A KB-answerer agent was created from the gallery and simulated (12 tokens, cost shown).
  - "Request publish" followed by "Approve" by the same person shows "A second person must approve an agent version."
- **Add-ins & AI access** (`04`): a crm.addin token is shown once. The Outlook sidebar harness, using that token against the real API, shows the CRM contact (`05`).

## Results: phone width (375×812)

- No horizontal overflow (scrollWidth 375) on:
  - Customer success, Prospecting & data, Custom objects, Data sync;
  - AI agents, Service desk;
  - the four Security subpages;
  - the public pay page (`06`).

## Results: synth-rep

- **Hidden tabs:** "Duplicates" and "Sensitive data" are not shown (`07`). Customer success lists only the rep's own customer.
- **Refused (403):**
  - API: dedupe, config bundles, warehouse exports, AI agents, impersonation sessions, intent settings change and impersonation start.
  - KRA PIN in the customer API is `•••67Z`, with `masked_fields: ["tax_id"]`.

## Defect found and fixed in the gate

- **What happened:** `/dashboard/security/{support-access,sso,config-sandbox,warehouse-exports}` were caught by the old `/dashboard/security` prefix redirect and sent to the admin page.
- **Fix:** the four pages were added to `BYPASS_PREFIX_REDIRECT` in `middleware.ts`.
- **Verification:**
  - re-checked in the browser: all four render, without overflow at 375 px;
  - tsc and the production build were re-run (`03_tsc_rerun.txt`, `04_build_rerun.txt`).
