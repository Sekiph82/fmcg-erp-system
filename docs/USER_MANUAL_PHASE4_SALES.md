# PHASE 4 — SALES & COMMERCIAL
## FMCG ERP User Manual

---

<a name="sales-orders"></a>
# MODULE 21: SALES ORDERS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Sales Order Management covers the complete order-to-cash cycle: customer orders, pricing, delivery, invoicing, and payment collection. Every customer transaction flows through this module.

**Why it exists in FMCG context:**  
A single FMCG company may process 200–500 customer orders per day across distributors, retailers, and van sales. Without a systematic order management system, orders are lost, delivered quantities are wrong, invoices don't match deliveries, and collections become impossible to track.

**Business impact:**  
- Complete order visibility from creation to collection
- Accurate invoicing (reduces disputes)
- Customer credit control (prevents bad debt)
- Delivery planning (routes, truck loads)
- Cash flow visibility (when will customers pay?)

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Sales Representative** | Creates orders, manages customer relationships |
| **Order Processing Clerk** | Confirms and processes orders |
| **Warehouse/Dispatch** | Picks, packs, and dispatches orders |
| **Finance / Credit Controller** | Approves credit-hold customers, manages collections |
| **Sales Manager** | Reviews order pipeline, approves discounts |

---

## 3. KEY CONCEPTS

**Sales Order Status Flow:**
```
DRAFT → CONFIRMED → PICKING → DISPATCHED → DELIVERED → INVOICED → PAID
```

**Credit Limit:** Maximum amount a customer can owe you at any time. System checks credit on every new order.

**Credit Hold:** If a customer exceeds their credit limit or has overdue invoices, new orders are placed on hold until Finance releases.

**Price List:** The agreed price for each product for each customer or customer group.

**Minimum Order Quantity (MOQ):** The smallest amount a customer can order for a product.

**Lead Time:** Days between order and delivery.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Sales Orders (`/dashboard/sales/orders`)

**Order list with quick status indicators:**
- Red: CRITICAL — overdue for dispatch or delivery
- Orange: HIGH — dispatch due today
- Green: Normal

**Summary KPIs:**
- Orders to dispatch today
- Orders pending payment (with age)
- Cash collected today

### Screen: New Sales Order

**Header section:**
| Field | Description | Required? |
|---|---|---|
| Customer | Select from customer master | Yes |
| Order Date | Today (system defaults) | Auto |
| Requested Delivery Date | When does customer want delivery? | Yes |
| Delivery Address | Select from customer's addresses | Yes |
| Sales Rep | Who is responsible for this order? | Yes |
| Payment Terms | From customer master (overrideable) | Auto |
| Price List | From customer master | Auto |

**Lines section** (add one row per product):
| Field | Description |
|---|---|
| Product | Select product from catalog |
| Quantity | Units ordered |
| Unit Price | Auto-populated from price list |
| Discount % | Only if user has sales.approve permission |
| Net Price | Calculated: Price × (1 - Discount%) |
| Line Total | Quantity × Net Price |

**Credit check:** When you click **Confirm**, system checks:
1. Customer credit limit
2. Overdue invoices
3. If either is a problem: order goes to credit hold

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Processing a Standard Distributor Order

**Step 1 — Order received from customer (phone/email/portal)**
- Go to `/dashboard/sales/orders`, click **New Order**
- Select customer: "Sunflower Distributors Ltd"
- System auto-loads: price list, payment terms, delivery address

**Step 2 — Add order lines**
- Click **Add Line**
- Product: "Liquid Detergent 1L"
- Quantity: 500 cases
- Price auto-populated: KES 1,840/case
- Repeat for each product

**Step 3 — Review order total and credit**
- Order total: KES 920,000
- Credit limit: KES 2,000,000
- Current outstanding: KES 800,000
- Available credit: KES 1,200,000 — ORDER APPROVED

**Step 4 — Confirm order**
- Click **Confirm**
- Order number generated: SO-2024-1234
- Warehouse team notified: new order ready for picking

