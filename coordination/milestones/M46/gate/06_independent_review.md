# M46 gate — step 6: independent review (2026-11-26)

- **Reviewer:** a separate read-only reviewer agent (feature-dev:code-reviewer).
  - It was given the file list and the intended security properties, not the author's conclusions.
- **Verdict:** ACCEPT_WITH_FIXES.

## Fixed in the gate (regression tests in `backend/tests/test_m46_s01_content_hub.py`)

| # | Sev. | Finding | Fix |
|---|---|---|---|
| 1 | high | Re-submitting a live page took it offline | "Live" means a live version exists. Pages are served by `live_path` whatever the draft/review status. Test: page in review stays 200. |
| 2 | high | Redirects beat live pages (cross-locale); authors could add open redirects | A live page in the requested locale wins over a redirect. Manual redirects need marketing.approve and must target a site path. No auto-redirect for members pages. Tests cover all three. |
| 3 | high | Rows of a table behind a members-only dynamic page leaked through a public table block | Table blocks on public pages show no rows of such tables. Test: anonymous 401 on the row page, public block rows = [], member sees the row. |
| 4 | high | Live content changed without review (CTAs, rows of a published table, moving a live page, author/category/tags, captions of served media) | CTA, rows of published tables and captions of public/gated media need marketing.approve. A page moves only on publish (`live_path`). Author/category/tags are served from the version snapshot. Tests cover CTA, rows, move. |
| 5 | med | Edits after approval kept APPROVED | Any non-access change on an IN_REVIEW/APPROVED page resets it to DRAFT. Test: publish refused after a title edit. |
| 6 | med | AI budget check not atomic | Atomic reservation (`UPDATE … WHERE spent + est <= budget`), then settled to the reported usage. A failed call keeps its reservation. |
| 7 | med | A self-typed e-mail turned CRM-targeted blocks into an oracle | CRM data (lifecycle, audiences) is used only for a verified identity: the signed-in portal user. Test: self-identified visitor gets the fallback; a portal member gets the targeted block. |
| 8 | med | Embedded/column blocks skipped personalization and experiments | Expand first, then personalize and choose recursively. |
| 9 | med | Public response carried audience/segment/experiment metadata | Rule keys are stripped. Test: no "audience"/"CUSTOMER"/"fallback" in the response. |
| 10 | med | `alternates` exposed members-only translations | Alternates only among live pages with the same access. |
| 11 | med | Members KB skipped other scope restrictions | The access list widens nothing else: company/department/factory/module/scope restrictions still apply. |
| 12 | med | Approval used findings computed at draft time | `decide()` re-runs the brand review with the current profile before approving. |
| 14 (part) | low | Duplicate slugs/keywords in one batch → 500 | Duplicates refused (422) / skipped. Bad positions → 422. |
| 15 | low | Malformed block data → 500 | Converted to 422. Test covers three kinds of junk. |
| 16 | low | Archived pages could not be re-reviewed | Submit accepts ARCHIVED. |
| 17 (part) | low | Staff media file without nosniff; table counts across sites | Both fixed. |

## Carried over (M47.S01.T006)

- **13: rate limits and amplification on public routes.**
  - Media view/convert writes per arbitrary visitor id.
  - The sitemap is N+1 and unbounded.
  - Embed query fan-out.
  - Experiment events are not covered by the analytics retention purge.
- **14 (rest):** concurrency races on first experiment row, JSON counter read-modify-write, approve-vs-edit TOCTOU.
- **17 (rest):**
  - Podcast RSS channel `<link>`/`<description>`.
  - Blocking file writes in media upload.
  - Upload limit enforced after spooling.
