# M25.S01.T002 — In-transit inventory ownership/status

Status: implementation complete; independently reviewed.

## Scope and decision

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Task authority: root `TASKS.md`; no task-specific T002 acceptance file was present.
- Before implementation, fetched `origin/main`; local HEAD and `origin/main` matched at `096f9ab8c3404663756be74a525f277f7919eba5`.
- Ownership is not inferred from Incoterm. A PO shipment link starts `UNCONFIRMED`; an authorized user records `SUPPLIER_OWNED` or `BUYER_OWNED` with a source reference. This records supplied workflow evidence and does not determine legal title.
- Status updates are limited to a forward-only shipment flow and require `logistics.edit`; ownership can be recorded only after cargo loading and before delivery. No GL, inventory valuation, or landed-cost posting is performed by this scope.

## Delivered

- Added `inventory_owner_status` to shipment/PO links with a database check constraint and an `UNCONFIRMED` default.
- Added append-only `shipment_ownership_events` with previous/new owner, source reference, optional notes, effective time, and authenticated actor identity.
- Added permission-protected API endpoints for listing ownership history and recording a confirmed owner. The update locks both the PO link and shipment rows, rejects out-of-scope shipment states, blank references, unsupported owner values, and duplicate current values.
- Prevented unlinking a PO link that has ownership history. PostgreSQL also enforces the event FK with `ON DELETE RESTRICT`.
- Added revision `20261029_0035`; it is safe for both the squashed-baseline path and existing schemas. Downgrade removes only marked revision-owned fields/table, refuses to drop a populated revision-owned history table, and preserves baseline-owned objects.
- Shipment status updates now require `logistics.edit` and follow the explicit lifecycle transitions in the API. The UI exposes only permitted next statuses and hides shipment edit controls for view-only users.
- Added owner-status and append-only history UI. The owner selector has no preselected party; the UI explains that Incoterm does not set ownership.

## Verification

- Python `compileall` for changed backend files and migration — passed.
- Frontend `npm run type-check` — passed.
- Targeted ESLint for the shipment page and mocked test — passed.
- Task-owned disposable PostgreSQL V04: migration through `20261029_0035`; `tests/test_m25_s01_t002_shipment_ownership_db.py` — **1 passed**. It covered permission denials, invalid and allowed shipment status transitions, initial `UNCONFIRMED`, evidence-reference validation, owner-change history, append-only event deletion rejection, PO-link deletion rejection, and restriction of user deletion so actor identity remains attached.
- Task-owned mocked browser V04: `m25-shipment-purchase-container-linkage.mocked.spec.ts` — **2 passed**. It covered the shipment/PO/container flow, documented ownership recording/history display, and view-only behavior.
- Independent read-only review — no remaining concrete blocker for this narrow synthetic feature claim.
- `git diff --check` — passed.

## Disposable database and cleanup

- PostgreSQL image: `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Task-owned container: `codex-m25-s01-t002-ca6215c18534436d8aab`; database: `fmcg_m25_s01_t002_ca6215c18534436d8aab`.
- Only synthetic records were used. Host port was bound to `127.0.0.1`; no password or persistent volume was created. The runner stopped and removed the exact labeled container after the run.
- V01 and V02 preserve early test-harness assertion failures; V03 records the pre-review pass; V04 records the final post-review-fix pass. Frontend V01 preserves an initial `127.0.0.1` Next.js HMR-origin failure; V02/V03/V04 use `localhost`, and V04 is the final passing run.

## Limits

- This closes only the M25.S01.T002 software workflow using synthetic test data. It does not establish an actual factory's inventory title, legal ownership, carrier/customs integration, production acceptance, or deployment approval.
- Ownership changes require an authorized user's explicit selection and a source reference. The reference is stored as supplied; the system does not validate a legal contract or external document repository.
- User deletion is restricted while an immutable ownership event references that actor; user deactivation remains the way to disable access without erasing attribution.
