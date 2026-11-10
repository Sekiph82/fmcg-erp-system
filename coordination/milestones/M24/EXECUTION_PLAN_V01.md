# M24 — Material Flow execution plan

**Authority:** root `TASKS.md`; implementation is limited to its current exact task.  
**Scope:** the 16 M24 tasks in S01–S04, using canonical `ProductionOrder` records and the existing stock, lot, reservation, material-flow, and genealogy models. No live factory, employee, or inventory data is assumed.

## Implementation batches

1. **Reservation and staging (S01):** bind reservations to released/in-progress production orders and their source warehouse; generate pick lists from reservations; establish warehouse/location staging; apply lot recommendations and FEFO rules.
2. **Material transactions (S02):** issue against reservations; record actual consumption; return excess; record scrap/spillage with attributable inventory movements.
3. **WIP and finished goods (S03):** model WIP transfers and bulk/intermediate movement; receive finished goods; link packaging consumption to the order and its genealogy.
4. **Integrity and closure (S04):** make stock and production changes atomic; create attributable genealogy events; constrain reversals/corrections; perform milestone acceptance and close.

## M24.S01.T001 implementation assumptions

- A reservation may be created only for a released or in-progress order, from its source warehouse, and only for active material with released, unblocked, unexpired stock.
- Quantities are converted to the material's inventory UOM and rounded upward to the stock precision already used by production readiness.
- Reservation rows and `stocks.quantity_reserved` / `quantity_available` change in one transaction under deterministic stock-row locks. Cancellation releases only the unissued quantity; order cancellation releases outstanding reservations in the same transaction.
- This task does not establish FEFO selection policy; S01.T004 owns lot recommendation and enforcement. Until then allocation is deterministic by stock-row identity.
- Reservations remain synthetic ERP records. No physical picking, factory activity, or live stock is claimed.
- T003 location semantics: source location is copied from each allocated stock row and validated against an active, unblocked location in an active RAW_MATERIAL or STAGING zone in the order's source warehouse. A null source is shown as unassigned and is never inferred. Staging must be an active, unblocked location in an active STAGING zone in that same warehouse: zero configured locations leaves destination unassigned, one is selected automatically, and multiple locations require an explicit selection. Existing reservations are not backfilled because their historical locations are unknown.
- T004 applies FEFO to production material reservations: eligible dated lots sort by earliest expiry first; missing-expiry lots follow dated lots, with untracked stock last; ties resolve by manufacture date, lot number, then stock-row ID. Expired, quarantined, held, non-released, non-FEFO-eligible, blocked, or unavailable stock is excluded. A fixed lot must be eligible and match the first FEFO recommendation; otherwise the request is rejected with the recommended lot. Material reservations are the scope here; the separate WMS product/shipment pick flow remains outside this task, consistent with the GAP-019 audit's deferred WMS pick-time coordination.

## M24.S02.T001 implementation assumptions

- Material issue is a dedicated, authenticated posting against an active reservation. Each requested line must identify a reservation line and may not exceed its outstanding reserved quantity.
- Reservation lines retain the exact source-stock row selected at reservation time. Legacy rows without that identity are rejected for issue instead of resolving an ambiguous stock row at posting time.
- One database transaction writes the POSTED flow header/lines, append-only stock movements, stock on-hand/reserved/available balances, issued quantities, and reservation status. An idempotency key serializes retries and returns the original transaction only when actor, reservation, and line quantities match.
- Issue requires production-order inventory edit scope and rechecks source-stock identity, arithmetic, location availability, and lot release/hold/expiry/FEFO eligibility under row locks. A raw material issue cannot be created or posted through generic draft routes, and generic reversal is blocked until an inventory-aware reversal exists.
- Issue records actual material leaving reserved inventory; it does not claim that production consumed the material. S02.T002 records actual consumption separately.
- Cancellation and issue acquire the production-order lock before the reservation lock so those state changes serialize. Unresolvable legacy reservations remain untouched and require a separately evidenced correction.

## M24.S02.T002 implementation assumptions

- Actual consumption is a separate event after inventory issue. It must reference the exact posted RAW_ISSUE flow line for the same in-progress production order and material; the issued quantity and UOM are derived from that line, not caller-supplied values.
- Each event records only actual consumed quantity. Returns and scrap remain separate S02.T003/S02.T004 events; consumption does not reduce warehouse stock a second time.
- Consumption quantity is finite, positive, and at the established 0.001 precision. Cumulative consumption, returns, and scrap linked to one issue line cannot exceed that line's issued quantity.
- The authenticated actor must have inventory edit scope for the order's source warehouse. Optional work-order attribution must belong to the same order, be in progress, and match any work order already attached to the issue.
- An idempotency key returns only the same actor's identical issue-line event. Older unlinked consumption for the same order/material is not allocated speculatively; it blocks new linked consumption until its history is resolved.
- The consumption event, issued-line reference, remaining variance snapshot, and idempotency identity commit together. Inventory movements and stock balances remain those written by S02.T001.

