# PHASE 7 — EXTENDED FMCG MODULES
## FMCG ERP User Manual

---

<a name="fleet"></a>
# MODULE 47: FLEET MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Fleet Management tracks every company vehicle — trucks, vans, motorcycles — including trips, fuel consumption, maintenance schedules, incident reporting, and driver assignments. It provides complete visibility into fleet cost, utilization, and safety.

**Why it exists in FMCG context:**  
A delivery fleet is both a major cost center and a critical operational asset. Untracked fuel consumption is a fraud risk. Missed maintenance leads to breakdowns during delivery. Unrecorded incidents create insurance liabilities. Fleet Management gives total control over one of FMCG's largest variable costs.

**Business impact:**  
- Reduces fuel fraud through per-trip consumption tracking
- Reduces breakdown incidents through preventive maintenance scheduling
- Provides cost-per-km data for delivery pricing decisions
- Incident documentation protects against fraudulent insurance claims

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Fleet Manager** | Overall fleet oversight, maintenance scheduling |
| **Driver** | Records trips, reports fuel, files incidents |
| **Dispatch Team** | Assigns vehicles to delivery runs |
| **Finance** | Reviews fleet costs, fuel expenses |
| **Maintenance Team** | Executes scheduled maintenance |

---

## 3. KEY CONCEPTS

**Vehicle Status:**
- AVAILABLE — ready for assignment
- ON_TRIP — currently in use
- MAINTENANCE — undergoing service
- GROUNDED — taken off road (serious defect or investigation)
- RETIRED — decommissioned

**Driver Status:** ACTIVE / ON_LEAVE / SUSPENDED

**Trip:** A recorded journey from departure point to destination (and back). Each trip logs: distance, duration, driver, purpose, cargo.

**Fuel Log:** Record of every fuel fill-up: litres, cost, odometer reading. Enables calculation of fuel efficiency (km/litre).

**Maintenance Schedule:** Planned service intervals (e.g., oil change every 5,000 km, major service every 25,000 km).

**Incident:** Any accident, near-miss, theft, or damage event.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Fleet Dashboard (`/dashboard/fleet`)

**Key metrics:**
- Vehicles available now
- Vehicles on active trips
- Vehicles in maintenance
- Overdue maintenance alerts (red)
- Total fleet km this month
- Total fuel cost this month
- Average fuel efficiency (km/litre) vs. benchmark

### Screen: Vehicles (`/dashboard/fleet/vehicles`)

**Per vehicle record:**
- Registration number
- Make, Model, Year
- Capacity (tonnes/m³)
- Assigned driver (primary)
- Current status
- Last odometer reading
- Next service due (date or km, whichever is earlier)
- Insurance expiry date

### Screen: Trips (`/dashboard/fleet/trips`)

**Columns:**
| Column | Description |
|---|---|
| Vehicle | Registration number |
| Driver | Who drove |
| Purpose | Delivery / Sales / Admin / Maintenance |
| Departure | From location |
| Destination | To location |
| Start Time | When trip began |
| End Time | When returned |
| Distance | Km driven |
| Cargo | What was loaded (links to delivery order if applicable) |
| Status | PLANNED / IN_PROGRESS / COMPLETED |

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Managing a Delivery Trip

**Step 1 — Pre-trip inspection (Driver)**
- Driver opens Fleet app on phone
- Selects their vehicle for today
- Completes pre-trip checklist:
  - Tyre condition (check pressure)
  - Lights (front, rear, indicators)
  - Engine oil level
  - Fuel level
  - Any damage or defects from previous day?
- Submits pre-trip check — any flagged issues send alert to Fleet Manager

**Step 2 — Trip start**
- Driver clicks **Start Trip**
- Enters: odometer reading at departure
- Selects: trip purpose (Delivery), linked delivery orders
- System records exact start time

**Step 3 — During trip**
- If fuel stop: driver records fuel log entry
  - Litres purchased, amount paid (KES), new odometer reading, station name
  - Fuel log prevents drivers claiming fuel for personal vehicles

**Step 4 — Trip end**
- Driver clicks **End Trip**
- Enters: odometer reading on return
- System calculates: distance driven, duration, fuel efficiency
- Any incidents: click **Report Incident** (see below)

**Step 5 — Reconcile deliveries**
- Fleet Manager reviews trip
- Confirms: all listed delivery orders were executed
- Any undelivered orders: reason required (customer absent, product quality issue, etc.)

