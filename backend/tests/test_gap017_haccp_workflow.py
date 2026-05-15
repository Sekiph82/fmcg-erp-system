"""GAP-017: HACCP Audit-Grade Workflow Completion — focused tests."""
from __future__ import annotations


# ── Registry / module contract ────────────────────────────────────────────────

def test_quality_in_module_definitions():
    from app.core.module_registry import MODULE_DEFINITIONS
    keys = [m.key for m in MODULE_DEFINITIONS]
    assert "quality" in keys, "quality module not in MODULE_DEFINITIONS"


def test_quality_permission_actions():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "quality")
    required = {"view", "create", "edit", "approve", "export"}
    assert required.issubset(set(m.permission_actions)), (
        f"quality missing actions: {required - set(m.permission_actions)}"
    )


def test_quality_is_critical():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "quality")
    assert m.critical is True, "quality module should be critical"


def test_quality_permission_codes_in_registry():
    from app.core.module_registry import registry_permission_codes
    codes = registry_permission_codes()
    for action in ("view", "create", "edit", "approve", "export"):
        assert f"quality.{action}" in codes, f"quality.{action} missing from registry"


# ── ORM model contract ────────────────────────────────────────────────────────

def test_corrective_action_has_pdca_closed_at():
    from app.models.quality import CorrectiveAction
    cols = {c.key for c in CorrectiveAction.__table__.columns}
    assert "pdca_closed_at" in cols, "CorrectiveAction missing pdca_closed_at column"


def test_audit_checklist_has_scheduling_columns():
    from app.models.quality import QualityAuditChecklist
    cols = {c.key for c in QualityAuditChecklist.__table__.columns}
    assert "scheduled_date" in cols, "QualityAuditChecklist missing scheduled_date"
    assert "recurrence_days" in cols, "QualityAuditChecklist missing recurrence_days"


# ── Schema contract ───────────────────────────────────────────────────────────

def test_corrective_action_read_has_pdca_closed_at():
    from app.schemas.qms import CorrectiveActionRead
    assert "pdca_closed_at" in CorrectiveActionRead.model_fields


def test_corrective_action_update_has_pdca_closed_at():
    from app.schemas.qms import CorrectiveActionUpdate
    assert "pdca_closed_at" in CorrectiveActionUpdate.model_fields


def test_audit_checklist_schemas_have_scheduling_fields():
    from app.schemas.qms import AuditChecklistBase, AuditChecklistRead, AuditChecklistUpdate
    for schema in (AuditChecklistBase, AuditChecklistRead, AuditChecklistUpdate):
        assert "scheduled_date" in schema.model_fields, f"{schema.__name__} missing scheduled_date"
        assert "recurrence_days" in schema.model_fields, f"{schema.__name__} missing recurrence_days"


# ── Migration head ────────────────────────────────────────────────────────────

def test_alembic_haccp_migration_in_chain():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "history"],
        capture_output=True, text=True,
        cwd=__file__[:__file__.index("tests")],
    )
    assert "20260515_0050" in result.stdout, (
        "Migration 20260515_0050 (HACCP PDCA + audit scheduling) not found in Alembic history"
    )
