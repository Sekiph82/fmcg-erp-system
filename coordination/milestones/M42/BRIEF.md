# M42 — Employee digital business cards (QR) — owner brief, 2026-11-24

Requested by Şekip Hayıt. Approved plan (Turkish, full text): https://claude.ai/artifact/EenmsQ1hRxUSh8QMbMjF5E — tasks are in root `TASKS.md` under M42.

## Goal
The digital business card made for Şekip Hayıt on GitHub Pages (repo Sekiph82/SekipHayit: static index.html + .vcf, cover video, large photo, Call/WhatsApp/E-mail tiles, Save contact, TR/EN) must be produced by the ERP for every employee. The single source is the employee record in HR → Employees. Staff join and leave all the time, so cards are created, updated and closed automatically.

## Owner decisions (binding)
1. Built inside this ERP project, same codebase and domain. No separate site.
2. Every employee gets a card and QR automatically when created (screen, API or Excel/CSV import). No draft/approve step.
3. Public URL is the name only, no random suffix: `/kartvizit/jane-mwangi`. A second person with the same name gets `jane-mwangi-2`. A slug never changes once issued, even if the name changes, so printed QR codes keep working.
4. Management lives under `/dashboard/hr/employees/...` (login). The public card must be outside `/dashboard` because scanners must not hit the login page.
5. Production domain will be on povu.com; exact host not decided yet. Use `PUBLIC_APP_URL` only, never hard-code a host. Development is not blocked; only the physical print run waits for the live domain and one real phone scan.
6. Terminated/archived employee → card closed automatically, shows "no longer valid", no personal data.

## Reuse (already in the repo — do not add libraries)
- `hr_employees` model and `/api/v1/hr/employees` CRUD; `/dashboard/hr/employees` screen with `ImportModal module="employees"` (bulk import in `bulk_import.py`).
- `qrcode[pil]` and `python-barcode` (see `services/gs1_service.py`).
- Public no-login pattern: `/verify/[token]`, `/d/[token]`, `documents_public.py`, `PUBLIC_ROUTES`.
- `brand_assets` (LOGO) for company logos; document storage + `file_validator` for photos; audit log; `access_control`.
- No PDF library: printable cards via print CSS.

## Privacy (Kenya Data Protection Act 2019)
Work phone and work e-mail only by default; never personal number, M-Pesa, bank, salary. Photo published only with recorded employee consent. Pages noindex, endpoints rate-limited, all changes audit-logged.

## Out of scope for now
NFC cards, Apple/Google Wallet passes, scan analytics, per-employee gallery/catalogue (link to the shared company catalogue only).

## Open owner questions (do not block implementation; ask in plain Turkish when needed)
- Exact production host (e.g. erp.povu.com or povu.com).
- WhatsApp tile on or off by default.
- Languages: EN + Swahili, add Turkish?
- Brand on cards: Resas Chemie, SAFINA, or automatic by the employee's company.