---

### Workflow: Preventive Maintenance Scheduling

**Step 1 — Set maintenance schedule (done once per vehicle)**
- Go to Vehicle record
- Click **Maintenance Schedule**
- Add service types:
  - Oil change: every 5,000 km
  - Full service: every 25,000 km
  - Tyre rotation: every 10,000 km
  - Insurance renewal: annually

**Step 2 — System auto-alerts**
- When vehicle approaches service due point (e.g., 500 km before service):
  - Fleet Manager receives notification
  - Vehicle shows "SERVICE DUE SOON" warning on dashboard

**Step 3 — Schedule maintenance**
- Go to `/dashboard/fleet/maintenance`
- Click **Schedule Service** for the vehicle
- Enter: service date, type, mechanic/workshop
- Vehicle status set to MAINTENANCE on that date

**Step 4 — Record service completion**
- After service: mechanic records work done
- Enters: parts replaced, labor hours, cost
- Updates odometer reading
- Next service due is automatically calculated from current reading

---

### Workflow: Recording an Incident

**Step 1** — Incident occurs (accident, damage, theft)  
**Step 2** — Driver immediately reports: call Fleet Manager AND record in system  
**Step 3** — Go to `/dashboard/fleet/incidents`  
**Step 4** — Click **New Incident**  
**Step 5** — Enter:
   - Vehicle registration
   - Driver
   - Date and time
   - Location
   - Incident type (Accident, Theft, Vandalism, Near-Miss)
   - Description of what happened
   - Photos (upload multiple)
   - Third parties involved (other vehicle registration, police OB number)
   - Estimated damage  
**Step 6** — Submit — Fleet Manager and Insurance team notified immediately  
**Step 7** — Follow-up: police report number, insurance claim number, repair status  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Excessive Fuel Consumption Detected
**Situation:** Fleet report shows Van KCB 123G is consuming 30% more fuel than similar vans on same routes.

**Investigation:**
1. Go to Fleet Dashboard → filter by Vehicle KCB 123G
2. Review Fuel Logs for last month: fill-up frequency, amounts, stations
3. Check Trips: actual distances match expected routes?
4. Check Maintenance: last tyre check? Last engine service?
5. Compare with GPS logs (if available)

**Possible findings:**
- Driver filling up at personal vehicle alongside company van (fraud) → disciplinary action
- Tyres under-inflated (increases consumption) → maintenance required
- Engine needs service (fuel injection issue) → schedule workshop visit
- Route deviation (driver taking detours) → GPS tracking needed

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Complete pre-trip inspection every day before departure
- ✅ Record fuel log immediately at the station — not later
- ✅ Report incidents within 1 hour, regardless of severity
- ✅ Schedule preventive maintenance before the due point — not after breakdown

### DON'T:
- ❌ Never fill company vehicle at an unmanned station (no receipt = no reimbursement)
- ❌ Don't use company vehicle for personal trips without authorization
- ❌ Never delay incident reporting — insurance claims require prompt notification
- ❌ Don't continue driving with a known defect — ground the vehicle and report

---

## QUICK TRAINING SUMMARY — Fleet Management

> **What:** Track vehicles, drivers, trips, fuel, maintenance, and incidents.  
> **Key daily actions:** Pre-trip check → Record trip → Log fuel → End trip.  
> **Fraud prevention:** Fuel logs per trip. Odometer readings at each fill-up.  
> **Maintenance:** System alerts before service is due. Never let alerts go unactioned.

---

<a name="cycle-count"></a>
# MODULE 48: CYCLE COUNTING

---

## 1. MODULE OVERVIEW

**What this module does:**  
Cycle Counting is a systematic, ongoing stock verification method where a portion of the inventory is counted every week rather than a disruptive full annual stocktake. The ABC classification prioritizes which items to count most frequently.

**Why it exists in FMCG context:**  
Annual stocktakes stop the factory for 1–2 days. Cycle counting spreads the work throughout the year, maintaining continuous inventory accuracy without operational disruption. High-value materials (A-class) are counted monthly; low-value, slow-moving items (C-class) annually.

---

## 3. KEY CONCEPTS

**ABC Classification:**
- **A-Class:** High value, high movement. Counted monthly. Typically top 20% of items = 80% of value.
- **B-Class:** Medium value. Counted quarterly.
- **C-Class:** Low value, slow movement. Counted annually.

