"""M34.S03.T004 supplier corrective-action linkage contracts."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import qms as qms_endpoint
from app.models.quality import CorrectiveAction
from app.schemas.qms import CorrectiveActionCreate, CorrectiveActionUpdate, CorrectiveActionRead


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_supplier_capa_link_is_optional_and_migration_is_additive():
    columns = {column.key: column for column in CorrectiveAction.__table__.columns}
    assert columns["supplier_id"].nullable is True
    assert columns["supplier_evaluation_id"].nullable is True
    assert {fk.target_fullname for fk in columns["supplier_id"].foreign_keys} == {"suppliers.id"}
    assert {fk.target_fullname for fk in columns["supplier_evaluation_id"].foreign_keys} == {"supplier_evaluations.id"}
    assert "supplier_id" in CorrectiveActionCreate.model_fields
    assert "supplier_evaluation_id" in CorrectiveActionCreate.model_fields
    assert "supplier_name" in CorrectiveActionRead.model_fields
    assert "supplier_id" not in CorrectiveActionUpdate.model_fields
    migration = (REPO_ROOT / "alembic/versions/20261104_0001_supplier_corrective_action_linkage.py").read_text()
    assert 'down_revision = "20261030_0010"' in migration
    assert 'op.add_column(' in migration and 'op.drop_column(' in migration
    assert "ondelete=\"SET NULL\"" in migration


def test_supplier_capa_read_requires_quality_view_permission():
    reader = SimpleNamespace(is_superuser=False, permissions=set(), roles=[])
    with pytest.raises(HTTPException) as denied:
        qms_endpoint._require_supplier_capa_permission(reader, "view")
    assert denied.value.status_code == 403


def test_supplier_capa_link_permission_actions_are_separate():
    reader = SimpleNamespace(is_superuser=False, permissions=set(), roles=[])
    with pytest.raises(HTTPException) as denied:
        qms_endpoint._require_supplier_capa_permission(reader, "create")
    assert denied.value.status_code == 403
