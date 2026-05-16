from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
import logging
from typing import Iterable

from fastapi import APIRouter

from app.core.ai_modes import AIMode, MODULE_AI_MODES


logger = logging.getLogger(__name__)
DEFAULT_ACTIONS = ("view", "create", "edit", "delete", "export")

SCOPED_PERMISSION_ACTION_ALIASES: dict[str, tuple[str, ...]] = {
    "view": (
        "view_all",
        "view_own_scope",
        "view_own_company",
        "view_own_branch",
        "view_own_warehouse",
        "view_own_factory",
        "view_own_line",
        "view_own_department",
        "view_own_region",
        "view_own_category",
    ),
    "create": ("create_all", "create_own_scope"),
    "edit": (
        "edit_all",
        "edit_own_scope",
        "edit_own_company",
        "edit_own_branch",
        "edit_own_warehouse",
        "edit_own_factory",
        "edit_own_line",
        "edit_own_department",
        "edit_own_region",
        "edit_own_category",
    ),
    "delete": ("delete_all", "delete_own_scope"),
    "approve": ("approve_all", "approve_own_scope"),
    "post": ("post_all", "post_own_scope", "post_own_company"),
    "release": ("release_all", "release_own_scope", "release_own_factory"),
    "close": ("close_all", "close_own_scope", "close_own_factory"),
    "cancel": ("cancel_all", "cancel_own_scope"),
    "adjust": ("adjust_all", "adjust_own_scope"),
    "receive": ("receive_all", "receive_own_scope"),
    "dispatch": ("dispatch_all", "dispatch_own_scope"),
    "transfer": ("transfer_all", "transfer_own_scope"),
    "export": ("export_all", "export_own_scope"),
    "import": ("import_all", "import_own_scope"),
}


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    label: str
    route_prefix: str
    import_path: str
    permission_actions: tuple[str, ...]
    sidebar_group: str
    icon_key: str
    ai_mode: str
    enabled: bool = True
    critical: bool = False

    @property
    def permission_codes(self) -> tuple[str, ...]:
        return tuple(f"{self.key}.{action}" for action in self.permission_actions)

    def to_manifest(self) -> dict:
        data = asdict(self)
        data["permission_actions"] = list(self.permission_actions)
        data["permission_codes"] = list(self.permission_codes)
        return data


@dataclass(frozen=True)
class EndpointRouteDefinition:
    key: str
    route_prefix: str
    import_path: str
    tags: tuple[str, ...]
    enabled: bool = True
    critical: bool = True