## M24.S02.T003 implementation assumptions

- An excess return references one posted reservation-based material issue line and is limited to its issued quantity minus linked consumption, prior returns, and scrap. Legacy unlinked consumption blocks the return because the unused balance cannot be established.
- Return is an authenticated, idempotent, atomic event: it creates a posted RETURN flow/line referencing the issue line, an append-only stock movement, a linked production-consumption return event, and a separate stock row at the original source location.
- Returned stock is marked blocked until review. A source location that is no longer active, usable, or in the same warehouse fails closed; the system does not choose another bin or release returned material automatically.
- A return does not reopen the reservation or change its issued quantity. It reduces the issue line's remaining consumable/returnable balance through the linked event history.
- Generic material RETURN drafts cannot be posted as a substitute for the atomic return path, and the current generic reversal path cannot reverse material issue/return stock. S04.T003 owns inventory-aware correction and reversal.
- Batch reconciliation takes total issued quantity from posted issue flow lines, not the repeated per-event issued snapshot on consumption rows, so multiple partial consumption/return events do not inflate the issued total.

## M24.S02.T004 implementation assumptions

- Scrap/spillage is recorded against a posted reservation-based issue line while the production order is in progress. The exact issue line and original reservation identity determine the material, lot, source, UOM, and remaining quantity.
- Each scrap event requires a positive quantity at 0.001 precision, a reason code (spillage, contamination, damage, process loss, or other), an explanation, the authenticated actor, and an idempotency key. Cumulative consumption, returns, and scrap cannot exceed the issued quantity.
- A posted SCRAP flow event/line and `ProductionConsumption` event are committed together and feed batch reconciliation. Scrap does not decrement warehouse stock again: T001 already posted the inventory issue and a second stock movement would double-count the loss. No financial scrap value is invented where unit cost is unknown.
- The material-flow line is marked scrap/rejected for event history; generic scrap drafts and generic reversal cannot bypass the linked, bounded workflow. S04.T003 owns inventory-aware corrections.

## M24.S03.T001 implementation assumptions

- WIP is the production order's measured output product while the order is IN_PROGRESS. Output quantity uses the order UOM, the order's batch number (or order number as a stable synthetic batch identity), and an active production stage/location in the source warehouse.
- WIP is not raw-material or finished-goods warehouse stock. Its authoritative ledger is the append-only, posted `INTERMEDIATE_CREATE` and `STAGE_TRANSFER` material-flow lines; available balances are derived from those records and retain the exact output-line origin.
- A WIP output cannot exceed the production order's planned quantity. A transfer requires an exact output-line origin, the current source stage/location, positive quantity at 0.001 precision, and an active destination in the same source warehouse. Partial moves leave a balance at the source and create a balance at the destination.
- Output and transfer posting require an authenticated actor with inventory edit access to the order source warehouse. Production-order row locks serialize output and transfer balance checks; idempotency keys return only the same actor's identical posted request. Generic create/confirm/reverse paths cannot bypass WIP posting or correction controls.
- The synthetic model records measured quantities and stage/location history only; it does not claim physical production, create warehouse stock, or infer live factory data. Bulk/intermediate multi-line transfer remains S03.T002.

## M24.S03.T002 implementation assumptions

- A bulk transfer is one atomic, authenticated posting for one in-progress production order containing up to 100 movement lines. Each line references one exact WIP output origin and moves a positive quantity at 0.001 precision from its current stage/location to another configured stage/location in that order's source warehouse.
- The service aggregates requested quantities by origin and source location before writing; every source must have enough posted balance. A batch cannot use one line's destination as another line's source, so balances do not depend on line ordering within the transaction.
- A bulk transaction preserves each origin's product, batch, UOM, and quality status. Partial moves preserve the remainder at its source. The transaction and all lines are append-only WIP lineage; no warehouse stock movement or new output quantity is created.
- One globally serialized idempotency key identifies the complete normalized line set. An identical retry by the original actor returns the original posting; reuse with another actor, order, or line set is rejected. Generic transfer and confirmation routes cannot post product WIP around the dedicated bulk workflow; reversal remains gated for S04.T003.

## M24.S03.T003 implementation assumptions

