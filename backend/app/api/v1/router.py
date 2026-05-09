from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, users, roles, audit, logs, two_factor, webhooks, fleet, cycle_count, search, security_monitor,
    suppliers, products, materials, warehouses,
    inventory, recipes, production, wms, procurement, quality, sales, finance,
    maintenance, logistics, tax_regulatory, dashboard, integrations,
    distributors, field_sales, delivery, returns_mgmt, pricing,
    hr, documents, analytics, bulk_import, marketing, ai,
    production_advanced, production_costing, production_ai, utilities, utility_management, electricity,
    water, soft_water, steam, compressor, solar, chemical_treatment, wastewater, machine_utility,
    utility_billing, utility_integration, utilities_reports,
    utility_alarm, utility_kpi,
    mrp, mps, planning, bom, production_execution, shop_floor,
    material_flow, machine_operator, shelf_life, traceability,
    qms,
    gs1,
    allergen,
    procurement_suggestion,
    subcontracting,
    landed_cost,
    invoice_match,
    bank_reconciliation,
    fixed_assets,
    dimensions,
    promotions,
    tpm,
    crm_pipeline,
    portal,
    supplier_portal,
    dunning,
    price_list,
    subscription,
    van_sales,
    contracts,
    moto_sales,
    commissions,
    expenses,
    recruitment,
    ess,
    appraisals,
    training,
    timesheets,
    notifications,
    kanban,
    report_builder,
    calendar,
    chatter,
    custom_fields,
    secondary_sales,
    esg,
    payroll_ke,
    serial_tracking,
    approvals,
    messaging,
    email_integration,
    company,
    whatsapp,
    quotation,
    helpdesk,
    project,
    pos,
    esign,
    bank_api,
    knowledge_base,
    surveys,
    voip,
    loyalty,
    meetings,
    nps,
    mobile,
    api_portal,
    containers,
    npd_workflow,
    consumer_complaints,
    regulatory_certs,
    dynamic_pricing,
    brand_assets,
    market_intelligence,
    copacking,
    iot,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(security_monitor.router, prefix="/security", tags=["security"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(two_factor.router, prefix="/auth/2fa", tags=["2fa"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(fleet.router, prefix="/fleet", tags=["fleet"])
api_router.include_router(cycle_count.router, prefix="/cycle-count", tags=["cycle-count"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(production.router, prefix="/production", tags=["production"])
api_router.include_router(wms.router, prefix="/wms", tags=["wms"])
api_router.include_router(procurement.router, prefix="/procurement", tags=["procurement"])
api_router.include_router(quality.router, prefix="/quality", tags=["quality"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(logistics.router, prefix="/logistics", tags=["logistics"])
api_router.include_router(tax_regulatory.router, prefix="/tax", tags=["tax-regulatory"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
# ── Sales & Distribution extensions ──────────────────────────────────────────
api_router.include_router(distributors.router, prefix="/distributors", tags=["distributors"])
api_router.include_router(field_sales.router, prefix="/field-sales", tags=["field-sales"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["delivery"])
api_router.include_router(returns_mgmt.router, prefix="/returns", tags=["returns"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
# ── HR ────────────────────────────────────────────────────────────────────────
api_router.include_router(hr.router, prefix="/hr", tags=["hr"])
# ── Documents ─────────────────────────────────────────────────────────────────
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
# ── Analytics / BI ────────────────────────────────────────────────────────────
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# ── Bulk Import ───────────────────────────────────────────────────────────────
api_router.include_router(bulk_import.router, prefix="/bulk-import", tags=["bulk-import"])
# ── Marketing ─────────────────────────────────────────────────────────────────
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"])
# ── AI & Intelligence ──────────────────────────────────────────────────────────
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
# ── Advanced Production Module ────────────────────────────────────────────────
api_router.include_router(production_advanced.router, prefix="/production-adv", tags=["production-advanced"])
# ── Production Costing Engine ─────────────────────────────────────────────────
api_router.include_router(production_costing.router, prefix="/production-cost", tags=["production-costing"])
# ── Production AI Intelligence ────────────────────────────────────────────────
api_router.include_router(production_ai.router, prefix="/production-ai", tags=["production-ai"])
# ── Utilities ─────────────────────────────────────────────────────────────────
api_router.include_router(utilities.router, prefix="/utilities", tags=["utilities"])
# ── Utility Management (factory utility infrastructure) ───────────────────────
api_router.include_router(utility_management.router, prefix="/utility-management", tags=["utility-management"])
# ── Electricity Management ────────────────────────────────────────────────────
api_router.include_router(electricity.router, prefix="/electricity", tags=["electricity"])
# ── Water Management ──────────────────────────────────────────────────────────
api_router.include_router(water.router, prefix="/water", tags=["water"])
# ── Soft Water Management ─────────────────────────────────────────────────────
api_router.include_router(soft_water.router, prefix="/soft-water", tags=["soft-water"])
# ── Steam & Boiler Management ──────────────────────────────────────────────────
api_router.include_router(steam.router, prefix="/steam", tags=["steam"])
# ── Compressor & Compressed Air Management ────────────────────────────────────
api_router.include_router(compressor.router, prefix="/compressor", tags=["compressor"])
# ── Solar Energy Management ────────────────────────────────────────────────────
api_router.include_router(solar.router, prefix="/solar", tags=["solar"])
# ── Chemical Water Treatment ───────────────────────────────────────────────────
api_router.include_router(chemical_treatment.router, prefix="/chemical-treatment", tags=["chemical-treatment"])
# ── Biological / Wastewater Treatment ─────────────────────────────────────────
api_router.include_router(wastewater.router, prefix="/wastewater", tags=["wastewater"])
# ── Machine Utility Consumption Mapping ────────────────────────────────────────
api_router.include_router(machine_utility.router, prefix="/machine-utility", tags=["machine-utility"])
# ── Utility Billing, Tariffs & Cost Allocation ─────────────────────────────────
api_router.include_router(utility_billing.router, prefix="/billing", tags=["utility-billing"])
# ── Utility Integration (cross-module orchestration) ─────────────────────────
api_router.include_router(utility_integration.router, prefix="/utility-management", tags=["utility-integration"])
# ── Utilities Reports & Analytics ─────────────────────────────────────────────
api_router.include_router(utilities_reports.router, prefix="/utilities-reports", tags=["utilities-reports"])
# ── Utility Alarm & Anomaly Detection ─────────────────────────────────────────
api_router.include_router(utility_alarm.router, prefix="/alarms", tags=["utility-alarms"])
# ── Utility KPI Center ────────────────────────────────────────────────────────
api_router.include_router(utility_kpi.router, prefix="/utility-kpi", tags=["utility-kpi"])
# ── MRP & Demand Forecasting ──────────────────────────────────────────────────
api_router.include_router(mrp.router, prefix="/mrp", tags=["mrp"])
# ── MPS (Master Production Scheduling) ───────────────────────────────────────
api_router.include_router(mps.router, prefix="/mps", tags=["mps"])
# ── Advanced Production Planning Suite ───────────────────────────────────────
api_router.include_router(planning.router, prefix="/planning", tags=["planning"])
# ── Advanced Multi-Level BOM / Formula / Packaging BOM ───────────────────────
api_router.include_router(bom.router, prefix="/bom", tags=["bom"])
# ── Production Execution System ───────────────────────────────────────────────
api_router.include_router(production_execution.router, prefix="/production-execution", tags=["production-execution"])
# ── Shop Floor Execution System ───────────────────────────────────────────────
api_router.include_router(shop_floor.router, prefix="/shop-floor", tags=["shop-floor"])
# ── Material Flow Engine ───────────────────────────────────────────────────────
api_router.include_router(material_flow.router, prefix="/material-flow", tags=["material-flow"])
# ── Machine + Operator Intelligence ───────────────────────────────────────────
api_router.include_router(machine_operator.router, prefix="/machine-ops", tags=["machine-operator"])
# ── FEFO + Shelf-Life Control ──────────────────────────────────────────────────
api_router.include_router(shelf_life.router, prefix="/shelf-life", tags=["shelf-life"])
# ── Lot Traceability + Batch Recall Management ────────────────────────────────
api_router.include_router(traceability.router, prefix="/traceability", tags=["traceability"])
# ── Quality Management System + HACCP ────────────────────────────────────────
api_router.include_router(qms.router, prefix="/qms", tags=["qms"])
# ── GS1 Barcode + Label Printing System ──────────────────────────────────────
api_router.include_router(gs1.router, prefix="/gs1", tags=["gs1"])
# ── Allergen + Nutrition Management ──────────────────────────────────────────
api_router.include_router(allergen.router, prefix="/allergen", tags=["allergen"])
# ── Procurement Suggestion Engine ────────────────────────────────────────────
api_router.include_router(procurement_suggestion.router, prefix="/procurement/suggestions", tags=["procurement-suggestions"])
# ── Subcontracting System ─────────────────────────────────────────────────────
api_router.include_router(subcontracting.router, prefix="/subcontracting", tags=["subcontracting"])
# ── Landed Cost Allocation ────────────────────────────────────────────────────
api_router.include_router(landed_cost.router, prefix="/landed-cost", tags=["landed-cost"])
# ── 3-Way Invoice Matching ────────────────────────────────────────────────────
api_router.include_router(invoice_match.router, prefix="/invoice-match", tags=["invoice-match"])
# ── Bank Reconciliation ───────────────────────────────────────────────────────
api_router.include_router(bank_reconciliation.router, prefix="/bank-reconciliation", tags=["bank-reconciliation"])
# ── Fixed Asset Accounting + Depreciation ─────────────────────────────────────
api_router.include_router(fixed_assets.router, prefix="/fixed-assets", tags=["fixed-assets"])
# ── Accounting Dimensions / Cost Centers ──────────────────────────────────────
api_router.include_router(dimensions.router, prefix="/dimensions", tags=["dimensions"])
# ── Promotional Schemes Auto-Apply ────────────────────────────────────────────
api_router.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
# ── Trade Promotion Management (TPM) ──────────────────────────────────────────
api_router.include_router(tpm.router, prefix="/tpm", tags=["tpm"])
# ── Advanced CRM Pipeline ─────────────────────────────────────────────────────
api_router.include_router(crm_pipeline.router, prefix="/crm", tags=["crm-pipeline"])
# ── Customer / Distributor Portal ─────────────────────────────────────────────
api_router.include_router(portal.router, prefix="/portal", tags=["portal"])
# ── Supplier Portal ────────────────────────────────────────────────────────────
api_router.include_router(supplier_portal.router, prefix="/supplier-portal", tags=["supplier-portal"])
# ── Dunning / Overdue Collection ───────────────────────────────────────────────
api_router.include_router(dunning.router, prefix="/dunning", tags=["dunning"])
# ── Price List & Discount Enhancement ─────────────────────────────────────────
api_router.include_router(price_list.router, prefix="/price-lists", tags=["price-lists"])
# ── Subscription / Recurring Orders ───────────────────────────────────────────
api_router.include_router(subscription.router, prefix="/recurring-orders", tags=["recurring-orders"])
# ── Van Sales / Mobile POS ────────────────────────────────────────────────────
api_router.include_router(van_sales.router, prefix="/van-sales", tags=["van-sales"])
# ── Contract Management ───────────────────────────────────────────────────────
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
# ── Moto Sales Extension (M-Pesa + Fraud + Performance) ──────────────────────
api_router.include_router(moto_sales.router, prefix="/moto-sales", tags=["moto-sales"])
# ── Sales Commission Tracking ─────────────────────────────────────────────────
api_router.include_router(commissions.router, prefix="/commissions", tags=["commissions"])
# ── Expense Claims ────────────────────────────────────────────────────────────
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
# ── Recruitment / ATS ─────────────────────────────────────────────────────────
api_router.include_router(recruitment.router, prefix="/recruitment", tags=["recruitment"])
# ── Employee Self-Service ─────────────────────────────────────────────────────
api_router.include_router(ess.router, prefix="/ess", tags=["ess"])
# ── Performance Appraisals ────────────────────────────────────────────────────
api_router.include_router(appraisals.router, prefix="/appraisals", tags=["appraisals"])
# ── Training & Skills Management ──────────────────────────────────────────────
api_router.include_router(training.router, prefix="/training", tags=["training"])
# ── Timesheet Approval Workflow ───────────────────────────────────────────────
api_router.include_router(timesheets.router, prefix="/timesheets", tags=["timesheets"])
# ── Notification Center ───────────────────────────────────────────────────────
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
# ── Kanban Boards ─────────────────────────────────────────────────────────────
api_router.include_router(kanban.router, prefix="/kanban", tags=["kanban"])
# ── Custom Report Builder ─────────────────────────────────────────────────────
api_router.include_router(report_builder.router, prefix="/reports-builder", tags=["report-builder"])
# ── Calendar & Resource Scheduling ───────────────────────────────────────────
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
# ── Chatter / Activity Timeline ───────────────────────────────────────────────
api_router.include_router(chatter.router, prefix="/chatter", tags=["chatter"])
# ── Custom Fields ─────────────────────────────────────────────────────────────
api_router.include_router(custom_fields.router, prefix="/custom-fields", tags=["custom-fields"])
# ── Secondary Sales / Distributor Sell-Through ────────────────────────────────
api_router.include_router(secondary_sales.router, prefix="/secondary-sales", tags=["secondary-sales"])
# ── ESG / Environmental Sustainability ────────────────────────────────────────
api_router.include_router(esg.router, prefix="/esg", tags=["esg"])
# ── Kenya Payroll Localization ─────────────────────────────────────────────────
api_router.include_router(payroll_ke.router, prefix="/payroll-ke", tags=["payroll-ke"])
# ── Serial Number Tracking ────────────────────────────────────────────────────
api_router.include_router(serial_tracking.router, prefix="/inventory/serials", tags=["serial-tracking"])
# ── Generic Approval Workflow ─────────────────────────────────────────────────
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
# ── Team Messaging / Channels ─────────────────────────────────────────────────
api_router.include_router(messaging.router, prefix="/messaging", tags=["messaging"])
# ── Email Integration ─────────────────────────────────────────────────────────
api_router.include_router(email_integration.router, prefix="/email", tags=["email"])
# ── Multi-Company / Branch ────────────────────────────────────────────────────
api_router.include_router(company.router, prefix="/companies", tags=["companies"])
# ── WhatsApp Business API ─────────────────────────────────────────────────────
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
# ── Quote / Estimation Module ─────────────────────────────────────────────────
api_router.include_router(quotation.router, prefix="/quotes", tags=["quotes"])
# ── Helpdesk / Customer Complaint Ticketing ───────────────────────────────────
api_router.include_router(helpdesk.router, prefix="/helpdesk", tags=["helpdesk"])
# ── Project Management ────────────────────────────────────────────────────────
api_router.include_router(project.router, prefix="/projects", tags=["projects"])
# ── Retail / Shop POS ─────────────────────────────────────────────────────────
api_router.include_router(pos.router, prefix="/pos", tags=["pos"])
# ── Electronic Signatures ─────────────────────────────────────────────────────
api_router.include_router(esign.router, prefix="/esign", tags=["esign"])
# ── Bank API / Open Banking ───────────────────────────────────────────────────
api_router.include_router(bank_api.router, prefix="/bank-api", tags=["bank-api"])
# ── Knowledge Base / Internal Wiki ────────────────────────────────────────────
api_router.include_router(knowledge_base.router, prefix="/kb", tags=["knowledge-base"])
# ── Employee Surveys & Engagement ─────────────────────────────────────────────
api_router.include_router(surveys.router, prefix="/surveys", tags=["surveys"])
# ── VoIP / Call Center ────────────────────────────────────────────────────────
api_router.include_router(voip.router, prefix="/calls", tags=["voip"])
# ── Customer Loyalty Program ──────────────────────────────────────────────────
api_router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
# ── Video Meetings ────────────────────────────────────────────────────────────
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
# ── NPS Tracking ─────────────────────────────────────────────────────────────
api_router.include_router(nps.router, prefix="/nps", tags=["nps"])
# ── Mobile Apps Support Layer ─────────────────────────────────────────────────
api_router.include_router(mobile.router, prefix="/mobile", tags=["mobile"])
# ── API Developer Portal ──────────────────────────────────────────────────────
api_router.include_router(api_portal.router, prefix="/developer", tags=["developer-portal"])
# ── Returnable Container Management ──────────────────────────────────────────
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
# ── NPD Workflow ──────────────────────────────────────────────────────────────
api_router.include_router(npd_workflow.router, prefix="/npd-workflow", tags=["npd-workflow"])
# ── Consumer Complaint Management ─────────────────────────────────────────────
api_router.include_router(consumer_complaints.router, prefix="/consumer-complaints", tags=["consumer-complaints"])
# ── Regulatory Certificate Tracking ──────────────────────────────────────────
api_router.include_router(regulatory_certs.router, prefix="/regulatory-certs", tags=["regulatory-certs"])
# ── Dynamic / AI Pricing Engine ───────────────────────────────────────────────
api_router.include_router(dynamic_pricing.router, prefix="/dynamic-pricing", tags=["dynamic-pricing"])
# ── Brand Asset / Label Design Management ─────────────────────────────────────
api_router.include_router(brand_assets.router, prefix="/brand-assets", tags=["brand-assets"])
# ── Market Intelligence ───────────────────────────────────────────────────────
api_router.include_router(market_intelligence.router, prefix="/market-intel", tags=["market-intelligence"])
# ── IoT / Real-Time Machine Data ─────────────────────────────────────────────
api_router.include_router(iot.router, prefix="/iot", tags=["iot"])
# ── Co-Packing / Toll Manufacturing ──────────────────────────────────────────
api_router.include_router(copacking.router, prefix="/copacking", tags=["copacking"])
