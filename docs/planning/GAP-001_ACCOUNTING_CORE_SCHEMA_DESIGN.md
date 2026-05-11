# GAP-001 Accounting Core Schema Design

## Task

`GAP-001B: Design data model/schema: Enterprise-Grade Accounting Core Depth`

This is a design-only checkpoint. It does not change database schema, ORM models, services, API behavior, or frontend behavior. The next task, `GAP-001C`, should turn the approved design into an Alembic migration.

## Design Goals

The current finance module already has chart of accounts, journal entries, journal lines, accounting periods, exchange rates, purchase invoices, supplier payments, sales invoice integration, cash accounts, budgets, dimensions, tax models, fixed assets, bank reconciliation, landed cost, and invoice matching. The schema design should extend that foundation rather than replacing it.

The enterprise accounting core should add:

- fiscal-year ownership for accounting periods
- audit-safe posted ledger controls
- reversal entries instead of direct posted-entry edits
- recurring journal templates and generation history
- idempotent accounting posting from source documents
- payment allocation across AR/AP documents
- AR/AP aging support
- multi-currency revaluation runs
- period-close checklist and posting gates
- tax-to-GL and Kenya localization hooks

## Existing Tables To Preserve

| Existing Model | Keep | Design Impact |
|---|---|---|
| `ChartOfAccount` | Yes | Add setup/template support later; do not replace existing hierarchy or account type fields. |
| `JournalEntry` | Yes | Add status/reversal/source-posting fields while preserving current `is_posted`, `posted_at`, and `posted_by_id` compatibility. |
| `JournalLine` | Yes | Preserve debit/credit structure; future posting validation should enforce active posting accounts and open periods. |
| `AccountingPeriod` | Yes | Attach periods to fiscal years and add close checklist state. |
| `ExchangeRate` | Yes | Revaluation runs should use existing rate records before adding external-rate connectors. |
| `PurchaseInvoice`, `PurchasePayment` | Yes | Add AP allocation and posting-log links without breaking current purchase invoice flow. |
| Sales invoice/payment models | Yes | Use existing sales models for AR allocation and ledger aging rather than duplicating invoice headers. |
| `TransactionTax`, VAT, withholding models | Yes | Add posting/log references where required during later integration tasks. |
| Dimension/cost center models | Yes | Keep dimension engine as the cross-module source for cost center and dimension allocation. |

## Proposed Enum Additions

These should be added in `backend/app/models/finance.py` during `GAP-001D` if the migration is accepted.

| Enum | Values | Purpose |
|---|---|---|
| `FiscalYearStatus` | `OPEN`, `CLOSING`, `CLOSED`, `LOCKED` | Controls fiscal-year close and reopen behavior. |
| `JournalStatus` | `DRAFT`, `POSTED`, `REVERSED`, `VOID` | Makes journal lifecycle explicit while keeping `is_posted` as compatibility data. |
| `RecurringJournalFrequency` | `MONTHLY`, `QUARTERLY`, `ANNUALLY`, `CUSTOM` | Defines recurring journal schedule cadence. |
| `RecurringJournalStatus` | `ACTIVE`, `PAUSED`, `CLOSED` | Controls generation eligibility. |
| `PostingBatchStatus` | `DRAFT`, `POSTED`, `FAILED`, `REVERSED` | Tracks source-document accounting posting attempts. |
| `PaymentAllocationPartyType` | `CUSTOMER`, `SUPPLIER` | Differentiates AR and AP allocations. |
| `CurrencyRevaluationStatus` | `DRAFT`, `POSTED`, `REVERSED` | Tracks unrealized FX revaluation lifecycle. |
| `AccountingCloseCheckStatus` | `PENDING`, `PASSED`, `FAILED`, `WAIVED` | Tracks period-close checklist gates. |

## Proposed New Tables

### `fiscal_years`

