# Visible Broken Action Targets

**Date:** 2026-05-21
**Total broken visible buttons/cards/tiles:** 296

## Statistics

| Metric | Count |
|--------|-------|
| Critical severity | 24 |
| High severity | 217 |
| Medium severity | 55 |
| Git history matches found | 22 |
| High-confidence original page found | 5 |
| Recommendation: RESTORE FROM GIT | 5 |
| Recommendation: CONVERT TO SUBVIEW | 291 |

## Supply Chain / Inventory

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0001 | cycle-count/page.tsx | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/entries` | high | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0002 | cycle-count/page.tsx | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/plans` | high | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0003 | cycle-count/page.tsx | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/reports` | medium | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0004 | cycle-count/page.tsx | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/tasks` | high | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0005 | cycle-count/page.tsx | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/variances` | high | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0006 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/bulk-hold-monitor` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0007 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/compliance` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0008 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/customer-rules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0009 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/disposition` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0010 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/expired` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0011 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/fefo-config` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0012 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/lot-aging` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0013 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/near-expiry` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0014 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/production-validation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0015 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/retest-queue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0016 | shelf-life/page.tsx | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/shipment-validation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0017 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/backward` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0018 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/forward` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0019 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/genealogy` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0020 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/mock-recall` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0021 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/recalls` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0022 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/regulatory` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0023 | traceability/page.tsx | /dashboard/inventory?tab=traceability | `/dashboard/traceability/search` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Manufacturing / Planning

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0024 | mrp/page.tsx | /dashboard/planning?tab=mrp | `/dashboard/mrp/forecast` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0025 | mrp/page.tsx | /dashboard/planning?tab=mrp | `/dashboard/mrp/run` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0026 | mrp/page.tsx | /dashboard/planning?tab=mrp | `/dashboard/mrp/suggestions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0027 | kanban/page.tsx | /dashboard/planning?tab=kanban | `/dashboard/kanban/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0028 | kanban/page.tsx | /dashboard/planning?tab=kanban | `/dashboard/kanban/boards` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0029 | kanban/page.tsx | /dashboard/planning?tab=kanban | `/dashboard/kanban/cards` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0030 | kanban/page.tsx | /dashboard/planning?tab=kanban | `/dashboard/kanban/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0031 | kanban/page.tsx | /dashboard/planning?tab=kanban | `/dashboard/kanban/view` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Manufacturing / Production

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0032 | production-execution/page.tsx | /dashboard/production?tab=execution | `/dashboard/production-execution/work-orders` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0033 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/assignment` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0034 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/certs` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0035 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/costing` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0036 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/downtime` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0037 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/machines` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0038 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/operators` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0039 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/performance` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0040 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/runtime` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0041 | machine-ops/page.tsx | /dashboard/production?tab=machine-ops | `/dashboard/machine-ops/teams` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0042 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/bulk-transfer` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0043 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/fg-receipt` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0044 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/history` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0045 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/issue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0046 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/reconciliation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0047 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/reservations` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0048 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/returns` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0049 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/tanks` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0050 | material-flow/page.tsx | /dashboard/production?tab=material-flow | `/dashboard/material-flow/wip-transfer` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Finance

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0051 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/controls` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0052 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/customers-ledger` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0053 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/payments` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0054 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/purchase-invoices` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0055 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/sales-invoices` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0056 | finance/accounting/page.tsx | /dashboard/finance?tab=accounting | `/dashboard/finance/accounting/suppliers-ledger` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0057 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0058 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/balance` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0059 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/import` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0060 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/open-items` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0061 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/rules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0062 | bank-reconciliation/page.tsx | /dashboard/finance?tab=bank-recon | `/dashboard/bank-reconciliation/statements` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0063 | invoice-match/page.tsx | /dashboard/finance?tab=invoice-match | `/dashboard/invoice-match/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0064 | invoice-match/page.tsx | /dashboard/finance?tab=invoice-match | `/dashboard/invoice-match/blocked` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0065 | invoice-match/page.tsx | /dashboard/finance?tab=invoice-match | `/dashboard/invoice-match/duplicates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0066 | invoice-match/page.tsx | /dashboard/finance?tab=invoice-match | `/dashboard/invoice-match/matches` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0067 | invoice-match/page.tsx | /dashboard/finance?tab=invoice-match | `/dashboard/invoice-match/review-queue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0068 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0069 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/assets/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0070 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/assets` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0071 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/categories` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0072 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/depreciation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0073 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/disposal` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0074 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/import` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0075 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/posting` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0076 | fixed-assets/page.tsx | /dashboard/finance?tab=fixed-assets | `/dashboard/fixed-assets/transfer` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0077 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0078 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/allocation-run` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0079 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/allocations` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0080 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/completeness` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0081 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/cost-centers` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0082 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/defaults` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0083 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/reclassify` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0084 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/types` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0085 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/validation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0086 | dimensions/page.tsx | /dashboard/finance?tab=dimensions | `/dashboard/dimensions/values` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0087 | dunning/page.tsx | /dashboard/finance?tab=dunning | `/dashboard/dunning/aging` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0088 | dunning/page.tsx | /dashboard/finance?tab=dunning | `/dashboard/dunning/cases` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0089 | dunning/page.tsx | /dashboard/finance?tab=dunning | `/dashboard/dunning/credit-holds` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0090 | dunning/page.tsx | /dashboard/finance?tab=dunning | `/dashboard/dunning/policies` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0091 | dunning/page.tsx | /dashboard/finance?tab=dunning | `/dashboard/dunning/workqueue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0092 | tax/page.tsx | /dashboard/finance?tab=tax | `/dashboard/tax/regulatory` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0093 | tax/page.tsx | /dashboard/finance?tab=tax | `/dashboard/tax/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0094 | tax/page.tsx | /dashboard/finance?tab=tax | `/dashboard/tax/rules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0095 | tax/page.tsx | /dashboard/finance?tab=tax | `/dashboard/tax/transactions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0096 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/advances` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0097 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0098 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/approval` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0099 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/categories` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0100 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/claims/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0101 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/claims` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0102 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/policies` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0103 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/reimbursement` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0104 | expenses/page.tsx | /dashboard/finance?tab=expenses | `/dashboard/expenses/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |

## HR & Payroll

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0105 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0106 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/candidates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0107 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/interviews` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0108 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/offers` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0109 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/pipeline` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0110 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0111 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/requisitions/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0112 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/requisitions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0113 | recruitment/page.tsx | /dashboard/hr?tab=recruitment | `/dashboard/recruitment/stages` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0114 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/admin` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0115 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0116 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/attendance` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0117 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/documents` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0118 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/leave` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0119 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/notifications` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0120 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/profile` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0121 | ess/page.tsx | /dashboard/hr?tab=ess | `/dashboard/ess/requests` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0122 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0123 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/development-plans` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0124 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/hr-review` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0125 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/manager-queue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0126 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/periods` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0127 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/records/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0128 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/records` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0129 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0130 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/self-review` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0131 | appraisals/page.tsx | /dashboard/hr?tab=appraisals | `/dashboard/appraisals/templates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0132 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0133 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/assignments` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0134 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/certifications` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0135 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/feedback` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0136 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/programs` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0137 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0138 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/sessions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0139 | training/page.tsx | /dashboard/hr?tab=training | `/dashboard/training/skill-matrix` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0140 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0141 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/approval-queue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0142 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/my-timesheets` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0143 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0144 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/time-entry` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0145 | timesheets/page.tsx | /dashboard/hr?tab=timesheets | `/dashboard/timesheets/weekly-view` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Sales

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0146 | price-lists/page.tsx | /dashboard/sales?tab=price-lists | `/dashboard/price-lists/approval-queue` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0147 | contracts/page.tsx | /dashboard/sales?tab=contracts | `/dashboard/contracts/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0148 | contracts/page.tsx | /dashboard/sales?tab=contracts | `/dashboard/contracts/expiring` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0149 | contracts/page.tsx | /dashboard/sales?tab=contracts | `/dashboard/contracts/list` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0150 | contracts/page.tsx | /dashboard/sales?tab=contracts | `/dashboard/contracts/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0151 | recurring-orders/page.tsx | /dashboard/sales?tab=recurring | `/dashboard/recurring-orders/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0152 | recurring-orders/page.tsx | /dashboard/sales?tab=recurring | `/dashboard/recurring-orders/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0153 | recurring-orders/page.tsx | /dashboard/sales?tab=recurring | `/dashboard/recurring-orders/templates/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0154 | recurring-orders/page.tsx | /dashboard/sales?tab=recurring | `/dashboard/recurring-orders/templates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0155 | commissions/page.tsx | /dashboard/sales?tab=commissions | `/dashboard/commissions/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0156 | commissions/page.tsx | /dashboard/sales?tab=commissions | `/dashboard/commissions/payouts` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0157 | commissions/page.tsx | /dashboard/sales?tab=commissions | `/dashboard/commissions/rules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0158 | commissions/page.tsx | /dashboard/sales?tab=commissions | `/dashboard/commissions/transactions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0159 | secondary-sales/page.tsx | /dashboard/sales?tab=secondary | `/dashboard/secondary-sales/analysis` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0160 | secondary-sales/page.tsx | /dashboard/sales?tab=secondary | `/dashboard/secondary-sales/inventory` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0161 | secondary-sales/page.tsx | /dashboard/sales?tab=secondary | `/dashboard/secondary-sales/upload` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0162 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0163 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/pos` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0164 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/reconciliation` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0165 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/route` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0166 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/stock` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0167 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/vans/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0168 | van-sales/page.tsx | /dashboard/sales?tab=van-sales | `/dashboard/van-sales/vans` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0169 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/accounts` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0170 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/activity` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0171 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0172 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/claims` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0173 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/drafts` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0174 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0175 | portal/page.tsx | /dashboard/sales?tab=portal | `/dashboard/portal/users` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Supply Chain / Procurement

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0176 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=suggestions | `/dashboard/procurement-suggestion/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0177 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=suggestions | `/dashboard/procurement-suggestion/groups` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0178 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=suggestions | `/dashboard/procurement-suggestion/suggestions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0179 | procurement-suggestion/page.tsx | /dashboard/procurement?tab=suggestions | `/dashboard/procurement-suggestion/supplier-prices` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0180 | subcontracting/page.tsx | /dashboard/procurement?tab=subcontracting | `/dashboard/subcontracting/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0181 | subcontracting/page.tsx | /dashboard/procurement?tab=subcontracting | `/dashboard/subcontracting/locations` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0182 | subcontracting/page.tsx | /dashboard/procurement?tab=subcontracting | `/dashboard/subcontracting/orders` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0183 | subcontracting/page.tsx | /dashboard/procurement?tab=subcontracting | `/dashboard/subcontracting/stock` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0184 | subcontracting/page.tsx | /dashboard/procurement?tab=subcontracting | `/dashboard/subcontracting/yield` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0185 | landed-cost/page.tsx | /dashboard/procurement?tab=landed-cost | `/dashboard/landed-cost/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0186 | landed-cost/page.tsx | /dashboard/procurement?tab=landed-cost | `/dashboard/landed-cost/documents` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0187 | landed-cost/page.tsx | /dashboard/procurement?tab=landed-cost | `/dashboard/landed-cost/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Quality

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0188 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0189 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/allergen` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0190 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/ccp` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0191 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/corrective-actions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0192 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/deviations` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0193 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/haccp` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0194 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/inspections` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0195 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/quarantine` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0196 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0197 | qms/page.tsx | /dashboard/quality?tab=qms | `/dashboard/qms/templates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0198 | allergen/page.tsx | /dashboard/quality?tab=allergen | `/dashboard/allergen/change-logs` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0199 | allergen/page.tsx | /dashboard/quality?tab=allergen | `/dashboard/allergen/material-profiles` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0200 | allergen/page.tsx | /dashboard/quality?tab=allergen | `/dashboard/allergen/product-allergens` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Logistics

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0201 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/drivers` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0202 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/fuel` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0203 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/incidents` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0204 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/maintenance` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0205 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0206 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/trips` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0207 | fleet/page.tsx | /dashboard/logistics?tab=fleet | `/dashboard/fleet/vehicles` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Documents & Communication

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0208 | chatter/page.tsx | /dashboard/communication?tab=chatter | `/dashboard/chatter/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0209 | chatter/page.tsx | /dashboard/communication?tab=chatter | `/dashboard/chatter/feed` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0210 | chatter/page.tsx | /dashboard/communication?tab=chatter | `/dashboard/chatter/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0211 | chatter/page.tsx | /dashboard/communication?tab=chatter | `/dashboard/chatter/search` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0212 | calendar/page.tsx | /dashboard/communication?tab=calendar | `/dashboard/calendar/availability` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0213 | calendar/page.tsx | /dashboard/communication?tab=calendar | `/dashboard/calendar/new-event` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0214 | calendar/page.tsx | /dashboard/communication?tab=calendar | `/dashboard/calendar/resources` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0215 | calendar/page.tsx | /dashboard/communication?tab=calendar | `/dashboard/calendar/view` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0216 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0217 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/list` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0218 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/preferences` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0219 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0220 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/schedules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0221 | notification-center/page.tsx | /dashboard/communication?tab=notifications | `/dashboard/notification-center/templates` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0264 | documents/compliance/page.tsx | /dashboard/documents?tab=compliance | `/dashboard/documents/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0265 | knowledge-base/page.tsx | /dashboard/documents?tab=knowledge-base | `/dashboard/knowledge-base/articles/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0266 | knowledge-base/page.tsx | /dashboard/documents?tab=knowledge-base | `/dashboard/knowledge-base/articles` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Intelligence / Analytics

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0222 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/finance` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0223 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/inventory` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0224 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/marketing` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0225 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/payments` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0226 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/procurement` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0227 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/production` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0228 | reports/page.tsx | /dashboard/analytics?tab=reports | `/dashboard/reports/sales` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0229 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0230 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/builder` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0231 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/catalog` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0232 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/dashboards` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0233 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/saved` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0234 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/schedules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0235 | report-builder/page.tsx | /dashboard/analytics?tab=report-builder | `/dashboard/report-builder/viewer` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Administration

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0236 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0237 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/fields` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0238 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/form-builder` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0239 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/new-field` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0240 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/values` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0241 | custom-fields/page.tsx | /dashboard/admin?tab=custom-fields | `/dashboard/custom-fields/workflow-rules` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0242 | mobile/page.tsx | /dashboard/admin?tab=mobile | `/dashboard/mobile/approvals` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0243 | mobile/page.tsx | /dashboard/admin?tab=mobile | `/dashboard/mobile/devices` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / Marketing

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0244 | marketing/campaigns/page.tsx | /dashboard/marketing?tab=campaigns | `/dashboard/marketing/campaigns/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0245 | marketing/promotions/page.tsx | /dashboard/marketing?tab=promotions | `/dashboard/marketing/promotions/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0246 | marketing/trade-spend/page.tsx | /dashboard/marketing?tab=trade-spend | `/dashboard/marketing/trade-spend/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0247 | marketing/ads/page.tsx | /dashboard/marketing?tab=ads | `/dashboard/marketing/ads/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0248 | marketing/social-media/page.tsx | /dashboard/marketing?tab=social-media | `/dashboard/marketing/social-media/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0249 | marketing/segments/page.tsx | /dashboard/marketing?tab=segments | `/dashboard/marketing/segments/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0250 | marketing/influencers/page.tsx | /dashboard/marketing?tab=influencers | `/dashboard/marketing/influencers/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0251 | marketing/visits/page.tsx | /dashboard/marketing?tab=visits | `/dashboard/marketing/visits/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0252 | marketing/brand-spend/page.tsx | /dashboard/marketing?tab=brand-spend | `/dashboard/marketing/brand-spend/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0253 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/ai` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0254 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/budget` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0255 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/calendar` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0256 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/claims` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0257 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/plans/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0258 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/plans` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0259 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/promotions/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0260 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/promotions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0261 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/roi` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0262 | tpm/page.tsx | /dashboard/marketing?tab=tpm | `/dashboard/tpm/settlement` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Commercial / CRM

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0263 | surveys/page.tsx | /dashboard/crm?tab=surveys | `/dashboard/surveys/new` | critical | CONVERT_TO_WORKSPACE_SUBVIEW |

## Administration / Integrations

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0267 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/dead-letter` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0268 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/definitions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0269 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/deliveries` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0270 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/inbound` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0271 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0272 | webhooks/page.tsx | /dashboard/integrations?tab=webhooks | `/dashboard/webhooks/subscriptions` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0273 | developer/page.tsx | /dashboard/integrations?tab=developer | `/dashboard/developer/graphql` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0274 | developer/page.tsx | /dashboard/integrations?tab=developer | `/dashboard/developer/keys` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

