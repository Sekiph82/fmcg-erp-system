# M21.S04.T002 — Conversion-profile UI

## Changes

- Added source-product and target-SKU selectors to conversion-profile creation, with the packaging-BOM choices limited to the selected target SKU.
- Exposed the existing profile fields needed by the conversion workflow, with client-side bounds matching the API contract and generated profile codes when the optional code is left blank.
- Added the existing package-components calculation to the profile view. The operator supplies target SKU quantity explicitly; the UI does not derive packaging demand from conversion yield.
- Added loading/error retry feedback for product and packaging-BOM selectors, positive finite quantity checks, and cleared prior package results when the profile, quantity, UOM, or effective date changes.

## Verification

- `npm.cmd run type-check` passed.
- `git diff --check` passed.
- Independent read-only review found no frontend/API contract mismatch. The reviewer identified stale package results after input changes; the UI now clears them on requested quantity, UOM, date, or profile changes.

## Scope limits

- No production or owner data was accessed or changed.
- No backend schema, lifecycle policy, automatic yield-to-SKU quantity mapping, or database behavior was changed.
- No browser-based visual acceptance was performed.
