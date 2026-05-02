# PHASE 2 — INVENTORY, QUALITY & COMPLIANCE
## FMCG ERP User Manual

---

<a name="inventory"></a>
# MODULE 9: INVENTORY & FEFO CONTROL

---

## 1. MODULE OVERVIEW

**What this module does:**  
Inventory management tracks every item in every location across all warehouses in real time. FEFO (First Expired, First Out) control enforces the rule that older stock — with earlier expiry dates — is always used or shipped before newer stock, preventing waste and ensuring product freshness.

**Why it exists in FMCG context:**  
FMCG products have shelf lives. Shampoo expires. Detergent degrades. Packaging materials deteriorate in humidity. If your warehouse ships products in random order, you will send customers products that expire before they can sell them — this destroys your relationship and reputation. FEFO is not optional in FMCG — it is a food safety and commercial requirement.

**Business impact:**  
- Eliminates expired stock in warehouses
- Ensures customers always receive maximum shelf life
- Reduces write-offs of expired inventory by 40–70%
- HACCP and food safety compliance
- Accurate real-time stock visibility across all locations

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Warehouse Manager** | Overall stock visibility, approves adjustments |
| **Store Keeper / Warehouseman** | Daily receipts, picks, transfers |
| **Production Planner** | Reviews stock levels for MRP inputs |
| **Finance** | Reviews stock valuation and write-offs |
| **Quality Control** | Places holds on specific lots |
| **Dispatch Team** | Picks orders using FEFO guidance |

---

## 3. KEY CONCEPTS

**Stock Location:** The specific physical location where stock is stored (Warehouse A, Rack B3, Cold Store 1).

**Lot Number:** A unique identifier for a batch of materials/products produced or received together. The lot number links to a specific production date, expiry date, and supplier.

**Expiry Date:** The date after which the product should not be used or sold.

**FEFO:** First Expired, First Out. The system always directs picking to the lot with the earliest expiry date first.

**FIFO:** First In, First Out. Alternative rule — use oldest received stock first.

**Stock Status:**
- **Available:** Normal stock, free to use/ship
- **Quality Hold:** Awaiting QC inspection result
- **Quarantine:** Failed QC or under investigation
- **Blocked:** Reserved for a specific purpose
- **Expired:** Past expiry date — cannot be used

**Stock Adjustment:** A correction to stock quantity (increase or decrease). Always requires a reason and approval.

**Stock Valuation:** The monetary value of your inventory (Quantity × Cost).

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Inventory Overview (`/dashboard/inventory`)

**Key metrics at top:**
- **Total Stock Value (KES)** — total value of all inventory
- **SKUs in Stock** — number of unique products/materials with stock
- **Critical Stock Items** — items below reorder point (red)
- **Expiring in 30 Days** — lots expiring soon (orange)
- **Expired Stock** — lots past expiry date (requires action)

**Main table columns:**
| Column | Description |
|---|---|
| Product / Material | Item name |
| Total Quantity | Sum across all lots and locations |
| UoM | Unit of measure |
| Available | Quantity not on hold or reserved |
| On Hold | Quantity under QC hold |
| Reserved | Committed to production/sales orders |
| On Order | Quantity ordered, not yet received |
| Reorder Point | Minimum stock level trigger |
| Status | OK / LOW / CRITICAL / OUT |

**Actions:**
- Click any row for **lot-level detail**
- **Stock Adjustment** — add or remove stock
- **Transfer** — move stock between locations
- **Place on Hold** — put a lot under QC investigation
- **Write Off** — dispose of expired/damaged stock

---

### Screen: Lot Detail (click any product → Lots tab)

**Shows every lot of that product:**
| Column | Description |
|---|---|
| Lot Number | Unique batch ID |
| Quantity | Available quantity in this lot |
| Expiry Date | When this lot expires |
| Production Date | When it was made / received |
| Location | Where physically stored |
| Status | Available / Hold / Quarantine / Expired |
| FEFO Order | System rank for picking (1 = pick first) |

---

### Screen: Stock Movements (`/dashboard/movements`)

**Complete audit trail of every movement:**
- Every receipt, issue, transfer, adjustment, write-off
- Shows: Date, Type, Quantity, Lot, From Location, To Location, User, Reference

