# PHASE 3 — PROCUREMENT & FINANCE
## FMCG ERP User Manual

---

<a name="procurement-suggestion"></a>
# MODULE 14: PROCUREMENT SUGGESTION ENGINE

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Procurement Suggestion Engine automatically analyzes your inventory levels, production plan, demand forecasts, and supplier data to generate intelligent purchase recommendations. It replaces manual material shortage analysis with an automated system that suggests what to buy, from which supplier, at what price, and when.

**Why it exists in FMCG context:**  
An FMCG company with 50+ raw materials and 20+ suppliers has thousands of potential purchase decisions every month. A procurement officer manually tracking each one will inevitably miss some, over-order others, and choose the wrong supplier for lack of time to compare prices. The Suggestion Engine eliminates these errors.

**Business impact:**  
- Reduces stockout incidents by 60–80%
- Reduces excess inventory by 20–30%
- Ensures best supplier is selected based on price, lead time, and performance
- Reduces time spent on manual shortage analysis from 4 hours to 15 minutes per day

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Procurement Officer** | Reviews suggestions, contacts suppliers, creates POs |
| **Production Planner** | Reviews suggestions that affect production schedule |
| **Finance Manager** | Approves large purchase suggestions above threshold |
| **Procurement Manager** | Approves and monitors overall procurement strategy |

---

## 3. KEY CONCEPTS

**Suggestion Run:** A calculation that analyzes all materials and generates a list of recommended purchases.

**Shortage Analysis:** For each material: Required quantity (from production plan) minus available stock minus already on order = shortage.

**Urgency Classification:**
- **CRITICAL (Red):** Will run out in less than lead time — order IMMEDIATELY
- **HIGH (Orange):** Will run out within 2× lead time — order this week
- **MEDIUM (Yellow):** Will run out within planning horizon — order this month
- **LOW (Green):** Below optimal stock level — monitor

**Supplier Scoring:** The system ranks suppliers based on:
- Price per unit
- Lead time
- Quality history (% of incoming QC passes)
- Reliability (% of on-time deliveries)
- Payment terms

**MOQ (Minimum Order Quantity):** The minimum amount a supplier will sell. Suggestions automatically respect MOQs.

**Grouped Orders:** Multiple materials from the same supplier are grouped into one purchase order to reduce administration and achieve better pricing.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Procurement Suggestion Dashboard (`/dashboard/procurement-suggestion`)

**Key metrics:**
- **Active Suggestions:** Total open recommendations
- **Critical Items:** Suggestions with CRITICAL urgency (must act today)
- **Estimated Purchase Value:** Total KES if all suggestions are approved
- **Supplier Coverage:** How many suppliers involved in current suggestions

### Screen: Running a Suggestion (`/dashboard/procurement-suggestion/runs`)

**Fields:**
| Field | Description | Example |
|---|---|---|
| Planning Horizon | How many days to plan ahead | 30 days |
| Include Safety Stock | Add buffer to requirements | Yes |
| Lead Time Factor | Buffer for delays (1.0 = exact, 1.2 = add 20%) | 1.2 |
| Minimum Coverage Days | Don't suggest if stock covers more than X days | 45 days |

**Steps to run:**
1. Click **New Suggestion Run**
2. Set parameters above
3. Click **Execute**
4. Wait 30–60 seconds
5. Results appear in Suggestions list

---

### Screen: Suggestions List (`/dashboard/procurement-suggestion/suggestions`)

**Columns:**
| Column | Meaning |
|---|---|
| Material | What to buy |
| Urgency | CRITICAL / HIGH / MEDIUM / LOW |
| Current Stock | Units/KG available now |
| Days Cover | How many days current stock will last |
| Required Qty | System's recommended order quantity |
| Preferred Supplier | Highest-scored supplier for this material |
| Suggested Price | Price from preferred supplier |
| Order By Date | Latest date to place order to avoid stockout |
| Status | PENDING / APPROVED / REJECTED / CONVERTED |