**Step 5 — Picking list generated**
- Go to `/dashboard/sales/orders`, find SO-2024-1234
- Click **Generate Picking List**
- FEFO: system selects lots with earliest expiry
- Picking list shows: rack location, lot number, quantity per product

**Step 6 — Dispatch**
- Warehouse confirms pick completed
- Driver assigned to delivery
- Click **Dispatch** — status changes to DISPATCHED
- System: records dispatch date, truck/driver
- Customer receives dispatch notification (if configured)

**Step 7 — Proof of Delivery (POD)**
- Driver delivers and gets customer signature
- Go to `/dashboard/sales/pod`
- Enter: Delivered quantities, customer signature (upload photo if available)
- Any discrepancy: enter reason (customer refused X units, etc.)
- Status changes to DELIVERED

**Step 8 — Invoice generation**
- System auto-generates invoice upon delivery confirmation
- Invoice lines = actual delivered quantities (not ordered quantities)
- Click **Post Invoice** — status INVOICED
- Invoice emailed to customer automatically

**Step 9 — Payment collection**
- Finance tracks outstanding invoice
- On due date: if unpaid, dunning process starts
- When payment received: record in Finance → Receivables
- Status: PAID

---

### Workflow: Handling a Credit-Hold Order

**Situation:** Customer "Fresh Foods Ltd" places an order but has overdue invoices from last month.

**System action:** Order goes to CREDIT_HOLD automatically. Sales Rep and Finance receive notifications.

**Step 1** — Finance Credit Controller opens the credit review  
**Step 2** — Reviews: What invoices are overdue? How long? Total overdue amount?  
**Step 3** — Options:
   - **Release the order:** Customer has promised payment — Finance trusts them
   - **Release with condition:** Customer must pay X% before dispatch
   - **Hold:** Do not release until payment received  
**Step 4** — If releasing: Click **Release Credit Hold** with reason noted  
**Step 5** — Order proceeds to picking and dispatch normally  

**Best practice:** Keep a note in the customer record about the reason for release. Repeated credit holds may indicate the customer's credit limit needs review.

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always confirm credit before picking and dispatching
- ✅ Record Proof of Delivery on the day of delivery
- ✅ Post invoices same day as delivery
- ✅ Review credit limits quarterly — business relationships change

### DON'T:
- ❌ Never dispatch orders without confirming availability in inventory
- ❌ Don't give discounts beyond your authorization level without approval
- ❌ Never create backdated orders — it corrupts sales reports and audit trails

---

## QUICK TRAINING SUMMARY — Sales Orders

> **What:** Full order-to-cash cycle from order creation through delivery to payment.  
> **Status flow:** Draft → Confirmed → Picking → Dispatched → Delivered → Invoiced → Paid.  
> **Credit check:** Runs automatically when order is confirmed.  
> **Key rule:** Record POD same day as delivery. Post invoices same day as delivery.

---

<a name="pricing"></a>
# MODULE 22: PRICING ENGINE & PROMOTIONS

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Pricing Engine manages all aspects of pricing: standard price lists, customer-specific prices, volume discounts, promotional schemes, and promotional simulation. The Trade Promotion Management (TPM) module manages formal trade promotions with budgets, claims, and ROI analysis.

**Why it exists in FMCG context:**  
FMCG pricing is extremely complex. A product might have a standard price list, a distributor price, a key account price, a promotional price during a campaign, and a volume discount for large orders — all simultaneously. Without a systematic pricing engine, sales teams manually calculate prices, make errors, and sometimes unknowingly sell below cost.

---

## 3. KEY CONCEPTS

**Price List:** A set of prices for products, applicable to a specific customer group or date range.

**7-Level Price Resolution:** When a sales order is created, the system checks in this priority order:
1. Customer-specific price (highest priority)
2. Customer group price
3. Promotional price (if active campaign)
4. Volume discount (if quantity threshold reached)
5. Seasonal price
6. Regional price
7. Standard price list (lowest priority, fallback)

**Margin Guardrail:** A minimum margin rule — system blocks pricing that would result in margin below the threshold (e.g., 15% gross margin). Requires Finance approval to override.

