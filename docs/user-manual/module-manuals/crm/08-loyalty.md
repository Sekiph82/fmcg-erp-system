# Customer Loyalty Program

**Route:** `/dashboard/crm?tab=loyalty`  
**Permission required:** `crm.view`

## What It Does

The Loyalty tab manages a points-based rewards program for customers and distributors. Customers are enrolled, assigned to tiers based on lifetime points, and can earn or redeem points against purchases.

![Loyalty tab](../../../screenshots/captured/module-ui/crm/crm/loyalty-tab.png)
*Loyalty tab showing KPI cards, tier cards, members list, and account detail panel.*

## KPI Cards

| KPI | Description |
|---|---|
| Active Members | Total enrolled loyalty accounts |
| Points Outstanding | Sum of all member point balances |
| Total Transactions | Total earn + redeem transactions across all accounts |

## Tier Cards

Each tier card displays:
- Tier name and color
- Member count
- Minimum lifetime points threshold
- Points earned per 100 spend
- Discount percentage (if any)
- List of perks

## Members Table

| Column | Description |
|---|---|
| Customer | Customer name and code |
| Tier | Tier badge (color-coded) |
| Points | Current point balance |
| Lifetime | Total points ever earned |
| Last Active | Date of most recent transaction |

Click any row to load the account detail panel on the right.

## Account Detail Panel

Shows for the selected member:
- Current point balance and lifetime points
- Tier discount percentage
- Recent transaction history (type, description, delta)

### Transaction Types

Transactions are shown with color coding. Types include:

- **EARN** — points added from purchase
- **REDEEM** — points deducted for reward
- **ADJUST** — manual adjustment
- **EXPIRE** — expired points deducted
- **ENROLL** — welcome bonus on enrollment

## Enrolling a Customer

Click `+ Enroll Customer` to open the enrollment modal.

![Enroll Customer form](../../../screenshots/captured/module-ui/crm/loyalty/enroll-form.png)
*Enroll Customer modal.*

### Enroll Form Fields

| Field | Type | Required |
|---|---|---|
| Customer ID (UUID) | Text | Yes |
| Welcome Bonus Points | Number | No (defaults to 0) |

API: `POST /api/v1/loyalty/accounts/enroll`

## Adding Points (Earn)

With an account selected, click `+ Earn`:

| Field | Description |
|---|---|
| Points (direct) | Enter exact points to add |
| Or: Spend Amount | Enter purchase amount — system auto-calculates points based on tier rate |
| Description | Reference (e.g. Order #SO-001) |

API: `POST /api/v1/loyalty/accounts/{customer_id}/earn`

## Redeeming Points

With an account selected, click `- Redeem`:

| Field | Description |
|---|---|
| Points to Redeem | Number of points to deduct |
| Reward Description | What the points were redeemed for |

API: `POST /api/v1/loyalty/accounts/{customer_id}/redeem`

## Tier Filter

The members list can be filtered by tier using the dropdown above the table.
