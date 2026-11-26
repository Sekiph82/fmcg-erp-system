# M48.S01.T011 — Reconciliation of historical `[v]` rows

Prepared 2026-11-26 against source `6ac96f1` (TASKS.md working copy with the owner's uncommitted edits). Proposal only: no row state in TASKS.md was changed.

## Method

- **Recount.** Every line matching `^\s*- \[v\]` in TASKS.md was counted: **104** rows.
  - 103 historical rows plus `M48.S00.T001`, which was added on 2026-11-26.
  - One historical row has no ID (line 1683, the live AI-provider acceptance). It is listed as `LIVE-AI (line 1683)`.
- **Evidence.**
  - Every path named in the row text, or mapped here, was checked on disk. The script marks any missing path as **(MISSING)**; 0 remain.
  - Commits come from `git log --oneline --grep <ID>`, from SHAs in the row text, and from keyword searches. Every SHA listed was verified with `git cat-file -e`.
- **Gate coverage check.**
  - The M43–M47 gate DB runners (`coordination/milestones/M4[3-7]/gate/run_*_db_tests.sh`) ran only `tests/test_m43_*` … `test_m47_*`.
  - The exception is `M46/gate/run_m46_regressions.sh`, which also re-ran `test_m36_s03_customer_timeline_db.py` and `test_m36_s04_t005_kb_db.py`. Both passed in `02_regressions_rerun.txt`.
  - The M47 full suite reported 1841 passed and 537 skipped. The skipped tests include every legacy DB-gated file named below.
  - Therefore no other legacy `[v]` row has been accepted by a gate under the 2026-11-25 protocol.
  - The claimed 2026-11-21 run of "157/157 DB files" (rows M36.S06.T001 and M40.S03.T002) has no stored log in `coordination/`.

## Disposition key

| Disposition | Meaning |
|---|---|
| LOCAL_SOFTWARE_ACCEPTED_BY_GATE | A consolidated gate under the current protocol actually exercised the row (gate path given). |
| NEEDS_M48_GATE_RETEST | Software and evidence exist, but no current gate covered it. The named tests and/or manual UI checks must run in M48.S02.T001 or M48.S01.T012; mobile and persona rows also go into the M52 matrix. |
| ACTIVATION_ONLY [D] | Needs a real external account or key; the local software is complete. |
| REMEDIATION_NEEDED | Evidence or test gap, stated in the note. A new remediation ID is needed before the row can become `[x]`. |

## Summary

| Disposition | Rows |
|---|---|
| LOCAL_SOFTWARE_ACCEPTED_BY_GATE | 3 |
| NEEDS_M48_GATE_RETEST | 93 |
| ACTIVATION_ONLY [D] | 3 |
| REMEDIATION_NEEDED | 5 |
| **Total** | **104** |

**Proposed remediation IDs.** Add these under M48.S01.T011:
- **R1: missing permission test.** No regression test checks that the three mobile admin endpoints (M37.S03.T002) refuse unauthorized users.
- **R2: missing scan test.** No DB test covers scan selection in GRN, stock transfer and cycle count (M37.S04.T008 = M40.S01.T003).
- **R3: missing review report.** No independent-review report for M36 was stored (M36.S06.T003).
- **R4: unreviewed audit.** The M38.S00 persona audit never had its independent review (M38.S00.T001).

**Retest bundle for M48.S01.T012:** every `backend/tests/test_m3[6-9]_*`, `test_m4[0-2]_*` and `test_esign_user_signatures_db.py` file.
- Run them on fresh disposable PostgreSQL from the head template.
- Run `npm run test:pwa` and `npm run test:auth-refresh`.
- `test_m38_clamav_scan_db.py` needs a local ClamAV daemon.
- `test_m39_cbk_rates_db.py` must use a fixture, never the live CBK site.

## Per-row table

| TASKS line | ID | Short title | Commits | Tests | Evidence path | Proposed disposition | Note |
|---|---|---|---|---|---|---|---|
| 532 | M16.S02.T003 | Live-provider acceptance with real API key | — | `test_hardening.py` | — | ACTIVATION_ONLY [D] | Software path exists; live run 2026-11-20 used owner key (row text). Further live acceptance is the existing M47.S02.T008 [D] NOT_DUE. Local AI mock/masking still in M48 gate full suite. |
| 1165 | M30.S05.T002 | Live-provider tests with real keys | — | `test_m30_s05_verification.py` | — | ACTIVATION_ONLY [D] | Same as M16.S02.T003: real keys required; tracked by M47.S02.T008 [D]. |
| 1496 | M36.S01.T001 | Two-way email integration (P0) | 32bdc96 | `test_m36_s01_t001_mailbox_db.py` | — | NEEDS_M48_GATE_RETEST | IMAP/SMTP part only; Gmail/Graph moved to M43.S01.T001/T002; live mailbox = M47.S02.T002 [D]. |
| 1504 | M36.S01.T002 | Automated sales sequences (P0) | — | `test_m36_s01_t002_sequences_db.py` | `coordination/milestones/M36/screenshots/B7/` | NEEDS_M48_GATE_RETEST | No commit references the ID; legacy DB test not run in M43–M47 gates. |
| 1510 | M36.S01.T003 | Unified conversations inbox (P0) | 8533fc0 | `test_m36_s01_t003_inbox_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1516 | M36.S01.T004 | CRM workflow automation engine (P0) | — | `test_m36_s01_t004_crm_automation_db.py` | `coordination/milestones/M36/screenshots/B4/dashboard_crm_automation.png` | NEEDS_M48_GATE_RETEST |  |
| 1522 | M36.S01.T005 | Calendar and meeting scheduling (P0) | 8c7c202 | `test_m36_s01_t005_meetings_db.py` | — | NEEDS_M48_GATE_RETEST | Native part only; Google/Outlook sync moved to M43.S01.T003/T004. |
| 1532 | M36.S02.T001 | Website lead capture forms (P1) | — | `test_m36_s02_t001_lead_capture_db.py` | `coordination/milestones/M36/screenshots/B3/forms_synth-contact_filled.png` | NEEDS_M48_GATE_RETEST |  |
| 1538 | M36.S02.T002 | Lead scoring (P1) | — | `test_m36_s02_sales_intelligence_db.py` | `coordination/milestones/M36/screenshots/B2/` | NEEDS_M48_GATE_RETEST |  |
| 1544 | M36.S02.T003 | Weighted sales forecasting (P1) | — | `test_m36_s02_sales_intelligence_db.py` | `coordination/milestones/M36/screenshots/B2/` | NEEDS_M48_GATE_RETEST | Shares the M36.S02.T002 test; no quota model (row states). |
| 1550 | M36.S02.T004 | Sales funnel analytics (P1) | — | `test_m36_s02_sales_intelligence_db.py` | `coordination/milestones/M36/screenshots/B2/` | NEEDS_M48_GATE_RETEST | Shares the M36.S02.T002 test. |
| 1556 | M36.S02.T005 | Marketing campaign management (P1) | 46adfeb | `test_m36_s02_t005_campaigns_db.py`, `test_m36_s02_t005_bounce_db.py`, `test_m36_outbound_consent_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1565 | M36.S03.T001 | Sales document engagement tracking (P1) | 12bac29 | `test_m36_s03_t001_document_links_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1571 | M36.S03.T002 | Unified customer activity timeline (P1) | — | `test_m36_s03_customer_timeline_db.py` | `coordination/milestones/M46/gate/02_regressions_rerun.txt` | LOCAL_SOFTWARE_ACCEPTED_BY_GATE (`coordination/milestones/M46/gate/02_regressions_rerun.txt`) | Re-run PASS in the M46 gate regressions (DB scope). M46 gate is the accepting gate; UI retest still falls in the M52 persona matrix. |
| 1577 | M36.S03.T003 | Mobile CRM experience (P1) | 17b874e | `test_m36_s03_t003_quick_notes_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1583 | M36.S03.T004 | Visual workflow designer (P1) | d0e6d93, 2bb561c, ec757c2 | `test_m36_s03_t004_workflow_designer_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1589 | M36.S03.T005 | Live chat and chatbot (P2) | 191f7b4 | `test_m36_s03_t005_live_chat_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1597 | M36.S04.T001 | AI sales copilot (P2) | 91ff4b2 | `test_m36_s04_t001_copilot_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1603 | M36.S04.T002 | Telephony and VoIP integration (P2) | 78b0d10 | `test_m36_s04_t002_telephony_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1609 | M36.S04.T003 | Quote approval and e-signature (P2) | 9053a7c | `test_m36_s03_t001_document_links_db.py`, `test_m41_s01_db.py` | — | NEEDS_M48_GATE_RETEST | Native typed-name signature only; third-party e-sign is M48.S01.T009 (open), activation M47.S02.T006 [D]. |
| 1616 | M36.S04.T004 | Customer self-service portal (P2) | 9432197 | `test_m36_s04_t004_portal_ticket_files_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1622 | M36.S04.T005 | Customer knowledge base (P2) | — | `test_m36_s04_t005_kb_db.py` | `coordination/milestones/M46/gate/02_regressions_rerun.txt` | LOCAL_SOFTWARE_ACCEPTED_BY_GATE (`coordination/milestones/M46/gate/02_regressions_rerun.txt`) | Re-run PASS in the M46 gate regressions. |
| 1630 | M36.S05.T001 | Customer journey attribution (P2) | 91ff4b2 | `test_m36_s05_t001_attribution_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1636 | M36.S05.T002 | Landing pages and A/B testing (P2) | a35a114, 2bb561c | `test_m36_s05_t002_landing_ab_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1642 | M36.S05.T003 | Integration catalog and sync console (P2) | ada2d62, dcc344a | `test_m36_s05_t003_integration_console_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1648 | M36.S05.T004 | Conversation intelligence (P3) | 7816ca2, 2bb561c | `test_m36_s05_t004_conversation_intel_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1654 | M36.S05.T005 | Account-based marketing (P3) | 348381c, 2bb561c | `test_m36_s05_t005_abm_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1662 | M36.S06.T001 | Run full CRM regression across lead → opportunity → quote → sales orde… | — | all test_m36_*_db.py (21 files) | — | NEEDS_M48_GATE_RETEST | Claims 157/157 DB files passed 2026-11-21, but no stored run log exists in coordination/. Covered by M48.S01.T012 full legacy DB regression. |
| 1664 | M36.S06.T002 | Perform browser visual regression and screenshot walkthrough of all im… | 2fe22cd | manual browser walkthrough | `coordination/milestones/M40/crm_walkthrough/` | NEEDS_M48_GATE_RETEST | Pre-protocol walkthrough; repeat at the M48 gate for CRM pages changed since. |
| 1666 | M36.S06.T003 | Independent code/security/privacy/migration audit with separate review… | 2bb561c, 2fb95a7, ef84cd6 | `test_m40_review_fixes_db.py` | — | REMEDIATION_NEEDED | Gap: no persisted independent-review report for M36 (findings are only in commit messages). Remediation: M48 gate reviewer re-reviews M36 scope and stores the report. |
| 1668 | M36.S06.T004 | Update CRM user/admin docs, provider setup instructions, consent polic… | 5333c50 | doc review | `docs/CRM_GUIDE.md` | NEEDS_M48_GATE_RETEST | Guide predates M43–M47 CRM changes; refresh/verify at gate. |
| 1673 | ESIGN-USR.T001 | IT registers each employee's signature at hiring; it is applied automa… | 7e6b8cb | `test_esign_user_signatures_db.py` | `coordination/milestones/ESIGN/` | NEEDS_M48_GATE_RETEST |  |
| 1683 | LIVE-AI (line 1683) | Live AI-provider acceptance where a real external model is required — … | — | `test_hardening.py`, `test_m36_s04_t001_copilot_db.py` | — | ACTIVATION_ONLY [D] | Row has no ID. Live Anthropic run recorded only in row text (no stored log). Activation-only; fixes it produced must be covered by the M48 gate full suite. Note: default OPENAI_MODEL gpt-4o is deprecated per OpenAI docs (see CAPABILITY_MATRIX). |
| 1725 | M37.S01.T001 | Web app manifest (`frontend/src/app/manifest.ts`), icons (`frontend/pu… | f326770 | frontend build | `frontend/src/app/manifest.ts`, `coordination/milestones/M47/gate/04_build_final.txt` | NEEDS_M48_GATE_RETEST | Build passes in M47 gate, but installability (Chrome getInstallabilityErrors) not re-checked. |
| 1726 | M37.S01.T002 | Service worker `frontend/public/sw.js`: caches only hashed `/_next/sta… | f326770 | `frontend/tests/unit/pwa-service-worker.test.mjs (npm run test:pwa)` | `frontend/public/sw.js` | NEEDS_M48_GATE_RETEST | test:pwa not part of the M43–M47 gate commands. |
| 1727 | M37.S01.T003 | Device registration: the installed app (display-mode standalone) regis… | f326770 | manual (installed PWA) | — | NEEDS_M48_GATE_RETEST | No automated test; manual device-registration check at gate. |
| 1728 | M37.S01.T004 | Camera barcode/QR scan via native `BarcodeDetector` (`frontend/src/com… | f326770 | manual camera scan | `frontend/src/components/BarcodeScanButton.tsx` | NEEDS_M48_GATE_RETEST |  |
| 1729 | M37.S01.T005 | Verification 2026-11-19: `tsc --noEmit` 0 errors; `eslint .` 0 errors … | f326770 | tsc/eslint/build/test:pwa | `coordination/milestones/M37/screenshots/report.json`, `frontend/scripts/capture-m37-pwa-evidence.mjs` | NEEDS_M48_GATE_RETEST |  |
| 1730 | M37.S01.T006 | Live-session acceptance on phone width with a real non-admin employee … | 66bcf45 | manual phone acceptance | — | NEEDS_M48_GATE_RETEST | Manual phone acceptance; repeat inside M52 persona/mobile matrix. |
| 1743 | M37.S03.T001 | Replace `/api/v1/mobile/push/send` stub with Web Push (VAPID) for inst… | d63fdbb | `test_m37_s03_t001_web_push_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1745 | M37.S03.T002 | Lock down `/mobile/devices/stats`, `/mobile/kpis`, `/mobile/push/send`… | d63fdbb | — | — | REMEDIATION_NEEDED | Gap: no backend test asserts that /mobile/push/send, /mobile/kpis, /mobile/devices/stats refuse users without users.edit/company.edit/integrations.edit. Add a permission regression test. |
| 1747 | M37.S03.T003 | iOS camera barcode fallback (JS decoder) if iOS scanning becomes a req… | 66081d0 | manual iOS scan | — | NEEDS_M48_GATE_RETEST |  |
| 1751 | M37.S04.T001 | Executive Dashboard summary is role-gated: `GET /api/v1/dashboard/summ… | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST |  |
| 1752 | M37.S04.T002 | Universal barcode resolver `GET /api/v1/shop-floor/barcodes/resolve`: … | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST |  |
| 1753 | M37.S04.T003 | Dispensing (warehouse → order) on existing prepared-lot infrastructure… | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST |  |
| 1754 | M37.S04.T004 | Scan-to-consume at the machine `POST /api/v1/shop-floor/work-orders/{i… | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST |  |
| 1755 | M37.S04.T005 | Scan audit: every scan, accepted or rejected, writes `MATERIAL_SCAN` t… | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST |  |
| 1756 | M37.S04.T006 | Verification 2026-11-19: `tests/test_m37_s04_barcode_material_flow_db.… | f091a9b | `test_m37_s04_barcode_material_flow_db.py` | `coordination/milestones/M37/screenshots/s04/` | NEEDS_M48_GATE_RETEST | Verification row for M37.S04.T001–T005. |
| 1759 | M37.S04.T008 | Extend `ScanInput` + resolver to goods receipt, putaway, transfers and… | 79d2a3f, f0d54aa | `test_m38_s06_scan_pick_putaway_db.py` | — | REMEDIATION_NEEDED | Gap: no backend test found for GRN/stock transfer/cycle-count scan selection (only pick/putaway). Add DB test. |
| 1761 | M37.S04.T009 | Next.js 16.4.2 → 16.4.6 (+ eslint-config-next) fixes GHSA-mfr8-8qww-v7… | 9d31ed8 | frontend build/tsc/eslint | `coordination/milestones/M47/gate/04_build_final.txt`, `frontend/package.json` | LOCAL_SOFTWARE_ACCEPTED_BY_GATE (`coordination/milestones/M47/gate/04_build_final.txt`) | next 16.4.6 in package.json; M47 gate build/tsc/eslint PASS on it. npm audit re-check at M48 gate. |
| 1766 | M38.S00.T001 | Persona/channel screen audit (helper sweep + hand re-check of key clai… | — | n/a (audit) | `coordination/milestones/M38/M38_S00_PERSONA_SCREEN_AUDIT.md` | REMEDIATION_NEEDED | Gap: row text says 'Independent review pending'; never recorded. Superseded in practice by M39/M40 sweeps; close via M48 gate reviewer or M52 persona matrix. |
| 1767 | M38.S01.T001 | External-realm auth: signed per-realm JWT (portal/supplier) in HttpOnl… | 31f6642, 2d1bf00 | `test_m38_s01_distributor_portal_db.py`, `test_m38_s05_supplier_portal_db.py` | `backend/app/core/external_auth.py` | NEEDS_M48_GATE_RETEST |  |
| 1768 | M38.S01.T002 | Distributor ordering portal: login page, catalog with server-side pric… | 933bb28 | `test_m38_s01_distributor_portal_db.py` | `coordination/milestones/M38/screenshots/portal/` | NEEDS_M48_GATE_RETEST |  |
| 1769 | M38.S02.T001 | Field rep / pre-seller "my day" PWA screen: route outlets, check-in wi… | 865130e | `test_m38_s02_field_app_db.py` | `coordination/milestones/M38/screenshots/field/` | NEEDS_M48_GATE_RETEST |  |
| 1770 | M38.S02.T002 | Moto rider screen: sell, M-Pesa STK push, day summary; supervisor frau… | 865130e | `test_m38_s02_field_app_db.py` | `coordination/milestones/M38/screenshots/field/` | NEEDS_M48_GATE_RETEST | Real M-Pesa STK = activation [D]; local software retest only. |
| 1771 | M38.S02.T003 | Delivery driver "my trip": stops, POD with signature/photo/GPS, failed… | 865130e | `test_m38_s02_field_app_db.py` | `coordination/milestones/M38/screenshots/field/` | NEEDS_M48_GATE_RETEST |  |
| 1772 | M38.S02.T004 | Collector screen: route of open balances, STK push / receipt. | 865130e | `test_m38_s02_field_app_db.py` | `coordination/milestones/M38/screenshots/collections/` | NEEDS_M48_GATE_RETEST |  |
| 1773 | M38.S03.T001 | Field controller: outlet/route audit checklist, scoring, rep complianc… | 865130e | `test_m38_s02_field_app_db.py` | `coordination/milestones/M38/screenshots/field/` | NEEDS_M48_GATE_RETEST |  |
| 1774 | M38.S04.T001 | ESS bound to the logged-in user (`Employee.user_id`), remove DEMO_EMPL… | 90658ec | `test_m38_s04_ess_self_db.py` | `coordination/milestones/M38/screenshots/ess/` | NEEDS_M48_GATE_RETEST |  |
| 1775 | M38.S05.T001 | Supplier portal UI (POs, acknowledge, ETA, documents) on S01.T001 auth… | 2d1bf00, 935b7de | `test_m38_s05_supplier_portal_db.py` | `coordination/milestones/M38/screenshots/supplier/` | NEEDS_M48_GATE_RETEST |  |
| 1776 | M38.S06.T001 | Customer ticket/NPS portal; warehouse pick/putaway execution; consumer… | 79d2a3f | `test_m38_s06_scan_pick_putaway_db.py`, `test_m38_clamav_scan_db.py` | `coordination/milestones/M38/screenshots/s06/`, `coordination/milestones/M38/screenshots/warehouse/`, `docs/PHONE_ACCEPTANCE_TEST.md` | NEEDS_M48_GATE_RETEST | Several sub-parts say 'independent review pending'; later reviews recorded in the row. ClamAV test needs local clamd service. |
| 1800 | M39.S01.T001 | Role screen sweep: synthetic login per seeded role, open every visible… | c278293 | `test_m39_screen_endpoints_db.py` | `coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md`, `coordination/milestones/M40/role_menus/` | NEEDS_M48_GATE_RETEST | Role sweep must be re-run in M52 persona matrix. |
| 1801 | M39.S01.T002 | Fix the sweep's findings: menu entries and tabs gated on the permissio… | c278293, 6e0476c, faebd01 | `test_m39_screen_endpoints_db.py`, `test_m40_plain_rights_scope.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1802 | M39.S02.T001 | Shop order tracking: simple status timeline (received → confirmed → pr… | 1b42325 | `test_m38_s01_distributor_portal_db.py` | `backend/app/services/delivery_eta.py` | NEEDS_M48_GATE_RETEST | ETA covered only indirectly; verify in gate. |
| 1803 | M39.S02.T002 | Shop payment by assigned method: customer's payment method (cash on de… | 1b42325 | `test_m38_s01_distributor_portal_db.py` | — | NEEDS_M48_GATE_RETEST | Live M-Pesa = [D]. |
| 1804 | M39.S02.T003 | Shop sign-up request from the app: a shop requests an account (name, p… | 1b42325 | `test_m38_s01_distributor_portal_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1809 | M39.S02.T005 | Real prices for the POVU range: owner's interim USD list (2026-11-20, … | 8329caa | seed review | `backend/app/db/seed_catalogue.py` | NEEDS_M48_GATE_RETEST | Final price list from owner is a commissioning data item, not software. |
| 1810 | M39.S03.T001 | Persona gap audit (owner, 2026-11-20: 'many users — work very carefull… | — | n/a (audit) | `coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md` | NEEDS_M48_GATE_RETEST | Superseded by M48 PERSONA_INVENTORY + M52 matrix. |
| 1811 | M39.S03.T002 | A focused home screen per user group ('my work today': own queues, app… | c278293 | `test_m39_screen_endpoints_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1812 | M39.S03.T003 | Close the audit's missing modules and hand-offs, each as its own row a… | c278293 | `test_m39_screen_endpoints_db.py` | `coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md` | NEEDS_M48_GATE_RETEST | 4 residual findings were line-scope configuration. |
| 1814 | M39.S03.T004 | Production to the ledger and warehouse links: completing an order book… | 8329caa | `test_m39_payroll_gl_db.py` | — | NEEDS_M48_GATE_RETEST | Production journal rules referenced by test_m39_payroll_gl_db.py. |
| 1815 | M39.S03.T005 | Kenya Payroll run detail page: totals, per-employee lines, calculate /… | c278293 | `test_m39_payroll_gl_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1817 | M39.S03.T007 | Owner decisions 2026-11-20 implemented: (a) invoice at delivery (drive… | 8329caa | `test_m39_invoicing_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1818 | M39.S03.T009 | Provider keys from the app: Integrations → Provider Keys (system admin… | 0cf0032 | `test_m39_invoicing_db.py` | — | NEEDS_M48_GATE_RETEST | Real provider keys = [D]. |
| 1819 | M39.S03.T010 | Accounting rule set prepared for finance (owner 2026-11-20: "prepare i… | 3bb44d0 | `test_m39_invoicing_db.py`, `test_m39_payroll_gl_db.py` | — | NEEDS_M48_GATE_RETEST | Finance approval of rules is an owner/commissioning action. |
| 1820 | M39.S03.T011 | Employer payroll contributions: NSSF employer (= employee share), hous… | bbd20d2 | `test_m39_payroll_gl_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1821 | M39.S03.T012 | USD rate from the Central Bank of Kenya (129.99 KES, posted 19-11-2026… | 89378cf | `test_m39_cbk_rates_db.py` | — | NEEDS_M48_GATE_RETEST | The rate entry itself is dev-DB data; software path = M39.S03.T013. |
| 1822 | M39.S03.T013 | KES rates kept current by the system (owner 2026-11-20): `cbk_rates.py… | 89378cf | `test_m39_cbk_rates_db.py` | — | NEEDS_M48_GATE_RETEST | Live CBK scrape is external; test must use a local fixture. |
| 1823 | M39.S03.T014 | Rule set shown to finance on sign-in: while the rule set is not approv… | 3bb44d0 | manual finance sign-in | — | NEEDS_M48_GATE_RETEST |  |
| 1824 | M39.S03.T015 | iPhone retest fixes (owner screenshots 2026-11-20): page bottom hidden… | 44c9a66 | manual iPhone | — | NEEDS_M48_GATE_RETEST |  |
| 1825 | M39.S03.T016 | Sales invoices follow the "mandatory once approved" switch: before fin… | 3bb44d0 | `test_m39_invoicing_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1826 | M39.S03.T017 | Phone test steps 10–12 passed on iPhone (portal order WEB-261120-C933D… | f47c365 | manual iPhone | — | NEEDS_M48_GATE_RETEST |  |
| 1827 | M39.S03.T018 | Owner 2026-11-20: on a phone every button/tab is visible without a sid… | — | Playwright phone sweep | — | NEEDS_M48_GATE_RETEST | Sweep script/result not stored in coordination/; re-run in M52 mobile matrix. |
| 1835 | M40.S01.T001 | Customer NPS / survey answering from the partner portal and a public o… | ee911c4, 3fd6ef1 | `test_m40_s01_t001_feedback_loyalty_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1837 | M40.S01.T002 | Maintenance technician "my work orders" phone screen: assigned/open wo… | 438e2b4, f0d54aa | `test_m40_s01_t002_technician_jobs_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1839 | M40.S01.T003 | Warehouse scanner extension (= M37.S04.T008): goods receipt, transfers… | 79d2a3f | `test_m38_s06_scan_pick_putaway_db.py` | — | REMEDIATION_NEEDED | Same gap as M37.S04.T008 (no GRN/transfer/cycle-count scan test). |
| 1841 | M40.S01.T004 | Merchandiser flow in the field app: outlet-by-outlet shelf check (faci… | 79d2a3f | `test_m40_s01_t004_shelf_check_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1843 | M40.S01.T005 | Remove the legacy ESS login/account code (SHA-256, unused token); ESS … | 79d2a3f | `test_m38_s04_ess_self_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1845 | M40.S01.T006 | Redirect stubs: confirm each of the 153 old addresses lands on a worki… | — | `frontend/scripts/validate-manual-routes.mjs (partial)` | — | NEEDS_M48_GATE_RETEST | Live redirect check result not stored; re-run. |
| 1847 | M40.S02.T001 | Workflow linkage audit (strict): every backend module has a screen; ev… | 443fc1d, ef84cd6, 2fb95a7, c2fbda2, 159a59f | `test_m40_s02_t001_approval_inbox_db.py`, `test_m40_s02_t001_lookup_db.py`, `test_m40_s02_t001_route_guard_db.py`, `test_m40_review_fixes_db.py` | — | NEEDS_M48_GATE_RETEST |  |
| 1849 | M40.S02.T002 | Live click-through of every persona (owner, sales, field rep, moto rid… | 1450cd5 | manual persona click-through | `coordination/milestones/M40/role_menus/` | NEEDS_M48_GATE_RETEST | Shopify live import is [!]/[D]; persona re-run = M52. |
| 1851 | M40.S03.T001 | Open rows from earlier milestones completed in this sweep (not externa… | 66081d0 | see listed rows | — | NEEDS_M48_GATE_RETEST | Meta row; inherits the dispositions of the rows it lists. |
| 1853 | M40.S03.T002 | Final regression (backend suite + DB suites on disposable PostgreSQL +… | — | full backend + 157 DB files | — | NEEDS_M48_GATE_RETEST | No stored run log; M48.S01.T012 repeats it. |
| 1858 | M41.S01.T001 | Discount approval on quotations and sales orders: `discount_approval_r… | a2e6261 | `test_m41_s01_db.py` | `coordination/milestones/M41/live_report.txt`, `coordination/milestones/M41/live_report_rerun.txt` | NEEDS_M48_GATE_RETEST |  |
| 1860 | M41.S01.T002 | Verify the signer's e-mail on the customer quote signature (one-time c… | a2e6261 | `test_m41_s01_db.py` | `coordination/milestones/M41/live_report.txt`, `coordination/milestones/M41/live_report_rerun.txt` | NEEDS_M48_GATE_RETEST |  |
| 1862 | M41.S01.T003 | eTIMS item classification: `Product.etims_item_code` and `tax_type_cod… | a2e6261 | `test_m41_s01_db.py` | `coordination/milestones/M41/live_report.txt`, `coordination/milestones/M41/live_report_rerun.txt` | NEEDS_M48_GATE_RETEST | eTIMS provider auth/cancel/status remain activation [D] once a provider is chosen. |
| 1870 | M42.S01.T001 | Data: `employee_business_cards` (one per employee: `slug` unique and p… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1872 | M42.S01.T002 | Public endpoints (no login, in PUBLIC_ROUTES, rate-limited, noindex): … | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1874 | M42.S01.T003 | QR: `GET /api/v1/hr/employees/{id}/card/qr.svg/png` (login) with the e… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1876 | M42.S02.T001 | Public page `/kartvizit/[slug]` (outside `/dashboard`): mobile-first c… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1878 | M42.S02.T002 | HR screens: "Business card" tab on the employee record under `/dashboa… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1880 | M42.S02.T003 | ESS "My business card": employee sees and shares own card and QR; edit… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST |  |
| 1882 | M42.S03.T001 | Acceptance: live click-through (add employee → card live → scan QR wit… | e27e126, 6bd7314 | `test_m42_business_cards_db.py` | `coordination/milestones/M42/live_report.txt` | NEEDS_M48_GATE_RETEST | Physical print run waits for production domain (Persistent External gate) — that part only is [D]. |
| 3102 | M48.S00.T001 | Safely synchronize existing Desktop C:\\Users\\sekip\\Desktop\\fmcg-er… | 6ac96f1 | n/a (baseline) | `coordination/milestones/M48/BASELINE.md` | NEEDS_M48_GATE_RETEST | Current milestone; accepted only by the M48.S02.T001 gate. |