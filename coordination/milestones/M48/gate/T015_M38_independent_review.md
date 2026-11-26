# T015 — Independent review of M38.S00.T001 persona/channel screen audit

- Reviewed document: `coordination/milestones/M38/M38_S00_PERSONA_SCREEN_AUDIT.md` (added in `0f9b7bf`, 2026-11-19 15:43).
- Reviewed against: the code at the audit commit `0f9b7bf` (was each claim true when it was written?) and the code at HEAD `60e360a`
  (is it still true?).
- Method: a static read only, using `git show`/`git grep` at `0f9b7bf` plus grep and file reads at HEAD. Nothing was run, no
  database was used, and no file was changed except this report.
- Reviewer: independent subagent. I did not write the audit or any M38 code.

## Verdict: **ACCEPT_WITH_FIXES**

Every claim I could check against `0f9b7bf` was true when the audit was written, with one exception: the redirect-stub count is
wrong. That count is not a blocking error. The audit is a snapshot taken before M38, and M38 has since closed most of the gaps
it lists, so most rows are now CHANGED_SINCE. That change is expected, not a defect. The fixes needed are to the document (and
are noted in TASKS); there are no code blockers:

1. Correct cross-cutting finding 3. There are **154** server-side redirect stub pages, not "about 40", both at `0f9b7bf` and at
   HEAD (153 under `/dashboard` plus the root `page.tsx`). None of them has been removed since. M38.S06.T001 reclassified them
   as deliberate hub consolidation (TASKS.md:1793), and that judgement is reasonable, but the number in both places is wrong.
2. Add a "status as of HEAD" note, or a pointer to the M38 completion rows, so readers don't take the persona matrix as current.
3. Record the personas and channels missing from the audit (see Gaps), and the residual items that are still open at HEAD.

## Counts

There are 31 material claims: 10 cross-cutting, 17 persona rows and 4 re-check greps. Each is marked against **current code**:

| Mark | Count |
|---|---|
| CONFIRMED (still true at HEAD) | 5 |
| CHANGED_SINCE (true at audit time, superseded by M38/M40 work) | 23 |
| WRONG | 1 |
| UNVERIFIABLE_STATICALLY | 2 |

At audit time (`0f9b7bf`): 28 were confirmed true, 1 was wrong (the stub count) and 2 cannot be checked statically.

## Claim table

`@A` means the file at audit commit `0f9b7bf`. Paths without a prefix are at HEAD.

### Cross-cutting findings

