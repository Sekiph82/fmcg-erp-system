import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, insert, delete

from app.models.user import User, user_role
from app.models.role import Role, Permission, role_permission
from app.core.security import hash_password

logger = logging.getLogger(__name__)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL = "admin@erp.com"
ADMIN_FULL_NAME = "System Administrator"

DEMO_USERS = [
    {
        "username": "ceo",
        "password": "ceo123",
        "email": "ceo@erp.com",
        "full_name": "Chief Executive Officer",
        "role": "ceo",
    },
    {
        "username": "coo",
        "password": "coo123",
        "email": "coo@erp.com",
        "full_name": "Chief Operating Officer",
        "role": "coo",
    },
    {
        "username": "cfo",
        "password": "cfo123",
        "email": "cfo@erp.com",
        "full_name": "Chief Financial Officer",
        "role": "cfo",
    },
    {
        "username": "cto",
        "password": "cto123",
        "email": "cto@erp.com",
        "full_name": "Chief Technology Officer",
        "role": "cto",
    },
    {
        "username": "cmo",
        "password": "cmo123",
        "email": "cmo@erp.com",
        "full_name": "Chief Marketing Officer",
        "role": "cmo",
    },
    {
        "username": "mkt_manager",
        "password": "mkt123",
        "email": "mktmanager@erp.com",
        "full_name": "Marketing Manager",
        "role": "marketing_manager",
    },
    {
        "username": "data_manager",
        "password": "data123",
        "email": "data@erp.com",
        "full_name": "Data Manager",
        "role": "data_manager",
    },
]