**Promotional Scheme:** A planned discount or incentive for customers (e.g., "Buy 10 cases, get 1 free" or "30% off floor cleaner in June").

**ROI Analysis:** Did the promotion generate enough incremental sales to cover its cost?

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Creating a Promotional Scheme

**Situation:** Marketing wants to run "Buy 12 cases of Shampoo 500ml, get 1 free" in June to clear stock.

**Step 1** — Go to `/dashboard/promotions/schemes/new`  
**Step 2** — Fill scheme details:
   - Name: "June Shampoo Promotion"
   - Type: Free Goods (Buy X Get Y)
   - Product: Shampoo 500ml
   - Trigger: Buy 12 cases
   - Reward: 1 free case
   - Valid: 01-Jun-2024 to 30-Jun-2024
   - Eligible customers: All distributors  
**Step 3** — Run simulation: `/dashboard/promotions/simulate`
   - Enter expected order volumes
   - System shows: cost of promotion, expected incremental volume, estimated ROI  
**Step 4** — Submit for approval (Marketing Manager + Finance approval required)  
**Step 5** — Once approved: scheme activates automatically on June 1  
**Step 6** — When a June sales order includes Shampoo 500ml × 24 cases → system automatically adds 2 free cases  
**Step 7** — At month-end: view promotion analytics — actual vs. projected sales, total cost, ROI  

---

### Workflow: Price Override with Margin Check

**Situation:** Sales Rep wants to give a special price to a new customer — 18% discount.

**Step 1** — In sales order, Sales Rep enters 18% discount on Detergent 1L  
**Step 2** — System calculates resulting margin: 11% (below 15% minimum)  
**Step 3** — System shows: "⚠️ Price below margin guardrail. Sales Manager approval required."  
**Step 4** — Order goes to **Override Queue** automatically  
**Step 5** — Sales Manager reviews: Is this a strategic customer worth the low margin?  
**Step 6** — If approved: enters approval reason and override code, order proceeds  
**Step 7** — Audit trail: who approved, when, and why the margin exception was granted  

---

## QUICK TRAINING SUMMARY — Pricing & Promotions

> **What:** 7-level price resolution, promotional schemes, margin guardrails, TPM with ROI tracking.  
> **Key rule:** Below-margin pricing requires Sales Manager approval. Always run simulation before launching a promotion.  
> **Price resolution:** Customer-specific price wins. Standard list price is the fallback.

---

<a name="crm"></a>
# MODULE 23: CRM PIPELINE

---

## 1. MODULE OVERVIEW

**What this module does:**  
The CRM Pipeline manages the sales team's leads and opportunities — from initial contact through qualification, proposal, and negotiation to won or lost. It provides visibility into the sales funnel, win/loss patterns, and sales forecast based on pipeline value.

**Why it exists in FMCG context:**  
FMCG companies have multiple channels — modern trade, wholesale distributors, hotels/restaurants/catering, export markets. Tracking all these opportunities manually in spreadsheets means deals fall through gaps, follow-ups are missed, and sales management has no visibility into what's in the pipeline.

---

## 3. KEY CONCEPTS

**Lead:** A potential new customer or a new product opportunity with an existing customer.

**Opportunity:** A lead that has been qualified — you've confirmed they are a real prospect with budget and timeline.

**Pipeline Stage:**
1. **Prospecting** — initial contact made
2. **Qualification** — confirmed budget, authority, need, timeline
3. **Proposal** — price and product proposal sent
4. **Negotiation** — terms being discussed
5. **Closed-Won** — deal signed
6. **Closed-Lost** — prospect chose competitor or no decision

**Forecast:** Expected revenue from opportunities weighted by probability of closing.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Managing a New Sales Opportunity

**Step 1 — Create Lead**
- Go to `/dashboard/crm/leads`, click **New Lead**
- Enter: Company name, contact person, phone, email
- Source: (trade show, referral, cold call, portal inquiry)
- Potential products of interest
- Click Save