Represents a fiscal year and owns accounting periods.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `year_code` | string | Unique label such as `FY2026`. |
| `start_date` | date | Required. |
| `end_date` | date | Required. |
| `status` | `FiscalYearStatus` | Default `OPEN`. |
| `base_currency` | string | Default should follow existing company/base currency convention, currently KES-centered in finance services. |
| `retained_earnings_account_id` | FK `chart_of_accounts.id` | Required before year-end close can finalize. |
| `closed_by_id` | FK `users.id`, nullable | Audit field. |
| `closed_at` | datetime, nullable | Audit field. |
| `locked_by_id` | FK `users.id`, nullable | Audit field. |
| `locked_at` | datetime, nullable | Audit field. |
| `notes` | text, nullable | Close comments. |

Recommended constraints:

- `year_code` unique.
- `start_date <= end_date`.
- no overlapping fiscal-year date ranges should be enforced in service validation.

### `accounting_period_close_checks`

Stores close readiness checks for each period.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `period_id` | FK `accounting_periods.id` | Required. |
| `check_code` | string | Example: `TRIAL_BALANCE_BALANCED`, `BANK_RECON_COMPLETE`, `AR_AGING_REVIEWED`. |
| `label` | string | Human-readable checklist item. |
| `status` | `AccountingCloseCheckStatus` | Default `PENDING`. |
| `result_summary` | text, nullable | Short result or waiver reason. |
| `checked_by_id` | FK `users.id`, nullable | Audit field. |
| `checked_at` | datetime, nullable | Audit field. |

Recommended constraints:

- Unique `(period_id, check_code)`.

### `recurring_journal_templates`

Defines recurring accounting entries for accruals, prepayments, rent, utilities, depreciation, and other repeated postings.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `template_no` | string | Unique business identifier. |
| `name` | string | Required. |
| `description` | text, nullable | Optional. |
| `frequency` | `RecurringJournalFrequency` | Required. |
| `status` | `RecurringJournalStatus` | Default `ACTIVE`. |
| `start_date` | date | Required. |
| `end_date` | date, nullable | Optional. |
| `next_run_date` | date | Required for generation. |
| `last_run_date` | date, nullable | Updated after successful generation. |
| `created_by_id` | FK `users.id`, nullable | Audit field. |
| `default_memo` | string, nullable | Journal memo default. |

### `recurring_journal_template_lines`

Defines debit/credit lines for a recurring journal template.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `template_id` | FK `recurring_journal_templates.id` | Required. |
| `account_id` | FK `chart_of_accounts.id` | Required. |
| `debit` | numeric | Default 0. |
| `credit` | numeric | Default 0. |
| `description` | string, nullable | Optional. |
| `cost_center_id` | FK `cost_centers.id`, nullable | Optional if dimensions are enabled for the entry. |

Validation should require total debits to equal total credits at template save time and generation time.

### `accounting_posting_batches`

Provides an idempotent posting record for subledger-to-GL entries. This is the foundation for later GAP-002 integration.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `source_module` | string | Example: `sales`, `procurement`, `inventory`, `production`, `fixed_assets`, `tax`. |
| `source_event` | string | Example: `invoice_posted`, `goods_receipt`, `material_issue`, `production_completion`. |
| `source_id` | UUID/string | Source document ID as text for cross-module flexibility. |
| `source_ref` | string, nullable | Human-readable document number. |
| `status` | `PostingBatchStatus` | Default `DRAFT`. |
| `journal_entry_id` | FK `journal_entries.id`, nullable | Set after successful posting. |
| `idempotency_key` | string | Unique key to prevent duplicate postings. |
| `error_message` | text, nullable | Last failure reason. |
| `posted_by_id` | FK `users.id`, nullable | Audit field. |
| `posted_at` | datetime, nullable | Audit field. |

Recommended constraints:

- Unique `idempotency_key`.
- Unique `(source_module, source_event, source_id)` where the source event should post once.

### `accounting_posting_rules`