| # | Claim | At audit | Mark (HEAD) | Evidence |
|---|---|---|---|---|
| C1 | Portal login returns a random `token_urlsafe` that nothing validates (`portal_service.py:210`) | true | CHANGED_SINCE | @A `backend/app/services/portal_service.py:210`. At HEAD, `/portal/auth/login` is gone; sign-in is `portal_self.py:114` → `external_auth.password_login` (`backend/app/core/external_auth.py:131-140`), which issues a signed realm JWT in an HttpOnly cookie (`external_auth.py:57-61`). Residual: the old `portal_service.login` still builds a placeholder token at `portal_service.py:218-246` (comment at `:235`), but it now has **no callers** (grep `portal_service.login`/`svc.login` finds none). It is dead code. |
| C2 | Supplier portal login has the same placeholder (`supplier_portal_service.py:163`) | true | CHANGED_SINCE | @A `supplier_portal_service.py:163`. At HEAD, `supplier_self.py:92` (`/supplier-self/auth/login`) uses the external realm. The only `token_urlsafe` left in `supplier_portal_service.py:55` is the one-time invitation token, stored as a digest (`:53-67`). |
| C3 | ESS login has the same placeholder (`ess_service.py:40`) | true | CHANGED_SINCE | @A `ess_service.py:40`, and `("/ess/login","POST")` was in @A `module_registry.py` PUBLIC_ROUTES. At HEAD there is no login function in `ess_service.py`, and `/ess/login` is not in PUBLIC_ROUTES. ESS now uses the staff session through `/ess-self` (`ess_self.py:99-292`, every route `Depends(get_current_user)`). |
| C4 | Every data route behind those logins requires a staff login at router level, and none is scoped to the portal account | true | CHANGED_SINCE | @A `module_registry.py:596-600,665-674` (router-level `get_current_user`); @A `portal.py:20` `APIRouter()` had no account scoping. At HEAD, `portal_self`/`supplier_self` are registered with `external_realm=True` (`module_registry.py:490,492`, wiring at `:834-837`), so no staff dependency is attached, and every one of the 27 `portal_self` routes and 9 `supplier_self` routes takes the realm dependency `ext.get_portal_user`/`ext.get_supplier_user` (checked route by route). The staff admin routers now have `_staff_access` (`portal.py:24-33`, `supplier_portal.py:28-37`). |
| C5 | Portal passwords are unsalted SHA-256 (`portal_service.py:31-36`) | true | CHANGED_SINCE | @A `portal_service.py:31-36` uses `hashlib.sha256`. At HEAD, `portal_service.py:39-48` delegates to `security.hash_password` and `external_auth.check_password` (bcrypt, legacy SHA-256 upgraded on login: `external_auth.py:6,33`). |
| C6 | `POST /supplier-portal/auth/reset-password` sets a password from an e-mail alone, with no token; it is not public, so any ERP user can do it | true | CHANGED_SINCE | @A `supplier_portal.py:38-44`, and it was not in @A PUBLIC_ROUTES, so it sat behind the staff session as described. At HEAD there is no `reset` in `supplier_portal.py` or `supplier_portal_service.py`. Activation needs a 7-day one-time token (`supplier_portal_service.py:53-67`). Staff password links are at `supplier_portal.py:52` (permission-gated per TASKS.md:1787). |
| C7 | No screens outside the staff dashboard except `/login`, `/kb`, `/forms/[slug]`, `/unsubscribe` | true (minor omission) | CHANGED_SINCE | @A non-dashboard pages were `login`, `kb`, `kb/[slug]`, `forms/[slug]`, `unsubscribe`, the root `page.tsx` and `auth/2fa`, `auth/2fa/enroll`, `auth/change-password`. The audit left out the `auth/*` pages, which are staff-only, so its conclusion stands. At HEAD there are 33 non-dashboard pages, including `portal/{login,activate,signup}`, `portal`, `supplier/{login,activate}`, `supplier`, `verify/[token]`, `nps/[token]`, `survey/[token]`, `chat`, `book/*`, `pay/[token]`, `docs/[token]`, `d/[token]`, `plan/[token]`, `v/[token]`, `lp/[slug]`, `kartvizit/[slug]`, `site/*` and `kb/members`. |
| C8 | `dashboard/portal/*` and `dashboard/supplier-portal/*` are internal admin pages | true | CONFIRMED | They are still staff admin: `portal.py:24-33` (`sales.view`/`sales.edit`), `supplier_portal.py:28-37`. The partner-facing screens are `/portal` and `/supplier`. |
| C9 | About 40 sub-pages are redirect stubs (van-sales, supplier-portal, wms/picking, putaway, 4 qms, marketing/ecommerce, report-builder/executive, security/monitor) | **false** | **WRONG** | Static count of `page.tsx` files whose body is only a `redirect()`: **154 at `0f9b7bf`, 154 at HEAD**. 153 are under `dashboard/` and one is the root `page.tsx`; `site/[key]/page.tsx` was added and none were removed. Examples: `dashboard/wms/picking/page.tsx`, `dashboard/sales/pod/page.tsx`, `dashboard/procurement/[id]/page.tsx`, `dashboard/utilities/uom/page.tsx`, all of `dashboard/finance/accounting/*`, `dashboard/gs1/*`, `dashboard/promotions/*` and `dashboard/price-lists/*`. Every family the audit names is a stub, but the "~40" undercounts by about 4×. TASKS.md:1793 repeats "~40". |
| C10 | The PWA (M37) is for employees only, has no geolocation, no camera except the barcode button, and no offline writes | true | CHANGED_SINCE (partly) | @A: `geolocation` appears 0 times in `frontend/src`, and the only camera use is `BarcodeScanButton.tsx:27,54`. At HEAD: `lib/field.ts:25-26` uses geolocation; photo capture is at `dashboard/field/page.tsx:72` and `dashboard/maintenance/my-work/page.tsx:84`; a partner PWA manifest `public/povu-shop.webmanifest` (start_url `/portal`) exists, so the PWA is no longer employee-only. **Still true:** there are no offline writes (`public/sw.js:4,26`, where non-GET is never intercepted). |