# ── Permission definitions ────────────────────────────────────────────────────
# Format: (module, action, name, description, is_mobile_visible)
PERMISSIONS = [
    # Analytics / BI (cross-module hub)
    ("analytics",   "view",   "View Analytics",       "Access Analytics & BI hub and daily KPIs", True),
    ("analytics",   "export", "Export Analytics",     "Export BI reports and data",               False),
    # Users & Roles
    ("users",       "view",   "View Users",           "List and view user accounts",              True),
    ("users",       "create", "Create Users",          "Create new user accounts",                 False),
    ("users",       "edit",   "Edit Users",            "Edit, activate, deactivate user accounts", False),
    ("users",       "delete", "Delete Users",          "Delete user accounts",                     False),
    ("roles",       "view",   "View Roles",            "List and view roles",                      False),
    ("roles",       "create", "Create Roles",          "Create new roles",                         False),
    ("roles",       "edit",   "Edit Roles",            "Edit roles and assign permissions",        False),
    ("roles",       "delete", "Delete Roles",          "Delete roles",                             False),
    ("audit",       "view",   "View Audit Logs",       "Access the audit log trail",               False),
    ("audit",       "export", "Export Audit Logs",     "Export audit log data",                    False),

    # Inventory
    ("inventory",   "view",   "View Inventory",        "View stock and inventory data",            True),
    ("inventory",   "create", "Create Inventory",      "Add stock entries",                        False),
    ("inventory",   "edit",   "Edit Inventory",        "Adjust stock levels",                      False),
    ("inventory",   "delete", "Delete Inventory",      "Remove stock entries",                     False),
    ("inventory",   "export", "Export Inventory",      "Export inventory reports",                 False),
    # Stock Movements
    ("stock_movement", "edit",   "Edit Stock Movements",   "Edit stock movement reference/notes",  False),
    ("stock_movement", "delete", "Delete Stock Movements", "Delete and reverse stock movements",   False),

    # Products & Materials
    ("products",    "view",   "View Products",         "View product catalogue",                   True),
    ("products",    "create", "Create Products",       "Add new products",                         False),
    ("products",    "edit",   "Edit Products",         "Edit product details",                     False),
    ("products",    "delete", "Delete Products",       "Permanently delete products",              False),
    ("materials",   "view",   "View Materials",        "View raw materials",                       True),
    ("materials",   "create", "Create Materials",      "Add raw materials",                        False),
    ("materials",   "edit",   "Edit Materials",        "Edit material details",                    False),

    # Production
    ("production",  "view",   "View Production",       "View production orders and plans",         True),
    ("production",  "create", "Create Production",     "Create production orders",                 False),
    ("production",  "edit",   "Edit Production",       "Edit production orders",                   False),
    ("production",  "approve","Approve Production",    "Approve production plans",                 False),

    # Procurement
    ("procurement", "view",   "View Procurement",      "View purchase orders and requests",        True),
    ("procurement", "create", "Create Procurement",    "Raise purchase requests",                  False),
    ("procurement", "edit",   "Edit Procurement",      "Edit purchase orders",                     False),
    ("procurement", "approve","Approve Procurement",   "Approve purchase orders",                  False),

    # Sales
    ("sales",       "view",   "View Sales",            "View sales orders and invoices",           True),
    ("sales",       "create", "Create Sales",          "Create sales orders",                      False),
    ("sales",       "edit",   "Edit Sales",            "Edit sales orders",                        False),
    ("sales",       "approve","Approve Sales",         "Approve discounts and special pricing",    False),

    # Finance
    ("finance",     "view",   "View Finance",          "View financial records",                   False),
    ("finance",     "create", "Create Finance",        "Create journal entries",                   False),
    ("finance",     "edit",   "Edit Finance",          "Edit financial records",                   False),
    ("finance",     "approve","Approve Finance",       "Approve journal entries and payments",     False),
    ("finance",     "export", "Export Finance",        "Export financial reports",                 False),

    # M-Pesa specific
    ("mpesa",       "initiate_payment",   "Initiate M-Pesa Payment",    "Trigger M-Pesa STK push",              True),
    ("mpesa",       "view_transactions",  "View M-Pesa Transactions",   "View M-Pesa transaction history",      True),
    ("mpesa",       "retry_transaction",  "Retry M-Pesa Transaction",   "Retry a failed M-Pesa transaction",    False),
    ("mpesa",       "cancel_payment",     "Cancel M-Pesa Payment",      "Cancel a pending M-Pesa payment",      False),
    ("mpesa",       "reconcile_payment",  "Reconcile M-Pesa Payment",   "Mark M-Pesa payment as reconciled",    False),
    ("mpesa",       "view_payment_logs",  "View M-Pesa Payment Logs",   "View detailed M-Pesa payment logs",    False),

    # Logistics
    ("logistics",   "view",   "View Logistics",        "View shipments and customs",               True),
    ("logistics",   "create", "Create Logistics",      "Create shipment records",                  False),
    ("logistics",   "edit",   "Edit Logistics",        "Edit logistics records",                   False),

    # Quality
    ("quality",     "view",   "View Quality",          "View QC inspections",                      True),
    ("quality",     "create", "Create Quality",        "Create QC inspection records",             False),
    ("quality",     "approve","Approve Quality",       "Approve or reject QC results",             False),

    # Maintenance
    ("maintenance", "view",   "View Maintenance",      "View assets and work orders",              True),
    ("maintenance", "create", "Create Maintenance",    "Create work orders",                       False),
    ("maintenance", "edit",   "Edit Maintenance",      "Edit maintenance records",                 False),

    # Warehouses & WMS
    ("warehouses",  "view",   "View Warehouses",       "View warehouse configuration",             True),
    ("warehouses",  "create", "Create Warehouses",     "Add warehouses and zones",                 False),
    ("warehouses",  "edit",   "Edit Warehouses",       "Edit warehouse settings",                  False),
    ("wms",         "view",   "View WMS",              "View WMS operations",                      True),
    ("wms",         "create", "Create WMS",            "Create WMS transactions",                  False),
    ("wms",         "edit",   "Edit WMS",              "Edit WMS records",                         False),

    # Tax & Regulatory
    ("tax",         "view",   "View Tax",              "View tax rules and transactions",          False),
    ("tax",         "edit",   "Edit Tax",              "Manage tax rules",                         False),

    # Integrations
    ("integrations","view",   "View Integrations",     "View integration logs and configs",        False),
    ("integrations","edit",   "Edit Integrations",     "Configure integrations",                   False),

    # HR
    ("hr",          "view",   "View HR",               "View employees, shifts, leave and payroll",True),
    ("hr",          "create", "Create HR",             "Add employees, shifts and leave records",  False),
    ("hr",          "edit",   "Edit HR",               "Edit HR records",                          False),
    ("hr",          "approve","Approve HR",            "Approve leave requests and payroll",       False),
    ("hr",          "export", "Export HR",             "Export HR and payroll reports",            False),

    # Documents
    ("documents",   "view",   "View Documents",        "View document repository",                 False),
    ("documents",   "create", "Create Documents",      "Upload and create documents",              False),
    ("documents",   "edit",   "Edit Documents",        "Edit and version documents",               False),
    ("documents",   "approve","Approve Documents",     "Approve and publish documents",            False),

    # ── Bulk Import permissions ────────────────────────────────────────────────
    # Each module gets:  <module>.import  (run the import) and
    #                    <module>.import_template  (download the CSV/XLSX template)
    ("inventory",    "import",           "Import Inventory",            "Bulk-import stock records via CSV/XLSX",         False),
    ("inventory",    "import_template",  "Download Inventory Template", "Download inventory import template",             False),
    ("products",     "import",           "Import Products",             "Bulk-import product catalogue via CSV/XLSX",     False),
    ("products",     "import_template",  "Download Products Template",  "Download products import template",              False),
    ("materials",    "import",           "Import Materials",            "Bulk-import raw materials via CSV/XLSX",         False),
    ("materials",    "import_template",  "Download Materials Template", "Download materials import template",             False),
    ("production",   "import",           "Import Production",           "Bulk-import production orders via CSV/XLSX",     False),
    ("production",   "import_template",  "Download Production Template","Download production import template",            False),
    ("procurement",  "import",           "Import Procurement",          "Bulk-import purchase orders via CSV/XLSX",       False),
    ("procurement",  "import_template",  "Download Procurement Template","Download procurement import template",          False),
    ("sales",        "import",           "Import Sales",                "Bulk-import sales orders and customers via CSV", False),
    ("sales",        "import_template",  "Download Sales Template",     "Download sales import template",                 False),
    ("finance",      "import",           "Import Finance",              "Bulk-import journal entries via CSV/XLSX",       False),
    ("finance",      "import_template",  "Download Finance Template",   "Download finance import template",               False),
    ("logistics",    "import",           "Import Logistics",            "Bulk-import shipment records via CSV/XLSX",      False),
    ("logistics",    "import_template",  "Download Logistics Template", "Download logistics import template",             False),
    ("quality",      "import",           "Import Quality",              "Bulk-import QC inspection results via CSV",      False),
    ("quality",      "import_template",  "Download Quality Template",   "Download quality import template",               False),
    ("maintenance",  "import",           "Import Maintenance",          "Bulk-import assets and work orders via CSV",     False),
    ("maintenance",  "import_template",  "Download Maintenance Template","Download maintenance import template",          False),
    ("warehouses",   "import",           "Import Warehouses",           "Bulk-import warehouse/zone config via CSV",      False),
    ("warehouses",   "import_template",  "Download Warehouses Template","Download warehouses import template",            False),
    ("wms",          "import",           "Import WMS",                  "Bulk-import WMS transactions via CSV/XLSX",      False),
    ("wms",          "import_template",  "Download WMS Template",       "Download WMS import template",                   False),
    ("hr",           "import",           "Import HR",                   "Bulk-import employees and attendance via CSV",   False),
    ("hr",           "import_template",  "Download HR Template",        "Download HR import template",                    False),
    ("tax",          "import",           "Import Tax",                  "Bulk-import tax rules via CSV/XLSX",             False),
    ("tax",          "import_template",  "Download Tax Template",       "Download tax import template",                   False),
    ("users",        "import",           "Import Users",                "Bulk-import user accounts via CSV",              False),
    ("users",        "import_template",  "Download Users Template",     "Download users import template",                 False),

    # ── Marketing permissions ──────────────────────────────────────────────────
    # Dashboard
    ("marketing",              "view",            "View Marketing",             "View all marketing data and dashboards",   False),
    ("marketing",              "create",          "Create Marketing",           "Create campaigns, promotions, and plans",  False),
    ("marketing",              "edit",            "Edit Marketing",             "Edit marketing records",                   False),
    ("marketing",              "approve",         "Approve Marketing",          "Approve campaigns and spend requests",     False),
    ("marketing",              "export",          "Export Marketing",           "Export marketing reports",                 False),
    # Campaigns
    ("campaigns",              "view",            "View Campaigns",             "View campaigns list and detail",           False),
    ("campaigns",              "create",          "Create Campaigns",           "Create new campaigns",                     False),
    ("campaigns",              "edit",            "Edit Campaigns",             "Edit campaign records",                    False),
    ("campaigns",              "approve",         "Approve Campaigns",          "Approve campaign plans",                   False),
    # Promotions
    ("promotions",             "view",            "View Promotions",            "View promotions list and detail",          False),
    ("promotions",             "create",          "Create Promotions",          "Create new promotions",                    False),
    ("promotions",             "edit",            "Edit Promotions",            "Edit promotion records",                   False),
    ("promotions",             "approve",         "Approve Promotions",         "Approve promotions",                       False),
    # Analytics
    ("marketing_analytics",    "view",            "View Marketing Analytics",   "View marketing analytics and KPIs",        False),
    ("marketing_analytics",    "export",          "Export Marketing Analytics", "Export marketing analytics reports",       False),
    # CRM, spend, influencer, ecommerce, optimizer
    ("crm",                    "view",            "View CRM",                   "View CRM profiles and interactions",       True),
    ("crm",                    "create",          "Create CRM",                 "Create CRM profiles and log interactions", False),
    ("crm",                    "edit",            "Edit CRM",                   "Edit CRM records",                         False),
    ("trade_spend",            "view",            "View Trade Spend",           "View trade spend records",                 False),
    ("trade_spend",            "create",          "Create Trade Spend",         "Log trade spend",                          False),
    ("trade_spend",            "edit",            "Edit Trade Spend",           "Edit and delete trade spend records",      False),
    ("trade_spend",            "approve",         "Approve Trade Spend",        "Approve trade spend requests",             False),
    ("brand_spend",            "view",            "View Brand Spend",           "View brand spend records",                 False),
    ("brand_spend",            "create",          "Create Brand Spend",         "Log brand spend",                          False),
    ("brand_spend",            "edit",            "Edit Brand Spend",           "Edit and delete brand spend records",      False),
    ("brand_spend",            "approve",         "Approve Brand Spend",        "Approve brand spend requests",             False),
    ("influencer",             "view",            "View Influencers",           "View influencer profiles and campaigns",   False),
    ("influencer",             "create",          "Create Influencers",         "Add influencers and link campaigns",       False),
    ("influencer",             "edit",            "Edit Influencers",           "Edit influencer records",                  False),
    ("ecommerce",              "view",            "View E-commerce",            "View store and channel performance",       False),
    ("ecommerce",              "create",          "Create E-commerce",          "Add stores, products, and performance",    False),
    ("ecommerce",              "edit",            "Edit E-commerce",            "Edit e-commerce records",                  False),
    ("stores",                 "view",            "View Stores",                "View digital store/channel list",          False),
    ("stores",                 "create",          "Create Stores",              "Add new digital store channels",           False),
    ("stores",                 "edit",            "Edit Stores",                "Edit and delete store records",            False),
    ("store_performance",      "view",            "View Store Performance",     "View store performance data",              False),
    ("store_performance",      "create",          "Log Store Performance",      "Log store performance entries",            False),
    ("store_performance",      "edit",            "Edit Store Performance",     "Edit and delete performance records",      False),
    ("channel_products",       "view",            "View Channel Products",      "View product channel performance",         False),
    ("channel_products",       "create",          "Log Channel Products",       "Log product channel performance",          False),
    ("channel_products",       "edit",            "Edit Channel Products",      "Edit product channel performance records", False),
    ("ai_optimizer",           "view",            "View AI Optimizer",          "Run and view AI campaign optimizer",       False),
    ("marketing",              "import",          "Import Marketing",           "Bulk-import marketing data via CSV",       False),
    ("marketing",              "import_template", "Download Marketing Template","Download marketing import template",       False),
    # Granular marketing sub-module permissions
    ("segments",               "view",            "View Segments",              "View customer segments",                   False),
    ("segments",               "create",          "Create Segments",            "Create customer segments",                 False),
    ("segments",               "edit",            "Edit Segments",              "Edit customer segments",                   False),
    ("customer_visits",        "view",            "View Customer Visits",       "View field visits",                        False),
    ("customer_visits",        "create",          "Create Customer Visits",     "Log field visits",                         False),
    ("influencers",            "view",            "View Influencers",           "View influencer profiles",                 False),
    ("influencers",            "create",          "Create Influencers",         "Add influencer profiles",                  False),
    ("influencers",            "edit",            "Edit Influencers",           "Edit influencer records",                  False),
    ("surveys",                "view",            "View Surveys",               "View market surveys",                      False),
    ("surveys",                "create",          "Create Surveys",             "Create survey records",                    False),
    ("surveys",                "edit",            "Edit Surveys",               "Edit and delete survey records",           False),
    ("surveys",                "analyze",         "Analyze Surveys",            "Add responses, scores and analysis",       False),
    ("social_media",           "view",            "View Social Media",          "View social media activities",             False),
    ("social_media",           "edit",            "Edit Social Media",          "Edit social media records",                False),
    ("ad_performance",         "view",            "View Ad Performance",        "View ad performance records",              False),
    ("ad_performance",         "edit",            "Edit Ad Performance",        "Edit ad performance records",              False),
    ("attribution",            "view",            "View Attribution",           "View influencer and ad attribution data",  False),
    ("ai_optimizer",           "run",             "Run AI Optimizer",           "Trigger AI optimizer runs",                False),
    ("ai_optimizer",           "approve",         "Approve Optimizer",          "Approve optimizer recommendations",        False),
    # ── Cross-module marketing analytics permissions ──────────────────────────
    ("marketing_bi",           "view",            "View Marketing BI",          "View cross-module marketing BI analytics", False),
    ("marketing_bi",           "export",          "Export Marketing BI",        "Export marketing BI reports",              False),
    # Finance marketing spend report
    ("finance",                "view_marketing",  "View Marketing Spend",       "View trade/brand spend in finance module", False),
    # Sales attribution analytics
    ("sales",                  "view_attribution","View Sales Attribution",      "View campaign/promotion linked orders",    False),
    # Inventory channel stock
    ("inventory",              "view_channel",    "View Channel Stock",          "View e-commerce channel stock allocations",False),
    # Integrations marketing sync
    ("integrations",           "marketing_sync",  "Marketing Sync",             "Trigger marketing integration syncs",      False),

    # ── Utilities ─────────────────────────────────────────────────────────────
    ("utilities",  "view",   "View Utilities",   "View system configs, UOM conversions, number series and currencies", False),
    ("utilities",  "edit",   "Edit Utilities",   "Edit UOM conversions and exchange rates",                           False),
    ("utilities",  "manage", "Manage Utilities", "Full admin — create/delete system configs, number series, currencies", False),
]