MODULE_DEFINITIONS: tuple[ModuleDefinition, ...] = (
    ModuleDefinition(
        key="users",
        label="Users",
        route_prefix="/users",
        import_path="app.api.v1.endpoints.users",
        permission_actions=("view", "create", "edit", "delete"),
        sidebar_group="Administration",
        icon_key="users",
        ai_mode=AIMode.RULE_BASED,
        critical=True,
    ),
    ModuleDefinition(
        key="roles",
        label="Roles",
        route_prefix="/roles",
        import_path="app.api.v1.endpoints.roles",
        permission_actions=("view", "create", "edit", "delete"),
        sidebar_group="Administration",
        icon_key="shield",
        ai_mode=AIMode.RULE_BASED,
        critical=True,
    ),
    ModuleDefinition(
        key="inventory",
        label="Inventory",
        route_prefix="/inventory",
        import_path="app.api.v1.endpoints.inventory",
        permission_actions=DEFAULT_ACTIONS,
        sidebar_group="Supply Chain",
        icon_key="boxes",
        ai_mode=MODULE_AI_MODES.get("inventory", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="production",
        label="Production",
        route_prefix="/production",
        import_path="app.api.v1.endpoints.production",
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="Manufacturing",
        icon_key="factory",
        ai_mode=MODULE_AI_MODES.get("production", AIMode.STATISTICAL),
        critical=True,
    ),
    ModuleDefinition(
        key="planning",
        label="Advanced Planning",
        route_prefix="/planning",
        import_path="app.api.v1.endpoints.planning",
        permission_actions=("view", "create", "edit", "approve", "calculate", "export"),
        sidebar_group="Manufacturing",
        icon_key="calendar-range",
        ai_mode=MODULE_AI_MODES.get("planning", AIMode.STATISTICAL),
        critical=True,
    ),
    ModuleDefinition(
        key="npd",
        label="New Product Development",
        route_prefix="/npd-workflow",
        import_path="app.api.v1.endpoints.npd_workflow",
        permission_actions=("view", "create", "edit", "approve", "advance", "pilot", "export"),
        sidebar_group="Manufacturing",
        icon_key="flask-conical",
        ai_mode=MODULE_AI_MODES.get("npd", AIMode.HYBRID),
        critical=True,
    ),
    ModuleDefinition(
        key="bom",
        label="Advanced BOM / Formula",
        route_prefix="/bom",
        import_path="app.api.v1.endpoints.bom",
        permission_actions=("view", "create", "edit", "delete", "approve", "release", "archive", "cost", "ai", "export"),
        sidebar_group="Manufacturing",
        icon_key="layers",
        ai_mode=MODULE_AI_MODES.get("bom", AIMode.HYBRID),
        critical=True,
    ),
    ModuleDefinition(
        key="recipe",
        label="Recipes",
        route_prefix="/recipes",
        import_path="app.api.v1.endpoints.recipes",
        permission_actions=("view", "create", "edit", "delete", "approve", "obsolete", "export"),
        sidebar_group="Manufacturing",
        icon_key="book-open-check",
        ai_mode=MODULE_AI_MODES.get("recipe", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="procurement",
        label="Procurement",
        route_prefix="/procurement",
        import_path="app.api.v1.endpoints.procurement",
        permission_actions=("view", "create", "edit", "delete", "approve", "receive", "post", "cancel", "export", "import"),
        sidebar_group="Supply Chain",
        icon_key="shopping-cart",
        ai_mode=MODULE_AI_MODES.get("procurement", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="sales",
        label="Sales",
        route_prefix="/sales",
        import_path="app.api.v1.endpoints.sales",
        permission_actions=("view", "create", "edit", "approve", "cancel", "convert", "export", "import"),
        sidebar_group="Commercial",
        icon_key="receipt",
        ai_mode=MODULE_AI_MODES.get("sales", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="crm",
        label="CRM",
        route_prefix="/crm",
        import_path="app.api.v1.endpoints.crm_pipeline",
        permission_actions=("view", "create", "edit", "delete", "approve", "cancel", "convert", "export", "import"),
        sidebar_group="Commercial",
        icon_key="handshake",
        ai_mode=MODULE_AI_MODES.get("crm", AIMode.HYBRID),
        critical=True,
    ),
    ModuleDefinition(
        key="finance",
        label="Finance",
        route_prefix="/finance",
        import_path="app.api.v1.endpoints.finance",
        permission_actions=("view", "create", "edit", "approve", "export", "configure"),
        sidebar_group="Finance",
        icon_key="wallet",
        ai_mode=MODULE_AI_MODES.get("finance", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="hr",
        label="Human Resources",
        route_prefix="/hr",
        import_path="app.api.v1.endpoints.hr",
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="HR & Payroll",
        icon_key="users-round",
        ai_mode=MODULE_AI_MODES.get("hr", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="payroll_ke",
        label="Kenya Payroll",
        route_prefix="/payroll-ke",
        import_path="app.api.v1.endpoints.payroll_ke",
        permission_actions=("view", "create", "approve", "export"),
        sidebar_group="HR & Payroll",
        icon_key="banknote",
        ai_mode=MODULE_AI_MODES.get("payroll_ke", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="quality",
        label="Quality",
        route_prefix="/quality",
        import_path="app.api.v1.endpoints.quality",
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="Manufacturing",
        icon_key="clipboard-check",
        ai_mode=MODULE_AI_MODES.get("quality", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="consumer_complaints",
        label="Consumer Complaints",
        route_prefix="/consumer-complaints",
        import_path="app.api.v1.endpoints.consumer_complaints",
        permission_actions=("view", "create", "edit", "delete", "approve", "close", "link_recall", "export"),
        sidebar_group="Quality & Compliance",
        icon_key="message-square-warning",
        ai_mode=MODULE_AI_MODES.get("consumer_complaints", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="gs1",
        label="GS1 / Label Printing",
        route_prefix="/gs1",
        import_path="app.api.v1.endpoints.gs1",
        permission_actions=("view", "create", "edit", "approve", "print", "report", "admin"),
        sidebar_group="Compliance",
        icon_key="barcode",
        ai_mode=MODULE_AI_MODES.get("gs1", AIMode.RULE_BASED),
        critical=False,
    ),
    ModuleDefinition(
        key="maintenance",
        label="Maintenance",
        route_prefix="/maintenance",
        import_path="app.api.v1.endpoints.maintenance",
        permission_actions=("view", "create", "edit", "delete", "predict", "review_prediction", "export"),
        sidebar_group="Factory Operations",
        icon_key="wrench",
        ai_mode=MODULE_AI_MODES.get("maintenance", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="utilities",
        label="Utilities",
        route_prefix="/utilities",
        import_path="app.api.v1.endpoints.utilities",
        permission_actions=DEFAULT_ACTIONS,
        sidebar_group="Factory Operations",
        icon_key="gauge",
        ai_mode=MODULE_AI_MODES.get("utilities", AIMode.HYBRID),
        critical=True,
    ),
    ModuleDefinition(
        key="reports",
        label="Report Builder",
        route_prefix="/reports-builder",
        import_path="app.api.v1.endpoints.report_builder",
        permission_actions=("view", "create", "edit", "run", "export", "admin"),
        sidebar_group="Analytics",
        icon_key="bar-chart",
        ai_mode=MODULE_AI_MODES.get("reports", AIMode.RULE_BASED),
        critical=False,
    ),
    ModuleDefinition(
        key="notifications",
        label="Notification Center",
        route_prefix="/notifications",
        import_path="app.api.v1.endpoints.notifications",
        permission_actions=("view", "manage", "send", "configure", "report", "admin"),
        sidebar_group="Communication",
        icon_key="bell",
        ai_mode=MODULE_AI_MODES.get("notifications", AIMode.RULE_BASED),
        critical=False,
    ),
    ModuleDefinition(
        key="documents",
        label="Documents",
        route_prefix="/documents",
        import_path="app.api.v1.endpoints.documents",
        permission_actions=("view", "create", "edit", "approve", "archive", "export"),
        sidebar_group="Administration",
        icon_key="file-text",
        ai_mode=MODULE_AI_MODES.get("documents", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="knowledge_base",
        label="Knowledge Base",
        route_prefix="/kb",
        import_path="app.api.v1.endpoints.knowledge_base",
        permission_actions=("view", "create", "edit", "publish", "delete", "admin"),
        sidebar_group="Administration",
        icon_key="book-open",
        ai_mode=MODULE_AI_MODES.get("knowledge_base", AIMode.RULE_BASED),
        critical=False,
    ),
    ModuleDefinition(
        key="esign",
        label="Electronic Signatures",
        route_prefix="/esign",
        import_path="app.api.v1.endpoints.esign",
        permission_actions=("view", "request", "sign", "cancel", "admin"),
        sidebar_group="Administration",
        icon_key="signature",
        ai_mode=MODULE_AI_MODES.get("esign", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="ai",
        label="AI & Intelligence",
        route_prefix="/ai",
        import_path="app.api.v1.endpoints.ai",
        permission_actions=("view", "create", "edit", "approve", "export", "configure"),
        sidebar_group="Intelligence",
        icon_key="brain",
        ai_mode=AIMode.LLM_POWERED,
        critical=False,
    ),
    ModuleDefinition(
        key="shelf_life",
        label="Shelf-Life / FEFO",
        route_prefix="/shelf-life",
        import_path="app.api.v1.endpoints.shelf_life",
        permission_actions=("view", "create", "edit", "approve", "hold", "dispose", "report"),
        sidebar_group="Supply Chain",
        icon_key="calendar-clock",
        ai_mode=MODULE_AI_MODES.get("shelf_life", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="iot",
        label="IoT / Machine Streaming",
        route_prefix="/iot",
        import_path="app.api.v1.endpoints.iot",
        permission_actions=("view", "ingest", "configure", "acknowledge", "export", "admin"),
        sidebar_group="Operations",
        icon_key="radio-tower",
        ai_mode=MODULE_AI_MODES.get("iot", AIMode.RULE_BASED),
        critical=False,
    ),
    ModuleDefinition(
        key="company",
        label="Company & Branches",
        route_prefix="/companies",
        import_path="app.api.v1.endpoints.company",
        permission_actions=("view", "create", "edit", "delete", "export", "manage"),
        sidebar_group="Administration",
        icon_key="building",
        ai_mode=AIMode.RULE_BASED,
        critical=True,
    ),
)


ENDPOINT_ROUTE_DEFINITIONS: tuple[EndpointRouteDefinition, ...] = (
    EndpointRouteDefinition(key="health", route_prefix="/health", import_path="app.api.v1.endpoints.health", tags=('health',)),
    EndpointRouteDefinition(key="modules", route_prefix="/modules", import_path="app.api.v1.endpoints.modules", tags=('modules',)),
    EndpointRouteDefinition(key="search", route_prefix="/search", import_path="app.api.v1.endpoints.search", tags=('search',)),
    EndpointRouteDefinition(key="security_monitor", route_prefix="/security", import_path="app.api.v1.endpoints.security_monitor", tags=('security',)),
    EndpointRouteDefinition(key="auth", route_prefix="/auth", import_path="app.api.v1.endpoints.auth", tags=('auth',)),
    EndpointRouteDefinition(key="two_factor", route_prefix="/auth/2fa", import_path="app.api.v1.endpoints.two_factor", tags=('2fa',)),
    EndpointRouteDefinition(key="webhooks", route_prefix="/webhooks", import_path="app.api.v1.endpoints.webhooks", tags=('webhooks',)),
    EndpointRouteDefinition(key="fleet", route_prefix="/fleet", import_path="app.api.v1.endpoints.fleet", tags=('fleet',)),
    EndpointRouteDefinition(key="cycle_count", route_prefix="/cycle-count", import_path="app.api.v1.endpoints.cycle_count", tags=('cycle-count',)),
    EndpointRouteDefinition(key="audit", route_prefix="/audit", import_path="app.api.v1.endpoints.audit", tags=('audit',)),
    EndpointRouteDefinition(key="logs", route_prefix="/logs", import_path="app.api.v1.endpoints.logs", tags=('logs',)),
    EndpointRouteDefinition(key="suppliers", route_prefix="/suppliers", import_path="app.api.v1.endpoints.suppliers", tags=('suppliers',)),
    EndpointRouteDefinition(key="products", route_prefix="/products", import_path="app.api.v1.endpoints.products", tags=('products',)),
    EndpointRouteDefinition(key="materials", route_prefix="/materials", import_path="app.api.v1.endpoints.materials", tags=('materials',)),
    EndpointRouteDefinition(key="warehouses", route_prefix="/warehouses", import_path="app.api.v1.endpoints.warehouses", tags=('warehouses',)),
    EndpointRouteDefinition(key="wms", route_prefix="/wms", import_path="app.api.v1.endpoints.wms", tags=('wms',)),
    EndpointRouteDefinition(key="logistics", route_prefix="/logistics", import_path="app.api.v1.endpoints.logistics", tags=('logistics',)),
    EndpointRouteDefinition(key="tax_regulatory", route_prefix="/tax", import_path="app.api.v1.endpoints.tax_regulatory", tags=('tax-regulatory',)),
    EndpointRouteDefinition(key="dashboard", route_prefix="/dashboard", import_path="app.api.v1.endpoints.dashboard", tags=('dashboard',)),
    EndpointRouteDefinition(key="integrations", route_prefix="/integrations", import_path="app.api.v1.endpoints.integrations", tags=('integrations',)),
    EndpointRouteDefinition(key="distributors", route_prefix="/distributors", import_path="app.api.v1.endpoints.distributors", tags=('distributors',)),
    EndpointRouteDefinition(key="field_sales", route_prefix="/field-sales", import_path="app.api.v1.endpoints.field_sales", tags=('field-sales',)),
    EndpointRouteDefinition(key="delivery", route_prefix="/delivery", import_path="app.api.v1.endpoints.delivery", tags=('delivery',)),
    EndpointRouteDefinition(key="returns_mgmt", route_prefix="/returns", import_path="app.api.v1.endpoints.returns_mgmt", tags=('returns',)),
    EndpointRouteDefinition(key="pricing", route_prefix="/pricing", import_path="app.api.v1.endpoints.pricing", tags=('pricing',)),
    EndpointRouteDefinition(key="analytics", route_prefix="/analytics", import_path="app.api.v1.endpoints.analytics", tags=('analytics',)),
    EndpointRouteDefinition(key="bulk_import", route_prefix="/bulk-import", import_path="app.api.v1.endpoints.bulk_import", tags=('bulk-import',)),
    EndpointRouteDefinition(key="marketing", route_prefix="/marketing", import_path="app.api.v1.endpoints.marketing", tags=('marketing',)),
    EndpointRouteDefinition(key="production_advanced", route_prefix="/production-adv", import_path="app.api.v1.endpoints.production_advanced", tags=('production-advanced',)),
    EndpointRouteDefinition(key="production_costing", route_prefix="/production-cost", import_path="app.api.v1.endpoints.production_costing", tags=('production-costing',)),
    EndpointRouteDefinition(key="production_ai", route_prefix="/production-ai", import_path="app.api.v1.endpoints.production_ai", tags=('production-ai',)),
    EndpointRouteDefinition(key="utility_management", route_prefix="/utility-management", import_path="app.api.v1.endpoints.utility_management", tags=('utility-management',)),
    EndpointRouteDefinition(key="electricity", route_prefix="/electricity", import_path="app.api.v1.endpoints.electricity", tags=('electricity',)),
    EndpointRouteDefinition(key="water", route_prefix="/water", import_path="app.api.v1.endpoints.water", tags=('water',)),
    EndpointRouteDefinition(key="soft_water", route_prefix="/soft-water", import_path="app.api.v1.endpoints.soft_water", tags=('soft-water',)),
    EndpointRouteDefinition(key="steam", route_prefix="/steam", import_path="app.api.v1.endpoints.steam", tags=('steam',)),
    EndpointRouteDefinition(key="compressor", route_prefix="/compressor", import_path="app.api.v1.endpoints.compressor", tags=('compressor',)),
    EndpointRouteDefinition(key="solar", route_prefix="/solar", import_path="app.api.v1.endpoints.solar", tags=('solar',)),
    EndpointRouteDefinition(key="chemical_treatment", route_prefix="/chemical-treatment", import_path="app.api.v1.endpoints.chemical_treatment", tags=('chemical-treatment',)),
    EndpointRouteDefinition(key="wastewater", route_prefix="/wastewater", import_path="app.api.v1.endpoints.wastewater", tags=('wastewater',)),
    EndpointRouteDefinition(key="machine_utility", route_prefix="/machine-utility", import_path="app.api.v1.endpoints.machine_utility", tags=('machine-utility',)),
    EndpointRouteDefinition(key="utility_billing", route_prefix="/billing", import_path="app.api.v1.endpoints.utility_billing", tags=('utility-billing',)),
    EndpointRouteDefinition(key="utility_integration", route_prefix="/utility-management", import_path="app.api.v1.endpoints.utility_integration", tags=('utility-integration',)),
    EndpointRouteDefinition(key="utilities_reports", route_prefix="/utilities-reports", import_path="app.api.v1.endpoints.utilities_reports", tags=('utilities-reports',)),
    EndpointRouteDefinition(key="utility_alarm", route_prefix="/alarms", import_path="app.api.v1.endpoints.utility_alarm", tags=('utility-alarms',)),
    EndpointRouteDefinition(key="utility_kpi", route_prefix="/utility-kpi", import_path="app.api.v1.endpoints.utility_kpi", tags=('utility-kpi',)),
    EndpointRouteDefinition(key="mrp", route_prefix="/mrp", import_path="app.api.v1.endpoints.mrp", tags=('mrp',)),
    EndpointRouteDefinition(key="mps", route_prefix="/mps", import_path="app.api.v1.endpoints.mps", tags=('mps',)),
    EndpointRouteDefinition(key="production_execution", route_prefix="/production-execution", import_path="app.api.v1.endpoints.production_execution", tags=('production-execution',)),
    EndpointRouteDefinition(key="shop_floor", route_prefix="/shop-floor", import_path="app.api.v1.endpoints.shop_floor", tags=('shop-floor',)),
    EndpointRouteDefinition(key="material_flow", route_prefix="/material-flow", import_path="app.api.v1.endpoints.material_flow", tags=('material-flow',)),
    EndpointRouteDefinition(key="machine_operator", route_prefix="/machine-ops", import_path="app.api.v1.endpoints.machine_operator", tags=('machine-operator',)),
    # shelf_life promoted to MODULE_DEFINITIONS — see above
    EndpointRouteDefinition(key="traceability", route_prefix="/traceability", import_path="app.api.v1.endpoints.traceability", tags=('traceability',)),
    EndpointRouteDefinition(key="qms", route_prefix="/qms", import_path="app.api.v1.endpoints.qms", tags=('qms',)),
    # gs1 promoted to MODULE_DEFINITIONS — see above
    EndpointRouteDefinition(key="allergen", route_prefix="/allergen", import_path="app.api.v1.endpoints.allergen", tags=('allergen',)),
    EndpointRouteDefinition(key="procurement_suggestion", route_prefix="/procurement/suggestions", import_path="app.api.v1.endpoints.procurement_suggestion", tags=('procurement-suggestions',)),
    EndpointRouteDefinition(key="subcontracting", route_prefix="/subcontracting", import_path="app.api.v1.endpoints.subcontracting", tags=('subcontracting',)),
    EndpointRouteDefinition(key="landed_cost", route_prefix="/landed-cost", import_path="app.api.v1.endpoints.landed_cost", tags=('landed-cost',)),
    EndpointRouteDefinition(key="invoice_match", route_prefix="/invoice-match", import_path="app.api.v1.endpoints.invoice_match", tags=('invoice-match',)),
    EndpointRouteDefinition(key="bank_reconciliation", route_prefix="/bank-reconciliation", import_path="app.api.v1.endpoints.bank_reconciliation", tags=('bank-reconciliation',)),
    EndpointRouteDefinition(key="fixed_assets", route_prefix="/fixed-assets", import_path="app.api.v1.endpoints.fixed_assets", tags=('fixed-assets',)),
    EndpointRouteDefinition(key="dimensions", route_prefix="/dimensions", import_path="app.api.v1.endpoints.dimensions", tags=('dimensions',)),
    EndpointRouteDefinition(key="promotions", route_prefix="/promotions", import_path="app.api.v1.endpoints.promotions", tags=('promotions',)),
    EndpointRouteDefinition(key="tpm", route_prefix="/tpm", import_path="app.api.v1.endpoints.tpm", tags=('tpm',)),
    EndpointRouteDefinition(key="portal", route_prefix="/portal", import_path="app.api.v1.endpoints.portal", tags=('portal',)),
    EndpointRouteDefinition(key="supplier_portal", route_prefix="/supplier-portal", import_path="app.api.v1.endpoints.supplier_portal", tags=('supplier-portal',)),
    EndpointRouteDefinition(key="dunning", route_prefix="/dunning", import_path="app.api.v1.endpoints.dunning", tags=('dunning',)),
    EndpointRouteDefinition(key="price_list", route_prefix="/price-lists", import_path="app.api.v1.endpoints.price_list", tags=('price-lists',)),
    EndpointRouteDefinition(key="subscription", route_prefix="/recurring-orders", import_path="app.api.v1.endpoints.subscription", tags=('recurring-orders',)),
    EndpointRouteDefinition(key="van_sales", route_prefix="/van-sales", import_path="app.api.v1.endpoints.van_sales", tags=('van-sales',)),
    EndpointRouteDefinition(key="contracts", route_prefix="/contracts", import_path="app.api.v1.endpoints.contracts", tags=('contracts',)),
    EndpointRouteDefinition(key="moto_sales", route_prefix="/moto-sales", import_path="app.api.v1.endpoints.moto_sales", tags=('moto-sales',)),
    EndpointRouteDefinition(key="commissions", route_prefix="/commissions", import_path="app.api.v1.endpoints.commissions", tags=('commissions',)),
    EndpointRouteDefinition(key="expenses", route_prefix="/expenses", import_path="app.api.v1.endpoints.expenses", tags=('expenses',)),
    EndpointRouteDefinition(key="recruitment", route_prefix="/recruitment", import_path="app.api.v1.endpoints.recruitment", tags=('recruitment',)),
    EndpointRouteDefinition(key="ess", route_prefix="/ess", import_path="app.api.v1.endpoints.ess", tags=('ess',)),
    EndpointRouteDefinition(key="appraisals", route_prefix="/appraisals", import_path="app.api.v1.endpoints.appraisals", tags=('appraisals',)),
    EndpointRouteDefinition(key="training", route_prefix="/training", import_path="app.api.v1.endpoints.training", tags=('training',)),
    EndpointRouteDefinition(key="timesheets", route_prefix="/timesheets", import_path="app.api.v1.endpoints.timesheets", tags=('timesheets',)),
    # notifications promoted to MODULE_DEFINITIONS — see above
    EndpointRouteDefinition(key="kanban", route_prefix="/kanban", import_path="app.api.v1.endpoints.kanban", tags=('kanban',)),
    # report_builder promoted to MODULE_DEFINITIONS — see below
    EndpointRouteDefinition(key="calendar", route_prefix="/calendar", import_path="app.api.v1.endpoints.calendar", tags=('calendar',)),
    EndpointRouteDefinition(key="chatter", route_prefix="/chatter", import_path="app.api.v1.endpoints.chatter", tags=('chatter',)),
    EndpointRouteDefinition(key="custom_fields", route_prefix="/custom-fields", import_path="app.api.v1.endpoints.custom_fields", tags=('custom-fields',)),
    EndpointRouteDefinition(key="secondary_sales", route_prefix="/secondary-sales", import_path="app.api.v1.endpoints.secondary_sales", tags=('secondary-sales',)),
    EndpointRouteDefinition(key="esg", route_prefix="/esg", import_path="app.api.v1.endpoints.esg", tags=('esg',)),
    EndpointRouteDefinition(key="serial_tracking", route_prefix="/inventory/serials", import_path="app.api.v1.endpoints.serial_tracking", tags=('serial-tracking',)),
    EndpointRouteDefinition(key="approvals", route_prefix="/approvals", import_path="app.api.v1.endpoints.approvals", tags=('approvals',)),
    EndpointRouteDefinition(key="messaging", route_prefix="/messaging", import_path="app.api.v1.endpoints.messaging", tags=('messaging',)),
    EndpointRouteDefinition(key="email_integration", route_prefix="/email", import_path="app.api.v1.endpoints.email_integration", tags=('email',)),
    # company promoted to ModuleDefinition (GAP-025G)
    EndpointRouteDefinition(key="whatsapp", route_prefix="/whatsapp", import_path="app.api.v1.endpoints.whatsapp", tags=('whatsapp',)),
    EndpointRouteDefinition(key="quotation", route_prefix="/quotes", import_path="app.api.v1.endpoints.quotation", tags=('quotes',)),
    EndpointRouteDefinition(key="helpdesk", route_prefix="/helpdesk", import_path="app.api.v1.endpoints.helpdesk", tags=('helpdesk',)),
    EndpointRouteDefinition(key="project", route_prefix="/projects", import_path="app.api.v1.endpoints.project", tags=('projects',)),
    EndpointRouteDefinition(key="pos", route_prefix="/pos", import_path="app.api.v1.endpoints.pos", tags=('pos',)),
    EndpointRouteDefinition(key="bank_api", route_prefix="/bank-api", import_path="app.api.v1.endpoints.bank_api", tags=('bank-api',)),
    EndpointRouteDefinition(key="surveys", route_prefix="/surveys", import_path="app.api.v1.endpoints.surveys", tags=('surveys',)),
    EndpointRouteDefinition(key="voip", route_prefix="/calls", import_path="app.api.v1.endpoints.voip", tags=('voip',)),
    EndpointRouteDefinition(key="loyalty", route_prefix="/loyalty", import_path="app.api.v1.endpoints.loyalty", tags=('loyalty',)),
    EndpointRouteDefinition(key="meetings", route_prefix="/meetings", import_path="app.api.v1.endpoints.meetings", tags=('meetings',)),
    EndpointRouteDefinition(key="nps", route_prefix="/nps", import_path="app.api.v1.endpoints.nps", tags=('nps',)),
    EndpointRouteDefinition(key="mobile", route_prefix="/mobile", import_path="app.api.v1.endpoints.mobile", tags=('mobile',)),
    EndpointRouteDefinition(key="api_portal", route_prefix="/developer", import_path="app.api.v1.endpoints.api_portal", tags=('developer-portal',)),
    EndpointRouteDefinition(key="containers", route_prefix="/containers", import_path="app.api.v1.endpoints.containers", tags=('containers',)),
    # consumer_complaints promoted to MODULE_DEFINITIONS - see above
    EndpointRouteDefinition(key="regulatory_certs", route_prefix="/regulatory-certs", import_path="app.api.v1.endpoints.regulatory_certs", tags=('regulatory-certs',)),
    EndpointRouteDefinition(key="dynamic_pricing", route_prefix="/dynamic-pricing", import_path="app.api.v1.endpoints.dynamic_pricing", tags=('dynamic-pricing',)),
    EndpointRouteDefinition(key="brand_assets", route_prefix="/brand-assets", import_path="app.api.v1.endpoints.brand_assets", tags=('brand-assets',)),
    EndpointRouteDefinition(key="market_intelligence", route_prefix="/market-intel", import_path="app.api.v1.endpoints.market_intelligence", tags=('market-intelligence',)),
    # iot promoted to MODULE_DEFINITIONS - see above
    EndpointRouteDefinition(key="copacking", route_prefix="/copacking", import_path="app.api.v1.endpoints.copacking", tags=('copacking',)),
    EndpointRouteDefinition(key="receipt_ocr", route_prefix="/receipt-ocr", import_path="app.api.v1.endpoints.receipt_ocr", tags=('receipt-ocr',)),
)

def iter_enabled_modules() -> Iterable[ModuleDefinition]:
    return (module for module in MODULE_DEFINITIONS if module.enabled)


def module_manifest() -> list[dict]:
    return [module.to_manifest() for module in MODULE_DEFINITIONS]


def registry_permission_codes() -> set[str]:
    return {code for module in MODULE_DEFINITIONS for code in module.permission_codes}


def permission_coverage_candidates(permission: str) -> set[str]:
    """Return permission codes that should satisfy a base module action."""
    if "." not in permission:
        return {permission}
    module, action = permission.split(".", 1)
    candidates = {permission}
    candidates.update(f"{module}.{alias}" for alias in SCOPED_PERMISSION_ACTION_ALIASES.get(action, ()))
    return candidates


def permission_is_covered(required_permission: str, granted_permissions: Iterable[str]) -> bool:
    """Treat scoped all/own permissions as satisfying their base action for visibility."""
    granted = set(granted_permissions)
    if "*" in granted or required_permission in granted:
        return True
    return bool(permission_coverage_candidates(required_permission) & granted)


def covered_registry_permission_codes(granted_permissions: Iterable[str]) -> set[str]:
    """Return registry permissions visible through exact or scoped permission grants."""
    granted = set(granted_permissions)
    return {
        required
        for required in registry_permission_codes()
        if permission_is_covered(required, granted)
    }


def permission_coverage_report(
    required_permissions: Iterable[str],
    granted_permissions: Iterable[str],
) -> dict[str, list[str]]:
    """Build a deterministic permission coverage report for drift/audit checks."""
    covered: list[str] = []
    missing: list[str] = []
    granted = set(granted_permissions)

    for permission in sorted(set(required_permissions)):
        if permission_is_covered(permission, granted):
            covered.append(permission)
        else:
            missing.append(permission)

    return {"covered": covered, "missing": missing}


def _register_routes(
    api_router: APIRouter,
    definitions: Iterable[ModuleDefinition | EndpointRouteDefinition],
    *,
    environment: str,
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    fail_fast = environment.lower() == "production"

    for definition in definitions:
        if not definition.enabled:
            diagnostics.append({"module": definition.key, "status": "disabled"})
            continue
        try:
            endpoint_module = import_module(definition.import_path)
            router = getattr(endpoint_module, "router")
            tags = getattr(definition, "tags", (definition.key,))
            api_router.include_router(
                router,
                prefix=definition.route_prefix,
                tags=list(tags),
            )
            diagnostics.append({"module": definition.key, "status": "registered"})
        except Exception as exc:
            message = (
                f"Failed to register module '{definition.key}' from "
                f"{definition.import_path}: {exc}"
            )
            diagnostics.append(
                {
                    "module": definition.key,
                    "status": "failed",
                    "critical": str(definition.critical).lower(),
                    "error": message,
                }
            )
            if fail_fast:
                raise RuntimeError(message) from exc
            logger.exception(message)

    return diagnostics


def register_module_routes(
    api_router: APIRouter,
    *,
    environment: str,
) -> list[dict[str, str]]:
    """Register enabled core module routes from the backend-owned module registry."""
    return _register_routes(api_router, iter_enabled_modules(), environment=environment)


def register_endpoint_routes(
    api_router: APIRouter,
    *,
    environment: str,
) -> list[dict[str, str]]:
    """Register non-core endpoint routes from backend-owned route definitions."""
    return _register_routes(api_router, ENDPOINT_ROUTE_DEFINITIONS, environment=environment)