## Factory Operations / Utilities

| ID | Source File | Visible Via | Target | Severity | Recommendation |
|----|------------|-------------|--------|----------|----------------|
| BVT-0275 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/boiler` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0276 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/chemicals` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0277 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/compressor` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0278 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/electricity` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0279 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/machine-utility` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0280 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/soft-water` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0281 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/solar` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0282 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/utility-cost` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0283 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/wastewater` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0284 | utility-management/kpi-center/page.tsx | /dashboard/utility-management?tab=kpi-center | `/dashboard/utility-management/kpi-center/water` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0285 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/anomalies` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0286 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/cost-allocation` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0287 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/daily-consumption` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0288 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/equipment-efficiency` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0289 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/load-analysis` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0290 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/sustainability` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0291 | utility-management/reports/page.tsx | /dashboard/utility-management?tab=reports | `/dashboard/utility-management/reports/treatment` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0292 | esg/page.tsx | /dashboard/utility-management?tab=esg | `/dashboard/esg/activities` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0293 | esg/page.tsx | /dashboard/utility-management?tab=esg | `/dashboard/esg/factors` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0294 | esg/page.tsx | /dashboard/utility-management?tab=esg | `/dashboard/esg/intelligence` | high | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0295 | esg/page.tsx | /dashboard/utility-management?tab=esg | `/dashboard/esg/reports` | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0296 | esg/page.tsx | /dashboard/utility-management?tab=esg | `/dashboard/esg/targets` | high | CONVERT_TO_WORKSPACE_SUBVIEW |