**Step 2 — Qualify Lead**
- Call/meet the prospect
- Confirm: Do they have budget? Are they the decision-maker? Do they need what we sell? When do they need it?
- If qualified: click **Qualify** — lead becomes Opportunity
- Set: Estimated value (KES), Close date (expected), Probability %

**Step 3 — Move through stages**
- As you progress: drag opportunity to next stage on Pipeline Board
- At each stage: log activity (call notes, email records, visit report)

**Step 4 — Close a deal**
- When deal is agreed: click **Close Won**
- Enter: Final value, products, payment terms
- System: creates a customer record, notifies Order Processing

**Step 5 — Close a loss (important — don't hide losses)**
- If prospect chose competitor: click **Close Lost**
- Enter: Reason for loss (Price too high? Product not right? Competitor relationship?)
- Win/Loss analysis uses this data — it's valuable intelligence

---

## QUICK TRAINING SUMMARY — CRM Pipeline

> **What:** Track sales leads and opportunities from first contact to closed deal.  
> **Pipeline board:** Drag opportunities through stages. Log every call and meeting.  
> **Key insight:** Always record why you lost — it improves future strategy.  
> **AI agents:** Lead prioritization, pipeline risk detection, win/loss pattern analysis.

---

<a name="portal"></a>
# MODULE 24: CUSTOMER / DISTRIBUTOR PORTAL

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Customer Portal gives distributors and key customers a self-service interface to: view their orders, check invoices and balances, download statements, place new orders, and submit claims — without calling your sales team.

**Why it exists in FMCG context:**  
A major FMCG distributor might place 20–30 orders per week. Without a portal, each order requires a phone call or email to your sales team. With a portal, distributors self-serve 24/7, reducing your team's administrative burden by 40% and improving customer satisfaction.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Onboarding a New Distributor to the Portal

**Step 1** — Go to `/dashboard/portal/accounts`  
**Step 2** — Click **New Portal Account**  
**Step 3** — Link to existing customer record in your system  
**Step 4** — Set permissions: can they view invoices? Download statements? Place orders?  
**Step 5** — Click **Invite** — system sends email with login link and temporary password  
**Step 6** — Distributor sets their own password, agrees to terms  
**Step 7** — Distributor now has access to their own portal showing only their data  

---

## QUICK TRAINING SUMMARY — Customer Portal

> **What:** Self-service web portal for distributors — orders, invoices, statements, claims.  
> **Data isolation:** Each distributor sees ONLY their own data — never another company's data.  
> **Key benefit:** Reduces phone/email order volume by 40%. Customers can track their own accounts 24/7.

---

<a name="supplier-portal"></a>
# MODULE 25: SUPPLIER PORTAL

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Supplier Portal gives approved suppliers a window into their purchase orders, expected delivery schedules, invoice submission, payment status, and document exchange — all in a controlled, scoped environment.

**Why it exists in FMCG context:**  
Managing supplier communications via email creates confusion, lost documents, and disputes. A portal ensures all PO information is transmitted electronically, ETAs are formally committed, invoices are submitted digitally (enabling faster 3-way matching), and document exchange (certificates, SDS) is organized.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Supplier Acknowledges a Purchase Order

**Step 1** — Procurement sends PO to supplier through system (email notification)  
**Step 2** — Supplier logs into their portal  
**Step 3** — Goes to My Purchase Orders  
**Step 4** — Finds the new PO  
**Step 5** — Reviews: products, quantities, delivery date, prices  
**Step 6** — Clicks **Acknowledge** (or proposes changes)  
**Step 7** — If accepting: clicks **Confirm Delivery Date** — enters expected delivery date  
**Step 8** — Procurement sees confirmation immediately — no email needed  

---

## QUICK TRAINING SUMMARY — Supplier Portal

> **What:** Self-service interface for suppliers — view POs, confirm ETAs, submit invoices, share documents.  
> **Data isolation:** Each supplier sees only their own POs.  
> **Key benefit:** Eliminates email chains for PO acknowledgment and invoice submission.

---

<a name="dunning"></a>
# MODULE 26: DUNNING & COLLECTIONS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Dunning is the systematic process of following up on overdue invoices to collect payment. The system identifies overdue accounts, applies the appropriate collection policy, sends reminders, escalates cases, and tracks promises-to-pay (PTP).

**Why it exists in FMCG context:**  
FMCG distributors frequently test payment terms. Without a systematic dunning process, some customers stretch from 30-day to 60-day to 90-day terms — and your cash flow suffers. A dunning system enforces payment discipline consistently, without relying on individual collector initiative.

---

## 3. KEY CONCEPTS

**Aging Report:** Groups unpaid invoices by how long they are overdue: Current (not yet due), 1–30 days, 31–60 days, 61–90 days, >90 days.

**Dunning Level:** The escalation stage (Level 1 = polite reminder, Level 5 = legal action).

**Dunning Policy:** Rules for each customer group: how many reminders, at what intervals, what medium (SMS, email, letter), and at what level does credit get blocked.

**Promise-to-Pay (PTP):** A formal commitment from the customer to pay by a specific date. System tracks PTP dates and alerts when broken.

**Credit Hold:** Automatic block on new orders when customer exceeds overdue threshold.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Daily Collections Process

**Step 1 — Morning review (15 minutes)**
- Go to `/dashboard/dunning/workqueue`
- Your personal queue shows: which accounts to contact today, priority order
- Sorted by: overdue amount × risk rating

**Step 2 — Review each account**
For each customer in queue:
- View all overdue invoices (amounts, dates, invoice numbers)
- Check if there's an active PTP (did they promise to pay by today?)
- Check credit hold status

**Step 3 — Make contact**
- Phone call / WhatsApp / email to accounts payable contact
- Notes from last call visible at top of screen
- After contact: log what was discussed

**Step 4 — Record outcome**
- Customer paid: record payment in Finance module. Case resolved.
- Customer promised to pay by date: click **Record PTP** — enter date and amount
- Dispute raised: click **Open Dispute** — describe the issue
- No response: update notes, system will escalate level

**Step 5 — Escalation check**
- Accounts that haven't responded after Level 2: system escalates to Level 3 (formal letter)
- After Level 4: Credit Controller recommends legal action to Finance Manager
- If account is habitually late: recommend permanent credit limit reduction

---

## QUICK TRAINING SUMMARY — Dunning & Collections

> **What:** Systematic follow-up on overdue invoices with escalating reminders and credit control.  
> **Aging guide:** Current = OK. 1–30 days = soft reminder. 31–60 = call. 61–90 = credit hold. >90 = escalate.  
> **PTP tracking:** Record every customer promise. System alerts when broken.  
> **Best result:** Consistent weekly contact beats occasional intense chasing.

---

<a name="subscription"></a>
# MODULE 27: SUBSCRIPTION / RECURRING ORDERS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Recurring Orders automate the generation of sales orders for customers who buy the same products on a predictable schedule (weekly, monthly, quarterly). Instead of manually creating the same order repeatedly, the system creates it automatically on the right date.

**Why it exists in FMCG context:**  
Hotels, institutions, hospitals, and regular distributors often buy the same products every month. Creating the same order manually 12 times a year per customer is wasteful and error-prone. Subscription orders eliminate this work and ensure no repeat customer is forgotten.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Setting Up a Recurring Order

**Step 1** — Go to `/dashboard/recurring-orders/templates/new`  
**Step 2** — Select customer  
**Step 3** — Add products and quantities (same as a regular sales order)  
**Step 4** — Set recurrence:
   - Frequency: Monthly
   - Day of month: 1st
   - Start date: 01-Jun-2024
   - End date: 31-Dec-2024 (or leave blank for indefinite)  
**Step 5** — Set: Pre-generate X days before (e.g., 5 days before)  
**Step 6** — Click **Save Template**  
**Step 7** — On the 27th of each month: system auto-creates a draft order  
**Step 8** — Order Processing team reviews and confirms (or system auto-confirms if configured)  

---

## QUICK TRAINING SUMMARY — Recurring Orders

> **What:** Automatic creation of repeat orders for customers with predictable buying patterns.  
> **Setup:** Create a template once. System generates orders automatically on schedule.  
> **Review:** Always review auto-generated orders before dispatch — customer needs may have changed.

---

<a name="van-sales"></a>
# MODULE 28: VAN SALES / MOBILE POS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Van Sales manages the complete field sales operation — loading vans with stock, tracking sales rep routes, recording sales transactions in the field (Mobile POS), collecting payments (including M-Pesa), and reconciling van stock at day-end.

**Why it exists in FMCG context:**  
In Kenya, 60–70% of FMCG sales go through informal trade (small shops, kiosks, dukas). These customers don't call in orders — sales reps visit them with product-loaded vans and sell on the spot. Without a system to track this, you cannot know: which areas are profitable, which products move, who is collecting payments, or what the true route costs are.

---

## 3. KEY CONCEPTS

**Van Load:** The stock loaded onto a van at the start of each day (transferred from warehouse to van).

**Route:** The sequence of customer visits planned for a van on a specific day.

**Mobile POS:** The sales app on the rep's phone/tablet — records sales, prints receipts, collects M-Pesa payments.

**Van Reconciliation:** End-of-day process: stock sold + stock returned + stock remaining should equal stock loaded.

**Rider Performance Score:** System calculates a 0–100 score per rep based on: orders per day, revenue per day, collections rate, discount given, on-time visits.

**Fraud Alert:** System flags suspicious patterns: excessive discounts, payment amount differs from invoice, route deviation.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Van Management (`/dashboard/van-sales/vans`)

- List of all vans with: current status, assigned rep, today's stock value, route
- Load plan for each van
- Current GPS location (if device integration available)

### Screen: Mobile POS (`/dashboard/van-sales/pos`)

**Used by sales rep on field device (phone/tablet)**

**Field sales workflow:**
1. Open order: customer name auto-populated from route
2. Add products by scanning barcode or selecting from list
3. Prices auto-load from customer's price list
4. Apply any approved promotion
5. Select payment method:
   - **Cash:** Enter amount received
   - **M-Pesa:** System triggers STK push to customer's phone
   - **Credit:** Recorded as receivable (subject to credit limit)
6. Receipt generated (print or WhatsApp to customer)
7. Stock deducted from van inventory in real time

### Screen: Van Reconciliation (`/dashboard/van-sales/reconciliation`)

**End of day:**
- Van loaded: 500 units Detergent 1L (value: KES 92,000)
- Sold today: 380 units (value: KES 69,920)
- Returns from customers: 5 units
- Expected closing stock: 115 units
- Actual closing stock count: 112 units
- **Variance: -3 units** → requires explanation

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Complete Van Sales Day

**Morning (6:00am) — Van Loading**
**Step 1** — Warehouse loads products onto van per the day's load plan  
**Step 2** — Driver/rep confirms load: count each product, sign loading sheet  
**Step 3** — In system: Warehouse clicks **Confirm Van Load** for that van  
**Step 4** — Stock moves from warehouse to van inventory  

**During Day — Field Sales**
**Step 5** — Rep follows route, visits customers  
**Step 6** — At each visit: opens Mobile POS, creates sales transaction  
**Step 7** — Scans products or selects from list  
**Step 8** — Collects payment — M-Pesa triggers immediately  
**Step 9** — Customer receives receipt  
**Step 10** — System: real-time stock deduction from van, real-time cash tracking  

**Evening (after last visit) — Reconciliation**
**Step 11** — Rep returns to depot  
**Step 12** — Count remaining stock in van, per product  
**Step 13** — Go to Van Reconciliation screen, enter closing stock counts  
**Step 14** — System shows: variances (shortages or surpluses)  
**Step 15** — Supervisor reviews:
   - Zero variance: excellent
   - Small variance: acceptable if within tolerance (e.g., 0.5%)
   - Large variance: investigation required — damaged goods? Returns not recorded? Fraud?  
**Step 16** — Click **Close Day** — reconciliation locked, cash collected confirmed  

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Record every sale on the Mobile POS immediately — not at end of day
- ✅ Confirm M-Pesa receipt before leaving customer
- ✅ Count van stock at end of every day — never skip reconciliation
- ✅ Report any discrepancy immediately to supervisor

### DON'T:
- ❌ Never give discounts beyond your authorization level
- ❌ Never accept cash without issuing a receipt
- ❌ Don't skip a customer on the route without recording the reason (no one home, shop closed, etc.)
- ❌ Never reconcile the van without physically counting the stock

---

## QUICK TRAINING SUMMARY — Van Sales / Mobile POS

> **What:** Field sales management — van loading, route execution, mobile POS transactions, day-end reconciliation.  
> **Golden rule:** Every sale = receipt. Every day = reconciliation. No exceptions.  
> **Fraud detection:** System automatically flags excessive discounts, unverified cash, route deviations.  
> **M-Pesa:** STK push sent to customer's phone. Confirm payment before leaving.

---

<a name="contracts"></a>
# MODULE 29: CONTRACT MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Contract Management handles formal agreements with customers and suppliers — pricing contracts, volume commitment agreements, rebate agreements, and service agreements. It tracks contract terms, milestones, performance against targets, and expiry.

**Why it exists in FMCG context:**  
A supermarket chain that commits to buying KES 10,000,000 of your products per year might receive a 5% rebate at year-end. Without a contract management system, calculating who is owed what rebate and when contracts expire becomes a spreadsheet nightmare — leading to disputes and missed revenue.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Creating a Customer Contract

**Step 1** — Go to `/dashboard/contracts/new`  
**Step 2** — Select: Contract Type = Customer Sales Agreement  
**Step 3** — Select: Customer  
**Step 4** — Set: Start Date, End Date, Signed Date  
**Step 5** — Add Contract Terms:
   - Volume commitment: KES 10,000,000 per year
   - Base discount: 5%
   - Rebate: 2% end-of-year if above KES 12,000,000 purchased  
**Step 6** — Upload signed contract document  
**Step 7** — Submit for approval (Sales Manager → Finance Manager)  
**Step 8** — Once approved: contract is ACTIVE  
**Step 9** — System auto-tracks actual purchases vs. commitment  
**Step 10** — 30 days before expiry: system sends renewal reminder  

---

## QUICK TRAINING SUMMARY — Contract Management

> **What:** Track customer and supplier agreements — pricing, volumes, rebates, renewal dates.  
> **Alert:** System reminds you 30 days before contract expiry. Never let a key contract expire without renewal.  
> **Performance tracking:** View actual vs. committed volumes on each contract at any time.

---

<a name="commissions"></a>
# MODULE 30: SALES COMMISSIONS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Sales Commission Tracking calculates commissions earned by sales representatives and agents based on configurable rules (percentage of sales, tiered rates, product-specific rates). It handles disputes, adjustments, and payout processing.

**Why it exists in FMCG context:**  
Sales teams in FMCG are often incentivized through commissions. Manual commission calculation is error-prone and contested by sales reps. An automated system builds trust (reps can see their own commission in real time) and reduces Finance's monthly calculation burden from days to minutes.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Monthly Commission Run

**Step 1** — At month-end, Finance goes to `/dashboard/commissions/rules`  
**Step 2** — Verify commission rules are up to date  
**Step 3** — Go to Transactions → click **Calculate This Month**  
**Step 4** — System processes all invoiced sales for the month, applies applicable rules  
**Step 5** — Commission statement generated per sales rep  
**Step 6** — Sales reps can view their own commission breakdown in ESS portal  
**Step 7** — If rep disputes a line: they raise dispute in system with explanation  
**Step 8** — Finance reviews, approves or rejects dispute  
**Step 9** — Approved commissions go to Payroll for inclusion in pay run  

---

## QUICK TRAINING SUMMARY — Sales Commissions

> **What:** Automatic commission calculation from sales transactions based on configurable tiered rules.  
> **Who sees what:** Each rep sees their own commissions. Managers see all.  
> **Disputes:** Reps can raise disputes on specific lines. Finance resolves.  
> **Payout:** Feeds directly to Kenya Payroll module.

---