**Filters:**
- By material/product
- By movement type
- By date range
- By user
- By lot number

---

### Screen: FEFO Configuration (`/dashboard/shelf-life/fefo-config`)

**For each product category, define:**
- Minimum shelf life for customer shipments (e.g., "must have at least 75% of shelf life remaining")
- FEFO enforcement level (STRICT / WARNING / ADVISORY)
- Special handling rules for cold chain items

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Receiving Goods (Raw Materials from Supplier)

**Step 1 — Goods arrive at gate**
- Physical check: are the goods in good condition? Correct quantity? Correct labels?
- Cross-check against the Purchase Order

**Step 2 — Open Goods Receipt in system**
- Go to `/dashboard/inventory`
- Click **New Goods Receipt**
- Select the related Purchase Order from dropdown

**Step 3 — Record receipt details**
- For each item on the PO:
  - Enter: Quantity received (may differ from PO)
  - Enter: Lot/Batch number from supplier's label
  - Enter: Expiry date (from label)
  - Enter: Manufacturing date (if available)
  - Select: Storage location (which rack/bay)
  - Attach: Supplier Certificate of Analysis (if required by QC policy)

**Step 4 — Initial QC inspection**
- System prompts: "This material requires incoming QC inspection"
- Status = QUALITY_HOLD
- QC team receives notification
- Material is stored but cannot be used until QC releases

**Step 5 — QC releases (or holds)**
- If QC passes: status changes to AVAILABLE, MRP can now use this stock
- If QC fails: status = QUARANTINE, procurement team notified for supplier claim

**Step 6 — System posts the goods receipt**
- Stock quantity increases
- Purchase Order is updated (partially/fully received)
- Finance module: GRN posted for 3-way matching

---

### Workflow: Picking for a Sales Order (FEFO Enforcement)

**Situation:** Customer orders 500 units of Floor Cleaner 1L.

**Step 1** — Dispatch team opens the Sales Order in system  
**Step 2** — Click **Generate Picking List**  
**Step 3** — System automatically selects the lot with the **earliest expiry date** first  
**Step 4** — If that lot has insufficient quantity, system splits: use all of Lot A, take remainder from Lot B (next earliest)  
**Step 5** — Picking list shows: "Pick 300 units from Lot FC1L-2024-001 (expires Oct 2025), then 200 units from Lot FC1L-2024-003 (expires Dec 2025)"  
**Step 6** — Warehouse team picks and scans each lot barcode to confirm  
**Step 7** — System updates stock: deducts from confirmed lots  
**Step 8** — Delivery note generated with lot numbers for traceability  

**What happens if you try to override FEFO?**  
- System shows a WARNING (orange): "You are picking a newer lot while an older lot exists"  
- If FEFO is set to STRICT, the system will **block** the pick unless a manager approves with reason  
- Reason codes: "Customer request", "Lot under investigation", "Older lot reserved for another order"  

---

### Workflow: Stock Adjustment (Correction)

**Situation:** Physical count shows 450 units of product but system shows 500. You need to adjust.

**Step 1** — Go to `/dashboard/inventory`, find the product  
**Step 2** — Click **Stock Adjustment**  
**Step 3** — Select reason code: "Count discrepancy — short count"  
**Step 4** — Enter the correct quantity: 450  
**Step 5** — System shows: you are reducing stock by 50 units  
**Step 6** — System requires Warehouse Manager approval for adjustments above threshold  
**Step 7** — Manager reviews and approves  
**Step 8** — Stock is corrected, adjustment is logged in audit trail with your user ID  
**Step 9** — Finance is notified of inventory value adjustment  

---

### Workflow: Handling Expired Stock

**Situation:** System alert: "Lot FC1L-2023-045 has expired — 800 units."

**Step 1** — QC Manager is notified automatically  
**Step 2** — QC Manager goes to inventory, finds the expired lot  
**Step 3** — Places lot under QUARANTINE (physical segregation required)  
**Step 4** — Raises a Quality Disposition request:
- Options: Rework, Reprocess, Donate, Dispose
- For expired goods: usually DISPOSE  
**Step 5** — Finance Manager approves write-off (above threshold = management approval)  
**Step 6** — QC and Warehouse witness disposal  
**Step 7** — Write-off posted in system with reason, lot number, quantity, and value  
**Step 8** — Finance posts the expense to Inventory Write-off cost center  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario A: Customer Complaint — Expired Product
**Situation:** Distributor calls to say they received Floor Cleaner that expires in 2 months. Their customers won't accept less than 75% shelf life remaining.

