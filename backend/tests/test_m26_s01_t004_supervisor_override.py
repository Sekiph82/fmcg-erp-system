from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.machine_operator import AssignmentHistory, AssignmentType, ReviewType, SupervisorReview
from app.schemas.machine_operator import AssignmentCreate, AssignmentValidateResult
from app.services import machine_operator_service as service


class _Session:
    def __init__(self):
        self.added = []

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, record):
        return None


class _Result:
    def __init__(self, record):
        self.record = record

    def scalar_one_or_none(self):
        return self.record

    def scalars(self):
        return self

    def all(self):
        return [self.record] if self.record is not None else []


class _ScopedSession:
    def __init__(self, *records):
        self.records = list(records)

    async def execute(self, _statement):
        return _Result(self.records.pop(0))


def _actor(*permissions):
    return SimpleNamespace(
        id=uuid4(),
        is_superuser=False,
        roles=[
            SimpleNamespace(
                is_active=True,
                permissions=[SimpleNamespace(code=code, is_active=True) for code in permissions],
            )
        ],
    )


def _scoped_approver(line_id):
    return SimpleNamespace(
        id=uuid4(),
        is_superuser=False,
        roles=[
            SimpleNamespace(
                is_active=True,
                permissions=[SimpleNamespace(code="production.approve_own_scope", is_active=True)],
                access_scopes=[
                    SimpleNamespace(
                        scope_type="production_line",
                        scope_id=line_id,
                        is_active=True,
                        can_approve=True,
                    )
                ],
            )
        ],
    )


def _validation(*blocks):
    return AssignmentValidateResult(
        valid=not blocks,
        warnings=[],
        blocks=list(blocks),
        operator_certified=not blocks,
        machine_available=True,
    )


@pytest.mark.asyncio
async def test_supervisor_override_records_actor_reason_and_failed_validation(monkeypatch):
    blocked = "Operator lacks an approved basic qualification for the configured skill"

    async def validate(*_args, **_kwargs):
        return _validation(blocked)

    monkeypatch.setattr(service, "validate_assignment", validate)
    db = _Session()
    actor = _actor("production.approve")
    payload = AssignmentCreate(
        work_order_id=uuid4(),
        operator_id=uuid4(),
        cert_override_flag=True,
        cert_override_reason="Temporary coverage approved for this shift",
    )

    assignment = await service.create_assignment(db, payload, actor=actor)

    assert assignment.cert_override_flag is True
    assert assignment.cert_override_reason == "Temporary coverage approved for this shift"
    assert assignment.cert_validation_passed is False
    history = [row for row in db.added if isinstance(row, AssignmentHistory)]
    operator_assignment = next(row for row in history if row.assignment_type == AssignmentType.OPERATOR)
    assert operator_assignment.changed_by == actor.id
    assert operator_assignment.reason.startswith("Supervisor qualification override:")
    review = next(row for row in db.added if isinstance(row, SupervisorReview))
    assert review.review_type == ReviewType.CERT_OVERRIDE
    assert review.reviewed_by == actor.id
    assert "Temporary coverage approved for this shift" in review.comments


@pytest.mark.asyncio
async def test_override_requires_approval_permission(monkeypatch):
    async def validate(*_args, **_kwargs):
        return _validation("Operator lacks an approved basic qualification for the configured skill")

    monkeypatch.setattr(service, "validate_assignment", validate)
    payload = AssignmentCreate(
        work_order_id=uuid4(),
        cert_override_flag=True,
        cert_override_reason="Approved exception",
    )

    with pytest.raises(ValueError, match="(?i)production approval permission"):
        await service.create_assignment(_Session(), payload, actor=_actor("production.edit"))


@pytest.mark.asyncio
async def test_override_does_not_bypass_machine_or_work_order_blockers(monkeypatch):
    async def validate(*_args, **_kwargs):
        return _validation("Machine not found")

    monkeypatch.setattr(service, "validate_assignment", validate)
    payload = AssignmentCreate(
        work_order_id=uuid4(),
        cert_override_flag=True,
        cert_override_reason="Approved exception",
    )

    with pytest.raises(ValueError, match="qualification check blocks assignment"):
        await service.create_assignment(_Session(), payload, actor=_actor("production.approve"))


@pytest.mark.asyncio
async def test_override_requires_a_non_empty_reason(monkeypatch):
    async def validate(*_args, **_kwargs):
        return _validation("Certification expired for this machine")

    monkeypatch.setattr(service, "validate_assignment", validate)
    payload = AssignmentCreate(
        work_order_id=uuid4(),
        cert_override_flag=True,
        cert_override_reason="  ",
    )

    with pytest.raises(ValueError, match="non-empty audit reason"):
        await service.create_assignment(_Session(), payload, actor=_actor("production.approve"))


@pytest.mark.asyncio
async def test_reason_is_rejected_without_an_override(monkeypatch):
    async def validate(*_args, **_kwargs):
        return _validation()

    monkeypatch.setattr(service, "validate_assignment", validate)
    payload = AssignmentCreate(
        work_order_id=uuid4(),
        cert_override_flag=False,
        cert_override_reason="   ",
    )

    with pytest.raises(ValueError, match="reason can only be supplied"):
        await service.create_assignment(_Session(), payload, actor=_actor("production.edit"))


@pytest.mark.asyncio
async def test_scoped_supervisor_can_override_only_within_their_line():
    work_center_id = uuid4()
    machine_id = uuid4()
    work_order = SimpleNamespace(work_center_id=work_center_id)
    machine = SimpleNamespace(
        id=machine_id,
        work_center_id=work_center_id,
        plant_id=None,
        section_id=None,
        line_id="LINE-7",
    )

    assert await service._has_work_order_scope_permission(
        _ScopedSession(work_order, machine),
        _scoped_approver("LINE-7"),
        action="approve",
        work_order_id=uuid4(),
        machine_id=machine_id,
    )
    assert not await service._has_work_order_scope_permission(
        _ScopedSession(work_order, machine),
        _scoped_approver("LINE-8"),
        action="approve",
        work_order_id=uuid4(),
        machine_id=machine_id,
    )
