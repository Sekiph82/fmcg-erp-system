# Pricing, Price Lists & Dynamic Pricing

---

## Pricing & Promotions

**Route:** `/dashboard/sales?tab=pricing`  
**Permission required:** `sales.view`

### What It Does

Pricing manages tiered price rules and promotional discounts. Pricing rules define the unit price for a product at a given customer tier, region, or individual level. Promotions add time-limited percentage or fixed-amount discounts.

![Pricing tab](../../../screenshots/captured/module-ui/sales/sales/pricing-tab.png)
*Pricing tab showing pricing rules and promotions with tiered level badges and KPI counts.*

### Pricing Dashboard KPIs

| KPI | Description |
|---|---|
| Standard Rules | Count of STANDARD-level pricing rules |
| Region Rules | Count of REGION-level rules |
| Distributor Rules | Count of DISTRIBUTOR-level rules |
| Active Promos | Promotions currently within active date range |

### Pricing Levels

| Level | Badge | Description |
|---|---|---|
| `STANDARD` | Gray | Default price for all customers |
| `REGION` | Blue | Region-specific price override |
| `DISTRIBUTOR` | Yellow | Distributor channel price |
| `CUSTOMER` | Green | Customer-specific negotiated price |

### New Pricing Rule Modal

Button: **+ Pricing Rule** (visible when on Rules tab)

![New Pricing Rule modal](../../../screenshots/captured/module-ui/sales/pricing/new-pricing-rule-modal.png)
*New Pricing Rule modal showing product, pricing level, region, unit price, currency, quantity threshold, and effective dates.*

| Field | Label | Required | Notes |
|---|---|---|---|
| `product_id` | Product | Yes | Product to price |
| `pricing_level` | Pricing Level | Yes | STANDARD / REGION / DISTRIBUTOR / CUSTOMER |
| `region` | Region | No | Required if REGION level |
| `unit_price` | Unit Price | Yes | Price per unit |
| `currency` | Currency | No | Default: KES |
| `min_quantity` | Min Quantity | No | Volume pricing threshold |
| `effective_from` | Effective From | No | Start date |
| `effective_to` | Effective To | No | End date |
| `notes` | Notes | No | — |

### Promotions Tab

Internal tab within Pricing. Switch via "Promotions" tab label. Button: **+ Promotion**

### Promotion Types

| Type | Description |
|---|---|
| `DISCOUNT` | Percentage or fixed-amount discount |
| `BUNDLE` | Buy X products, get bundle price |
| `VOLUME` | Price reduction at volume thresholds |

### Promotion Fields

| Field | Description |
|---|---|
| `code` | Promo code customers or reps apply |
| `name` | Display name |
| `promo_type` | DISCOUNT / BUNDLE / VOLUME |
| `discount_type` | PERCENTAGE / FIXED_AMOUNT |
| `discount_value` | Discount percentage or fixed amount |
| `min_order_value` | Minimum order value to qualify |
| `start_date` / `end_date` | Active period |
| `region` | Optional regional restriction |

---

## Price Lists

**Route:** `/dashboard/sales?tab=price-lists`  
**Permission required:** `sales.view`

### What It Does

Price Lists define named groups of product prices. A price list is assigned to a customer or customer segment and used to look up prices when creating sales orders, overriding the standard pricing rule hierarchy.

![Price Lists tab](../../../screenshots/captured/module-ui/sales/sales/price-lists-tab.png)
*Price Lists tab showing named price lists with assigned customer groups.*

---

## Dynamic Pricing

**Route:** `/dashboard/sales?tab=dynamic-pricing`  
**Permission required:** `sales.view`

### What It Does

Dynamic Pricing applies automatic price adjustments based on configurable rules (demand signals, competitor data, margin floors). Rules are evaluated at order creation time.

![Dynamic Pricing tab](../../../screenshots/captured/module-ui/sales/sales/dynamic-pricing-tab.png)
*Dynamic Pricing tab showing dynamic pricing rules with triggers and adjustment parameters.*