**Actions:**
- **Approve** — accept the suggestion as-is
- **Modify** — change quantity or supplier before approving
- **Reject** — decline with mandatory reason
- **Convert to PR** — creates a formal Purchase Request

---

### Screen: Supplier Compare (`/dashboard/procurement-suggestion/supplier-compare`)

**Side-by-side comparison of all suppliers for a material.**

**For each supplier shows:**
- Price per unit / KG
- Current lead time (days)
- Last 6 months quality pass rate (%)
- Last 6 months on-time delivery rate (%)
- Payment terms
- Current outstanding POs
- Overall score (calculated by system)

**When to use this screen:**
- Preferred supplier's price has increased significantly — is there a better alternative?
- Preferred supplier has recent quality failures — should you switch?
- Exploring new suppliers for competitive pricing

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Weekly Procurement Review (Standard)

**Every Monday — 30-minute process**

**Step 1 — Run the suggestion engine**
- Go to `/dashboard/procurement-suggestion/runs`
- Click **New Suggestion Run**, use standard 30-day parameters
- Click **Execute** and wait for completion

**Step 2 — Tackle CRITICAL items first**
- Filter suggestions by Urgency = CRITICAL
- For each CRITICAL item:
  - Check: Is the preferred supplier available?
  - Call supplier to confirm availability and current price
  - If confirmed: click **Approve** 
  - Click **Convert to PR** — system creates Purchase Request automatically

**Step 3 — Review HIGH urgency items**
- Filter by Urgency = HIGH
- Group items by supplier (use Grouped Orders view)
- Review each group: does total order value make sense?
- Approve and convert the HIGH priority items for this week

**Step 4 — Review MEDIUM items**
- These don't need immediate action
- Scan for any surprises (unexpected shortages, new materials)
- Schedule for next week's order or batch into current week's PO if supplier allows

**Step 5 — Run AI review (optional)**
- Go to `/dashboard/procurement-suggestion/ai`
- Click **Run AI Agents**
- Review DEMAND_RISK_PREDICTOR: any upcoming shortages the basic run missed?
- Review COST_OPTIMIZER: any substitution opportunities?

---

### Workflow: Responding to Supplier Price Increase

**Situation:** SLES supplier announces 15% price increase. Current suggestion shows SLES order.

**Step 1** — Go to Supplier Compare for SLES  
**Step 2** — View all 3 approved SLES suppliers  
**Step 3** — Compare: can Supplier B match or beat new price with same quality?  
**Step 4** — Contact Supplier B — get a formal quote  
**Step 5** — Update Supplier B's price in system  
**Step 6** — Rerun comparison — does Supplier B now rank higher?  
**Step 7** — If yes: update SLES Material Master — set Supplier B as preferred  
**Step 8** — Rerun suggestions — system now recommends Supplier B  
**Step 9** — Place order with Supplier B, notify Supplier A of decision  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: SLES Critical Shortage During Production
**Situation:** Monday morning. MRP shows SLES will run out in 3 days. Production is running 24/7.

**Action:**
1. Suggestion Engine shows SLES as CRITICAL — red flag
2. Click SLES suggestion, see: 47 KG remaining, need 200 KG/day, lead time 5 days
3. We need to place emergency order NOW even for a partial delivery
4. Check Supplier Compare — can any supplier do express delivery?
5. Call Supplier A: they can deliver 500 KG within 2 days at 8% premium
6. Approve suggestion, modify to express delivery option
7. Convert to PO immediately
8. Notify Production Manager to reduce batch size temporarily to extend current stock
9. Follow up with supplier for confirmation

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Run suggestions every Monday without fail
- ✅ Act on CRITICAL items the same day they appear
- ✅ Update supplier prices when you receive new quotes
- ✅ Use Supplier Compare before switching suppliers
- ✅ Keep lead times updated when suppliers change their schedules

