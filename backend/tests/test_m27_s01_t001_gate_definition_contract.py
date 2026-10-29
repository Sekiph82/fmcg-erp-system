from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints import qms
from app.api.v1.endpoints.qms import _require_quality_gate_definition_permission
from app.models.quality import ParameterType, QualityGateSeverity
from app.schemas.qms import QCTemplateUpdate, QualityGateDefinitionCreate, QualityGateDefinitionUpdate
from app.services.qms_service import _qc_parameter_has_specification, update_quality_gate_definition


def _user(*permission_codes):
    permissions = [SimpleNamespace(code=code, is_active=True) for code in permission_codes]
    return SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=permissions)],
    )


def test_definition_schema_normalizes_identifiers_without_fixing_gate_vocabulary():
    definition = QualityGateDefinitionCreate(
        code=" incoming_release ",
        name=" Incoming inspection ",
        gate_type=" material_quality ",
        trigger_event=" on_receipt ",
        target_module=" PROCUREMENT ",
        description="  configurable reference  ",
        required_template_ids=[uuid4()],
    )

    assert definition.code == "INCOMING_RELEASE"
    assert definition.gate_type == "MATERIAL_QUALITY"
    assert definition.trigger_event == "ON_RECEIPT"
    assert definition.target_module == "procurement"
    assert definition.description == "configurable reference"


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("code", "   "),
        ("gate_type", "bad-code"),
        ("trigger_event", ""),
        ("target_module", "not a module"),
    ],
)
def test_definition_schema_rejects_blank_or_unsafe_identifiers(field_name, value):
    values = {
        "code": "QC_GATE",
        "name": "Quality gate",
        "gate_type": "QC",
        "trigger_event": "ON_RECEIPT",
        "target_module": "procurement",
        "required_template_ids": [uuid4()],
    }
    values[field_name] = value

    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(**values)


def test_definition_patch_requires_a_change_and_rejects_null_for_required_fields():
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate()
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate(name=None)
    assert QualityGateDefinitionUpdate(is_active=False).is_active is False


def test_active_definition_requires_at_least_one_required_qc_template():
    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(
            code="QC_GATE",
            name="QC gate",
            gate_type="QC",
            trigger_event="ON_RECEIPT",
            target_module="procurement",
        )
    disabled = QualityGateDefinitionCreate(
        code="QC_GATE",
        name="QC gate",
        gate_type="QC",
        trigger_event="ON_RECEIPT",
        target_module="procurement",
        is_active=False,
    )
    assert disabled.required_template_ids == []


def test_gate_policy_defaults_are_conservative_and_configurable():
    definition = QualityGateDefinitionCreate(
        code="QC_GATE",
        name="QC gate",
        gate_type="QC",
        trigger_event="ON_RECEIPT",
        target_module="procurement",
        required_template_ids=[uuid4()],
    )

    assert definition.severity == QualityGateSeverity.MEDIUM
    assert definition.is_mandatory is True
    assert definition.waiver_allowed is False
    assert definition.waiver_reason_required is True
    assert definition.waiver_approval_required is True

    allowed_noncritical_waiver = QualityGateDefinitionCreate(
        code="OPTIONAL_REVIEW",
        name="Optional review",
        gate_type="QC",
        trigger_event="ON_RECEIPT",
        target_module="procurement",
        severity=QualityGateSeverity.HIGH,
        waiver_allowed=True,
        required_template_ids=[uuid4()],
    )
    assert allowed_noncritical_waiver.waiver_allowed is True


