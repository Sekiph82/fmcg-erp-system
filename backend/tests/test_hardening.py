"""Hardening regression tests for auth, config, AI, and module metadata."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, Response
from pydantic import ValidationError
from starlette.requests import Request

from app.api.v1.endpoints.modules import get_module_manifest, get_permission_coverage
from app.api.v1.endpoints.ai import _require_live_ai_for_high_risk
from app.core.auth_cookies import clear_auth_cookie, set_auth_cookie
from app.core.config import Settings, settings
from app.core.deps import get_current_user
from app.core.module_registry import (
    EndpointRouteDefinition,
    MODULE_DEFINITIONS,
    ModuleDefinition,
    permission_coverage_report,
    permission_is_covered,
    register_endpoint_routes,
    register_module_routes,
    registry_permission_codes,
)
from app.core.observability import metrics_snapshot, record_request
from app.db.seed import DEMO_USERS
from app.services.ai_provider import AIResponse
from app.services.ai_service import (
    _RecommendationOutput,
    _generate_validated_output,
)

pytestmark = pytest.mark.filterwarnings(
    "ignore:relationship .* conflicts with relationship.*:sqlalchemy.exc.SAWarning"
)


def _cookie_request(token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"cookie", f"{settings.AUTH_COOKIE_NAME}={token}".encode())],
        }
    )


def _bearer_request(token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
    )


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode()
        for key, value in response.raw_headers
        if key.lower() == b"set-cookie"
    ]


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDb:
    def __init__(self, user=None):
        self.user = user
        self.committed = False

    async def execute(self, _stmt):
        return FakeScalarResult(self.user)

    async def commit(self):
        self.committed = True


class FakeProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    async def generate_structured_output(self, prompt: str, system: str | None = None):
        self.prompts.append(prompt)
        obj = self.outputs.pop(0)
        return obj, AIResponse("{}", "test", "test-model")


class FakeScalarListResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakePermissionDb:
    def __init__(self, codes):
        self.codes = codes

    async def execute(self, _stmt):
        return FakeScalarListResult(self.codes)


def test_auth_cookie_is_httponly_and_uses_configured_security_flags(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "AUTH_COOKIE_SAMESITE", "strict")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)

    response = Response()
    set_auth_cookie(response, "token-123")

    header = _set_cookie_headers(response)[0].lower()
    assert f"{settings.AUTH_COOKIE_NAME}=token-123" in header
    assert "httponly" in header
    assert "secure" in header
    assert "samesite=strict" in header
    assert "max-age=900" in header


def test_clear_auth_cookie_expires_auth_cookie(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "AUTH_COOKIE_SAMESITE", "lax")

    response = Response()
    clear_auth_cookie(response)

    header = _set_cookie_headers(response)[0].lower()
    assert f"{settings.AUTH_COOKIE_NAME}=" in header
    assert "max-age=0" in header
    assert "httponly" in header
    assert "secure" in header
    assert "samesite=lax" in header


@pytest.mark.asyncio
async def test_get_current_user_accepts_cookie_token(monkeypatch):
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id, is_active=True, roles=[])

    async def not_blocked(_token: str) -> bool:
        return False

    monkeypatch.setattr("app.core.deps.decode_token", lambda token: str(user_id))
    monkeypatch.setattr("app.core.deps.token_blocklist.is_blocked", not_blocked)

    current = await get_current_user(
        request=_cookie_request("cookie-token"),
        db=FakeDb(user),
    )

    assert current is user


@pytest.mark.asyncio
async def test_get_current_user_rejects_authorization_header_without_cookie(monkeypatch):
    async def not_blocked(_token: str) -> bool:
        return False

    monkeypatch.setattr("app.core.deps.decode_token", lambda token: "unused")
    monkeypatch.setattr("app.core.deps.token_blocklist.is_blocked", not_blocked)

    with pytest.raises(Exception) as exc_info:
        await get_current_user(
            request=_bearer_request("legacy-token"),
            db=FakeDb(),
        )

    assert getattr(exc_info.value, "status_code", None) == 401


def test_production_config_rejects_security_landmines():
    base = {
        "_env_file": None,
        "ENVIRONMENT": "production",
        "SECRET_KEY": "production-secret-key",
        "PASSWORD_REQUIRE_SPECIAL": True,
        "SEED_DEMO_DATA": False,
        "SEED_INITIAL_ADMIN": True,
        "SYNC_INITIAL_ADMIN_PASSWORD": False,
        "OTP_DEV_DELIVERY_MODE": False,
        "INITIAL_ADMIN_PASSWORD": "StrongerAdmin1!",
        "AUTH_COOKIE_SECURE": True,
        "REDIS_PASSWORD": "str0ngRedisPass4Tests",
        "TWO_FACTOR_EMAIL_ENABLED": False,
    }

    Settings(**base)

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(**{**base, "SECRET_KEY": "changeme"})
    with pytest.raises(ValueError, match="PASSWORD_REQUIRE_SPECIAL"):
        Settings(**{**base, "PASSWORD_REQUIRE_SPECIAL": False})
    with pytest.raises(ValueError, match="SEED_DEMO_DATA"):
        Settings(**{**base, "SEED_DEMO_DATA": True})
    with pytest.raises(ValueError, match="INITIAL_ADMIN_PASSWORD"):
        Settings(**{**base, "INITIAL_ADMIN_PASSWORD": ""})
    with pytest.raises(ValueError, match="AUTH_COOKIE_SECURE"):
        Settings(**{**base, "AUTH_COOKIE_SECURE": False})


_PROD_BASE = {
    "_env_file": None,
    "ENVIRONMENT": "production",
    "SECRET_KEY": "production-secret-key",
    "PASSWORD_REQUIRE_SPECIAL": True,
    "SEED_DEMO_DATA": False,
    "SEED_INITIAL_ADMIN": True,
    "SYNC_INITIAL_ADMIN_PASSWORD": False,
    "OTP_DEV_DELIVERY_MODE": False,
    "INITIAL_ADMIN_PASSWORD": "StrongerAdmin1!",
    "AUTH_COOKIE_SECURE": True,
    "REDIS_PASSWORD": "str0ngRedisPass4Tests",
    "TWO_FACTOR_EMAIL_ENABLED": False,
}


def test_management_seed_defaults_off(monkeypatch):
    """ERP_SEED_MANAGEMENT_USERS defaults false; no management vars leak into code defaults."""
    for var in ("ERP_SEED_MANAGEMENT_USERS", "ERP_CEO_PASSWORD", "ERP_CTO_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    isolated = Settings(_env_file=None)
    assert isolated.ERP_SEED_MANAGEMENT_USERS is False
    assert isolated.ERP_CEO_PASSWORD == ""
    assert isolated.ERP_CTO_PASSWORD == ""


def test_no_technical_manager_config_vars():
    """No ERP_TECHNICAL_MANAGER_* variables should exist on Settings."""
    isolated = Settings(_env_file=None)
    assert not hasattr(isolated, "ERP_TECHNICAL_MANAGER_EMAIL")
    assert not hasattr(isolated, "ERP_TECHNICAL_MANAGER_PASSWORD")


def test_cto_config_var_exists():
    """ERP_CTO_* vars exist — CTO is the technical management role."""
    isolated = Settings(_env_file=None)
    assert hasattr(isolated, "ERP_CTO_EMAIL")
    assert hasattr(isolated, "ERP_CTO_PASSWORD")
    assert hasattr(isolated, "ERP_CTO_FULL_NAME")


def test_production_rejects_change_me_management_passwords():
    """Production startup must reject CHANGE_ME passwords when management seed is enabled."""
    with pytest.raises(ValueError, match="ERP_CEO_PASSWORD"):
        Settings(**{
            **_PROD_BASE,
            "ERP_SEED_MANAGEMENT_USERS": True,
            "ERP_CEO_EMAIL": "ceo@example.com",
            "ERP_CEO_PASSWORD": "CHANGE_ME_CEO_PASSWORD",
        })


def test_production_rejects_email_without_password():
    """Production startup must reject email set without matching password."""
    with pytest.raises(ValueError, match="ERP_CFO_PASSWORD"):
        Settings(**{
            **_PROD_BASE,
            "ERP_SEED_MANAGEMENT_USERS": True,
            "ERP_CFO_EMAIL": "cfo@example.com",
            "ERP_CFO_PASSWORD": "",
        })


def test_production_allows_partial_management_seed():
    """Production accepts management seed when only some roles are configured (others blank)."""
    s = Settings(**{
        **_PROD_BASE,
        "ERP_SEED_MANAGEMENT_USERS": True,
        "ERP_CEO_EMAIL": "ceo@example.com",
        "ERP_CEO_PASSWORD": "StrongCeo1!",
        # all other ERP_*_EMAIL and ERP_*_PASSWORD remain "" — should be skipped
    })
    assert s.ERP_CEO_EMAIL == "ceo@example.com"


def test_production_allows_management_seed_all_blank():
    """ERP_SEED_MANAGEMENT_USERS=true with all blank emails/passwords is valid (nothing to seed)."""
    Settings(**{**_PROD_BASE, "ERP_SEED_MANAGEMENT_USERS": True})


def test_seed_defaults_do_not_enable_demo_users_or_plaintext_passwords(monkeypatch):
    # Clear vars that .env.development may inject so we test code defaults only.
    for var in ("SEED_DEMO_DATA", "DEMO_USER_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    isolated = Settings(_env_file=None)

    assert isolated.SEED_DEMO_DATA is False
    assert isolated.DEMO_USER_PASSWORD == ""
    assert all("password" not in demo for demo in DEMO_USERS)


def test_observability_metrics_record_requests():
    before = metrics_snapshot()["requests_total"]
    record_request("GET", "/health", 200, 12)
    record_request("POST", "/api/v1/example", 503, 750)
    snapshot = metrics_snapshot()

    assert snapshot["requests_total"] >= before + 2
    assert snapshot["requests_by_route"]["GET /health"] >= 1
    assert snapshot["responses_by_status"]["503"] >= 1
    assert snapshot["slow_requests_total"] >= 1
    assert snapshot["error_requests_total"] >= 1


def test_high_risk_ai_actions_are_blocked_in_mock_mode(monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.ai._ai_is_mock_mode", lambda: True)

    with pytest.raises(Exception) as exc_info:
        _require_live_ai_for_high_risk("Test approval")

    assert getattr(exc_info.value, "status_code", None) == 409


def test_registry_route_registration_loads_enabled_modules(monkeypatch):
    endpoint_router = APIRouter()

    @endpoint_router.get("/ping")
    async def ping():
        return {"ok": True}

    module = ModuleDefinition(
        key="factory-test",
        label="Factory Test",
        route_prefix="/factory-test",
        import_path="tests.fake_factory_module",
        permission_actions=("view",),
        sidebar_group="Testing",
        icon_key="factory",
        ai_mode="rule_based",
        critical=True,
    )

    monkeypatch.setattr("app.core.module_registry.MODULE_DEFINITIONS", (module,))
    monkeypatch.setattr(
        "app.core.module_registry.import_module",
        lambda path: SimpleNamespace(router=endpoint_router),
    )

    api_router = APIRouter()
    diagnostics = register_module_routes(api_router, environment="development")
    paths = {route.path for route in api_router.routes}

    assert diagnostics == [{"module": "factory-test", "status": "registered"}]
    assert "/factory-test/ping" in paths


def test_registry_route_registration_fails_fast_in_production(monkeypatch):
    module = ModuleDefinition(
        key="broken",
        label="Broken",
        route_prefix="/broken",
        import_path="tests.broken_module",
        permission_actions=("view",),
        sidebar_group="Testing",
        icon_key="alert",
        ai_mode="rule_based",
        critical=False,
    )

    def fake_import(_path):
        raise ImportError("boom")

    monkeypatch.setattr("app.core.module_registry.MODULE_DEFINITIONS", (module,))
    monkeypatch.setattr("app.core.module_registry.import_module", fake_import)

    with pytest.raises(RuntimeError, match="Failed to register module 'broken'"):
        register_module_routes(APIRouter(), environment="production")


def test_endpoint_route_registration_loads_non_core_routes(monkeypatch):
    endpoint_router = APIRouter()

    @endpoint_router.get("/status")
    async def status():
        return {"ok": True}

    route = EndpointRouteDefinition(
        key="factory-health",
        route_prefix="/factory-health",
        import_path="tests.fake_factory_health",
        tags=("factory-health",),
    )

    monkeypatch.setattr("app.core.module_registry.ENDPOINT_ROUTE_DEFINITIONS", (route,))
    monkeypatch.setattr(
        "app.core.module_registry.import_module",
        lambda path: SimpleNamespace(router=endpoint_router),
    )

    api_router = APIRouter()
    diagnostics = register_endpoint_routes(api_router, environment="development")
    paths = {route.path for route in api_router.routes}

    assert diagnostics == [{"module": "factory-health", "status": "registered"}]
    assert "/factory-health/status" in paths


@pytest.mark.asyncio
async def test_ai_json_validation_repairs_once():
    provider = FakeProvider(
        [
            {"recommendations": [{"category": "stock"}]},
            {"recommendations": [{"category": "stock", "title": "Review reorder points"}]},
        ]
    )

    obj, resp = await _generate_validated_output(
        provider,
        prompt="recommend",
        system="system",
        schema=_RecommendationOutput,
    )

    assert obj["recommendations"][0]["title"] == "Review reorder points"
    assert resp.provider == "test"
    assert len(provider.prompts) == 2
    assert "Repair this AI response" in provider.prompts[1]


@pytest.mark.asyncio
async def test_ai_json_validation_fails_safely_after_bad_repair():
    provider = FakeProvider(
        [
            {"recommendations": [{"category": "stock"}]},
            {"recommendations": [{"category": "still-missing-title"}]},
        ]
    )

    with pytest.raises(ValidationError):
        await _generate_validated_output(
            provider,
            prompt="recommend",
            system="system",
            schema=_RecommendationOutput,
        )
    assert len(provider.prompts) == 2


@pytest.mark.asyncio
async def test_module_manifest_permissions_match_registry():
    db = FakePermissionDb(sorted(registry_permission_codes()))
    manifest = await get_module_manifest(SimpleNamespace(is_superuser=True, roles=[]), db=db)
    modules = manifest["modules"]
    permission_codes = set(manifest["permission_codes"])
    registry_codes = registry_permission_codes()

    assert permission_codes == registry_codes
    assert len({module["key"] for module in modules}) == len(modules)
    assert all(module["route_prefix"].startswith("/") for module in modules)
    assert all(module["permission_codes"] for module in modules)

    for module in modules:
        expected = {f"{module['key']}.{action}" for action in module["permission_actions"]}
        assert set(module["permission_codes"]) == expected
        assert set(module["permission_codes"]).issubset(permission_codes)

    critical_modules = {module.key for module in MODULE_DEFINITIONS if module.critical}
    assert {"users", "roles", "inventory", "production"}.issubset(critical_modules)


@pytest.mark.asyncio
async def test_module_manifest_is_filtered_by_user_permissions():
    inventory_perm = SimpleNamespace(code="inventory.view")
    role = SimpleNamespace(is_active=True, permissions=[inventory_perm])
    user = SimpleNamespace(is_superuser=False, roles=[role])

    db = FakePermissionDb(["inventory.view", "users.view"])
    manifest = await get_module_manifest(user, db=db)
    visible_keys = {module["key"] for module in manifest["modules"]}

    assert visible_keys == {"inventory"}
    assert manifest["visible_permission_codes"] == ["inventory.view"]


@pytest.mark.asyncio
async def test_module_manifest_treats_scoped_view_permissions_as_module_visibility():
    inventory_perm = SimpleNamespace(code="inventory.view_all", is_active=True)
    role = SimpleNamespace(is_active=True, permissions=[inventory_perm])
    user = SimpleNamespace(is_superuser=False, roles=[role])

    db = FakePermissionDb(["inventory.view_all", "users.view"])
    manifest = await get_module_manifest(user, db=db)
    visible_keys = {module["key"] for module in manifest["modules"]}

    assert visible_keys == {"inventory"}
    assert "inventory.view" in manifest["visible_permission_codes"]
    assert "inventory.view_all" in manifest["visible_permission_codes"]


def test_permission_coverage_report_supports_scoped_aliases():
    report = permission_coverage_report(
        ["inventory.view", "inventory.edit", "finance.post", "roles.view"],
        ["inventory.view_own_scope", "finance.post_own_company"],
    )

    assert permission_is_covered("inventory.view", ["inventory.view_all"])
    assert report["covered"] == ["finance.post", "inventory.view"]
    assert report["missing"] == ["inventory.edit", "roles.view"]


@pytest.mark.asyncio
async def test_permission_coverage_endpoint_reports_registry_drift(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.modules.registry_permission_codes",
        lambda: {"finance.post", "inventory.view", "roles.view"},
    )

    result = await get_permission_coverage(db=FakePermissionDb(["custom.legacy", "inventory.view_all"]))

    assert result["registry_permission_count"] == 3
    assert result["database_permission_count"] == 2
    assert result["covered_registry_permissions"] == ["inventory.view"]
    assert result["missing_registry_permissions"] == ["finance.post", "roles.view"]
    assert result["database_only_permissions"] == ["custom.legacy", "inventory.view_all"]
