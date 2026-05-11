# GAP-002 Posting Integration Schema Design

## Task

`GAP-002B: Design data model/schema: Accounting-to-Inventory-to-Manufacturing Posting Integration`

This is a design-only checkpoint. No database migration, ORM model, service, API, or frontend behavior is changed in this task.

## Design Goal

Connect operational inventory, procurement, production, and landed-cost events to auditable finance postings without replacing the existing stock ledger or GAP-001 accounting foundation.

The target design must support:

- idempotent operational posting batches
- journal linkage from stock and source documents
- GRNI, WIP, finished-goods, landed-cost, variance, and adjustment postings
- accounting-period enforcement before operational events create GL impact
- reversal by linked journal/reversal batch, not direct mutation
- additive migration steps that preserve current development data

## Current Model Facts Reviewed

| Area | Existing Field / Model | Design Impact |
|---|---|---|
| Stock ledger | `StockMovement` has `unit_cost` and `total_cost` but no finance linkage. | Add nullable accounting linkage to stock movements. |
| Procurement receipt | `GRNLine.stock_movement_id` exists. | GRN line can be linked to both movement and posting batch/journal. |
| Production material issue | `MaterialConsumption.stock_movement_id` exists. | Material issue can be tied to WIP/raw-material posting. |
| Finished goods receipt | `FinishedGoodsReceipt.stock_movement_id` exists. | Finished-goods receipt can be tied to FG/WIP posting. |
| Landed cost | `LCInventoryAdjustment.journal_ref` exists, but no FK journal/batch linkage. | Replace string-only traceability with nullable accounting FKs. |
| Accounting foundation | `AccountingPostingBatch` and `AccountingPostingRule` exist from GAP-001. | Reuse these instead of creating a parallel posting engine. |

## Additive Schema Design

### 1. Stock Movement Accounting Linkage

Add nullable fields to `stock_movements`:

| Field | Type | Purpose |
|---|---|---|
| `posting_batch_id` | UUID FK to `accounting_posting_batches.id`, nullable | Links the movement to the idempotent finance posting batch. |
| `journal_entry_id` | UUID FK to `journal_entries.id`, nullable | Direct journal trace for reconciliation/reporting. |
| `accounting_status` | enum, nullable/default `NOT_REQUIRED` or `PENDING` | Shows whether the movement is pending, posted, failed, reversed, or exempt. |
| `valuation_method` | enum/string, nullable | Captures the costing basis used at posting time. |
| `valuation_amount` | Numeric(18, 4), nullable | Accounting value posted for the movement. |
| `valuation_currency` | String(10), nullable/default company currency | Currency of the posted value. |
| `posting_error` | Text, nullable | Last posting failure, safe for operational diagnostics. |

Indexes:

- `stock_movements.posting_batch_id`
- `stock_movements.journal_entry_id`
- `stock_movements.accounting_status`
- composite index on `movement_date`, `stock_type`, `movement_type`

Rationale: `StockMovement` remains the operational ledger. Accounting links are nullable so existing development rows and non-financial movements remain valid.

### 2. Source Document Posting Linkage

Add nullable fields to source line tables that already produce inventory/accounting impact:

| Table | Fields |
|---|---|
| `grn_lines` | `posting_batch_id`, `journal_entry_id`, `accounting_status`, `posting_error` |
| `material_consumptions` | `posting_batch_id`, `journal_entry_id`, `accounting_status`, `posting_error` |
| `finished_goods_receipts` | `posting_batch_id`, `journal_entry_id`, `accounting_status`, `posting_error` |
| `lc_allocation_lines` | `posting_batch_id`, `journal_entry_id`, `accounting_status`, `posting_error` |
| `lc_inventory_adjustments` | `posting_batch_id`, `journal_entry_id`, `accounting_status`, `posting_error` |

Rationale: finance users often reconcile from the source document, not only the stock ledger. These fields keep traceability visible without changing current workflow status fields.

### 3. Operational Posting Event Detail Table

Add a new table named `operational_posting_events`.

Suggested columns:

| Field | Type | Purpose |
|---|---|---|
| `id` | UUID PK | Event row identity. |
| `source_module` | String(80), indexed | `procurement`, `production`, `inventory`, `landed_cost`, `sales`, etc. |
| `source_event` | String(80), indexed | Event type, such as `GRN_RECEIPT_POSTED` or `MATERIAL_ISSUED_TO_WIP`. |
| `source_id` | String(80), indexed | Source document/header ID. |
| `source_line_id` | String(80), nullable/indexed | Source line ID when posting is line-level. |
| `stock_movement_id` | UUID FK to `stock_movements.id`, nullable | Associated inventory ledger movement. |
| `posting_batch_id` | UUID FK to `accounting_posting_batches.id`, nullable | Batch created or reused for idempotency. |
| `journal_entry_id` | UUID FK to `journal_entries.id`, nullable | Journal created by the event. |
| `status` | enum | `PENDING`, `POSTED`, `FAILED`, `REVERSED`, `NOT_REQUIRED`. |
| `event_date` | Date | Accounting period validation date. |
| `amount` | Numeric(18, 4), nullable | Amount posted. |
| `currency` | String(10), nullable | Posting currency. |
| `idempotency_key` | String(220), unique | Prevents double posting on retry. |
| `reversal_event_id` | UUID FK to `operational_posting_events.id`, nullable | Links reversal/correction events. |
| `error_message` | Text, nullable | Last safe posting error. |
| `created_by_id` | UUID FK to `users.id`, nullable | Actor/system user. |

Rationale: `AccountingPostingBatch` handles one source event at the finance level. The event table adds line-level operational traceability when one source document generates multiple movements or journal lines.

### 4. Inventory Account Mapping

Add a new table named `inventory_account_mappings`.

