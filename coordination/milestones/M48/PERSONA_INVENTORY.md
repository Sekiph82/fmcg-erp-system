# M48 persona and identity inventory

Prepared 2026-11-26 for M48.S00.T002 (persona inventory review). Source: `6ac96f1`. This list feeds the exhaustive role/persona matrix, which is hard gate 5 in `QUALITY_RUBRIC.md` and the M52 acceptance.

## Summary

### The 42 seeded staff roles

`ROLE_DEFINITIONS` in `backend/app/db/seed.py:642` defines **42** staff roles. A script checked them against the 42 historical roles in `coordination/milestones/M40/role_menus/summary.json`: the names and the order are identical.

### Identities outside the 42

There are **50** further identities that are not among the 42 historical role logins.

| Group | Count |
|---|---|
| Field and mobile app variants | 9 |
| Staff special identities | 8 |
| Customer, distributor and shop portal realm | 13 |
| Supplier portal realm | 7 |
| Public visitors, token holders and members | 13 |
| **Total** | **50** |

These identities are reached in three ways, not by a role of their own:
- **Linking a staff login to a record**, for example a sales rep, a driver or an employee.
- **A permission inside a role**, for example a field controller or a supervisor.
- **A separate realm or token**, for example the portal, the supplier portal or a public link.

The M40 sweep only logged in once per seeded role. These 50 identities were therefore exercised only partly, by the M40.S02.T002 click-through and the M38/M39 phone tests.

### Partial variants

There are also **5 partial variants** of seeded roles: F07, F08, F10, F11 and F12. The seeded role exists, but the persona depends on a linked record or a scope.

### Excluded labels

Two kinds of role labels are data, not login identities, and are left out:
- CRM buying-committee roles (`backend/app/services/crm_abm_service.py:19`);
- chat channel member roles (`backend/app/models/messaging.py:19`).

## A. Seeded staff roles (42, all in the historical 42)

| # | Identity | Realm / login | Source (file:line) | In the 42 historical roles? |
|---|---|---|---|---|
| S01 | `owner` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:643` | Yes |
| S02 | `admin` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:647` | Yes |
| S03 | `ceo` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:691` | Yes |
| S04 | `coo` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:732` | Yes |
| S05 | `cfo` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:774` | Yes |
| S06 | `cto` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:797` | Yes |
| S07 | `cmo` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:831` | Yes |
| S08 | `data_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:873` | Yes |
| S09 | `finance_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:893` | Yes |
| S10 | `sales_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:906` | Yes |
| S11 | `procurement_officer` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:921` | Yes |
| S12 | `warehouse_operator` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:933` | Yes |
| S13 | `production_supervisor` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:945` | Yes |
| S14 | `quality_officer` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:958` | Yes |
| S15 | `logistics_officer` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:969` | Yes |
| S16 | `maintenance_technician` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:979` | Yes |
| S17 | `hr_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:989` | Yes |
| S18 | `company_admin` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1001` | Yes |
| S19 | `factory_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1012` | Yes |
| S20 | `warehouse_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1030` | Yes |
| S21 | `production_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1040` | Yes |
| S22 | `quality_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1058` | Yes |
| S23 | `procurement_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1073` | Yes |
| S24 | `regional_sales_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1084` | Yes |
| S25 | `scoped_finance_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1096` | Yes |
| S26 | `scoped_hr_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1105` | Yes |
| S27 | `read_only_auditor` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1112` | Yes |
| S28 | `shop_floor_operator` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1122` | Yes |
| S29 | `field_auditor` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1131` | Yes |
| S30 | `field_supervisor` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1135` | Yes |
| S31 | `warehouse_picker` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1139` | Yes |
| S32 | `accountant` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1144` | Yes |
| S33 | `payroll_officer` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1149` | Yes |
| S34 | `planner` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1153` | Yes |
| S35 | `sales_order_desk` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1159` | Yes |
| S36 | `marketing_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1165` | Yes |
| S37 | `field_marketing_agent` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1193` | Yes |
| S38 | `brand_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1206` | Yes |
| S39 | `trade_marketing_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1225` | Yes |
| S40 | `digital_marketing_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1240` | Yes |
| S41 | `ecommerce_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1258` | Yes |
| S42 | `crm_manager` | Staff (`/login`, seeded role) | `backend/app/db/seed.py:1274` | Yes |

## B. Field and mobile app variants of staff logins

These are not separate seeded roles. The field app is at `/dashboard/field`; its backend is `backend/app/api/v1/endpoints/field_app.py`. It chooses the screen from what is linked to the signed-in user (see the module docstring, lines 1–11).