### DON'T:
- ❌ Don't approve suggestions blindly — check if the quantity makes business sense
- ❌ Don't reject CRITICAL items without an alternative plan
- ❌ Don't override preferred supplier without checking quality history

---

## QUICK TRAINING SUMMARY — Procurement Suggestion Engine

> **What:** Automated recommendation of what to buy, from whom, and when — based on production plan and stock.  
> **Key rule:** Check CRITICAL items first, every Monday.  
> **Urgency guide:** CRITICAL = order today. HIGH = order this week. MEDIUM = this month.  
> **Key screen:** Supplier Compare — use before any major purchasing decision.

---

<a name="subcontracting"></a>
# MODULE 15: SUBCONTRACTING

---

## 1. MODULE OVERVIEW

**What this module does:**  
Subcontracting manages production that is done by an external manufacturer (contract manufacturer) on your behalf. You issue raw materials to the subcontractor, they process them, and return finished or semi-finished goods to you. The module tracks material issuance, production at the subcontractor, receipt of finished goods, yield, and performance.

**Why it exists in FMCG context:**  
Many FMCG companies outsource certain products, packaging formats, or seasonal overflow production to contract manufacturers. This is common for sachet filling (which requires specialized equipment), contract blending, or co-packing of retail multipacks. Without systematic tracking, raw materials issued to subcontractors are impossible to account for, and discrepancies in yield become hidden losses.

---

## 3. KEY CONCEPTS

**Subcontractor:** The external company that processes your materials. Must be pre-approved and quality-certified.

**Material Issue:** Sending raw materials from your warehouse to the subcontractor's facility.

**Subcontractor Stock:** Materials physically at the subcontractor's location but owned by you. Still tracked in your system.

**Yield Record:** How much finished product was returned vs. how many materials were issued. Poor yield = materials lost at subcontractor.

**Performance Score:** System calculates a score per subcontractor based on: yield consistency, quality pass rate, on-time delivery, and cost compliance.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Full Subcontracting Cycle

**Step 1 — Create Subcontracting Order**
- Go to `/dashboard/subcontracting/orders`
- Click **New SC Order**
- Select: Subcontractor, Product to manufacture, Quantity required
- Set: Date of material issue, Expected completion date
- Link to: Sales Order or Production Plan that drives this need

**Step 2 — Issue Materials to Subcontractor**
- Go to order → click **Issue Materials**
- System shows BOM for the product — materials required listed
- Warehouse selects lots to issue (FEFO applies)
- Records: quantities issued, lot numbers
- System deducts from your warehouse, adds to "Subcontractor Stock" for that SC location
- Physical transport of materials arranged

**Step 3 — Subcontractor Produces**
- Subcontractor processes materials over agreed period
- You can monitor progress (if subcontractor has portal access, they update status)

**Step 4 — Receive Finished Goods**
- Goods arrive at your warehouse from subcontractor
- Go to SC Order → **Record Receipt**
- Enter: Quantity received, lot number from subcontractor
- System calculates: **Yield %** = Received ÷ Materials Issued × Standard Conversion Factor
- If yield below threshold (e.g., below 94%): automatic alert sent to Procurement Manager

**Step 5 — Quality Inspection**
- Received goods go to Incoming QC Hold
- QC inspects as per standard incoming inspection procedure
- If PASS: goods move to FG stock
- If FAIL: supplier claim raised against subcontractor

**Step 6 — Close Subcontracting Order**
- Once goods received and QC passed
- Click **Close Order**
- System: reconciles materials (any excess returned or written off), posts cost

---

## QUICK TRAINING SUMMARY — Subcontracting

> **What:** Track raw material issuance to contract manufacturers and receipt of finished goods.  
> **Key metric:** Yield % — monitors material losses at subcontractor.  
> **Warning sign:** Yield drops below 94% — investigate immediately.  
> **Integration:** Links to Inventory (material issue), QC (incoming inspection), Finance (cost posting).

