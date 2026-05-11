# ERP Roadmap and Manual Plan

Source document: `C:/Users/sekip/Desktop/fmcg-erp-system-main/docs/planning/butun modulleri yaptir.docx`
Extracted: 2026-05-10T22:18:26

🔴 TIER 1 — Critical Gaps

Missing, partial, or not mature enough for real FMCG factory deployment


### 1. Enterprise-Grade Accounting Core Depth

Critical for FMCG.

Needed:

• Full double-entry general ledger• Chart of accounts setup wizard• Fiscal year and accounting period closing• Journal entries, recurring journals, reversal entries• Accounts receivable / accounts payable aging• Tax rules, withholding tax, VAT/GST localization• Trial balance, balance sheet, income statement, cash-flow statement• Payment allocation and partial reconciliation• Audit-proof immutable posting controls• Multi-currency revaluation• Kenya-specific tax/reporting workflows if this is for Kenya FMCG


### 2. Accounting-to-Inventory-to-Manufacturing Posting Integration

Critical for FMCG.

Your repo has many separate modules, but the critical test is whether every stock and production action creates correct financial impact.

Needed:

• Goods receipt → inventory asset + GRNI liability• Purchase invoice → AP + tax + landed cost adjustment• Material issue to production → WIP debit / inventory credit• Production completion → finished goods valuation• Scrap/waste → variance posting• Sales invoice → AR + revenue + tax• Delivery → COGS + inventory credit• Returns → reverse inventory and finance entries• Batch-level costing and expiry-loss write-off• Period-end inventory valuation reconciliation


### 3. Permission and Security Hardening Across All New Modules

Critical for production. Seen in mature projects through role/access design and security policies.Your core app has middleware for security headers, input sanitization, gzip, CORS, request IDs, and exception handling. But some advanced endpoints show weaker enforcement patterns. For example, traceability event creation is exposed with only DB dependency, while many QMS endpoints depend on current user but not granular permission checks.

Needed:

• Every route must declare permission requirements• Role matrix by module/action: view/create/edit/delete/approve/export/admin• High-risk actions require approval: recall, payroll, payments, GL posting, batch release, PO approval• Route-level tests proving unauthorized users are blocked• Field-level permissions for salary, cost, margin, customer credit limit• Immutable audit log for all changes• Admin-only destructive actions• No unauthenticated write endpoints except explicitly public webhooks with signatures


### 4. End-to-End Workflow Completion Testing

Critical because your repo has many modules.Your module list is now huge. The danger is “many rooms in the castle, but some doors open into painted walls.” The router shows breadth across production, QMS, traceability, finance, HR, portals, messaging, AI, IoT, POS, etc.

Needed:

• Full workflow tests from RFQ → PO → GRN → QC → stock → MRP → production → QC release → delivery → invoice → payment• Recall drill test: finished lot → impacted customers → notifications → returns → regulatory report• MRP run test with sales orders, forecast, BOM, safety stock, lead time, and supplier MOQ• Batch expiry/FEFO dispatch test• Financial posting test for each inventory movement• Regression test suite for all modules• Seed data that supports every workflow without breaking demo logic


### 5. Production-Grade Frontend Parity With Backend

Critical because backend breadth without frontend parity creates ghost modules.The backend router contains many endpoints, but the comparison must verify whether each has usable UI screens, forms, list views, approvals, dashboards, filters, exports, and error handling.

Needed:

• Module-by-module frontend coverage matrix• Sidebar should show main modules cleanly, with expandable children• Every backend endpoint should map to UI or be intentionally API-only• List/create/edit/delete screens• Approval screens• Audit/activity timeline• Import/export UX• Role-based visible menus• Consistent empty states, loading states, validation, and error messages• Mobile/tablet compatibility for warehouse, van sales, shop floor, QC, delivery


### 6. Real Integrations Instead of Stub/Placeholder Integrations

Your traceability module includes blockchain anchoring, but the code explicitly says STUB mode simulates anchoring and production should wire Ethereum/Polygon/Hyperledger SDK. Your AI provider has real OpenAI/Anthropic/Gemini support, but also mock fallback with deterministic demo content.

Needed:

• Real barcode scanner hardware flow• Real Zebra/Honeywell label printing• Real M-Pesa / bank API integration• Real email/SMS/WhatsApp sending• Real IoT MQTT/OPC-UA data ingestion• Real accounting export/import if using local accounting middleware• Real AI keys, prompts, grounding, and tool execution control• Remove or clearly label all mock/demo/stub modes in production

🟠 TIER 2 — High Importance

Partial or present, but needs depth and operational maturity


### 7. Advanced Manufacturing Capacity Planning / APS

