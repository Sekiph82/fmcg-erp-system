# Sales and Distribution

**URLs:** `/dashboard/sales`, `/dashboard/logistics`, `/dashboard/crm`  
**Module:** Sales  
**Permission:** `sales.view`

---

## Screenshot

![Sales Workspace](../screenshots/captured/072_sales.png)

---

## Sales Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | ?tab=overview | Sales KPI summary |
| Orders | ?tab=orders | Sales order management |
| Invoices | ?tab=invoices | Customer invoices, eTIMS |
| Customers | ?tab=customers | Customer master |
| Quotes | ?tab=quotes | Quotations |
| Shipments | ?tab=shipments | Delivery notes |
| Delivery | ?tab=delivery | Delivery scheduling |
| Collections | ?tab=collections | Payment collection |
| Returns | ?tab=returns | Return merchandise authorisation |
| Pricing | ?tab=pricing | Base pricing rules |
| Price Lists | ?tab=price-lists | Customer/channel price lists |
| Dynamic Pricing | ?tab=dynamic-pricing | AI-driven pricing |
| Contracts | ?tab=contracts | Customer contracts |
| Recurring | ?tab=recurring | Recurring orders |
| Commissions | ?tab=commissions | Sales rep commissions |
| Secondary | ?tab=secondary | Secondary distribution |
| Van Sales | ?tab=van-sales | Van sales pre-sell / settlement |
| Distributors | ?tab=distributors | Distributor management |
| Field Sales | ?tab=field-sales | Route-to-market tracking |
| Margin | ?tab=margin | Gross margin by order/customer |
| Portal | ?tab=portal | Customer self-service portal |
| Reports | ?tab=reports | Sales reports |

---

## Logistics Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | ?tab=overview | Logistics KPI |
| Shipments | ?tab=shipments | Outbound shipments |
| Containers | ?tab=containers | Import container tracking |
| Arrivals | ?tab=arrivals | Expected arrivals |
| Documents | ?tab=documents | Shipping documents |
| Fleet | ?tab=fleet | Vehicle management |

---

## CRM Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | — | CRM KPIs |
| Pipeline | ?tab=pipeline | Sales pipeline board |
| Leads | ?tab=leads | Lead management |
| Opportunities | ?tab=opportunities | Opportunity management |
| Activities | ?tab=activities | Calls, meetings, follow-ups |
| Forecast | ?tab=forecast | Sales forecast |
| Territory | ?tab=territory | Sales territory management |
| Stages | ?tab=stages | Pipeline stage config |
| Win/Loss | ?tab=win-loss | Deal analysis |
| Loyalty | ?tab=loyalty | Loyalty program |
| NPS | ?tab=nps | Net Promoter Score |
| Surveys | ?tab=surveys | Customer surveys |

---

## eTIMS (KRA e-Invoicing)

Kenya Revenue Authority requires electronic invoicing for VAT-registered businesses. The system posts each invoice to eTIMS automatically after posting. Requirements:
- Customer must have a KRA PIN on file
- Product must have a correct VAT code
- ETIMS credentials configured in Admin → Integrations

---

## Van Sales Model

Kenya FMCG distribution uses a van sales model:
1. Pre-selling: sales rep takes orders before loading
2. Loading: warehouse loads van per approved plan
3. Selling: driver delivers and collects
4. Settlement: returns and cash settled at end of route

---

## M-Pesa Collections

Collections tab supports M-Pesa as a payment method. M-Pesa transactions are imported via the integration and matched to open invoices.