**Investigation using inventory system:**
1. Ask distributor for the lot number (from the bottle)
2. Go to `/dashboard/inventory`, search by lot number
3. Find: when was this lot produced? What was the expiry date when shipped?
4. Check if FEFO config for this customer is set correctly
5. Was the FEFO rule bypassed? Check stock movements — who picked this lot?
6. Update FEFO config for this customer to require 75% minimum shelf life remaining
7. Raise credit note for returned goods

---

### Scenario B: Raw Material Shortage Mid-Production
**Situation:** Production is stopped at 60% because SLES lot is exhausted and the next lot is under QC hold.

**Action:**
1. Production Supervisor raises alert in system
2. QC Manager expedites inspection of the held lot (request urgent QC)
3. Meanwhile, check if any other location has available SLES
4. If not, check if SLES is expected from a pending PO (check Goods in Transit)
5. If expedited QC passes, release lot immediately
6. Production resumes
7. Root cause analysis: was safety stock too low? Update reorder point.

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always record lot numbers when receiving goods (without this, FEFO cannot work)
- ✅ Place any suspicious or damaged goods on Quality Hold immediately
- ✅ Physically segregate Quarantine stock in a clearly marked area
- ✅ Run a stock count weekly for fast-moving items, monthly for slow movers
- ✅ Review "Expiring in 30 Days" report every Monday

### DON'T:
- ❌ Never pick stock without checking the system's FEFO recommendation
- ❌ Don't adjust stock without proper approval — every adjustment needs a reason
- ❌ Never receive goods without recording the lot number — no lot number = no traceability
- ❌ Don't ignore expired stock alerts — they are a legal and safety issue
- ❌ Never use QUARANTINE stock for production without QC release

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "FEFO shows lot that doesn't exist in warehouse" | Stock system shows available but physical stock is missing | Run cycle count for that product |
| "Cannot post goods receipt — PO not found" | GR linked to wrong PO or PO already fully received | Check PO status; contact procurement |
| "Stock adjustment blocked" | Quantity exceeds approval threshold | Request Warehouse Manager approval |
| "Lot cannot be shipped — minimum shelf life not met" | FEFO/shelf life config blocks shipment | Check if another lot has more remaining shelf life; contact QC |
| "Stock count won't close" | Unresolved variances above tolerance | Investigate variances; get manager approval for write-off |

---

## QUICK TRAINING SUMMARY — Inventory & FEFO

> **What:** Real-time stock visibility with automated FEFO picking enforcement.  
> **Key rule:** Always record lot numbers. FEFO is not optional in FMCG.  
> **Key screens:** Inventory overview, Lot detail, Stock movements, Picking list.  
> **Emergency action:** Expired stock → Quarantine immediately → QC Manager investigation → Write-off with approval.

---

<a name="traceability"></a>
# MODULE 10: LOT TRACEABILITY & BATCH RECALL

---

## 1. MODULE OVERVIEW

**What this module does:**  
Lot Traceability allows you to trace the complete journey of any material or product — from the raw material supplier, through production, to the end customer. Batch Recall provides the tools to quickly identify all affected products and customers in the event of a quality or safety issue.

**Why it exists in FMCG context:**  
Regulatory bodies require FMCG manufacturers to be able to trace products. If a contaminated batch of raw material is discovered, you need to know:
- Which production batches used that material?
- Which customers received those finished goods?
- Which lots are still in your warehouse?
All within hours — not days.

**Business impact:**  
- Regulatory compliance (KEBS, FDA, EU)
- Rapid recall execution — minimize consumer harm
- Supplier accountability — prove which supplier's material caused an issue
- Minimize recall scope — trace precisely, don't pull everything off shelves

---

## 2. KEY CONCEPTS

**Forward Trace:** Start from a raw material lot → find all finished products made with it → find all customers who received those products.