Your repo has MRP, MPS, planning, production execution, shop floor, machine/operator modules, and material flow routes. But advanced planning needs more than route names.

Needed:

• Finite capacity scheduling• Machine calendars and downtime windows• Operator skill matrix• Changeover time by product family• CIP/cleaning time for food/FMCG production lines• Bottleneck detection• Drag-and-drop production schedule board• Schedule simulation before release• Automatic rescheduling after machine breakdown• Planned vs actual production variance


### 8. Warehouse Management Depth

Needed:

• Putaway strategies• Bin/location hierarchy• Wave picking / batch picking• FEFO enforced during picking• Pallet/license plate tracking• Mobile scanner workflow• Offline warehouse mode• Cycle count reconciliation approvals• Damaged/quarantine stock movement• Warehouse productivity metrics


### 9. Procurement and Supplier Management Maturity

Needed:

• RFQ comparison• Supplier scoring• Supplier lead-time reliability• Supplier food safety approval workflow• Approved supplier list per material• Contract pricing• Blanket orders• Purchase requisition approval matrix• Supplier claims and NCRs• Import/shipping document workflow


### 10. CRM / Sales Pipeline Depth

Needed:

• Lead → opportunity → quote → order pipeline• Sales activity tracking• Customer segmentation• Credit-limit and payment-risk scoring• Distributor performance dashboard• Lost-deal reason analytics• Customer visit planning• Retail outlet geolocation• Competitor activity capture• Salesperson target vs achievement


### 11. HRMS and Payroll Completeness

Needed:

• Employee master data• Attendance/shift management• Payroll calculation rules• Statutory deductions/local tax• Leave management• Overtime approvals• Expense reimbursement posting to finance• Training matrix• Document expiry alerts• Employee self-service mobile UX


### 12. Document Management and Internal Knowledge System

Needed:

• Version-controlled SOPs• HACCP plan document control• COA/SDS attachments• Supplier certificates and expiry alerts• Product label artwork approval• E-signature approval chain• Searchable internal wiki• Document retention policy• Access control per document type• Audit trail for document changes

🟡 TIER 3 — Medium Importance

UX, reporting, maintainability, extensibility


### 13. Custom Report Builder Depth

Your repo has a report builder route and analytics route. But mature ERP users expect report engines, not just static endpoints.

Needed:

• Drag-and-drop report builder• Saved filters• Scheduled email reports• Pivot tables• Drill-down dashboards• SQL-safe query builder• Export to Excel/PDF/CSV• Role-based report access• KPI widgets• Report templates for production, finance, sales, stock, QC, utilities


### 14. Notification Center Completeness

Your router includes notifications, messaging, email, WhatsApp, meetings, and chatter.

Needed:

• In-app notification bell• Unread counts• User preferences• Email digest• SMS/WhatsApp escalation• Critical alert escalation rules• Approval pending alerts• Stockout alerts• CCP violation alerts• Recall escalation alerts• Mark read / bulk clear / snooze


### 15. UI/UX Navigation and Sidebar Information Architecture

Your repo has enough modules to overload any sidebar. This is now an information architecture problem, not just a coding problem.

Needed:

• 12–16 fixed main groups maximum• Submodules hidden until parent opens• Search/command palette• Favorites/pinned modules• Recently used modules• Role-based menu visibility• Breadcrumbs• Module landing pages• Clear separation: Factory, Sales, Finance, HR, Quality, AI, Admin• No endless scroll-down accordion maze 🧭


### 16. API Documentation and Developer Portal Maturity

Your repo includes /docs, backend OpenAPI, webhooks, integrations, and developer portal routes.

Needed:

• Public/internal API docs• Auth examples• Webhook signature docs• Rate-limit docs• SDK examples• Postman collection• Developer API keys• Audit logs for API access• Sandbox mode• Versioned API strategy

🟢 TIER 4 — FMCG-Specific & Regulatory

Your repo is already strong here, but these areas need completion and certification-grade polish


### 17. HACCP Audit-Grade Workflow Completion

Your QMS module has HACCP hazards, CCPs, CCP logs, violations, corrective actions, lot hold/release, allergen validation, and reports.

Needed:

• HACCP plan PDF generation• CCP monitoring mobile UI• Calibration link to CCP instruments• Automatic corrective action if CCP limit exceeded• HACCP revision approvals• Audit-ready evidence pack• BRC/ISO/FSSC checklist templates• CAPA effectiveness verification• Supplier food safety document expiry alerts• Mock recall drill records


### 18. GS1 / Label Printing / Packaging Compliance

Your router includes GS1 and brand asset/label design management.

Needed:

