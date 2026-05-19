# Promotions & Schemes

---

## Promotions

**Route:** `/dashboard/marketing?tab=promotions`  
**Permission required:** `marketing.view`

### What It Does

The Promotions tab manages trade and consumer promotions — discount offers, bundle deals, free item giveaways, and retailer/distributor support programs. Each promotion is linked to a campaign and can target specific customers or segments.

![Promotions tab](../../../screenshots/captured/module-ui/marketing/marketing/promotions-tab.png)
*Promotions list showing promotion code, name, type, linked campaign, start/end dates, discount, and status.*

### Promotion Types

| Value | Label |
|---|---|
| `DISCOUNT` | Price Discount |
| `BUNDLE` | Bundle Deal |
| `FREE_ITEM` | Free Item / BOGOF |
| `REBATE` | Rebate |
| `BUY_X_GET_Y` | Buy X Get Y |
| `RETAILER_SUPPORT` | Retailer Support |
| `DISTRIBUTOR_SUPPORT` | Distributor Support |
| `CASHBACK` | Cashback |

### Discount Types

| Value | Description |
|---|---|
| `PERCENTAGE` | Percentage off (e.g. 10%) |
| `FIXED` | Fixed amount off (e.g. KES 50) |

### Creating a New Promotion

Click `+ New Promotion` or navigate to `/dashboard/marketing/promotions/new`.

![New Promotion form](../../../screenshots/captured/module-ui/marketing/promotions/new-promotion-form.png)
*New Promotion form.*

### New Promotion Form Fields

| Field | Type | Required |
|---|---|---|
| Promotion Name | Text | Yes |
| Promotion Type | Select | Yes |
| Linked Campaign | Select | No |
| Discount Type | Select | No |
| Discount Value | Number | No |
| Start Date | Date | No |
| End Date | Date | No |
| Region | Text | No |
| Notes | Textarea | No |

API: `POST /api/v1/marketing/promotions`

---

## Promotion Schemes

**Route:** `/dashboard/marketing?tab=promotions-schemes`  
**Permission required:** `marketing.view`

### What It Does

The Schemes tab shows promotion scheme configurations — predefined discount structures and eligibility rules that can be applied across promotions. Schemes define eligibility conditions (customer segment, channel, minimum order quantity) and the associated discount or incentive.

![Promotion Schemes tab](../../../screenshots/captured/module-ui/marketing/marketing/schemes-tab.png)
*Promotion Schemes tab showing scheme configurations.*