### Persona matrix

| # | Persona — audit status | At audit | Mark (HEAD) | Evidence |
|---|---|---|---|---|
| P1 | Distributor — BACKEND-ONLY, no login/UI, drafts not priced SOs | true | CHANGED_SINCE | Login at `frontend/src/app/portal/login/page.tsx`, app at `portal/page.tsx`. Backend `portal_self.py:250` serves the catalog at server prices (`:106-109`, `:264-269`), and `:276` places orders, which become a priced DRAFT sales order with source DISTRIBUTOR (`:4-6`). Orders, invoices, statement and shipments are at `:412-480`. |
| P2 | Retailer/customer — PARTIAL, no ticket/NPS/loyalty | true | CHANGED_SINCE | Tickets: `portal_self.py:547-648` and the portal Support tab (`portal/page.tsx:353-361`). Feedback: `:676-683`. Loyalty: `:695`. Public NPS: `app/nps/[token]/page.tsx:14`, with `/public/nps/{token}` in PUBLIC_ROUTES. |
| P3 | Supplier — BACKEND-ONLY, reset has no token | true | CHANGED_SINCE | Pages: `app/supplier/{login,activate}/page.tsx` and `app/supplier/page.tsx:7` (calls `supplier-self`). Backend `supplier_self.py:131-271`: POs, acknowledge, ETA, documents and payments, all scoped to the supplier realm. |
| P4 | E-commerce buyer — MISSING by design (Shopify import) | true | CONFIRMED | `backend/app/services/shopify_service.py` exists at both commits. Note: registered shops can now self-order through the `/portal` "POVU Shop" PWA (`public/povu-shop.webmanifest`). There is still no anonymous storefront. |
| P5 | Consumer QR — BACKEND-ONLY | true | CHANGED_SINCE | `app/verify/[token]/page.tsx:18` calls `/traceability/blockchain/public/{qr}`, which is public (`module_registry.py:705`). |
| P6 | Pre-seller / rep — PARTIAL, no "my day", `logVisit` unused, no GPS/order | true | CHANGED_SINCE | `dashboard/field/page.tsx:78-155` has the route, visit with GPS (`:137-138`) and photo (`:139`), and order capture (`:155-172`). Backend: `field_app.py:234,271,294,327`. `fieldSalesApi.logVisit` is still unused but has been superseded by `/field/visits`. |
| P7 | Van sales — PARTIAL: check-in sends no GPS; no UI for visit photo, sync or day log | true | **CONFIRMED (still open)** | `dashboard/van-sales/route/page.tsx:20` still sends `vanSalesApi.checkIn(id, {})`, while `lib/van_sales.ts:227` accepts `gps_lat/gps_lng`. `vanSalesApi.sync` (`lib/van_sales.ts:255`) has 0 callers in `src/app`. Backend `van_sales.py:267` (visit photo) and `:303,368` (rep-day-log) have no frontend client. No M38 row covers this. |
| P8 | Moto sales — BACKEND-ONLY, `lib/moto_sales.ts` 0 importers | true | CHANGED_SINCE | The rider gets the "My route (moto)" tab (`dashboard/field/page.tsx:29`), with order, collect and M-Pesa STK (`:213-216`, `field_app.py:456`). The supervisor gets fraud alerts and a leaderboard (`dashboard/field/supervisor/page.tsx:8-9,25,30`, `field_app.py:777`). Residual: `frontend/src/lib/moto_sales.ts` still has 0 importers and is dead client code. |
| P9 | Field controller — MISSING, only `VisitType.TRADE_AUDIT/STORE_CHECK` | true | CHANGED_SINCE | @A/HEAD `backend/app/models/marketing.py:121,124`. At HEAD, the audit checklist, outlets, audits with photo and compliance are in `field_app.py:628-776`, with UI at `dashboard/field/page.tsx:325-380` and `field/supervisor/page.tsx:23-80`. Roles `field_auditor`/`field_supervisor` are at `seed.py:1131-1138`. |
| P10 | Merchandiser — PARTIAL, desktop market-intel, no outlet photo/planogram | true | CHANGED_SINCE (partly) | Shelf check per visit, with facings, out-of-stock, shelf price, `planogram_ok` and a photo: `dashboard/field/page.tsx:391-417`, `field_app.py:824-887`. Market-intel is still a desktop page (`dashboard/market-intelligence/page.tsx:34-35`). |
| P11 | Delivery driver — no POD capture, `createPod` never called | true | CHANGED_SINCE | "My deliveries": `dashboard/field/page.tsx:243-304`, with a signature canvas (`:267-279`), GPS (`:293`) and a fail reason (`:304`). Backend: `field_app.py:503-627`. `deliveryApi.createPod` (`lib/delivery.ts:68`) is still unused, superseded by `/field/trip-orders/{id}/deliver`. |
| P12 | Collector — PARTIAL, office only, no route list, no STK from UI | true | CHANGED_SINCE (partly) | Collect and STK in the field route: `dashboard/field/page.tsx:196-236`, `field_app.py:391-500`. Residual: collections require a SalesRep link (`field_app.py:117-121,410`), so a collector who is not a rep has no screen. |
| P13 | Factory operator — COMPLETE | n/a | UNVERIFIABLE_STATICALLY | The screens exist (`dashboard/shop-floor/terminal/page.tsx`, present at `0f9b7bf` and HEAD; PWA shortcut at `app/manifest.ts:21`). Whether they are "complete" needs a running walkthrough. |
| P14 | Warehouse picker — PARTIAL, setup only | true | CHANGED_SINCE | `dashboard/warehouse-floor/page.tsx:61-73` does scan-confirmed pick and putaway (`/wms/picking/tasks/{id}/scan-confirm`). It has a nav entry (`components/nav-config.tsx:254-258`) and a PWA shortcut (`manifest.ts:24`). Role `warehouse_picker` is at `seed.py:1139`. |
| P15 | QC/lab, procurement, finance, management, approvers, IT, POS — COMPLETE | n/a | UNVERIFIABLE_STATICALLY | A completeness judgement over many modules can't be proven statically. The pages and roles exist (`seed.py:893-1110`; `dashboard/mobile/approvals`). |
| P16 | Maintenance technician — COMPLETE (desktop), no mobile "my work orders" | true | CHANGED_SINCE | `dashboard/maintenance/my-work/page.tsx` (added in `438e2b4`, M40.S01.T002; absent at `0f9b7bf`), with nav "My Jobs" at `nav-config.tsx:272`. |
| P17 | ESS — PARTIAL, 7 pages hard-code `DEMO_EMPLOYEE`, no payslip | true | CHANGED_SINCE | `DEMO_EMPLOYEE`: 7 files at `0f9b7bf`, 0 at HEAD. "My payslips" is at `dashboard/ess/payslips/page.tsx:12`, using `ess_self.py:225`. Nav is at `nav-config.tsx:243-250`. |