**Count Plan:** The schedule of which items to count in which period.

**Count Task:** Individual assignment to count specific items in specific locations.

**Count Entry:** The actual physical count recorded by the warehouse team.

**Variance:** Difference between system quantity and physical count.

**Variance Approval Threshold:** Variances above a certain value require management approval before system is adjusted.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Creating and Executing a Cycle Count

**Step 1 — Generate ABC Classification (monthly)**
- Go to `/dashboard/cycle-count/plans`
- Click **Run ABC Classification**
- System ranks all materials/products by value × velocity
- Assigns each item to A, B, or C class

**Step 2 — Create Count Plan**
- Click **New Count Plan**
- Name: "Week 20 - A-Class Raw Materials"
- Select: items to count (filter by Class A, Raw Materials)
- Assign to: Warehouse Team A
- Schedule: 23-May-2024 (Thursday morning, before production starts)

**Step 3 — Conduct the count**
- Warehouse team goes to physical locations
- Opens their Count Tasks in system
- For each item: enter physical quantity found in that location
- Record lot numbers being counted
- Note any damaged, expired, or unlabeled items

**Step 4 — Review variances**
- Go to `/dashboard/cycle-count/variances`
- System compares count entries vs. system quantities
- Items with zero variance: green — no action
- Items with small variance within tolerance: yellow — review and post
- Items with large variance above approval threshold: red — requires Warehouse Manager investigation

**Step 5 — Investigate large variances**
For each red item:
1. Recount physically (was it a counting error?)
2. Check recent stock movements (any unposted receipts or issues?)
3. Check if the item was moved to another location without system update
4. If genuine loss: document reason (theft, damage, evaporation, spillage)
5. Get Warehouse Manager approval for adjustment above KES 10,000

**Step 6 — Post adjustments**
- Once approved: click **Post Adjustments**
- System stock updated to physical count
- Finance notified of inventory value impact
- Audit trail: who counted, who approved, variance amount and reason

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Count A-class items every month — this is where the value is
- ✅ Count in the morning before production starts — reduces movement during count
- ✅ Have two people count independently for high-value items
- ✅ Investigate all large variances — they indicate a problem in your processes

### DON'T:
- ❌ Never adjust stock without recording a reason
- ❌ Don't adjust large variances without Warehouse Manager approval
- ❌ Never count items while they are being moved or processed — you'll get wrong numbers

---

## QUICK TRAINING SUMMARY — Cycle Counting

> **What:** Rolling, partial inventory counts to maintain accuracy without full stocktake disruption.  
> **ABC rule:** A-class = monthly. B-class = quarterly. C-class = annually.  
> **Variance action:** Small = post after review. Large = investigate → approve → post.  
> **Best practice:** Count A-class materials early morning before production. Accuracy requires no movement during count.

---

<a name="putaway"></a>
# MODULE 49: PUTAWAY RULES

---

## 1. MODULE OVERVIEW

**What this module does:**  
Putaway Rules define where new stock should be placed when it arrives in the warehouse. Instead of warehouse staff deciding arbitrarily where to put items, the system guides them to the optimal location based on product characteristics, zone rules, and current occupancy.

**Why it exists in FMCG context:**  
A poorly organized warehouse increases picking time by 40–60%. Correct putaway means: fast-moving items near dispatch, cold items in cold stores, heavy items on bottom shelves, hazardous materials isolated. FEFO also requires organized lot placement so older stock is always accessible first.

---

## 3. KEY CONCEPTS

**Putaway Rule Types:**
- **Fixed Location:** Product X always goes to Location B3 (consistent, easy for staff)
- **Zone-Based:** Raw materials → Zone A; FG → Zone B; Returns → Zone C
- **FEFO-Optimized:** New delivery goes to back; older stock stays near front
- **ABC-Based:** A-class items placed nearest to dispatch for fast picking

**Putaway Task:** A system-generated instruction: "Move Product X (Lot Y, Qty Z) from Receiving Dock to Location A3B2."

**Location Capacity:** Each storage location has a maximum capacity. System won't direct to full locations.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Receiving and Putting Away a Delivery

**Step 1 — Goods arrive at dock**
- Standard Goods Receipt in Inventory module
- GRN posted — goods enter "Receiving" zone initially

**Step 2 — System generates putaway task**
- Based on product type and applicable putaway rule
- "Putaway Task PT-2024-089: SLES 70%, 500 KG, Lot SLES-2024-003 → Location RM-A3-B2 (Raw Material Zone A, Rack 3, Bay 2)"