Suggested columns:

| Field | Type | Purpose |
|---|---|---|
| `id` | UUID PK | Mapping identity. |
| `stock_type` | enum/string, nullable | Raw material, packaging, finished goods, etc. |
| `product_id` | UUID FK to `products.id`, nullable | Product-specific override. |
| `material_id` | UUID FK to `materials.id`, nullable | Material-specific override. |
| `category_key` | String(120), nullable | Category-level fallback if product/material category models are inconsistent. |
| `valuation_method` | enum/string, nullable | Standard, weighted average, FIFO, or current project enum. |
| `inventory_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Inventory asset account. |
| `wip_account_id` | UUID FK to `chart_of_accounts.id`, nullable | WIP account for production consumption. |
| `finished_goods_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Finished goods inventory account. |
| `cogs_account_id` | UUID FK to `chart_of_accounts.id`, nullable | COGS account for sales/issue flows. |
| `grni_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Goods received not invoiced / receipts clearing. |
| `landed_cost_clearing_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Landed cost clearing account. |
| `variance_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Production/inventory variance account. |
| `scrap_account_id` | UUID FK to `chart_of_accounts.id`, nullable | Scrap/write-off expense account. |
| `is_active` | Boolean | Enables phased rollout without deletion. |
| `priority` | Integer | Allows item-specific rules to beat category/default rules. |
| `notes` | Text, nullable | Configuration notes. |

Unique/index guidance:

- Do not over-constrain nullable product/material/category combinations in the first migration.
- Add indexes on `product_id`, `material_id`, `stock_type`, `is_active`, and `priority`.
- Service logic should choose the most specific active mapping first.

Rationale: `AccountingPostingRule` defines event-level debit/credit behavior. `inventory_account_mappings` supplies item/category account selection for inventory valuation and WIP/FG flows.

## Posting Event Types

Introduce a shared enum or string constants for operational event names:

| Event | Expected Posting |
|---|---|
| `GRN_RECEIPT_POSTED` | Dr Inventory, Cr GRNI |
| `SUPPLIER_INVOICE_POSTED` | Dr GRNI and tax recoverable, Cr AP |
| `MATERIAL_ISSUED_TO_WIP` | Dr WIP, Cr Raw Material Inventory |
| `FINISHED_GOODS_RECEIVED` | Dr Finished Goods Inventory, Cr WIP |
| `LAND_COST_ALLOCATED` | Dr Inventory/Landed Cost Asset, Cr Landed Cost Clearing/AP |
| `INVENTORY_ADJUSTMENT_GAIN` | Dr Inventory, Cr Inventory Variance |
| `INVENTORY_ADJUSTMENT_LOSS` | Dr Inventory Variance/Scrap, Cr Inventory |
| `CYCLE_COUNT_VARIANCE_POSTED` | Dr/Cr Inventory and variance according to sign |
| `SALES_DISPATCH_COGS_POSTED` | Dr COGS, Cr Finished Goods Inventory |
| `OPERATIONAL_POSTING_REVERSED` | Reversal journal created by GAP-001 helper |

## Period And Idempotency Rules

- Every posting-capable operational service must call `assert_posting_period_open(event_date)` before creating journal impact.
- Every posting event must use a deterministic idempotency key.
- Suggested key format: `{source_module}:{source_event}:{source_id}:{source_line_id or header}`.
- Re-running a posting call must return the existing `AccountingPostingBatch` and journal instead of creating duplicates.
- If a source document can be unposted/cancelled, create a reversal event and reversal journal; do not mutate the original journal to hide history.

## Service Boundary Design

The next business-logic task should preserve this split:

| Layer | Responsibility |
|---|---|
| Inventory/procurement/production/landed-cost services | Create operational rows and stock movements. |
| Finance posting service | Resolve account mappings, validate period, create balanced journal entries, update posting batch status. |
| API endpoints | Trigger existing service workflows and return source document plus posting status. |
| Frontend | Display posting state and safe error messages; never calculate GL entries directly. |

## Migration Strategy For GAP-002C

The first migration should be additive only:

1. Create the operational posting status enum.
2. Create `operational_posting_events`.
3. Create `inventory_account_mappings`.
4. Add nullable posting/journal/status/error columns to `stock_movements`.
5. Add nullable posting/journal/status/error columns to `grn_lines`.
6. Add nullable posting/journal/status/error columns to `material_consumptions`.
7. Add nullable posting/journal/status/error columns to `finished_goods_receipts`.
8. Add nullable posting/journal/status/error columns to landed-cost allocation and adjustment tables.
9. Add indexes and foreign keys with `ondelete="SET NULL"` where appropriate.
10. Do not backfill journals automatically in the migration.

Existing rows should remain valid. If needed, mark old operational rows as `PENDING` or `NOT_REQUIRED` through a later reconciliation/admin task, not an irreversible migration.

## Acceptance Criteria For Later Implementation

GAP-002 implementation should not be considered complete until tests prove:

- GRN posting creates or reuses one idempotent accounting batch and balanced journal.
- Material issue creates WIP/raw-material accounting impact.
- Finished goods receipt creates FG/WIP accounting impact.
- Landed cost posting links allocation/adjustment rows to journal impact.
- Closed accounting periods block operational GL posting.
- Missing account mappings return a clear safe error.
- Retrying a posting action does not double-post.
- Reversal creates linked reversal events and reversal journals.

## Design Decision Summary

- Reuse `AccountingPostingBatch` and `AccountingPostingRule`.
- Add nullable journal/posting links to existing source rows.
- Add `operational_posting_events` for line-level traceability and reversals.
- Add `inventory_account_mappings` for item/category-level account resolution.
- Keep migrations additive and non-destructive.
- Keep frontend out of accounting calculations.