**Backward Trace:** Start from a finished product lot → find all raw materials that went into it → find the supplier of each material.

**Genealogy Graph:** Visual network diagram showing the complete chain: Supplier → RM Lot → Production Batch → FG Lot → Customer.

**Mock Recall Drill:** A practice exercise — trace a hypothetical lot and measure how quickly and completely you can identify the scope.

**Recall Level:**
- **Level 1 (Consumer Level):** Product must be retrieved from all consumers — highest urgency
- **Level 2 (Retail Level):** Product pulled from store shelves
- **Level 3 (Distributor Level):** Product retrieved before reaching retail

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Trace Dashboard (`/dashboard/traceability`)

- Number of active recalls
- Recall completion % (how many units retrieved vs. total at risk)
- Open traceability queries (pending investigations)
- Mock drill schedule

### Screen: Trace Search (`/dashboard/traceability/search`)

**Quick search by any identifier:**
- Lot number
- Product name
- Supplier name
- Date range
- Customer name

**Returns:** All records connected to that search parameter

---

### Screen: Forward Trace (`/dashboard/traceability/forward`)

**Start with a raw material lot, find all affected finished goods and customers.**

**Example:**
1. Enter: Lot number "SLES-2024-001-BASF" (a suspect SLES lot)
2. Click **Trace Forward**
3. System returns:
   - Production batches that used this SLES lot: "LD1L-2024-056, LD1L-2024-057, SH500ML-2024-023"
   - Finished goods lots produced: "FG-LD1L-2024-0890, FG-LD1L-2024-0891"
   - Customers shipped to: "Carrefour Westgate (200 cases), Naivas Thika (150 cases)"
   - Quantity in your warehouse: "300 cases (still in FG store)"

---

### Screen: Backward Trace (`/dashboard/traceability/backward`)

**Start with a finished product lot, find all raw materials used.**

**Example:**
1. Customer reports problem with Shampoo 500ml, Lot "SH500ML-2024-023"
2. Enter lot number
3. Click **Trace Backward**
4. System shows all raw materials in this batch:
   - SLES 70%: Lot "SLES-2024-001-BASF" (BASF, received 15-Jan-2024)
   - CAPB 30%: Lot "CAPB-2024-005-EVK" (Evonik, received 8-Jan-2024)
   - Fragrance: Lot "FR-2024-012-IFF" (IFF, received 20-Jan-2024)
   - Preservative: Lot "PRES-2024-003-DOW" (Dow, received 2-Jan-2024)
   - Bottles: Lot "BTL-2024-034" (local supplier, received 18-Jan-2024)
5. Send this data to your QC and procurement teams
6. Supplier of any suspect material can now be notified

---

### Screen: Genealogy Graph (`/dashboard/traceability/genealogy`)

**Visual network map showing the full trace path.**

Nodes:
- 🔶 Supplier (orange)
- 🔵 Raw Material Lot (blue)
- 🏭 Production Batch (factory icon)
- 🟢 Finished Goods Lot (green)
- 🛒 Customer (shopping cart icon)

Lines between nodes show material flow direction.

Click any node to see details (dates, quantities, status).

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Initiating a Recall

**Situation:** QC discovers a contamination issue with a SLES lot. You need to identify and recall all affected products.

**Step 1 — Confirm the issue**
- QC Manager documents the issue: what contamination, which supplier lot
- Production Manager confirms which production batches used that SLES lot

**Step 2 — Run Forward Trace**
- Go to `/dashboard/traceability/forward`
- Enter suspect SLES lot number
- System generates full list: production batches, FG lots, customers, quantities

**Step 3 — Quarantine in-house stock**
- All FG lots identified in the trace: immediately place on QUARANTINE in inventory
- Physical segregation required — label with "RECALL HOLD — DO NOT SHIP"

**Step 4 — Create a Recall record**
- Go to `/dashboard/traceability/recalls`
- Click **New Recall**
- Enter: Affected lots, recall level (1/2/3), reason, responsible person
- System auto-populates customer list and contact information

**Step 5 — Notify customers**
- System generates a recall notification letter per customer
- Letter includes: product, lot numbers, quantity, reason for recall, return instructions
- Send via email from the recall screen
- Log all communications in recall record

