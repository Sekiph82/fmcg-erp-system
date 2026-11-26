# M46 gate — step 5: real local app walkthrough (2026-11-26)

## Setup

- **Backend:** uvicorn on :8046 using the disposable DB `m46_walk` (head 0076). The owner's dev DB was not used.
- **Media:** stored in a scratch folder. `PROVIDER_EGRESS=local`; no provider keys.
- **Frontend:** `next dev` on :3246 (distDir `.next-m46walk`, removed afterwards).
- **Data:** synthetic POVU content, built by a seed script through the real API:
  - personas `synth-author` (marketing view/create/edit) and `synth-approver` (marketing view/approve);
  - portal accounts PA-WALK-GOLD (on the "Gold members" list) and PA-WALK-OTHER;
  - site `povu` (en/sw/tr) with home en+sw, products, a dynamic product page, a blog post, a members page with a gated video (ffmpeg-generated, 4 s) with en/sw captions, and an unpublished draft.
- **Reseed:** after the review fixes the backend was restarted on a fresh DB and reseeded; every check below was repeated on the fixed code.

## Public site (anonymous)

- `/site/povu/en` (`01`): hero, CTA, anonymous fallback block, control variant, FAQ.
- **Head metadata:**
  - canonical `/site/povu/en`;
  - hreflang en+sw;
  - meta description;
  - JSON-LD WebPage + FAQPage.
- No overflow.
- **Public response hygiene:** no `audience`/`fallback`/`experiment` keys.
- **Not served:**
  - the unpublished draft `/secret-launch` → 404;
  - the members page → "for signed-in members" (API 401).
- **Dynamic page:** `/sw/product/povu-juice-1l` renders the row (sw → en fallback for an untranslated page).

## Members (portal realm)

- Signed in as the Gold member at phone width 375×812 (`02`):
  - the members page and the video play (currentTime 2.08 s, readyState 4);
  - caption tracks en, sw;
  - scrollWidth 375 (no overflow).

## Shop / portal in Swahili and Turkish (M46.S01.T007)

- The portal was used in Swahili (`03`) and Turkish at 375 px.
- All 8 tabs were opened in each language. For every tab:
  - horizontal overflow is 0;
  - `window.__i18nMissing` is empty (no missing keys).
- Formats:
  - money shows "Ksh 0.00" (sw-KE);
  - dates and numbers use the locale.

## Staff workflow

- **synth-author** (`04`):
  - opened the draft, added an FAQ block in the visual editor, saved ("not live until published"), previewed at phone width;
  - ran the SEO audit: 75/100. Findings: title length, missing description, no H1. Search Console NOT_CONFIGURED;
  - submitted for review;
  - publishing as the author → 403.
- **synth-approver** (`05`): approved and published in the UI. Result: v1 LIVE, "approved by synth-approver".

## Notes

- **Gate defect fixed:** the staff API client redirected public pages to /login when a staff call returned 401. `/site`, `/book`, `/pay`, `/survey`, `/docs` and `/plan` were added to its public-page list. The last five had the same pre-existing gap.
- **Not covered here:** the content studio and members & media screens were exercised by the API tests only (DB tests), not clicked through.