---

<a name="landed-cost"></a>
# MODULE 16: LANDED COST ALLOCATION

---

## 1. MODULE OVERVIEW

**What this module does:**  
Landed Cost Allocation distributes all costs associated with importing goods — freight, customs duty, insurance, clearance fees, port charges — across the items in each shipment. This gives you the true cost of imported materials, not just the invoice price.

**Why it exists in FMCG context:**  
Importing SLES from India? The invoice price is $1.20/KG. But after adding: sea freight ($0.08/KG), import duty (25% = $0.30/KG), customs clearance ($0.03/KG), port storage ($0.02/KG) — your true landed cost is $1.63/KG — 36% higher than invoice price! Without landed cost allocation, your product cost calculations are significantly understated, leading to incorrect pricing and margin analysis.

---

## 3. KEY CONCEPTS

**Landed Cost:** Invoice price + all costs to get the goods from supplier factory gate to your warehouse.

**Allocation Method:** How costs are distributed across items:
- **By Value:** Each item gets a share of freight proportional to its invoice value
- **By Weight:** Each item gets a share based on its weight
- **By Quantity:** Costs split equally per unit
- **By Volume:** Split by cubic metres

**LC Document:** The landed cost record that links the GRN to all associated freight/duty/customs costs.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Recording Landed Costs for an Import Shipment

**Situation:** You receive a container of SLES (2,000 KG) and CAPB (500 KG) from India.

**Step 1 — Receive goods (GRN)**
- Standard goods receipt in Inventory module
- Items received at invoice cost only initially

**Step 2 — Create Landed Cost document**
- Go to `/dashboard/landed-cost/new`
- Link to the GRN(s) that this shipment covers
- Enter the shipment reference (e.g., invoice number, container number)

**Step 3 — Add cost components**
- Click **Add Cost Line** for each cost:
  - Freight: KES 48,000
  - Import Duty: KES 120,000
  - Customs Clearance: KES 12,000
  - Port Storage: KES 6,000
  - Insurance: KES 4,500
- Select allocation method for each (usually: Duty = By Value; Freight = By Weight)

**Step 4 — Review allocation**
- System shows how each cost is distributed across SLES and CAPB
- SLES (2,000 KG, 80% of weight) → gets 80% of freight
- Review if allocation looks reasonable
- Adjust method if needed

**Step 5 — Post the landed cost**
- Click **Post**
- System updates stock cost for SLES and CAPB to include their share of all costs
- Stock valuation now reflects true landed cost
- Finance module receives journal entry: Freight/Duty expense → Inventory Asset

---

## QUICK TRAINING SUMMARY — Landed Cost Allocation

> **What:** Distributes freight, duty, insurance, and clearance costs across imported items.  
> **Why critical:** Without it, your product costs are understated by 20–40% for imported materials.  
> **Key action:** Create a landed cost document for every import shipment before closing the GRN.  
> **Allocation:** Freight → by weight. Duty → by value. Use consistent methods for all shipments.

---

<a name="invoice-match"></a>
# MODULE 17: 3-WAY INVOICE MATCHING

---

## 1. MODULE OVERVIEW

**What this module does:**  
3-Way Invoice Matching is the process of verifying that a supplier's invoice matches both the Purchase Order (what you agreed to buy) AND the Goods Receipt Note (what you actually received) before authorizing payment. It catches duplicate invoices, overbilling, and undelivered goods before money is paid.

**Why it exists in FMCG context:**  
FMCG companies process hundreds of supplier invoices monthly. Manual matching is error-prone — overbilling is common, and duplicate invoices (paying the same invoice twice) cost companies thousands monthly. The 3-way match system automates the verification and blocks payment for any invoice that doesn't match.

