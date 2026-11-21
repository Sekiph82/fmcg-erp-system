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
HR = ("hr",)  # appraisals, training, recruitment: HR only (not payroll clerks)
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
    "/procurement/suggestions": ("procurement", "mrp", "planning"),
    "/production-cost": ("production", "finance"),
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

# Master data many modules must read (pick lists), while changing it stays with the owning module.
_OPS = ("production", "production_execution", "planning", "shop_floor", "sales", "procurement", "logistics", "quality",
        "qms", "inventory", "wms", "warehouses", "finance", "maintenance", "field", "mrp", "mps")
READ_EXTRA: dict[str, tuple[str, ...]] = {"/warehouses": _OPS, "/materials": _OPS, "/products": _OPS}
# single collections inside a module router that other modules read for pick lists
READ_EXTRA_SEGMENTS: dict[str, frozenset[str]] = {"work-centers": frozenset({"maintenance", "tpm"})}

# A handler counts as checking permissions itself only for real calls in its BODY (signature/decorator excluded).
_OWN_CHECK = re.compile(
    r"\b(has_permission|has_any_permission|require_permission|require_any_permission|can_modify_record|can_view_record|"
    r"can_view_scope|can_modify_scope|can_access_scope|check_permission|ensure_\w+|_superuser_only|_can_\w+|_my_\w+|"
    r"_own_or_404|_scope|apply_\w*scope\w*|get_portal_user|get_supplier_user)\s*\(|"
    r"\bis_superuser\b|current_user\.id\s*[!=]=|==\s*current_user\.id|"
    r"HTTPException\(\s*(status_code\s*=\s*)?(403|status\.HTTP_403_FORBIDDEN)")
_BASE_DEPS = {"get_current_user", "get_db"}
_PERMISSION_DEP = re.compile(r"permission|require|superuser|guard|portal_user|supplier_user|verify_|realm", re.I)
# write actions that need an approval-level right, not just any write right (segregation of duties)
APPROVAL_SEGMENTS = {"approve", "reject", "post", "finalize", "mark-paid", "pay", "void", "dispose", "revalue", "impair",
                     "close-period", "reverse", "write-off", "release"}
APPROVAL_ACTIONS = {"approve", "approve_all", "post", "manage"}


def _dep_names(dependant, out: list[str]) -> list[str]:
    for d in dependant.dependencies:
        name = getattr(d.call, "__qualname__", repr(d.call))
        out.append(name)
        if name not in _BASE_DEPS:
            _dep_names(d, out)
    return out


def _body_source(fn) -> str:
    import ast
    import textwrap
    try:
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
    except (OSError, TypeError, SyntaxError):
        return ""
    node = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if node is None:
        return ""
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]  # docstring
    return "\n".join(ast.get_source_segment(src, n) or "" for n in body)


_RECORD_CHECK = re.compile(r"\b(_require_\w+_action|ensure_\w+_action_allowed|can_modify_record|can_modify_scope|can_access_scope)\s*\(")


def has_record_check(route: APIRoute) -> bool:
    """The handler checks the user's right on the record itself (scope-aware), so scoped approval rights may pass."""
    return bool(_RECORD_CHECK.search(_body_source(route.endpoint)))


def has_own_check(route: APIRoute, router_deps: list) -> bool:
    """True when the route already enforces a permission: a permission dependency, or a check in its body."""
    names = [n for n in _dep_names(route.dependant, []) if n not in _BASE_DEPS]
    if any(_PERMISSION_DEP.search(n) for n in names) or any(_PERMISSION_DEP.search(str(d)) for d in router_deps):
        return True
    return bool(_OWN_CHECK.search(_body_source(route.endpoint)))


def _literal_segments(request: Request) -> list[str]:
    route = request.scope.get("route")
    path = getattr(route, "path", "") or request.url.path
    return [seg for seg in path.split("/") if seg and not seg.startswith("{")]


def module_guard(modules: tuple[str, ...], read_extra: tuple[str, ...] = (), scoped_approval: bool = False):
    from app.core.deps import get_current_user

    mods = frozenset(modules)
    read_mods = mods | frozenset(read_extra)

    async def _module_permission(request: Request, current_user=Depends(get_current_user)):
        if getattr(current_user, "is_superuser", False):
            return current_user
        codes = get_effective_permission_codes(current_user)
        if "*" in codes:
            return current_user
        read = request.method in ("GET", "HEAD", "OPTIONS")
        segments = _literal_segments(request) + [p for p in request.url.path.split("/") if p]
        need_mods, approval = (read_mods if read else mods), (not read and bool(APPROVAL_SEGMENTS.intersection(segments)))
        if read:
            for seg in set(segments) & READ_EXTRA_SEGMENTS.keys():
                need_mods = need_mods | READ_EXTRA_SEGMENTS[seg]
        if not read and "payments" in segments and "sales" in segments:
            need_mods = frozenset({"finance"})          # recording customer money is a finance task
        if not read and "custom-fields" in segments and "values" not in segments:
            need_mods = frozenset({"company", "roles", "users"})   # field definitions are administration
        for code in codes:
            module, _, action = code.partition(".")
            if module not in need_mods:
                continue
            if approval:
                # approve_own_scope / approve_own_region … only where the handler then checks the record's scope
                if action in APPROVAL_ACTIONS or (scoped_approval and action.startswith(("approve_", "post_"))):
                    return current_user
            elif read or not (action.startswith("view") or action == "export"):
                return current_user
        detail = "This needs an approval right." if approval else "Required permission is missing."
        raise HTTPException(403, {"detail": detail, "modules": sorted(need_mods)})

    return _module_permission
