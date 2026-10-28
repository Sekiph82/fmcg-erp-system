"""M03.S02.T004 direct master-data permissions and audit behavior."""
from __future__ import annotations

import asyncio
import inspect
import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.api.v1.endpoints import materials, products, suppliers, warehouses
from app.api.v1.endpoints import company as company_endpoint
from app.api.v1.endpoints.bulk_import import ProductAdapter, SupplierAdapter
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS
from app.models.audit_log import AuditEvent
from app.models.company import Branch, Company
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
    SupplierQualificationStatus,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.master import (
    MaterialCreate,
    MaterialUpdate,
    ProductCreate,
    ProductUpdate,
    SupplierCreate,
    SupplierUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)
from app.schemas.company import BranchCreate, CompanyCreate, CompanyUpdate
from app.services.import_engine import ImportEngine, ImportMode
from app.services import master_stewardship
from app.services.master_stewardship import record_master_data_change, snapshot_master_data
from app.db.session import AsyncSessionLocal, engine


def _role(*codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        is_active=True,
        permissions=[SimpleNamespace(code=code, is_active=True) for code in codes],
    )


def _actor(*codes: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        email="steward@example.test",
        full_name="Synthetic Steward",
        is_superuser=False,
        roles=[_role(*codes)],
    )


def _require_t004_disposable_database() -> None:
    expected = os.environ.get("M03_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M03_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M03_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m03_t004_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T004 disposable database.")


def _record_and_schemas(module_key: str):
    record_id = uuid4()
    if module_key == "products":
        return (
            products,
            "product",
            "products",
            Product(id=record_id, sku="P-T004", name="Synthetic product", category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS),
            ProductCreate(sku="P-T004", name="Synthetic product", category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS),
            ProductUpdate(name="Updated synthetic product"),
        )
    if module_key == "materials":
        return (
            materials,
            "material",
            "materials",
            Material(id=record_id, code="M-T004", name="Synthetic material", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG),
            MaterialCreate(code="M-T004", name="Synthetic material", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG),
            MaterialUpdate(name="Updated synthetic material"),
        )
    if module_key == "suppliers":
        return (
            suppliers,
            "supplier",
            "suppliers",
            Supplier(id=record_id, code="S-T004", name="Synthetic supplier", email="old@example.com", tax_id="SYNTHETIC-TAX-ID"),
            SupplierCreate(code="S-T004", name="Synthetic supplier", email="old@example.com", tax_id="SYNTHETIC-TAX-ID"),
            SupplierUpdate(name="Updated synthetic supplier"),
        )
    return (
        warehouses,
        "warehouse",
        "warehouses",
        Warehouse(id=record_id, code="W-T004", name="Synthetic warehouse", warehouse_type=WarehouseType.RAW_MATERIAL),
        WarehouseCreate(code="W-T004", name="Synthetic warehouse", warehouse_type=WarehouseType.RAW_MATERIAL),
        WarehouseUpdate(name="Updated synthetic warehouse"),
    )


@pytest.mark.parametrize("module_key", ["products", "materials", "suppliers", "warehouses"])
def test_master_create_and_edit_routes_require_the_matching_permission(module_key: str):
    endpoint_module, entity, route_module, *_ = _record_and_schemas(module_key)
    for method, permission_action in (("POST", "create"), ("PATCH", "edit")):
        route = next(
            item for item in endpoint_module.router.routes
            if method in item.methods and item.path in {"/", f"/{{{entity}_id}}"}
        )
        dependency = next(
            item for item in route.dependant.dependencies if item.name == "current_user"
        )
        permission = inspect.getclosurevars(dependency.call).nonlocals["permission_code"]
        assert permission == f"{route_module}.{permission_action}"
        with pytest.raises(HTTPException) as denied:
            asyncio.run(dependency.call(current_user=_actor(f"{route_module}.view")))
        assert denied.value.status_code == 403
        assert asyncio.run(dependency.call(current_user=_actor(permission))).is_superuser is False


