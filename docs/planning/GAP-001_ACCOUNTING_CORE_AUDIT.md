# GAP-001 Accounting Core Audit

## Task

`GAP-001A: Audit current implementation: Enterprise-Grade Accounting Core Depth`

This audit was started by explicit user override while `GAP-028K` remains blocked on screenshot capture. No business logic was changed.

## Planning Requirements

The planning document places this gap in Tier 1 critical ERP foundations. Enterprise-grade accounting needs:

- full double-entry general ledger
- chart of accounts setup wizard
- fiscal year and accounting period closing
- journal entries, recurring journals, reversal entries
- accounts receivable and accounts payable aging
- tax rules, withholding tax, VAT/GST localization
- trial balance, balance sheet, income statement, cash-flow statement
- payment allocation and partial reconciliation
- audit-proof immutable posting controls
- multi-currency revaluation
- Kenya-specific tax/reporting workflows where applicable

## Current Implementation Summary

The repository already has a meaningful finance/accounting foundation. It is not only placeholder UI.

| Area | Current Status | Evidence | Notes |
|---|---|---|---|
| Chart of accounts | Partial | `backend/app/models/finance.py`, `backend/app/api/v1/endpoints/finance.py`, `frontend/src/app/dashboard/finance/accounting/chart-of-accounts/page.tsx` | COA model supports hierarchy, account type, control flag, currency, active flag. Missing setup wizard, account templates, strict posting-account validation, retained earnings mapping, and statutory presets. |
| General ledger | Partial | `ChartOfAccount`, `JournalEntry`, `JournalLine`, `/finance/journal/`, `/finance/reports/general-ledger` | Double-entry lines exist and manual journal creation validates total debit equals total credit. Missing reversal entries, recurring journals, immutable posting controls, fiscal-year controls, and automatic posting engine across modules. |
| Journal posting | Partial | `post_journal_entry` in `backend/app/api/v1/endpoints/finance.py` | Posted flag, posted user, and timestamp exist. Missing reversal workflow, no-post-after-close enforcement in journal post path, no immutable ledger guard against later changes at DB/service level. |
| Trial balance | Existing | `finance_service.trial_balance`, `/finance/reports/trial-balance`, frontend trial-balance page | Based on posted journal lines. Needs retained earnings/opening-balance treatment and period/fiscal-year context before production accounting sign-off. |
| Balance sheet | Partial | `finance_service.balance_sheet`, `/finance/reports/balance-sheet`, frontend balance-sheet page | Produces assets/liabilities/equity and `is_balanced`. Missing statement layout controls, retained earnings, comparative periods, and finalized period reporting. |
| Profit and loss | Partial | `finance_service.profit_and_loss`, `/finance/reports/profit-loss`, frontend profit-loss page | Uses revenue and expense accounts. Missing COGS integration, gross margin sectioning, period close treatment, dimensions, and comparative statements. |
| Cash-flow statement | Missing | No dedicated model/service/endpoint/page found | `AccountingDashboard.cash_flow` is receivables minus payables, not a real cash-flow statement. |
| Accounting periods | Partial | `AccountingPeriod`, `PeriodStatus`, `/finance/accounting/periods/`, period-closing frontend page | Period rows can be opened/closed/locked. Missing fiscal year model, close checklist, subledger reconciliation gates, and hard enforcement across every posting endpoint. |
| Exchange rates | Partial | `ExchangeRate`, `RateSource`, `/finance/exchange-rates/`, conversion helper | Daily KES rates and conversion exist. Missing realized/unrealized FX gain/loss posting, revaluation runs, multi-currency subledger balances, and automated source connectors. |
| Purchase invoices/AP | Partial | `PurchaseInvoice`, `PurchaseInvoiceLine`, `PurchasePayment`, purchase invoice frontend pages | Supplier invoice and payments exist. Missing AP aging endpoint/page as a first-class report, payment allocation, credit notes, withholding tax integration, approval/payment hold flow, and automatic AP postings. |
| Sales invoices/AR | Partial | `backend/app/models/sales.py`, finance accounting sales invoice endpoints, customer ledger page | Sales invoice/payment data exists and customer ledger aggregates outstanding balance. Missing AR aging report with buckets, payment allocation across multiple invoices, credit note handling, dunning integration to GL, and automatic AR/revenue/tax postings. |
| Bank/M-Pesa/cash | Partial | `CashAccount`, `CashTransaction`, `MpesaReconciliation`, bank reconciliation module | Cash/bank accounts and M-Pesa matching exist. Missing complete payment allocation and reliable ledger posting for all cash movements. |
| Bank reconciliation | Partial | `backend/app/models/bank_reconciliation.py`, endpoint/service/lib/pages | Bank statements, lines, rules, matches, adjustments, AI recommendations exist. Needs tighter GL posting/adjustment workflow and production evidence around statement close. |
| Tax/VAT/withholding | Partial | `backend/app/models/tax_regulatory.py`, `frontend/src/app/dashboard/tax`, VAT return page | Tax categories/rules/transactions/eTIMS/VAT returns/withholding records exist. Missing guaranteed integration into invoices and GL postings, jurisdiction presets, VAT return lock/submit controls, and tax audit evidence pack. |
| Fixed assets | Partial | `backend/app/models/fixed_assets.py`, fixed assets pages | Asset categories/assets/depreciation/disposal/revaluation fields exist. Needs confirmed GL posting integration, depreciation posting run, impairment/revaluation controls, and audit locks. |
| Cost centers/dimensions | Partial | `backend/app/models/dimensions.py`, dimensions pages | Dimension types/values/cost centers/allocation rules/runs/reclassification exist. Finance reports do not yet consistently filter/post by dimensions. |
| Budgets | Partial | `Budget`, `BudgetLine`, `/finance/budgets/`, budget frontend page | Budget vs actual exists using posted GL lines. Needs fiscal-year controls, approval matrix, revision audit, and actuals by dimensions. |
| Production costing | Partial | `ProductionCostEntry`, `ProductCost`, `production_costing`, `bom_costing`, production costing page | Production cost rollups exist but are not yet a full accounting posting engine into WIP/FG/variance GL. |
| Landed cost | Partial | `backend/app/models/landed_cost.py`, landed-cost frontend pages | Landed cost allocation exists. Needs guaranteed inventory valuation and AP/clearing GL postings. |
| Invoice matching | Partial | `backend/app/models/invoice_match.py`, invoice-match pages | Three-way match model is strong. Needs final payable/posting integration and approval evidence. |