**Step 6 — Track retrieval**
- As customers return goods, record in the recall tracker
- Recall completion % updates automatically
- Target: 100% retrieval within 24–72 hours depending on recall level

**Step 7 — Close recall**
- Once all stock accounted for: click **Close Recall**
- Post-recall report generated
- Root cause analysis completed by QC
- Supplier notified and credit/replacement arranged

---

### Workflow: Mock Recall Drill

**Frequency:** Every 6 months (required by many retailers and food safety certifications)

**Step 1** — Go to `/dashboard/traceability/mock-recall`  
**Step 2** — Select a random finished goods lot from last 3 months  
**Step 3** — Start timer  
**Step 4** — Run Forward Trace from the raw materials in that lot  
**Step 5** — Identify all customers who received that lot  
**Step 6** — Document how long it took to:
   - Identify raw material suppliers: target <30 minutes
   - Identify all affected FG lots: target <1 hour
   - Identify all affected customers: target <2 hours
**Step 7** — Complete the drill report  
**Step 8** — Record drill results in system  
**Step 9** — If any step took too long, investigate why and improve  

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Record lot numbers at every stage — receipt, production, dispatch
- ✅ Run mock recall drills every 6 months
- ✅ Keep customer delivery records permanently (recall can happen years later)
- ✅ Act within 1 hour of confirming a potential recall — speed saves lives and brand reputation

### DON'T:
- ❌ Never ship products without recording the lot number on the delivery note
- ❌ Don't wait for all information before starting a recall — partial information → partial recall is better than no action
- ❌ Never destroy evidence of a potential recall until regulatory authority confirms you can

---

## QUICK TRAINING SUMMARY — Traceability & Recall

> **What:** Full supply chain trace from raw material supplier to customer, with rapid recall capability.  
> **Forward Trace:** RM lot → which customers received affected finished goods.  
> **Backward Trace:** FG lot → which raw materials and suppliers were involved.  
> **Recall rule:** Start within 1 hour of confirmed issue. Quarantine in-house stock first. Notify customers second.

---

<a name="qms"></a>
# MODULE 11: QUALITY CONTROL & QMS / HACCP

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Quality Management System (QMS) manages all quality control activities: inspections, test results, deviations, corrective actions, HACCP control points, and allergen validation. It integrates with production orders to enforce quality gates before goods can move forward.

**Why it exists in FMCG context:**  
FMCG products are used by consumers. A contaminated batch of shampoo, a wrongly labeled allergen, or an underdosed preservative can cause consumer harm, product recalls, and regulatory fines. QMS ensures every batch meets specification before leaving the factory.

**Business impact:**  
- Consumer safety protection
- Regulatory compliance (KEBS standards, ISO 22000, FSSC 22000)
- Reduced rework and waste from early detection
- Customer satisfaction through consistent quality
- Legal protection — documented evidence of quality controls

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **QC Inspector** | Conducts inspections, records results |
| **QC Manager** | Reviews results, approves/rejects batches |
| **Production Supervisor** | Responds to quality holds, corrective actions |
| **R&D Manager** | Defines quality specifications and test parameters |
| **Food Safety Team** | Manages HACCP plans and CCPs |
| **Regulatory Affairs** | Uses QMS reports for audits and certifications |

---

## 3. KEY CONCEPTS

**Inspection:** A formal quality check with documented results. Types:
- **Incoming Inspection:** Raw materials from supplier
- **In-Process Inspection:** During production (e.g., viscosity check every 2 hours)
- **Finished Goods Inspection:** Before releasing to FG warehouse

**QC Parameter:** A specific test (e.g., pH, viscosity, fill weight). Each parameter has:
- Test method (how to measure)
- Specification (acceptable range: e.g., pH 6.5–7.5)
- Warning limit (approaching spec limit — investigate)
- Reject limit (outside spec — fail)

**Deviation:** A result that falls outside specification. Requires investigation.

**CAPA (Corrective Action & Preventive Action):** The formal process to:
1. Correct the immediate problem
2. Find root cause
3. Prevent recurrence

**HACCP (Hazard Analysis Critical Control Points):** A food safety system identifying the key points in production where contamination must be controlled. Each CCP has:
- Critical limit (e.g., temperature must be >72°C for 15 seconds)
- Monitoring procedure
- Corrective action if limit is breached

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: QMS Dashboard (`/dashboard/qms`)

- **Open Inspections:** Batches waiting for QC inspection
- **Pending Deviations:** Out-of-spec results needing investigation
- **Open CAPAs:** Corrective actions in progress
- **HACCP Alerts:** CCP monitoring results that triggered alerts
- **Quality Release Rate:** % of batches passing first-time

### Screen: QC Inspections (`/dashboard/qms/inspections`)

**Creating a new inspection:**
1. Click **New Inspection**
2. Select: Inspection Type (Incoming / In-Process / FG)
3. Link to: Production Order or GRN
4. Select: Inspection Template (which tests to run)
5. Assign to: QC Inspector
6. System generates checklist of tests to perform

**Recording results:**
1. For each test:
   - Enter actual measured value
   - System automatically checks against specification
   - Green = PASS, Red = FAIL, Orange = WARNING
2. Add notes if needed
3. Upload lab results document (optional)
4. Click **Complete Inspection**
5. If all PASS: system prompts "Release Batch" — one click releases the production order
6. If any FAIL: system prompts deviation investigation

---

### Screen: HACCP Analysis (`/dashboard/qms/haccp`)

**For each product line, defines:**
- Process flow diagram (mixing → filling → packaging → storage)
- Hazard analysis per step (biological, chemical, physical hazards)
- Critical Control Points (CCPs) — steps where control is CRITICAL
- Critical limits per CCP
- Monitoring frequency and method

**Example HACCP entry for liquid detergent:**

| Process Step | Hazard | CCP? | Critical Limit | Monitoring | Corrective Action |
|---|---|---|---|---|---|
| Chemical mixing | Chemical contamination | Yes | pH 6.5–7.5 | Every batch, pH meter | Hold batch, adjust pH, retest |
| Filling | Underfill (consumer fraud) | Yes | Min 990ml per unit | Every 50 units, net weight check | Stop line, adjust filler, re-check |
| Labeling | Wrong label (allergen error) | Yes | Label must match formula | 100% visual check | Stop line, remove incorrect labels |

---

### Screen: CCP Monitoring (`/dashboard/qms/ccp`)

**Daily monitoring log for each Critical Control Point.**

**How to record:**
1. At each monitoring point (e.g., every batch for pH):
   - Click **New CCP Record**
   - Select: Which CCP, which production order
   - Enter: Measured value
   - If value outside critical limit: system automatically triggers Corrective Action alert
   - Supervisor receives immediate notification
   - Production must STOP until corrective action completed

---

### Screen: Deviations (`/dashboard/qms/deviations`)

**Opened when any QC result is outside specification.**

**Fields:**
- Deviation type (Out of Spec, Process deviation, Equipment failure)
- Affected product and lot
- Description of the deviation
- Immediate action taken (batch held, etc.)
- Root cause investigation
- CAPA linked

---

### Screen: Corrective Actions (`/dashboard/qms/corrective-actions`)

**CAPA workflow:**
1. **Contain:** Stop the immediate problem (hold batch, quarantine materials)
2. **Investigate:** What caused this? (5-Why analysis tool built in)
3. **Correct:** Fix this specific occurrence
4. **Prevent:** Change process/procedure to prevent recurrence
5. **Verify:** Did the correction work? (follow-up check)

**5-Why tool example:**
- Why did the batch fail pH? → SLES was added before water
- Why was SLES added first? → Operator followed old procedure
- Why was old procedure used? → New procedure not communicated to night shift
- Why not communicated? → Training session only done for day shift
- Root cause: Incomplete training rollout → Add night shift to training schedule

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Incoming Raw Material Inspection

**Step 1 — Goods arrive**
- Receiving team notes supplier lot number and quantity
- Places material on "Incoming QC Hold" location (physically separated)
- Creates GRN in system

**Step 2 — QC Inspector notified**
- System sends notification when GRN is created
- Inspector goes to QMS → Inspections → click the pending inspection