• GS1-128 label generation• GTIN management• Expiry/lot/date AI parsing validation• Zebra/Honeywell printer integration• Label approval workflow• Multi-language label content• Allergen/nutrition/regulatory copy on label• QR traceability labels• Packaging BOM link to finished goods• Label reprint audit log


### 19. Shelf-Life / FEFO / Expiry Control

Your router includes shelf-life and traceability modules.

Needed:

• FEFO enforced at sales picking• Expiry risk dashboard• Near-expiry discount suggestions• Block expired stock automatically• Shelf-life extension approval workflow• Retest date tracking• Stability study records• Expiry-based MRP planning• Customer-specific minimum shelf-life rules• Disposal/write-off workflow


### 20. Consumer Complaint and Recall Linkage

Your router includes consumer complaints, recall/traceability, helpdesk, NPS, and quality modules.

Needed:

• Complaint → batch lookup• Complaint severity scoring• Complaint → CAPA• Complaint trend analytics• Photo/video evidence upload• Retailer/customer communication templates• Auto-trigger recall risk review• Regulatory report linkage• Root cause analysis workflow• Complaint closure approval


### 21. New Product Development / Formula Governance

Your repo includes recipes, BOM, NPD workflow, brand assets, market intelligence, dynamic pricing, allergen, QMS, and AI formulation.

Needed:

• Formula version control• Trial batch records• Lab sample approval• Cost simulation• Ingredient substitution workflow• Allergen impact check• Packaging artwork approval• Shelf-life study plan• Regulatory claim validation• Launch readiness checklist

⚪ TIER 5 — Advanced / Future Roadmap

Useful, powerful, but not first-fire priorities


### 22. True IoT / Machine Streaming

Your router has IoT and utility modules, plus utility alarms, utility KPI, electricity, water, steam, compressor, solar, wastewater, machine utility, and utility integration.

Needed:

• MQTT broker integration• OPC-UA connector• WebSocket streaming dashboard• PLC/SCADA integration• Machine downtime auto-detection• Sensor calibration records• Real-time alarms• Utility cost per batch• Energy anomaly detection• Predictive maintenance model


### 23. ML-Based Predictive Maintenance

Your repo has maintenance, machine operator intelligence, utilities, IoT, alarms, and KPI routes.

Needed:

• Vibration/temperature trend ingestion• Failure probability model• Maintenance recommendation engine• Spare parts demand prediction• Condition-based maintenance triggers• MTBF/MTTR dashboard• Downtime cost analytics• Maintenance route planning• Technician mobile app• Run-to-fail vs preventive cost comparison


### 24. AI Agent Governance and Prompt Registry

Your AI provider abstraction is real and supports multiple providers plus mock fallback. Your AI endpoint also includes natural-language ERP command parsing, but part of it is rule-based and comments say production should use LLM function calling.

Needed:

• Prompt template registry per module• Versioned prompts• Prompt approval workflow• Function/tool schema registry• Agent memory scoped by module• ERP data-grounding rules• AI output audit log• Human approval for high-risk actions• Prompt injection tests• “Mock vs Live AI” production guard


### 25. Multi-Company / Multi-Branch / Franchise Scaling

Your router includes companies and branches/multi-company-style routes.

Needed:

• Company-specific chart of accounts• Branch warehouse mapping• Intercompany sales/purchase• Consolidated reporting• Branch-level price lists• Branch-specific taxes• Branch stock transfers• Franchise/distributor visibility rules• Multi-currency per company• Legal entity separation

KULLANIM KILAVUZU HAZIRLAMA


### PROMPT 1 — Manual Audit / Repo Analysis

Bunu ilk ver. Amaç: Codex önce hiçbir manual yazmadan sistemi analiz edecek, modülleri, sayfaları, butonları, endpointleri, eksikleri çıkaracak.

