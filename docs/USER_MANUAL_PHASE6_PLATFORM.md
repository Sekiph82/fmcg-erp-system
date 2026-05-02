# PHASE 6 — PLATFORM & INTELLIGENCE
## FMCG ERP User Manual

---

<a name="notifications"></a>
# MODULE 38: NOTIFICATION CENTER

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Notification Center manages all system alerts and communications — configuring what events trigger notifications, which users receive them, through which channels (in-app, email, SMS), and scheduling automated reports and reminders.

**Why it exists in FMCG context:**  
An FMCG ERP generates hundreds of events daily: low stock alerts, overdue invoices, production holds, credit checks, expense approvals. Without a managed notification system, users are overwhelmed by irrelevant alerts or miss critical ones. The Notification Center ensures the right person receives the right alert at the right time.

---

## 3. KEY CONCEPTS

**Notification Template:** A pre-built message format for a specific event type. E.g., "Stock Low Alert" template uses: {{product_name}} is at {{current_stock}} {{uom}}, below reorder point of {{reorder_point}}.

**Notification Channel:** How notifications are delivered:
- **In-App:** Bell icon notification inside the ERP (always available)
- **Email:** Sent to user's email address
- **SMS:** Sent to user's mobile (requires SMS gateway setup)

**Notification Preference:** User-level setting — which events to receive via which channel.

**Scheduled Notification:** Automated reports sent on a schedule (e.g., "Send stock summary every Monday at 7am to Production Manager").

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Setting Up Stock Alert Notifications

**Step 1** — Go to `/dashboard/notification-center/preferences`  
**Step 2** — Find "Stock Alert" notification type  
**Step 3** — Enable for: In-App = Yes, Email = Yes, SMS = No (reduce noise)  
**Step 4** — Set threshold: only notify if stock drops below safety stock level  
**Step 5** — Click Save  
**Step 6** — Now whenever any product falls below safety stock: you receive in-app + email notification  

### Workflow: Creating a Scheduled Report

**Step 1** — Go to `/dashboard/notification-center/schedules`  
**Step 2** — Click **New Schedule**  
**Step 3** — Select template: "Weekly Inventory Summary"  
**Step 4** — Schedule: Every Monday at 7:00 AM  
**Step 5** — Recipients: Production Planner, Operations Manager  
**Step 6** — Channel: Email  
**Step 7** — Save — report will be generated and sent automatically  

---

## QUICK TRAINING SUMMARY — Notification Center

> **What:** Manage all ERP alerts and automated reports — who gets what, when, and how.  
> **Best practice:** Enable critical alerts (low stock, credit hold, QC fail) for in-app + email. Use SMS sparingly.  
> **Scheduled reports:** Replace manual Monday-morning report generation — set it up once, receive forever.

---

<a name="kanban"></a>
# MODULE 39: KANBAN BOARDS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Kanban Boards provide visual project and task management — any team can create a board, add columns (stages), and move cards (tasks) through the workflow. Pre-seeded boards exist for CRM, Recruitment, Tasks, Approvals, and Operations.

**Why it exists in FMCG context:**  
Cross-functional projects — new product launches, factory expansions, audit preparations — involve multiple departments with interdependent tasks. Kanban gives everyone visibility into what's being done, who is responsible, and what is blocking progress, without lengthy status meetings.

---

## 3. KEY CONCEPTS

**Board:** A collection of columns representing stages of a workflow.

**Column:** A stage in the workflow (e.g., "To Do", "In Progress", "Review", "Done").

**Card:** A task or work item that moves through the columns.

**Card Number:** Auto-generated (e.g., "KB-0042") — used for referencing in communications.

**WIP Limit:** Maximum number of cards allowed in a column at one time — prevents overloading.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Using Kanban for a New Product Launch

**Step 1** — Create a new board: "Antibacterial Handwash Launch"  
**Step 2** — Add columns: Concept → Formulation → QA Testing → Packaging Design → Production Trial → Launch Ready  
**Step 3** — Create cards for each task:
   - "Finalize formula" → Formulation column, assigned to R&D Manager
   - "Order packaging samples" → Formulation column, assigned to Procurement
   - "Conduct QA stability tests" → QA Testing, assigned to QC Manager  
