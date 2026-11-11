"""Every registered API route requires an ERP session except the explicit public allowlist."""
from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.core.deps import get_current_user
from app.core.module_registry import PUBLIC_ROUTES, register_endpoint_routes, register_module_routes


def _calls(dependant, acc):
    for dep in dependant.dependencies:
        acc.append(dep.call)
        _calls(dep, acc)
    return acc


def _walk(router, prefix, inherited):
    for item in router.routes:
        if isinstance(item, APIRoute):
            yield prefix + item.path, item, inherited
        elif hasattr(item, "original_router"):
            ctx = item.include_context
            deps = [d.dependency for d in (ctx.dependencies or [])]
            yield from _walk(item.original_router, prefix + (ctx.prefix or ""), inherited + deps)


def _routes():
    api = APIRouter()
    register_endpoint_routes(api, environment="development")
    register_module_routes(api, environment="development")
    return list(_walk(api, "", []))


def test_only_allowlisted_routes_are_reachable_without_a_session():
    open_routes = set()
    routes = _routes()
    assert len(routes) > 2000
    for path, route, inherited in routes:
        if get_current_user in inherited or get_current_user in _calls(route.dependant, []):
            continue
        for method in set(route.methods) - {"HEAD", "OPTIONS"}:
            open_routes.add((path, method))
    assert open_routes == set(PUBLIC_ROUTES)


def test_public_allowlist_entries_all_exist():
    existing = {(path, method) for path, route, _ in _routes() for method in route.methods}
    assert set(PUBLIC_ROUTES) <= existing
