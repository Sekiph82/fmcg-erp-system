from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, users, roles, audit, logs,
    suppliers, products, materials, warehouses,
    inventory, recipes, production, wms, procurement, quality, sales, finance,
    maintenance, logistics, tax_regulatory, dashboard, integrations,
    distributors, field_sales, delivery, returns_mgmt, pricing,
    hr, documents, analytics, bulk_import, marketing, ai,
    production_advanced, production_costing, production_ai, utilities, utility_management, electricity,
    water, soft_water, steam, compressor, solar, chemical_treatment, wastewater, machine_utility,
    utility_billing, utility_integration, utilities_reports,
    utility_alarm, utility_kpi,
    mrp, mps,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
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