**Step 4** — As tasks progress, team members drag cards to next column  
**Step 5** — Add comments to cards for updates and questions  
**Step 6** — @mention team members who need to action something  
**Step 7** — View board in weekly review meeting — see exactly where each task is  

---

## QUICK TRAINING SUMMARY — Kanban Boards

> **What:** Visual task management — move cards through stages to track projects and workflows.  
> **Pre-built boards:** CRM Pipeline, Recruitment, Approvals, Operations.  
> **Best practice:** Add WIP limits to prevent teams from taking on too many tasks at once.

---

<a name="report-builder"></a>
# MODULE 40: CUSTOM REPORT BUILDER

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Report Builder enables non-technical users to create custom data reports by selecting data sources, choosing fields, applying filters, and visualizing results — without writing any SQL. Reports can be saved, scheduled, and shared.

**Why it exists in FMCG context:**  
Standard reports cover 80% of needs. But every business has unique reporting requirements: "Show me all products where gross margin is below 20% AND inventory cover is above 45 days" — this requires a custom report. The Report Builder empowers managers to get their own answers without waiting for IT.

---

## 3. KEY CONCEPTS

**Data Source:** A module or table to pull data from (e.g., Sales Orders, Inventory, Finance, HR).

**Field:** A column to include in the report (e.g., Product Name, Quantity, Price, Date).

**Filter:** A condition to limit the data (e.g., "Date = Last 30 days", "Status = ACTIVE").

**Calculated Field:** A field derived from other fields using formulas (e.g., "Margin %" = (Price - Cost) / Price × 100).

**Report Schedule:** Automatically run and email a report at specified intervals.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Building a Custom Report (Example: Low-Margin High-Stock Products)

**Business need:** "Show all products with margin below 20% AND inventory cover above 45 days."

**Step 1** — Go to `/dashboard/report-builder/builder`  
**Step 2** — Step 1 of 4 — Select Data Source: "Products & Inventory"  
**Step 3** — Step 2 — Select Fields:
   - Product Name
   - Product Category
   - Standard Cost
   - Price List (default)
   - Current Stock Quantity
   - Days Cover (calculated from stock ÷ average daily demand)
   - Gross Margin %  
**Step 4** — Step 3 — Add Filters:
   - Gross Margin % < 20
   - Days Cover > 45
   - Status = ACTIVE  
**Step 5** — Step 4 — Preview: run report and review data  
**Step 6** — Name report: "Low Margin / High Stock Alert"  
**Step 7** — Click **Save**  
**Step 8** — Optional: Schedule weekly — sends to CFO every Monday 8am  

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Name reports clearly so others know what they contain
- ✅ Use filters to limit data — huge reports with millions of rows are slow and hard to read
- ✅ Add calculated fields for ratios (margin %, days cover, growth %)
- ✅ Schedule critical management reports so they arrive at the same time every week

### DON'T:
- ❌ Don't create reports with fields you have no permission to view (system will show placeholder or block)
- ❌ Don't share sensitive reports (salary, customer pricing) with unauthorized users

---

## QUICK TRAINING SUMMARY — Custom Report Builder

> **What:** 4-step wizard to build custom reports — select source, fields, filters, preview.  
> **No SQL needed:** Point-and-click interface for any manager.  
> **Schedule it:** Set up weekly reports once — they run automatically.  
> **AI assist:** "Analyze this report for patterns" — AI summarizes findings.

---

<a name="calendar"></a>
# MODULE 41: CALENDAR & RESOURCE SCHEDULING

---

## 1. MODULE OVERVIEW

**What this module does:**  
Calendar & Resource Scheduling manages company events, meetings, room/equipment bookings, and resource availability. It shows a unified view of all company activities and integrates with recruitment (interview scheduling), training (session booking), and maintenance (planned downtime).

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Booking a Meeting Room

**Step 1** — Go to `/dashboard/calendar/new-event`  
**Step 2** — Fill event details: Title, Date, Start Time, End Time, Description  
**Step 3** — Add participants: select from employee list (they receive invite)  
**Step 4** — Add Resource: "Boardroom A" (check availability first using Availability Finder)  
**Step 5** — System checks: is Boardroom A free at that time?  
**Step 6** — If available: confirms booking  
**Step 7** — If booked: shows next available slot  
**Step 8** — Click **Save** — event created, participants notified, room blocked  

### Workflow: Finding Available Slots for an Interview Panel

