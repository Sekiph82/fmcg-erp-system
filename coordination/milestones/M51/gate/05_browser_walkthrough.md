# M51 manual browser walkthrough (2026-11-26/27)

## Environment
- **App:** real local ERP. The backend ran through the "M49 walk backend" launch entries against the disposable DB `m51_walk` on `m49-gate-pg:25432`. The frontend was the "M49 walk frontend" entry on port 3249 (dist `.next-m49walk`, since deleted).
- **Data:** synthetic POVU seed `m51_walk_seed.py`.
- **Providers:** simulators only (`PROVIDER_EGRESS=local`).
- **Browser:** built-in browser pane; desktop and mobile (375×812) viewports.

## Checks and results
| # | Area / persona | Locale / viewport | Result | Screenshot |
|---|----------------|-------------------|--------|------------|
| 1 | CRM dashboard (sales manager) | SW desktop | Nav, headings, buttons and empty states in Kiswahili; numbers and dates formatted per locale | `screenshots/01_crm_kiswahili.jpg` |
| 2 | CRM → Pipeline | EN desktop | **Defect found:** the page stayed on "Loading" indefinitely, because the pipeline selector only rendered after the load that needed it (this bug predates M51). Fixed in `frontend/src/app/dashboard/crm/pipeline/page.tsx` (a142ca2); the board now renders | `screenshots/02_crm_pipeline_fixed_en.jpg` |
| 3 | Marketing → SEO & AEO (marketing manager) | TR mobile | First pass partly translated (single-word labels left in English). This started the coverage pass: 1,117 more strings | `screenshots/03_seo_pro_turkish_mobile_partial.jpg` |
| 4 | Marketing → Media studio | TR desktop | Upload, jobs, TTS voices (espeak-ng en/sw/tr) and image drafts labelled in Turkish. The image job shows DRAFT and needs a second reviewer | `screenshots/04_media_studio_turkish.jpg` |
| 5 | Login | TR | Login form, 2FA prompt and errors in Turkish; backend error codes are mapped through `backend_messages` | `screenshots/05_login_turkish.jpg` |
| 6 | SEO & AEO after the coverage pass | TR desktop | Tabs, tables and actions translated. Search Console shows NOT_CONFIGURED (no account) | `screenshots/06_seo_pro_turkish_after_coverage.jpg` |

## Option values
The codemod had wrapped some data-valued `<option>` elements in `tx()`, so a translated label could be sent to the API. Twenty options now have explicit `value=`. The scanner `scripts/i18n-options.mjs` reports `[]`.

Browser check: the Search Console selects (dimension and period) post English values while showing Turkish labels.

## Known limits (carried, not hidden)
- **Backend text:** some dynamic backend text, such as provider NOT_CONFIGURED reasons that embed setting names, stays in English. Only fixed backend error codes are localized.
- **Untranslated remainder:** about 379 single-word labels, 140 option labels without a value and 53 skip-list strings remain in English. They are carried to M52 together with export and PDF localization.
- **Native-speaker review:** the SW and TR catalogs are machine-assisted. A native-speaker review is recommended before commissioning (an M52 note).

## Public routes and auth
Public-route auth (`/public/visitor-verify/*` and `/public/media-files/*` are public; staff routes return 401) is covered by the route-auth and T009/T010/T011 DB tests (see `02_db_tests_full.txt`), not by this walkthrough.
