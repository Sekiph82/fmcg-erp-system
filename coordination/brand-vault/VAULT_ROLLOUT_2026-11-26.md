# POVU Brand Vault rollout into the ERP (ERP-POVU-VAULT-001..003, 2026-11-26)

## Source and verification
- **Source of truth:** the owner-designated folder `C:\Users\sekip\Desktop\Character Reference Sheets\Character Refence Sheets`.
- **Release:** public `Sekiph82/POVU-Brand-Vault`, `manifests/approved-release-local.json` (status APPROVED_RELEASE).
- **Fresh SHA-256 of the local originals, equal to the release manifest:**
  - POVU Logo.png: d602bc99…68acf (1 603 593 bytes);
  - POVU_Icon_Pack.zip: d013ad30…77de01.
- **Icon package:** all 15 files extracted from the local ZIP match the manifest's POVU_ICON_EXTRACTED hashes.
- **Alpha check:**
  - logo 1536×1024 RGBA, alpha 0–254 (transparent);
  - icons RGBA.

## Copies in the ERP

All byte-identical (same SHA-256 as the release); nothing regenerated, resized, recoloured or padded.

| ERP file | Vault asset |
|---|---|
| frontend/public/brand/povu-logo.png | POVU Logo.png (POVU_NEW_LOGO) |
| frontend/public/favicon.ico | icon pack favicon.ico |
| frontend/public/icons/povu-icon-16/32/180/192/512.png | POVU_Icon_16/32/180/192/512.png |

## Wiring
- **Login page:** the full logo at its own 3:2 proportions.
- **Sidebar and mobile header:** the square app icon (192 px, object-contain).
- **`layout.tsx` icons:** favicon.ico, PNG 16/32 and apple-touch 180.
- **PWA manifests** (ERP `manifest.ts` and POVU Shop `povu-shop.webmanifest`): 192 and 512 "any".
  - The package has no maskable variant. Making one would mean padding (modifying) the artwork, so the maskable entry was removed rather than generated.
- **Service worker:** cache bumped to `povu-pwa-v2`, so old icon caches are evicted on activate. New icon file names also bypass cached copies. The notification icon and the offline page use the new icon.

## Rollback
- **Old files kept:**
  - the old favicon is preserved at `public/brand-legacy/favicon-pre-vault.ico`;
  - the old `povu-logo.jpg` and `icons/icon-*.png`, `apple-touch-icon.png` and `icon-maskable-512.png` stay in place, unreferenced.
- **To roll back:** revert this commit (references and sw VERSION).

## Checks
- `node --test tests/unit/pwa-service-worker.test.mjs`: 4/4 pass.
- tsc clean.
- **Browser (local dev):**
  - the login shows the new transparent logo;
  - `<link rel=icon>` points to favicon.ico, 32 and 16 px, plus apple-touch 180;
  - the ERP and Shop manifests list the new 192/512 icons (HTTP 200);
  - sw VERSION is povu-pwa-v2; the offline page uses the new icon.
- **Not done here:** a real device install of the PWA (home-screen icon). That belongs to commissioning (M47.S02.T009) together with the production domain.