**Step 1** — Go to `/dashboard/calendar/availability`  
**Step 2** — Select participants: Hiring Manager, HR Manager, Technical Lead  
**Step 3** — Set: date range for interview (next 5 working days)  
**Step 4** — Set: duration needed (90 minutes)  
**Step 5** — System shows all time slots where all 3 are free  
**Step 6** — Select a slot, click **Create Event** directly from availability view  

---

## QUICK TRAINING SUMMARY — Calendar & Scheduling

> **What:** Company-wide event management and resource booking.  
> **Availability finder:** Check multiple people's availability simultaneously before scheduling.  
> **Integration:** Interview scheduling (Recruitment), training sessions, and maintenance windows all flow through Calendar.

---

<a name="chatter"></a>
# MODULE 42: ACTIVITY TIMELINE / CHATTER

---

## 1. MODULE OVERVIEW

**What this module does:**  
Chatter is the activity timeline system — a contextual communication feed attached to every record in the ERP. Instead of emailing colleagues about a specific invoice, production order, or customer, you communicate directly on the record itself. Everyone involved can see the full conversation history.

**Why it exists in FMCG context:**  
"Did we follow up on Invoice #1234?" — this question leads to searching through email chains. With Chatter, the answer is visible on Invoice #1234's timeline: who said what, when, and what actions were taken. Context is never lost.

---

## 3. KEY CONCEPTS

**Activity:** A system-generated or manual log entry on a record (e.g., "Status changed from DRAFT to CONFIRMED", "@John Doe please review the quantities").

**Comment:** A manual message posted by a user on a specific record.

**@Mention:** Tag a user to bring their attention to a comment. They receive a notification.

**Attachment:** File uploaded directly to a record's timeline.

---

## 5. KEY USE CASES

**Scenario 1: Sales Order Discrepancy Discussion**
- Customer calls: "We received 45 cases but ordered 50"
- Open the Sales Order
- On the Chatter panel: post "Customer called — says they received 45 cases. Warehouse: please confirm actual quantities dispatched. @James Kariuki"
- James sees the notification, checks dispatch records
- Responds on the same order: "Confirmed dispatch was 45 cases — 5 were on QC hold. Will ship remainder tomorrow."
- Finance team can see this history when they process the invoice

**Scenario 2: Production Issue Escalation**
- QC holds a batch
- QC Inspector posts on the production order: "Batch failed pH test — 5.8, spec is 6.5–7.5. @Sarah Wanjiku please advise on corrective action."
- Production Manager sees notification immediately
- Responds: "Add 2 KG of caustic soda solution, remix 20 minutes, retest."
- Complete decision trail is on the record — no lost email

---

## QUICK TRAINING SUMMARY — Chatter & Timeline

> **What:** Contextual communication attached to ERP records — comments, activities, @mentions.  
> **Use instead of:** Email for anything related to a specific ERP record.  
> **Key benefit:** Complete decision history on every record. Never "where was that email?" again.  
> **@mention:** Tag colleagues for action items — they get instant notification.

---

<a name="custom-fields"></a>
# MODULE 43: CUSTOM FIELDS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Custom Fields allows system administrators to add extra data fields to any entity in the ERP — customers, products, sales orders, employees, etc. — without modifying the core system code. 16 field types supported: text, number, date, dropdown, checkbox, multi-select, file attachment, and more.

**Why it exists in FMCG context:**  
Every business has unique data requirements. An FMCG company might need: a "Temperature Requirement" field on products (some products need cold storage), a "Route Classification" field on customers (for van sales routing), or a "Regulatory Status" field on materials. Custom Fields provide this flexibility without development work.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Adding a Custom Field to Products

**Situation:** You want to add a "Storage Temperature" field to all products to indicate cold, ambient, or hot storage.

**Step 1** — Go to `/dashboard/custom-fields/new-field`  
**Step 2** — Field settings:
   - Entity Type: Product
   - Field Name: "Storage Temperature"
   - Field Code: "storage_temp" (auto-generated, can edit)
   - Field Type: Dropdown
   - Options: "Cold (<8°C)", "Ambient (8°C–30°C)", "Warm (>30°C)"
   - Required: Yes
   - Section: "Logistics"  
**Step 3** — Save field  
**Step 4** — Now every Product record has a new "Storage Temperature" dropdown  
**Step 5** — Existing products show "Not Set" — update in bulk or one by one  
**Step 6** — Report Builder can now filter/report on Storage Temperature  