@pytest.mark.parametrize(
    "changes",
    [
        {"severity": QualityGateSeverity.CRITICAL, "is_mandatory": False},
        {"severity": QualityGateSeverity.CRITICAL, "waiver_allowed": True},
        {"waiver_allowed": True, "waiver_reason_required": False},
        {"waiver_allowed": True, "waiver_approval_required": False},
    ],
)
def test_gate_policy_rejects_unsafe_severity_and_waiver_combinations(changes):
    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(
            code="QC_GATE",
            name="QC gate",
            gate_type="QC",
            trigger_event="ON_RECEIPT",
            target_module="procurement",
            required_template_ids=[uuid4()],
            **changes,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"severity": QualityGateSeverity.CRITICAL, "is_mandatory": False},
        {"severity": QualityGateSeverity.CRITICAL, "waiver_allowed": True},
        {"waiver_allowed": True, "waiver_approval_required": False},
    ],
)
def test_gate_policy_patch_rejects_explicitly_unsafe_combinations(changes):
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate(**changes)


def test_gate_versions_require_positive_numbers_and_valid_effective_windows():
    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(
            code="QC_GATE", name="QC gate", gate_type="QC", trigger_event="ON_RECEIPT",
            target_module="procurement", version=0,
        )
    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(
            code="QC_GATE", name="QC gate", gate_type="QC", trigger_event="ON_RECEIPT",
            target_module="procurement", effective_from=date(2026, 10, 20),
            effective_to=date(2026, 10, 19),
        )
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate(effective_from=None)

    today = date.today()
    future = QualityGateDefinitionCreate(
        code="QC_GATE", name="QC gate", gate_type="QC", trigger_event="ON_RECEIPT",
        target_module="procurement", version=2, effective_from=today + timedelta(days=5),
        effective_to=None, is_active=False,
    )
    assert future.version == 2
    assert future.effective_to is None


@pytest.mark.asyncio
async def test_gate_policy_patch_checks_combined_persisted_rule_values():
    class LockOnlyDB:
        async def execute(self, _statement):
            return None

    definition = SimpleNamespace(
        code="POLICY_GATE",
        effective_from=date.today() + timedelta(days=1),
        effective_to=None,
        severity="HIGH",
        is_mandatory=True,
        waiver_allowed=False,
        waiver_reason_required=False,
        waiver_approval_required=True,
        is_active=False,
        required_templates=[],
    )

    with pytest.raises(ValueError, match="must require a reason"):
        await update_quality_gate_definition(LockOnlyDB(), definition, {"waiver_allowed": True})

    assert definition.waiver_allowed is True


def test_definition_reads_require_global_quality_read_permission():
    with pytest.raises(HTTPException) as exc:
        _require_quality_gate_definition_permission(_user("quality.view"), "view")
    assert exc.value.status_code == 403
    _require_quality_gate_definition_permission(_user("quality.view_all"), "view")
    _require_quality_gate_definition_permission(_user("quality.gate_configure"), "view")


def test_definition_writes_require_quality_gate_configuration_permission():
    with pytest.raises(HTTPException) as exc:
        _require_quality_gate_definition_permission(_user("quality.edit_all"), "edit")
    assert exc.value.status_code == 403
    _require_quality_gate_definition_permission(_user("quality.gate_configure"), "edit")


@pytest.mark.parametrize(
    "parameter_type,target,minimum,maximum,expected",
    [
        (ParameterType.NUMERIC, None, None, None, False),
        (ParameterType.NUMERIC, "5", 1, 10, True),
        (ParameterType.NUMERIC, "11", 1, 10, False),
        (ParameterType.NUMERIC, None, 1, 10, True),
        (ParameterType.NUMERIC, "NaN", None, None, False),
        (ParameterType.TEXT, "  pass  ", None, None, True),
        (ParameterType.TEXT, None, None, None, False),
        (ParameterType.BOOLEAN, "true", None, None, True),
        (ParameterType.BOOLEAN, "yes", None, None, False),
        (ParameterType.PASS_FAIL, "PASS", None, None, True),
        (ParameterType.PASS_FAIL, "FAIL", None, None, False),
    ],
)
def test_gate_specification_requires_type_appropriate_acceptance_criteria(
    parameter_type, target, minimum, maximum, expected
):
    parameter = SimpleNamespace(
        parameter_type=parameter_type,
        target_value=target,
        min_value=minimum,
        max_value=maximum,
    )
    assert _qc_parameter_has_specification(parameter) is expected