**Step 3 — Forklift/warehouse team executes**
- Open Putaway Task on mobile device or printed task sheet
- Move goods to designated location
- Scan confirmation: scan product barcode, scan location barcode
- Click **Confirm Putaway**

**Step 4 — System updates**
- Stock now shows correct location
- Location capacity updated
- If FEFO-optimized: system ensures older stock is in the front position

---

## QUICK TRAINING SUMMARY — Putaway Rules

> **What:** System-guided stock placement in the warehouse — right product to right location automatically.  
> **Why:** Organized putaway = fast picking = fewer errors = FEFO compliance.  
> **Key rule:** Never override a putaway instruction without checking with Warehouse Manager.  
> **Result:** Consistent warehouse organization, reduced picking time, correct FEFO positioning.

---

<a name="secondary-sales"></a>
# MODULE 50: SECONDARY SALES / DISTRIBUTOR SELL-THROUGH

---

## 1. MODULE OVERVIEW

**What this module does:**  
Secondary Sales tracks what distributors are selling to their customers (retailers, kiosks, hotels). This is also called "sell-through" or "offtake." While your primary sales are to distributors, secondary sales data shows whether your products are actually moving off distributor shelves — or sitting there.

**Why it exists in FMCG context:**  
Selling to a distributor is a primary sale. But if the distributor can't sell to their customers, they won't reorder from you. Tracking secondary sales tells you: which markets are active, which product formats sell best by region, whether promotional activities drove actual consumer purchases, and which distributors are overstocked vs. underserved.

---

## 3. KEY CONCEPTS

**Primary Sale:** Your company sells to Distributor A — 1,000 cases. This is recorded in your Sales Orders module.

**Secondary Sale (Sell-Through):** Distributor A sells to 50 retailers in their area — 1,000 cases. This is secondary sales data.

**Distributor Inventory Snapshot:** A point-in-time record of what stock each distributor currently holds. Enables calculation of their pipeline fill and offtake rate.

**Sell-Through Rate:** Secondary sales ÷ primary sales. If a distributor buys 1,000 cases from you but only sells 700 to retailers, their sell-through rate is 70%. Below 80% suggests they may be overstocked or having sales challenges.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Uploading Distributor Sell-Through Data

**Two ways to upload secondary sales:**

**Method A — CSV Upload**
1. Distribute a standard CSV template to each distributor (monthly)
2. Distributors fill: product name/SKU, quantity sold, customer type, date range
3. Go to `/dashboard/secondary-sales/upload`
4. Select distributor, upload their CSV
5. System validates data (checks SKU codes, dates, quantities)
6. Confirms upload → data is now in the system

**Method B — Manual Entry**
1. Go to `/dashboard/secondary-sales/upload`
2. Select: Manual Entry
3. Select distributor
4. Enter date range
5. For each product: enter quantity sold

### Workflow: Analyzing Sell-Through Performance

**Step 1** — Go to `/dashboard/secondary-sales/analysis`  
**Step 2** — Filter by: Distributor, Region, Product, Date Range  
**Step 3** — View:
   - Total primary sales to distributor
   - Total secondary sales (offtake from distributor)
   - Sell-through rate (%)
   - Estimated current stock at distributor
   - Days cover at current offtake rate  
**Step 4** — Identify distributors with sell-through below 75% — these need attention  
**Step 5** — Options:
   - Visit distributor to understand challenges
   - Provide trade promotion support
   - Reduce next order until current stock sells down  

---

## QUICK TRAINING SUMMARY — Secondary Sales

> **What:** Track what distributors sell to their customers (offtake/sell-through data).  
> **Why critical:** High primary sales to distributors ≠ products moving to consumers. Sell-through tells the real story.  
> **Target:** Sell-through rate above 80% monthly.  
> **Action:** Distributors below 70% sell-through need support visit or reduced next order.

---

<a name="esg"></a>
# MODULE 51: ESG & SUSTAINABILITY REPORTING

---

## 1. MODULE OVERVIEW

**What this module does:**  
The ESG (Environmental, Social, Governance) module tracks the company's environmental impact — greenhouse gas emissions (Scope 1, 2, and 3), energy consumption, water usage, waste generation, and sustainability targets. It generates reports aligned with GHG Protocol, DEFRA, and IPCC standards.

