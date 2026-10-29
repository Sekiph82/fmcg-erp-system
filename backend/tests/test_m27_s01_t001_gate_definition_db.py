"""Gate-definition storage checks on a task-owned disposable PostgreSQL database."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal, engine
from app.models.quality import (
    ParameterType,
    QCType,
    QCTemplate,
    QCTemplateParameter,
    QualityGateDefinition,
)
from app.schemas.qms import QualityGateDefinitionRead
from app.services.qms_service import (
    create_quality_gate_definition,
    ensure_qc_template_change_preserves_active_gates,
    get_quality_gate_definition,
    get_template,
    list_quality_gate_definitions,
    create_quality_gate_definition,
    update_quality_gate_definition,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S01_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S01_T001_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"fmcg_m27_s01_t001_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(text("SELECT current_database()"))).scalar_one()
    assert actual == expected


async def _create_required_template(db, suffix: str) -> QCTemplate:
    template = QCTemplate(
        name=f"Synthetic gate QC {suffix}",
        qc_type=QCType.INCOMING,
        is_mandatory=True,
        blocks_progression=True,
        release_required=True,
    )
    db.add(template)
    await db.flush()
    db.add(
        QCTemplateParameter(
            template_id=template.id,
            parameter_name=f"Specification {suffix}",
            parameter_type=ParameterType.NUMERIC,
            unit="unit",
            target_value="5",
            min_value=1,
            max_value=10,
            is_critical=True,
        )
    )
    await db.flush()
    return template


@pytest.mark.asyncio
async def test_gate_definition_can_be_configured_and_filtered_by_trigger_and_module():
    suffix = uuid4().hex[:16].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = await _create_required_template(db, suffix)
        template_id = template.id
        created = await create_quality_gate_definition(
            db,
            {
                "code": f"TEST_GATE_{suffix}",
                "name": "Synthetic receiving gate",
                "gate_type": "MATERIAL_QUALITY",
                "trigger_event": "ON_RECEIPT",
                "target_module": "procurement",
                "description": "Synthetic test configuration only",
                "is_active": True,
                "required_template_ids": [template.id],
            },
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        found = await list_quality_gate_definitions(
            db, trigger_event="ON_RECEIPT", target_module="procurement"
        )
        assert [item.code for item in found] == [f"TEST_GATE_{suffix}"]
        assert found[0].id == created.id
        read_model = QualityGateDefinitionRead.model_validate(found[0])
        assert read_model.required_template_ids == [template_id]
        assert len(read_model.required_templates) == 1
        assert read_model.required_templates[0].parameters[0].parameter_name == f"Specification {suffix}"
        assert read_model.severity.value == "MEDIUM"
        assert read_model.is_mandatory is True
        assert read_model.waiver_allowed is False
        assert read_model.waiver_reason_required is True
        assert read_model.waiver_approval_required is True
        assert read_model.version == 1
        assert read_model.effective_from == date.today()
        assert read_model.effective_to is None


@pytest.mark.asyncio
async def test_gate_definition_codes_are_unique_in_the_database():
    code = f"UNIQUE_GATE_{uuid4().hex[:16].upper()}"
    data = {
        "code": code,
        "name": "Synthetic unique gate",
        "gate_type": "MATERIAL_QUALITY",
        "trigger_event": "ON_RECEIPT",
        "target_module": "procurement",
        "is_active": True,
    }
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = await _create_required_template(db, uuid4().hex[:12].upper())
        await create_quality_gate_definition(db, {**data, "required_template_ids": [template.id]})
        await db.commit()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        duplicate = QualityGateDefinition(**data)
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
        existing = await db.scalar(
            select(QualityGateDefinition).where(QualityGateDefinition.code == code)
        )
        assert existing is not None


@pytest.mark.asyncio
async def test_active_gate_rejects_qc_template_without_specification_parameters():
    suffix = uuid4().hex[:16].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = QCTemplate(
            name=f"Synthetic incomplete QC {suffix}",
            qc_type=QCType.INCOMING,
            is_mandatory=True,
            blocks_progression=True,
            release_required=True,
        )
        db.add(template)
        await db.flush()
        with pytest.raises(ValueError, match="specification parameter"):
            await create_quality_gate_definition(
                db,
                {
                    "code": f"INCOMPLETE_GATE_{suffix}",
                    "name": "Synthetic incomplete gate",
                    "gate_type": "MATERIAL_QUALITY",
                    "trigger_event": "ON_RECEIPT",
                    "target_module": "procurement",
                    "required_template_ids": [template.id],
                    "is_active": True,
                },
            )
        await db.rollback()


@pytest.mark.asyncio
async def test_active_gate_rejects_parameter_row_without_acceptance_criteria():
    suffix = uuid4().hex[:16].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = QCTemplate(
            name=f"Synthetic blank-spec QC {suffix}",
            qc_type=QCType.INCOMING,
            is_mandatory=True,
            blocks_progression=True,
            release_required=True,
        )
        db.add(template)
        await db.flush()
        db.add(
            QCTemplateParameter(
                template_id=template.id,
                parameter_name=f"Unspecified acceptance {suffix}",
                parameter_type=ParameterType.NUMERIC,
                unit="unit",
                target_value=None,
                min_value=None,
                max_value=None,
                is_critical=True,
            )
        )
        await db.flush()
        with pytest.raises(ValueError, match="specification parameter"):
            await create_quality_gate_definition(
                db,
                {
                    "code": f"BLANK_SPEC_GATE_{suffix}",
                    "name": "Synthetic blank-spec gate",
                    "gate_type": "MATERIAL_QUALITY",
                    "trigger_event": "ON_RECEIPT",
                    "target_module": "procurement",
                    "required_template_ids": [template.id],
                    "is_active": True,
                },
            )
        await db.rollback()


@pytest.mark.asyncio
async def test_concurrent_gate_activation_serializes_against_template_weakening():
    suffix = uuid4().hex[:16].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = await _create_required_template(db, suffix)
        template_id = template.id
        definition = QualityGateDefinition(
            code=f"RACE_GATE_{suffix}",
            name="Synthetic activation race gate",
            gate_type="MATERIAL_QUALITY",
            trigger_event="ON_RECEIPT",
            target_module="procurement",
            is_active=False,
            required_templates=[template],
        )
        db.add(definition)
        await db.commit()
        definition_id = definition.id

    activation_validated = asyncio.Event()
    allow_activation_commit = asyncio.Event()
    weakening_attempted = asyncio.Event()

    async def activate_existing_gate():
        async with AsyncSessionLocal() as db:
            await _assert_task_database(db)
            definition = await get_quality_gate_definition(db, definition_id, for_update=True)
            await update_quality_gate_definition(db, definition, {"is_active": True})
            activation_validated.set()
            await allow_activation_commit.wait()
            await db.commit()

    async def try_weaken_template():
        await activation_validated.wait()
        async with AsyncSessionLocal() as db:
            await _assert_task_database(db)
            weakening_attempted.set()
            template = await get_template(db, template_id, for_update=True)
            with pytest.raises(ValueError, match="active quality gate"):
                await ensure_qc_template_change_preserves_active_gates(
                    db, template, {"is_active": False}
                )
            await db.rollback()

    activation = asyncio.create_task(activate_existing_gate())
    weakening = asyncio.create_task(try_weaken_template())
    await activation_validated.wait()
    await weakening_attempted.wait()
    await asyncio.sleep(0.1)
    allow_activation_commit.set()
    await asyncio.gather(activation, weakening)

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        definition = await get_quality_gate_definition(db, definition_id)
        template = await get_template(db, template_id)
        assert definition.is_active is True
        assert template.is_active is True


@pytest.mark.asyncio
async def test_database_rejects_critical_or_waiver_policy_without_safeguards():
    suffix = uuid4().hex[:12].upper()
    invalid_policies = [
        {"severity": "CRITICAL", "is_mandatory": False},
        {"severity": "CRITICAL", "waiver_allowed": True},
        {"waiver_allowed": True, "waiver_approval_required": False},
        {"waiver_allowed": True, "waiver_reason_required": False},
        {"severity": "UNKNOWN"},
    ]

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        for index, policy in enumerate(invalid_policies):
            db.add(
                QualityGateDefinition(
                    code=f"INVALID_POLICY_{suffix}_{index}",
                    name="Synthetic invalid policy",
                    gate_type="QC",
                    trigger_event="ON_RECEIPT",
                    target_module="procurement",
                    **policy,
                )
            )
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()


@pytest.mark.asyncio
async def test_gate_versions_are_sequential_non_overlapping_and_selected_by_as_of_date():
    suffix = uuid4().hex[:12].upper()
    code = f"VERSIONED_GATE_{suffix}"
    today = date.today()
    first_end = today + timedelta(days=1)
    second_start = today + timedelta(days=2)
    common = {
        "code": code,
        "gate_type": "MATERIAL_QUALITY",
        "trigger_event": "ON_RECEIPT",
        "target_module": "procurement",
        "is_active": True,
        "required_template_ids": [],
    }

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        first_template = await _create_required_template(db, f"{suffix}01")
        first = await create_quality_gate_definition(
            db,
            {
                **common,
                "version": 1,
                "name": "Synthetic gate version one",
                "is_active": True,
                "required_template_ids": [first_template.id],
                "effective_from": today - timedelta(days=3),
                "effective_to": None,
            },
        )
        first_id = first.id
        await update_quality_gate_definition(db, first, {"effective_to": first_end})
        second_template = await _create_required_template(db, f"{suffix}02")
        second = await create_quality_gate_definition(
            db,
            {
                **common,
                "version": 2,
                "name": "Synthetic gate version two",
                "is_active": True,
                "required_template_ids": [second_template.id],
                "effective_from": second_start,
                "effective_to": None,
            },
        )
        second_id = second.id
        await db.commit()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        today_versions = await list_quality_gate_definitions(db, as_of_date=today)
        future_versions = await list_quality_gate_definitions(db, as_of_date=second_start)
        today_ids = {definition.id for definition in today_versions}
        future_ids = {definition.id for definition in future_versions}
        assert first_id in today_ids
        assert second_id not in today_ids
        assert first_id not in future_ids
        assert second_id in future_ids

        with pytest.raises(ValueError, match="cannot overlap"):
            await create_quality_gate_definition(
                db,
                {
                    **common,
                    "version": 3,
                    "name": "Synthetic overlapping gate version",
                    "is_active": False,
                    "effective_from": first_end,
                    "effective_to": second_start + timedelta(days=1),
                },
            )
        await db.rollback()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        first = await get_quality_gate_definition(db, first_id, for_update=True)
        with pytest.raises(ValueError, match="cannot be rewritten"):
            await update_quality_gate_definition(
                db, first, {"effective_to": first_end + timedelta(days=1)}
            )
        with pytest.raises(ValueError, match="effective quality gate version is immutable"):
            await update_quality_gate_definition(
                db,
                first,
                {
                    "effective_from": today + timedelta(days=10),
                    "name": "Synthetic retroactive rename",
                },
            )
        await db.rollback()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        second = await get_quality_gate_definition(db, second_id, for_update=True)
        with pytest.raises(ValueError, match="cannot overlap"):
            await update_quality_gate_definition(db, second, {"effective_from": first_end})
        await db.rollback()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        with pytest.raises(ValueError, match="next version.*3"):
            await create_quality_gate_definition(
                db,
                {
                    **common,
                    "version": 4,
                    "name": "Synthetic skipped gate version",
                    "is_active": False,
                    "effective_from": second_start + timedelta(days=2),
                },
            )
        await db.rollback()