---

## QUICK TRAINING SUMMARY — Custom Fields

> **What:** Add custom data fields to any ERP entity without coding.  
> **When to use:** When you have data to track that the standard system doesn't capture.  
> **Field types:** Text, Number, Date, Dropdown, Checkbox, Multi-select, URL, File, Formula (computed).  
> **Admin task:** Only system administrators should create custom fields.

---

<a name="2fa"></a>
# MODULE 44: 2FA & SECURITY

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Security Settings module allows users to enable Two-Factor Authentication (2FA) for their account, and administrators to monitor security events, manage locked accounts, and view the security dashboard.

---

## 3. KEY CONCEPTS

**2FA (Two-Factor Authentication):** Requires a second proof of identity beyond your password — either a time-based code from an authenticator app (TOTP), SMS code, or email code.

**TOTP (Time-based One-Time Password):** A 6-digit code generated by an app (Google Authenticator, Microsoft Authenticator) that changes every 30 seconds.

**Recovery Codes:** One-time use backup codes to access your account if you lose your authenticator device. Store these safely.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Setting Up 2FA for Your Account

**Step 1** — Go to `/dashboard/security`  
**Step 2** — Click **Enable Two-Factor Authentication**  
**Step 3** — Choose method: "Authenticator App (TOTP)" (most secure)  
**Step 4** — System shows a QR code  
**Step 5** — On your phone: open Google Authenticator or similar app  
**Step 6** — Tap the "+" to add a new account  
**Step 7** — Scan the QR code on screen  
**Step 8** — App shows: "FMCG ERP — [your username]" with a 6-digit code  
**Step 9** — Enter the 6-digit code into the verification box on screen  
**Step 10** — Click **Verify & Enable**  
**Step 11** — System shows 8 Recovery Codes — **SAVE THESE SECURELY** (print or store in password manager)  
**Step 12** — 2FA is now active — every login will require your code  

### Workflow: Logging In with 2FA Active

**Step 1** — Enter username and password as normal  
**Step 2** — System detects 2FA is enabled for your account  
**Step 3** — Prompted: "Enter your 6-digit authentication code"  
**Step 4** — Open your authenticator app, view current code  
**Step 5** — Type the 6-digit code quickly (it changes every 30 seconds)  
**Step 6** — Click **Verify** — logged in successfully  

---

### Security Monitor (Admin Only)

**Go to `/dashboard/security/monitor` to view:**
- Failed login attempts in the last 24 hours
- Top IP addresses with multiple failures (potential attack)
- Security anomalies (AI injection attempts, policy violations)
- Account lock status
- Manual unlock tool

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Enable 2FA for ALL admin and finance accounts — non-negotiable
- ✅ Store recovery codes in a secure location (not on the same device as the authenticator)
- ✅ Report any unexpected 2FA prompts to IT immediately (someone has your password)

### DON'T:
- ❌ Never share your 6-digit authentication code with anyone — not even IT
- ❌ Don't use the same phone for work and personal authenticator apps if possible
- ❌ Never screenshot or photograph your QR code setup

---

## QUICK TRAINING SUMMARY — 2FA & Security

> **What:** Two-factor authentication and security monitoring.  
> **2FA setup:** Scan QR code with authenticator app. Save recovery codes offline.  
> **Admin:** Security Monitor dashboard — view failed logins, locked accounts, anomalies.  
> **Security rule:** Admin and Finance accounts MUST have 2FA enabled. No exceptions.

---

<a name="webhooks"></a>
# MODULE 45: WEBHOOK / EVENT ENGINE

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Webhook Engine allows the ERP to send real-time notifications to external systems whenever specific events occur (e.g., "when a sales order is created", "when a payment is received", "when stock falls below safety level"). External systems receive these events and can react automatically.

**Why it exists in FMCG context:**  
Modern FMCG operations integrate with multiple external systems: e-commerce platforms (Jumia, Kilimall), logistics partners (delivery APIs), accounting systems (QuickBooks, Sage), and business intelligence tools. Webhooks enable these systems to stay synchronized in real-time without manual data export.

---

## 3. KEY CONCEPTS

**Event Definition:** A named event that the ERP can fire (e.g., "invoice.created", "stock.low_alert", "payment.received").

