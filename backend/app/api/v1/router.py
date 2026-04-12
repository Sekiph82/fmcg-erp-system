from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, users, roles, audit, logs,
    suppliers, products, materials, warehouses,
    inventory, recipes, production, wms, procurement, quality, sales, finance,
    maintenance, logistics, tax_regulatory, dashboard, integrations,
    distributors, field_sales, delivery, returns_mgmt, pricing,
    hr, documents, analytics, bulk_import, marketing, ai,
    production_advanced,
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
