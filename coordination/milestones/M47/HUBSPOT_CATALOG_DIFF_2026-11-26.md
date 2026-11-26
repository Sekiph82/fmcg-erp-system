# HubSpot catalog diff: live page (2026-11-26) vs snapshot HUBSPOT_CATALOG_FEATURES_2026-11-25.md

## Fetch status
| URL | Status | Notes |
|---|---|---|
| https://legal.hubspot.com/hubspot-product-and-services-catalog/products | HTTP 200, 2,555,267 bytes (curl, server-rendered HTML) | Read in full. All 483 `tr[data-row-id]` hub-feature rows parsed, plus the Agent Hub list (11), AEO list (9) and the per-hub pricing rows. Page JSON-LD `dateModified`: **2026-11-05T22:16:24Z**, which is before the 2026-11-25 snapshot. |
| https://www.hubspot.com/products | HTTP 200 | Fetched only. Marketing overview, not a feature catalog, so not diffed. |
| .../products/marketing, /sales, /service, /content, /data | HTTP 200 each | Fetched only, not diffed (same reason). |
| .../products/commerce | HTTP 200, redirects to /products/revenue | Fetched only, not diffed. |
| .../products/artificial-intelligence, /products/aeo | HTTP 200 each | Fetched only, not diffed. |

## Live row counts per section (hub tables)
Smart CRM: Unify customer data 46, Unify teams 34, Unify tech stack 13 · Marketing: Generate leads 42, Automate marketing 45 · Sales: Build pipeline 50, Close deals 32 · Service: Scale support 50, Drive retention 30 · Content: Create content 41, Manage content 26 · Data: Manage data 13, Activate data 9 · Revenue: Quote without delay 24, Bill with confidence 18, Collect payments 10 · **Total 483**. Agent Hub has 11 agents and AEO has 9 items, the same as the snapshot.

## Comparison method
For each section, every live row name was normalized and checked against the snapshot text. Each snapshot item was then checked against the live rows. Every mismatch was reviewed by hand.

## NEW (on the live page, not in the snapshot)
None. Every live-only hit is a row that the snapshot recorded under a shortened or merged name:
- "Data enrichment (automatic, bulk, continuous, company, contact, segment, workflow actions)" is 8 separate live rows.
- "Recent/Top visitor email digests" is 2 live rows.
- "Calendar / board / report visualization for CRM index pages (Beta)" is 3 live rows. One of them is "Non-pipeline board visualization…".
- "HubSpot Work / Work agents" is 2 live rows.
- "Filter insights / Segment analytics (Beta)" and "Segment insights/analytics" are each 2 live rows.
- "Simple/Custom revenue reporting" is 2 live rows.
- Short forms in the snapshot whose full live names differ only in wording: "Subdomain/ccTLD availability", "SEO recommendations", "Facebook Messenger", "Mobile app", "Phone numbers", "Email tracking", "Video hosting", "Smart content for email", "ABM tools", "Stripe processing", "Capital financing (Stripe)", "Affirm and Klarna", "LinkedIn Sales Navigator and CRM Sync", "In-person meeting notetaker (Beta)". On the live page that last one reads "[iOS only] (Beta)".

## REMOVED (in the snapshot, no longer on the live page)
None.

## RENAMED
None confirmed. "AI formatting recommendations (Beta)" (Smart CRM) and "AI data formatting recommendations" (Data Hub) appear on the live page as "AI-powered (data) formatting recommendations (Beta)". This looks like snapshot shorthand, not a rename, because the page has not been modified since 2026-11-05. The live Data Hub row carries a Beta label that the snapshot left out.

Minor live-page typos, recorded for completeness: "Call recording and transciption" (Sales) and "Subdomain and countr code…" (Content).

## Conclusion
No material change. The live catalog matches the snapshot section by section (0 new, 0 removed, 0 renamed). Its dateModified of 2026-11-05 is earlier than the snapshot date. Edition cells were extracted but not re-diffed value by value, because the snapshot does not store per-row edition values.
