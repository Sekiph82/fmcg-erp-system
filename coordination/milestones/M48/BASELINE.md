# M48.S00.T001 — Baseline (2026-11-26)

- Source SHA: `6ac96f1ed375a3f067d367c8aba598854787e8e9` (main == origin/main after a fast-forward from 8e9b2be; owner commit "plan all 60 ERP excellence upgrades"). Untracked owner files preserved: `.hiveai/`, `backend/M25_S01_T003_POSTGRES_V0{2,3}.log`.
- TASKS.md row states at the baseline: 103 `[v]`, 119 `[ ]` (M48–M52), 32 `[D]`.
- Last recorded test baseline (M47 gate, historical, not new acceptance): backend 1841 passed / 537 skipped / 0 failed; DB-gated 55/55 M43–M47 files.
- Backend test files: 363. Skip gates are environment flags (`M45_DB`, `M43_S01_DB`, `M46_DB`, `M44_DB`, `M21_…`, `M22_…`, `M31_…`, …, about 60 distinct flags). 51 files also use `pytest.skip`/`skip(`. The full inventory and dispositions belong to M48.S01.T012.

## Audit findings reproduced by source inspection

| Finding | Source | Confirmed |
|---|---|---|
| Ads providers report `live_publishing: False` unconditionally, and drafts are validate-only | `backend/app/api/v1/endpoints/ads.py:57-59`; module docstring "Live publishing is refused" | yes |
| TikTok `publish_id` returned as the publish result | `backend/app/services/social_service.py:139` | yes (state machine to verify in T005) |
| Prospect drafts hard-code "POVU drinks"; the agent template names "POVU Water 500 ml" / "POVU Juice 1 L" | `backend/app/services/customer_data_service.py:208`, `backend/app/services/agent_service.py:248`; `master.py:48` BEVERAGE enum and `market_intelligence.py:32` comment to review | yes |
| The warehouse writer supports only LOCAL_DIR/S3/POSTGRES; SNOWFLAKE/BIGQUERY are `UNCONFIGURED` text only | `backend/app/services/warehouse_export_service.py:48-49,196` | yes |
| DocuSign/Adobe Sign are status strings only (`NOT_CONFIGURED`) | `backend/app/services/cpq_service.py:14,35` | yes |
| No card-payment provider adapter (only M-Pesa payment links) | `backend/app/services/payment_link_service.py`; no Pesapal/Flutterwave code | yes |

## 60-recommendation traceability (status updated as rows move)

