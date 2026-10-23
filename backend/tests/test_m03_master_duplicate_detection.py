"""Regression coverage for database-key based master duplicate checks."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from app.api.v1.endpoints.bulk_import import MaterialAdapter, ProductAdapter, SupplierAdapter, WarehouseAdapter
from app.db.session import AsyncSessionLocal, engine
from app.models.company import Branch, Company
from app.models.import_history import ImportHistory
from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.schemas.master import ProductCreate
from app.services.import_engine import ImportEngine, ImportMode
from app.services.master_duplicate_detection import (
    duplicate_signature,
    ensure_unique_record,
    unique_key_groups,
)


def test_master_import_adapters_use_database_unique_keys():
    assert ProductAdapter().duplicate_key_groups() == [("barcode",), ("sku",)]
    assert MaterialAdapter().duplicate_key_groups() == [("code",)]
    assert SupplierAdapter().duplicate_key_groups() == [("code",)]
    assert WarehouseAdapter().duplicate_key_groups() == [("code",)]


def test_branch_duplicate_key_is_company_scoped():
    assert unique_key_groups(Branch) == [("company_id", "branch_code")]


def test_duplicate_signatures_preserve_declared_database_equality():
    keys = [("sku",), ("barcode",)]
    assert duplicate_signature(keys, {"sku": "SKU-A", "barcode": None}) == (("sku",), ("SKU-A",))
    assert duplicate_signature(keys, {"sku": "sku-a", "barcode": None}) == (("sku",), ("sku-a",))
    assert duplicate_signature(keys, {"sku": None, "barcode": None}) is None


def _require_task_owned_database() -> None:
    expected = os.environ.get("M03_DISPOSABLE_TEST_DATABASE_NAME", "")
    if os.environ.get("M03_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M03_DISPOSABLE_TEST_DATABASE=1 only for a task-owned disposable PostgreSQL database.")
    if (
        engine.url.drivername not in {"postgresql", "postgresql+asyncpg"}
        or engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"fmcg_m03_t001_[a-f0-9]{20,32}", expected)
        or engine.url.database != expected
    ):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback T001 disposable database.")


@pytest.mark.asyncio
async def test_duplicate_records_return_uniform_conflict_without_owner_data():
    _require_task_owned_database()
    suffix = uuid4().hex[:16]
    company_id = None
    product_ids: list = []
    import_file_names = [f"m03-duplicate-{suffix}-csv.csv", f"m03-duplicate-{suffix}-db.csv"]

    async with AsyncSessionLocal() as db:
        company = Company(
            name=f"Synthetic duplicate check {suffix}",
            short_code=f"D{suffix[:10]}",
        )
        db.add(company)
        await db.flush()
        company_id = company.id

        first = Product(
            sku=f"SKU-{suffix}",
            barcode=f"BAR-{suffix}",
            name="Synthetic duplicate test product",
            category=ProductCategory.OTHER,
            uom=UnitOfMeasure.PCS,
        )
        second = Product(
            sku=f"SKU2-{suffix}",
            barcode=f"BAR2-{suffix}",
            name="Synthetic second test product",
            category=ProductCategory.OTHER,
            uom=UnitOfMeasure.PCS,
        )
        material = Material(
            code=f"MAT-{suffix}",
            name="Synthetic duplicate test material",
            material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
        )
        supplier = Supplier(code=f"SUP-{suffix}", name="Synthetic duplicate test supplier")
        warehouse = Warehouse(
            code=f"WH-{suffix}",
            name="Synthetic duplicate test warehouse",
            warehouse_type=WarehouseType.FINISHED_GOODS,
            company_id=company_id,
        )
        branch = Branch(company_id=company_id, name="Synthetic branch", branch_code=f"BR-{suffix[:10]}")
        db.add_all([first, second, material, supplier, warehouse, branch])
        await db.commit()
        product_ids = [first.id, second.id]

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(HTTPException) as sku_conflict:
                await ensure_unique_record(db, Product, {"sku": f"SKU-{suffix}", "barcode": f"OTHER-{suffix}"})
            assert sku_conflict.value.status_code == 409
            assert sku_conflict.value.detail == {
                "code": "duplicate_master_record",
                "resource": "products",
                "fields": ["sku"],
            }

            with pytest.raises(HTTPException) as barcode_conflict:
                await ensure_unique_record(db, Product, {"sku": f"OTHER-{suffix}", "barcode": f"BAR-{suffix}"})
            assert barcode_conflict.value.status_code == 409
            assert barcode_conflict.value.detail["fields"] == ["barcode"]

            # Updating a record without changing its own key is allowed.
            await ensure_unique_record(
                db,
                Product,
                {"sku": f"SKU-{suffix}", "barcode": f"BAR-{suffix}"},
                exclude_id=product_ids[0],
            )

            for model, values, fields in [
                (Material, {"code": f"MAT-{suffix}"}, ["code"]),
                (Supplier, {"code": f"SUP-{suffix}"}, ["code"]),
                (Warehouse, {"code": f"WH-{suffix}"}, ["code"]),
                (Company, {"short_code": f"D{suffix[:10]}"}, ["short_code"]),
                (Branch, {"company_id": company_id, "branch_code": f"BR-{suffix[:10]}"}, ["company_id", "branch_code"]),
            ]:
                with pytest.raises(HTTPException) as conflict:
                    await ensure_unique_record(db, model, values)
                assert conflict.value.status_code == 409
                assert conflict.value.detail["fields"] == fields

            with pytest.raises(HTTPException) as crud_conflict:
                from app.crud.master import create_product

                await create_product(
                    db,
                    ProductCreate(
                        sku=f"SKU-{suffix}",
                        name="Synthetic duplicate through CRUD",
                        category=ProductCategory.OTHER,
                        uom=UnitOfMeasure.PCS,
                    ),
                )
            assert crud_conflict.value.status_code == 409

            csv_duplicate = (
                "sku,barcode,name,category,uom\n"
                f"CSV-{suffix},CSV-BAR-{suffix},Synthetic CSV one,OTHER,PCS\n"
                f"CSV-{suffix},CSV-BAR2-{suffix},Synthetic duplicate SKU,OTHER,PCS\n"
                f"CSV3-{suffix},CSV-BAR2-{suffix},Synthetic valid after rejected row,OTHER,PCS\n"
            )
            csv_result = await ImportEngine().run(
                content=csv_duplicate.encode(),
                adapter=ProductAdapter(),
                mode=ImportMode.VALIDATE_ONLY,
                db=db,
                user_id=None,
                username="m03-synthetic-test",
                user_roles=[],
                file_name=import_file_names[0],
            )
            assert csv_result.valid_rows == 2 and csv_result.failed_rows == 1
            assert "Duplicate in CSV" in csv_result.errors[0].message

            db_duplicate = (
                "sku,barcode,name,category,uom\n"
                f"CSV-DB-{suffix},BAR-{suffix},Synthetic existing barcode,OTHER,PCS\n"
                f"CSV-DB-{suffix},CSV-DB-BAR-{suffix},Synthetic valid after DB rejection,OTHER,PCS\n"
            )
            db_result = await ImportEngine().run(
                content=db_duplicate.encode(),
                adapter=ProductAdapter(),
                mode=ImportMode.VALIDATE_ONLY,
                db=db,
                user_id=None,
                username="m03-synthetic-test",
                user_roles=[],
                file_name=import_file_names[1],
            )
            assert db_result.valid_rows == 1 and db_result.failed_rows == 1
            assert "Already exists in database" in db_result.errors[0].message
            assert "barcode" in db_result.errors[0].message
            await db.commit()
    finally:
        async with AsyncSessionLocal() as cleanup:
            await cleanup.execute(delete(Branch).where(Branch.company_id == company_id))
            await cleanup.execute(delete(Warehouse).where(Warehouse.company_id == company_id))
            await cleanup.execute(delete(Product).where(Product.id.in_(product_ids)))
            await cleanup.execute(delete(ImportHistory).where(ImportHistory.file_name.in_(import_file_names)))
            await cleanup.execute(delete(Material).where(Material.code == f"MAT-{suffix}"))
            await cleanup.execute(delete(Supplier).where(Supplier.code == f"SUP-{suffix}"))
            await cleanup.execute(delete(Company).where(Company.id == company_id))
            await cleanup.commit()
