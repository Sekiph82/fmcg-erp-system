"""
Bulk Import API
───────────────
Centralised router for all module import endpoints.

GET  /bulk-import/{module}/template          – download CSV template
POST /bulk-import/{module}/validate          – validate only, no DB write
POST /bulk-import/{module}/import            – full import
GET  /bulk-import/history                    – import history (with filters)
GET  /bulk-import/history/{id}/errors        – download error CSV for one run

Permissions: {perm_module}.import_template / {perm_module}.import
"""
from __future__ import annotations

import io
import uuid as _uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.import_history import ImportHistory
from app.models.user import User
from app.services.import_engine import (
    BaseImportAdapter,
    FieldMeta,
    ImportMode,
    ImportResult,
    generate_error_csv,
    import_engine,
    parse_csv_rows,
)

# ── Model / schema imports ────────────────────────────────────────────────────

from app.models.master import Product, Material, Supplier, Warehouse
from app.models.hr import Employee
from app.models.inventory import Stock, StockMovement, MovementType, StockType
from app.models.recipe import Recipe
from app.models.quality import QCParameter

from app.schemas.master import (
    ProductCreate, MaterialCreate, SupplierCreate, WarehouseCreate,
)
from app.schemas.hr import EmployeeCreate
from app.schemas.quality import QCParameterCreate
from pydantic import BaseModel

# ── Adapters ──────────────────────────────────────────────────────────────────


