"""Baseline module permission for API routes that carry no permission check of their own (M40.S02.T001).

The 2026-11-21 audit found ~1,270 routes that only required a signed-in user, e.g. any employee could list all
invoices, record a customer payment or edit tax settings. Every route of a guarded module that has neither a
permission dependency nor a permission check in its handler now needs a right in one of the module's permission
groups: any right to read (GET/HEAD), and a right other than view/export to change anything. Routes with their
own, stricter checks are untouched. Self-service modules (my notifications, my field app, my ESS, my mailbox, …)
are not listed here and keep their own ownership checks.
"""
from __future__ import annotations

import inspect
import re

from fastapi import Depends, HTTPException, Request
from fastapi.routing import APIRoute

from app.core.access_control import get_effective_permission_codes

UTIL = ("utilities", "utility_management")
HR = ("hr", "employees", "payroll")
PROD = ("production", "production_execution", "planning", "shop_floor", "mps")
QUALITY = ("quality", "qms")

# route prefix → permission modules (any of them)
MODULE_GUARDS: dict[str, tuple[str, ...]] = {
    "/alarms": UTIL, "/billing": UTIL, "/compressor": UTIL, "/machine-utility": UTIL, "/utilities-reports": UTIL,
    "/utility-kpi": UTIL, "/utility-management": UTIL, "/wastewater": UTIL, "/steam": UTIL, "/soft-water": UTIL,
    "/allergen": (*QUALITY, "production", "recipe", "bom", "npd"),
    "/appraisals": HR, "/training": HR, "/recruitment": HR,
    "/brand-assets": ("marketing", "campaigns", "brand_spend", "social_media"),
    "/bulk-import": ("company", "products", "materials", "sales", "inventory"),
    "/commissions": ("sales", "finance"),
    "/containers": ("logistics", "procurement", "inventory"),
    "/contracts": ("sales", "procurement", "finance"),
    "/copacking": ("production", "procurement"),
    "/custom-fields": ("company", "roles", "users", "sales", "crm", "inventory", "procurement", "production", "hr", "finance"),
    "/cycle-count": ("cycle_count", "inventory", "wms"),
    "/dimensions": ("finance",),
    "/dunning": ("finance", "sales"),
    "/dynamic-pricing": ("pricing", "sales"),
    "/esg": ("esg",),
    "/fixed-assets": ("finance",),
    "/fleet": ("fleet", "logistics"),
    "/helpdesk": ("crm", "sales", *QUALITY, "consumer_complaints"),
    "/kanban": (*PROD, "inventory"),
    "/landed-cost": ("finance", "procurement", "inventory"),
    "/logistics": ("logistics",),
    "/market-intel": ("marketing", "sales", "field", "customer_visits"),
    "/material-flow": ("inventory", *PROD),
    "/materials": ("materials", "inventory", "procurement", "production", "recipe", "bom"),
    "/mrp": ("mrp", *PROD),
    "/pos": ("sales", "stores"),
    "/price-lists": ("pricing", "sales"),
    "/procurement": ("procurement",),
    "/production": PROD, "/production-adv": PROD, "/production-ai": PROD, "/production-execution": PROD,
    "/products": ("products", "sales", "inventory", "production", "pricing", "marketing"),
    "/projects": ("npd", "planning", "production", "marketing", "company"),
    "/promotions": ("promotions", "marketing", "sales", "trade_spend"),
    "/qms": QUALITY, "/quality": QUALITY, "/regulatory-certs": QUALITY,
    "/quotes": ("sales", "crm"),
    "/receipt-ocr": ("finance", "procurement", "inventory"),
    "/recurring-orders": ("sales",),
    "/sales": ("sales", "finance"),
    "/secondary-sales": ("sales", "stores", "store_performance"),
    "/shelf-life": ("shelf_life", *QUALITY, "inventory"),
    "/surveys": ("surveys", "marketing", "crm"),
    "/tax": ("tax", "finance"),
    "/tpm": ("maintenance", "production"),
    "/traceability": ("traceability", *QUALITY),
    "/van-sales": ("sales", "field", "logistics"),
    "/warehouses": ("warehouses", "inventory", "wms"),
    "/whatsapp": ("crm", "sales", "marketing"),
    "/wms": ("wms", "inventory"),
}

_OWN_CHECK = re.compile(
    r"has_permission|has_any_permission|require_permission|require_any_permission|ensure_\w+|_superuser_only|"
    r"is_superuser|_guard|_can_\w+|_my_\w+|_scope\(|_own_or_404|can_modify_record|check_permission|"
    r"_require\w*|_assert\w*|get_portal_user|get_supplier_user|verify_\w+|_mine|current_user\.id\s*[!=]=|"
    r"user_id\s*==\s*current_user|_allowed\(|forbid|403|_scoped|scope_|_visible|_owned", re.I)
_BASE_DEPS = {"get_current_user", "get_db"}


def _dep_names(dependant, out: list[str]) -> list[str]:
    for d in dependant.dependencies:
        name = getattr(d.call, "__qualname__", repr(d.call))
        out.append(name)
        if name not in _BASE_DEPS:
            _dep_names(d, out)
    return out


def has_own_check(route: APIRoute, router_deps: list) -> bool:
    """True when the route already enforces a permission (dependency or a check in its handler)."""
    if router_deps or any(n not in _BASE_DEPS for n in _dep_names(route.dependant, [])):
        return True
    try:
        body = inspect.getsource(route.endpoint).split("\n", 1)[1]
    except (OSError, TypeError, IndexError):
        return False
    return bool(_OWN_CHECK.search(body))


def module_guard(modules: tuple[str, ...]):
    from app.core.deps import get_current_user

    mods = frozenset(modules)

    async def _module_permission(request: Request, current_user=Depends(get_current_user)):
        if getattr(current_user, "is_superuser", False):
            return current_user
        read = request.method in ("GET", "HEAD", "OPTIONS")
        for code in get_effective_permission_codes(current_user):
            if code == "*":
                return current_user
            module, _, action = code.partition(".")
            if module in mods and (read or not (action.startswith("view") or action == "export")):
                return current_user
        raise HTTPException(403, {"detail": "Required permission is missing.", "modules": sorted(mods)})

    return _module_permission