| # | Identity | How it is resolved | Source (file:line) | In the 42? |
|---|---|---|---|---|
| F01 | Sales rep / pre-seller (on foot) | `SalesRep.user_id`, `vehicle_type=FOOT` | `backend/app/api/v1/endpoints/field_app.py:113`; `backend/app/models/field_sales.py:17` | **NO** |
| F02 | Moto rider (motorbike sales with M-Pesa STK) | `SalesRep.vehicle_type=MOTORBIKE`; moto sales API | `backend/app/models/field_sales.py:14`; `backend/app/api/v1/endpoints/moto_sales.py:62` | **NO** |
| F03 | Van seller | `SalesRep.vehicle_type=VAN`; van-sales driver `driver_id` | `backend/app/models/field_sales.py:15`; `backend/app/models/van_sales.py:98`; `backend/app/api/v1/endpoints/van_sales.py:35` | **NO** |
| F04 | Delivery driver ("my trip", POD) | `DeliveryTrip.driver_user_id` | `backend/app/models/delivery.py:43`; `backend/app/api/v1/endpoints/field_app.py:220` | **NO** |
| F05 | Fleet driver (fleet register record) | `fleet_drivers` row; must be linked to F04 | `backend/app/models/fleet.py:102` | **NO** |
| F06 | Collector (open balances; cash, M-Pesa or cheque) | Field app collections; dunning `assigned_collector_id` | `backend/app/api/v1/endpoints/field_app.py:405`; `backend/app/models/dunning.py:147` | **NO** |
| F07 | Field controller / outlet auditor | Permission `field.audit` | `backend/app/api/v1/endpoints/field_app.py:626`; `backend/app/db/seed.py:1133` | Partly (`field_auditor`) |
| F08 | Field supervisor (compliance, fraud alerts, leaderboard) | Permission `field.supervise` | `backend/app/api/v1/endpoints/field_app.py:228`; `backend/app/db/seed.py:1137` | Partly (`field_supervisor`) |
| F09 | Merchandiser (shelf check) | Field app Shelf tab after check-in | `backend/app/api/v1/endpoints/field_app.py:824` | **NO** (`field_marketing_agent` is a different marketing role) |
| F10 | Maintenance technician ("My Jobs") | Work orders assigned by user id | `backend/app/api/v1/endpoints/maintenance.py:1103` | Partly (`maintenance_technician`) |
| F11 | Shop-floor operator session (line-scoped) | Operator session on the terminal | `backend/app/api/v1/endpoints/shop_floor.py:256`; `backend/app/models/shop_floor.py:100` | Partly (`shop_floor_operator`) |
| F12 | Warehouse-floor picker (scan pick / putaway) | Permission `inventory.dispatch` | `backend/app/db/seed.py:1139` | Partly (`warehouse_picker`) |
| F13 | POS cashier session | POS session | `backend/app/api/v1/endpoints/pos.py:116` | **NO** |
| F14 | ESS employee (My HR, payslips, leave, my business card) | `Employee.user_id` resolved by `/ess-self` | `backend/app/api/v1/endpoints/ess_self.py:99`, `:225` | **NO** (any staff login can also be an ESS employee) |

## C. Staff special identities

| # | Identity | Source (file:line) | In the 42? |
|---|---|---|---|
| X01 | Impersonating admin (audited, time-boxed) | `backend/app/api/v1/endpoints/impersonation.py:29` | **NO** |
| X02 | SSO user (OIDC, and SAML when it is built) | `backend/app/api/v1/endpoints/sso.py:27` | **NO** |
| X03 | Personal access token (API client) | `backend/app/api/v1/endpoints/access_tokens.py:31` | **NO** |
| X04 | MCP server client (AI agent) | `backend/app/api/v1/endpoints/mcp_server.py:22` | **NO** |
| X05 | Company membership ADMIN / USER / VIEWER (narrows any role per company) | `backend/app/models/company.py:14` | **NO** |
| X06 | Line-scoped production operator (line-scope assignment, the 4 residual M39 findings) | `coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md` | **NO** |
| X07 | Approver in My Approvals (any role, by approval rule) | `frontend/src/app/dashboard/my-approvals` | **NO** |
| X08 | Outlook / Gmail CRM add-in user | `backend/app/api/v1/endpoints/crm_addin.py` | **NO** |

## D. Customer, distributor and shop portal realm

The portal is at `/portal` and has its own JWT realm. Sign-in is at `backend/app/api/v1/endpoints/portal_self.py:114`. Ordering is limited to OWNER and BUYER (`portal_self.py:31`). Claims are limited to OWNER, BUYER and LOGISTICS (`portal_self.py:32`).

| # | Identity | Source (file:line) | In the 42? |
|---|---|---|---|
| P01–P06 | Portal user roles OWNER, FINANCE, BUYER, LOGISTICS, VIEWER, CUSTOM | `backend/app/models/portal.py:31` | **NO** (6) |
| P07 | Account type CUSTOMER | `backend/app/models/portal.py:15` | **NO** |
| P08 | Account type DISTRIBUTOR (distributor ordering portal) | `backend/app/models/portal.py:15` | **NO** |
| P09 | Account type KEY_ACCOUNT | `backend/app/models/portal.py:15` | **NO** |
| P10 | Account type RETAILER (duka / shop, "POVU Shop" app) | `backend/app/models/portal.py:15` | **NO** |
| P11 | Account type INSTITUTIONAL | `backend/app/models/portal.py:15` | **NO** |
| P12 | Account type MIXED | `backend/app/models/portal.py:15` | **NO** |
| P13 | Shop sign-up applicant (before approval) | `backend/app/api/v1/endpoints/portal_self.py:157`; staff approval at `backend/app/api/v1/endpoints/portal.py:142` | **NO** |

