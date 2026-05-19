# Leads Management

**Route:** `/dashboard/crm?tab=leads`  
**Permission required:** `crm.view`

## What It Does

The Leads tab lists all lead records with status and temperature filters. Leads represent the earliest stage of the sales pipeline — an identified prospect that has not yet been qualified as an opportunity.

![Leads tab](../../../screenshots/captured/module-ui/crm/crm/leads-tab.png)
*Leads tab showing table of lead records with code, company, contact, source, stage, temperature, score, expected revenue, and status.*

## Leads Table Columns

| Column | Description |
|---|---|
| Code | `lead_code` — auto-generated lead reference |
| Company | `company_name` |
| Contact | `contact_person_name` and `contact_phone` |
| Source | `source_type` — how the lead was generated |
| Stage | Current pipeline stage name |
| Temp | Temperature indicator (Cold / Warm / Hot) |
| Score | `lead_score` (0–100) shown as a bar and number |
| Expected Rev | `expected_revenue` in `currency` |
| Status | Lead status badge |
| Actions | `View` link to record detail |

## Filters

| Filter | Values |
|---|---|
| Status | OPEN · WON · LOST · ON_HOLD · ARCHIVED |
| Temperature | COLD · WARM · HOT |

![Leads filter dropdowns expanded](../../../screenshots/captured/module-ui/crm/leads/leads-dropdowns.png)
*Status and temperature filter dropdowns expanded.*

## Creating a New Lead

Click `+ New Lead` to open the create modal.

![New Lead form](../../../screenshots/captured/module-ui/crm/leads/new-lead-form.png)
*New Lead modal with required and optional fields.*

### New Lead Form Fields

| Field | Type | Required |
|---|---|---|
| Company Name | Text | Yes |
| Contact Person | Text | No |
| Email | Email input | No |
| Phone | Text | No |
| Source Type | Select | No (defaults to MANUAL) |
| Notes | Textarea | No |

### Source Types

| Value | Label |
|---|---|
| `WEBSITE` | Website |
| `REFERRAL` | Referral |
| `FIELD_SALES` | Field Sales |
| `EVENT` | Event / Trade Show |
| `OUTBOUND` | Outbound Call |
| `INBOUND` | Inbound Inquiry |
| `CAMPAIGN` | Campaign |
| `MANUAL` | Manual Entry |
| `IMPORT` | Import |

![New Lead source type dropdown expanded](../../../screenshots/captured/module-ui/crm/leads/new-lead-source-dropdown.png)
*Source type dropdown expanded in the New Lead form.*

## Record Statuses

| Status | Meaning |
|---|---|
| `OPEN` | Active, in pipeline |
| `WON` | Closed as a win |
| `LOST` | Closed as a loss |
| `ON_HOLD` | Paused |
| `ARCHIVED` | Hidden from active views |

## Temperature

| Value | Color | Meaning |
|---|---|---|
| `COLD` | Grey | Low engagement |
| `WARM` | Amber | Moderate interest |
| `HOT` | Red | High urgency / ready to close |

## Account Types

CRM records carry an `account_type` field:

| Value | Description |
|---|---|
| `PROSPECT` | New, unqualified contact |
| `CUSTOMER` | Existing customer |
| `DISTRIBUTOR` | Distribution partner |
| `RETAILER` | Retail outlet |
| `MODERN_TRADE` | Supermarket / chain |
| `INSTITUTIONAL` | Institutional buyer |
| `SUPPLIER_XSELL` | Cross-sell from supplier network |
| `OTHER` | Other |

## Record Detail

Click `View` on any row to open `/dashboard/crm/records/{id}` — the 360° record detail page showing interest lines, activities, competitors, and win/loss data.
