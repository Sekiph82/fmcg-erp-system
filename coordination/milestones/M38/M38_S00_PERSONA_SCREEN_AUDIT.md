# M38.S00 — Persona / channel screen audit (2026-11-19)

> **Status note (M48.S01.T024, 2026-11-26): this matrix is the pre-M38 state (commit `0f9b7bf`), not current.**
> Most rows were closed by M38/M40 work; see the independent review
> `coordination/milestones/M48/gate/T015_M38_independent_review.md` for the per-claim status at HEAD. Corrections:
> finding 3 should read about **154** redirect stubs, not "~40". Closed by T024: van-sales check-in now sends GPS with
> accuracy, and visit photo, rep day log and offline sync have UI; a cash collector without a SalesRep link gets the
> field-app collector screen (open dunning cases assigned to them); the dead `portal_service.login`,
> `lib/moto_sales.ts` and `deliveryApi.createPod` were removed. The personas and channels missing here (field
> marketing agent, marketing back-office, logistics officer, read-only auditor, regional sales manager, order desk,
> WhatsApp, M-Pesa payer, developer/integrator, post-audit public channels) are carried into the M52 persona inventory.

Owner question: "Who has modules in the app, and are their screens complete? Distributors, field controllers,
motorised teams — every team that should benefit needs its own screen."

Method: read-only sweep of `backend/app/api/v1/endpoints`, `backend/app/core/module_registry.py` and
`frontend/src/app` (helper agent), with the key claims re-checked by hand (grep evidence below).

## Cross-cutting findings

1. **External logins don't work.** Portal (`portal_service.py:210`), supplier portal (`supplier_portal_service.py:163`)
   and ESS (`ess_service.py:40`) login return a random `token_urlsafe` string that nothing validates. Every data route
   behind them requires an ERP staff login (router-level `get_current_user`), and nothing is scoped to the portal
   account. Portal passwords are unsalted SHA-256 (`portal_service.py:31-36`).
   `POST /supplier-portal/auth/reset-password` (`supplier_portal.py:38`) sets any supplier user's password from an
   e-mail address alone, with no reset token. It is not public, so any ERP user can do it.
2. **There are no screens outside the staff dashboard.** Apart from `/login`, `/kb`, `/forms/[slug]` and `/unsubscribe`,
   every page is under `/dashboard` (staff JWT). `dashboard/portal/*` and `dashboard/supplier-portal/*` are internal
   admin pages, not the distributor's or supplier's own.
3. **About 40 sub-pages are redirect stubs** into tabbed hubs: van-sales, supplier-portal, wms/picking, putaway,
   four qms pages, marketing/ecommerce, report-builder/executive and security/monitor.
4. **The PWA (M37) is for employees only.** It has no geolocation or camera capture except the barcode button, and
   no offline writes (a deliberate M37 decision).

## Persona matrix

| Persona | Status | Gap |
|---|---|---|
| Distributor (ordering) | BACKEND-ONLY | No distributor login or UI. Auth is a placeholder. Draft orders don't become priced sales orders. |
| Retailer / customer (tickets, NPS, loyalty) | PARTIAL | Only the public KB and lead forms exist. A customer can't open or track a ticket, answer NPS, or see loyalty points. |
| Supplier | BACKEND-ONLY | No supplier login or UI. Auth is a placeholder. Password reset has no token. |
| E-commerce buyer | MISSING (by design) | The Shopify connector imports orders (M17), so no own storefront is needed. |
| Consumer QR authenticity | BACKEND-ONLY | Public `/traceability/blockchain/public/{qr}` exists, but there is no page for it. |
| Pre-seller / sales rep | PARTIAL | Manager view only. No "my day" screen. `fieldSalesApi.logVisit` is unused. No GPS or order capture. |
| Van sales | PARTIAL (best covered) | Check-in sends no GPS (`van-sales/route/page.tsx`). Visit photo, sync and day log have no UI. |
| Motorised (moto) sales | BACKEND-ONLY | `lib/moto_sales.ts` has 0 importers, so STK push, fraud alerts and the leaderboard have no UI. There is no rider screen. |
| Field controller / supervisor | MISSING | Only `VisitType.TRADE_AUDIT/STORE_CHECK` exist. No audit checklist, scoring or route-compliance view. |
| Merchandiser | PARTIAL | Market-intel is a desktop form. No outlet-by-outlet photo or planogram flow. |
| Delivery driver (POD) | BACKEND-ONLY for the driver | `deliveryApi.createPod` is never called. No signature, photo or GPS capture. No "my trip" screen. |
| Collector (cash / M-Pesa) | PARTIAL | Office collections screen only. No route list. No STK push from the UI. |
| Factory operator | COMPLETE | Terminal, dispensing and scan-to-consume (M37). |
| Warehouse picker | PARTIAL | Setup screens only. No pick, putaway or short-pick execution (the M37.S04.T008 scanner extension is open). |
| QC / lab, procurement, finance, management, approvers, IT, POS | COMPLETE | Minor redirect stubs only. |
| Maintenance technician | COMPLETE (desktop) | No "my work orders" mobile view. |
| Employee self-service (ESS) | PARTIAL, demo-wired | 7 ESS pages hard-code `DEMO_EMPLOYEE` instead of the logged-in user's `Employee.user_id`. No payroll payslip download. |

Re-check evidence: `grep -rln DEMO_EMPLOYEE frontend/src/app` → 7 files; `grep -rl moto_sales frontend/src --include=*.tsx`
→ 0; `grep -rn "createPod|logVisit" frontend/src/app` → 0; `token_urlsafe` at the three login sites listed above.

## Build order (M38)

1. Shared external-realm auth: a signed JWT per realm (portal / supplier), an HttpOnly cookie, salted hashes with an
   upgrade on login, a rate limit, an account-scoped dependency, and a fix for the supplier reset password.
2. Distributor ordering portal: catalog with server-side prices, place order → priced DRAFT sales order, status,
   invoices/statement, reorder.
3. Field app "my day" screens on the M37 PWA, with GPS and photo:
   - rep / pre-seller visit + order;
   - moto rider (sell, M-Pesa STK, day summary);
   - delivery driver (my trip, POD signature/photo);
   - collector.
4. Field controller: route/outlet audit checklist, scoring, rep compliance.
5. ESS bound to the logged-in user, plus my payslips.
6. Supplier portal UI (POs, acknowledge, ETA, documents).
7. Customer ticket/NPS portal, warehouse pick/putaway execution, the consumer QR page, and replacing the redirect stubs.
