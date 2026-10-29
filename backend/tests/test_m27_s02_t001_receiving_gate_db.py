"""Receiving-gate migration and enforcement checks on a task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text

from app.db.session import AsyncSessionLocal, engine
from app.models.quality import ParameterType, QCType, QCTemplate, QCTemplateParameter
from app.services.qms_service import create_quality_gate_definition, ensure_receiving_quality_gates_pass


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S02_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S02_T001_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"fmcg_m27_s02_t001_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(text("SELECT current_database()"))).scalar_one()
    assert actual == expected


@pytest.mark.asyncio
async def test_migration_adds_template_parameter_reference_and_index():
    async with engine.connect() as connection:
        def inspect_schema(sync_connection):
            inspector = inspect(sync_connection)
            columns = {item["name"] for item in inspector.get_columns("qc_test_results")}
            foreign_keys = inspector.get_foreign_keys("qc_test_results")
            indexes = {item["name"] for item in inspector.get_indexes("qc_test_results")}
            return columns, foreign_keys, indexes

        columns, foreign_keys, indexes = await connection.run_sync(inspect_schema)

    assert "template_parameter_id" in columns
    assert any(
        item["constrained_columns"] == ["template_parameter_id"]
        and item["referred_table"] == "qc_template_parameters"
        for item in foreign_keys
    )
    assert "ix_qc_test_results_template_parameter_id" in indexes


@pytest.mark.asyncio
async def test_active_receiving_gate_blocks_a_grn_line_without_a_passing_template_inspection():
    suffix = uuid4().hex[:20].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        template = QCTemplate(
            name=f"Synthetic receiving gate template {suffix}",
            qc_type=QCType.INCOMING,
            is_mandatory=True,
            blocks_progression=True,
            release_required=True,
        )
        db.add(template)
        await db.flush()
        db.add(QCTemplateParameter(
            template_id=template.id,
            parameter_name=f"Synthetic result {suffix}",
            parameter_type=ParameterType.NUMERIC,
            target_value="5",
            min_value=Decimal("1"),
            max_value=Decimal("10"),
            is_critical=True,
        ))
        await db.flush()
        await create_quality_gate_definition(db, {
            "code": f"RCV_{suffix}",
            "name": f"Synthetic receiving gate {suffix}",
            "gate_type": "INCOMING_QUALITY",
            "trigger_event": "ON_RECEIPT",
            "target_module": "procurement",
            "is_active": True,
            "required_template_ids": [template.id],
        })
        await db.commit()

        grn = SimpleNamespace(
            id=uuid4(),
            grn_no=f"SYNTHETIC-{suffix}",
            received_date=date.today(),
            lines=[SimpleNamespace(
                id=uuid4(), accepted_quantity=Decimal("2"), material_id=uuid4(), product_id=None,
            )],
        )
        with pytest.raises(ValueError, match="no accepted, passed inspection"):
            await ensure_receiving_quality_gates_pass(db, grn)

        await db.rollback()