def test_supplier_read_routes_require_supplier_view_permission():
    for path in ("/", "/{supplier_id}"):
        route = next(
            item for item in suppliers.router.routes
            if "GET" in item.methods and item.path == path
        )
        dependency = next(item for item in route.dependant.dependencies if item.name == "_")
        permission = inspect.getclosurevars(dependency.call).nonlocals["permission_code"]
        assert permission == "suppliers.view"
        with pytest.raises(HTTPException) as denied:
            asyncio.run(dependency.call(current_user=_actor("procurement.view")))
        assert denied.value.status_code == 403


def test_seeded_steward_permissions_follow_existing_master_roles():
    codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    assert {f"{module}.{action}" for module in ("products", "materials", "suppliers", "warehouses") for action in ("create", "edit")} <= codes
    assert "suppliers.create" in ROLE_DEFINITIONS["procurement_officer"]["permissions"]
    assert "suppliers.edit" in ROLE_DEFINITIONS["procurement_officer"]["permissions"]
    for role in ("ceo", "coo", "cfo", "admin", "data_manager", "procurement_officer", "logistics_officer", "company_admin", "procurement_manager"):
        if any(
            permission in ROLE_DEFINITIONS[role]["permissions"]
            for permission in ("procurement.view", "procurement.view_all")
        ):
            assert "suppliers.view" in ROLE_DEFINITIONS[role]["permissions"]
    assert "products.create" in ROLE_DEFINITIONS["cmo"]["permissions"]
    assert "products.edit" in ROLE_DEFINITIONS["cmo"]["permissions"]
    assert "materials.create" in ROLE_DEFINITIONS["coo"]["permissions"]
    assert "materials.edit" in ROLE_DEFINITIONS["coo"]["permissions"]
    assert "warehouses.create" in ROLE_DEFINITIONS["coo"]["permissions"]
    assert "warehouses.edit" in ROLE_DEFINITIONS["coo"]["permissions"]
    assert sum(code == "warehouses.create" for code in (f"{module}.{action}" for module, action, *_ in PERMISSIONS)) == 1
    assert sum(code == "warehouses.edit" for code in (f"{module}.{action}" for module, action, *_ in PERMISSIONS)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("module_key", ["products", "materials", "suppliers", "warehouses"])
async def test_master_create_and_update_routes_record_audit_in_same_transaction(module_key: str, monkeypatch):
    endpoint_module, entity, route_module, record, create_data, update_data = _record_and_schemas(module_key)
    actor = _actor(f"{route_module}.create", f"{route_module}.edit")
    db = SimpleNamespace(commit=AsyncMock())
    audit = AsyncMock()
    monkeypatch.setattr(endpoint_module, "record_master_data_change", audit)

    async def create_record(*_args, **_kwargs):
        return record

    async def get_record(*_args, **_kwargs):
        return record

    async def update_record(_db, existing, data):
        existing.name = data.name
        return existing

    monkeypatch.setattr(endpoint_module.crud, f"create_{entity}", create_record)
    monkeypatch.setattr(endpoint_module.crud, f"get_{entity}", get_record)
    monkeypatch.setattr(endpoint_module.crud, f"update_{entity}", update_record)

    await getattr(endpoint_module, f"create_{entity}")(create_data, db, actor)
    audit.assert_awaited_once_with(
        db,
        record=record,
        actor=actor,
        action="CREATE",
        permission=f"{route_module}.create",
    )
    db.commit.assert_awaited_once()

    audit.reset_mock()
    db.commit.reset_mock()
    await getattr(endpoint_module, f"update_{entity}")(record.id, update_data, db, actor)
    audit.assert_awaited_once()
    kwargs = audit.await_args.kwargs
    assert kwargs["record"] is record
    assert kwargs["actor"] is actor
    assert kwargs["action"] == "UPDATE"
    assert kwargs["permission"] == f"{route_module}.edit"
    assert "name" in kwargs["before"]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_records_actor_before_after_and_redacts_supplier_contact_values(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.rows = []

        def add(self, row):
            self.rows.append(row)

        async def flush(self):
            return None

    db = FakeSession()
    actor = _actor("suppliers.edit")
    record = Supplier(
        id=uuid4(), code="S-T004-AUDIT", name="Synthetic supplier",
        email="old@example.test", tax_id="SYNTHETIC-TAX-ID",
        compliance_notes="Sensitive synthetic compliance note",
    )
    before = snapshot_master_data(record)
    record.name = "Changed synthetic supplier"
    record.email = "new@example.com"
    record.compliance_notes = "Changed sensitive synthetic note"

    await record_master_data_change(
        db,
        record=record,
        actor=actor,
        action="UPDATE",
        permission="suppliers.edit",
        before=before,
    )

    assert len(db.rows) == 1
    event = db.rows[0]
    assert event.event_type == AuditEvent.MASTER_DATA_UPDATED
    assert event.module == "suppliers"
    assert event.target_type == "suppliers"
    assert event.target_id == str(record.id)
    assert event.actor_id == actor.id
    assert event.actor_email == actor.email
    assert event.actor_name == actor.full_name
    assert event.before_value == {
        "name": "Synthetic supplier",
        "email": "[REDACTED]",
        "compliance_notes": "[REDACTED]",
    }
    assert event.after_value == {
        "name": "Changed synthetic supplier",
        "email": "[REDACTED]",
        "compliance_notes": "[REDACTED]",
    }
    assert event.details == {
        "workflow": "DIRECT_AUTHORIZED_EDIT",
        "approval_required": False,
        "required_permission": "suppliers.edit",
        "changed_fields": ["compliance_notes", "email", "name"],
    }


@pytest.mark.asyncio
async def test_create_audit_records_after_values_and_actor():
    class FakeSession:
        def __init__(self):
            self.rows = []

        def add(self, row):
            self.rows.append(row)

        async def flush(self):
            return None

    db = FakeSession()
    actor = _actor("products.create")
    record = Product(
        id=uuid4(), sku="P-T004-CREATE", name="Synthetic created product",
        category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS,
    )

    await record_master_data_change(
        db,
        record=record,
        actor=actor,
        action="CREATE",
        permission="products.create",
    )

    assert len(db.rows) == 1
    event = db.rows[0]
    assert event.event_type == AuditEvent.MASTER_DATA_CREATED
    assert event.module == "products"
    assert event.actor_id == actor.id
    assert event.target_id == str(record.id)
    assert event.before_value == {}
    assert event.after_value["sku"] == record.sku
    assert event.after_value["name"] == record.name
    assert event.details["required_permission"] == "products.create"


@pytest.mark.asyncio
async def test_noop_master_edit_does_not_create_audit_event():
    class FakeSession:
        def __init__(self):
            self.rows = []

        def add(self, row):
            self.rows.append(row)

        async def flush(self):
            return None

    db = FakeSession()
    actor = _actor("products.edit")
    record = Product(
        id=uuid4(), sku="P-T004-NOOP", name="Synthetic unchanged product",
        category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS,
    )
    before = snapshot_master_data(record)

    await record_master_data_change(
        db,
        record=record,
        actor=actor,
        action="UPDATE",
        permission="products.edit",
        before=before,
    )

    assert db.rows == []


@pytest.mark.asyncio
async def test_direct_supplier_qualification_sets_the_authenticated_actor_as_approver(monkeypatch):
    actor = _actor("suppliers.create", "suppliers.edit")
    supplier = Supplier(
        id=uuid4(), code="S-T004-QUAL", name="Synthetic qualified supplier",
        qualification_status=SupplierQualificationStatus.APPROVED,
    )
    db = SimpleNamespace(flush=AsyncMock(), commit=AsyncMock())
    audit = AsyncMock()
    monkeypatch.setattr(suppliers.crud, "create_supplier", AsyncMock(return_value=supplier))
    monkeypatch.setattr(suppliers, "record_master_data_change", audit)
    create_data = SupplierCreate(
        code=supplier.code,
        name=supplier.name,
        qualification_status=SupplierQualificationStatus.APPROVED,
    )

    await suppliers.create_supplier(create_data, db, actor)

    assert supplier.approved_by_id == actor.id
    assert supplier.approved_at is not None
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["record"] is supplier
    assert audit.await_args.kwargs["permission"] == "suppliers.create"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_supplier_update_cannot_choose_another_approver(monkeypatch):
    actor = _actor("suppliers.edit")
    supplier = Supplier(
        id=uuid4(), code="S-T004-QUAL-UPDATE", name="Synthetic supplier",
        qualification_status=SupplierQualificationStatus.PENDING,
    )
    before_approver = uuid4()
    update_data = SupplierUpdate(
        qualification_status=SupplierQualificationStatus.APPROVED,
        approved_by_id=before_approver,
    )
    assert "approved_by_id" not in update_data.model_fields_set
    db = SimpleNamespace(commit=AsyncMock(), flush=AsyncMock())
    audit = AsyncMock()

    async def update_record(_db, existing, data):
        existing.qualification_status = data.qualification_status
        return existing

    monkeypatch.setattr(suppliers.crud, "get_supplier", AsyncMock(return_value=supplier))
    monkeypatch.setattr(suppliers.crud, "update_supplier", update_record)
    monkeypatch.setattr(suppliers, "record_master_data_change", audit)

    await suppliers.update_supplier(supplier.id, update_data, db, actor)

    assert supplier.approved_by_id == actor.id
    assert supplier.approved_by_id != before_approver
    assert supplier.approved_at is not None
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["record"] is supplier
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_audit_write_prevents_master_endpoint_commit(monkeypatch):
    actor = _actor("products.create")
    product = Product(
        id=uuid4(), sku="P-T004-ROLLBACK", name="Synthetic product",
        category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS,
    )
    db = SimpleNamespace(commit=AsyncMock())

    async def create_product(*_args, **_kwargs):
        return product

    async def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(products.crud, "create_product", create_product)
    monkeypatch.setattr(products, "record_master_data_change", fail_audit)

    with pytest.raises(RuntimeError, match="synthetic audit failure"):
        await products.create_product(
            ProductCreate(sku=product.sku, name=product.name, category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS),
            db,
            actor,
        )

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_company_and_branch_writes_record_actor_and_changes_before_commit(monkeypatch):
    actor = _actor("company.create", "company.edit")
    events: list[str] = []

    class FakeSession:
        def add(self, _record):
            events.append("add")

        async def flush(self):
            events.append("flush")

        async def commit(self):
            events.append("commit")

        async def refresh(self, _record):
            events.append("refresh")

    async def audit(_db, **kwargs):
        events.append("audit")
        assert kwargs["actor"] is actor
        assert kwargs["action"] in {"CREATE", "UPDATE"}
        assert kwargs["permission"] in {"company.create", "company.edit"}

    db = FakeSession()
    monkeypatch.setattr(company_endpoint, "ensure_unique_record", AsyncMock())
    monkeypatch.setattr(company_endpoint, "record_master_data_change", audit)
    monkeypatch.setattr(company_endpoint, "_build_company_read", AsyncMock(return_value="company-read"))
    created = await company_endpoint.create_company(
        CompanyCreate(name="Synthetic Company", short_code="SYN"), db, actor
    )
    assert created == "company-read"
    assert events.index("audit") < events.index("commit")

    events.clear()
    company = Company(id=uuid4(), name="Before Company", short_code="SYN")
    monkeypatch.setattr(company_endpoint, "_check_company_access", AsyncMock())
    monkeypatch.setattr(company_endpoint, "_get_or_404", AsyncMock(return_value=company))
    updated = await company_endpoint.update_company(
        company.id, CompanyUpdate(name="After Company"), db, actor
    )
    assert updated == "company-read"
    assert events.index("audit") < events.index("commit")

    events.clear()
    monkeypatch.setattr(company_endpoint, "_get_or_404", AsyncMock(return_value=company))

    def add_record(record):
        events.append("add")
        if isinstance(record, Branch):
            record.id = record.id or uuid4()
            record.is_active = True
            record.created_at = datetime.now(timezone.utc)

    monkeypatch.setattr(db, "add", add_record)
    created_branch = await company_endpoint.add_branch(
        company.id,
        BranchCreate(name="Synthetic Branch", branch_code="BR-NEW"),
        db,
        actor,
    )
    assert created_branch.name == "Synthetic Branch"
    assert events.index("audit") < events.index("commit")

    events.clear()
    branch = Branch(
        id=uuid4(), company_id=company.id, name="Before Branch", branch_code="BR-1",
        is_active=True, created_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(db, "get", AsyncMock(return_value=branch), raising=False)
    monkeypatch.setattr(company_endpoint, "ensure_unique_record", AsyncMock())
    branch_read = await company_endpoint.update_branch(
        branch.id, BranchCreate(name="After Branch", branch_code="BR-1"), db, actor
    )
    assert branch_read.name == "After Branch"
    company_endpoint._check_company_access.assert_awaited_with(db, actor, company.id)
    assert events.index("audit") < events.index("commit")


@pytest.mark.asyncio
async def test_master_bulk_import_records_audit_for_each_inserted_record(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.rows = []

        def add(self, row):
            self.rows.append(row)

        async def flush(self):
            return None

    db = FakeSession()
    actor = _actor("products.import")
    records = [
        Product(id=uuid4(), sku="P-T004-IMPORT-1", name="Synthetic one", category=ProductCategory.OTHER),
        Product(id=uuid4(), sku="P-T004-IMPORT-2", name="Synthetic two", category=ProductCategory.OTHER),
    ]
    adapter = ProductAdapter()
    adapter.duplicate_fields_in_db = AsyncMock(return_value=None)
    adapter.insert = AsyncMock(side_effect=records)
    audit = AsyncMock()
    monkeypatch.setattr("app.services.master_stewardship.record_master_data_change", audit)
    csv_content = (
        "sku,name,category\n"
        "P-T004-IMPORT-1,Synthetic one,OTHER\n"
        "P-T004-IMPORT-2,Synthetic two,OTHER\n"
    ).encode()

    result = await ImportEngine().run(
        content=csv_content,
        adapter=adapter,
        mode=ImportMode.IMPORT_VALID_ONLY,
        db=db,
        user_id=actor.id,
        username=actor.email,
        user_roles=[],
        actor=actor,
    )

    assert result.imported is True and result.valid_rows == 2
    assert audit.await_count == 2
    assert [call.kwargs["record"] for call in audit.await_args_list] == records
    assert all(call.kwargs["actor"] is actor for call in audit.await_args_list)
    assert all(call.kwargs["permission"] == "products.import" for call in audit.await_args_list)


@pytest.mark.asyncio
async def test_master_bulk_import_refuses_writes_without_authenticated_audit_actor():
    class FakeSession:
        def add(self, _record):
            return None

        async def flush(self):
            return None

    adapter = ProductAdapter()
    adapter.duplicate_fields_in_db = AsyncMock(return_value=None)
    adapter.insert = AsyncMock()

    with pytest.raises(ValueError, match="Authenticated actor required"):
        await ImportEngine().run(
            content=b"sku,name,category\nP-T004-IMPORT-3,Synthetic three,OTHER\n",
            adapter=adapter,
            mode=ImportMode.IMPORT_VALID_ONLY,
            db=FakeSession(),
            user_id=None,
            username="anonymous",
            user_roles=[],
        )

    adapter.insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_imported_approved_supplier_records_the_authenticated_steward(monkeypatch):
    class FakeSession:
        def add(self, _record):
            return None

        async def flush(self):
            return None

    actor = _actor("procurement.import")
    supplier = Supplier(
        id=uuid4(),
        code="S-T004-IMPORT-APPROVED",
        name="Synthetic imported supplier",
        qualification_status=SupplierQualificationStatus.APPROVED,
    )
    adapter = SupplierAdapter()
    adapter.duplicate_fields_in_db = AsyncMock(return_value=None)
    adapter.insert = AsyncMock(return_value=supplier)
    audit = AsyncMock()
    monkeypatch.setattr("app.services.master_stewardship.record_master_data_change", audit)

    result = await ImportEngine().run(
        content=(
            b"code,name,qualification_status\n"
            b"S-T004-IMPORT-APPROVED,Synthetic imported supplier,APPROVED\n"
        ),
        adapter=adapter,
        mode=ImportMode.IMPORT_VALID_ONLY,
        db=FakeSession(),
        user_id=actor.id,
        username=actor.email,
        user_roles=[],
        actor=actor,
    )

    assert result.imported is True
    assert supplier.approved_by_id == actor.id
    assert supplier.approved_at is not None
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["actor"] is actor
    assert audit.await_args.kwargs["permission"] == "procurement.import"
    assert audit.await_args.kwargs["record"] is supplier


@pytest.mark.asyncio
async def test_postgresql_master_update_audit_persists_and_rolls_back_atomically(monkeypatch):
    _require_t004_disposable_database()
    suffix = uuid4().hex
    actor_id = uuid4()
    product_id = uuid4()

    async with AsyncSessionLocal() as db:
        actor = User(
            id=actor_id,
            email=f"m03-t004-{suffix}@example.test",
            username=f"m03-t004-{suffix}",
            full_name="Synthetic T004 Steward",
            hashed_password="synthetic-test-only",
        )
        product = Product(
            id=product_id,
            sku=f"T004-{suffix}",
            name="Synthetic before value",
            category=ProductCategory.OTHER,
            uom=UnitOfMeasure.PCS,
        )
        db.add(actor)
        db.add(product)
        await db.flush()
        before = snapshot_master_data(product)
        product.name = "Synthetic after value"
        await record_master_data_change(
            db,
            record=product,
            actor=actor,
            action="UPDATE",
            permission="products.edit",
            before=before,
        )
        await db.commit()

        event = await db.scalar(
            select(AuditLog).where(
                AuditLog.event_type == AuditEvent.MASTER_DATA_UPDATED,
                AuditLog.target_id == str(product_id),
            )
        )
        assert event is not None
        assert event.actor_id == actor_id
        assert event.before_value == {"name": "Synthetic before value"}
        assert event.after_value == {"name": "Synthetic after value"}

        rollback_product_id = uuid4()
        rollback_product = Product(
            id=rollback_product_id,
            sku=f"T004-ROLLBACK-{suffix}",
            name="Synthetic rollback before",
            category=ProductCategory.OTHER,
            uom=UnitOfMeasure.PCS,
        )
        db.add(rollback_product)
        await db.flush()
        rollback_before = snapshot_master_data(rollback_product)
        rollback_product.name = "Synthetic rollback after"

        async def fail_audit(*_args, **_kwargs):
            raise RuntimeError("synthetic audit storage failure")

        monkeypatch.setattr(master_stewardship, "log_event", fail_audit)
        with pytest.raises(RuntimeError, match="synthetic audit storage failure"):
            await record_master_data_change(
                db,
                record=rollback_product,
                actor=actor,
                action="UPDATE",
                permission="products.edit",
                before=rollback_before,
            )
        await db.rollback()
        assert await db.get(Product, rollback_product_id) is None

    async with AsyncSessionLocal() as cleanup:
        await cleanup.execute(delete(Product).where(Product.id == product_id))
        await cleanup.execute(delete(User).where(User.id == actor_id))
        await cleanup.commit()
