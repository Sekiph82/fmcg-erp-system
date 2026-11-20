# M39.S03.T001 — Persona gap audit (2026-11-20)

Owner request (2026-11-20): everyone who uses the app — shops, dealers and distributors ordering; delivery and field
audit; marketing; finance; accounting; production; planning; stock control; quality control and assurance — gets their
own screens, sees only what their permissions allow, and the systems they hand work to are connected.

Method: (1) a synthetic login per seeded role opened every menu entry and every workspace tab at desktop width and
recorded what was visible but refused or broken (`M39.S01` sweep, evidence table below); (2) the end-to-end hand-offs
between modules were traced in code (`grep` of the service/endpoints) and the missing ones were built and tested;
(3) roles were compared with the owner's user groups.

## 1. User groups → roles → screens

| User group | Role(s) | Main screens | State |
|---|---|---|---|
| Shop / dealer / distributor | partner portal login (`/portal`, own "POVU Shop" app) | order, pay, track, statement, claims, support | sign-up, payment by terms, M-Pesa pay, tracking with ETA added (M39.S02) |
| Moto rider / pre-seller | linked sales rep (no role) | Field App: route, check-in, order, collect | menu now shown only to linked reps/drivers/field staff |
| Delivery driver | trip driver login (no role) | Field App: My deliveries, POD | office can now set the driver's login on a trip (before: impossible) |
| Field audit | `field_auditor`, `field_supervisor` (new) | Field App audits; supervisor compliance | roles added (M38 phone run) |
| Order desk / customer service | `sales_order_desk` (new), `sales_manager`, `crm_manager` | Sales, CRM; bell notice for each new shop/field order | role + new-order notifications added |
| Marketing | `cmo`, `marketing_manager`, `brand_manager`, `trade_marketing_manager`, `digital_marketing_manager`, `ecommerce_manager`, `field_marketing_agent` | Marketing, CRM, analytics | analytics summary failed (fixed) |
| Finance | `cfo`, `finance_manager`, `scoped_finance_manager` | Finance, POS, payroll approval | 2FA enforced |
| Accounting | `accountant` (new) | Finance (journals, posting, reconciliation) | before: only managers had finance access |
| Payroll | `payroll_officer` (new) prepares; finance approves | Payroll | before: no preparer role |
| Production | `factory_manager`, `production_manager`, `production_supervisor`, `shop_floor_operator`, `maintenance_technician` | Production, shop floor, maintenance | routings/batches/QC/waste/WIP lists failed (fixed) |
| Planning | `planner` (new) | Planning, MPS, MRP | before: planning only inside production roles; MRP dashboard failed (fixed) |
| Stock control | `warehouse_manager`, `warehouse_operator`, `warehouse_picker` | Inventory, Warehouses, Warehouse Floor | floor now fed by sales shipments |
| Quality control / assurance | `quality_officer`, `quality_manager` | Quality, traceability, shelf life | traceability tab hidden from those without the right |
| Procurement | `procurement_officer`, `procurement_manager` | Procurement, supplier portal | PO list / inbound schedule failed (fixed) |
| HR / employees | `hr_manager`, `scoped_hr_manager`; every employee: My HR | HR, My HR | My HR only for linked employees |

## 2. Hand-offs between systems

| Hand-off | Before | Now |
|---|---|---|
| Shop/field order → order desk | DRAFT order waited unseen | bell notification to `sales.edit` holders |
| Shop sign-up → sales | (no sign-up) | request → staff approve → customer + account + link |
| Sales shipment → warehouse floor | floor tasks only typed by hand | "start picking" creates one scan task per line (bin with stock); scan marks the line picked, shipment PACKED |
| Trip → shop | none | portal tracking: stage + driver ETA from the trip |
| Office trip → driver's app | driver login could not be set | driver login picker (active employees / reps) |
| Payroll approval → ledger | payslips only | journal via rule `payroll/PAYROLL_APPROVED` |
| Expense approval → ledger | free-text sub-ledger only | journal via rule `expenses/EXPENSE_FINANCE_APPROVED` |
| Supplier payment → ledger | PO status only | journal via rule `procurement/SUPPLIER_PAYMENT_MADE` |
| Cycle count / stock adjustment → ledger | stock ledger only | journal via rule `inventory/STOCK_ADJUSTMENT` (shortage Dr expense / Cr inventory; surplus reversed) |
| POS counter sale → ledger (void → reversal) | POS tables only | journal via rule `pos/POS_SALE`; a void posts the reversal |
| Sales invoice, customer payment, purchase invoice, GRN valuation, landed cost → ledger | already posted | unchanged |
| MRP → purchase requisition / production order | present | unchanged |
| Production → finished-goods QC quarantine → release | present | unchanged |
| Order confirmation → credit limit check | present | unchanged |

Posting rules are configuration: until finance creates the five new rules, approval still works and the event is
logged as unposted (deliberate, so payroll/expenses are not blocked overnight). **Owner decision:** keep that, or make
the rule mandatory like sales invoices.

## 3. Still open (not built tonight)

