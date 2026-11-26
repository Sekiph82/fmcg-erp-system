# M50 gate: AI agents, prospecting, service and data platform (2026-11-26)

## Candidate and environment
- **Final candidate:** the M50 gate commit.
  - The full DB run was on frozen `507dc03`.
  - After that run, two re-review fixes went in: N1 (charge real spend on settle) and N2 (fail-closed DNS pinning assertion). Every affected DB file was rerun afterwards (§2).
  - One frontend lint fix (§3).
- **Database:** disposable `postgres:16-alpine` (`m49-gate-pg`). Template `m50_tmpl` was built empty → head 20261130_0080 plus a synthetic POVU seed. The owner's dev DB was never used.
- **Services:** local Mailpit, Mosquitto, ClamAV and Redis.
- **Providers:** simulators only (`PROVIDER_EGRESS=local`). No paid LLM or provider call.

## 1. Migrations (`01_migrations.txt`)
- Empty → 0080: 27 M50 tables.
- Seeded copy with evidence rows:
  - Downgraded and upgraded twice (0080 → 0079 → head): 18 archives, then 36.
  - Evidence rows kept in `*_archived_0080`.
  - `dw_jobs.file_format` goes 10 → 6 → 10, and 'parquet' is rewritten to 'csv' on downgrade.
  - Seed rows kept.

## 2. Backend
- **Full DB-gated inventory** (`02_db_tests_full.txt`, `02_db_tests_full_report.md`): **260/260 PASS**. Each file ran on its own fresh DB with the services.
- **Rerun after N1/N2** (`02_db_tests_rerun_final.md`): **9/9 PASS**. Files: test_m50 t002, t007, t008, t011, t013 (18 passed, including the N2 pinning assertion), and the agent suites.
- **No-DB suite** (`02_backend_suite_nodb.txt`, `507dc03`): **1997 passed, 0 failed**, 778 skipped. The skips are DB/service flags covered by the DB run.
  - route-auth and t013 rerun after N1/N2: 10 passed.

## 3. Frontend (`03_frontend.txt`)
- tsc exit 0.
- eslint: 2 errors at first (`react/no-unescaped-entities` in the service-agent page). Fixed; 0 errors on re-run.
- i18n report ok.
- `next build` exit 0. The build directory was deleted.

## 4. Manual browser walkthrough (`05_browser_walkthrough.md`, 5 screenshots)
- Prospecting: NOT_CONFIGURED reasons, cited candidates, and outreach that waits for a second person.
- Data sync: stock is export-only.
- Public chat:
  - a grounded answer with a citation;
  - a refund request is refused and handed to a person; the injected KB text is never obeyed;
  - CSAT/CES posts through the new public route (202).
- AI evaluation: a SYNTHETIC run with corpus and config hashes.
- Agents page.

One defect found (F, silent empty prospecting run) and fixed in T014.

## 5. Independent review (Opus reviewer, read-only)
- **Review of `0bdf90c`:** ACCEPT_WITH_FIXES, 14 findings. High: S1 SSRF DNS rebinding; S2 two-person bypass on data-sync proposals. Medium: S3, S4, S5, I1. The rest Low. All fixed in T013 (`507dc03`).
- **Re-review:** **ACCEPT**. All 14 CLOSED; 3 new Low findings:
  - **N1 fixed:** settle charges real spend; the overage is noted.
  - **N2 fixed:** pinning fails closed if the httpcore internals change.
  - **N3 accepted as a known limit:** a stolen refresh token used inside the 10 s grace window can avoid revocation. The grant still expires at ADDIN_GRANT_MAX_DAYS and is revocable from CRM → Mail add-in sessions.

## 6. Quality
No category scores are assigned. Scoring happens in M52 per `QUALITY_RUBRIC.md`.

## 7. Remaining, honestly
- **Activation only:**
  - Brave Search and People Data Labs keys plus licence notes;
  - a real LLM provider (`SERVICE_AGENT_LLM_ENABLED`);
  - a real SAML IdP;
  - Gmail/Outlook add-in deployment on real hosts. Check whether Apps Script LockService needs an extra scope.
- **Known limits:**
  - **Search fetch:** DNS pinning applies to live provider egress.
  - **Older modules use plain httpx clients outside the egress guard:** webhook subscribers, WhatsApp, M-Pesa, eTIMS, SMS, CBK, Shopify, web push, ai.py. They are carried to M52.S01.T004.
  - **Missing company scoping:** no `company_id` on the prospecting or service-QA tables.
  - **Clustering and safety detection:** lexical support-QA clustering; keyword safety detection.
  - **Parquet:** the uncompressed-size cap trusts the file footer.
  - **Data sync:** `mapping_editor` keeps only the latest editor.
  - **Add-ins:** N3 above.

## Result
**M50 gate: PASS.**
