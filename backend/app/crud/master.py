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
    obj = Supplier(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_supplier(db: AsyncSession, obj: Supplier, data: SupplierUpdate) -> Supplier:
    for k, v in data.model_dump(exclude_unset=True).items():
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
    obj = Product(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_product(db: AsyncSession, obj: Product, data: ProductUpdate) -> Product:
    for k, v in data.model_dump(exclude_unset=True).items():
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
    obj = Material(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_material(db: AsyncSession, obj: Material, data: MaterialUpdate) -> Material:
    for k, v in data.model_dump(exclude_unset=True).items():
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
    obj = Warehouse(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def update_warehouse(db: AsyncSession, obj: Warehouse, data: WarehouseUpdate) -> Warehouse:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj
