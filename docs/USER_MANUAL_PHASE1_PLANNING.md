# PHASE 1 — PLANNING & PRODUCTION
## FMCG ERP User Manual

---

<a name="mrp"></a>
# MODULE 1: MRP & DEMAND FORECASTING

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Material Requirements Planning (MRP) module calculates what raw materials and packaging you need to buy — and when — based on your production plan, current stock levels, and supplier lead times. Demand Forecasting uses historical sales data to predict future demand.

**Why it exists in FMCG context:**  
FMCG companies produce many product variants with short shelf lives. Running out of SLES (a key detergent ingredient) stops your entire factory. Overstocking perishables wastes money. MRP eliminates both problems by calculating the exact quantities to order at the exact right time.

**Business impact:**  
- Reduces stockouts by 60–80%
- Reduces excess inventory by 20–40%
- Automates purchase request generation
- Links production schedule directly to procurement

---

## 2. USER ROLES

| Role | What they do in this module |
|---|---|
| **Production Planner** | Runs MRP, reviews suggestions, converts to PRs |
| **Procurement Officer** | Receives generated PRs, validates with suppliers |
| **Warehouse Manager** | Provides current stock data for MRP accuracy |
| **Finance Manager** | Reviews cash impact of procurement suggestions |
| **Operations Manager** | Approves large procurement runs |

---

## 3. KEY CONCEPTS

**MRP Run:** A calculation process where the system reads your production plan, subtracts available stock, and outputs a list of materials to order.

**BOM (Bill of Materials):** The recipe for each product — e.g., 1 litre of liquid detergent requires 120g SLES, 40g CAPB, etc.

**Lead Time:** How many days from placing a PO to receiving goods at your warehouse. If SLES takes 5 days, MRP orders it 5 days before it is needed.

**Reorder Point:** The minimum stock level that triggers a reorder suggestion.

**Safety Stock:** Extra buffer stock held to absorb delays or demand spikes.

**Net Requirements:** Gross requirement (what production needs) minus available stock minus stock on order = what you actually need to buy.

**Demand Forecast:** A prediction of future sales based on past 3–12 months of data, seasonality, and trends.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: MRP Dashboard (`/dashboard/mrp`)

**Purpose:** Overview of all MRP runs, open suggestions, and forecasting status.

**Key information displayed:**
- **Active Suggestions:** Number of open procurement suggestions awaiting action
- **Last MRP Run:** Date and time of the most recent MRP calculation
- **Forecast Accuracy:** How close your forecasts were to actual demand (%)
- **Critical Materials:** Materials at or below safety stock level (red)
- **Upcoming Shortages:** Materials projected to run out within 14 days

**Buttons:**
- **Run MRP Now** — triggers a full MRP calculation immediately
- **View Suggestions** — opens the suggestions list
- **View Forecast** — opens demand forecasting view

---

### Screen: MRP Runs (`/dashboard/mrp/run`)

**Purpose:** Create and execute MRP calculations.

**Fields explained:**
| Field | What to enter | Example |
|---|---|---|
| Planning Horizon | How many days ahead to plan | 30, 60, or 90 days |
| Include Safety Stock | Yes/No — include buffer stock in calculations | Yes (recommended) |
| Demand Source | Where sales data comes from | Sales Orders + Forecast |
| Run Date | Leave as Today (system defaults) | 2024-05-02 |

**How to Run MRP:**
1. Click **New MRP Run**
2. Set Planning Horizon (recommended: 30 days for fast-moving items, 60 for imports)
3. Select Demand Source: "Sales Orders + Forecast" (most accurate)
4. Click **Execute Run**
5. System processes for 30–120 seconds depending on product count
6. Results appear in the Suggestions screen

---

### Screen: MRP Suggestions (`/dashboard/mrp/suggestions`)

**Purpose:** Review what the system recommends you purchase.

**Columns explained:**
| Column | Meaning |
|---|---|
| Material | Name of raw material or packaging |
| Required Quantity | How much you need to order |
| Unit | Unit of measure (KG, Litres, Pieces) |
| Current Stock | What you have right now |
| On Order | Already ordered, not yet received |
| Net Need | Required minus available |
| Suggested Order Date | Latest date to place PO to avoid stockout |
| Priority | CRITICAL / HIGH / MEDIUM / LOW |

**Actions per suggestion:**
- **Approve** — converts suggestion to a Purchase Request
- **Reject** — removes suggestion (with reason required)
- **Modify Quantity** — adjust if you want to order more/less
- **Combine** — merge multiple suggestions for same supplier

---

### Screen: Demand Forecasting (`/dashboard/mrp/forecast`)

**Purpose:** View and adjust demand predictions by product/SKU.

**Key sections:**
- **Forecast Chart:** 12-month chart showing historical actual vs. forecast
- **Forecast Accuracy %:** How close past predictions were (aim for >80%)
- **Manual Overrides:** Add planned promotions, seasonal peaks, market events
- **Forecast by Product:** Per-SKU forecast with confidence interval

**When to use manual overrides:**
- You have a confirmed promotional campaign next month
- Rainy season traditionally boosts detergent sales 20%
- A major customer has just placed an unusually large order
- A competitor has exited the market

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow 1: Monthly MRP Run (Standard Procedure)

**Frequency:** Every Monday morning or before weekly procurement meeting  
**Estimated time:** 15–30 minutes

**Step 1 — Verify your stock data is up to date**
- Go to `/dashboard/inventory`
- Confirm no pending stock takes or adjustments
- If warehouse has done a count, ensure it is posted before running MRP

**Step 2 — Verify your production plan is confirmed**
- Go to `/dashboard/mps`
- Confirm production orders for next 30 days are approved
- Unconfirmed orders will give inaccurate MRP results

**Step 3 — Run MRP**
- Navigate to `/dashboard/mrp/run`
- Click **New MRP Run**
- Set: Planning Horizon = 30 days, Demand Source = Sales Orders + Forecast
- Click **Execute Run**
- Wait for completion notification (check top right bell icon)

**Step 4 — Review suggestions**
- Go to `/dashboard/mrp/suggestions`
- Filter by Priority = CRITICAL first
- For each suggestion:
  - Check if quantity makes sense (compare with your production schedule)
  - Check if supplier can deliver by suggested order date
  - Approve, Reject with reason, or Modify

**Step 5 — Convert approved suggestions to PRs**
- Select all approved suggestions
- Click **Convert to Purchase Requests**
- System creates PRs automatically in Procurement module
- Procurement officer receives notification to proceed

**Step 6 — Review forecast if needed**
- Go to `/dashboard/mrp/forecast`
- Review next month prediction for top 10 products by volume
- Add any known events as manual overrides

---

### Workflow 2: Emergency MRP Run (Stockout Alert)

**Situation:** Warehouse alerts you SLES will run out in 3 days.

**Step 1** — Go to `/dashboard/mrp/run`  
**Step 2** — Click **New MRP Run**, set Planning Horizon = 14 days  
**Step 3** — In the **Filter** field, type "SLES" to focus on that material  
**Step 4** — Execute Run  
**Step 5** — Review suggestion — system will flag as CRITICAL  
**Step 6** — Approve immediately and call your procurement team  
**Step 7** — On the suggestion, note "URGENT: Express delivery required" in the notes field  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario A: Rainy Season Demand Spike
**Situation:** Your sales team forecasts 30% higher demand for Floor Cleaner in April due to long rains.

**Action:**
1. Go to Demand Forecasting
2. Find "Floor Cleaner 500ml" in the product list
3. Click **Add Override** for April
4. Enter +30% adjustment
5. Add note: "Long rains promotion — sales team estimate"
6. Run MRP — it will now show larger order quantities for Floor Cleaner ingredients

**Outcome:** You pre-order extra SLES and fragrance before April, avoiding a production stoppage during your peak season.

---

### Scenario B: Supplier Delays — Lead Time Update
**Situation:** Your SLES supplier calls to say they now need 8 days instead of 5 for delivery.

**Action:**
1. Go to `/dashboard/suppliers`
2. Find the SLES supplier
3. Update their Lead Time from 5 to 8 days
4. Re-run MRP
5. All future SLES suggestions will now have earlier order dates

**Outcome:** System now accounts for longer delivery time automatically — no more last-minute scrambles.

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Run MRP every week minimum — more often if production is volatile
- ✅ Always verify stock data before running MRP
- ✅ Add manual overrides for planned promotions and seasonal events
- ✅ Review CRITICAL suggestions on the same day they appear
- ✅ Keep supplier lead times updated in the supplier master

### DON'T:
- ❌ Never approve MRP suggestions blindly without checking current stock
- ❌ Don't run MRP if a large stock count is in progress (you'll get wrong numbers)
- ❌ Don't reject CRITICAL suggestions without escalating to management
- ❌ Don't ignore the Forecast Accuracy % — if it drops below 70%, review your forecast methodology
- ❌ Never manually delete MRP run history — it is needed for audit and forecasting

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "MRP run shows zero requirements" | Production plan is empty or no sales orders in period | Confirm production orders in MPS, check sales order dates |
| "Suggestion quantity seems too high" | Safety stock is set too high in material master | Review material master safety stock settings |
| "Cannot convert to PR — supplier missing" | Material has no preferred supplier assigned | Go to Material master, assign a preferred supplier |
| "Forecast accuracy 0%" | Not enough historical data (less than 3 months) | Wait for more data; use manual forecasts in the meantime |
| "Run takes more than 10 minutes" | Too many active products in planning | Run for specific material groups or reduce planning horizon |

---

## 9. SYSTEM INTEGRATIONS

MRP connects to:
- **Sales Orders** → actual demand data
- **Production Orders / MPS** → production schedule = demand trigger
- **Inventory** → current stock levels
- **Supplier Master** → lead times, preferred suppliers
- **Procurement** → outputs go directly to Purchase Requests
- **Demand Forecasting** → probabilistic future demand

---

## 10. AI USAGE IN MRP

**What AI does:**
- Suggests adjustments to safety stock levels based on demand variability
- Flags unusual demand patterns (sudden spikes/drops)
- Recommends optimal reorder quantities to minimize cost

**How to use AI in MRP:**
1. Go to `/dashboard/procurement-suggestion/ai`
2. Click **Run AI Agents**
3. Review suggestions from DEMAND_RISK_PREDICTOR and COST_OPTIMIZER agents

**What NOT to trust AI for:**
- AI cannot know about a supplier going bankrupt (you must update manually)
- AI forecasts are averages — they miss one-off events like strikes or floods
- Always cross-check AI reorder quantities with your production manager

---

## QUICK TRAINING SUMMARY — MRP & Demand Forecasting

> **What:** Calculates what to buy, when, and how much based on your production plan and stock.  
> **Who:** Production Planner runs it; Procurement Officer acts on results.  
> **How often:** Weekly (minimum). Run immediately after production plan changes.  
> **Key action:** Run MRP → Review suggestions → Approve critical ones → Convert to Purchase Requests.  
> **Golden rule:** Garbage in = garbage out. Clean stock data = accurate MRP.

---

<a name="mps"></a>
# MODULE 2: MASTER PRODUCTION SCHEDULING (MPS)

---

## 1. MODULE OVERVIEW

**What this module does:**  
MPS is your factory's weekly/monthly production calendar. It answers: "When do we produce which products, in what quantities, using which production lines?" MPS translates the sales forecast and customer orders into a realistic, capacity-checked production schedule.

**Why it exists in FMCG context:**  
You cannot produce everything at once. A 5,000-litre mixer cannot simultaneously fill Detergent 1L and Shampoo 500ml. MPS allocates your limited production capacity across all your products to meet demand without overloading the factory.

**Business impact:**  
- Prevents production overloads and bottlenecks
- Ensures right products are available when customers order
- Balances short-term orders vs. long-term forecast
- Direct input to MRP for material procurement

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Production Planner** | Creates and maintains the MPS |
| **Operations Manager** | Approves the weekly MPS |
| **Sales Manager** | Provides confirmed orders and priority customers |
| **Factory Manager** | Provides actual capacity constraints |
| **Quality Manager** | Flags quality holds that affect production |

---

## 3. KEY CONCEPTS

**Master Schedule:** The approved week-by-week plan of what to produce.

**Capacity:** Maximum output per production line per shift per day (e.g., Mixer A can process 5,000 litres per 8-hour shift).

**Campaign:** A continuous production run of the same product (e.g., produce Detergent 1L for 3 days straight to reduce changeover).

**Changeover Time:** Time lost when switching from one product to another (cleaning the mixer, setting up new batch, etc.).

**Frozen Horizon:** The period (typically 1–2 weeks ahead) during which the schedule should not change because materials are already ordered and production has started.

**Available-to-Promise (ATP):** The quantity you can safely promise a customer based on the production schedule minus committed orders.

**What-If Simulation:** Test different scenarios before committing (e.g., "What if I delay Product A by 2 days to fit an urgent order?")

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: MPS Dashboard (`/dashboard/mps`)

**Key metrics displayed:**
- **Schedule Adherence %** — how closely last week's actual production matched the plan
- **Capacity Utilization %** — percentage of factory capacity being used this week
- **Lines at Risk** — production lines overloaded or underloaded (shown as color-coded bars)
- **Upcoming Changeovers** — list of product switches this week with estimated downtime

---

### Screen: Planning Board (`/dashboard/mps/planning-board`)

**Purpose:** Visual Gantt chart — drag-and-drop interface to schedule production.

**How to read the Planning Board:**
- **Rows** = Production lines (Mixer A, Filler Line 1, etc.)
- **Columns** = Days/weeks
- **Colored blocks** = Production runs for specific products
- **Red blocks** = Overloaded (too much planned for that line)
- **Gray gaps** = Downtime (changeovers, maintenance)
- **Blue blocks** = Normal production

**Actions on Planning Board:**
- **Drag a block** to move production to a different day
- **Resize a block** to extend or shorten a production run
- **Click a block** to see details (product, quantity, status)
- **Right-click** to Split, Extend, or Postpone a run

---

### Screen: Capacity Heatmap (`/dashboard/mps/capacity`)

**Purpose:** Shows capacity utilization by production line by day, colored from green (low) to red (overloaded).

**How to use:**
1. Identify red cells (overloaded days)
2. Move production blocks on Planning Board to balance
3. Re-check heatmap until no red cells remain
4. Aim for 75–85% utilization (leave buffer for breakdowns and quality holds)

---

### Screen: What-If Simulator (`/dashboard/mps/whatif`)

**Purpose:** Test schedule changes without committing them.

**How to run a simulation:**
1. Click **New Simulation**
2. Give it a name (e.g., "Delay Shampoo to fit urgent Detergent order")
3. Make changes to the simulated schedule
4. Click **Compare** to see original vs. simulated KPIs
5. If satisfied, click **Apply to Live Schedule**
6. If not, discard the simulation

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Creating Weekly Production Schedule

**Day:** Every Thursday for the following week's production

**Step 1 — Import demand data**
- System auto-populates demand from confirmed sales orders and MRP suggestions
- Review the auto-generated demand in `/dashboard/mps/planning-board`

**Step 2 — Check capacity**
- Go to Capacity Heatmap
- Note which days are overloaded (red)
- Identify which production lines have spare capacity

**Step 3 — Assign production runs**
- On Planning Board, drag product blocks to appropriate lines and days
- Group same-product runs together to minimize changeovers
- Leave 4–8% buffer for unplanned downtime

**Step 4 — Validate with What-If (if needed)**
- If an urgent order forces a change, use What-If Simulator first
- Never move frozen-horizon items without management approval

**Step 5 — Review campaign view**
- Go to `/dashboard/mps/campaigns`
- Verify same products are grouped together
- Changeover matrix will show estimated hours lost to switches

**Step 6 — Get approval**
- Click **Submit for Approval**
- Operations Manager receives notification
- Manager reviews and clicks **Approve**

**Step 7 — Publish schedule**
- Once approved, click **Publish**
- Shop Floor team receives the schedule on their terminals
- Procurement team sees the locked production plan for MRP purposes

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Urgent Order From Key Customer
**Situation:** Your largest customer (Carrefour) calls at 9am with an urgent order for 50,000 bottles of Liquid Detergent 1L, needed in 5 days. Your current schedule has Cream Rinse in that slot.

**Action:**
1. Open What-If Simulator
2. Create new simulation: "Carrefour Urgent Detergent"
3. Move Cream Rinse to next week
4. Place Liquid Detergent in the freed slot
5. Check Capacity Heatmap — is next week overloaded?
6. Check stock of Cream Rinse raw materials — can they wait?
7. Simulate — view impact on other orders
8. Present to Operations Manager for decision
9. If approved, apply to live schedule

**Key check:** Will moving Cream Rinse cause a stockout for any committed Cream Rinse customers?

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Freeze the schedule 1–2 weeks ahead (no changes within frozen period)
- ✅ Group same-product campaigns together to minimize changeovers
- ✅ Keep 15–20% capacity buffer for breakdowns and rework
- ✅ Always run What-If before making urgent schedule changes
- ✅ Update the schedule when production order quantities change

### DON'T:
- ❌ Don't schedule at 100% capacity — breakdowns will cause customer delivery failures
- ❌ Don't accept urgent orders without checking the schedule impact first
- ❌ Don't change the frozen period without management approval
- ❌ Don't ignore the changeover matrix — underestimating changeover causes schedule slippage

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "Capacity heatmap shows 100%+ for Monday" | Too many production orders assigned | Use What-If to redistribute to other days |
| "Schedule adherence showing 40%" | Actual production not matching plan | Investigate: machine downtime? Material shortage? Quality holds? |
| "Cannot approve schedule — open items" | Unresolved conflicts in the plan | Review yellow warning items on planning board |
| "What-If simulation won't apply" | Simulation conflicts with frozen horizon | Get Operations Manager override or accept delay |

---

## QUICK TRAINING SUMMARY — MPS

> **What:** Factory weekly production calendar — who makes what, when, on which line.  
> **Who:** Production Planner creates it; Operations Manager approves it; Shop Floor executes it.  
> **Key screen:** Planning Board (drag-and-drop Gantt chart).  
> **Key rule:** Never plan at 100% capacity. Freeze 1–2 weeks ahead. Use What-If before urgent changes.  
> **Links to:** MRP (materials), Shop Floor (execution), Inventory (stock targets).

---

<a name="planning"></a>
# MODULE 3: ADVANCED PLANNING SUITE

---

## 1. MODULE OVERVIEW

**What this module does:**  
Advanced Planning extends MPS with detailed production scheduling, bottleneck analysis, capacity simulation, and changeover matrix optimization. Where MPS gives a weekly plan, Advanced Planning gives a day-level and hour-level schedule with precise sequencing.

**Why it exists in FMCG context:**  
Multi-product FMCG factories run multiple lines simultaneously, each with different capabilities, speeds, and cleaning requirements. Advanced Planning prevents scheduling conflicts, minimizes changeover waste, and ensures the right operator with the right certification is on the right machine.

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Senior Production Planner** | Uses Advanced Planning for detailed scheduling |
| **Factory Manager** | Reviews bottleneck analysis and capacity reports |
| **Line Supervisors** | Execute plans and report actual vs. plan |
| **Maintenance Team** | Provides machine availability windows |

---

## 3. KEY CONCEPTS

**Schedule Board:** Hour-by-hour production schedule for each line, down to individual batch/lot level.

**Bottleneck:** The production step that limits overall factory throughput. In a 3-stage process (mix → fill → pack), if Filling can only do 1,000 units/hour but Mixing can do 2,000 units/hour, Filling is the bottleneck.

**Bottleneck Explorer:** Tool that identifies which machine or process is currently limiting your factory output.

**Changeover Matrix:** A table showing how long it takes to switch from Product A to Product B on each production line (cleaning + setup time). Some switches take 30 minutes; others (e.g., fragrance to fragrance) take 3 hours.

**Simulation Sandbox:** A safe space to test complex scheduling scenarios before applying to the live plan.

**Capacity Board:** Visual map of all production lines showing booked vs. available time.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Planning Dashboard (`/dashboard/planning`)

Shows:
- **Schedule Board** — current week's hour-by-hour plan
- **Bottleneck Score** — which line is currently the constraining factor
- **Capacity Utilization** — per line, this week
- **Changeover Summary** — total hours lost to changeovers this week

---

### Screen: Schedule Board (`/dashboard/planning/schedule`)

**Purpose:** Detailed production sequencing — add specific batches to specific timeslots.

**How to use:**
1. Lines are displayed as rows
2. Each cell represents 1 hour
3. Click a cell to assign a production batch
4. Color coding: Green = confirmed, Yellow = tentative, Red = conflict
5. Hover over any batch to see: product, quantity, operator, start/end time

---

### Screen: Bottleneck Explorer (`/dashboard/planning/bottlenecks`)

**Purpose:** Find where your factory is constrained.

**Reading the report:**
- Bar chart showing output rate per production stage
- The **shortest bar** is your bottleneck
- Recommendations: "Increase Filling Line 2 speed from 800 to 1,000 units/hr to reduce bottleneck by 25%"

---

### Screen: Changeover Matrix (`/dashboard/planning/changeover`)

**Purpose:** Look up how long it takes to switch between products on each line.

**Example table:**

| From → To | Detergent | Shampoo | Cream | Wipes |
|---|---|---|---|---|
| Detergent | — | 120 min | 180 min | 240 min |
| Shampoo | 90 min | — | 150 min | 200 min |
| Cream | 180 min | 120 min | — | 180 min |

**How to minimize changeovers:**
- Always produce similar-fragrance products in sequence
- Schedule by "cleaning intensity" — light to heavy, not back to light
- Group same-base-formula products together

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Weekly Detailed Scheduling

**Step 1** — Open Schedule Board for next week  
**Step 2** — Import batches from MPS (click **Import from MPS**)  
**Step 3** — Check Changeover Matrix — arrange batch sequence to minimize changeovers  
**Step 4** — Assign specific operators to batches (check certifications)  
**Step 5** — Check Bottleneck Explorer — is any stage showing >90% utilization?  
**Step 6** — Use Simulation Sandbox to test alternative sequences  
**Step 7** — Apply best sequence to live schedule  
**Step 8** — Print/export schedule for Line Supervisors  

---

## QUICK TRAINING SUMMARY — Advanced Planning

> **What:** Hour-level production scheduling with bottleneck identification and changeover optimization.  
> **Who:** Senior Production Planner and Factory Manager.  
> **Key insight:** Use Changeover Matrix to group similar products — saves hours of cleaning time daily.  
> **Best practice:** Always check Bottleneck Explorer after adding urgent orders — it shows if you're over-committing.

---

<a name="bom"></a>
# MODULE 4: BOM & FORMULA MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Bill of Materials (BOM) management defines the exact recipe/formula for every product you manufacture. It records which raw materials, packaging, and intermediates go into each finished product, in what quantities, at what yield.

**Why it exists in FMCG context:**  
An FMCG product like Liquid Detergent 1L has 15–20 ingredients. The BOM ensures:
- Every batch is made consistently (quality)
- Cost is calculated accurately (margin)
- MRP orders the right materials (procurement)
- Production workers follow the correct recipe (compliance)

**Business impact:**  
- Consistent product quality across batches
- Accurate cost of goods sold (COGS) calculation
- Correct material consumption in production
- Regulatory compliance for food/personal care products

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **R&D / Formulation Manager** | Creates and approves BOMs |
| **Quality Manager** | Approves final BOM for production use |
| **Production Planner** | Uses BOMs for production orders |
| **Procurement** | Uses BOMs for material requirements |
| **Finance** | Uses BOMs for standard cost calculation |

---

## 3. KEY CONCEPTS

**Bill of Materials (BOM):** The complete list of ingredients, packaging, and materials needed to produce one unit of a finished product, along with the quantity of each.

**BOM Line:** One row in the BOM — e.g., "SLES 70% — 12% of batch weight"

**Yield:** The percentage of input materials that become finished product. If you put in 100 litres and get 95 litres out, yield = 95%.

**Loss Factor / Waste %:** The opposite of yield. If SLES has 5% loss during processing, the BOM should include 5% extra.

**Component Type:** Ingredient can be:
- **Active ingredient** — functional component
- **Packaging primary** — the bottle/sachet
- **Packaging secondary** — box/carton
- **Subcomponent** — an intermediate mix used in the formula

**BOM Version:** When a formula changes (e.g., switching to a different preservative), a new BOM version is created. Old version is archived.

**BOM Status:** DRAFT → APPROVED → ACTIVE → OBSOLETE

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: BOM Master (`/dashboard/bom`)

**List of all BOMs. Columns:**
| Column | Description |
|---|---|
| Product | The finished product this BOM makes |
| Version | BOM version number (1.0, 1.1, 2.0, etc.) |
| Status | DRAFT / APPROVED / ACTIVE / OBSOLETE |
| Batch Size | How many units this BOM is defined for (e.g., per 1,000 litres) |
| Standard Cost | Calculated cost per unit based on current material prices |
| Last Updated | When the BOM was last changed |

**Buttons:**
- **New BOM** — creates a new BOM from scratch
- **Clone** — copies an existing BOM (useful for variants)
- **Compare Versions** — side-by-side comparison of two BOM versions

---

### Screen: BOM Detail (click any BOM)

**Header section:**
- **Product:** Which finished good this BOM produces
- **Batch Size:** e.g., "1,000 litres" — all quantities are relative to this
- **Yield %:** e.g., 97% — means 3% of material is lost during processing
- **Production Area:** Which part of the factory uses this BOM
- **Standard Cost:** Auto-calculated from material prices

**BOM Lines table:**
| Field | Description | Example |
|---|---|---|
| Material | Raw material or packaging name | "SLES 70%" |
| Component Type | Active / Packaging / Subcomponent | Active |
| Quantity | Amount per batch | 120 KG |
| UoM | Unit of measure | KG |
| Loss % | Waste factor for this ingredient | 2% |
| Net Quantity | Quantity after accounting for loss | 122.4 KG |
| Cost | Current price × quantity | KES 14,688 |
| Required | Is it mandatory? | Yes |

---

### Screen: BOM Version Compare (`/dashboard/bom/compare`)

**Purpose:** See exactly what changed between two BOM versions.

**How to use:**
1. Select BOM product from dropdown
2. Select Version A (old) and Version B (new)
3. Click **Compare**
4. System shows:
   - Lines that are identical (no change)
   - Lines that changed (highlighted yellow)
   - New lines added (highlighted green)
   - Lines removed (highlighted red)
   - Cost impact of changes (in KES per 1,000 units)

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Creating a New Product BOM

**Situation:** R&D has developed a new product — "Antibacterial Handwash 250ml". You need to create its BOM before production can start.

**Step 1** — Get the formulation sheet from R&D (approved by QA)  
**Step 2** — Navigate to `/dashboard/bom`, click **New BOM**  
**Step 3** — Fill header:
- Product: "Antibacterial Handwash 250ml" (select from dropdown)
- Batch Size: 1,000 litres
- Yield %: 96%
- Status: DRAFT

**Step 4** — Add BOM lines one by one:
- Click **Add Line**
- Select Material (must exist in Material Master)
- Enter Quantity per batch
- Enter Loss %
- System auto-calculates Net Quantity

**Step 5** — Add packaging:
- Click **Add Line**
- Select "250ml HDPE Bottle"
- Quantity: 4,000 units (per 1,000 litre batch)
- Component Type: Packaging Primary

**Step 6** — Verify totals:
- Check that ingredient percentages add up to ~100% of liquid batch
- Review standard cost calculation
- Compare to R&D formulation sheet

**Step 7** — Submit for approval:
- Change status to "Submitted for Approval"
- Quality Manager receives notification
- QM reviews, approves or sends back with comments

**Step 8** — Activate:
- Once approved, Quality Manager changes status to ACTIVE
- BOM is now available for production orders

---

### Workflow: Updating an Existing BOM (Formula Change)

**Situation:** Supplier of your current preservative has increased price by 40%. R&D recommends switching to an alternative preservative.

**Step 1** — Open existing BOM for affected product  
**Step 2** — Click **Clone** to create a new version (e.g., v1.1 from v1.0)  
**Step 3** — In the cloned version, find the old preservative line  
**Step 4** — Delete old preservative line; add new preservative with new quantity  
**Step 5** — Run **Cost Impact Analysis** — compare cost per 1,000 units  
**Step 6** — Submit new version for Q&A approval  
**Step 7** — After approval, activate v1.1 and archive v1.0  
**Step 8** — Production team is notified to use new BOM from next production run  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Cost Reduction Initiative
**Situation:** Finance says your margin on Liquid Detergent 1L has dropped to 18%. Target is 25%. You need to reduce COGS by 7%.

**Action:**
1. Open BOM for Liquid Detergent 1L
2. Review each ingredient line — which have the highest cost impact?
3. Use BOM Cost Analysis to rank by cost contribution
4. Identify 2–3 candidates for quantity reduction (coordinate with R&D)
5. Clone BOM, reduce CAPB from 4% to 3% (as R&D suggests)
6. Run cost simulation — does it achieve target?
7. Send revised BOM to QA for approval and consumer testing
8. If approved, activate new version

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always include loss factors for each ingredient (prevents stock discrepancies)
- ✅ Version control every formula change (never overwrite — always clone)
- ✅ Verify BOM standard cost against actual production costs monthly
- ✅ Get QA sign-off before activating any new BOM
- ✅ Keep BOM batch size consistent across all products (e.g., always per 1,000 litres)

### DON'T:
- ❌ Never activate a BOM without QA approval
- ❌ Never delete old BOM versions — archive them for regulatory traceability
- ❌ Don't mix units (some ingredients in litres, others in KG) — be consistent
- ❌ Never change an ACTIVE BOM directly — always clone to a new version first

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "Material not found" when adding BOM line | Material doesn't exist in Material Master | Create material first in Master Data |
| "Cost calculation shows zero" | Material has no price set | Update material purchase price in supplier master |
| "BOM not appearing in production order dropdown" | BOM status is DRAFT, not ACTIVE | Get QA approval and activate BOM |
| "Batch consumption higher than BOM" | Loss factor not set correctly | Review and update loss % for each ingredient |

---

## QUICK TRAINING SUMMARY — BOM & Formula

> **What:** The recipe for every product — materials, quantities, packaging, waste factors.  
> **Who:** R&D creates it, QA approves it, Production uses it.  
> **Key rule:** Never change active BOMs — always clone and create a new version.  
> **Business impact:** Wrong BOM = wrong material consumption = wrong COGS = wrong pricing.

---

<a name="production"></a>
# MODULE 5: PRODUCTION ORDERS / MES

---

## 1. MODULE OVERVIEW

**What this module does:**  
Production Orders (also called Work Orders) are the formal instructions to the factory to produce a specific quantity of a specific product on a specific date. The Manufacturing Execution System (MES) tracks the order from creation through execution to completion.

**Why it exists in FMCG context:**  
Without formal production orders, it is impossible to track: how much you actually produced vs. planned, what materials were consumed, where a batch was produced, which operator made it, and what quality checks were performed. This is essential for food safety, cost tracking, and inventory accuracy.

**Business impact:**  
- Accurate production tracking and reporting
- Automatic material consumption posting
- Quality hold enforcement before goods move to finished goods
- Traceability records for recalls
- Actual vs. standard cost variance analysis

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Production Planner** | Creates and schedules production orders |
| **Factory Supervisor** | Confirms, starts, and closes production orders |
| **Operator** | Executes production and records consumption |
| **Quality Control** | Approves batch before goods receipt to FG |
| **Warehouse** | Receives finished goods to stock |

---

## 3. KEY CONCEPTS

**Production Order Status Flow:**

```
DRAFT → PLANNED → CONFIRMED → IN_PROGRESS → QUALITY_HOLD → COMPLETED → CLOSED
```

- **DRAFT:** Created but not yet confirmed
- **PLANNED:** Confirmed, materials checked, ready to start
- **CONFIRMED:** Materials reserved, on schedule
- **IN_PROGRESS:** Production has started
- **QUALITY_HOLD:** Finished but waiting QC approval
- **COMPLETED:** QC passed, goods receipted to FG stock
- **CLOSED:** Accounting done, variances posted

**Batch/Lot Number:** Every production order creates a unique lot number (e.g., "LOT-2024-05-002-LD1L"). This is the traceability key.

**Planned vs. Actual:** The system tracks planned quantities (from BOM) vs. actual quantities consumed/produced. Variances are reported automatically.

**Material Consumption:** When a production order is completed, the system automatically deducts the BOM-specified ingredients from stock.

**Finished Goods Receipt:** The entry of completed product into the finished goods warehouse.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Production Plans (`/dashboard/production`)

Lists all production orders with status, schedule, and key KPIs.

**Key filters:**
- Filter by status (In Progress, Completed, etc.)
- Filter by production line
- Filter by date range
- Filter by product

**Summary cards at top:**
- Total Active Orders
- Orders Due Today
- Orders Overdue
- On-Time Delivery %

---

### Screen: Production Order Detail (click any order)

**Tabs:**
1. **Overview** — Basic info (product, quantity, dates, status, BOM used)
2. **Materials** — What materials are needed, reserved, and consumed
3. **Operations** — Work steps (mix → fill → pack), times, operators
4. **Quality** — QC inspection results, certificates
5. **Outputs** — Finished goods produced, lot numbers
6. **Costs** — Standard vs. actual material and labor costs
7. **History** — All status changes with timestamps and user names

**Key buttons on detail screen:**
- **Confirm** — Moves from PLANNED to CONFIRMED, reserves materials
- **Start** — Moves to IN_PROGRESS, timestamp recorded
- **Record Output** — Enter actual quantities produced
- **Complete** — Moves to QUALITY_HOLD for QC inspection
- **Close** — Finalizes costs (Finance only)

---

### Screen: New Production Order

**Fields to fill:**
| Field | Description | Example |
|---|---|---|
| Product | What are you producing? | Liquid Detergent 1L |
| Quantity | How many units? | 10,000 units |
| BOM | Which formula version to use | v1.1 (current active) |
| Production Line | Which line/mixer? | Mixer Line A |
| Planned Start | When does production begin? | 2024-05-06 06:00 |
| Planned End | When should it finish? | 2024-05-06 14:00 |
| Priority | Urgency | NORMAL / HIGH / URGENT |

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Full Production Order Cycle

**Step 1 — Create Production Order (Planner)**
- Go to `/dashboard/production`
- Click **New Production Order**
- Fill all fields (Product, Quantity, BOM, Line, Dates)
- Click **Save as Draft**

**Step 2 — Review Materials (Planner)**
- Open the draft order
- Go to **Materials** tab
- Check all materials have sufficient stock (green = available, red = shortage)
- If shortage: raise a procurement request before confirming

**Step 3 — Confirm Order (Planner)**
- Click **Confirm**
- System reserves materials in inventory (they cannot be used for other orders)
- Status changes to CONFIRMED
- Shop Floor team receives notification

**Step 4 — Start Production (Supervisor)**
- On the Shop Floor terminal, find the confirmed order
- Click **Start Production**
- System records start time
- Status changes to IN_PROGRESS
- Batch/Lot number is automatically generated

**Step 5 — Record Material Consumption (Operator)**
- As each ingredient is weighed and added, click **Record Consumption**
- Enter actual quantity used (system shows expected quantity from BOM)
- If actual differs from BOM (e.g., due to spillage): enter variance reason

**Step 6 — Record Output (Operator)**
- When production run is complete, click **Record Output**
- Enter: Quantity produced, any yield loss with reason
- Attach batch/lot numbers from sub-batches if applicable

**Step 7 — Quality Control (QC Team)**
- Status automatically moves to QUALITY_HOLD
- QC Inspector receives notification
- Inspector collects samples and runs tests
- In QC module, enters results against the production order
- If PASS: clicks **Release** — order status moves to COMPLETED
- If FAIL: clicks **Hold** — batch placed in quarantine, Investigation triggered

**Step 8 — Goods Receipt (Warehouse)**
- After QC release, Warehouse receives notification
- In Inventory, records Goods Receipt from Production
- Finished goods added to FG warehouse stock with lot number
- Production order status: COMPLETED

**Step 9 — Close Order (Finance)**
- At month-end, Finance clicks **Close Order**
- System calculates material consumption variance
- Any unused reserved materials are returned to stock
- Cost variance is posted to accounting
- Status: CLOSED

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Production Order Partially Completed
**Situation:** You planned to produce 10,000 units of Shampoo 500ml but a machine breakdown stopped production at 7,000 units.

**Action:**
1. Record output: 7,000 units (partial quantity)
2. Click **Partial Completion** in Record Output screen
3. Enter reason: "Machine breakdown on Filler 2"
4. Raise maintenance work order from the production order (link to Maintenance module)
5. Create new production order for remaining 3,000 units when machine is repaired
6. Link new order to original (system tracks split)

---

### Scenario: QC Fails Batch
**Situation:** Lab results show SLES concentration is below spec in a batch of Floor Cleaner 1L.

**Action:**
1. QC Inspector marks batch as FAIL in QC module
2. Status changes to QUALITY_HOLD
3. Batch is physically moved to Quarantine area
4. QC Manager raises Corrective Action (CAPA) in QMS module
5. Investigation: Was it wrong SLES lot? Weighing error? Calibration issue?
6. If rework is possible: create new Rework Production Order
7. If disposal needed: write off stock with QC Manager approval
8. Root cause noted in CAPA report

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always check material availability before confirming an order
- ✅ Record actual consumption in real time (not the next day)
- ✅ Create a lot number for every production order — traceability requirement
- ✅ Never skip QC release before moving goods to Finished Goods stock
- ✅ Close orders within 5 working days of completion (for accurate month-end costing)

### DON'T:
- ❌ Don't start production without a confirmed order
- ❌ Don't skip recording material consumption variances (they destroy cost accuracy)
- ❌ Never move goods from QUALITY_HOLD without QC sign-off
- ❌ Don't close orders without Finance review of variances

---

## QUICK TRAINING SUMMARY — Production Orders / MES

> **What:** Formal instructions to produce a product, with full tracking from start to close.  
> **Status flow:** Draft → Planned → Confirmed → In Progress → Quality Hold → Completed → Closed.  
> **Key rule:** QC must release every batch before it enters Finished Goods stock.  
> **Best practice:** Record actual consumption in real time — don't do it the next day.

---

<a name="shopfloor"></a>
# MODULE 6: SHOP FLOOR EXECUTION

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Shop Floor module provides the factory floor interface for operators and supervisors. It is designed to be used on tablets and large touchscreen terminals on the production floor. It shows live production status, queue of orders, downtime tracking, and shift handover.

**Why it exists in FMCG context:**  
Paper-based production recording in FMCG creates errors, delays, and traceability gaps. A digital shop floor system captures real-time data directly from where production happens — batch records, consumption, downtime events, and quality issues — the moment they occur.

---

## 2. USER ROLES

| Role | Screen used |
|---|---|
| **Line Operator** | Operator Terminal |
| **Line Supervisor** | Supervisor Console |
| **Production Planner** | Queue Board (view only) |
| **Maintenance** | Downtime Board |

---

## 3. KEY CONCEPTS

**Operator Terminal:** Simplified touchscreen interface for operators — shows their assigned order, required materials, quantities, and buttons to start/stop/complete.

**Supervisor Console:** Full-view dashboard showing all lines, all operators, live production rates, and alerts.

**Downtime Board:** Record when a machine stopped, why, and for how long (planned vs. unplanned).

**Queue Board:** List of all confirmed production orders waiting to be started, in priority order.

**Shift Handover:** Formal handover record — what was completed in the outgoing shift, what the incoming shift must continue.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Operator Terminal (`/dashboard/shop-floor/terminal`)

**Designed for touchscreen use on the production floor.**

**Display:**
- Current order assigned to this terminal
- Product name and photo
- Target quantity for this shift
- Actual quantity produced so far (real-time counter)
- Materials to consume (checklist with checkboxes)
- Large buttons: **START**, **PAUSE**, **RECORD OUTPUT**, **REPORT ISSUE**

**How an operator uses this:**
1. Clock in at start of shift
2. See their assigned production order
3. Press **START** when production begins
4. Check off materials as they are added (system confirms against BOM)
5. Enter output quantities periodically
6. Press **REPORT ISSUE** if machine breaks down or material quality problem
7. At end of shift, press **RECORD HANDOVER**

---

### Screen: Supervisor Console (`/dashboard/shop-floor/supervisor`)

**Shows all active lines on one screen:**
- Line status: Running / Paused / Down / Idle
- Current product per line
- Output rate (units/hour) vs. target
- Operator names per line
- Active alerts (red badges for issues)
- OEE (Overall Equipment Effectiveness) per line, updated every 5 minutes

**Key supervisor actions:**
- **Reassign Operator** — move operator to another line
- **Approve Downtime Reason** — confirm an operator's downtime report
- **Escalate Issue** — send alert to maintenance team
- **Override Pause** — manually resume a paused line

---

### Screen: Downtime Board (`/dashboard/shop-floor/downtime`)

**Records every production stoppage.**

**When a machine stops:**
1. Operator presses **REPORT ISSUE** on terminal
2. Selects downtime category from list:
   - Machine breakdown
   - Planned maintenance
   - Material shortage
   - Quality hold
   - Changeover
   - Power outage
3. Supervisor receives notification
4. Maintenance team also notified if category = Machine Breakdown
5. When machine restarts: Operator presses **RESUME** and enters actual downtime duration

**Downtime report shows:**
- Total downtime this shift
- Downtime by category (breakdown, changeover, shortage)
- OEE impact (how much production was lost)
- MTTR (Mean Time To Repair) trend

---

### Screen: Shift Handover (`/dashboard/shop-floor/handover`)

**At end of each shift, supervisor completes:**
- Orders completed this shift (quantity, lot numbers)
- Orders in progress (status, how much remaining)
- Machines with issues (describe problem for next shift)
- Materials that are running low
- Quality holds — batches in quarantine
- Priority orders for next shift

**Incoming supervisor reviews and acknowledges.**

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Starting a Production Run

**Step 1** — Supervisor assigns order to line via Supervisor Console  
**Step 2** — Operator sees new order on their terminal  
**Step 3** — Operator confirms materials are available (visual check against terminal checklist)  
**Step 4** — Operator presses **START** — system records exact start time  
**Step 5** — Operator adds materials, checks off each one on terminal  
**Step 6** — Machine runs; operator monitors rate and records output every 2 hours  
**Step 7** — At end of run: operator presses **COMPLETE**  
**Step 8** — System prompts: enter final output quantity, confirm lot number, note any issues  
**Step 9** — If output quantity differs from planned: enter variance reason  
**Step 10** — System triggers QC notification for batch inspection  

