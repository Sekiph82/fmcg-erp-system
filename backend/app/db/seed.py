import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, insert, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.user import User, user_role
from app.models.role import AccessScope, Role, Permission, role_permission
from app.core.config import settings
from app.core.module_registry import MODULE_DEFINITIONS
from app.core.security import hash_password

logger = logging.getLogger(__name__)

DEMO_USERS = [
    {
        "username": "ceo",
        "email": "ceo@erp.com",
        "full_name": "Chief Executive Officer",
        "role": "ceo",
    },
    {
        "username": "coo",
        "email": "coo@erp.com",
        "full_name": "Chief Operating Officer",
        "role": "coo",
    },
    {
        "username": "cfo",
        "email": "cfo@erp.com",
        "full_name": "Chief Financial Officer",
        "role": "cfo",
    },
    {
        "username": "cto",
        "email": "cto@erp.com",
        "full_name": "Chief Technology Officer",
        "role": "cto",
    },
    {
        "username": "cmo",
        "email": "cmo@erp.com",
        "full_name": "Chief Marketing Officer",
        "role": "cmo",
    },
    {
        "username": "mkt_manager",
        "email": "mktmanager@erp.com",
        "full_name": "Marketing Manager",
        "role": "marketing_manager",
    },
    {
        "username": "data_manager",
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
    ("finance",     "configure", "Configure Finance",   "Configure fiscal years, periods, and posting rules", False),

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
    ("documents",   "archive","Archive Documents",     "Archive or obsolete controlled documents", False),
    ("documents",   "export", "Export Documents",      "Export document metadata and files",       False),

    # Knowledge base and e-signature
    ("knowledge_base", "view",    "View Knowledge Base",    "View internal knowledge articles",         False),
    ("knowledge_base", "create",  "Create Knowledge Base",  "Create knowledge categories and articles", False),
    ("knowledge_base", "edit",    "Edit Knowledge Base",    "Edit knowledge articles",                  False),
    ("knowledge_base", "publish", "Publish Knowledge Base", "Publish knowledge articles",               False),
    ("knowledge_base", "delete",  "Archive Knowledge Base", "Archive knowledge articles",               False),
    ("knowledge_base", "admin",   "Admin Knowledge Base",   "Administer knowledge-base structure",      False),
    ("esign", "view",    "View E-Signatures",   "View electronic signature requests",       False),
    ("esign", "request", "Request E-Signature", "Create electronic signature requests",     False),
    ("esign", "sign",    "Sign Electronically", "Sign assigned electronic signature tasks", False),
    ("esign", "cancel",  "Cancel E-Signature",  "Cancel own signature requests",            False),
    ("esign", "admin",   "Admin E-Signatures",  "Administer electronic signature workflow", False),

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

    # ── AI & Intelligence ─────────────────────────────────────────────────────
    ("ai",  "view",    "View AI",            "View AI dashboard, predictions, recommendations, logs",          False),
    ("ai",  "create",  "Run AI",             "Generate AI predictions, recommendations, scenarios, formulations, chat", False),
    ("ai",  "edit",    "Action AI",          "Mark AI recommendations as actioned or dismissed",               False),
    ("ai",  "approve", "Approve AI",         "Approve AI-generated formulations and high-risk recommendations", False),

    # ── Utility Management (factory infrastructure) ────────────────────────────
    ("utility_management", "view",   "View Utility Management",   "View utility assets, meters, readings, consumption", False),
    ("utility_management", "create", "Create Utility Management", "Add utility assets, meters, and log readings",        False),
    ("utility_management", "edit",   "Edit Utility Management",   "Edit utility asset and meter configuration",          False),

    # ── Fleet Management ──────────────────────────────────────────────────────
    ("fleet",  "view",   "View Fleet",    "View vehicles, drivers, trips, fuel, and incidents",   False),
    ("fleet",  "create", "Create Fleet",  "Add vehicles, drivers, and log trips",                 False),
    ("fleet",  "edit",   "Edit Fleet",    "Edit fleet records and approve trips",                 False),

    # ── Cycle Counting ────────────────────────────────────────────────────────
    ("cycle_count", "view",    "View Cycle Count",    "View count plans, tasks, and variances",         False),
    ("cycle_count", "create",  "Create Cycle Count",  "Create count plans and enter count results",     False),
    ("cycle_count", "approve", "Approve Cycle Count", "Approve variances and post stock adjustments",   False),

    # ── Webhook / Event Engine ────────────────────────────────────────────────
    ("integrations", "webhooks", "Manage Webhooks",  "Create, delete, and test webhook subscriptions", False),

    # ── ESG / Sustainability ──────────────────────────────────────────────────
    ("esg",  "view",   "View ESG",    "View ESG activities, emissions, and targets",        False),
    ("esg",  "create", "Create ESG",  "Log ESG activity data and emission records",         False),
    ("esg",  "edit",   "Edit ESG",    "Edit ESG factors, targets, and activity records",    False),
    ("esg",  "export", "Export ESG",  "Export ESG reports",                                 False),

    # ── Kenya Payroll ─────────────────────────────────────────────────────────
    ("payroll_ke", "view",    "View Payroll",      "View payroll runs and payslips",                      False),
    ("payroll_ke", "create",  "Create Payroll",    "Create and calculate payroll runs",                   False),
    ("payroll_ke", "approve", "Approve Payroll",   "Approve payroll runs for payment",                    False),
    ("payroll_ke", "export",  "Export Payroll",    "Export statutory reports and payslips",               False),
]

SCOPE_AWARE_PERMISSIONS = [
    # Inventory / warehouse scoped access
    ("inventory", "view_all", "View All Inventory", "View inventory across all allowed companies and warehouses", True),
    ("inventory", "view_own_scope", "View Scoped Inventory", "View inventory inside assigned operational scopes", True),
    ("inventory", "edit_all", "Edit All Inventory", "Edit inventory across all warehouses", False),
    ("inventory", "edit_own_scope", "Edit Scoped Inventory", "Edit inventory inside assigned warehouses only", False),
    ("inventory", "adjust_all", "Adjust All Inventory", "Adjust stock in all warehouses", False),
    ("inventory", "adjust_own_scope", "Adjust Scoped Inventory", "Adjust stock inside assigned warehouses only", False),
    ("inventory", "receive_all", "Receive All Inventory", "Receive stock into all warehouses", False),
    ("inventory", "receive_own_scope", "Receive Scoped Inventory", "Receive stock into assigned warehouses only", False),
    ("inventory", "dispatch_all", "Dispatch All Inventory", "Dispatch stock from all warehouses", False),
    ("inventory", "dispatch_own_scope", "Dispatch Scoped Inventory", "Dispatch stock from assigned warehouses only", False),
    ("inventory", "transfer_all", "Transfer All Inventory", "Transfer stock between all warehouses", False),
    ("inventory", "transfer_own_scope", "Transfer Scoped Inventory", "Transfer stock between assigned warehouses only", False),
    ("warehouses", "view_all", "View All Warehouses", "View all warehouse configuration", True),
    ("warehouses", "view_own_scope", "View Scoped Warehouses", "View assigned warehouse configuration", True),
    ("cycle_count", "perform_own_scope", "Perform Scoped Cycle Counts", "Perform cycle counts in assigned warehouses only", False),

    # Procurement
    ("procurement", "view_all", "View All Procurement", "View procurement across companies and branches", True),
    ("procurement", "view_own_scope", "View Scoped Procurement", "View procurement in assigned scope", True),
    ("procurement", "create_all", "Create All Procurement", "Create procurement documents across all scopes", False),
    ("procurement", "create_own_scope", "Create Scoped Procurement", "Create purchase documents in assigned scope", False),
    ("procurement", "edit_all", "Edit All Procurement", "Edit procurement documents across all scopes", False),
    ("procurement", "edit_own_scope", "Edit Scoped Procurement", "Edit purchase documents in assigned scope", False),
    ("procurement", "approve_all", "Approve All Procurement", "Approve procurement documents across all scopes", False),
    ("procurement", "approve_own_scope", "Approve Scoped Procurement", "Approve purchase documents in assigned scope", False),
    ("procurement", "receive_all", "Receive All Procurement", "Receive procurement goods across all scopes", False),
    ("procurement", "receive_own_scope", "Receive Scoped Procurement", "Receive procurement goods in assigned scope", False),
    ("procurement", "post_all", "Post All Procurement", "Post procurement receipts/payments across all scopes", False),
    ("procurement", "post_own_scope", "Post Scoped Procurement", "Post procurement receipts/payments in assigned scope", False),
    ("procurement", "cancel_all", "Cancel All Procurement", "Cancel procurement documents across all scopes", False),
    ("procurement", "cancel_own_scope", "Cancel Scoped Procurement", "Cancel procurement documents in assigned scope", False),
    ("procurement", "delete_all", "Delete All Procurement", "Delete procurement setup records across all scopes", False),
    ("procurement", "delete_own_scope", "Delete Scoped Procurement", "Delete procurement setup records in assigned scope", False),
    ("procurement", "export_all", "Export All Procurement", "Export procurement records across all scopes", False),
    ("procurement", "export_own_scope", "Export Scoped Procurement", "Export procurement records in assigned scope", False),
    ("procurement", "import_all", "Import All Procurement", "Import procurement records across all scopes", False),
    ("procurement", "import_own_scope", "Import Scoped Procurement", "Import procurement records in assigned scope", False),

    # Sales / CRM
    ("sales", "view_all", "View All Sales", "View all sales records", True),
    ("sales", "view_own_scope", "View Scoped Sales", "View sales records in assigned scope", True),
    ("sales", "create_all", "Create All Sales", "Create sales records across all commercial scopes", False),
    ("sales", "create_own_region", "Create Scoped Sales Region", "Create sales records in assigned region/team/customer scope", False),
    ("sales", "edit_all", "Edit All Sales", "Edit sales records across all commercial scopes", False),
    ("sales", "edit_own_region", "Edit Scoped Sales Region", "Edit sales records in assigned region/team/customer scope", False),
    ("sales", "approve_all", "Approve All Sales", "Approve commercial sales records across all scopes", False),
    ("sales", "approve_own_region", "Approve Scoped Sales Region", "Approve commercial sales records in assigned region/team/customer scope", False),
    ("sales", "cancel_all", "Cancel All Sales", "Cancel sales records across all commercial scopes", False),
    ("sales", "cancel_own_region", "Cancel Scoped Sales Region", "Cancel sales records in assigned region/team/customer scope", False),
    ("sales", "convert_all", "Convert All Sales", "Convert commercial documents across all commercial scopes", False),
    ("sales", "convert_own_region", "Convert Scoped Sales Region", "Convert commercial documents in assigned region/team/customer scope", False),
    ("crm", "view_all", "View All CRM", "View all CRM/customer records", True),
    ("crm", "view_own_region", "View Scoped CRM Region", "View CRM records in assigned region/team/customer scope", True),
    ("crm", "create_all", "Create All CRM", "Create CRM records across all commercial scopes", False),
    ("crm", "create_own_region", "Create Scoped CRM Region", "Create CRM records in assigned region/team/customer scope", False),
    ("crm", "edit_all", "Edit All CRM", "Edit CRM records across all commercial scopes", False),
    ("crm", "edit_own_region", "Edit Scoped CRM Region", "Edit CRM records in assigned region/team/customer scope", False),
    ("crm", "cancel_all", "Cancel All CRM", "Cancel CRM records across all commercial scopes", False),
    ("crm", "cancel_own_region", "Cancel Scoped CRM Region", "Cancel CRM records in assigned region/team/customer scope", False),
    ("crm", "convert_all", "Convert All CRM", "Convert CRM records across all commercial scopes", False),
    ("crm", "convert_own_region", "Convert Scoped CRM Region", "Convert CRM records in assigned region/team/customer scope", False),
    ("pricing", "request_discount", "Request Discount", "Request a sales discount approval", False),
    ("pricing", "approve", "Approve Pricing", "Approve pricing and discount exceptions", False),

    # Production / MRP
    ("production", "view_all", "View All Production", "View all production orders and plans", True),
    ("production", "view_own_scope", "View Scoped Production", "View production in assigned factory/line scope", True),
    ("production", "create_all", "Create All Production", "Create production orders in any factory/warehouse scope", False),
    ("production", "create_own_scope", "Create Scoped Production", "Create production orders in assigned factory/line scope", False),
    ("production", "edit_own_scope", "Edit Scoped Production", "Edit production in assigned factory/line scope", False),
    ("production", "release_own_scope", "Release Scoped Production", "Release production orders in assigned factory/line scope", False),
    ("production", "close_own_scope", "Close Scoped Production", "Close production orders in assigned factory/line scope", False),
    ("production", "cancel_own_scope", "Cancel Scoped Production", "Cancel production orders in assigned factory/line scope", False),
    ("mrp", "view_all", "View All MRP", "View MRP runs and suggestions across factories", True),
    ("mrp", "run_own_scope", "Run Scoped MRP", "Run MRP in assigned factory/warehouse scope", False),
    ("planning", "view_all", "View All APS Planning", "View APS scenarios, capacity boards, and bottlenecks across factories", True),
    ("planning", "view_own_scope", "View Scoped APS Planning", "View APS planning data in assigned factory/line scope", True),
    ("planning", "create_all", "Create All APS Planning", "Create APS scenarios across all planning scopes", False),
    ("planning", "create_own_scope", "Create Scoped APS Planning", "Create APS scenarios in assigned planning scope", False),
    ("planning", "edit_all", "Edit All APS Planning", "Edit APS scenarios, calendars, and changeover rules across all scopes", False),
    ("planning", "edit_own_scope", "Edit Scoped APS Planning", "Edit APS planning records in assigned scope", False),
    ("planning", "calculate_all", "Calculate All APS Planning", "Run APS scheduling calculations across all scopes", False),
    ("planning", "calculate_own_scope", "Calculate Scoped APS Planning", "Run APS scheduling calculations in assigned scope", False),
    ("planning", "approve_all", "Approve All APS Planning", "Activate, lock, publish, and approve APS planning outputs across all scopes", False),
    ("planning", "approve_own_scope", "Approve Scoped APS Planning", "Activate, lock, publish, and approve APS planning outputs in assigned scope", False),
    ("bom", "view_all", "View All BOM", "View all BOM/formula records", True),
    ("recipe", "view_all", "View All Recipes", "View all recipe records", True),

    # Quality / traceability
    ("quality", "view_all", "View All Quality", "View all quality records", True),
    ("quality", "view_own_scope", "View Scoped Quality", "View quality records in assigned scope", True),
    ("quality", "create_all", "Create All Quality", "Create quality records across all scopes", False),
    ("quality", "create_own_scope", "Create Scoped Quality", "Create quality records in assigned scope", False),
    ("quality", "edit_all", "Edit All Quality", "Edit quality records across all scopes", False),
    ("quality", "edit_own_scope", "Edit Scoped Quality", "Edit quality records in assigned scope", False),
    ("quality", "approve_own_scope", "Approve Scoped Quality", "Approve quality records in assigned scope", False),
    ("quality", "release_own_scope", "Release Scoped Quality", "Release lots in assigned quality scope", False),
    ("qms", "view_all", "View All QMS", "View all QMS records", True),
    ("qms", "edit_own_scope", "Edit Scoped QMS", "Edit QMS records in assigned scope", False),
    ("qms", "manage_haccp", "Manage HACCP", "Manage HACCP configuration and controls", False),
    ("traceability", "view_all", "View All Traceability", "View all traceability records", True),
    ("traceability", "recall_initiate", "Initiate Recall", "Initiate product recall workflows", False),
    ("traceability", "recall_close", "Close Recall", "Close product recall workflows", False),
    ("traceability", "regulatory_export", "Export Regulatory Traceability", "Export regulatory traceability reports", False),

    # Finance
    ("finance", "view_all", "View All Finance", "View finance records across companies", False),
    ("finance", "view_own_scope", "View Scoped Finance", "View finance records inside assigned company/branch/cost center", False),
    ("finance", "create_all", "Create All Finance", "Create finance records across companies", False),
    ("finance", "create_own_scope", "Create Scoped Finance", "Create finance records inside assigned company/branch/cost center", False),
    ("finance", "edit_all", "Edit All Finance", "Edit finance records across companies", False),
    ("finance", "edit_own_scope", "Edit Scoped Finance", "Edit finance records inside assigned company/branch/cost center", False),
    ("finance", "post_all", "Post All Finance", "Post finance records across companies", False),
    ("finance", "post_own_scope", "Post Scoped Finance", "Post finance records inside assigned company/branch/cost center", False),
    ("bank_reconciliation", "manage_own_scope", "Manage Scoped Bank Reconciliation", "Manage bank reconciliation in assigned company/bank scope", False),
    ("invoice_match", "approve_own_scope", "Approve Scoped Invoice Match", "Approve matched invoices in assigned company scope", False),

    # HR / payroll
    ("hr", "view_own_scope", "View Scoped HR", "View HR records inside assigned company/branch/department", False),
    ("hr", "edit_own_scope", "Edit Scoped HR", "Edit HR records inside assigned company/branch/department", False),
    ("employees", "view_own_scope", "View Scoped Employees", "View employees inside assigned department scope", False),
    ("payroll", "view", "View Payroll", "View payroll records", False),
    ("payroll", "manage_own_scope", "Manage Scoped Payroll", "Manage payroll in assigned company/branch/department", False),

    # Maintenance / utilities / IoT
    ("maintenance", "view_all", "View All Maintenance", "View all maintenance assets and work orders", True),
    ("maintenance", "edit_own_scope", "Edit Scoped Maintenance", "Edit maintenance records in assigned machine/factory scope", False),
    ("utilities", "view_all", "View All Utilities", "View all utility assets/readings", False),
    ("utilities", "edit_own_scope", "Edit Scoped Utilities", "Edit utility records in assigned utility area/factory scope", False),
    ("iot", "manage", "Manage IoT", "Manage IoT device configuration", False),

    # Administration / audit
    ("users", "manage", "Manage Users", "Manage user lifecycle and assignments", False),
    ("roles", "manage", "Manage Roles", "Manage roles, permissions, and scopes", False),
    ("company", "manage", "Manage Company Setup", "Manage company and branch setup", False),
    ("auditor", "export", "Export Audit Reports", "Export auditor-approved reports", False),
    ("shop_floor", "view_own_scope", "View Scoped Shop Floor", "View assigned shop-floor execution scope", True),
    ("production_execution", "update_own_line", "Update Own Production Line", "Update execution records on assigned line", False),
]

PERMISSIONS.extend(SCOPE_AWARE_PERMISSIONS)


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
            "documents.view", "documents.create", "documents.edit", "documents.approve", "documents.archive", "documents.export",
            "knowledge_base.view", "knowledge_base.create", "knowledge_base.edit", "knowledge_base.publish", "knowledge_base.delete", "knowledge_base.admin",
            "esign.view", "esign.request", "esign.sign", "esign.cancel", "esign.admin",
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
            "documents.view", "documents.approve", "documents.archive", "documents.export",
            "knowledge_base.view", "esign.view",
            "audit.view", "audit.export",
            "integrations.view",
            "analytics.view", "analytics.export",
            "marketing_analytics.view",
            "ai.view", "ai.create", "ai.edit", "ai.approve",
            "planning.view_all", "planning.calculate_all", "planning.approve_all",
            "utility_management.view",
            "fleet.view",
            "cycle_count.view",
            "esg.view", "esg.export",
            "payroll_ke.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "coo": {
        "description": "Chief Operating Officer — broad operational oversight",
        "permissions": [
            "production.view", "production.create", "production.edit", "production.approve",
            "planning.view_all", "planning.create_own_scope", "planning.edit_own_scope",
            "planning.calculate_own_scope", "planning.approve_own_scope",
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
            "documents.view", "knowledge_base.view", "esign.view",
            "analytics.view",
            "audit.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },
    "cfo": {
        "description": "Chief Financial Officer — full financial and compliance oversight",
        "permissions": [
            "finance.view", "finance.create", "finance.edit", "finance.approve", "finance.export", "finance.configure",
            "finance.post_all",
            "mpesa.initiate_payment", "mpesa.view_transactions", "mpesa.retry_transaction",
            "mpesa.cancel_payment", "mpesa.reconcile_payment", "mpesa.view_payment_logs",
            "tax.view", "tax.edit",
            "procurement.view", "procurement.approve",
            "sales.view",
            "inventory.view",
            "hr.view", "hr.approve",
            "documents.view", "knowledge_base.view", "esign.view",
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
        "description": "Chief Technology Officer — integrations, system config, AI, and full import authority",
        "permissions": [
            "integrations.view", "integrations.edit", "integrations.webhooks",
            "users.view", "users.create", "users.edit",
            "roles.view", "roles.create", "roles.edit",
            "audit.view", "audit.export",
            # CTO manages system utilities (configs, UOM, number series, currencies)
            "utilities.view", "utilities.edit", "utilities.manage",
            # Full AI access
            "ai.view", "ai.create", "ai.edit", "ai.approve",
            # Read-only visibility across all operational modules
            "production.view", "procurement.view", "inventory.view",
            "planning.view_all",
            "logistics.view", "quality.view", "maintenance.view",
            "warehouses.view", "wms.view", "materials.view", "products.view",
            "sales.view", "finance.view", "tax.view", "hr.view",
            "documents.view", "knowledge_base.view", "knowledge_base.create", "knowledge_base.edit",
            "knowledge_base.publish", "knowledge_base.admin",
            "esign.view", "esign.request", "esign.sign", "esign.cancel", "esign.admin",
            "mpesa.view_transactions", "mpesa.view_payment_logs",
            "analytics.view",
            "utility_management.view",
            "fleet.view", "cycle_count.view",
            "esg.view",
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
            "crm.view_all", "crm.create_all", "crm.edit_all", "crm.cancel_all", "crm.convert_all",
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
            "sales.view_all", "sales.create_all", "sales.edit_all", "sales.approve_all", "sales.cancel_all", "sales.convert_all",
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
        "description": "Data Manager — bulk import, AI analytics, and template authority across all enabled modules",
        "permissions": [
            # Read access to every module (needed to validate imports)
            "inventory.view", "products.view", "materials.view",
            "production.view", "planning.view_all", "procurement.view", "sales.view",
            "finance.view", "logistics.view", "quality.view",
            "maintenance.view", "warehouses.view", "wms.view",
            "hr.view", "tax.view", "users.view",
            "documents.view", "knowledge_base.view", "esign.view",
            "audit.view",
            "analytics.view",
            "ai.view", "ai.create",
            "esg.view",
            # Full bulk-import authority across all modules
            *_ALL_IMPORT_PERMS,
        ],
    },

    # ── Operational roles (module-scoped import only) ─────────────────────────
    "finance_manager": {
        "description": "Full finance and M-Pesa access",
        "permissions": [
            "finance.view", "finance.create", "finance.edit", "finance.approve", "finance.export", "finance.configure",
            "finance.post_all",
            "mpesa.initiate_payment", "mpesa.view_transactions", "mpesa.retry_transaction",
            "mpesa.cancel_payment", "mpesa.reconcile_payment", "mpesa.view_payment_logs",
            "payroll_ke.view", "payroll_ke.create", "payroll_ke.approve", "payroll_ke.export",
            "sales.view",
            # Import: own module only
            *_import("finance"),
        ],
    },
    "sales_manager": {
        "description": "Sales operations and limited payment initiation",
        "permissions": [
            "sales.view", "sales.create", "sales.edit",
            "sales.view_all", "sales.create_own_region", "sales.edit_own_region",
            "sales.approve_own_region", "sales.cancel_own_region", "sales.convert_own_region",
            "crm.view_all", "crm.create_own_region", "crm.edit_own_region",
            "crm.cancel_own_region", "crm.convert_own_region",
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
            "stock_movement.edit", "stock_movement.delete",
            "cycle_count.view", "cycle_count.create", "cycle_count.approve",
            # Import: own module only
            *_import("inventory", "warehouses", "wms"),
        ],
    },
    "production_supervisor": {
        "description": "Production planning and execution",
        "permissions": [
            "production.view", "production.create", "production.edit", "production.approve",
            "planning.view_own_scope", "planning.create_own_scope", "planning.edit_own_scope",
            "planning.calculate_own_scope",
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
            "documents.view", "documents.create", "knowledge_base.view", "esign.sign",
            # Import: own module only
            *_import("quality"),
        ],
    },
    "logistics_officer": {
        "description": "Logistics, shipments, and customs documentation",
        "permissions": [
            "logistics.view", "logistics.create", "logistics.edit",
            "procurement.view", "inventory.view",
            "documents.view", "documents.create", "knowledge_base.view", "esign.sign",
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
            "payroll_ke.view", "payroll_ke.create", "payroll_ke.approve", "payroll_ke.export",
            "users.view",
            "documents.view", "documents.create", "knowledge_base.view", "esign.sign",
            # Import: own module only
            *_import("hr"),
        ],
    },

    "company_admin": {
        "description": "Company administrator with company-scoped administrative authority",
        "permissions": [
            "users.view", "users.manage", "roles.view", "company.manage",
            "inventory.view_all", "production.view_all", "quality.view_all",
            "planning.view_all",
            "sales.view_all", "finance.view_own_scope", "procurement.view_all",
            "hr.view_own_scope", "maintenance.view_all", "utilities.view_all",
        ],
    },
    "factory_manager": {
        "description": "Factory manager with broad operational visibility and scoped factory mutation",
        "permissions": [
            "production.view_all", "inventory.view_all", "quality.view_all",
            "maintenance.view_all", "utilities.view_all",
            "planning.view_all", "planning.create_own_scope", "planning.edit_own_scope",
            "planning.calculate_own_scope", "planning.approve_own_scope",
            "production.create_own_scope", "production.edit_own_scope", "production.release_own_scope",
            "production.close_own_scope", "production.cancel_own_scope",
            "quality.approve_own_scope", "maintenance.edit_own_scope",
        ],
    },
    "warehouse_manager": {
        "description": "Warehouse manager with all-stock visibility and assigned-warehouse mutation",
        "permissions": [
            "inventory.view_all", "warehouses.view_all", "wms.view", "products.view", "materials.view",
            "inventory.edit_own_scope", "inventory.adjust_own_scope",
            "inventory.receive_own_scope", "inventory.dispatch_own_scope",
            "inventory.transfer_own_scope",
            "cycle_count.perform_own_scope",
        ],
    },
    "production_manager": {
        "description": "Production manager with all-order visibility and assigned factory/line control",
        "permissions": [
            "production.view_all", "mrp.view_all", "bom.view_all", "recipe.view_all",
            "planning.view_all", "planning.create_own_scope", "planning.edit_own_scope",
            "planning.calculate_own_scope", "planning.approve_own_scope",
            "production.create_own_scope", "production.edit_own_scope", "production.release_own_scope",
            "production.close_own_scope", "production.cancel_own_scope", "mrp.run_own_scope",
        ],
    },
    "quality_manager": {
        "description": "Quality manager with broad QMS visibility and scoped release approval",
        "permissions": [
            "quality.view_all", "qms.view_all", "traceability.view_all",
            "quality.create_own_scope", "quality.edit_own_scope",
            "quality.approve_own_scope", "quality.release_own_scope",
            "qms.edit_own_scope", "traceability.recall_initiate",
        ],
    },
    "procurement_manager": {
        "description": "Procurement manager with supplier visibility and scoped purchasing control",
        "permissions": [
            "procurement.view_all", "procurement.create_own_scope",
            "procurement.edit_own_scope", "procurement.approve_own_scope",
            "procurement.receive_own_scope", "procurement.post_own_scope",
            "procurement.cancel_own_scope", "procurement.export_own_scope",
            "procurement.import_own_scope",
            "materials.view", "inventory.view_all",
        ],
    },
    "regional_sales_manager": {
        "description": "Sales manager with all-customer visibility and scoped regional mutation",
        "permissions": [
            "sales.view_all", "crm.view_all",
            "sales.create_own_region", "sales.edit_own_region",
            "sales.approve_own_region", "sales.cancel_own_region", "sales.convert_own_region",
            "crm.create_own_region", "crm.edit_own_region",
            "crm.cancel_own_region", "crm.convert_own_region",
            "pricing.request_discount",
        ],
    },
    "scoped_finance_manager": {
        "description": "Finance manager with scoped company/branch posting authority",
        "permissions": [
            "finance.view_own_scope", "finance.create_own_scope", "finance.edit_own_scope",
            "finance.post_own_scope",
            "bank_reconciliation.manage_own_scope", "invoice_match.approve_own_scope",
            "finance.export",
        ],
    },
    "scoped_hr_manager": {
        "description": "HR manager with scoped department and payroll authority",
        "permissions": [
            "hr.view_own_scope", "employees.view_own_scope",
            "hr.edit_own_scope", "payroll.view", "payroll.manage_own_scope",
        ],
    },
    "read_only_auditor": {
        "description": "Read-only auditor with assigned-scope visibility and optional export",
        "permissions": [
            "inventory.view_own_scope", "production.view_own_scope", "quality.view_own_scope",
            "planning.view_own_scope", "sales.view_own_scope", "finance.view_own_scope", "procurement.view_own_scope",
            "audit.view", "auditor.export",
        ],
    },
    "shop_floor_operator": {
        "description": "Operator with limited assigned-line execution authority",
        "permissions": [
            "shop_floor.view_own_scope", "production_execution.update_own_line",
            "production.view_own_scope", "planning.view_own_scope",
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


FULL_SCOPE_ACTIONS = {
    "can_view": True,
    "can_create": True,
    "can_edit": True,
    "can_delete": True,
    "can_approve": True,
    "can_post": True,
    "can_release": True,
    "can_cancel": True,
    "can_export": True,
    "can_import": True,
    "can_transfer": True,
    "can_adjust": True,
    "can_receive": True,
    "can_dispatch": True,
}

DEFAULT_ROLE_ACCESS_SCOPES = {
    "owner": [
        {"scope_type": "global", "scope_id": "ALL", "scope_name": "All ERP scopes", **FULL_SCOPE_ACTIONS},
    ],
    "admin": [
        {"scope_type": "global", "scope_id": "ALL", "scope_name": "All ERP scopes", **FULL_SCOPE_ACTIONS},
    ],
}


async def seed_admin(db: AsyncSession) -> None:
    """Seed permissions, predefined roles, and the default admin user."""

    # ── 1. Batch-upsert all permissions (single round-trip) ───────────────────
    permission_defs = {
        f"{module}.{action}": (module, action, name, description, is_mobile)
        for module, action, name, description, is_mobile in PERMISSIONS
    }
    for module in MODULE_DEFINITIONS:
        for action in module.permission_actions:
            code = f"{module.key}.{action}"
            permission_defs.setdefault(
                code,
                (
                    module.key,
                    action,
                    f"{action.replace('_', ' ').title()} {module.label}",
                    f"{action.replace('_', ' ').title()} permission for {module.label}",
                    False,
                ),
            )

    perm_rows = [
        {
            "code": f"{module}.{action}",
            "name": name,
            "description": description,
            "module": module,
            "action": action,
            "is_active": True,
            "is_mobile_visible": is_mobile,
        }
        for module, action, name, description, is_mobile in permission_defs.values()
    ]
    await db.execute(
        pg_insert(Permission).values(perm_rows).on_conflict_do_nothing(index_elements=["code"])
    )
    await db.flush()

    result = await db.execute(select(Permission))
    perm_map: dict[str, Permission] = {p.code: p for p in result.scalars().all()}
    all_perm_ids = [p.id for p in perm_map.values()]

    # ── 2. Batch-upsert all roles, then assign permissions ────────────────────
    role_rows = [
        {"name": rname, "description": rdef["description"], "is_system_role": True}
        for rname, rdef in ROLE_DEFINITIONS.items()
    ]
    role_insert = pg_insert(Role).values(role_rows)
    await db.execute(
        role_insert.on_conflict_do_update(
            index_elements=["name"],
            set_={
                "description": role_insert.excluded.description,
                "is_system_role": True,
            },
        )
    )
    await db.flush()

    result = await db.execute(select(Role))
    role_map: dict[str, Role] = {r.name: r for r in result.scalars().all()}

    for role_name, role_def in ROLE_DEFINITIONS.items():
        role = role_map.get(role_name)
        if not role:
            continue

        if role_def["permissions"] == "*":
            perm_ids = all_perm_ids
        else:
            perm_ids = [perm_map[c].id for c in role_def["permissions"] if c in perm_map]

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
    default_scope_role_ids = [
        role_map[role_name].id
        for role_name in DEFAULT_ROLE_ACCESS_SCOPES
        if role_name in role_map
    ]
    if default_scope_role_ids:
        await db.execute(
            delete(AccessScope).where(
                AccessScope.role_id.in_(default_scope_role_ids),
                AccessScope.user_id.is_(None),
                AccessScope.scope_type == "global",
                AccessScope.scope_id == "ALL",
            )
        )
        scope_rows = []
        for role_name, scopes in DEFAULT_ROLE_ACCESS_SCOPES.items():
            role = role_map.get(role_name)
            if not role:
                continue
            for scope in scopes:
                scope_rows.append({"id": uuid.uuid4(), "role_id": role.id, **scope})
        if scope_rows:
            await db.execute(insert(AccessScope), scope_rows)
        await db.flush()

    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar_one()
    if user_count > 0:
        await db.commit()
        return
    if not settings.SEED_INITIAL_ADMIN:
        logger.info("Initial admin seed disabled; no user accounts were created.")
        await db.commit()
        return
    if not settings.INITIAL_ADMIN_PASSWORD:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD is required before creating the first admin user.")

    owner_result = await db.execute(select(Role).where(Role.name == "owner"))
    owner_role = owner_result.scalar_one_or_none()

    admin = User(
        email=settings.INITIAL_ADMIN_EMAIL,
        username=settings.INITIAL_ADMIN_USERNAME,
        full_name=settings.INITIAL_ADMIN_FULL_NAME,
        hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
        must_change_password=True,
    )
    db.add(admin)
    await db.flush()

    if owner_role:
        await db.execute(
            insert(user_role).values(user_id=admin.id, role_id=owner_role.id)
        )

    logger.info("=" * 50)
    logger.info("  INITIAL ADMIN USER CREATED")
    logger.info("  username : %s", settings.INITIAL_ADMIN_USERNAME)
    logger.info("  email    : %s", settings.INITIAL_ADMIN_EMAIL)
    logger.info("  password : configured via INITIAL_ADMIN_PASSWORD")
    logger.info("=" * 50)

    # ── 4. Seed demo C-suite users ─────────────────────────────────────────────
    if not settings.SEED_DEMO_DATA:
        await db.commit()
        return
    if not settings.DEMO_USER_PASSWORD:
        raise RuntimeError("DEMO_USER_PASSWORD is required when SEED_DEMO_DATA=true.")
    for demo in DEMO_USERS:
        role_result = await db.execute(select(Role).where(Role.name == demo["role"]))
        demo_role = role_result.scalar_one_or_none()

        demo_user = User(
            email=demo["email"],
            username=demo["username"],
            full_name=demo["full_name"],
            hashed_password=hash_password(settings.DEMO_USER_PASSWORD),
            is_active=True,
            is_superuser=False,
            must_change_password=True,
        )
        db.add(demo_user)
        await db.flush()

        if demo_role:
            await db.execute(
                insert(user_role).values(user_id=demo_user.id, role_id=demo_role.id)
            )

        logger.info("  DEMO USER: username=%s  role=%s", demo["username"], demo["role"])

    await db.commit()
