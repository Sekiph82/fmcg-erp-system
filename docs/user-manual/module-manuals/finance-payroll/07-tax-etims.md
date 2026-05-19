# Tax, eTIMS & VAT Returns

---

## Tax & Regulatory

**Route:** `/dashboard/finance?tab=tax`  
**Permission required:** `finance.view`

### What It Does

Tax manages tax rules, regulatory compliance flags, and transaction-level tax application across Kenya and Turkey operations.

![Tax tab](../../../screenshots/captured/module-ui/finance-payroll/finance/tax-tab.png)
*Tax tab showing the regulatory compliance dashboard with KPI tiles and quick links.*

![Tax dashboard](../../../screenshots/captured/module-ui/finance-payroll/tax/tax-dashboard.png)
*Tax standalone dashboard with detailed compliance status, expiring flags, and regulatory summary table.*

### Tax Dashboard KPIs

| Tile | Description |
|---|---|
| Total Tax Posted (KES) | Sum of all applied tax amounts |
| Non-Compliant Flags | Count of `NON_COMPLIANT` + `EXPIRED` regulatory records; red if > 0 |
| Pending Flags | Count of `PENDING` regulatory items; yellow |
| Expiring (30 days) | Regulatory items expiring within 30 days; orange if > 0 |

### Regulatory Status Values

| Status | Badge | Meaning |
|---|---|---|
| `COMPLIANT` | Green | Requirement met |
| `NON_COMPLIANT` | Red | Requirement not met |
| `EXPIRED` | Red | Previously compliant, now lapsed |
| `PENDING` | Yellow | Under review |
| `NOT_APPLICABLE` | Gray | Does not apply to this entity |

### Tax Sub-pages

| Page | Route | Purpose |
|---|---|---|
| Tax Rules & Categories | `/dashboard/tax/rules` | Country VAT, excise, withholding tax rules |
| Regulatory Flags | `/dashboard/tax/regulatory` | Compliance, licenses, certifications |
| Transaction Taxes | `/dashboard/tax/transactions` | Applied taxes on POs, SOs, invoices |
| Tax Reports | `/dashboard/tax/reports` | Tax summary by country and type |

---

## eTIMS

**Route:** `/dashboard/finance?tab=etims`  
**Permission required:** `finance.view`

### What It Does

eTIMS (Electronic Tax Invoice Management System) is the KRA's mandatory electronic invoicing platform. This tab manages eTIMS invoice submissions and tracks submission status.

![eTIMS tab](../../../screenshots/captured/module-ui/finance-payroll/finance/etims-tab.png)
*eTIMS tab showing invoice submission queue with KRA status codes and submission timestamps.*

### eTIMS Submission Workflow

```
Sales Invoice created in ERP
    → Invoice queued for eTIMS submission
    → Submitted to KRA eTIMS API
    → KRA assigns eTIMS invoice number (CIS number)
    → Status updated: SUBMITTED / ACCEPTED / REJECTED
```

### eTIMS Status Values

| Status | Meaning |
|---|---|
| `PENDING` | Queued, not yet submitted |
| `SUBMITTED` | Sent to KRA API |
| `ACCEPTED` | KRA confirmed acceptance |
| `REJECTED` | KRA rejected — error code shown |

---

## VAT Returns

**Route:** `/dashboard/finance?tab=vat-returns`  
**Permission required:** `finance.view`

### What It Does

VAT Returns generates Kenya VAT3 return data for monthly KRA filing. It aggregates standard-rated, zero-rated, and exempt supplies and their corresponding input tax.

![VAT Returns tab](../../../screenshots/captured/module-ui/finance-payroll/finance/vat-returns-tab.png)
*VAT Returns tab showing VAT3 period summary with output tax, input tax, and net VAT payable.*

### VAT3 Return Summary

| Field | Description |
|---|---|
| Period | VAT return month/year |
| Standard Rated Sales | Sales subject to 16% VAT |
| Output VAT | 16% × standard rated sales |
| Zero-Rated Sales | Exports and zero-rated supplies |
| Exempt Sales | VAT-exempt supplies |
| Input Tax | VAT paid on purchases, claimable as credit |
| Net VAT Payable | Output VAT minus input tax; positive = amount owed to KRA |