**Subscription:** A configuration that links an event to an external URL. When the event fires, a POST request is sent to that URL.

**HMAC Signature:** Every webhook payload is signed with a secret key. The receiving system should verify this signature to confirm the message is genuine and hasn't been tampered with.

**Idempotency Key:** A unique ID in each webhook payload that allows the receiving system to detect and ignore duplicate deliveries.

**Dead-Letter Queue:** Failed webhooks (external system didn't respond) are stored here for investigation and manual retry.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Setting Up a Webhook Subscription

**Situation:** Your e-commerce platform needs to know when a sales order is confirmed so it can update order status.

**Step 1** — Go to `/dashboard/webhooks/subscriptions`  
**Step 2** — Click **New Subscription**  
**Step 3** — Select Event: "sales_order.confirmed"  
**Step 4** — Enter URL: `https://your-ecommerce.com/api/erp-webhook`  
**Step 5** — Generate a webhook secret (or enter your own)  
**Step 6** — Set: Retry attempts = 3, Timeout = 10 seconds  
**Step 7** — Click **Save**  
**Step 8** — Use **Send Test Ping** to verify the connection works  
**Step 9** — Now every time a sales order is confirmed, your e-commerce platform receives the payload immediately  

---

## QUICK TRAINING SUMMARY — Webhook Engine

> **What:** Real-time event notifications to external systems via HTTP POST.  
> **Security:** Every payload signed with HMAC. Receiving system MUST verify signature.  
> **Dead-letter queue:** Failed deliveries are retried 3 times, then stored for manual review.  
> **Common use:** Sync with e-commerce, logistics, BI tools, or partner systems.

---

<a name="ai"></a>
# MODULE 46: AI & INTELLIGENCE LAYER

---

## 1. MODULE OVERVIEW

**What this module does:**  
The AI & Intelligence Layer provides enterprise-level AI capabilities embedded in the ERP: demand predictions, business recommendations, scenario simulations, chemical formulation generation, and a conversational ERP Copilot. All AI actions are logged, require human review, and never execute transactions automatically.

**Why it exists in FMCG context:**  
FMCG companies generate enormous amounts of operational data but rarely have the analyst resources to extract insights from it. AI surfaces patterns, forecasts outcomes, and generates recommendations that would take human analysts hours — in seconds. The key difference from dangerous "AI automation" is that this system recommends; humans decide.

**Business impact:**  
- Faster insight generation (minutes vs. hours)
- AI-assisted demand forecasting reduces safety stock by 15–25%
- Formulation AI reduces product development time by 30–40%
- ERP Copilot reduces time spent hunting for reports and data

---

## 2. USER ROLES

| Role | AI Access |
|---|---|
| **CEO / Operations Manager** | All AI modules — full access |
| **Production Planner** | Predictions, scenarios |
| **Finance Manager** | Recommendations, scenarios, risk analysis |
| **R&D Manager** | Formulation Engine |
| **Sales Manager** | CRM AI, predictions |
| **Data Manager / Analyst** | Full AI + report builder AI |

---

## 3. KEY CONCEPTS

**AI Provider:** The underlying LLM (Large Language Model). System uses Gemini, OpenAI, or Anthropic depending on configuration. Visible in the status bar.

**AI Mode:**
- **Live:** Connected to real LLM API — produces real, data-grounded insights
- **Mock/Dev:** No API key configured — returns demo responses (labeled clearly)

**AI Agents (Module-Level):** Each module has rule-based agents (no LLM) that run statistical analysis and detect anomalies. These are labeled "Rule-Based" and are always ON.

**AI Copilot:** The conversational chat interface where you can ask any question about your ERP data in plain language.

**Recommendations:** Actionable suggestions generated by AI. Must be reviewed and actioned by a human — AI never acts autonomously.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: AI Dashboard (`/dashboard/ai`)

- **Provider status:** Which LLM is active (Gemini / OpenAI / Anthropic / Mock)
- **Active predictions:** Forecasts generated, not yet archived
- **Pending recommendations:** AI suggestions awaiting your action
- **Recent formulations:** AI-generated product formulas
- **AI logs:** Complete history of all AI calls

### Screen: AI Predictions (`/dashboard/ai/predictions`)

**Generate Predictions:**
- Click **Generate Predictions**
- Select prediction types: Sales Forecast, Stock Depletion, Cost Trends, Supplier Risk
- AI analyzes last 90 days of ERP data
- Returns 5–8 predictions with: type, summary, risk level (low/medium/high/critical), confidence score

**Reading a prediction:**
- **Risk Level:** How urgent is this?
- **Confidence Score:** How certain is the AI? (0.0 = guess, 1.0 = very confident)
- **Summary:** Plain English explanation
- **Items At Risk:** Specific products/materials highlighted

**Critical rule:** A HIGH RISK prediction does not automatically trigger any action. You must review and decide.

### Screen: AI Recommendations (`/dashboard/ai/recommendations`)

**Generate Recommendations:**
- Click **Generate Recommendations**
- Optionally focus on an area (pricing, stock, suppliers)
- AI reviews ERP data and generates 5–8 actionable recommendations

**Each recommendation shows:**
- Category: Pricing / Stock / Supplier / Production / Margin
- Title: Short action statement
- Reason: Why AI is recommending this (data-backed)
- Expected Impact: Estimated benefit in KES or %
- Priority: Low / Medium / High / Critical
- Confidence: How certain the AI is

**What to do with a recommendation:**
1. Read the recommendation carefully
2. Verify the underlying data (check the referenced product/supplier)
3. Discuss with relevant team member
4. If you agree: click **Action** — logs that you reviewed and acted on it
5. If you disagree: click **Dismiss** — logs the dismissal with optional reason
6. Never automatically execute a recommendation without human verification

### Screen: ERP Copilot (`/dashboard/ai/chat`)

**The conversational interface. Type any question about your ERP data.**

**Good questions to ask:**
- "What is our outstanding receivables balance?"
- "Which products had the highest sales last month?"
- "Are there any materials at critical stock levels right now?"
- "What is the current production plan for next week?"
- "Show me our top 5 customers by revenue this year"
- "Which suppliers have quality issues?"
- "What is our current cash position?"

**Questions the Copilot CANNOT answer:**
- Anything outside the ERP data (market prices, competitor data)
- Requests to execute transactions: "Approve this invoice" — it will decline
- Questions requiring data it doesn't have access to

**Safety note:** The Copilot is designed to assist with information only. It cannot post transactions, approve anything, or change data in the system. If it appears to do so, report it to IT immediately.

### Screen: Formulation Engine (`/dashboard/ai/formulations`)

**Generate a new product formulation.**

**Input fields:**
- Product Category (liquid detergent, shampoo, cream, wipes, etc.)
- Target Properties (cleaning power, fragrance, eco-friendly, skin-mild, etc.)
- Cost Target (maximum cost per KG in USD)
- Performance Priority (cost / balanced / quality)

**Output includes:**
- Complete ingredient list with INCI names, CAS numbers, percentages
- Total must equal 100%
- Process instructions (step-by-step manufacturing)
- Cost breakdown (raw materials, packaging, labor)
- Performance profile
- Three alternative formulations (economy, premium, eco)
- Safety notes per ingredient
- Regulatory compliance notes

**Critical rule:** AI-generated formulations are starting points for your R&D team. They must be reviewed by a qualified chemist and validated through laboratory testing before production. Never produce based solely on AI output.

### Screen: Scenario Simulator (`/dashboard/ai/scenarios`)

**Test business scenarios before committing.**

**Scenario types:**
- **Price Change:** "What happens if I increase Detergent 1L price by 10%?"
- **Cost Change:** "What if SLES cost increases 25%?"
- **Supplier Change:** "What if I switch SLES supplier at -5% cost?"
- **Product Change:** "What if I launch a new Premium Detergent 750ml?"

**Output:**
- Revenue impact (% change)
- Volume impact (elasticity)
- Margin impact
- Break-even timeline
- Top 3 risks
- Top 3 opportunities
- Final recommendation (proceed / modify / avoid)

**When to use:** Before major pricing decisions, supplier changes, or new product launches. Scenario Simulator gives you data-grounded reasoning in seconds.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Using AI for Monthly Business Review

**Every month-end: 30-minute AI-assisted review**

**Step 1** — Generate Predictions
- Go to AI Predictions
- Click **Generate Predictions** for "all types"
- Review results: any HIGH or CRITICAL predictions?
- Share critical predictions with management

**Step 2** — Generate Recommendations
- Click **Generate Recommendations**
- Read each recommendation: which are actionable this month?
- Action the highest priority ones
- Dismiss irrelevant ones with reason

**Step 3** — Chat with Copilot for quick answers
- "What was our average gross margin this month?"
- "Which product lines are above target?"
- "Are there any unusual variances in the data?"

**Step 4** — Archive actioned predictions**
- Clean up prediction list — archive items that are no longer relevant

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: AI Recommends Emergency Stock Order
**AI Recommendation appears:** "CRITICAL: SLES 70% will deplete in 4 days at current production rate. Order 2,000 KG immediately. Preferred supplier: BASF, Lead time: 5 days. Current stock: 180 KG."

**Your verification steps:**
1. Go to Inventory — verify SLES current stock is indeed ~180 KG ✓
2. Check production plan — confirm production rate is accurate ✓
3. Check Supplier Master — confirm BASF lead time is 5 days ✓
4. Agree with recommendation

**Your action:** Go to Procurement → Create PO for 2,000 KG SLES from BASF. This is a human action triggered by AI insight.

---

### Scenario: AI Formulation for New Product
**Situation:** You want to develop an eco-friendly shampoo for the premium market.

**Step 1:** Go to Formulation Engine
**Step 2:** Enter:
- Category: Shampoo
- Properties: eco-friendly, no sulphates, natural fragrance, biodegradable
- Cost target: $2.50/KG
- Priority: Quality

**Step 3:** Review output — 15 ingredients listed with INCI names, CAS numbers, percentages
**Step 4:** Send to R&D Manager: "AI has generated a starting formula — please review and validate"
**Step 5:** R&D reviews, modifies based on their expertise, and orders lab samples
**Step 6:** After lab validation: create BOM in system with validated formula

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Always verify AI recommendations against actual data before acting
- ✅ Use AI Copilot for quick information retrieval — it saves time finding reports
- ✅ Use Formulation Engine as a starting point — not a final product
- ✅ Review AI logs periodically — understand what AI is analyzing
- ✅ Dismiss irrelevant recommendations with a reason — it helps the AI learn context

### DON'T:
- ❌ Never execute financial transactions based solely on AI recommendation without human review
- ❌ Don't share AI-generated formulations with suppliers before internal QA review
- ❌ Never trust AI confidence score of 100% — AI is probabilistic, not certain
- ❌ Don't use the Copilot to discuss confidential information unnecessarily
- ❌ Never attempt to manipulate the AI into revealing secrets — attempts are logged

---

## 8. COMMON QUESTIONS

**Q: "The AI is in Mock Mode. What does this mean?"**  
A: No API key is configured. Responses are demo data, clearly labeled [MOCK/DEV MODE]. Contact your IT administrator to configure a real LLM provider.

**Q: "AI recommendation says one thing, my experience says another. Which do I trust?"**  
A: Trust your experience. AI is a tool that surfaces patterns in data. It doesn't know about market relationships, regulatory changes, or context that isn't in the ERP data. Use AI as input, not final decision-maker.

**Q: "Can AI approve an expense claim or purchase order?"**  
A: No. AI cannot execute any transaction in the system. It can only suggest, analyze, and answer questions.

---

## AI SAFETY PRINCIPLES (ALL USERS MUST KNOW)

1. **AI recommends. Humans decide.** Every AI output requires human review before action.
2. **AI cannot execute transactions.** It cannot post invoices, approve POs, or change stock levels.
3. **AI outputs are logged.** Every AI call is recorded with who asked, what was asked, and what was answered.
4. **All inputs are filtered.** The system has prompt injection protection — attempts to manipulate AI behavior are detected and blocked.
5. **Sensitive data is masked.** Customer names and financial details are partially masked before being sent to external AI providers.

---

## QUICK TRAINING SUMMARY — AI & Intelligence Layer

> **What:** AI-powered predictions, recommendations, scenario simulation, formulation engine, and ERP Copilot.  
> **AI Mode:** Live (real LLM) or Mock (demo data). Check mode in AI status bar.  
> **Golden rule:** AI recommends. YOU decide and execute.  
> **Copilot:** Ask any question about your ERP data in plain language — fastest way to get answers.  
> **Formulation Engine:** Starting point only — always validate in the lab before production.  
> **Safety:** All AI actions logged. AI cannot execute transactions. Prompt injection blocked.

---