---

## QUICK TRAINING SUMMARY — Shop Floor

> **What:** Real-time production tracking interface for operators and supervisors.  
> **Key screens:** Operator Terminal (simple), Supervisor Console (full view), Downtime Board.  
> **Golden rule:** Record everything in real time — downtime, output, material consumption.  
> **Why it matters:** Real-time shop floor data = accurate OEE, cost tracking, and traceability.

---

<a name="materialflow"></a>
# MODULE 7: MATERIAL FLOW ENGINE

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Material Flow Engine manages all physical movements of materials within the factory — from the raw material warehouse into production, through work-in-progress stages, to finished goods. It provides a detailed audit trail of every material movement.

**Why it exists in FMCG context:**  
Materials move constantly in a factory: raw materials are issued to production, intermediate mixes move between tanks, packaging components are staged at filling lines, and finished goods move to the warehouse. Without systematic tracking, stock becomes inaccurate and batch traceability breaks down.

---

## 3. KEY CONCEPTS

**Issue to Production:** Moving raw materials from warehouse to production floor — reduces RM stock, creates WIP.

**WIP (Work-in-Progress):** Materials that have been issued to production but not yet completed as finished goods. They sit in mixing tanks, intermediate storage, etc.

**Reservation:** A commitment that specific materials are set aside for a specific production order — no one else can use them.

**Tank Occupancy:** Track which product/batch is currently in each mixing tank.

**FG Receipt:** The formal receipt of completed products into finished goods inventory.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Issuing Materials to Production

**Step 1** — Go to `/dashboard/material-flow/issue`  
**Step 2** — Select the Production Order  
**Step 3** — System shows the BOM — all required materials pre-populated  
**Step 4** — Warehouse team picks materials from shelves  
**Step 5** — For each material: enter actual quantity picked, scan lot number barcode  
**Step 6** — Click **Confirm Issue**  
**Step 7** — System: deducts from RM stock, adds to WIP, records lot numbers used  
**Step 8** — Print picking list as confirmation  

**Critical:** Always scan the lot number — this creates the traceability link between raw material lot and the finished batch.

---

### Workflow: Recording Finished Goods Receipt

**Step 1** — QC has released the batch (QUALITY_HOLD → COMPLETED in Production Order)  
**Step 2** — Go to `/dashboard/material-flow/fg-receipt`  
**Step 3** — Select the completed Production Order  
**Step 4** — Confirm: Quantity completed, lot number, date of production  
**Step 5** — Select: Destination warehouse location (e.g., "FG Rack A3")  
**Step 6** — Click **Post FG Receipt**  
**Step 7** — System: adds to FG inventory, closes WIP for this order  

---

## QUICK TRAINING SUMMARY — Material Flow

> **What:** Track every material movement — issue, WIP, transfer, FG receipt.  
> **Key action:** Always scan lot numbers when issuing to production — it's the traceability foundation.  
> **Links to:** Production Orders (source), Inventory (stock impact), Traceability (lot tracking).

---

<a name="machineops"></a>
# MODULE 8: MACHINE & OPERATOR INTELLIGENCE

---

## 1. MODULE OVERVIEW

**What this module does:**  
Machine + Operator Intelligence tracks the performance of every production machine and every operator. It records runtime, downtime, OEE (Overall Equipment Effectiveness), operator certifications, and cost contribution per machine/operator.

**Why it exists in FMCG context:**  
In a factory producing 100,000+ units per day, knowing that Mixer A is performing at 72% efficiency while Mixer B is at 91% — and that Operator John Mwangi on Filler 3 produces 15% fewer units per hour than average — allows you to make targeted improvements that increase output and reduce cost.

---

## 3. KEY CONCEPTS

**OEE (Overall Equipment Effectiveness):** The single most important manufacturing KPI. OEE = Availability × Performance × Quality. World-class OEE = 85%. If your OEE is 60%, you have significant improvement potential.

**MTBF (Mean Time Between Failures):** Average time between breakdowns. Higher = more reliable machine.

**MTTR (Mean Time To Repair):** Average time to fix a breakdown. Lower = faster maintenance response.

**Operator Certification:** Each operator must hold certifications for the machines they operate. System blocks an uncertified operator from being assigned to a machine.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: MO Dashboard (`/dashboard/machine-ops`)

- OEE by machine (gauge charts, color-coded)
- Top 5 downtime reasons this month
- Operator performance ranking (units/hour)
- Certification expiry alerts (operators with expiring certs highlighted)
- Machine health score trend

### Screen: Machine Master (`/dashboard/machine-ops/machines`)

For each machine:
- Machine name and ID
- Production line assignment
- Rated capacity (units/hour)
- Current OEE %
- Last maintenance date
- Next scheduled maintenance

### Screen: OEE / Performance (`/dashboard/machine-ops/performance`)

Detailed OEE breakdown:
- **Availability:** Machine was running vs. available time
- **Performance:** Actual speed vs. rated speed
- **Quality:** Good units vs. total produced
- Trend charts: last 30 days
- Comparison: this machine vs. fleet average

### Screen: Cert Monitor (`/dashboard/machine-ops/certs`)

- List of all operators and their certifications
- Expiry dates (red = expired, orange = expiring in 30 days)
- One-click email reminder to operator and HR

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Investigating Low OEE

**Situation:** Machine OEE dropped from 78% to 59% this week.

**Step 1** — Open OEE Performance screen for the machine  
**Step 2** — Check OEE breakdown: which component dropped? (Availability, Performance, or Quality?)  
**Step 3** — If Availability: check Downtime Board — what caused stoppages?  
**Step 4** — If Performance: check actual vs. rated speed — tool wear? Operator skill?  
**Step 5** — If Quality: check QC records — more rejects this week?  
**Step 6** — Link to Maintenance module if machine breakdown is the cause  
**Step 7** — Schedule corrective action and monitor OEE next week  

---

## QUICK TRAINING SUMMARY — Machine & Operator Intelligence

> **What:** Performance tracking for every machine and operator — OEE, downtime, certifications.  
> **Key metric:** OEE. Target 85%+. Below 70% = investigate immediately.  
> **Best practice:** Review OEE weekly. Check cert expiry monthly.

---
