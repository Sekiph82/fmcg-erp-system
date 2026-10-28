"""M03.S02.T005 master-to-master referential integrity."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from starlette.testclient import TestClient

from app.core.exception_handlers import _constraint_name, register_handlers
from app.crud.master import create_warehouse
from app.db.session import AsyncSessionLocal, engine
from app.models.company import Branch, Company
from app.models.master import Warehouse, WarehouseType
from app.schemas.master import WarehouseCreate


def _require_task_owned_database() -> None:
    expected = os.environ.get("M03_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M03_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip(
            "Set M03_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database."
        )
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m03_t005_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match the exact loopback T005 disposable database."
        )


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_warehouse_branch_must_belong_to_its_explicit_company():
    _require_task_owned_database()
    suffix = uuid4().hex[:18]

    async with AsyncSessionLocal() as db:
        owning_company = Company(name=f"T005 owner {suffix}", short_code=f"O{suffix[:8]}")
        other_company = Company(name=f"T005 other {suffix}", short_code=f"X{suffix[:8]}")
        db.add_all([owning_company, other_company])
        await db.flush()

        branch = Branch(
            company_id=owning_company.id,
            name=f"T005 branch {suffix}",
            branch_code=f"B{suffix[:10]}",
        )
        db.add(branch)
        await db.flush()
        owning_company_id = owning_company.id
        other_company_id = other_company.id
        branch_id = branch.id
        db.add(
            Warehouse(
                code=f"OK-{suffix}",
                name="Synthetic valid warehouse",
                warehouse_type=WarehouseType.RAW_MATERIAL,
                company_id=owning_company_id,
                branch_id=branch_id,
            )
        )
        await db.commit()

        # The CRUD boundary rejects a mismatch before inserting the warehouse.
        with pytest.raises(HTTPException) as api_error:
            await create_warehouse(
                db,
                WarehouseCreate(
                    code=f"API-{suffix}",
                    name="Synthetic mismatch",
                    warehouse_type=WarehouseType.RAW_MATERIAL,
                    company_id=other_company_id,
                    branch_id=branch_id,
                ),
            )
        assert api_error.value.status_code == 422
        assert api_error.value.detail["code"] == "warehouse_branch_company_mismatch"

        # The database remains authoritative for import/direct-SQL/race paths.
        db.add(
            Warehouse(
                code=f"DB-{suffix}",
                name="Synthetic mismatch",
                warehouse_type=WarehouseType.RAW_MATERIAL,
                company_id=other_company_id,
                branch_id=branch_id,
            )
        )
        with pytest.raises(IntegrityError) as db_error:
            await db.flush()
        assert _constraint_name(db_error.value) == "fk_warehouses_branch_company"
        await db.rollback()

        # A branch-only warehouse remains valid: its company is unambiguous
        # through the branch, and the optional company column stays nullable.
        branch_only = Warehouse(
            code=f"BO-{suffix}",
            name="Synthetic branch-only warehouse",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            company_id=None,
            branch_id=branch_id,
        )
        db.add(branch_only)
        await db.commit()

        # Moving a branch cannot invalidate warehouses already linked to it.
        with pytest.raises(IntegrityError) as branch_error:
            await db.execute(
                update(Branch)
                .where(Branch.id == branch_id)
                .values(company_id=other_company_id)
            )
            await db.flush()
        assert _constraint_name(branch_error.value) == "fk_warehouses_branch_company"
        await db.rollback()

        # The pre-existing branch FK's SET NULL behavior remains valid with the
        # composite constraint, retaining the separate company-only scope.
        await db.execute(delete(Branch).where(Branch.id == branch_id))
        await db.commit()
        explicit_company_warehouse = await db.scalar(
            select(Warehouse).where(Warehouse.code == f"OK-{suffix}")
        )
        branch_only_warehouse = await db.scalar(
            select(Warehouse).where(Warehouse.code == f"BO-{suffix}")
        )
        assert explicit_company_warehouse is not None
        assert explicit_company_warehouse.company_id == owning_company_id
        assert explicit_company_warehouse.branch_id is None
        assert branch_only_warehouse is not None
        assert branch_only_warehouse.company_id is None
        assert branch_only_warehouse.branch_id is None


def test_warehouse_branch_company_constraint_is_reported_as_conflict():
    class DatabaseConstraintViolation(Exception):
        constraint_name = "fk_warehouses_branch_company"

    app = FastAPI()
    register_handlers(app)

    @app.post("/warehouse")
    async def create_invalid_warehouse():
        raise IntegrityError(
            "INSERT", {}, DatabaseConstraintViolation("scope mismatch")
        )

    response = TestClient(app).post("/warehouse")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "warehouse_branch_company_mismatch"
