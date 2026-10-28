# M21.S04.T003 — CSV import/export support

## Changes

- Registered conversion profiles with the existing bulk-import framework, including template download, validate-only preview, strict/import-valid-only modes, duplicate detection, and import-history recording.
- Added row-level checks for source/target product IDs and for linked packaging BOM existence, type, and matching target SKU.
- Added CSV export for the active profiles visible from the conversion-profile list. Export cells beginning with spreadsheet formula markers are escaped.
- Added the minimal `bom.import` and `bom.import_template` permission definitions and grants for admin and production manager roles, and guarded the UI actions with the corresponding permissions. Existing `bom.export` permission protects export.
- Documented the CSV flow, UUID references, generated profile codes, and duplicate behavior in the manufacturing manual.

## Verification

- Frontend `npm.cmd run type-check` passed.
- Python compilation passed for the BOM endpoint, bulk-import endpoint, and seed permissions module.
- Runtime module import confirmed the adapter is registered and the import/export endpoints load. A direct seed check confirmed the new permissions and production-manager grants; the formula-safe cell helper prefixes a formula-leading value.
- Generated the import template and confirmed its CSV headers, field types, and sentinel example row.
- `git diff --check` passed.
- Independent read-only review found two blockers in the first pass (missing seeded import permissions and spreadsheet formula injection). Both were fixed; the follow-up review found no remaining blocker.

## Scope limits

- No production or owner data was accessed or changed; no database-backed import run was performed.
- Duplicate profile-code/version pairs are rejected during validation and are never updated or overwritten. Export includes active profiles, matching the conversion list.
- The seed changes add only the permissions needed for this import feature. Broader permissions/audit/history verification remains in M21.S04.T004.