Defines configurable GL mapping rules for source events.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `source_module` | string | Required. |
| `source_event` | string | Required. |
| `rule_name` | string | Required. |
| `debit_account_id` | FK `chart_of_accounts.id`, nullable | Used when a rule has a fixed debit side. |
| `credit_account_id` | FK `chart_of_accounts.id`, nullable | Used when a rule has a fixed credit side. |
| `tax_account_id` | FK `chart_of_accounts.id`, nullable | Optional tax posting account. |
| `clearing_account_id` | FK `chart_of_accounts.id`, nullable | Optional GRNI, WIP, landed-cost, or payment clearing account. |
| `is_active` | boolean | Default true. |
| `priority` | int | Lower number wins when multiple rules match. |
| `notes` | text, nullable | Rule explanation. |

The first implementation should keep matching simple and explicit. Avoid a rule-expression engine until real source events need it.

### `payment_allocations`

Supports partial and multi-invoice allocation for customer and supplier payments.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `party_type` | `PaymentAllocationPartyType` | `CUSTOMER` or `SUPPLIER`. |
| `customer_payment_id` | FK to existing sales/customer payment table, nullable | Used for AR allocation. |
| `supplier_payment_id` | FK `purchase_payments.id`, nullable | Used for AP allocation. |
| `sales_invoice_id` | FK to existing sales invoice table, nullable | Used for AR allocation. |
| `purchase_invoice_id` | FK `purchase_invoices.id`, nullable | Used for AP allocation. |
| `allocated_amount` | numeric | Required, greater than 0. |
| `allocation_date` | date | Required. |
| `notes` | text, nullable | Optional. |
| `created_by_id` | FK `users.id`, nullable | Audit field. |

Validation rules:

- For `CUSTOMER`, require customer payment and sales invoice references.
- For `SUPPLIER`, require supplier payment and purchase invoice references.
- Total allocations cannot exceed payment amount.
- Invoice paid amount cannot exceed invoice total.

### `currency_revaluation_runs`

Stores unrealized FX revaluation runs.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `run_no` | string | Unique business identifier. |
| `as_of_date` | date | Required. |
| `currency` | string | Revalued foreign currency. |
| `rate_id` | FK `exchange_rates.id`, nullable | Existing exchange-rate record used. |
| `status` | `CurrencyRevaluationStatus` | Default `DRAFT`. |
| `journal_entry_id` | FK `journal_entries.id`, nullable | Set when posted. |
| `unrealized_gain_account_id` | FK `chart_of_accounts.id` | Required before posting gains. |
| `unrealized_loss_account_id` | FK `chart_of_accounts.id` | Required before posting losses. |
| `created_by_id` | FK `users.id`, nullable | Audit field. |
| `posted_by_id` | FK `users.id`, nullable | Audit field. |
| `posted_at` | datetime, nullable | Audit field. |

### `currency_revaluation_lines`

Stores account-level revaluation details for a run.

Suggested fields:

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. |
| `run_id` | FK `currency_revaluation_runs.id` | Required. |
| `account_id` | FK `chart_of_accounts.id` | Required. |
| `foreign_currency_balance` | numeric | Balance before conversion. |
| `book_base_balance` | numeric | Existing base-currency balance. |
| `revalued_base_balance` | numeric | Balance at revaluation rate. |
| `gain_loss_amount` | numeric | Positive gain or negative loss. |

## Proposed Changes To Existing Tables

### `accounting_periods`

Add:

- `fiscal_year_id` nullable FK to `fiscal_years.id` during migration; later make required after backfill is proven.
- `close_notes` nullable text.
- `closed_by_id` nullable FK to `users.id`.
- `locked_by_id` nullable FK to `users.id`.

Keep:

- existing `status`, `period_start`, `period_end`, `is_current`, `closed_at`, `locked_at`.

### `journal_entries`

Add:

- `status` enum, default derived from current `is_posted`.
- `reversal_of_entry_id` nullable self-FK for reversal journal entries.
- `reversed_by_entry_id` nullable self-FK for the original entry once reversed.
- `source_module` nullable string.
- `source_event` nullable string.
- `source_id` nullable string.
- `source_ref` nullable string.
- `posting_batch_id` nullable FK to `accounting_posting_batches.id`.
- `locked_at` nullable datetime.