| Gap | Why it matters | Proposed next step |
|---|---|---|
| Production consumption and finished-goods cost do not post | WIP/finished goods not in the ledger | post issue to WIP and FG receipt at standard cost |
| Scoped template roles (`scoped_finance_manager`, `scoped_hr_manager`, `read_only_auditor`, `company_admin` for finance/HR) | finance, HR, maintenance and MPS APIs take only the plain right, so an "own scope" grant cannot open them; the screens are now hidden instead of failing | build scope filtering into those APIs if branch-level finance/HR users are needed |
| Shop-floor operator live queue / machine ops | need a production-line scope assigned to the user | assign line scopes when operators are onboarded |
| Delivery (POD) does not create the invoice | cash-on-delivery shops get no invoice until office acts | owner decision: auto-invoice on delivery vs office invoices |
| Shop not told "on the way" by SMS/WhatsApp | relies on opening the app | needs SMS/WhatsApp provider credentials [!] |
| Portal prices ignore trade promotions | promotions shown to sales, not applied to shop orders | apply active promotion rules in the portal/field price |
| Employer-side payroll contributions | not in run totals → not in the ledger | add to payroll calculation, then a journal line |
| POVU range has no prices | shops cannot order the new range | owner price list [!] |
| Native App Store / Play listing | installs from the browser only | company developer accounts [!] |

## 4. Role sweep evidence

Synthetic login per seeded role (Playwright, desktop width), every menu entry and every workspace tab opened; a
problem = page visible but "Access restricted"/"Failed to load", or an API call on it answering 403/405/5xx. Run 1 was
before the fixes; the final column is the last run of each role after all fixes (full 42-role run, then re-runs of
the roles touched by the last fixes). Totals: **run 1 = 314 problems over 38 roles; final = 4 over 42 roles.**

| Role | Menu entries | Pages/tabs opened | Problems run 1 | Problems final | Remaining (reason) |
|---|---|---|---|---|---|
| `accountant` | 7 | 58 | — (new role) | 0 |  |
| `admin` | 10 | 49 | 1 | 0 |  |
| `brand_manager` | 7 | 43 | 4 | 0 |  |
| `ceo` | 29 | 196 | 5 | 0 |  |
| `cfo` | 14 | 103 | 4 | 0 |  |
| `cmo` | 12 | 100 | 4 | 0 |  |
| `company_admin` | 17 | 109 | 59 | 0 |  |
| `coo` | 26 | 174 | 5 | 0 |  |
| `crm_manager` | 8 | 54 | 14 | 0 |  |
| `cto` | 26 | 207 | 8 | 0 |  |
| `data_manager` | 24 | 170 | 11 | 0 |  |
| `digital_marketing_manager` | 7 | 43 | 4 | 0 |  |
| `ecommerce_manager` | 10 | 64 | 12 | 0 |  |
| `factory_manager` | 14 | 69 | 12 | 0 |  |
| `field_auditor` | 4 | 5 | 0 | 0 |  |
| `field_marketing_agent` | 8 | 57 | 11 | 0 |  |
| `field_supervisor` | 4 | 5 | 0 | 0 |  |
| `finance_manager` | 7 | 50 | 1 | 0 |  |
| `hr_manager` | 7 | 44 | 3 | 0 |  |
| `logistics_officer` | 9 | 35 | 0 | 0 |  |
| `maintenance_technician` | 6 | 18 | 2 | 0 |  |
| `marketing_manager` | 11 | 83 | 4 | 0 |  |
| `owner` | 35 | 269 | 3 | 0 |  |
| `payroll_officer` | 5 | 28 | — (new role) | 0 |  |
| `planner` | 11 | 80 | — (new role) | 0 |  |
| `procurement_manager` | 8 | 25 | 2 | 0 |  |
| `procurement_officer` | 8 | 25 | 0 | 0 |  |
| `production_manager` | 10 | 48 | 4 | 0 |  |
| `production_supervisor` | 12 | 60 | 5 | 0 |  |
| `quality_manager` | 8 | 34 | 0 | 0 |  |
| `quality_officer` | 11 | 55 | 6 | 0 |  |
| `read_only_auditor` | 17 | 85 | 48 | 1 | shop-floor aggregate needs a production-line scope (section 3) |
| `regional_sales_manager` | 6 | 49 | 10 | 0 |  |
| `sales_manager` | 9 | 58 | 3 | 0 |  |
| `sales_order_desk` | 8 | 57 | — (new role) | 0 |  |
| `scoped_finance_manager` | 4 | 7 | 26 | 0 |  |
| `scoped_hr_manager` | 3 | 4 | 21 | 0 |  |
| `shop_floor_operator` | 6 | 28 | 10 | 3 | shop-floor live queue / machine ops need an assigned production-line scope (section 3) |
| `trade_marketing_manager` | 10 | 67 | 9 | 0 |  |
| `warehouse_manager` | 8 | 15 | 1 | 0 |  |
| `warehouse_operator` | 7 | 14 | 0 | 0 |  |
| `warehouse_picker` | 4 | 5 | 2 | 0 |  |

The remaining problems are the documented scope limitation: the shop-floor endpoints accept a scoped user only for
the production line in their scope, and the test users have no line assigned.