## Backend Files Audited

| File | What It Contains |
|---|---|
| `backend/app/models/finance.py` | Core COA, journal, cash, M-Pesa reconciliation, costing, budget, exchange-rate, accounting-period, purchase-invoice/payment models. |
| `backend/app/schemas/finance.py` | Pydantic schemas for COA, journal, cash, reports, purchase invoices, ledgers, periods, exchange rates. |
| `backend/app/api/v1/endpoints/finance.py` | Finance API endpoints for COA, journal, posting, cash accounts, M-Pesa reconciliation, costing, budgets, reports, accounting periods, exchange rates, sales/purchase invoices, payments, ledgers, dashboard. |
| `backend/app/services/finance_service.py` | Production cost rollup, M-Pesa matching, cash/payment reports, receivables, budget vs actual, trial balance, P&L, balance sheet, GL drilldown, FX conversion. |
| `backend/app/crud/finance.py` | CRUD helpers for COA, journals, cash transactions, reconciliations, costing, budgets. |
| `backend/app/models/bank_reconciliation.py` | Bank account, statement, statement line, match, rule, adjustment, AI recommendation models. |
| `backend/app/models/invoice_match.py` | Three-way invoice matching, tolerance, duplicate, review, AI recommendation models. |
| `backend/app/models/landed_cost.py` | Landed cost header/lines/GRN links/allocation lines/inventory adjustment models. |
| `backend/app/models/fixed_assets.py` | Fixed asset category, asset, depreciation schedule, event, disposal, component, AI recommendation models. |
| `backend/app/models/tax_regulatory.py` | Country tax config, tax categories/rules/mappings/transactions/eTIMS/VAT/withholding models. |
| `backend/app/models/dimensions.py` | Cost center, dimensions, allocations, validation, reclassification models. |