**Business impact:**  
- Eliminates duplicate payments (saves companies 0.5–2% of total purchase spend)
- Catches overbilling automatically
- Ensures you only pay for goods actually received
- Reduces AP processing time by 60%
- Provides audit evidence for every payment

---

## 3. KEY CONCEPTS

**3-Way Match:** PO (agreed price and quantity) + GRN (goods received) + Invoice (supplier's bill) must all agree within tolerance.

**Tolerance Rules:** Minor discrepancies are acceptable (e.g., ±2% on price, ±1 unit on quantity). Rules are configurable per supplier and item type.

**Match Status:**
- **MATCHED:** All three documents agree — payment can proceed
- **PARTIAL_MATCH:** Two of three match — needs review
- **UNMATCHED:** Significant discrepancy — payment blocked
- **ON_HOLD:** Under investigation
- **DISPUTED:** Formal dispute raised with supplier

**Duplicate Detection:** System checks: same supplier, same amount, same or similar reference number within a time window. Flags potential duplicates for human review.

**Cumulative Billing Guard:** Prevents overpaying across multiple invoices for the same PO (e.g., PO is for KES 100,000 — system blocks payment once invoices reach that total).

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Match Dashboard (`/dashboard/invoice-match`)

**Shows:**
- Invoices matched and ready for payment today
- Invoices requiring review (partial/unmatched)
- Blocked invoices
- Potential duplicates flagged
- Total payable value this week (matched invoices)
- Average matching rate % (aim for >90%)

### Screen: Review Queue (`/dashboard/invoice-match/review-queue`)

**All invoices with discrepancies needing human review.**

**For each invoice:**
- Invoice number and supplier
- Invoice amount vs. PO amount vs. GRN amount
- Discrepancy highlighted in red
- Suggested action (e.g., "Accept — within tolerance" or "Contact supplier")
- **Actions:** Approve match, Reject invoice, Raise dispute, Request credit note

### Screen: Blocked Invoices (`/dashboard/invoice-match/blocked`)

**Payment is blocked for these invoices until resolved.**

**Common block reasons:**
- No matching GRN (goods not yet received)
- Duplicate invoice
- Amount significantly exceeds PO
- Goods received but quality hold pending

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Processing a Supplier Invoice

**Step 1 — Supplier submits invoice**
- By email, post, or through Supplier Portal
- Finance AP team enters invoice into system
  - Or supplier uploads through portal (auto-creates invoice)

**Step 2 — System runs automatic 3-way match**
- Links invoice to PO (by PO number on invoice)
- Finds GRN for that PO
- Compares: quantities, prices, totals
- Applies tolerance rules
- Auto-assigns match status

**Step 3A — If MATCHED**
- Invoice appears in "Ready for Payment" queue
- Finance Approver reviews and authorizes payment
- Payment processed on due date

**Step 3B — If PARTIAL_MATCH**
- Invoice appears in Review Queue
- AP team reviews: what is the discrepancy?
  - Example: Supplier invoiced KES 52,000, PO shows KES 50,000
  - Call supplier: "Your invoice shows 520 KG at KES 100. Our GRN shows 500 KG received. Please issue credit note for 20 KG."
  - If supplier confirms delivery of 520 KG: update GRN, rerun match
  - If price discrepancy: check if there's an updated price agreement not in system

**Step 3C — If UNMATCHED (Blocked)**
- Finance team notified
- Do not process payment
- Contact supplier with specific discrepancy details
- Possible resolutions:
  - Supplier issues credit note → re-match
  - GRN is missing → check with warehouse (goods may have arrived but not been received in system)
  - PO is wrong → amend PO with Procurement Manager approval

**Step 4 — Duplicate check**
- System automatically flags potential duplicates
- Review queue shows: "Invoice INV-2024-567 appears similar to INV-2024-234 (same supplier, same amount, 3 days apart)"
- AP team investigates: is this the same invoice submitted twice?
- If duplicate: reject second invoice, notify supplier

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Supplier Overbills by 12%
**Situation:** SLES supplier invoices for 2,400 KG. Your GRN shows only 2,100 KG received. Invoice amount = KES 184,800. GRN value = KES 161,700.

**System action:** Marks invoice as UNMATCHED (12% discrepancy exceeds tolerance).

**Your action:**
1. Check if another delivery was made but not receipted in system
2. If GRN is correct: call supplier — "We received 2,100 KG, not 2,400 KG. Please send delivery confirmation."
3. Supplier admits error and sends credit note for KES 23,100
4. Post credit note in system
5. Invoice is now matched to PO and adjusted GRN value
6. Payment authorized

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always enter invoices same day received — don't batch them
- ✅ Review Review Queue every day — unresolved items mean delayed supplier payments
- ✅ Investigate all duplicate flags — even if they look legitimate
- ✅ Require PO number on all supplier invoices (makes matching automatic)

### DON'T:
- ❌ Never authorize payment for UNMATCHED invoices without Finance Manager approval
- ❌ Don't ignore tolerance rule warnings — they are there for a reason
- ❌ Never delete invoice records — archive rejected invoices with reason

---

## QUICK TRAINING SUMMARY — 3-Way Invoice Matching

> **What:** Verifies supplier invoice matches PO (agreed) and GRN (received) before payment.  
> **Match types:** MATCHED = pay. PARTIAL = review. UNMATCHED = blocked.  
> **Duplicate detection:** System flags similar invoices from same supplier.  
> **Key rule:** Never pay an UNMATCHED invoice without Finance Manager override with documented reason.

---

<a name="bank-recon"></a>
# MODULE 18: BANK RECONCILIATION

---

## 1. MODULE OVERVIEW

**What this module does:**  
Bank Reconciliation matches the transactions in your bank account statement against the records in your ERP system. It identifies: unrecorded payments, outstanding cheques, bank charges not in system, duplicate entries, and fraudulent transactions.

**Why it exists in FMCG context:**  
A company receiving hundreds of customer payments per week (M-Pesa, bank transfers, cheques) must ensure that every KES received is recorded in the system — and that every payment made matches a supplier PO. Unreconciled bank accounts mask errors, fraud, and missing payments.

**Business impact:**  
- Catches payment fraud early
- Ensures cash flow reports are accurate
- Identifies unrecorded customer payments (increases receivables)
- Detects bank charges that weren't budgeted
- Required for annual audit

---

## 3. KEY CONCEPTS

**Bank Statement:** The official record from your bank showing all transactions.

**System Ledger:** Your ERP's record of all payments and receipts.

**Reconciliation Match:** When a bank transaction matches a system transaction exactly (same amount, same date ±tolerance, same reference).

**Outstanding:** A transaction in the bank statement but not yet in the system (or vice versa).

**Unreconciled Item:** A transaction that doesn't match anything on the other side.

**M-Pesa Reconciliation:** Special reconciliation for M-Pesa transactions which have different format, timing, and transaction codes.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Monthly Bank Reconciliation

**Frequency:** At least monthly. Weekly recommended for high-volume accounts.

**Step 1 — Import bank statement**
- Download statement from bank in CSV format
- Go to `/dashboard/bank-reconciliation/import`
- Upload the CSV file
- System parses all transactions

**Step 2 — Review auto-matched transactions**
- System automatically matches transactions by amount, date, and reference number
- View matched items — scan for any that look wrong
- Auto-matches typically cover 70–85% of transactions

**Step 3 — Handle unmatched bank transactions**
Go to Workspace for this statement.

For each unmatched bank entry:
- **Customer payment not in system:** Locate the customer, post the receipt in Sales module. Then match.
- **Bank charge/fee:** Create a bank charge journal entry. Then match.
- **Duplicate/Error:** Mark as duplicate. Raise with bank if needed.
- **Unknown debit:** Investigate immediately — could be fraud. Escalate to Finance Manager.

**Step 4 — Handle unmatched system transactions**
System transactions that don't appear in bank:
- **Outstanding cheque:** Cheque issued but not yet cashed. Leave as outstanding.
- **Uncleared deposit:** Payment sent but not yet showing in bank. Wait for it to clear.
- **Stale cheque:** Cheque issued >6 months ago, never cashed. Reverse and investigate.

**Step 5 — M-Pesa reconciliation**
- Go to M-Pesa tab in reconciliation workspace
- System automatically matches Safaricom Daraja API transactions to system records
- M-Pesa transactions have unique references — matching is usually 95%+ automatic
- Review unmatched: usually late reversals or failed transactions

**Step 6 — Lock reconciliation**
- Once balance = 0 unreconciled items (or all are properly explained):
- Click **Lock** — no further changes can be made to this period
- Generate Reconciliation Report for Finance Manager review

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Reconcile every bank account, every month — no exceptions
- ✅ Investigate any unknown debit immediately (fraud risk)
- ✅ Lock reconciliation once complete — prevents post-reconciliation tampering
- ✅ Keep bank statements for 7 years (Kenya legal requirement)

### DON'T:
- ❌ Never process payroll or large payments on a day when reconciliation is open and suspicious items exist
- ❌ Don't leave unreconciled items without explanation in the Notes field

---

## QUICK TRAINING SUMMARY — Bank Reconciliation

> **What:** Match bank statement to ERP records to ensure every transaction is accounted for.  
> **Auto-match:** System handles 70–85% automatically. Finance handles the rest manually.  
> **Red flag:** Unknown debits — investigate same day, could be fraud.  
> **Lock statement:** Once reconciled, lock it — prevents retroactive changes.

---

<a name="fixed-assets"></a>
# MODULE 19: FIXED ASSETS & DEPRECIATION

---

## 1. MODULE OVERVIEW

**What this module does:**  
Fixed Asset Accounting tracks every capital asset the company owns — factory machinery, vehicles, computers, furniture, buildings. It calculates depreciation automatically (the gradual reduction in asset value over its useful life), manages disposals, and provides the data for financial statements.

**Why it exists in FMCG context:**  
A factory has millions of KES in machinery. If you don't track these assets, your balance sheet is wrong, your tax calculations are incorrect (depreciation is tax deductible), your insurance coverage is inadequate, and maintenance can't plan when to replace aging equipment.

---

## 3. KEY CONCEPTS

**Capitalization:** The decision that an item is a fixed asset (not an expense). General rule: useful life > 1 year AND cost above company threshold (e.g., KES 50,000).

**Depreciation Methods:**
- **Straight Line:** Equal depreciation each year. Example: Mixer KES 5,000,000 over 10 years = KES 500,000/year.
- **Reducing Balance:** Higher depreciation early, lower later. Example: Vehicle depreciates 25% per year on remaining value.

**Asset Category:** Defines the depreciation method and useful life for a type of asset (e.g., "Production Machinery" = Straight Line, 10 years).

**Accumulated Depreciation:** Total depreciation posted to date.

**Net Book Value (NBV):** Cost minus accumulated depreciation = current book value.

**Disposal:** When an asset is sold, scrapped, or written off.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Adding a New Fixed Asset

**Step 1 — Asset purchased (Finance approves PO)**  
**Step 2 — Go to `/dashboard/fixed-assets/assets/new`**  
**Step 3 — Fill asset details:**
- Asset Name: "Mixer Line A — 5,000L Capacity"
- Category: Production Machinery
- Supplier: (from supplier master)
- Purchase Date: 2024-01-15
- Cost: KES 4,850,000
- Useful Life: 10 years
- Depreciation Method: Straight Line
- Location: Factory Floor — Production Area A

**Step 4 — Link to Purchase Order**
- System calculates monthly depreciation = KES 4,850,000 ÷ 120 months = KES 40,417/month

**Step 5 — Post asset**
- Finance clicks **Capitalize**
- System: debit Fixed Assets, credit Creditors/Cash
- Monthly depreciation will now run automatically on the scheduled posting day

---

### Workflow: Monthly Depreciation Posting Run

**Step 1** — Go to `/dashboard/fixed-assets/posting`  
**Step 2** — Select period (e.g., May 2024)  
**Step 3** — Click **Calculate** — system shows total depreciation for all assets this month  
**Step 4** — Review: does the amount seem right? Flag any unusual items  
**Step 5** — Click **Post** — system creates journal entries: debit Depreciation Expense, credit Accumulated Depreciation  
**Step 6** — Finance Manager reviews and approves  
**Step 7** — Depreciation report available for management accounts  

---

## QUICK TRAINING SUMMARY — Fixed Assets

> **What:** Track every capital asset from purchase through depreciation to disposal.  
> **Key rule:** Capitalize assets above KES 50,000 with useful life >1 year. Expense items below threshold.  
> **Monthly action:** Run depreciation posting — takes <5 minutes.  
> **Disposal:** Always record asset disposals on the day they occur to avoid overstating balance sheet.

---

<a name="dimensions"></a>
# MODULE 20: ACCOUNTING DIMENSIONS & COST CENTERS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Accounting Dimensions allow you to tag every transaction with additional classification codes — by department, cost center, project, or product line. This enables detailed reporting: "How much did Production Department spend on utilities this month?" or "What is the profitability of the Shampoo product line?"

**Why it exists in FMCG context:**  
A factory that produces 10 product lines needs to know which product line is profitable. Without cost center coding, all costs are lumped together and you cannot see whether your premium shampoo is subsidizing your budget detergent.

---

## 3. KEY CONCEPTS

**Dimension Type:** A category of classification. Examples:
- **Department:** Production, Sales, Finance, HR, Marketing
- **Cost Center:** Production Line A, Production Line B, Warehouse, Head Office
- **Product Line:** Detergents, Shampoos, Creams, Wipes
- **Project:** New Product Launch 2024, Expansion Project

**Dimension Value:** A specific code within a dimension (e.g., within Department: "PROD", "SALES", "HR").

**Default Dimension Rules:** Automatically apply dimensions to transactions based on product, supplier, or account. This reduces manual tagging.

**Allocation Run:** Distribute indirect costs (e.g., factory utility bills) across production lines based on usage percentage.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Tagging a Transaction with Dimensions

**Step 1** — Any financial transaction (purchase invoice, expense claim, sales invoice) has a Dimensions tab  
**Step 2** — Open the transaction, click **Dimensions** tab  
**Step 3** — Select values for each applicable dimension:
   - Department: PRODUCTION
   - Cost Center: MIXER_LINE_A
   - Product Line: DETERGENTS  
**Step 4** — Save transaction  
**Step 5** — Reports can now filter by any combination of dimensions  

### Workflow: Monthly Cost Allocation

**Situation:** Factory utility bill of KES 450,000 needs to be split across 3 production lines based on electricity consumption.

**Step 1** — Go to `/dashboard/dimensions/allocation-run`  
**Step 2** — Select: Source = Utility Cost, Period = May 2024  
**Step 3** — Define allocation basis: Line A = 45%, Line B = 35%, Line C = 20%  
**Step 4** — Click **Run Allocation**  
**Step 5** — System creates journal entries splitting the KES 450,000 across the three cost centers  
**Step 6** — Cost center reports now show each line's true utility cost  

---

## QUICK TRAINING SUMMARY — Dimensions & Cost Centers

> **What:** Tag every transaction with department, cost center, product line, and project codes.  
> **Why:** Enables management reporting by department, product line, or project.  
> **Best practice:** Set up default dimension rules so most transactions are tagged automatically.  
> **Monthly action:** Run cost allocation to distribute indirect costs across cost centers.

---
