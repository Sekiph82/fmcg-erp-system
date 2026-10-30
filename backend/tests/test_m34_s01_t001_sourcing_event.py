"""M34.S01.T001 event-model coverage; PostgreSQL writes require an exact disposable target."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import create_rfq, get_rfq, list_rfqs
from app.db.session import AsyncSessionLocal, engine
from app.models.procurement import RFQLine, RFQRequest
from app.schemas.procurement import RFQCreate


TASK_DB_ENV = "M34_S01_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S01_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s01_t001_[a-f0-9]{24}")


def _is_task_database(url, expected_name: str | None) -> bool:
    return bool(
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and TASK_DB_PATTERN.fullmatch(expected_name)
        and url.database == expected_name
    )


def _require_task_database() -> None:
    expected_name = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1":
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for the task-owned disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's exact passwordless loopback database.")


def test_database_guard_rejects_wrong_database_or_remote_target():
    name = "fmcg_m34_s01_t001_0123456789abcdef01234567"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m34_s01_t002_0123456789abcdef01234567")
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="user", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


def test_rfq_create_accepts_existing_single_item_and_multi_line_event_shapes():
    legacy = RFQCreate(rfq_no="RFQ-LEGACY", title="Existing item", quantity="3.000", unit="KG")
    event = RFQCreate(
        rfq_no="RFQ-EVENT",
        title="Synthetic ingredient sourcing event",
        lines=[
            {"line_no": 2, "description": "Packaging item", "quantity": "100", "unit": "PCS"},
            {"line_no": 1, "description": "Base ingredient", "quantity": "25.5", "unit": "KG"},
        ],
    )

    assert legacy.quantity == 3
    assert legacy.lines == []
    assert event.quantity is None
    assert [line.line_no for line in event.lines] == [2, 1]


@pytest.mark.parametrize(
    "payload",
    [
        {"rfq_no": "RFQ-EMPTY", "title": "No requirement"},
        {
            "rfq_no": "RFQ-MIXED",
            "title": "Ambiguous requirement",
            "quantity": "1",
            "lines": [{"line_no": 1, "description": "Line", "quantity": "1"}],
        },
        {
            "rfq_no": "RFQ-DUPLICATE",
            "title": "Duplicate numbers",
            "lines": [
                {"line_no": 1, "description": "First", "quantity": "1"},
                {"line_no": 1, "description": "Second", "quantity": "2"},
            ],
        },
        {
            "rfq_no": "RFQ-BAD-LINE",
            "title": "Unidentified line",
            "lines": [{"line_no": 1, "quantity": "1"}],
        },
        {
            "rfq_no": "RFQ-NONFINITE-LINE",
            "title": "Non-finite line quantity",
            "lines": [{"line_no": 1, "description": "Invalid", "quantity": "Infinity"}],
        },
        {"rfq_no": "RFQ-SCALE", "title": "Excess scale", "quantity": "1.0001"},
        {"rfq_no": "RFQ-PRECISION", "title": "Excess precision", "quantity": "100000000000"},
    ],
)
def test_rfq_create_rejects_missing_ambiguous_or_duplicate_sourcing_requirements(payload):
    with pytest.raises(ValueError):
        RFQCreate(**payload)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL database")
async def test_sourcing_event_lines_persist_and_return_through_existing_rfq_routes():
    _require_task_database()
    suffix = uuid4().hex[:16]
    rfq_no = f"M34-T001-{suffix}"
    actor = SimpleNamespace(id=None, is_superuser=True, roles=[])
    rfq_id = None
    legacy_rfq_id = None
    try:
        body = RFQCreate(
            rfq_no=rfq_no,
            title="Synthetic multi-line tender",
            description="Disposable M34.S01.T001 fixture; not owner procurement data.",
            lines=[
                {"line_no": 1, "description": "Synthetic bottle resin", "quantity": "25", "unit": "KG"},
                {"line_no": 2, "description": "Synthetic closures", "quantity": "1000", "unit": "PCS"},
            ],
        )
        async with AsyncSessionLocal() as db:
            created = await create_rfq(body, db, actor)
            rfq_id = created.id
            assert created.quantity is None
            assert created.line_count == 2
            assert [line.line_no for line in created.lines] == [1, 2]
            assert [line.quantity for line in created.lines] == [25, 1000]

        async with AsyncSessionLocal() as db:
            legacy = await create_rfq(
                RFQCreate(rfq_no=f"M34-T001-LEGACY-{suffix}", title="Synthetic legacy RFQ", quantity="3", unit="KG"),
                db,
                actor,
            )
            legacy_rfq_id = legacy.id
            assert legacy.quantity == 3
            assert legacy.lines == []

        async with AsyncSessionLocal() as db:
            detail = await get_rfq(rfq_id, db, actor)
            assert detail.rfq_no == rfq_no
            assert detail.line_count == 2
            assert [line.unit for line in detail.lines] == ["KG", "PCS"]
            assert detail.status.value == "DRAFT"

        async with AsyncSessionLocal() as db:
            rows = await list_rfqs(None, 200, db, actor)
            event_row = next(row for row in rows if row.id == rfq_id)
            legacy_row = next(row for row in rows if row.id == legacy_rfq_id)
            assert event_row.line_count == 2
            assert legacy_row.quantity == 3

        async with AsyncSessionLocal() as db:
            for line_no, invalid_quantity in ((99, Decimal("NaN")), (100, Decimal("Infinity"))):
                db.add(RFQLine(
                    rfq_id=rfq_id,
                    line_no=line_no,
                    description="Invalid direct-database quantity",
                    quantity=invalid_quantity,
                    unit="KG",
                ))
                with pytest.raises(DBAPIError):
                    await db.flush()
                await db.rollback()
    finally:
        if rfq_id is not None:
            async with AsyncSessionLocal() as db:
                await db.execute(delete(RFQLine).where(RFQLine.rfq_id == rfq_id))
                await db.execute(delete(RFQRequest).where(RFQRequest.id == rfq_id))
                if legacy_rfq_id is not None:
                    await db.execute(delete(RFQRequest).where(RFQRequest.id == legacy_rfq_id))
                await db.commit()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL database")
async def test_migration_replaces_weak_checks_on_an_existing_sourcing_line_table():
    """Adoption must enforce the same quantity/line rules as a fresh install."""
    _require_task_database()
    backend_root = Path(__file__).resolve().parents[1]
    await engine.dispose()

    def run_alembic(*args: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend_root,
            env=os.environ.copy(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode:
            raise AssertionError(f"alembic {' '.join(args)} failed ({result.returncode}):\n{result.stdout}")

    run_alembic("downgrade", "-1")
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE TABLE rfq_request_lines (
                    id UUID PRIMARY KEY,
                    rfq_id UUID NOT NULL,
                    line_no INTEGER NOT NULL,
                    material_id UUID NULL,
                    product_id UUID NULL,
                    description VARCHAR(500) NULL,
                    quantity NUMERIC(14, 3) NOT NULL,
                    unit VARCHAR(20) NOT NULL,
                    required_by DATE NULL,
                    notes VARCHAR(1000) NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    CONSTRAINT ck_rfq_request_line_number_positive CHECK (line_no >= 0),
                    CONSTRAINT ck_rfq_request_line_quantity_positive CHECK (quantity >= 0),
                    CONSTRAINT uq_rfq_request_line UNIQUE (rfq_id, line_no),
                    CONSTRAINT fk_rfq_request_lines_rfq_id_rfq_requests FOREIGN KEY (rfq_id) REFERENCES rfq_requests(id) ON DELETE RESTRICT,
                    CONSTRAINT fk_rfq_request_lines_material_id_materials FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
                    CONSTRAINT fk_rfq_request_lines_product_id_products FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
                """
            )
        )
        await connection.execute(
            text(
                "CREATE INDEX ix_rfq_request_lines_rfq_id ON rfq_request_lines (rfq_id)"
            )
        )

    run_alembic("upgrade", "head")
    await engine.dispose()
    async with engine.connect() as connection:
        checks = await connection.execute(
            text(
                """
                SELECT conname, pg_get_constraintdef(oid) AS expression
                FROM pg_constraint
                WHERE conrelid = 'rfq_request_lines'::regclass AND contype = 'c'
                """
            )
        )
        by_name = {row.conname: row.expression for row in checks}
        foreign_keys = await connection.execute(
            text(
                """
                SELECT conname, pg_get_constraintdef(oid) AS expression
                FROM pg_constraint
                WHERE conrelid = 'rfq_request_lines'::regclass AND contype = 'f'
                """
            )
        )
        fk_by_name = {row.conname: row.expression for row in foreign_keys}
    assert "line_no > 0" in by_name["ck_rfq_request_line_number_positive"]
    quantity_check = by_name["ck_rfq_request_line_quantity_positive"]
    assert "quantity >" in quantity_check
    assert all(token in quantity_check for token in ("NaN", "Infinity"))
    assert "ON DELETE CASCADE" in fk_by_name["fk_rfq_request_lines_rfq_id_rfq_requests"]
    assert "ON DELETE SET NULL" in fk_by_name["fk_rfq_request_lines_material_id_materials"]
    assert "ON DELETE SET NULL" in fk_by_name["fk_rfq_request_lines_product_id_products"]