@pytest.mark.asyncio
async def test_create_route_denies_writer_without_gate_configuration_permission(monkeypatch):
    called = False

    async def create_should_not_run(_db, _data):
        nonlocal called
        called = True

    monkeypatch.setattr(qms.svc, "create_quality_gate_definition", create_should_not_run)
    body = QualityGateDefinitionCreate(
        code="QC_GATE", name="QC gate", gate_type="QC",
        trigger_event="ON_RECEIPT", target_module="procurement", required_template_ids=[uuid4()],
    )

    with pytest.raises(HTTPException) as exc:
        await qms.create_quality_gate_definition(body, object(), _user("quality.view_all"))

    assert exc.value.status_code == 403
    assert called is False


class _IntegrityFailingDB:
    def __init__(self):
        self.rollback_called = False

    async def commit(self):
        original = SimpleNamespace(
            diag=SimpleNamespace(constraint_name="uq_quality_gate_definitions_code")
        )
        raise IntegrityError("insert", {}, original)

    async def rollback(self):
        self.rollback_called = True


@pytest.mark.asyncio
async def test_create_route_returns_conflict_for_duplicate_gate_code(monkeypatch):
    async def create_definition(_db, data):
        return SimpleNamespace(id=uuid4(), **data)

    monkeypatch.setattr(qms.svc, "create_quality_gate_definition", create_definition)
    body = QualityGateDefinitionCreate(
        code="QC_GATE", name="QC gate", gate_type="QC",
        trigger_event="ON_RECEIPT", target_module="procurement", required_template_ids=[uuid4()],
    )
    db = _IntegrityFailingDB()

    with pytest.raises(HTTPException) as exc:
        await qms.create_quality_gate_definition(body, db, _user("quality.gate_configure"))

    assert exc.value.status_code == 409
    assert db.rollback_called is True


class _TemplateMutationDB:
    def __init__(self):
        self.rollback_called = False
        self.commit_called = False
        self.delete_called = False

    async def rollback(self):
        self.rollback_called = True

    async def commit(self):
        self.commit_called = True

    async def delete(self, _template):
        self.delete_called = True


@pytest.mark.asyncio
async def test_template_patch_rejects_weakening_a_test_used_by_active_gate(monkeypatch):
    template = SimpleNamespace(id=uuid4(), is_active=True, is_mandatory=True,
                               blocks_progression=True, release_required=True, parameters=[])

    async def get_template(_db, _template_id, *, for_update=False):
        assert for_update is True
        return template

    async def reject_change(_db, _template, changes):
        assert changes == {"is_active": False}
        raise ValueError("active gate conflict")

    monkeypatch.setattr(qms.svc, "get_template", get_template)
    monkeypatch.setattr(qms.svc, "ensure_qc_template_change_preserves_active_gates", reject_change)
    db = _TemplateMutationDB()

    with pytest.raises(HTTPException) as exc:
        await qms.update_template(uuid4(), QCTemplateUpdate(is_active=False), db, _user())

    assert exc.value.status_code == 409
    assert db.rollback_called is True
    assert db.commit_called is False
    assert template.is_active is True


@pytest.mark.asyncio
async def test_template_delete_rejects_a_template_still_linked_to_a_gate(monkeypatch):
    template = SimpleNamespace(id=uuid4())

    async def get_template(_db, _template_id, *, for_update=False):
        assert for_update is True
        return template

    async def reject_delete(_db, _template_id):
        raise ValueError("linked template conflict")

    monkeypatch.setattr(qms.svc, "get_template", get_template)
    monkeypatch.setattr(qms.svc, "ensure_qc_template_can_be_deleted", reject_delete)
    db = _TemplateMutationDB()

    with pytest.raises(HTTPException) as exc:
        await qms.delete_template(uuid4(), db, _user())

    assert exc.value.status_code == 409
    assert db.rollback_called is True
    assert db.delete_called is False
    assert db.commit_called is False