Continue from current repository state. Work directly in the repo.TASK:Create a complete documentation audit for the FMCG ERP system before writing the user manual.GOAL:I want a full user manual later, but first I need a precise audit of the actual application:- all modules- all frontend pages/routes- all sidebar/menu items- all visible buttons/actions- all backend API endpoints- all schemas/models/services- all permissions/roles used- all incomplete, placeholder, mock, or disconnected featuresIMPORTANT:Do NOT invent features.Do NOT write the final user manual yet.Only inspect the repository and create an audit document.Do not modify business logic.Only create documentation files.==================================================1. CREATE AUDIT FILE==================================================Create:docs/user-manual/MANUAL_AUDIT.mdIf docs/user-manual/ does not exist, create it.==================================================2. FRONTEND INVENTORY==================================================Scan the frontend code and document:- all routes/pages- app router or page router structure- sidebar/menu/navigation configuration- module groups- visible menu labels- visible buttons/actions- forms- tables- filters- modals- dropdown actions- import/export buttons- create/edit/delete/approve/reject buttons- dashboard widgets- empty states if discoverable- related frontend file pathsFor each page, create a table:| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |If a page appears to be a placeholder, clearly mark:“Frontend placeholder or partial implementation.”==================================================3. BACKEND INVENTORY==================================================Scan the backend code and document:- all routers- all endpoint methods and paths- all related schemas- all related models- all related services- permission dependencies- authentication dependencies- status/workflow enums- mock/stub/demo-only logic- whether endpoints appear connected to frontendCreate a table:| Module | Method | Endpoint | Router File | Schema/Model/Service | Permission/Auth | Frontend Connection | Notes |If an endpoint exists but no frontend page is found, mark:“Backend/API available, frontend screen not clearly found.”If an endpoint appears public or lacks permission checks, mark:“Permission enforcement needs review.”==================================================4. MODULE COMPLETENESS MATRIX==================================================Create a module completeness table:| Module | Frontend Exists | Backend Exists | DB Models Exist | Services Exist | Permissions Exist | Workflow/Statuses Exist | Manual Priority | Notes/Gaps |Use values:- Yes- No- Partial- Not clearly discoverableManual Priority values:- Critical- High- Medium- Low- Admin/Technical only==================================================5. BUTTON / ACTION INVENTORY==================================================Create a detailed visible action inventory.For each page/module:| Module | Page | Button/Action Label | UI File Path | Expected Behavior | API Endpoint If Found | Permission If Found | Notes |Include actions such as:- Create- New- Add- Edit- Delete- Archive- Approve- Reject- Submit- Cancel- Import- Export- Upload- Download- Filter- Search- Save- Reset- Run- Generate- Convert- Send- Print- View DetailsIf the behavior cannot be verified from code, write:“Behavior not clearly discoverable from current code.”==================================================6. WORKFLOW / STATUS INVENTORY==================================================Find and document important workflow/status enums and state transitions.Examples:- DRAFT → APPROVED → IN_PROGRESS → COMPLETED- PENDING → APPROVED → REJECTED- INITIATED → IN_PROGRESS → COMPLETED- OPEN → RESOLVED → CLOSEDCreate a table:| Module | Status/Workflow | Values Found | Where Found | Notes |==================================================7. ROLE / PERMISSION INVENTORY==================================================Document:- roles- permissions- route-level permission checks- UI-level role checks- missing permission areasCreate a table:| Module | Permission | Used In Backend | Used In Frontend | Notes |Clearly flag dangerous actions that must require permission:- delete- approve- reject- recall- payroll- payments- finance posting- AI natural language execution- batch release- stock adjustment- production completion==================================================8. MOCK / STUB / DEV-ONLY INVENTORY==================================================Find and list all mock, stub, fake, demo, placeholder, or development-only logic.Create a table:| Module | Feature | File Path | Mock/Stub Description | Production Risk | Recommendation |==================================================9. OUTPUT QUALITY==================================================The audit must be honest and specific.Use actual file paths.Do not write generic comments.Do not claim a module is complete unless frontend, backend, data model, permissions, and workflow are clearly present.If something is uncertain, write:“Not clearly discoverable from current code.”==================================================10. UPDATE TASKS.md==================================================Update or create TASKS.md with:Current phase:- User manual audit completedCompleted in last run:- Created docs/user-manual/MANUAL_AUDIT.md- Audited frontend routes/pages/sidebar/buttons- Audited backend routers/endpoints/schemas/models/services- Created module completeness matrix- Created button/action inventory- Created workflow/status inventory- Created role/permission inventory- Created mock/stub/dev-only inventoryNext immediate task:- Create automated screenshot capture system using Playwright- Generate screenshots-index.json- Use MANUAL_AUDIT.md and screenshots-index.json to write the full user manualBlockers:- List anything that could not be discovered from the repository- List modules that need manual UI review- List pages where frontend/backend connection could not be confirmedFINAL RESPONSE:After finishing, summarize only:- audit file created- number of modules found- number of frontend routes/pages found- number of backend endpoints found- biggest gaps discovered- next command/task to run


### PROMPT 2 — Screenshot Automation / Playwright Capture

Bunu ikinci ver. Amaç: Codex Playwright ile ekranları otomatik gezip screenshot alacak sistem kuracak.