class ProductAdapter(BaseImportAdapter):
    module       = "products"
    perm_module  = "products"
    schema_class = ProductCreate
    unique_key   = ["sku"]
    field_overrides: dict = {}
    example_row  = {
        "sku": "SKU001", "name": "Tomato Sauce 500ml",
        "category": "FOOD", "uom": "PCS",
        "units_per_carton": "12", "selling_price": "150.00", "standard_cost": "95.00",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(Product).where(Product.sku == row.get("sku")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = Product(**data)
        db.add(obj)
        await db.flush()
        return obj


class MaterialAdapter(BaseImportAdapter):
    module        = "materials"
    perm_module   = "materials"
    schema_class  = MaterialCreate
    unique_key    = ["code"]
    # supplier_id UUID → supplier_code business key
    field_overrides = {"supplier_id": "supplier_code"}
    example_row   = {
        "code": "MAT001", "name": "Tomato Paste",
        "material_type": "RAW", "uom": "KG",
        "standard_cost": "80.00", "lead_time_days": "7", "supplier_code": "SUP001",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        code = row.pop("supplier_code", None)
        if code:
            r = await db.execute(select(Supplier).where(Supplier.code == code))
            sup = r.scalar_one_or_none()
            if sup is None:
                errors.append(f"supplier_code '{code}' not found")
            else:
                row["supplier_id"] = sup.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(Material).where(Material.code == row.get("code")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = Material(**data)
        db.add(obj)
        await db.flush()
        return obj


class SupplierAdapter(BaseImportAdapter):
    module       = "suppliers"
    perm_module  = "procurement"
    schema_class = SupplierCreate
    unique_key   = ["code"]
    field_overrides: dict = {}
    example_row  = {
        "code": "SUP001", "name": "ABC Suppliers Ltd",
        "contact_person": "John Doe", "email": "john@abc.com",
        "phone": "+254700000000", "city": "Nairobi", "country": "Kenya",
        "payment_terms_days": "30", "preferred_payment_method": "MPESA",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(Supplier).where(Supplier.code == row.get("code")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = Supplier(**data)
        db.add(obj)
        await db.flush()
        return obj


class WarehouseAdapter(BaseImportAdapter):
    module       = "warehouses"
    perm_module  = "warehouses"
    schema_class = WarehouseCreate
    unique_key   = ["code"]
    field_overrides: dict = {}
    example_row  = {
        "code": "WH001", "name": "Main Warehouse",
        "warehouse_type": "FINISHED_GOODS",
        "city": "Nairobi", "country": "Kenya", "capacity_sqm": "5000",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(Warehouse).where(Warehouse.code == row.get("code")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = Warehouse(**data)
        db.add(obj)
        await db.flush()
        return obj


class EmployeeAdapter(BaseImportAdapter):
    module       = "employees"
    perm_module  = "hr"
    schema_class = EmployeeCreate
    unique_key   = ["employee_code"]
    field_overrides: dict = {}
    example_row  = {
        "employee_code": "EMP001", "full_name": "Jane Mwangi",
        "department": "Operations", "role": "Line Operator",
        "hire_date": date.today().isoformat(), "status": "ACTIVE",
        "phone": "+254700000001", "payment_method": "MPESA",
        "mpesa_number": "+254700000001",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(Employee).where(Employee.employee_code == row.get("employee_code"))
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = Employee(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# Flat Pydantic schema for inventory initial stock import
class _StockEntryImport(BaseModel):
    product_sku:    str
    warehouse_code: str
    quantity:       Decimal
    unit_cost:      Optional[Decimal] = None
    lot_number:     Optional[str] = None
    expiry_date:    Optional[date] = None
    reference:      str
    notes:          Optional[str] = None


class InventoryStockAdapter(BaseImportAdapter):
    module          = "inventory_stock"
    perm_module     = "inventory"
    schema_class    = _StockEntryImport
    unique_key      = ["product_sku", "warehouse_code", "reference"]
    field_overrides : dict = {}
    example_row     = {
        "product_sku": "SKU001", "warehouse_code": "WH001",
        "quantity": "100", "unit_cost": "95.00",
        "reference": "INIT-2024-001", "lot_number": "LOT001",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []

        sku = row.pop("product_sku", None)
        wh_code = row.pop("warehouse_code", None)

        if sku:
            r = await db.execute(select(Product).where(Product.sku == sku))
            prod = r.scalar_one_or_none()
            if prod is None:
                errors.append(f"product_sku '{sku}' not found")
            else:
                row["product_id"] = prod.id
        else:
            errors.append("product_sku is required")

        if wh_code:
            r = await db.execute(select(Warehouse).where(Warehouse.code == wh_code))
            wh = r.scalar_one_or_none()
            if wh is None:
                errors.append(f"warehouse_code '{wh_code}' not found")
            else:
                row["warehouse_id"] = wh.id
        else:
            errors.append("warehouse_code is required")

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False  # stock entries are always additive

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from sqlalchemy import and_

        product_id   = data["product_id"]
        warehouse_id = data["warehouse_id"]
        quantity     = Decimal(str(data["quantity"]))
        unit_cost    = data.get("unit_cost")

        # Upsert stock balance
        r = await db.execute(
            select(Stock).where(
                and_(Stock.product_id == product_id,
                     Stock.warehouse_id == warehouse_id,
                     Stock.lot_id.is_(None))
            )
        )
        stock = r.scalar_one_or_none()
        if stock:
            stock.quantity_on_hand += quantity
            stock.quantity_available += quantity
        else:
            stock = Stock(
                stock_type=StockType.PRODUCT,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=quantity,
                quantity_reserved=Decimal("0"),
                quantity_available=quantity,
            )
            db.add(stock)

        # Record movement
        mv = StockMovement(
            reference_number=data.get("reference", "IMPORT"),
            movement_type=MovementType.RECEIPT,
            stock_type=StockType.PRODUCT,
            movement_date=date.today(),
            product_id=product_id,
            destination_warehouse_id=warehouse_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost if unit_cost else None,
            notes=data.get("notes"),
        )
        db.add(mv)
        await db.flush()
        return stock


# Flat schema for Recipe header import
class _RecipeImport(BaseModel):
    product_sku: str       # resolved → product_id
    version:     str
    name:        str
    description: Optional[str] = None
    is_active:   bool = True
    valid_from:  Optional[date] = None
    valid_to:    Optional[date] = None


class RecipeAdapter(BaseImportAdapter):
    module          = "recipes"
    perm_module     = "production"
    schema_class    = _RecipeImport
    unique_key      = ["product_sku", "version"]
    field_overrides : dict = {}
    example_row     = {
        "product_sku": "SKU001", "version": "v1.0",
        "name": "Standard Tomato Sauce Recipe", "is_active": "true",
        "valid_from": date.today().isoformat(),
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        sku = row.pop("product_sku", None)
        if sku:
            r = await db.execute(select(Product).where(Product.sku == sku))
            prod = r.scalar_one_or_none()
            if prod is None:
                errors.append(f"product_sku '{sku}' not found")
            else:
                row["product_id"] = prod.id
        else:
            errors.append("product_sku is required")
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(Recipe).where(
                Recipe.product_id == row.get("product_id"),
                Recipe.version == row.get("version"),
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from app.models.recipe import RecipeStatus
        obj = Recipe(
            product_id=data["product_id"],
            version=data["version"],
            name=data["name"],
            description=data.get("description"),
            is_active=data.get("is_active", True),
            valid_from=data.get("valid_from"),
            valid_to=data.get("valid_to"),
            status=RecipeStatus.DRAFT,
        )
        db.add(obj)
        await db.flush()
        return obj


class QCParameterAdapter(BaseImportAdapter):
    module       = "qc_parameters"
    perm_module  = "quality"
    schema_class = QCParameterCreate
    unique_key   = ["name"]
    field_overrides: dict = {}
    example_row  = {
        "name": "pH Level", "parameter_type": "NUMERIC",
        "unit": "pH", "min_value": "3.5", "max_value": "4.5",
        "is_critical": "true", "applicable_types": "ALL",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(QCParameter).where(QCParameter.name == row.get("name"))
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = QCParameter(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Adapter registry ──────────────────────────────────────────────────────────

ADAPTERS: dict[str, BaseImportAdapter] = {
    "products":        ProductAdapter(),
    "materials":       MaterialAdapter(),
    "suppliers":       SupplierAdapter(),
    "warehouses":      WarehouseAdapter(),
    "employees":       EmployeeAdapter(),
    "inventory_stock": InventoryStockAdapter(),
    "recipes":         RecipeAdapter(),
    "qc_parameters":   QCParameterAdapter(),
}

# Permission module mapping  (adapter.module → permission prefix in seed.py)
_PERM_MODULE: dict[str, str] = {a.module: a.perm_module for a in ADAPTERS.values()}


# ── Permission helper ─────────────────────────────────────────────────────────

async def _assert_perm(perm_module: str, action: str, user: User, db: AsyncSession) -> None:
    if user.is_superuser:
        return
    code = f"{perm_module}.{action}"
    # Lazy-load roles + permissions
    from sqlalchemy.orm import selectinload
    r = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(
            __import__("app.models.role", fromlist=["Role"]).Role.permissions
        ))
        .where(User.id == user.id)
    )
    loaded = r.scalar_one_or_none()
    if loaded:
        for role in loaded.roles:
            for perm in role.permissions:
                if perm.code == code:
                    return
    raise HTTPException(status_code=403, detail=f"Permission required: {code}")


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter()


def _get_adapter(module: str) -> BaseImportAdapter:
    adapter = ADAPTERS.get(module)
    if not adapter:
        supported = ", ".join(sorted(ADAPTERS.keys()))
        raise HTTPException(
            status_code=404,
            detail=f"No import adapter for module '{module}'. Supported: {supported}",
        )
    return adapter


# ── Template download ─────────────────────────────────────────────────────────

@router.get("/{module}/template")
async def download_template(
    module:       str,
    current_user: User            = Depends(get_current_user),
    db:           AsyncSession    = Depends(get_db),
):
    """Download a CSV template for the given module."""
    adapter = _get_adapter(module)
    await _assert_perm(_PERM_MODULE[module], "import_template", current_user, db)

    csv_bytes = adapter.build_template()
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{module}_template.csv"'},
    )


# ── Validate (no DB write) ────────────────────────────────────────────────────

@router.post("/{module}/validate")
async def validate_import(
    module:       str,
    file:         UploadFile        = File(...),
    current_user: User              = Depends(get_current_user),
    db:           AsyncSession      = Depends(get_db),
):
    """Validate a CSV without writing to the database."""
    adapter = _get_adapter(module)
    await _assert_perm(_PERM_MODULE[module], "import", current_user, db)

    content = await file.read()
    result = await import_engine.run(
        content=content,
        adapter=adapter,
        mode=ImportMode.VALIDATE_ONLY,
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        user_roles=[r.name for r in getattr(current_user, "roles", [])],
        file_name=file.filename or "upload.csv",
    )
    await db.commit()
    return result.to_response()


# ── Full import ───────────────────────────────────────────────────────────────

@router.post("/{module}/import")
async def run_import(
    module:       str,
    file:         UploadFile        = File(...),
    mode:         ImportMode        = Form(ImportMode.IMPORT_VALID_ONLY),
    current_user: User              = Depends(get_current_user),
    db:           AsyncSession      = Depends(get_db),
):
    """
    Run a bulk import.
    mode = import_valid_only  → skip invalid rows, import valid ones
    mode = strict             → abort if any row has errors
    """
    adapter = _get_adapter(module)
    await _assert_perm(_PERM_MODULE[module], "import", current_user, db)

    if mode == ImportMode.VALIDATE_ONLY:
        raise HTTPException(status_code=400, detail="Use /validate for validate_only mode")

    content = await file.read()
    result = await import_engine.run(
        content=content,
        adapter=adapter,
        mode=mode,
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        user_roles=[r.name for r in getattr(current_user, "roles", [])],
        file_name=file.filename or "upload.csv",
    )
    await db.commit()
    return result.to_response()


# ── Import history ────────────────────────────────────────────────────────────

@router.get("/history")
async def list_import_history(
    module:       Optional[str]  = Query(None),
    username:     Optional[str]  = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    skip:         int            = Query(0, ge=0),
    limit:        int            = Query(50, ge=1, le=200),
    current_user: User           = Depends(get_current_user),
    db:           AsyncSession   = Depends(get_db),
):
    """Import history log. Any authenticated user sees their own; superusers see all."""
    q = select(ImportHistory).order_by(ImportHistory.created_at.desc())

    if not current_user.is_superuser:
        q = q.where(ImportHistory.user_id == current_user.id)

    if module:
        q = q.where(ImportHistory.module == module)
    if username:
        q = q.where(ImportHistory.username.ilike(f"%{username}%"))
    if date_from:
        q = q.where(ImportHistory.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(ImportHistory.created_at <= datetime.combine(date_to, datetime.max.time()))

    q = q.offset(skip).limit(limit)
    r = await db.execute(q)
    rows = r.scalars().all()

    return [
        {
            "id":            str(h.id),
            "module":        h.module,
            "file_name":     h.file_name,
            "import_mode":   h.import_mode,
            "total_rows":    h.total_rows,
            "success_count": h.success_count,
            "failure_count": h.failure_count,
            "status":        h.status,
            "username":      h.username,
            "user_roles":    h.user_roles,
            "created_at":    h.created_at.isoformat() if h.created_at else None,
        }
        for h in rows
    ]


@router.get("/history/{history_id}/errors")
async def download_history_errors(
    history_id:   _uuid.UUID,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Download error CSV for a specific import history run."""
    r = await db.execute(select(ImportHistory).where(ImportHistory.id == history_id))
    record = r.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="History record not found")

    # Users can only download their own unless superuser
    if not current_user.is_superuser and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    if not record.errors_json:
        return Response(content=b"row,field,message\n", media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="no_errors.csv"'})

    buf = io.StringIO()
    import csv as _csv
    writer = _csv.DictWriter(buf, fieldnames=["row", "field", "message"])
    writer.writeheader()
    for e in record.errors_json:
        writer.writerow(e)

    return Response(
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="errors_{record.module}_{history_id}.csv"'},
    )


# ── Module manifest (for frontend discovery) ─────────────────────────────────

@router.get("/modules")
async def list_import_modules(_: User = Depends(get_current_user)):
    """Return the list of importable modules with their permission info."""
    return [
        {
            "module":      a.module,
            "perm_module": a.perm_module,
            "unique_key":  a.unique_key,
            "fields":      [
                {
                    "name":        m.name,
                    "required":    m.required,
                    "type":        m.type_hint,
                    "enum_values": m.enum_values,
                    "default":     m.default,
                }
                for m in a.field_metas()
            ],
        }
        for a in ADAPTERS.values()
    ]
