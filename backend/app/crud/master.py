from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import uuid

from app.models.master import Product, Material, Supplier, Warehouse
from app.schemas.master import (
    ProductCreate, ProductUpdate,
    MaterialCreate, MaterialUpdate,
    SupplierCreate, SupplierUpdate,
    WarehouseCreate, WarehouseUpdate,
)
from app.services.master_duplicate_detection import ensure_unique_record


# ── Generic helpers ────────────────────────────────────────────────────────────

async def _get(db, model, id_):
    result = await db.execute(select(model).where(model.id == id_))
    return result.scalar_one_or_none()


async def _list(db, model, skip=0, limit=50):
    result = await db.execute(select(model).offset(skip).limit(limit))
    return list(result.scalars().all())


async def _count(db, model):
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar_one()


# ── Supplier ───────────────────────────────────────────────────────────────────

async def get_supplier(db: AsyncSession, supplier_id: uuid.UUID) -> Optional[Supplier]:
    return await _get(db, Supplier, supplier_id)

async def list_suppliers(db: AsyncSession, skip=0, limit=50) -> List[Supplier]:
    return await _list(db, Supplier, skip, limit)

async def create_supplier(db: AsyncSession, data: SupplierCreate) -> Supplier:
    values = data.model_dump()
    await ensure_unique_record(db, Supplier, values)
    obj = Supplier(**values)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_supplier(db: AsyncSession, obj: Supplier, data: SupplierUpdate) -> Supplier:
    changes = data.model_dump(exclude_unset=True)
    values = {column.name: getattr(obj, column.name) for column in Supplier.__table__.columns}
    values.update(changes)
    await ensure_unique_record(db, Supplier, values, exclude_id=obj.id)
    for k, v in changes.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Product ────────────────────────────────────────────────────────────────────

async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Optional[Product]:
    return await _get(db, Product, product_id)

async def list_products(db: AsyncSession, skip=0, limit=50) -> List[Product]:
    return await _list(db, Product, skip, limit)

async def create_product(db: AsyncSession, data: ProductCreate) -> Product:
    values = data.model_dump()
    await ensure_unique_record(db, Product, values)
    obj = Product(**values)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_product(db: AsyncSession, obj: Product, data: ProductUpdate) -> Product:
    changes = data.model_dump(exclude_unset=True)
    values = {column.name: getattr(obj, column.name) for column in Product.__table__.columns}
    values.update(changes)
    await ensure_unique_record(db, Product, values, exclude_id=obj.id)
    for k, v in changes.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Material ───────────────────────────────────────────────────────────────────

async def get_material(db: AsyncSession, material_id: uuid.UUID) -> Optional[Material]:
    return await _get(db, Material, material_id)

async def list_materials(db: AsyncSession, skip=0, limit=50) -> List[Material]:
    return await _list(db, Material, skip, limit)

async def create_material(db: AsyncSession, data: MaterialCreate) -> Material:
    values = data.model_dump()
    await ensure_unique_record(db, Material, values)
    obj = Material(**values)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_material(db: AsyncSession, obj: Material, data: MaterialUpdate) -> Material:
    changes = data.model_dump(exclude_unset=True)
    values = {column.name: getattr(obj, column.name) for column in Material.__table__.columns}
    values.update(changes)
    await ensure_unique_record(db, Material, values, exclude_id=obj.id)
    for k, v in changes.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Warehouse ──────────────────────────────────────────────────────────────────

async def get_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Optional[Warehouse]:
    return await _get(db, Warehouse, warehouse_id)

async def list_warehouses(db: AsyncSession, skip=0, limit=50) -> List[Warehouse]:
    return await _list(db, Warehouse, skip, limit)

async def create_warehouse(db: AsyncSession, data: WarehouseCreate) -> Warehouse:
    values = data.model_dump()
    await ensure_unique_record(db, Warehouse, values)
    obj = Warehouse(**values)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_warehouse(db: AsyncSession, obj: Warehouse, data: WarehouseUpdate) -> Warehouse:
    changes = data.model_dump(exclude_unset=True)
    values = {column.name: getattr(obj, column.name) for column in Warehouse.__table__.columns}
    values.update(changes)
    await ensure_unique_record(db, Warehouse, values, exclude_id=obj.id)
    for k, v in changes.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Delete helpers ─────────────────────────────────────────────────────────────

async def delete_supplier(db: AsyncSession, obj: Supplier) -> None:
    await db.delete(obj)
    await db.flush()

async def delete_product(db: AsyncSession, obj: Product) -> None:
    await db.delete(obj)
    await db.flush()

async def delete_material(db: AsyncSession, obj: Material) -> None:
    await db.delete(obj)
    await db.flush()

async def delete_warehouse(db: AsyncSession, obj: Warehouse) -> None:
    await db.delete(obj)
    await db.flush()
