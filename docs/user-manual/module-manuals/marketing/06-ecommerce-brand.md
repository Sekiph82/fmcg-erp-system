# E-Commerce & Brand Spend

---

## E-Commerce

**Route:** `/dashboard/marketing?tab=ecommerce`  
**Permission required:** `marketing.view`

### What It Does

The E-Commerce tab integrates with online store platforms to track storefront performance — sales, orders, GMV, and product-level performance across marketplaces and owned stores.

![E-Commerce tab](../../../screenshots/captured/module-ui/marketing/marketing/ecommerce-tab.png)
*E-Commerce tab showing connected stores, platform badges, GMV, and order counts.*

### Online Store Platforms

| Value | Label |
|---|---|
| `JUMIA` | Jumia |
| `KILIMALL` | Kilimall |
| `SHOPIFY` | Shopify |
| `WOOCOMMERCE` | WooCommerce |
| `AMAZON` | Amazon |
| `TIKTOK_SHOP` | TikTok Shop |
| `INSTAGRAM_SHOP` | Instagram Shop |
| `OTHER` | Other |

### Store Status

| Value | Meaning |
|---|---|
| `ACTIVE` | Live and selling |
| `INACTIVE` | Paused |
| `PENDING` | Setup in progress |

---

## Brand Spend

**Route:** `/dashboard/marketing?tab=brand-spend`  
**Permission required:** `marketing.view`

### What It Does

The Brand Spend tab tracks above-the-line (ATL) and below-the-line (BTL) marketing expenditure. It records spend by category, vendor, and campaign for brand investment accountability.

![Brand Spend tab](../../../screenshots/captured/module-ui/marketing/marketing/brand-spend-tab.png)
*Brand Spend tab showing spend records by category and campaign.*

### Brand Spend Categories

| Value | Label |
|---|---|
| `TV` | Television |
| `RADIO` | Radio |
| `DIGITAL_ADS` | Digital Advertising |
| `INFLUENCER` | Influencer Fees |
| `EVENT` | Events & Activations |
| `SAMPLING` | Product Sampling |
| `BRANDING_MATERIAL` | Branding & POS Material |
| `AGENCY_COST` | Agency Fees |
| `CREATIVE_PRODUCTION` | Creative Production |
| `MEDIA_BUYING` | Media Buying |

### Brand Spend Fields

| Field | Description |
|---|---|
| `category` | Spend category (see above) |
| `amount` | Amount (KES) |
| `vendor_name` | Vendor or agency name |
| `campaign_id` | Linked campaign (optional) |
| `spend_date` | Date of spend |
| `invoice_ref` | Invoice reference |
| `notes` | Free text notes |