## Frontend Files Audited

Finance/accounting frontend pages exist under:

- `frontend/src/app/dashboard/finance`
- `frontend/src/app/dashboard/finance/accounting`
- `frontend/src/app/dashboard/bank-reconciliation`
- `frontend/src/app/dashboard/invoice-match`
- `frontend/src/app/dashboard/landed-cost`
- `frontend/src/app/dashboard/fixed-assets`
- `frontend/src/app/dashboard/dimensions`
- `frontend/src/app/dashboard/tax`
- `frontend/src/app/dashboard/analytics/finance`
- `frontend/src/app/dashboard/reports/finance`
- `frontend/src/app/dashboard/reports/payments`

The UI has broad surface coverage, but runtime wiring and complete workflow behavior still need feature-by-feature verification.

## Migration Evidence

Relevant migrations already exist, including:

- `backend/alembic/versions/a1b2c3d4e5f6_finance_accounting_module.py`
- `backend/alembic/versions/e7f8a9b0c1d2_bank_reconciliation.py`
- `backend/alembic/versions/d6e7f8a9b0c1_three_way_invoice_matching.py`
- `backend/alembic/versions/c5d6e7f8a9b0_landed_cost_allocation.py`
- `backend/alembic/versions/20260510_0710_fix_fixed_assets_schedule_enum.py`
- `backend/alembic/versions/c8d9e0f1a2b3_production_costing.py`

The model surface is broader than the initial finance migration, so schema reconciliation should be verified before adding new accounting tables.

## Critical Gaps To Design Next

| Gap | Why It Matters | Suggested Next Design Direction |
|---|---|---|
| Fiscal year model | Periods exist, but fiscal-year close is not modeled. | Add fiscal year entity with period ownership, status, close/reopen rules, and retained earnings configuration. |
| Immutable posted ledger | Posted journals are flagged but not fully protected from mutation. | Add service/DB guards for posted entries/lines; only reversal entries should correct posted accounting. |
| Reversal entries | Required for audit-safe corrections. | Add reversal link fields and reversal endpoint/service that creates an opposite journal. |
| Recurring journals | Required for accruals, prepayments, payroll, rent, utilities, depreciation. | Add recurring journal template/schedule/generation run. |
| Posting engine | Subledgers do not consistently create GL impact. | Add accounting posting service with posting rules per source document and idempotent source keys. |
| Period close enforcement | Period close should block postings everywhere. | Add central `assert_period_open(entry_date)` used by all posting paths. |
| AR/AP aging | Ledgers exist but aging buckets are not first-class. | Add AR/AP aging services/endpoints/pages with bucket configuration. |
| Payment allocation | Payments update one invoice but do not support robust allocation/reconciliation. | Add payment header/allocation models for partial/multi-invoice allocation and unapplied cash. |
| Cash-flow statement | Missing real statement. | Add direct or indirect cash-flow report based on posted journals/cash transactions. |
| Multi-currency revaluation | Exchange rates exist but no revaluation postings. | Add revaluation run, unrealized gain/loss accounts, and audit trail. |
| Tax-to-GL integration | Tax models exist but invoice/GL posting integration is incomplete. | Connect invoice tax calculation to tax transaction records and GL tax payable/receivable accounts. |
| Kenya localization | eTIMS/VAT/withholding models exist, but production workflow is incomplete. | Define Kenya tax profile, KRA/eTIMS status workflow, VAT return close/submit/audit pack. |

## Acceptance Criteria Result

`GAP-001A` is complete: current implementation, partial areas, missing enterprise accounting requirements, likely files, and next design direction are documented.

No schema, model, service, API, or frontend business logic was changed in this audit step.