**Why it exists in FMCG context:**  
Multinational retailers (Unilever, Diageo, Carrefour) increasingly require their suppliers to disclose ESG data. Export markets (EU, UK) are introducing mandatory sustainability disclosure. Kenya's listed companies and large businesses face growing stakeholder pressure for environmental transparency. ESG reporting is moving from "nice to have" to "must have" for competitive FMCG players.

**Business impact:**  
- Enables reporting to retailers requiring supplier ESG data
- Identifies highest-carbon activities for reduction programs
- Tracks progress toward sustainability targets
- Prepares for mandatory ESG disclosure requirements
- Potential for green financing at better rates

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Sustainability Manager** | Owns ESG program, enters data, produces reports |
| **Operations Manager** | Provides utility and production data |
| **Finance Manager** | Reviews financial impact of sustainability initiatives |
| **CEO / Board** | Reviews ESG dashboard, approves targets |

---

## 3. KEY CONCEPTS

**Emission Scopes:**
- **Scope 1 (Direct):** Emissions your company directly produces — factory boilers, company vehicles, generators.
- **Scope 2 (Indirect Energy):** Emissions from electricity you buy — from KPLC or the national grid.
- **Scope 3 (Value Chain):** Emissions from your supply chain and customers — your suppliers' factories, employee commuting, product use and disposal.

**GHG (Greenhouse Gases):** The gases causing climate change — primarily CO₂, methane (CH₄), and nitrous oxide (N₂O). All converted to CO₂ equivalent (kgCO₂e) for comparison.

**Emission Factor:** How much CO₂ equivalent is produced per unit of activity. Example: 1 kWh of electricity from KPLC grid = 0.432 kgCO₂e (Kenya grid emission factor).

**Carbon Intensity:** Total emissions ÷ production volume (e.g., kgCO₂e per tonne of product produced). A key metric for comparing environmental performance over time.

**ESG Target:** A formal commitment for improvement (e.g., "Reduce Scope 1 emissions by 30% by 2030 vs. 2022 baseline").

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: ESG Dashboard (`/dashboard/esg`)

**Key metrics displayed:**
| Metric | Description |
|---|---|
| Scope 1 Emissions (kgCO₂e) | Direct factory emissions |
| Scope 2 Emissions (kgCO₂e) | Electricity-related emissions |
| Total Carbon Footprint | Scope 1 + 2 total |
| Carbon Intensity (per tonne) | kgCO₂e per tonne of product |
| Water Consumption | Total m³ per period |
| Renewable Energy % | % of energy from solar or other renewables |
| Target Progress | % progress toward each ESG target |

**Charts:**
- Scope 1 vs. Scope 2 breakdown (donut chart)
- Emissions trend last 12 months (line chart)
- By source type (bar chart)

### Screen: Activity Data (`/dashboard/esg/activities`)

**Records ESG-relevant activities. Common examples:**
| Activity Source | Type | Unit | Measurement |
|---|---|---|---|
| KPLC Electricity | Scope 2 | kWh | From utility bill |
| Diesel generator | Scope 1 | Litres | From fuel log |
| LPG for boiler | Scope 1 | KG | From consumption records |
| Company vehicles | Scope 1 | Litres | From fleet fuel logs |
| Business air travel | Scope 3 | km | From travel records |

### Screen: Emission Factors (`/dashboard/esg/factors`)

**Library of emission factors for each activity source:**
- KPLC Kenya grid: 0.432 kgCO₂e/kWh (default seeded)
- Diesel: 2.68 kgCO₂e/litre (DEFRA factor)
- LPG: 1.55 kgCO₂e/litre
- Petrol: 2.31 kgCO₂e/litre

**Note:** Update KPLC grid factor annually — Kenya's renewable energy mix changes.

### Screen: ESG Targets (`/dashboard/esg/targets`)

**Set and track sustainability commitments:**

**Example targets:**
| Target | Baseline | Current | Target | Deadline |
|---|---|---|---|---|
| Reduce Scope 1 emissions | 450 tonnes CO₂e (2022) | 380 tonnes | 315 tonnes (-30%) | Dec 2030 |
| 50% renewable electricity | 15% (2022) | 28% | 50% | Dec 2027 |
| Reduce water intensity | 8.5 m³/tonne | 7.2 m³/tonne | 5.0 m³/tonne | Dec 2028 |

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Monthly ESG Data Collection

