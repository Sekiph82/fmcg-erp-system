"""GAP-024: AI Agent Governance and Prompt Registry focused contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import MODULE_DEFINITIONS, registry_permission_codes
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ACTIONS = {"view", "create", "edit", "approve", "export", "configure"}
REQUIRED_CODES = {f"ai.{a}" for a in REQUIRED_ACTIONS}


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _frontend_src(relative_path: str) -> str:
    frontend_root = ROOT.parent / "frontend"
    return (frontend_root / relative_path).read_text(encoding="utf-8")


# ── Module registry ───────────────────────────────────────────────────────────

def test_ai_is_module_definition():
    keys = {m.key for m in MODULE_DEFINITIONS}
    assert "ai" in keys


def test_ai_module_permission_actions():
    mod = next((m for m in MODULE_DEFINITIONS if m.key == "ai"), None)
    assert mod is not None
    declared = set(mod.permission_actions)
    missing = REQUIRED_ACTIONS - declared
    assert not missing, f"ai module missing permission_actions: {missing}"
    assert "configure" in declared, "ai module missing configure action"
    assert "export" in declared, "ai module missing export action"


# ── Permission seeds ──────────────────────────────────────────────────────────

def test_ai_permission_tuples_exist():
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    missing = REQUIRED_CODES - seeded
    assert not missing, f"Missing ai permission tuples in seed: {missing}"


def test_ai_export_permission_seeded():
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    assert "ai.export" in seeded
    assert "ai.configure" in seeded


def test_ai_registry_permission_codes():
    all_codes = registry_permission_codes()
    missing = REQUIRED_CODES - all_codes
    assert not missing, f"registry_permission_codes missing: {missing}"


# ── Role grants ───────────────────────────────────────────────────────────────

def test_admin_has_full_ai_permissions():
    perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = {"ai.view", "ai.create", "ai.edit", "ai.approve",
               "ai.export", "ai.configure"} - perms
    assert not missing, f"admin missing ai permissions: {missing}"


def test_cto_has_ai_configure_export():
    perms = set(ROLE_DEFINITIONS["cto"]["permissions"])
    required = {"ai.view", "ai.create", "ai.edit", "ai.approve", "ai.export", "ai.configure"}
    missing = required - perms
    assert not missing, f"cto missing ai permissions: {missing}"


def test_ceo_has_ai_export():
    perms = set(ROLE_DEFINITIONS["ceo"]["permissions"])
    required = {"ai.view", "ai.create", "ai.edit", "ai.approve", "ai.export"}
    missing = required - perms
    assert not missing, f"ceo missing ai permissions: {missing}"


def test_coo_has_ai_view_create_export():
    perms = set(ROLE_DEFINITIONS["coo"]["permissions"])
    required = {"ai.view", "ai.create", "ai.export"}
    missing = required - perms
    assert not missing, f"coo missing ai permissions: {missing}"


# ── Endpoint source guards ────────────────────────────────────────────────────

def test_ai_endpoints_use_require_permission():
    src = _source("app/api/v1/endpoints/ai.py")
    assert "require_permission" in src


def test_ai_endpoints_configure_permission_guard():
    src = _source("app/api/v1/endpoints/ai.py")
    assert 'require_permission("ai", "configure")' in src


def test_ai_forecast_baseline_uses_require_permission():
    src = _source("app/api/v1/endpoints/ai.py")
    assert 'require_permission("ai", "view")' in src


def test_ai_prompts_crud_endpoints_present():
    src = _source("app/api/v1/endpoints/ai.py")
    assert "/prompts/" in src
    assert "deactivate" in src


# ── ORM model imports ─────────────────────────────────────────────────────────

def test_ai_prompt_model_importable():
    from app.models.ai import AIPrompt
    assert AIPrompt.__tablename__ == "ai_prompts"


def test_ai_prompt_model_fields():
    from app.models.ai import AIPrompt
    assert hasattr(AIPrompt, "key")
    assert hasattr(AIPrompt, "version")
    assert hasattr(AIPrompt, "content")
    assert hasattr(AIPrompt, "is_active")
    assert hasattr(AIPrompt, "prompt_type")


def test_ai_schemas_importable():
    from app.schemas.ai import AIPromptCreate, AIPromptUpdate, AIPromptRead
    schema = AIPromptCreate(
        key="test.prompt",
        title="Test Prompt",
        content="You are an ERP assistant.",
    )
    assert schema.key == "test.prompt"


# ── Service layer ─────────────────────────────────────────────────────────────

def test_ai_service_resolve_prompt_importable():
    from app.services.ai_service import resolve_prompt
    assert callable(resolve_prompt)


# ── Migration file ────────────────────────────────────────────────────────────

def test_ai_prompt_reconciliation_migration_exists():
    migrations = list((ROOT / "alembic" / "versions").glob("*ai_prompt*"))
    assert migrations, "No ai_prompt reconciliation migration found"


def test_ai_prompt_migration_creates_table():
    src = _source("alembic/versions/20260516_0040_ai_prompt_registry_reconciliation.py")
    assert "ai_prompts" in src
    assert "uq_ai_prompts_key_version" in src


# ── Frontend guards ───────────────────────────────────────────────────────────

def test_ai_dashboard_page_guard():
    src = _frontend_src("src/app/dashboard/ai/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_chat_page_guard():
    src = _frontend_src("src/app/dashboard/ai/chat/page.tsx")
    assert "RequirePermission" in src
    assert "ai.create" in src


def test_ai_governance_page_guard():
    src = _frontend_src("src/app/dashboard/ai/governance/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_formulations_page_guard():
    src = _frontend_src("src/app/dashboard/ai/formulations/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_predictions_page_guard():
    src = _frontend_src("src/app/dashboard/ai/predictions/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_recommendations_page_guard():
    src = _frontend_src("src/app/dashboard/ai/recommendations/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_scenarios_page_guard():
    src = _frontend_src("src/app/dashboard/ai/scenarios/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_logs_page_guard():
    src = _frontend_src("src/app/dashboard/ai/logs/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src


def test_ai_nl_command_page_guard():
    src = _frontend_src("src/app/dashboard/ai/nl-command/page.tsx")
    assert "RequirePermission" in src
    assert "ai.view" in src