| Rec | Task | Title | Original IDs | Status |
|---|---|---|---|---|
| 01/60 | M48.S01.T001 | Meta Ads production mutation adapter | 12–15 | open |
| 02/60 | M48.S01.T002 | Google Ads production mutation adapter | 12–15 | open |
| 03/60 | M48.S01.T003 | LinkedIn Ads production mutation adapter | 12–15 | open |
| 04/60 | M48.S01.T004 | TikTok Ads production mutation adapter | 12–15 | open |
| 05/60 | M48.S01.T005 | TikTok organic posting state machine and correctness | 16 | open |
| 06/60 | M48.S01.T006 | Canonical POVU product/brand context; remove beverage placeholders | 22 | open |
| 07/60 | M48.S01.T007 | Snowflake writer and sync adapter | — | open |
| 08/60 | M48.S01.T008 | BigQuery writer and sync adapter | — | open |
| 09/60 | M48.S01.T009 | DocuSign and Adobe Acrobat Sign adapters | 35 | open |
| 10/60 | M48.S01.T010 | Card payment and CPQ settlement adapters | 35 | open |
| 11/60 | M48.S01.T011 | Reconcile 103 historical [v] entries and acceptance scope | — | open |
| 12/60 | M48.S01.T012 | Complete all legacy/new database and skipped-test regression | — | open |
| 13/60 | M49.S01.T001 | Recurring Google and Outlook meetings | 03 | open |
| 14/60 | M49.S01.T002 | Calendar webhooks and renewal | 04 | open |
| 15/60 | M49.S01.T003 | Shared/delegated mailboxes | — | open |
| 16/60 | M49.S01.T004 | Advanced VoIP and contact center | 08 | open |
| 17/60 | M49.S01.T005 | Multilingual transcription and speaker separation | 09 | open |
| 18/60 | M49.S01.T006 | Unified advertising lifecycle UI | 12–15 | open |
| 19/60 | M49.S01.T007 | Facebook and Instagram rich media | 16 | open |
| 20/60 | M49.S01.T008 | LinkedIn image/video publishing | 16 | open |
| 21/60 | M49.S01.T009 | YouTube and other supported social adapters | 16 | open |
| 22/60 | M49.S01.T010 | Multichannel social listening and moderation | 18 | open |
| 23/60 | M49.S01.T011 | Audience lifecycle and platform synchronization | 20 | open |
| 24/60 | M49.S01.T012 | Integrated Marketing Studio | — | open |
| 25/60 | M50.S01.T001 | Full AI Prospecting Agent orchestration | 22, 23/24 | open |
| 26/60 | M50.S01.T002 | External research and authorized web search adapters | 22, 23/24 | open |
| 27/60 | M50.S01.T003 | External customer enrichment adapters | 23/24 | open |
| 28/60 | M50.S01.T004 | External buyer-intent feed | — | open |
| 29/60 | M50.S01.T005 | Grounded generative RAG customer service agent | 28 | open |
| 30/60 | M50.S01.T006 | Customer support QA and knowledge gaps | 28 | open |
| 31/60 | M50.S01.T007 | Agent Builder advanced workflow and handoff | — | open |
| 32/60 | M50.S01.T008 | Agent budgets and concurrency robustness | — | open |
| 33/60 | M50.S01.T009 | Common no-code data synchronization across all ERP objects | 32 | open |
| 34/60 | M50.S01.T010 | SAML, Parquet and OCR implementation | — | open |
| 35/60 | M50.S01.T011 | Gmail and Outlook add-in security and usability | 33 | open |
| 36/60 | M50.S01.T012 | AI accuracy, evaluation and safety framework | — | open |
| 37/60 | M51.S01.T001 | Advanced visual CMS layout editor | 36 | open |
| 38/60 | M51.S01.T002 | Global components, themes and templates | 36 | open |
| 39/60 | M51.S01.T003 | Google Search Console actual adapter | 37 | open |
| 40/60 | M51.S01.T004 | Technical SEO crawler and performance | 37 | open |
| 41/60 | M51.S01.T005 | AEO measurement provider adapter | 40 | open |
| 42/60 | M51.S01.T006 | Actual AI image and multimedia production adapters | 38 | open |
| 43/60 | M51.S01.T007 | TTS, video and media processing standardization | 38 | open |
| 44/60 | M51.S01.T008 | Full ERP EN/SW/TR localization | 40 | open |
| 45/60 | M51.S01.T009 | Secure visitor e-mail verification | 39 | open |
| 46/60 | M51.S01.T010 | Large media and object storage | — | open |
| 47/60 | M52.S01.T001 | Synthetic load and performance benchmark | — | open |
| 48/60 | M52.S01.T002 | Distributed rate limiting | — | open |
| 49/60 | M52.S01.T003 | Worker and job scalability | — | open |
| 50/60 | M52.S01.T004 | Central errors, retry and dead-letter handling | — | open |
| 51/60 | M52.S01.T005 | DB index and query optimization | — | open |
| 52/60 | M52.S01.T006 | Central authorization/company isolation | — | open |
| 53/60 | M52.S01.T007 | Full exhaustive persona browser walkthrough | — | open |
| 54/60 | M52.S01.T008 | WCAG 2.2 AA accessibility | — | open |
| 55/60 | M52.S01.T009 | Local backup/restore disaster recovery | — | open |
| 56/60 | M52.S01.T010 | Dependency, SBOM and licensing | — | open |
| 57/60 | M52.S01.T011 | Current architecture and API docs | — | open |
| 58/60 | M52.S01.T012 | Synthetic data isolation and old fixtures cleanup | — | open |
| 59/60 | M52.S01.T013 | Finance/CPQ/manufacturing/GL integrated regression | 35 | open |
| 60/60 | M52.S01.T014 | Independent final HubSpot comparison and quality gate | — | open |