**Frequency:** Monthly. Collate data within 2 weeks of month-end.

**Step 1 — Collect electricity data**
- Pull monthly KPLC bill
- Go to ESG Activities → Add Activity
- Source: KPLC Electricity, Type: Scope 2
- Enter: kWh consumed (from bill)
- System auto-calculates: kWh × 0.432 = kgCO₂e

**Step 2 — Collect diesel/fuel data**
- From Fleet module: pull total fuel consumption (litres diesel)
- From Utilities module: pull generator fuel usage
- Add Activities for each fuel type

**Step 3 — Collect LPG/natural gas data**
- From procurement records: LPG purchased and consumed
- Add Activity entry

**Step 4 — Pull fleet data (auto-import)**
- Go to ESG Dashboard
- Click **Import from Fleet Module**
- System auto-imports vehicle fuel consumption from Fleet module
- Review and confirm

**Step 5 — Review dashboard**
- Dashboard updates automatically with new data
- Check: are this month's figures consistent with last month?
- Any large unexplained increase? (new generator? higher production?)

**Step 6 — Generate monthly report**
- Go to ESG Reports
- Click **Generate Period Report**
- Select: May 2024
- Report shows: all Scope 1 and 2 emissions, comparison to prior month, target progress

---

### Workflow: Preparing an ESG Report for a Retail Customer

**Situation:** Carrefour has requested your ESG data as part of their supplier sustainability program.

**Step 1** — Go to `/dashboard/esg/reports`  
**Step 2** — Select: Annual Report, FY2023  
**Step 3** — Generate report — system compiles:
   - Total Scope 1 emissions (tonnes CO₂e)
   - Total Scope 2 emissions
   - Carbon intensity (per tonne of product)
   - Water consumption intensity
   - Renewable energy percentage
   - ESG targets and progress  
**Step 4** — Export as PDF (Carrefour-ready format)  
**Step 5** — Review with CEO before submitting to customer  
**Step 6** — Submit to Carrefour's supplier portal  

---

### Workflow: Setting Up a New Sustainability Target

**Situation:** Board of Directors has committed to "Net Zero Scope 1 emissions by 2040."

**Step 1** — Go to `/dashboard/esg/targets`  
**Step 2** — Click **New Target**  
**Step 3** — Fill:
   - Target Name: "Net Zero Scope 1 Emissions"
   - Metric: Scope 1 Emissions (kgCO₂e)
   - Baseline Year: 2022
   - Baseline Value: 450,000 kgCO₂e (from 2022 data)
   - Target Value: 0 (Net Zero)
   - Target Date: 31-Dec-2040
   - Intermediate milestones: -30% by 2027, -60% by 2032, -80% by 2037  
**Step 4** — Save  
**Step 5** — Dashboard now shows progress bar toward this target  
**Step 6** — Board receives quarterly target progress in ESG reports  

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: Identifying Largest Emission Sources
**Situation:** Management wants to know where to focus their decarbonization efforts.

**Action:**
1. Go to ESG Dashboard
2. View "Emissions by Source" bar chart
3. Ranking shows: Generator Diesel (38%), KPLC Electricity (31%), Production LPG (22%), Fleet Fuel (9%)
4. Key insight: generator diesel is biggest source — because factory is off-grid during load-shedding
5. Recommendation: solar installation would address both Scope 1 (generator) and Scope 2 (KPLC) reduction
6. Model the impact: add solar activity with -35% generation forecast
7. Show target progress with solar in place — would meet 2027 target

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Record activity data every month — don't wait until year-end (data quality degrades)
- ✅ Update KPLC emission factor annually (download from EPRA or international databases)
- ✅ Ensure all data entries have source documentation (utility bill, fuel receipt)
- ✅ Have ESG data reviewed by the Finance team (same controls as financial data)

### DON'T:
- ❌ Never estimate activity data unless clearly labeled as estimated
- ❌ Don't submit ESG data to customers without CEO review
- ❌ Don't set targets without baseline data — they won't be credible
- ❌ Never remove historical ESG records — they form the baseline for all future comparisons

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "Emission factor not found for this source" | New source type added without emission factor | Go to Emission Factors, add appropriate factor for the source |
| "Carbon intensity seems too high" | Production volume was lower than usual (unit of production denominator) | Check if production volume data is correctly entered |
| "Target shows 0% progress" | Baseline data not entered | Go to Target, verify baseline year and value are set |
| "KPLC import shows different than bill" | Tariff structure changed | Verify kWh on bill vs. what was entered |

