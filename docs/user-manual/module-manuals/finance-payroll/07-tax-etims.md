# Tax, eTIMS & VAT Returns

---

## Tax & Regulatory

**Route:** `/dashboard/finance?tab=tax`
**Permission required:** `finance.view`

### What It Does

Tax manages tax rules, regulatory compliance flags, and transaction-level tax application across Kenya and Turkey operations.

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

## eTIMS — Electronic Tax Invoice Management System

**Route:** `/dashboard/finance?tab=etims` (global monitoring page)
**Invoice card:** `/dashboard/sales/invoices/[id]` (per-invoice fiscalization)
**Permission required:** `finance.view`

![Finance tax / eTIMS page](../../../screenshots/captured/095_finance-tax.png)
*Finance module with eTIMS tab — global submission queue, provider health panel, and per-row action buttons.*

### Overview

eTIMS is the Kenya Revenue Authority's mandatory electronic invoicing platform. Kenya VAT-registered businesses are required by law to submit invoices to KRA via an approved eTIMS provider before final GL posting.

**Current implementation status:**

- Connector-ready architecture implemented — provider-neutral adapter interface, payload builder, and all backend endpoints are live.
- SimulationETIMSConnector active by default — all submissions are simulated locally. No live KRA API calls are made.
- `production_execution_allowed = false` — the system will not send data to any real provider until credentials are configured and this flag is explicitly enabled.
- **Live provider blocked** — live eTIMS submissions require: (a) KRA eTIMS provider selection, (b) sandbox credentials registered at the KRA developer portal, (c) accountant approval of the GL posting gate rules.

> **Do not describe the eTIMS connector as "live" or "KRA-connected." The connector architecture is complete; live provider validation is pending.**

---

### eTIMS Workflow

```
Invoice created (status: ISSUED)
    ↓
Prepare fiscal payload     [POST /etims/prepare/{invoice_id}]
    ↓
ETimsSubmission created (status: READY)
    ↓
Submit to provider adapter [POST /etims/submit/{invoice_id}]
    ↓
SimulationETIMSConnector → fake ACCEPTED response (no network call)
    ↓
ETimsSubmission updated (status: ACCEPTED / REJECTED)
    ↓
[GL posting gate: NOT YET ENFORCED — blocked pending accountant decision]
    ↓
Finance JournalEntry (POSTED) — currently posts regardless of eTIMS status
```

> **GL posting gate:** The finance service does not currently check eTIMS submission status before allowing GL journal posting. This gate (TASK-005.1D) is blocked pending accountant confirmation of which invoice types require fiscal acceptance before GL posting.

---

### eTIMS Status Values (10 statuses)

| Status | Badge | Meaning |
|---|---|---|
| `DRAFT` | Gray | Fiscal payload not yet prepared |
| `READY` | Blue | Payload built; not yet submitted to provider |
| `PENDING` | Yellow | Queued at provider; response awaited |
| `SUBMITTED` | Blue | Transmitted to provider adapter |
| `RETRY_PENDING` | Orange | Scheduled for automatic retry |
| `ACCEPTED` | Green | KRA/provider confirmed acceptance |
| `REJECTED` | Red | KRA/provider rejected — error code shown |
| `FAILED` | Red | Transmission error; network or adapter failure |
| `ERROR` | Red | Internal error during payload build or adapter call |
| `CANCELLED` | Gray | Submission manually cancelled |

---

### Global eTIMS Monitoring Page

**Route:** `/dashboard/finance/etims` (also accessible via Finance → eTIMS tab)

> Hover over the ? icon in the page header for quick field, status, and workflow guidance.

#### Provider Health Panel

Shows the current adapter configuration. Click **Check Health** to query the provider adapter:

| Field | Description |
|---|---|
| Provider | Adapter name (e.g. `SimulationETIMSConnector`) |
| Environment | `sandbox` or `production` |
| Live | Whether real external calls are enabled |
| `production_execution_allowed` | `false` in simulation; `true` only when credentials configured |
| Note / Detail | Adapter-specific status message |

In simulation mode, the banner reads: **"Simulation mode — production_execution_allowed = false"**

#### KPI Counters

| Counter | Statuses included |
|---|---|
| Pending / Submitted | PENDING + SUBMITTED |
| Accepted | ACCEPTED |
| Rejected / Failed / Error | REJECTED + FAILED + ERROR |
| Cancelled | CANCELLED |

#### Submission Table Columns