- The existing authenticated production-order completion remains the single finished-goods receipt path because it already posts the stock movement, finished-goods lot/receipt, configured quality inspection, and material genealogy in one transaction.
- If an order has no M24 WIP output ledger, preserve the established completion behavior for legacy orders. If WIP output exists, the completion quantity must equal the entire available WIP balance across all exact output origins and stage/location balances; partial or excess receipts are rejected until an explicit correction workflow exists.
- The WIP-to-finished-goods ledger event is recorded with the production completion and stock receipt in the same database transaction. Each event line consumes an exact WIP origin at its current source stage/location, carries the source lot/batch/UOM/quality, and points to the order's target warehouse. Existing production receipt records remain authoritative for the received finished-goods lot and stock movement.
- Generic material-flow FG receipt drafts, confirmations, and reversals cannot bypass production completion or mutate the WIP balance without the inventory-aware production workflow. WIP/finished-goods corrections remain gated for S04.T003.
- This synthetic workflow records ERP state only. It makes no claim about physical output, a real factory, or actual staff activity.

## M24.S03.T004 implementation assumptions

- Reserved packaging is issued through a dedicated authenticated `PKG_ISSUE` transaction using exact reservation lines and the same stock, lot, warehouse, actor, idempotency, return, and scrap controls as other production material issues. Generic packaging drafts cannot post or reverse inventory.
- Actual package consumption references one exact posted packaging issue line for the same in-progress production order. It is quantity-bounded and append-only; issuing stock does not itself claim consumption.
- On production-order completion, actual packaging consumption events are linked to the finished-goods trace event and lot. A tracked package lot also creates a `packed_from` lot-genealogy edge; untracked packaging retains material, order, issue-line, and finished-lot trace-event lineage without inventing a source lot.
- If packaging for a BOM material was separately issued through the packaging workflow, order completion does not consume that same BOM material again. Unissued packaging keeps the established BOM completion path.
- Unconsumed issued packaging remains eligible for the existing linked return/scrap workflows; the task does not assume every issued quantity was physically consumed.
- These are synthetic ERP records only; no physical factory, staff, or real packaging activity is implied.

## M24.S04.T002 implementation assumptions

- At production completion, actual consumption events linked to exact posted M24 reservation issue lines are written into the finished-goods transformation event. Trace quantities come from `ProductionConsumption`, never from issued quantity or caller-entered estimates.
- A material already posted through a reservation-based M24 issue is not issued again by the legacy BOM completion path. This avoids a second stock deduction while retaining legacy BOM consumption for materials with no M24 issue history.
- Completing an order releases only unissued reservation balances in the same transaction as the finished-goods receipt and completion. Issued quantities remain in their consumption/return/scrap histories; no reservation release may change on-hand stock.
- Raw-material lots create `intermediate_from` genealogy edges and packaging lots create `packed_from` edges. The trace event line keeps the exact issue-line source location and consumption-event identity. An untracked source remains visible as a trace event line without an invented lot edge.
- Returns and scrap remain separate issue-line events; only actual consumed quantity is linked to the finished-goods lot.
- These are synthetic ERP records only; no physical factory, staff, or actual consumption is implied.

## M24.S04.T003 implementation assumptions

- Generic reversal is fail-closed for every posted material-flow transaction until one atomic correction path can update all affected stock, reservation, WIP, finished-goods, genealogy, and accounting records. Writing an opposite-looking flow row and marking the source REVERSED is not a correction.
- Generic `REVERSAL` drafts cannot be created or confirmed. The service layer enforces the same boundary so a future endpoint cannot bypass it.
- Unused issued material can use the existing exact issue-line return or scrap workflows, subject to their own quantity and status rules. This task does not broaden those rules.
- WIP and finished-goods corrections remain blocked. No stock balance, genealogy edge, financial amount, physical event, or approval is fabricated to simulate a correction.
- These controls preserve source transactions and their existing history. An inventory-aware compensating-event workflow remains future work.

## M24.S01.T002 implementation assumptions

- Generate a read-only pick-list view from the outstanding quantities on an active reservation, grouped by material and allocated lot. Do not create another stock allocation or mutate inventory when rendering it.
- Keep the established WMS `PickingTask` flow for product/shipment picking; its model requires a product and does not represent raw-material reservation lines.
- S01.T003 adds source/staging identity to reservation lines and the read-only pick list. FEFO recommendation/enforcement remains S01.T004.

## Validation and audit boundary

- Use syntax/compile and diff checks while implementing. Defer comprehensive API, disposable-PostgreSQL, regression, frontend, migration, and E2E suites to S04.T004, except a focused check needed to diagnose a concrete failure or protect a critical inventory invariant.
- At S04.T004, run the consolidated M24 validation against a task-owned disposable database, obtain one independent code review and one consolidated security review, resolve findings, then record evidence and accept implemented task rows honestly.
- Preserve prior evidence and unrelated local owner changes. Synchronize with `origin/main` before further implementation and publish only explicitly scoped, verified work.