---

## QUICK TRAINING SUMMARY — ESG & Sustainability Reporting

> **What:** Track and report company greenhouse gas emissions, water, and sustainability targets.  
> **Scopes:** Scope 1 = direct (generators, vehicles). Scope 2 = electricity from grid.  
> **Data sources:** KPLC bills, fleet fuel logs, LPG procurement records — collected monthly.  
> **Targets:** Set baselines before setting targets. Board-approved targets go here.  
> **External reporting:** Generate GHG Protocol-compliant reports for retail customers and regulatory bodies.

---

# APPENDICES

---

## APPENDIX A: KEYBOARD SHORTCUTS & COMMAND PALETTE

**Global Command Palette:** Press **Ctrl+K** (Windows) or **Cmd+K** (Mac) from any screen.

Type any of the following to navigate instantly:
| Type this | Goes to |
|---|---|
| "mrp" | MRP Dashboard |
| "sales order" | Sales Orders list |
| "new customer" | Create new customer form |
| "inventory" | Inventory overview |
| "payroll" | Kenya Payroll dashboard |
| "stock alert" | Items below reorder point |
| "ai chat" | ERP Copilot |
| Any lot number | Find that lot directly |
| Any customer name | Open customer record |
| Any product name | Open product record |

---

## APPENDIX B: PERMISSION LEVELS

| Module | view | create | edit | approve | delete | export |
|---|---|---|---|---|---|---|
| Inventory | See stock | Post GRN | Adjust stock | — | Remove records | CSV download |
| Sales | See orders | Create orders | Edit orders | Approve discounts | — | Sales reports |
| Finance | See records | Create journals | Edit entries | Approve payments | — | Financial reports |
| HR | See employees | Add employees | Edit records | Approve leave/payroll | — | HR reports |
| AI | See results | Run AI | Action items | Approve formulations | Archive | — |

---

## APPENDIX C: COMMON ERROR CODES

| Code | Meaning | Action |
|---|---|---|
| 401 | Session expired | Log in again |
| 403 | Permission denied | Contact your administrator to grant access |
| 404 | Record not found | Check if it was deleted or if you have the correct ID |
| 422 | Validation error | Check the field-level error messages shown on screen |
| 429 | Too many requests | Wait a moment and retry (rate limit) |
| 500 | System error | Contact IT support; error has been logged automatically |

---

## APPENDIX D: GLOSSARY

| Term | Definition |
|---|---|
| ABC Classification | Categorization of inventory by value and movement frequency |
| AHL | Affordable Housing Levy (Kenya, 1.5% of gross salary) |
| BOM | Bill of Materials — recipe/formula for a product |
| CAPA | Corrective Action and Preventive Action |
| CCP | Critical Control Point in HACCP |
| EAN-13 | Standard consumer product barcode (13 digits) |
| FEFO | First Expired, First Out — picking rule for perishables |
| GRN | Goods Receipt Note — document confirming receipt of supplier delivery |
| HACCP | Hazard Analysis Critical Control Points — food safety methodology |
| KRA | Kenya Revenue Authority |
| NHIF | National Hospital Insurance Fund |
| NSSF | National Social Security Fund |
| OEE | Overall Equipment Effectiveness (Availability × Performance × Quality) |
| PAYE | Pay As You Earn — income tax deducted from salaries |
| PR | Purchase Request — internal request to buy materials |
| PO | Purchase Order — formal order to supplier |
| PTP | Promise to Pay — customer commitment to pay by specific date |
| SSCC | Serial Shipping Container Code — pallet barcode |
| WIP | Work in Progress — materials issued to production but not yet finished |

---

## APPENDIX E: SUPPORT & ESCALATION

**For system access issues:** Contact IT Administrator  
**For data entry questions:** Contact your department trainer  
**For approval workflows:** Contact your line manager  
**For financial controls:** Contact Finance Manager  
**For AI issues:** Contact Data Manager or CTO  

**Security incident (suspected fraud, unauthorized access, data breach):**  
Report IMMEDIATELY to IT Security → escalate to CFO and CEO within 1 hour.  
Do NOT use email for security incidents — use phone.

---

*End of FMCG ERP User Manual — Phase 7*

*This manual covers all 51 modules of the FMCG ERP system.*  
*Last updated: May 2026 | Version 1.0*