**Step 3 — Conduct inspection**
- Follow the inspection template:
  - Visual inspection (color, odor, packaging integrity)
  - Sample collection per procedure
  - Lab testing (viscosity, pH, concentration, etc.)
- Record all results in the system

**Step 4 — Review results**
- If ALL PASS: Click **Release** — material status changes to AVAILABLE
- If ANY FAIL: Click **Reject** — material goes to QUARANTINE
  - Supplier is notified automatically
  - Procurement team informed to arrange replacement
  - Supplier must provide Certificate of Analysis and root cause

**Step 5 — Archive certificate**
- Upload supplier Certificate of Analysis document
- System links it to the material lot permanently

---

### Workflow: In-Process Quality Check

**Situation:** Mixer A is running a batch of Shampoo 500ml. In-process checks are required every 2 hours.

**Step 1** — At 2-hour mark, operator stops for in-process check  
**Step 2** — QC Inspector takes sample from mixing vessel  
**Step 3** — Opens QMS → Inspections → finds the in-process inspection for this production order  
**Step 4** — Records: viscosity, pH, active ingredient concentration  
**Step 5** — Results automatically checked against spec:
   - pH: 6.8 (PASS — spec is 6.5–7.2)
   - Viscosity: 450 cP (PASS — spec is 400–600 cP)
   - SLES concentration: 11.2% (FAIL — spec is 11.5–12.5%)  
**Step 6** — System alerts: "SLES concentration below spec. Batch on hold."  
**Step 7** — Production stopped. Deviation opened automatically.  
**Step 8** — Formulation Manager informed — recommends adding 30 KG SLES and remixing  
**Step 9** — After correction: re-sample and re-test  
**Step 10** — PASS: batch released, production continues  

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Complete HACCP monitoring records promptly — they are legal documents
- ✅ Open a CAPA for EVERY out-of-spec result, no matter how minor
- ✅ Keep all QC records for minimum 2 years (longer for food/pharma)
- ✅ Calibrate all QC equipment on schedule and record in system
- ✅ Run mock recalls through the QMS records to verify completeness

### DON'T:
- ❌ Never release a batch without completing the required inspections
- ❌ Don't ignore WARNING results (orange) — they become FAIL results if ignored
- ❌ Never back-date QC records — timestamp fraud is a serious violation
- ❌ Don't close a CAPA until the preventive action has been verified to work

---

## QUICK TRAINING SUMMARY — QMS & HACCP

> **What:** Complete quality management from incoming inspection through production to finished goods.  
> **Key principle:** No batch leaves QC hold without inspection. Every failure triggers CAPA.  
> **HACCP:** Identifies the critical control points — if a CCP limit is breached, production stops immediately.  
> **Best practice:** Complete all QC records in real time. Paper backdating destroys audit credibility.

---

<a name="gs1"></a>
# MODULE 12: GS1 BARCODE & LABEL PRINTING

---

## 1. MODULE OVERVIEW

**What this module does:**  
GS1 Barcode management generates standardized barcodes and product labels for all finished goods. It supports GS1-128, EAN-13, QR codes, and SSCC (pallet) codes. Label templates are configurable per product and per customer.

**Why it exists in FMCG context:**  
Modern retail chains (Carrefour, Naivas, Quickmart) require GS1-compliant barcodes on every product and pallet. Without correct barcodes, your products cannot be scanned at checkout, cannot be received into retailer warehouses, and will be rejected. GS1 compliance is a non-negotiable requirement for formal retail.

---

## 2. KEY CONCEPTS

**EAN-13:** The standard product barcode on consumer goods (the black-and-white barcode on every product in a supermarket). 13-digit number.

**GS1-128:** Advanced barcode encoding lot number, expiry date, quantity, and other data. Used for logistics and B2B.

**SSCC (Serial Shipping Container Code):** Unique barcode for each pallet. Tracks pallets through the supply chain.

**GS1 Company Prefix:** Your company's unique GS1 identifier (must be registered with GS1 Kenya). The prefix is the first digits of every barcode you generate.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Printing Product Labels

