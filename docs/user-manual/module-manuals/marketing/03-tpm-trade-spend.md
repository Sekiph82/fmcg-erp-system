# Trade Promotion Management & Trade Spend

---

## Trade Promotion Management (TPM)

**Route:** `/dashboard/marketing?tab=tpm`  
**Permission required:** `marketing.view`

### What It Does

The TPM tab manages structured trade promotion agreements with distributors, wholesalers, and retailers. It tracks promotional investment, expected off-take, and actual sales uplift per trade deal.

![TPM tab](../../../screenshots/captured/module-ui/marketing/marketing/tpm-tab.png)
*TPM tab showing trade promotion deal list and summary metrics.*

### TPM Deal Lifecycle

Trade promotion deals follow a structured approval and settlement process:

1. Deal created in DRAFT
2. Submitted for approval
3. APPROVED — deal activates and off-take tracking begins
4. SETTLED — investment reconciled against actual uplift
5. CLOSED — deal archived

---

## Trade Spend

**Route:** `/dashboard/marketing?tab=trade-spend`  
**Permission required:** `marketing.view`

### What It Does

The Trade Spend tab records and tracks all trade-channel investment — shelf placement fees, display rentals, distributor support, and activation costs. It provides a spend-by-type and spend-by-region breakdown to support budget management.

![Trade Spend tab](../../../screenshots/captured/module-ui/marketing/marketing/trade-spend-tab.png)
*Trade Spend tab showing spend records categorized by type.*

### Trade Spend Types

| Value | Label |
|---|---|
| `DISCOUNT_SUPPORT` | Discount Support |
| `DISPLAY_FEE` | Display / Gondola Fee |
| `SHELF_PLACEMENT` | Shelf Placement |
| `ACTIVATION_SUPPORT` | Activation Support |
| `REBATE` | Rebate |
| `DISTRIBUTOR_SUPPORT` | Distributor Support |
| `MERCHANDISING` | Merchandising |

### Trade Spend Fields

| Field | Description |
|---|---|
| `spend_type` | Category (see above) |
| `amount` | Spend amount (KES) |
| `region` | Target region |
| `outlet_name` | Specific outlet or distributor |
| `campaign_id` | Linked campaign (optional) |
| `spend_date` | Date of spend |
| `notes` | Free text notes |