The M52 matrix must cover every pairing of user role and account type that changes behaviour. At minimum:
- BUYER on a DISTRIBUTOR account;
- BUYER on a RETAILER account;
- VIEWER, which must be refused when it tries to order;
- FINANCE, for the statement and payment;
- LOGISTICS, for claims.

## E. Supplier portal realm

The supplier portal is at `/supplier` and has its own JWT realm.

| # | Identity | Source (file:line) | In the 42? |
|---|---|---|---|
| U01–U07 | Supplier users OWNER, SALES, LOGISTICS, FINANCE, QUALITY, VIEWER, CUSTOM | `backend/app/models/supplier_portal.py:22`; rights at `backend/app/api/v1/endpoints/supplier_self.py:27-29`; login at `backend/app/api/v1/endpoints/supplier_self.py:92` | **NO** (7) |

## F. Public visitors, token holders and members

None of these identities has a staff login.

| # | Identity | Source (file:line) | In the 42? |
|---|---|---|---|
| V01 | Website visitor (analytics consent and collection) | `backend/app/api/v1/endpoints/web_analytics_public.py:77` | **NO** |
| V02 | Known web identity (verified visitor) | `backend/app/models/crm.py:1241`; `backend/app/api/v1/endpoints/portal_self.py:215` | **NO** |
| V03 | Website chat visitor | `backend/app/api/v1/endpoints/chat_public.py:47`; `backend/app/models/crm.py:739` | **NO** |
| V04 | Lead-form submitter / landing-page visitor | `backend/app/api/v1/endpoints/crm_lead_forms_public.py:32`; `backend/app/api/v1/endpoints/crm_landing_public.py:34` | **NO** |
| V05 | CMS site reader, and members-only page member (portal realm account on the access list) | `backend/app/api/v1/endpoints/cms_public.py:64`, `:81`; `backend/app/models/cms.py:61` | **NO** |
| V06 | Knowledge-base / help-centre reader | `backend/app/api/v1/endpoints/kb_public.py:28` | **NO** |
| V07 | Quote or document link recipient, including the customer signer (one-time e-mail code) | `backend/app/api/v1/endpoints/documents_public.py:40`; `backend/app/api/v1/endpoints/sales_depth_public.py:26` | **NO** |
| V08 | Deal-plan (mutual action plan) buyer | `backend/app/api/v1/endpoints/deal_plans_public.py:21` | **NO** |
| V09 | Payer: payment link, or Pesapal card checkout | `backend/app/api/v1/endpoints/payment_links_public.py:2`; `backend/app/api/v1/endpoints/card_payments_public.py:48` | **NO** |
| V10 | NPS or survey respondent (one-time token) | `backend/app/api/v1/endpoints/nps_public.py:21`; `backend/app/api/v1/endpoints/service_desk_public.py:1` | **NO** |
| V11 | Meeting invitee / booking-page guest | `backend/app/api/v1/endpoints/booking_public.py:48`; `backend/app/api/v1/endpoints/meetings_public.py:14` | **NO** |
| V12 | E-mail recipient (unsubscribe and preferences) | `backend/app/api/v1/endpoints/crm_unsubscribe_public.py:27` | **NO** |
| V13 | Consumer scanning a pack QR code (`/verify/[token]`), or a business-card viewer (`/kartvizit/[slug]`) | `backend/app/api/v1/endpoints/traceability.py:529`; `backend/app/api/v1/endpoints/business_cards_public.py:65` | **NO** |

Machine callers are not UI personas, so they are not counted here. They belong to the security matrix and need signature and replay tests:
- the M-Pesa callback;
- the Pesapal IPN;
- the social webhooks;
- the public data-sync endpoint;
- the public messaging key.

## Counting rule

| Section | Counted as "not in the 42" |
|---|---|
| B | 9 (F01–F06, F09, F13, F14) |
| C | 8 |
| D | 13 (6 roles, 6 account types, 1 applicant) |
| E | 7 |
| F | 13 |
| **Total** | **50** |

The 5 "Partly" rows (F07, F08, F10, F11, F12) are reported apart from the 50. Their seeded roles are in the 42, but the M52 matrix must still exercise each linked or scoped variant.

## Gaps to carry into the M52 matrix

1. None of the 50 identities has a synthetic login in the M40 role-menu sweep. Each one needs a seeded synthetic account or link before the M52 run.
2. The moto rider, the van seller and the on-foot rep share one screen, keyed on `vehicle_type`. Each needs its own fixture to prove its vehicle-specific actions, such as the STK push and van stock.
3. The merchandiser has no seeded least-privilege role. Decide whether to add one (`field_marketing_agent` is a marketing role, not this persona).
4. The line-scoped operator (X06 / F11) needs a configured production-line scope, so that the 4 residual M39 findings are exercised.
5. The fleet driver record (F05) and the driver login (F04) are separate records, and nothing yet shows the two linked. Verify the link in the persona run.