### Re-check evidence line

| # | Audit grep | At audit | Mark (HEAD) | Result |
|---|---|---|---|---|
| R1 | `grep -rln DEMO_EMPLOYEE frontend/src/app` → 7 | 7 ✔ | CHANGED_SINCE | 0 |
| R2 | `grep -rl moto_sales frontend/src --include=*.tsx` → 0 | 0 ✔ | CONFIRMED | 0. Moto UI now calls `/field/moto` and `/moto-sales/fraud/...` directly. |
| R3 | `grep -rn "createPod\|logVisit" frontend/src/app` → 0 | 0 ✔ | CONFIRMED | 0. Superseded by the `/field/*` client. |
| R4 | `token_urlsafe` at the three login sites | ✔ | CHANGED_SINCE | See C1–C3. |

## Gaps

### Personas and channels present in the code but missing from the audit

These were present at `0f9b7bf` unless marked "post-audit".

1. **Field marketing agent.** Role `field_marketing_agent` (`seed.py:1193`) for customer visits and surveys. It is not in the matrix. The nearest row is "Merchandiser", but this role has no field-app screen of its own (the field app is gated on SalesRep, driver or `field.audit`).
2. **Marketing back-office personas.** `marketing_manager`, `brand_manager`, `trade_marketing_manager`, `digital_marketing_manager`, `ecommerce_manager` and `crm_manager` (`seed.py:1165-1274`) are not listed, not even in the "COMPLETE" catch-all row.
3. **Logistics officer / dispatcher.** Role `logistics_officer` (`seed.py:969`) plans the trips that drivers execute. It is not listed.
4. **Read-only / internal auditor.** Role `read_only_auditor` (`seed.py:1112`). It is not listed.
5. **Regional sales manager.** Role `regional_sales_manager` (`seed.py:1084`), the scoped manager of reps. It is only implied by "Manager view".
6. **Order desk** (post-audit). Role `sales_order_desk` (`seed.py:1159`) confirms the DRAFT orders created by the distributor portal and the field app. It belongs in the persona list now.
7. **WhatsApp channel.** The `whatsapp` module was registered at `0f9b7bf`, with a public webhook in PUBLIC_ROUTES. A customer channel, not assessed.
8. **M-Pesa payer channel.** Public callbacks `/integrations/mpesa/callback`, `/sales/mpesa/callback` and `/moto-sales/mpesa/callback` were in @A PUBLIC_ROUTES. The payer is an external actor the audit doesn't mention.
9. **Third-party developer / integrator.** `api_portal` is at `/developer` (`module_registry.py:607`, also at `0f9b7bf`). Not listed.
10. **Post-audit public channels.** These now exist and would need a row in any refreshed audit: booking (`/book`), live chat (`/chat`), payment links (`/pay`), shared documents and quotes (`/docs`, `/d`), deal plans (`/plan`), video messages (`/v`), business cards (`/kartvizit`), landing pages and CMS site (`/lp`, `/site`), surveys (`/survey`), KB members (`/kb/members`), and the MCP and Slack endpoints.

### Residual issues still open at HEAD

These were found while verifying. None blocks this review.

- **Van sales (P7) is unchanged.** Check-in still sends no GPS (`van-sales/route/page.tsx:20`), and the backend visit photo, rep-day-log and sync endpoints have no UI. No M38 or later row tracks this.
- **Collector-only persona (P12).** Collections need a SalesRep link (`field_app.py:117-121`), so a dedicated cash collector can't use the field app.
- **Dead code** (mention only, not deleted): the placeholder-token `portal_service.login` (`portal_service.py:218-246`, no callers), `frontend/src/lib/moto_sales.ts` (0 importers) and `deliveryApi.createPod` (`lib/delivery.ts:68`, 0 callers). The first is the riskiest to leave in place, because a future caller would bring the unvalidated token back.
- **Stub count.** "~40" in the audit and in TASKS.md:1793 should read about 154.

## Not verified (needs a running app)

- Whether the screens actually render and complete their flows for each role, especially P13, P15 and the "COMPLETE" judgements.
- GPS and camera permission behaviour on real devices, and the cookie and CSRF behaviour of the realm sign-in in a browser.