Continue from current repository state. Work directly in the repo.TASK:Create an automated screenshot capture system for the FMCG ERP user manual.CONTEXT:The project has hundreds of pages/modules. I do NOT want to manually provide 600+ screenshots.The previous task should have created:docs/user-manual/MANUAL_AUDIT.mdUse that audit if it exists.GOAL:Create a Playwright-based screenshot crawler that:- logs into the ERP- visits all accessible frontend routes/module pages- captures screenshots- extracts visible buttons/actions where possible- creates a screenshots index file- stores screenshots in a documentation folder- does not change business dataIMPORTANT:Do not change application business logic.Only add documentation/screenshot tooling files.Do not hardcode passwords or secrets.Use environment variables for credentials.==================================================1. VERIFY OR ADD PLAYWRIGHT==================================================Check whether Playwright is already installed.If Playwright is not installed:- add it as a dev dependency in the correct frontend/package location- add necessary config only if needed- do not break existing package filesPrefer TypeScript if the repo supports it.JavaScript is acceptable if simpler for the current repo.==================================================2. CREATE SCREENSHOT STRUCTURE==================================================Create:docs/user-manual/screenshots/docs/user-manual/screenshots/README.mddocs/user-manual/screenshots/screenshots-index.jsondocs/user-manual/screenshots/routes.jsonCreate a script in the best repo location, for example:frontend/scripts/capture-user-manual-screenshots.tsor:scripts/capture-user-manual-screenshots.tsChoose the structure that best fits the repository.Add a package script if appropriate:"manual:screenshots": "..."The command should be easy to run.==================================================3. LOGIN FLOW==================================================The script must use these environment variables:MANUAL_TEST_BASE_URLMANUAL_TEST_USERNAMEMANUAL_TEST_PASSWORDDefault base URL may be:http://localhost:3000Behavior:1. Open the base URL.2. Go to login page if not already redirected.3. Login using MANUAL_TEST_USERNAME and MANUAL_TEST_PASSWORD.4. Confirm login succeeded.5. If login fails, stop immediately with a clear error.Do NOT hardcode real credentials.If environment variables are missing, print clear instructions.Example:MANUAL_TEST_BASE_URL=http://localhost:3000MANUAL_TEST_USERNAME=admin@example.comMANUAL_TEST_PASSWORD=your_password_herenpm run manual:screenshots==================================================4. ROUTE DISCOVERY==================================================Try to discover routes from the actual frontend code and from:docs/user-manual/MANUAL_AUDIT.mdSearch for:- sidebar/menu config files- navigation config files- app router pages- route definitions- module registry files- frontend route constantsThen create/update:docs/user-manual/screenshots/routes.jsonEach route must have:{  "id": "inventory-products",  "title": "Products",  "module": "Inventory",  "path": "/inventory/products",  "priority": "core",  "capture": true}Include all known sidebar/module routes where possible.If route discovery is incomplete, still create a maintainable routes.json with the routes you can find, and document missing discovery limitations in README.md.==================================================5. SCREENSHOT CAPTURE REQUIREMENTS==================================================For each route in routes.json where capture is true:1. Navigate to the route.2. Wait for page/network stability.3. Capture full-page screenshot.4. Save as:docs/user-manual/screenshots/{module-slug}/{route-slug}.pngExample:docs/user-manual/screenshots/inventory/products.png5. Update screenshots-index.json with:{  "id": "...",  "title": "...",  "module": "...",  "path": "...",  "screenshot": "...",  "status": "captured | failed | skipped",  "error": null,  "capturedAt": "...",  "viewport": "1440x1000",  "visibleActions": []}==================================================6. SAFE READ-ONLY BEHAVIOR==================================================The screenshot script must be read-only by default.Do NOT:- create records- edit records- delete records- approve records- reject records- submit forms- run destructive operations- trigger real external sends/payments/recalls/payrollIt may safely:- open pages- open dropdowns if safe- inspect visible buttons- capture screenshots- optionally open create modal only if it does not save anything automatically- close modals after screenshotIf any action is risky, skip it and mark in screenshots-index.json.==================================================7. OPTIONAL UI STATE CAPTURE==================================================Where safe and easy, capture:- main/list page- create form/modal opened but not submitted- filter panel- action menu/dropdown- detail page if link exists and opening is read-only- dashboard viewDo not make the script fragile.If no demo data exists, mark detail/edit screenshots as skipped.==================================================8. VISIBLE ACTION EXTRACTION==================================================For each route, use Playwright to extract visible action labels.Collect visible:- button text- link text for obvious actions- menu item labels where visible- aria-labels if usefulStore them in screenshots-index.json:"visibleActions": [  "Create",  "Edit",  "Delete",  "Approve",  "Export",  "Import",  "Filter",  "Search"]Only include actions actually visible.==================================================9. ERROR HANDLING==================================================If a page fails:- do not stop the whole capture- save status as failed- include the error message- continue to next routeIf authentication fails:- stop immediately- print clear instructionsIf backend/frontend is not running:- print clear instructions to start the app, for example start-dev.bat or docker compose==================================================10. README INSTRUCTIONS==================================================Create docs/user-manual/screenshots/README.md explaining:- how to start the ERP locally- how to set MANUAL_TEST_BASE_URL- how to set MANUAL_TEST_USERNAME- how to set MANUAL_TEST_PASSWORD- how to run the screenshot capture script- where screenshots are saved- how screenshots-index.json works- how routes.json works- how to add missing routes manually- how to rerun screenshots after UI changes- how to troubleshoot login/backend/frontend errors==================================================11. MANUAL INTEGRATION PLACEHOLDER==================================================If docs/user-manual/INDEX.md exists, update it with:## Screenshot LibraryScreenshots are stored under:docs/user-manual/screenshots/Route and capture metadata are stored in:docs/user-manual/screenshots/screenshots-index.jsonIf INDEX.md does not exist yet, create a minimal one with the Screenshot Library section.Do not fabricate screenshot references.Only reference the screenshots folder and index.==================================================12. UPDATE TASKS.md==================================================Update TASKS.md with:Current phase:- User manual screenshot automation addedCompleted in last run:- Added Playwright screenshot crawler- Added screenshot output folder- Added screenshots-index.json- Added routes.json- Added README instructions- Added package script for screenshot capture if appropriateNext immediate task:- Run the ERP locally- Set MANUAL_TEST_BASE_URL, MANUAL_TEST_USERNAME, MANUAL_TEST_PASSWORD- Run the screenshot script- Review failed/skipped screenshots- Use screenshots-index.json and MANUAL_AUDIT.md to generate the full user manualBlockers:- List route discovery limitations- List whether login credentials are required- List whether demo data is missing for detail/edit/modal screenshotsFINAL RESPONSE:After finishing, summarize only:- files created- command to run screenshots- required environment variables- where screenshots will be saved- known limitations