Keep:

- existing `is_posted`, `posted_at`, `posted_by_id`, `entry_date`, `reference`, `description`, and line relationship.

Compatibility rule:

- `is_posted = true` should map to `status = POSTED` unless reversal fields indicate `REVERSED`.

### `purchase_payments`

Add only if current payment table does not already support this after inspection in `GAP-001C/D`:

- `unallocated_amount` numeric, default 0.
- `posted_journal_entry_id` nullable FK to `journal_entries.id`.

The first migration may skip these fields if allocation can be calculated from existing amount and `payment_allocations`.

## Report-Only Features That Should Not Add Tables Yet

Some requirements should be implemented as services/endpoints first, not as persistent tables:

| Feature | Reason |
|---|---|
| AR aging | Can be computed from invoices, payments, allocations, and dates. Add snapshot tables only if management needs historical aging snapshots. |
| AP aging | Same as AR aging. |
| Trial balance | Already report-driven from posted journal lines. |
| P&L and balance sheet | Already report-driven; improve layout/retained earnings logic without duplicating statement rows. |
| Cash-flow statement | Should initially be computed from posted GL/cash transactions; persist only if finalized statement packs are required. |

## Validation Rules For Later Implementation

The schema enables these service/API rules:

- Posted journal entries and lines are immutable.
- Posted corrections require a reversal entry, never direct mutation.
- Posting is blocked when the target accounting period is closed or locked.
- Posting is blocked when the fiscal year is closed or locked.
- Journal lines must use active posting accounts.
- Journal templates and journal entries must balance total debit and total credit.
- Source-document postings use idempotency keys.
- Payment allocations cannot over-allocate a payment or invoice.
- Revaluation runs cannot post twice.
- Closing a period requires required checklist gates to pass or be explicitly waived.

## Migration Strategy For GAP-001C

Use a reconciliation-first migration. Do not make destructive changes.

1. Create new enums and tables.
2. Add nullable fields to existing `accounting_periods` and `journal_entries`.
3. Backfill `journal_entries.status` from existing `is_posted`.
4. Create fiscal years from existing period date ranges if periods exist.
5. Link periods to fiscal years when date ranges match.
6. Add indexes and unique constraints only after backfill-safe fields exist.
7. Keep nullable foreign keys where existing development data may be incomplete.
8. Do not drop or rename existing columns.

Recommended indexes:

- `fiscal_years(year_code)`
- `accounting_periods(fiscal_year_id, period_start, period_end)`
- `journal_entries(status, entry_date)`
- `journal_entries(source_module, source_event, source_id)`
- `accounting_posting_batches(idempotency_key)`
- `payment_allocations(party_type, allocation_date)`
- `currency_revaluation_runs(as_of_date, currency, status)`

## Test Requirements For Later Tasks

`GAP-001J` should include focused tests for:

- fiscal-year creation and period linking
- posting blocked in closed/locked periods
- posted journal mutation blocked
- reversal entry creates balanced opposite lines
- recurring journal template validation
- recurring journal generation idempotency
- source posting idempotency via `accounting_posting_batches`
- customer payment partial allocation
- supplier payment partial allocation
- AR/AP aging bucket correctness
- FX revaluation creates balanced journal entries
- period-close checklist gates

## Documentation Requirements For Later Tasks

`GAP-001K` should document:

- accounting period and fiscal-year close workflow
- how to post and reverse journal entries
- recurring journal setup and generation
- AR/AP aging meaning and bucket configuration
- payment allocation workflow
- multi-currency revaluation workflow
- source-document posting audit trail
- Kenya tax posting assumptions and remaining localization limits

## Acceptance Criteria Result

`GAP-001B` is complete when this design is reviewed and committed to the roadmap checkpoint files. The next implementation task is `GAP-001C`, which should create an Alembic migration from this design without changing unrelated business logic.