# ── Import permission helpers ─────────────────────────────────────────────────
# Modules that support bulk import. Used to build per-role import grants.
_IMPORT_MODULES = [
    "inventory", "products", "materials", "production", "procurement",
    "sales", "finance", "logistics", "quality", "maintenance",
    "warehouses", "wms", "hr", "tax", "users", "marketing",
]

# Full import grant: run + download template for every module.
_ALL_IMPORT_PERMS: list[str] = [
    perm
    for m in _IMPORT_MODULES
    for perm in (f"{m}.import", f"{m}.import_template")
]

def _import(*modules: str) -> list[str]:
    """Return import + import_template for the given modules."""
    return [p for m in modules for p in (f"{m}.import", f"{m}.import_template")]


# ── Predefined roles and their permission sets ────────────────────────────────
ROLE_DEFINITIONS = {
    "owner": {
        "description": "Full system access — owner/executive",
        "permissions": "*",  # all
    },
    "admin": {
        "description": "User and role lifecycle management — plus destructive ERP data operations",
        "permissions": [
            "users.view", "users.create", "users.edit",
            "roles.view", "roles.create", "roles.edit",
            "audit.view", "audit.export",
            # Admin can delete products, inventory records, and stock movements
            "products.delete",
            "inventory.delete",
            "stock_movement.edit", "stock_movement.delete",
            # Admin can manage all utilities
            "utilities.view", "utilities.edit", "utilities.manage",
            # Admin can import users and manage import templates for user onboarding
            *_import("users"),
        ],
    },

    # ── C-Suite ───────────────────────────────────────────────────────────────
    "ceo": {
        "description": "Chief Executive Officer — full cross-functional oversight and import authority",
        "permissions": [
            # Operational visibility
            "production.view", "production.approve",
            "procurement.view", "procurement.approve",
            "inventory.view",
            "logistics.view",
            "quality.view", "quality.approve",
            "maintenance.view",
            "warehouses.view", "wms.view",
            "materials.view", "products.view",
            "sales.view", "sales.approve",
            "finance.view", "finance.approve", "finance.export",
            "mpesa.view_transactions",
            "tax.view",
            "hr.view", "hr.approve",
            "documents.view", "documents.approve",
            "audit.view", "audit.export",
            "integrations.view",
            "analytics.view", "analytics.export",
            "marketing_analytics.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "coo": {
        "description": "Chief Operating Officer — broad operational oversight",
        "permissions": [
            "production.view", "production.create", "production.edit", "production.approve",
            "procurement.view", "procurement.create", "procurement.edit", "procurement.approve",
            "inventory.view", "inventory.create", "inventory.edit", "inventory.delete",
            "stock_movement.edit", "stock_movement.delete",
            "products.delete",
            "utilities.view", "utilities.edit",
            "logistics.view", "logistics.create", "logistics.edit",
            "quality.view", "quality.create", "quality.approve",
            "maintenance.view", "maintenance.create", "maintenance.edit",
            "warehouses.view", "warehouses.create", "warehouses.edit",
            "wms.view", "wms.create", "wms.edit",
            "materials.view", "materials.create", "materials.edit",
            "products.view",
            "sales.view",
            "finance.view",
            "hr.view",
            "documents.view",
            "analytics.view",
            "audit.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "cfo": {
        "description": "Chief Financial Officer — full financial and compliance oversight",
        "permissions": [
            "finance.view", "finance.create", "finance.edit", "finance.approve", "finance.export",
            "mpesa.initiate_payment", "mpesa.view_transactions", "mpesa.retry_transaction",
            "mpesa.cancel_payment", "mpesa.reconcile_payment", "mpesa.view_payment_logs",
            "tax.view", "tax.edit",
            "procurement.view", "procurement.approve",
            "sales.view",
            "inventory.view",
            "hr.view", "hr.approve",
            "documents.view",
            "audit.view", "audit.export",
            # Marketing spend visibility for finance oversight
            "finance.view_marketing", "marketing_analytics.view", "marketing_bi.view",
            "trade_spend.view", "brand_spend.view",
            "integrations.view",
            "analytics.view", "analytics.export",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "cto": {
        "description": "Chief Technology Officer — integrations, system config, and full import authority",
        "permissions": [
            "integrations.view", "integrations.edit",
            "users.view", "users.create", "users.edit",
            "roles.view", "roles.create", "roles.edit",
            "audit.view", "audit.export",
            # CTO manages system utilities (configs, UOM, number series, currencies)
            "utilities.view", "utilities.edit", "utilities.manage",
            # Read-only visibility across all operational modules
            "production.view", "procurement.view", "inventory.view",
            "logistics.view", "quality.view", "maintenance.view",
            "warehouses.view", "wms.view", "materials.view", "products.view",
            "sales.view", "finance.view", "tax.view", "hr.view",
            "documents.view",
            "mpesa.view_transactions", "mpesa.view_payment_logs",
            "analytics.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "cmo": {
        "description": "Chief Marketing Officer — full marketing authority, cross-functional visibility, and full import authority",
        "permissions": [
            # Full marketing access
            "marketing.view", "marketing.create", "marketing.edit", "marketing.approve", "marketing.export",
            "campaigns.view", "campaigns.create", "campaigns.edit", "campaigns.approve",
            "promotions.view", "promotions.create", "promotions.edit", "promotions.approve",
            "marketing_analytics.view", "marketing_analytics.export",
            "crm.view", "crm.create", "crm.edit",
            "trade_spend.view", "trade_spend.create", "trade_spend.edit", "trade_spend.approve",
            "brand_spend.view", "brand_spend.create", "brand_spend.edit", "brand_spend.approve",
            "influencers.view", "influencers.create", "influencers.edit",
            "ecommerce.view", "ecommerce.create", "ecommerce.edit",
            "ai_optimizer.view", "ai_optimizer.run", "ai_optimizer.approve",
            "segments.view", "segments.create", "segments.edit",
            "customer_visits.view", "customer_visits.create",
            "surveys.view", "surveys.create", "surveys.edit", "surveys.analyze",
            "social_media.view", "social_media.edit",
            "ad_performance.view", "ad_performance.edit",
            "attribution.view",
            # New cross-module marketing permissions
            "marketing_bi.view", "marketing_bi.export",
            "finance.view_marketing",
            "sales.view_attribution",
            "inventory.view_channel",
            "integrations.marketing_sync",
            # Cross-functional visibility
            "sales.view", "sales.create", "sales.edit", "sales.approve",
            "products.view", "products.create", "products.edit",
            "inventory.view",
            "mpesa.initiate_payment", "mpesa.view_transactions",
            "finance.view",
            "audit.view",
            "integrations.view", "integrations.edit",
            # Full bulk-import authority across all modules (C-suite)
            *_ALL_IMPORT_PERMS,
        ],
    },

    # ── Data Manager ──────────────────────────────────────────────────────────
    "data_manager": {
        "description": "Data Manager — bulk import and template authority across all enabled modules",
        "permissions": [
            # Read access to every module (needed to validate imports)
            "inventory.view", "products.view", "materials.view",
            "production.view", "procurement.view", "sales.view",
            "finance.view", "logistics.view", "quality.view",
            "maintenance.view", "warehouses.view", "wms.view",
            "hr.view", "tax.view", "users.view",
            "documents.view",
            "audit.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },

    # ── Operational roles (module-scoped import only) ─────────────────────────
    "finance_manager": {
        "description": "Full finance and M-Pesa access",
        "permissions": [
            "finance.view", "finance.create", "finance.edit", "finance.approve", "finance.export",
            "mpesa.initiate_payment", "mpesa.view_transactions", "mpesa.retry_transaction",
            "mpesa.cancel_payment", "mpesa.reconcile_payment", "mpesa.view_payment_logs",
            "sales.view",
            # Import: own module only
            *_import("finance"),
        ],
    },
    "sales_manager": {
        "description": "Sales operations and limited payment initiation",
        "permissions": [
            "sales.view", "sales.create", "sales.edit",
            "mpesa.initiate_payment", "mpesa.view_transactions",
            "inventory.view", "products.view",
            # Import: own module only
            *_import("sales", "products"),
        ],
    },
    "procurement_officer": {
        "description": "Procurement and supplier payments",
        "permissions": [
            "procurement.view", "procurement.create", "procurement.edit",
            "materials.view",
            "inventory.view",
            "mpesa.view_transactions",
            # Import: own module only
            *_import("procurement", "materials"),
        ],
    },
    "warehouse_operator": {
        "description": "Warehouse and inventory operations",
        "permissions": [
            "inventory.view", "inventory.create", "inventory.edit", "inventory.delete",
            "warehouses.view", "wms.view", "wms.create", "wms.edit",
            "products.view", "materials.view",
            "stock_movement.edit",
            # Import: own module only
            *_import("inventory", "warehouses", "wms"),
        ],
    },
    "production_supervisor": {
        "description": "Production planning and execution",
        "permissions": [
            "production.view", "production.create", "production.edit",
            "inventory.view", "materials.view", "quality.view",
            # Import: own module only
            *_import("production", "materials"),
        ],
    },
    "quality_officer": {
        "description": "Quality control and inspection management",
        "permissions": [
            "quality.view", "quality.create", "quality.approve",
            "production.view", "inventory.view", "products.view",
            "documents.view", "documents.create",
            # Import: own module only
            *_import("quality"),
        ],
    },
    "logistics_officer": {
        "description": "Logistics, shipments, and customs documentation",
        "permissions": [
            "logistics.view", "logistics.create", "logistics.edit",
            "procurement.view", "inventory.view",
            "documents.view", "documents.create",
            # Import: own module only
            *_import("logistics"),
        ],
    },
    "maintenance_technician": {
        "description": "Asset maintenance and work order execution",
        "permissions": [
            "maintenance.view", "maintenance.create", "maintenance.edit",
            "inventory.view",
            # Import: own module only
            *_import("maintenance"),
        ],
    },
    "hr_manager": {
        "description": "HR operations — employees, attendance, leave and payroll",
        "permissions": [
            "hr.view", "hr.create", "hr.edit", "hr.approve", "hr.export",
            "users.view",
            "documents.view", "documents.create",
            # Import: own module only
            *_import("hr"),
        ],
    },

    # ── Marketing roles ───────────────────────────────────────────────────────
    "marketing_manager": {
        "description": "Marketing Manager — campaigns, promotions and spend management",
        "permissions": [
            "marketing.view", "marketing.create", "marketing.edit",
            "campaigns.view", "campaigns.create", "campaigns.edit",
            "promotions.view", "promotions.create", "promotions.edit",
            "marketing_analytics.view",
            "crm.view", "crm.create",
            "trade_spend.view", "trade_spend.create", "trade_spend.edit",
            "brand_spend.view", "brand_spend.create", "brand_spend.edit",
            "influencers.view", "influencers.create",
            "ecommerce.view",
            "ai_optimizer.view", "ai_optimizer.run",
            "segments.view", "segments.create",
            "customer_visits.view", "customer_visits.create",
            "surveys.view", "surveys.create", "surveys.edit", "surveys.analyze",
            "social_media.view", "social_media.edit",
            "ad_performance.view", "ad_performance.edit",
            "attribution.view",
            # Cross-module marketing analytics
            "marketing_bi.view", "finance.view_marketing",
            "sales.view_attribution", "inventory.view_channel",
            "integrations.view", "integrations.marketing_sync",
            "sales.view", "products.view", "inventory.view",
            "audit.view",
            *_import("marketing"),
        ],
    },
    "field_marketing_agent": {
        "description": "Field marketing agent — customer visits, surveys and CRM",
        "permissions": [
            "marketing.view",
            "crm.view", "crm.create", "crm.edit",
            "customer_visits.view", "customer_visits.create",
            "segments.view",
            "surveys.view", "surveys.create", "surveys.analyze",
            "trade_spend.view",
            "ecommerce.view",
            "sales.view", "products.view",
        ],
    },
    "brand_manager": {
        "description": "Brand Manager — brand spend, campaigns, promotions and influencers",
        "permissions": [
            "marketing.view", "marketing.create", "marketing.edit",
            "campaigns.view", "campaigns.create", "campaigns.edit",
            "promotions.view", "promotions.create", "promotions.edit",
            "marketing_analytics.view",
            "brand_spend.view", "brand_spend.create", "brand_spend.edit",
            "surveys.view", "surveys.create", "surveys.analyze",
            "influencers.view", "influencers.create", "influencers.edit",
            "social_media.view", "social_media.edit",
            "ad_performance.view",
            "attribution.view",
            "ecommerce.view",
            "ai_optimizer.view",
            "products.view", "sales.view",
            *_import("marketing"),
        ],
    },
    "trade_marketing_manager": {
        "description": "Trade Marketing Manager — trade spend and channel performance",
        "permissions": [
            "marketing.view", "marketing.create", "marketing.edit",
            "campaigns.view", "campaigns.create", "campaigns.edit",
            "promotions.view", "promotions.create", "promotions.edit",
            "marketing_analytics.view",
            "trade_spend.view", "trade_spend.create", "trade_spend.edit",
            "surveys.view", "surveys.create", "surveys.analyze",
            "ecommerce.view", "ecommerce.create", "ecommerce.edit",
            "crm.view",
            "sales.view", "products.view", "inventory.view",
            *_import("marketing"),
        ],
    },
    "digital_marketing_manager": {
        "description": "Digital Marketing Manager — social media, ads, influencers and attribution",
        "permissions": [
            "marketing.view", "marketing.create", "marketing.edit",
            "campaigns.view", "campaigns.create",
            "promotions.view",
            "marketing_analytics.view",
            "brand_spend.view", "brand_spend.create",
            "influencers.view", "influencers.create", "influencers.edit",
            "social_media.view", "social_media.edit",
            "ad_performance.view", "ad_performance.edit",
            "attribution.view",
            "ecommerce.view",
            "ai_optimizer.view",
            "products.view", "sales.view",
            *_import("marketing"),
        ],
    },
    "ecommerce_manager": {
        "description": "E-Commerce Manager — marketplace and channel performance",
        "permissions": [
            "marketing.view",
            "ecommerce.view", "ecommerce.create", "ecommerce.edit",
            "stores.view", "stores.create", "stores.edit",
            "store_performance.view", "store_performance.create", "store_performance.edit",
            "channel_products.view", "channel_products.create", "channel_products.edit",
            "ad_performance.view", "ad_performance.edit",
            "attribution.view",
            "marketing_analytics.view",
            "crm.view",
            "products.view", "inventory.view", "sales.view",
            *_import("marketing"),
        ],
    },
    "crm_manager": {
        "description": "CRM Manager — customer relationships, interactions and loyalty",
        "permissions": [
            "crm.view", "crm.create", "crm.edit",
            "marketing.view",
            "marketing_analytics.view",
            "sales.view", "products.view",
            *_import("marketing"),
        ],
    },
}


async def seed_admin(db: AsyncSession) -> None:
    """Seed permissions, predefined roles, and the default admin user."""

    # ── 1. Seed permissions ────────────────────────────────────────────────────
    perm_map: dict[str, Permission] = {}
    for module, action, name, description, is_mobile in PERMISSIONS:
        code = f"{module}.{action}"
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(
                code=code,
                name=name,
                description=description,
                module=module,
                action=action,
                is_mobile_visible=is_mobile,
            )
            db.add(perm)
            await db.flush()
        perm_map[code] = perm

    # ── 2. Seed predefined roles ───────────────────────────────────────────────
    all_perm_ids = [p.id for p in perm_map.values()]
    for role_name, role_def in ROLE_DEFINITIONS.items():
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=role_def["description"])
            db.add(role)
            await db.flush()

        # Determine permission IDs to assign
        if role_def["permissions"] == "*":
            perm_ids = all_perm_ids
        else:
            codes = role_def["permissions"]
            perm_ids = [perm_map[c].id for c in codes if c in perm_map]

        # Clear existing associations and re-insert via direct table operation
        await db.execute(
            delete(role_permission).where(role_permission.c.role_id == role.id)
        )
        if perm_ids:
            await db.execute(
                insert(role_permission),
                [{"role_id": role.id, "permission_id": pid} for pid in perm_ids],
            )

    await db.flush()

    # ── 3. Seed admin user ─────────────────────────────────────────────────────
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar_one()
    if user_count > 0:
        await db.commit()
        return

    owner_result = await db.execute(select(Role).where(Role.name == "owner"))
    owner_role = owner_result.scalar_one_or_none()

    admin = User(
        email=ADMIN_EMAIL,
        username=ADMIN_USERNAME,
        full_name=ADMIN_FULL_NAME,
        hashed_password=hash_password(ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    await db.flush()

    if owner_role:
        await db.execute(
            insert(user_role).values(user_id=admin.id, role_id=owner_role.id)
        )

    logger.info("=" * 50)
    logger.info("  DEFAULT ADMIN USER CREATED")
    logger.info("  username : %s", ADMIN_USERNAME)
    logger.info("  password : %s", ADMIN_PASSWORD)
    logger.info("  email    : %s", ADMIN_EMAIL)
    logger.info("=" * 50)

    # ── 4. Seed demo C-suite users ─────────────────────────────────────────────
    for demo in DEMO_USERS:
        role_result = await db.execute(select(Role).where(Role.name == demo["role"]))
        demo_role = role_result.scalar_one_or_none()

        demo_user = User(
            email=demo["email"],
            username=demo["username"],
            full_name=demo["full_name"],
            hashed_password=hash_password(demo["password"]),
            is_active=True,
            is_superuser=False,
        )
        db.add(demo_user)
        await db.flush()

        if demo_role:
            await db.execute(
                insert(user_role).values(user_id=demo_user.id, role_id=demo_role.id)
            )

        logger.info("  DEMO USER: username=%s  password=%s  role=%s",
                    demo["username"], demo["password"], demo["role"])

    await db.commit()
