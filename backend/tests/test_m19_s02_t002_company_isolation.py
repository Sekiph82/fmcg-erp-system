"""Company summary isolation checks against a task-owned disposable database."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core import token_blocklist
from app.core.config import settings
from app.core.deps import get_auth_db, get_db
from app.db.session import AsyncSessionLocal, engine
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.company import Company, CompanyUserRole, UserCompanyAccess
from app.models.master import Supplier, Warehouse, WarehouseType
from app.models.procurement import POStatus, PurchaseOrder
from app.models.role import Permission, Role
from app.models.sales import Customer, SOStatus, SalesOrder
from app.models.user import User
from app.services.auth_refresh_tokens import issue_auth_token_pair


def _require_task_owned_database() -> None:
    expected = os.environ.get("M19_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M19_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M19_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m19_s02_t002_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T002 disposable database.")


@pytest.mark.asyncio
async def test_company_summary_counts_only_requested_company(monkeypatch):
    _require_task_owned_database()
    suffix = uuid4().hex[:16]
    user_id = None
    role_id = None
    family_id = None
    company_ids: list = []
    warehouse_ids: list = []
    po_ids: list = []
    customer_ids: list = []
    so_ids: list = []
    supplier_id = None
    created_permission_id = None

    monkeypatch.setattr(token_blocklist, "is_blocked", _not_blocked)

    async with AsyncSessionLocal() as db:
        permission = await db.scalar(select(Permission).where(Permission.code == "company.view"))
        if permission is None:
            permission = Permission(
                code="company.view", name="Company view", module="company", action="view", is_active=True
            )
            db.add(permission)
            await db.flush()
            created_permission_id = permission.id

        role = Role(name=f"m19-summary-{suffix}", is_active=True, permissions=[permission])
        user = User(
            email=f"m19-summary-{suffix}@example.invalid",
            username=f"m19-summary-{suffix}",
            full_name="Synthetic company summary user",
            hashed_password="test-only-not-used-for-login",
            is_active=True,
            is_superuser=False,
            roles=[role],
        )
        allowed = Company(name=f"Synthetic allowed {suffix}", short_code=f"A{suffix[:10]}")
        denied = Company(name=f"Synthetic denied {suffix}", short_code=f"D{suffix[:10]}")
        supplier = Supplier(code=f"M19S{suffix[:10]}", name="Synthetic supplier")
        customer_a = Customer(code=f"M19A{suffix[:10]}", name="Synthetic customer A", company=allowed)
        customer_b = Customer(code=f"M19B{suffix[:10]}", name="Synthetic customer B", company=denied)
        db.add_all([user, allowed, denied, supplier, customer_a, customer_b])
        await db.flush()

        warehouse_a = Warehouse(
            code=f"M19A{suffix[:10]}", name="Synthetic warehouse A",
            warehouse_type=WarehouseType.FINISHED_GOODS, company_id=allowed.id,
        )
        warehouse_b = Warehouse(
            code=f"M19B{suffix[:10]}", name="Synthetic warehouse B",
            warehouse_type=WarehouseType.FINISHED_GOODS, company_id=denied.id,
        )
        warehouse_unassigned = Warehouse(
            code=f"M19U{suffix[:10]}", name="Synthetic unassigned warehouse",
            warehouse_type=WarehouseType.FINISHED_GOODS,
        )
        today = date.today()
        po_a = PurchaseOrder(
            po_no=f"M19A{suffix[:10]}", supplier_id=supplier.id, company_id=allowed.id,
            order_date=today, expected_delivery_date=today + timedelta(days=7), status=POStatus.APPROVED,
        )
        po_b = PurchaseOrder(
            po_no=f"M19B{suffix[:10]}", supplier_id=supplier.id, company_id=denied.id,
            order_date=today, expected_delivery_date=today + timedelta(days=7), status=POStatus.APPROVED,
        )
        po_unassigned = PurchaseOrder(
            po_no=f"M19U{suffix[:10]}", supplier_id=supplier.id,
            order_date=today, expected_delivery_date=today + timedelta(days=7), status=POStatus.APPROVED,
        )
        so_a = SalesOrder(
            order_no=f"M19A{suffix[:10]}", customer_id=customer_a.id, company_id=allowed.id,
            order_date=today, requested_delivery_date=today + timedelta(days=7), status=SOStatus.CONFIRMED,
        )
        so_b = SalesOrder(
            order_no=f"M19B{suffix[:10]}", customer_id=customer_b.id, company_id=denied.id,
            order_date=today, requested_delivery_date=today + timedelta(days=7), status=SOStatus.CONFIRMED,
        )
        db.add_all([warehouse_a, warehouse_b, warehouse_unassigned, po_a, po_b, po_unassigned, so_a, so_b])
        await db.flush()
        db.add(UserCompanyAccess(user_id=user.id, company_id=allowed.id, role=CompanyUserRole.VIEWER))
        await db.commit()

        user_id, role_id, supplier_id = user.id, role.id, supplier.id
        company_ids = [allowed.id, denied.id]
        warehouse_ids = [warehouse_a.id, warehouse_b.id, warehouse_unassigned.id]
        po_ids = [po_a.id, po_b.id, po_unassigned.id]
        customer_ids = [customer_a.id, customer_b.id]
        so_ids = [so_a.id, so_b.id]

    try:
        async with AsyncSessionLocal() as auth_db:
            token_pair = await issue_auth_token_pair(auth_db, user_id)
            await auth_db.commit()
            family_id = token_pair.family_id
        await _exercise_company_summary(company_ids, token_pair.access_token)
    finally:
        async with AsyncSessionLocal() as cleanup:
            if family_id is not None:
                await cleanup.execute(delete(AuthRefreshToken).where(AuthRefreshToken.family_id == family_id))
            if user_id is not None:
                await cleanup.execute(delete(UserCompanyAccess).where(UserCompanyAccess.user_id == user_id))
            if so_ids:
                await cleanup.execute(delete(SalesOrder).where(SalesOrder.id.in_(so_ids)))
            if po_ids:
                await cleanup.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(po_ids)))
            if warehouse_ids:
                await cleanup.execute(delete(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
            if customer_ids:
                await cleanup.execute(delete(Customer).where(Customer.id.in_(customer_ids)))
            if supplier_id is not None:
                await cleanup.execute(delete(Supplier).where(Supplier.id == supplier_id))
            if company_ids:
                await cleanup.execute(delete(Company).where(Company.id.in_(company_ids)))
            if role_id is not None:
                await cleanup.execute(delete(Role).where(Role.id == role_id))
            if user_id is not None:
                await cleanup.execute(delete(User).where(User.id == user_id))
            if created_permission_id is not None:
                await cleanup.execute(delete(Permission).where(Permission.id == created_permission_id))
            await cleanup.commit()


async def _exercise_company_summary(company_ids, token: str) -> None:
    from app.main import app

    original_overrides = app.dependency_overrides.copy()

    async def get_test_db():
        async with AsyncSessionLocal() as db:
            yield db

    try:
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_auth_db] = get_test_db
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://127.0.0.1",
            cookies={settings.AUTH_COOKIE_NAME: token},
        ) as client:
            allowed = await client.get(f"/api/v1/companies/{company_ids[0]}/summary")
            assert allowed.status_code == 200, allowed.text
            summary = allowed.json()
            assert summary["warehouse_count"] == 1
            assert summary["open_po_count"] == 1
            assert summary["open_so_count"] == 1

            denied = await client.get(f"/api/v1/companies/{company_ids[1]}/summary")
            assert denied.status_code == 403, denied.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def _not_blocked(_token: str) -> bool:
    return False