| Column | Description |
|---|---|
| Invoice | Invoice reference; links to invoice detail page |
| Status | Status badge (10 values) |
| Provider | Provider name + environment badge |
| TIMS No | `control_unit_invoice_no` — KRA control number (set on ACCEPTED) |
| KRA Response | `kra_response_code` + `kra_response_message` |
| Attempts | `attempt_count` / `retry_count` |
| Last Attempt | `last_attempt_at` timestamp |
| Actions | Retry / Cancel / Poll (per-row; state-gated) |

#### Action Buttons (per row)

| Button | Enabled when | API endpoint |
|---|---|---|
| **Retry** | Status is REJECTED, FAILED, ERROR, or RETRY_PENDING | `POST /etims/retry/{submission_id}` |
| **Cancel** | Status is not already CANCELLED | `POST /etims/cancel/{invoice_id}` |
| **Poll** | `provider_reference` is not null | `GET /etims/status/{submission_id}` |

Clicking **Cancel** opens a modal requiring a cancellation reason. If the submission is ACCEPTED, a red warning is shown. The flag `allow_cancel_accepted=true` is sent automatically when cancelling an accepted submission.

Row-level loading isolation: retrying or polling one row does not show a spinner on other rows.

#### Debug Details (per row)

Each row has a collapsible `<details>` panel containing:
- `error_code` / `error_message`
- `provider_reference` (provider's own submission ID before KRA control number)
- `signed_invoice_hash` (if accepted)
- `request_payload` (snapshot of the payload sent to the adapter)
- `response_payload` (full provider response body)

---

### Invoice Detail eTIMS Card

**Route:** `/dashboard/sales/invoices/[id]`

The eTIMS Fiscalization card appears on the invoice detail page, below the Payment History section.

#### Not Submitted State

When no ETimsSubmission exists for the invoice:
- **Submit** button is available (calls `POST /etims/submit/{invoice_id}`)
- No metadata shown

#### Submitted State

When a submission exists, the card shows:

| Field | Description |
|---|---|
| Provider | Adapter name + environment |
| TIMS No | KRA control number (`control_unit_invoice_no`) |
| KRA Response | Response code + message |
| Accepted At | `accepted_at` timestamp |
| Last Attempt | `last_attempt_at` |
| Attempts | `attempt_count` / `retry_count` |

Action buttons follow the same state rules as the global page. An error panel appears when `error_code` or `error_message` is present. The debug collapsible is also available.

**Button disable rules on invoice detail:**
- Submit disabled for ACCEPTED, SUBMITTED, PENDING (already in-flight)
- Retry enabled only for REJECTED, FAILED, ERROR, RETRY_PENDING
- Cancel disabled when already CANCELLED
- Poll disabled when `provider_reference` is null

---

### Provider Configuration (Environment Variables)

| Variable | Description | Default |
|---|---|---|
| `ETIMS_PROVIDER` | `simulation` or `http` | `simulation` |
| `ETIMS_API_URL` | Live provider base URL | — |
| `ETIMS_API_KEY` | Provider authentication key | — |
| `ETIMS_PIN` | Taxpayer KRA PIN | — |
| `ETIMS_BRANCH_CODE` | Branch/device code | — |
| `ETIMS_ENVIRONMENT` | `sandbox` or `production` | `sandbox` |

> **Do not set `ETIMS_PROVIDER=http`** until a KRA-approved provider is selected, sandbox credentials are registered, and the accountant has confirmed the GL posting gate requirements. Do not commit any eTIMS credentials to git.

---

### Blocked and Not Yet Implemented

| Feature | Status | Blocker |
|---|---|---|
| Live provider calls | Blocked | Provider selection + KRA sandbox credentials |
| GL posting gate (require ACCEPTED before posting) | Blocked | Accountant must confirm which invoice types require fiscal acceptance before GL posting |
| Product KRA item codes (`etims_item_code`, `tax_type_code`) | Not in product model | Tax advisor confirmation of HS codes required before migration |
| Multi-provider DB config table | Architecture gap | Deferred — env-var config only for now |
| Credit note / cancellation submission to KRA | Architecture gap | Provider-specific cancel path not yet implemented |

---

## VAT Returns

**Route:** `/dashboard/finance?tab=vat-returns`
**Permission required:** `finance.view`

### What It Does

VAT Returns generates Kenya VAT3 return data for monthly KRA filing. It aggregates standard-rated, zero-rated, and exempt supplies and their corresponding input tax.

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