**Step 1** — Production order is completed and QC approved  
**Step 2** — Go to `/dashboard/gs1/print-queue`  
**Step 3** — Select the production order  
**Step 4** — System auto-populates: Product, Lot Number, Expiry Date, Production Date, Quantity  
**Step 5** — Select Label Template (standard, export, etc.)  
**Step 6** — Enter printer name and label quantity  
**Step 7** — Click **Print**  
**Step 8** — Labels print with: EAN-13 barcode, GS1-128 with lot/expiry, product name, ingredients, weight  

### Workflow: Generating SSCC Pallet Labels

**Step 1** — When palletizing finished goods for dispatch  
**Step 2** — Go to `/dashboard/gs1/sscc`  
**Step 3** — Click **New SSCC**  
**Step 4** — Select: products on this pallet, quantities, destination  
**Step 5** — System generates unique SSCC number  
**Step 6** — Print pallet label (large format, visible from all sides of pallet)  
**Step 7** — SSCC linked to all lot numbers on the pallet for traceability  

---

## QUICK TRAINING SUMMARY — GS1 & Labels

> **What:** GS1-compliant barcode generation and label printing for all products and pallets.  
> **Key rule:** Never ship to formal retail without a valid, scanned EAN-13 barcode.  
> **Pallet labels (SSCC):** Required for all pallet shipments. Links pallet to all contained lots.  
> **Setup requirement:** GS1 Company Prefix must be registered with GS1 Kenya before going live.

---

<a name="allergen"></a>
# MODULE 13: ALLERGEN & NUTRITION MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Allergen Management tracks which allergens are present in every raw material and finished product. Nutrition Management calculates the nutritional profile of each product from its formula. Both generate the information needed for consumer labels and export documentation.

**Why it exists in FMCG context:**  
Regulatory requirements in Kenya, East Africa, and export markets mandate allergen declarations on product labels. If a product contains peanuts, tree nuts, gluten, or dairy — this MUST appear on the label. A missing allergen declaration is a product recall, regulatory fine, and potentially a life-threatening incident for allergic consumers.

---

## 3. KEY CONCEPTS

**Allergen Master:** The complete list of regulated allergens (14 major allergens under EU law + Kenya regulations):
- Cereals with gluten (wheat, rye, barley, oats)
- Crustaceans (shrimp, crab)
- Eggs
- Fish
- Peanuts
- Soybeans
- Milk/dairy
- Tree nuts (almonds, cashews, etc.)
- Celery
- Mustard
- Sesame
- Sulphur dioxide / sulphites
- Lupin
- Molluscs

**May Contain:** Cross-contamination risk — the product doesn't intentionally contain the allergen, but it is processed on shared equipment with allergen-containing products.

**Allergen Roll-Up:** The automatic calculation of which allergens are in a finished product based on its BOM (all ingredients).

**Label Readiness Score:** A quality check that measures if a product's label correctly declares all allergens present. Should be 100% before production.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Setting Up Allergen Profile for a New Raw Material

**Step 1** — When adding a new raw material to Material Master  
**Step 2** — Go to `/dashboard/allergen/material-profiles`  
**Step 3** — Find the material, click **Set Allergen Profile**  
**Step 4** — Review the supplier's Safety Data Sheet and Certificate of Analysis  
**Step 5** — For each allergen: mark as CONTAINS / MAY CONTAIN / FREE  
**Step 6** — Upload evidence (supplier document)  
**Step 7** — Save — allergen profile now applies to all finished products using this material  

### Workflow: Checking a Product's Allergen Status

**Step 1** — Go to `/dashboard/allergen/product-allergens`  
**Step 2** — Select the product  
**Step 3** — Click **Run Allergen Roll-Up** (system scans BOM and aggregates allergens from all ingredients)  
**Step 4** — Review: which allergens are CONTAINS (deliberate), which are MAY CONTAIN (cross-contamination)  
**Step 5** — Check Label Readiness Score — should be 6/6 or 100%  
**Step 6** — If label text already written, compare to roll-up result  
**Step 7** — Any discrepancy = update label before next production run  

---

## QUICK TRAINING SUMMARY — Allergen & Nutrition

> **What:** Track allergens in every ingredient and automatically calculate finished product allergen profile.  
> **Why critical:** Missing allergen declaration = product recall + potential consumer fatality.  
> **Action required:** Run allergen roll-up every time you change a formula. Check label readiness = 100% before printing labels.

---
