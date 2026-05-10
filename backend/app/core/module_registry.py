from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from app.core.ai_modes import AIMode, MODULE_AI_MODES


DEFAULT_ACTIONS = ("view", "create", "edit", "delete", "export")


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
        key="procurement",
        label="Procurement",
        route_prefix="/procurement",
        import_path="app.api.v1.endpoints.procurement",
        permission_actions=("view", "create", "edit", "approve", "export"),
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
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="Commercial",
        icon_key="receipt",
        ai_mode=MODULE_AI_MODES.get("sales", AIMode.RULE_BASED),
        critical=True,
    ),
    ModuleDefinition(
        key="finance",
        label="Finance",
        route_prefix="/finance",
        import_path="app.api.v1.endpoints.finance",
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="Finance",
        icon_key="wallet",
        ai_mode=MODULE_AI_MODES.get("finance", AIMode.RULE_BASED),
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
        key="maintenance",
        label="Maintenance",
        route_prefix="/maintenance",
        import_path="app.api.v1.endpoints.maintenance",
        permission_actions=DEFAULT_ACTIONS,
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
        key="ai",
        label="AI & Intelligence",
        route_prefix="/ai",
        import_path="app.api.v1.endpoints.ai",
        permission_actions=("view", "create", "edit", "approve", "export"),
        sidebar_group="Intelligence",
        icon_key="brain",
        ai_mode=AIMode.LLM_POWERED,
        critical=False,
    ),
)


def iter_enabled_modules() -> Iterable[ModuleDefinition]:
    return (module for module in MODULE_DEFINITIONS if module.enabled)


def module_manifest() -> list[dict]:
    return [module.to_manifest() for module in MODULE_DEFINITIONS]


def registry_permission_codes() -> set[str]:
    return {code for module in MODULE_DEFINITIONS for code in module.permission_codes}