### PROMPT 3 — Full User Manual Generation

Bunu üçüncü ver. Amaç: Codex artık MANUAL_AUDIT.md + screenshots-index.json + repo koduna göre full kullanım kılavuzu yazacak.

Continue from current repository state. Work directly in the repo.TASK:Create the complete FMCG ERP user manual using:- repository code- docs/user-manual/MANUAL_AUDIT.md- docs/user-manual/screenshots/screenshots-index.json- docs/user-manual/screenshots/routes.json- existing docs if anyGOAL:Write a detailed, professional user manual that explains:- what every module does- who uses each module- where to find it- how to use every main screen- what each important field means- what every visible button/action does- how workflows/statuses work- which roles/permissions can use each action- how modules connect to each other- common mistakes- troubleshooting- realistic FMCG example scenarios- what is complete, partial, missing, mock, or stubIMPORTANT:Do NOT invent features.Base the manual on actual code, MANUAL_AUDIT.md, and screenshots-index.json.If something is unclear, explicitly write:“Not clearly discoverable from current code.”If a backend module exists but no frontend screen exists, write:“Backend/API available, frontend screen not fully implemented.”If a frontend page exists but backend/API is missing or incomplete, write:“Frontend placeholder or partial implementation.”If a feature is mock/stub/demo-only, write:“Mock/Stub/Development mode only.”Do not modify application business logic.Only create/update documentation files and TASKS.md.==================================================1. USER MANUAL FILE STRUCTURE==================================================Create or update this folder:docs/user-manual/Create/update these files:INDEX.md00-introduction.md01-getting-started.md02-navigation-and-sidebar.md03-dashboard.md04-master-data.md05-inventory-and-warehouse.md06-procurement-and-suppliers.md07-products-recipes-bom.md08-production-and-shop-floor.md09-mrp-mps-and-planning.md10-quality-qms-haccp.md11-traceability-batch-recall-and-gs1.md12-sales-distribution-crm-and-field-sales.md13-finance-accounting-and-costing.md14-hr-payroll-expenses-and-training.md15-utilities-energy-iot-and-maintenance.md16-ai-copilot-agents-and-intelligence.md17-reports-analytics-and-dashboards.md18-documents-knowledge-base-and-communication.md19-admin-security-roles-and-permissions.md20-integrations-api-webhooks-and-portals.md21-mobile-pos-van-sales-and-delivery.md22-troubleshooting-and-faq.md23-glossary.md24-admin-technical-appendix.mdIf MANUAL_AUDIT.md identifies additional important modules that are not covered above, add additional chapter files with clear names.Do not delete MANUAL_AUDIT.md.Do not delete screenshot files.==================================================2. INDEX.md REQUIREMENTS==================================================INDEX.md must include:# FMCG ERP User ManualSections:- Introduction- Table of Contents- How to Use This Manual- User Role Reading Guide- Quick Start by Role- Screenshot Library- Module Coverage Status- Known Partial/Incomplete Modules- Admin/Technical ReferencesQuick Start by Role must include:- Admin user- Warehouse user- Production manager- QC manager- Procurement user- Sales user- Finance user- HR user- Field sales user- AI/admin userScreenshot Library must reference:docs/user-manual/screenshots/docs/user-manual/screenshots/screenshots-index.jsonModule Coverage Status must be based on MANUAL_AUDIT.md.==================================================3. REQUIRED FORMAT FOR EVERY MODULE CHAPTER==================================================For every module/chapter, use this exact structure:# Module Name## 1. PurposeExplain what the module is used for in normal business language.## 2. Who Uses This ModuleList relevant roles.## 3. Where to Find ItExplain sidebar/menu path if found.If not found, state:“No clear frontend navigation path found.”## 4. Main Screen OverviewExplain:- KPI cards- tables- filters- forms- tabs- charts- action buttons- empty states- screenshots if availableIf screenshots exist in screenshots-index.json, reference them as relative markdown image links.Example:![Products screen](screenshots/inventory/products.png)Only reference screenshots that actually exist in screenshots-index.json.## 5. Fields and ColumnsCreate tables:| Field/Column | Meaning | Required
- | Example | Notes |Use actual fields from schemas/models/frontend where possible.## 6. Buttons and ActionsCreate tables:| Button/Action | What It Does | When to Use | Permission/Role | Result | Related API |Use button/action inventory from MANUAL_AUDIT.md and screenshots-index.json.If behavior is uncertain, write:“Behavior not clearly discoverable from current code.”## 7. Step-by-Step UsageWrite practical numbered steps:- how to open the module- how to search/filter- how to create a record- how to edit a record- how to delete/archive if available- how to approve/reject if available- how to export/import if available- how to handle validation errors## 8. Complete Example ScenarioGive a realistic FMCG factory example for the module.## 9. Statuses and WorkflowExplain all statuses found in code.Example:DRAFT → APPROVED → IN_PROGRESS → COMPLETED → CLOSEDIf no workflow/status is found, write:“No explicit workflow/status values found.”## 10. Related ModulesExplain how this module connects to other modules.## 11. Permissions and SecurityDocument required roles/permissions found in code.If missing or unclear, write:“Permission enforcement not clearly found. Needs review.”## 12. Common MistakesList mistakes users may make.## 13. TroubleshootingList possible errors and what users/admins should do.## 14. Admin NotesOnly for admin/system users:- setup requirements- configuration- seed data- API notes- integration notes- mock/stub notes## 15. Implementation NotesMention actual code paths:- frontend files- backend router files- schema files- model files- service files==================================================4. SPECIAL CHAPTER REQUIREMENTS==================================================MRP / MPS / Planning:Include:- forecasts- MRP runs- MRP results- shortages- exceptions- suggestions- approve/reject suggestions- convert suggestions to purchase requisitions or production orders- required master data before running MRP- safety stock- lead times- forecast accuracy if presentTraceability / Recall / GS1:Include:- trace events- genealogy- forward traceability- backward traceability- recall initiation- recall scope calculation- containment- customer impact- customer notification- recall returns- recall closing- regulatory report- evidence- audit log- recall AI recommendations if present- blockchain/QR anchoring if present, clearly marking stub/dev-only logic if applicable- GS1/barcode/label printing if presentQMS / HACCP:Include:- QC templates- inspections- QC gate checks- HACCP hazards- CCP setup- CCP monitoring- CCP violations- corrective actions- deviations- lot hold/release- allergen validation- audit checklists- supplier food safety approval- calibration- AQL sampling- COA if present- QMS AI recommendations if presentAI Modules:Include:- AI status- live vs mock mode- provider configuration- Anthropic/OpenAI/Gemini/mock if present- predictions- recommendations- scenario simulator- formulation generator- ERP copilot chat- natural language command parsing- natural language command preview/execute/reject if present- rate limits- prompt injection safety- high-risk command confirmation- required API keys- admin safety notesFinance / Accounting:Include:- invoices- payments- bank reconciliation- fixed assets- landed cost- invoice matching- cost centers/dimensions- production costing- dunning- bank API/open banking- what appears complete- what appears partial- accounting gaps if discovered in MANUAL_AUDIT.mdInventory / WMS:Include:- products/materials- warehouses- stock movements- lots/batches- serial numbers- shelf life- cycle count- stock adjustments- FEFO if present- goods receipt- dispatch- scanner/barcode behavior if presentSales / Distribution / CRM:Include:- customers/distributors- orders- quotations- pricing- price lists- promotions- TPM- CRM pipeline- field sales- van sales- moto sales- delivery- returns- commissions- secondary sales- loyalty- NPS- customer portalUtilities / IoT / Maintenance:Include:- electricity- water- soft water- steam/boiler- compressor- solar- wastewater- chemical treatment- utility billing- machine utility mapping- utility alarms- utility KPI- IoT real-time data- maintenance- predictive maintenance if present or mark future/partial if not completeAdmin / Security:Include:- users- roles- permissions- audit logs- two-factor authentication- logs- security monitor- modules registry- company/multi-branch- webhooks- system configuration- environment setup- production safety guards if documented==================================================5. SCREENSHOT USAGE==================================================Use screenshots-index.json to reference screenshots.Rules:- Only reference screenshots whose status is "captured"- Use relative markdown image paths- Do not reference failed/skipped screenshots- If no screenshot exists for a module, write:“No screenshot captured for this module yet.”Do not overload chapters with too many screenshots.Use the most useful screenshots:- main/list page- dashboard- create form/modal- detail view- workflow/action page if available==================================================6. WRITING STYLE==================================================Write in clear professional English.The manual must be understandable for:- factory staff- warehouse workers- managers- finance/admin users- non-technical usersUse:- simple explanations- numbered steps- tables- notes- warningsUse these formats:> Note:> ...> Warning:> ...Avoid:- marketing language- vague claims- invented features- developer jargon in user sectionsAdmin/developer details belong only in:- Admin Notes- Implementation Notes- Admin Technical Appendix==================================================7. TROUBLESHOOTING AND FAQ==================================================Create a strong troubleshooting chapter covering:- login problems- permission denied- page not loading- backend unavailable- API errors- empty tables- failed imports- failed exports- failed screenshots- missing demo data- AI mock mode- AI API key missing- MRP run failed- recall action failed- QC release blocked- stock movement errors- delete/edit permission problems- external integration not configured==================================================8. GLOSSARY==================================================Create glossary entries for FMCG ERP terms:- SKU- BOM- Recipe- MRP- MPS- WMS- FEFO- FIFO- Lot- Batch- Traceability- Recall- CCP- HACCP- QMS- CAPA- COA- AQL- GRN- PO- PR- RFQ- COGS- Landed Cost- Cost Center- Distributor- Van Sales- Secondary Sales- TPM- IoT- OPC-UA- MQTT- AI CopilotAdd more terms discovered in code.==================================================9. ADMIN TECHNICAL APPENDIX==================================================Create 24-admin-technical-appendix.md with:- local development startup summary- environment files- production notes- API docs location- screenshot capture instructions- AI provider configuration- mock/stub/dev-only list summary- permission review notes- database/migration notes if discoverable- known gaps from MANUAL_AUDIT.md==================================================10. FINAL QUALITY CHECK==================================================After writing all files:1. Check all manual markdown files are readable.2. Check internal links are reasonable.3. Check screenshots referenced actually exist and were captured.4. Check every major module found in MANUAL_AUDIT.md is covered.5. Check no module is falsely marked complete.6. Check incomplete/partial modules are clearly labelled.7. Check implementation notes include real file paths.8. Check INDEX.md links to all chapters.==================================================11. UPDATE TASKS.md==================================================Update TASKS.md with:Current phase:- Full user manual generatedCompleted in last run:- Generated full docs/user-manual manual structure- Used MANUAL_AUDIT.md for module and button/action coverage- Used screenshots-index.json for screenshot references- Added module usage guides- Added role-based quick start- Added troubleshooting and glossary- Added admin technical appendix- Marked partial/incomplete/mock/stub features honestlyNext immediate task:- Manually review the generated manual- Run screenshot capture again if missing pages exist- Add missing screenshots where needed- Convert manual to PDF/HTML if required- Optionally add in-app Help links to manual chaptersBlockers:- List modules without screenshots- List modules with incomplete frontend/backend connection- List modules with unclear permissions- List features that remain mock/stub/dev-onlyFINAL RESPONSE:After finishing, summarize only:- manual files created- modules covered- screenshot usage- biggest incomplete areas- next recommended review step

Önerilen sıra

Şöyle ilerle:


### 1. PROMPT 1 → Codex audit çıkarsın.2. Audit dosyasını hızlıca kontrol et.3. PROMPT 2 → Screenshot automation kursun.4. ERP’yi çalıştırıp screenshot scriptini çalıştır.5. PROMPT 3 → Full manual yazdırsın.

En önemlisi şu: Prompt 3’ü, Prompt 2’nin screenshot scripti gerçekten çalışıp screenshots-index.json dolduktan sonra ver. Yoksa Codex manual yazar ama ekran görüntüsü referansları zayıf kalır.

Top of Form

Bottom of Form
