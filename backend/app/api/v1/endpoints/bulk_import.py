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
from app.models.utility_management import (
    UtilityAssetCategory as _UtilityAssetCategory,
    UtilityAsset as _UtilityAsset,
    UtilityDevice as _UtilityDevice,
    UtilityTransaction as _UtilityTransaction,
    UtilityReading as _UtilityReading,
    UtilityTariff as _UtilityTariff,
    UtilityBill as _UtilityBill,
    UtilityCostAllocation as _UtilityCostAllocation,
    UtilityAlarmRule as _UtilityAlarmRule,
    UtilityType as _UtilityType,
    SourceMethod as _SourceMethod,
    DataQuality as _DataQuality,
    SoftWaterRecord as _SoftWaterRecord,
    BoilerSteamRecord as _BoilerSteamRecord,
    BoilerStatus as _BoilerStatus,
    CompressorRecord as _CompressorRecord,
    CompressorStatus as _CompressorStatus,
    SolarRecord as _SolarRecord,
    TreatmentChemicalRecord as _TreatmentChemicalRecord,
    WastewaterRecord as _WastewaterRecord,
    WaterTreatmentChemical as _WaterTreatmentChemical,
    BillStatus as _BillStatus,
    AllocationMethod as _AllocationMethod,
    AlarmOperator as _AlarmOperator,
    AlarmSeverity as _AlarmSeverity,
    WastewaterProcess as _WastewaterProcess,
    ComplianceStatus as _ComplianceStatus,
    TreatmentType as _TreatmentType,
    DosingMode as _DosingMode,
)

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


# ── Recipe BOM Items adapter ──────────────────────────────────────────────────

class _RecipeItemImport(BaseModel):
    """
    CSV schema for bulk-importing BOM / Formulation Items into a recipe.
    Links to the recipe via product_sku + version (recipe must exist as DRAFT).
    Upsert behaviour: if a row with the same recipe + line_no already exists,
    it is updated; otherwise a new row is inserted.
    """
    product_sku:       str
    version:           str
    line_no:           int
    material_code:     str               # resolved → material_id
    quantity:          Decimal
    unit:              str
    loss_percent:      Optional[Decimal] = None   # → loss_percentage (0 if blank)
    optional:          Optional[bool]    = False   # → is_optional
    alternative_group: Optional[str]    = None
    notes:             Optional[str]    = None


class RecipeItemAdapter(BaseImportAdapter):
    """
    Bulk-import BOM lines for existing DRAFT recipes.

    Update behaviour:
      - If a RecipeItem with the same recipe + line_no already exists → UPDATE it.
      - If not → INSERT a new row.
      - To replace ALL lines for a recipe, delete existing lines manually before
        importing (or import with overlapping line_no values to overwrite).

    Permission: production.import
    """
    module          = "recipe_items"
    perm_module     = "production"
    schema_class    = _RecipeItemImport
    unique_key      = ["product_sku", "version", "line_no"]
    field_overrides : dict = {}
    example_row     = {
        "product_sku": "HH-001",      "version": "v1.0",
        "line_no": "1",               "material_code": "MAT001",
        "quantity": "120",            "unit": "KG",
        "loss_percent": "2",          "optional": "false",
        "alternative_group": "",      "notes": "Primary surfactant",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        from app.models.recipe import RecipeStatus

        errors: list[str] = []
        sku = row.pop("product_sku", None)
        ver = row.get("version")

        if not sku:
            errors.append("product_sku is required")
            return row, errors

        # 1. Look up finished product
        r = await db.execute(select(Product).where(Product.sku == sku))
        prod = r.scalar_one_or_none()
        if prod is None:
            errors.append(f"Finished product SKU '{sku}' not found")
            return row, errors

        # 2. Look up recipe (must exist and be DRAFT)
        r2 = await db.execute(
            select(Recipe).where(
                Recipe.product_id == prod.id,
                Recipe.version == ver,
            )
        )
        recipe = r2.scalar_one_or_none()
        if recipe is None:
            errors.append(
                f"Recipe for product '{sku}' version '{ver}' not found"
                " — import recipe headers first"
            )
            return row, errors
        if recipe.status != RecipeStatus.DRAFT:
            errors.append(
                f"Recipe '{sku}' v{ver} has status {recipe.status}"
                " — only DRAFT recipes can be modified"
            )
            return row, errors
        row["recipe_id"] = recipe.id

        # 3. Look up material
        mat_code = row.pop("material_code", None)
        if not mat_code:
            errors.append("material_code is required")
            return row, errors
        r3 = await db.execute(select(Material).where(Material.code == mat_code))
        mat = r3.scalar_one_or_none()
        if mat is None:
            errors.append(f"Material code '{mat_code}' not found")
        else:
            row["material_id"] = mat.id

        # 4. Business rule: quantity > 0
        qty = row.get("quantity")
        if qty is not None and qty <= 0:
            errors.append("quantity must be greater than zero")

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        # Always return False so the engine does not reject the row.
        # Upsert (update-or-insert) logic lives in insert().
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from app.models.recipe import RecipeItem
        from sqlalchemy import and_

        recipe_id = data["recipe_id"]
        line_no   = data["line_no"]

        # Check for an existing item with the same recipe + line_no
        r = await db.execute(
            select(RecipeItem).where(
                and_(
                    RecipeItem.recipe_id == recipe_id,
                    RecipeItem.line_no   == line_no,
                )
            )
        )
        item = r.scalar_one_or_none()

        loss_pct    = data.get("loss_percent")
        is_optional = data.get("optional")

        if item:
            # UPDATE existing row
            item.material_id       = data["material_id"]
            item.quantity          = data["quantity"]
            item.unit              = data["unit"]
            item.loss_percentage   = loss_pct    if loss_pct    is not None else 0
            item.is_optional       = is_optional if is_optional is not None else False
            item.alternative_group = data.get("alternative_group") or None
            item.notes             = data.get("notes") or None
        else:
            # INSERT new row
            item = RecipeItem(
                recipe_id=recipe_id,
                material_id=data["material_id"],
                line_no=line_no,
                quantity=data["quantity"],
                unit=data["unit"],
                loss_percentage=loss_pct    if loss_pct    is not None else 0,
                is_optional    =is_optional if is_optional is not None else False,
                alternative_group=data.get("alternative_group") or None,
                notes            =data.get("notes") or None,
            )
            db.add(item)

        await db.flush()
        return item


# ── Recipe Process Steps adapter ──────────────────────────────────────────────

class _RecipeStepImport(BaseModel):
    """
    CSV schema for bulk-importing Process Parameters (steps) into a recipe.
    Links to the recipe via product_sku + version (recipe must exist as DRAFT).
    Upsert behaviour: if a row with the same recipe + step_no already exists,
    it is updated; otherwise a new row is inserted.
    """
    product_sku:   str
    version:       str
    step_no:       int
    step_name:     str
    temperature_c: Optional[Decimal] = None   # → target_temperature
    target_ph:     Optional[Decimal] = None
    viscosity_cp:  Optional[Decimal] = None   # → target_viscosity
    mix_time_min:  Optional[int]     = None   # → mixing_time_minutes
    rpm:           Optional[int]     = None
    notes:         Optional[str]     = None


class RecipeStepAdapter(BaseImportAdapter):
    """
    Bulk-import process steps for existing DRAFT recipes.

    Update behaviour:
      - If a ProcessParameter with the same recipe + step_no already exists → UPDATE it.
      - If not → INSERT a new row.

    Permission: production.import
    """
    module          = "recipe_steps"
    perm_module     = "production"
    schema_class    = _RecipeStepImport
    unique_key      = ["product_sku", "version", "step_no"]
    field_overrides : dict = {}
    example_row     = {
        "product_sku": "HH-001",    "version": "v1.0",
        "step_no": "1",             "step_name": "Dry Premix",
        "temperature_c": "",        "target_ph": "",
        "viscosity_cp": "",         "mix_time_min": "15",
        "rpm": "120",               "notes": "Blend powder base",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        from app.models.recipe import RecipeStatus

        errors: list[str] = []
        sku = row.pop("product_sku", None)
        ver = row.get("version")

        if not sku:
            errors.append("product_sku is required")
            return row, errors

        # 1. Look up finished product
        r = await db.execute(select(Product).where(Product.sku == sku))
        prod = r.scalar_one_or_none()
        if prod is None:
            errors.append(f"Finished product SKU '{sku}' not found")
            return row, errors

        # 2. Look up recipe (must exist and be DRAFT)
        r2 = await db.execute(
            select(Recipe).where(
                Recipe.product_id == prod.id,
                Recipe.version == ver,
            )
        )
        recipe = r2.scalar_one_or_none()
        if recipe is None:
            errors.append(
                f"Recipe for product '{sku}' version '{ver}' not found"
                " — import recipe headers first"
            )
            return row, errors
        if recipe.status != RecipeStatus.DRAFT:
            errors.append(
                f"Recipe '{sku}' v{ver} has status {recipe.status}"
                " — only DRAFT recipes can be modified"
            )
            return row, errors
        row["recipe_id"] = recipe.id

        # 3. Business rule: step_name must not be blank (already enforced by
        #    Pydantic required field, but this gives a friendlier message)
        if not row.get("step_name", "").strip():
            errors.append("step_name is required and cannot be blank")

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        # Always return False so the engine does not reject the row.
        # Upsert (update-or-insert) logic lives in insert().
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from app.models.recipe import ProcessParameter
        from sqlalchemy import and_

        recipe_id = data["recipe_id"]
        step_no   = data["step_no"]

        r = await db.execute(
            select(ProcessParameter).where(
                and_(
                    ProcessParameter.recipe_id == recipe_id,
                    ProcessParameter.step_no   == step_no,
                )
            )
        )
        param = r.scalar_one_or_none()

        if param:
            # UPDATE existing step
            param.step_name          = data["step_name"]
            param.target_temperature = data.get("temperature_c")
            param.target_ph          = data.get("target_ph")
            param.target_viscosity   = data.get("viscosity_cp")
            param.mixing_time_minutes = data.get("mix_time_min")
            param.rpm                = data.get("rpm")
            param.notes              = data.get("notes") or None
        else:
            # INSERT new step
            param = ProcessParameter(
                recipe_id=recipe_id,
                step_no=step_no,
                step_name=data["step_name"],
                target_temperature=data.get("temperature_c"),
                target_ph         =data.get("target_ph"),
                target_viscosity  =data.get("viscosity_cp"),
                mixing_time_minutes=data.get("mix_time_min"),
                rpm               =data.get("rpm"),
                notes             =data.get("notes") or None,
            )
            db.add(param)

        await db.flush()
        return param


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


# ── Advanced Production Import Adapters ───────────────────────────────────────

from app.models.production_advanced import (
    WorkCenter as _WC, Routing as _Routing, WorkOrder as _WorkOrder,
    Shift as _Shift, ProductionSchedule as _Schedule,
    TimeTracking as _TT, DowntimeEvent as _DT,
    AdvQCInspection as _QCI, WasteRecord as _WR, BatchLot as _BL,
    LaborLog as _LL, OEERecord as _OEE,
)
from app.schemas.production_advanced import (
    WorkCenterCreate as _WCCreate,
    ShiftCreate as _ShiftCreate,
)
from app.models.production import ProductionOrder as _PO


class WorkCenterImportAdapter(BaseImportAdapter):
    module       = "work_centers"
    perm_module  = "production"
    schema_class = _WCCreate
    unique_key   = ["work_center_id"]
    field_overrides: dict = {}
    example_row  = {
        "work_center_id": "WC001", "name": "Mixing Line 1",
        "type": "LINE", "capacity": "2000", "capacity_uom": "L",
        "location": "Nairobi", "status": "active",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_WC).where(_WC.work_center_id == row.get("work_center_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _WC(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _RoutingImport(BaseModel):
    routing_id:  str
    product_sku: str
    version:     int = 1
    name:        Optional[str] = None
    is_active:   bool = True


class RoutingImportAdapter(BaseImportAdapter):
    module       = "routings"
    perm_module  = "production"
    schema_class = _RoutingImport
    unique_key   = ["routing_id"]
    field_overrides: dict = {}
    example_row  = {
        "routing_id": "R001", "product_sku": "DET001",
        "version": "1", "name": "Standard Routing", "is_active": "true",
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
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_Routing).where(_Routing.routing_id == row.get("routing_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _Routing(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _WorkOrderImport(BaseModel):
    work_order_id:    str
    production_order_no: str   # resolved → production_order_id
    work_center_code: str      # resolved → work_center_id
    operation:        str
    operator:         Optional[str] = None
    status:           str = "planned"
    start_time:       Optional[datetime] = None
    end_time:         Optional[datetime] = None


class WorkOrderImportAdapter(BaseImportAdapter):
    module       = "work_orders"
    perm_module  = "production"
    schema_class = _WorkOrderImport
    unique_key   = ["work_order_id"]
    field_overrides: dict = {}
    example_row  = {
        "work_order_id": "WO001", "production_order_no": "PO001",
        "work_center_code": "WC001", "operation": "Mixing",
        "operator": "Operator1", "status": "in_progress",
        "start_time": "2026-04-01 08:00", "end_time": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        po_no = row.pop("production_order_no", None)
        if po_no:
            r = await db.execute(select(_PO).where(_PO.order_no == po_no))
            po = r.scalar_one_or_none()
            if po is None:
                errors.append(f"production_order_no '{po_no}' not found")
            else:
                row["production_order_id"] = po.id
        wc_code = row.pop("work_center_code", None)
        if wc_code:
            r2 = await db.execute(select(_WC).where(_WC.work_center_id == wc_code))
            wc = r2.scalar_one_or_none()
            if wc is None:
                errors.append(f"work_center_code '{wc_code}' not found")
            else:
                row["work_center_id"] = wc.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_WorkOrder).where(_WorkOrder.work_order_id == row.get("work_order_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _WorkOrder(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _ScheduleImport(BaseModel):
    schedule_id:         str
    production_order_no: str
    work_center_code:    str
    shift:               Optional[str] = None
    start_time:          datetime
    end_time:            datetime
    status:              str = "planned"
    priority:            str = "medium"


class ScheduleImportAdapter(BaseImportAdapter):
    module       = "production_schedules"
    perm_module  = "production"
    schema_class = _ScheduleImport
    unique_key   = ["schedule_id"]
    field_overrides: dict = {}
    example_row  = {
        "schedule_id": "SCH001", "production_order_no": "PO001",
        "work_center_code": "WC001", "shift": "Shift A",
        "start_time": "2026-04-01 08:00", "end_time": "2026-04-01 16:00",
        "status": "planned", "priority": "high",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        po_no = row.pop("production_order_no", None)
        if po_no:
            r = await db.execute(select(_PO).where(_PO.order_no == po_no))
            po = r.scalar_one_or_none()
            if po is None:
                errors.append(f"production_order_no '{po_no}' not found")
            else:
                row["production_order_id"] = po.id
        wc_code = row.pop("work_center_code", None)
        if wc_code:
            r2 = await db.execute(select(_WC).where(_WC.work_center_id == wc_code))
            wc = r2.scalar_one_or_none()
            if wc is None:
                errors.append(f"work_center_code '{wc_code}' not found")
            else:
                row["work_center_id"] = wc.id
        # shift_name stored as denormalized column
        shift_name = row.pop("shift", None)
        if shift_name:
            row["shift_name"] = shift_name
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_Schedule).where(_Schedule.schedule_id == row.get("schedule_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _Schedule(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _TTImport(BaseModel):
    log_id:            str
    work_order_id_code: str   # resolved from work_order_id column (the string code)
    actual_start:      datetime
    actual_end:        Optional[datetime] = None
    downtime_minutes:  Optional[int] = 0
    reason:            Optional[str] = None


class TimeTrackingImportAdapter(BaseImportAdapter):
    module       = "time_tracking"
    perm_module  = "production"
    schema_class = _TTImport
    unique_key   = ["log_id"]
    field_overrides: dict = {}
    example_row  = {
        "log_id": "LOG001", "work_order_id_code": "WO001",
        "actual_start": "2026-04-01 08:05", "actual_end": "2026-04-01 08:50",
        "downtime_minutes": "5", "reason": "minor delay",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        wo_code = row.pop("work_order_id_code", None)
        if wo_code:
            r = await db.execute(select(_WorkOrder).where(_WorkOrder.work_order_id == wo_code))
            wo = r.scalar_one_or_none()
            if wo is None:
                errors.append(f"work_order '{wo_code}' not found")
            else:
                row["work_order_id"] = wo.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_TT).where(_TT.log_id == row.get("log_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _TT(**{k: v for k, v in data.items() if v is not None})
        if obj.actual_end and obj.actual_start:
            delta = obj.actual_end - obj.actual_start
            obj.duration_actual_min = int(delta.total_seconds() / 60)
        db.add(obj)
        await db.flush()
        return obj


class _DTImport(BaseModel):
    downtime_id:      str
    machine_id:       str
    start_time:       datetime
    end_time:         Optional[datetime] = None
    reason:           str
    category:         str = "unplanned"


class DowntimeImportAdapter(BaseImportAdapter):
    module       = "downtime_events"
    perm_module  = "production"
    schema_class = _DTImport
    unique_key   = ["downtime_id"]
    field_overrides: dict = {}
    example_row  = {
        "downtime_id": "DT001", "machine_id": "M001",
        "start_time": "2026-04-01 10:00", "end_time": "2026-04-01 10:20",
        "reason": "Power outage", "category": "external",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        machine_id = row.get("machine_id")
        if machine_id:
            # Try to resolve work center by work_center_id code
            r = await db.execute(select(_WC).where(_WC.work_center_id == machine_id))
            wc = r.scalar_one_or_none()
            if wc:
                row["work_center_id"] = wc.id
            else:
                # Still allow import but flag
                errors.append(f"machine_id '{machine_id}' does not match any work_center_id — create the work center first")
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_DT).where(_DT.downtime_id == row.get("downtime_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        d = {k: v for k, v in data.items() if v is not None}
        obj = _DT(**d)
        if obj.end_time and obj.start_time:
            delta = obj.end_time - obj.start_time
            obj.duration_min = max(0, int(delta.total_seconds() / 60))
        db.add(obj)
        await db.flush()
        return obj


class _QCImport(BaseModel):
    qc_id:               str
    production_order_no: str
    test_type:           str
    result:              str = "pass"
    value:               Optional[str] = None
    unit:                Optional[str] = None
    status:              str = "pass"
    checked_by:          Optional[str] = None
    date:                Optional[date] = None


class QCInspectionImportAdapter(BaseImportAdapter):
    module       = "qc_inspections"
    perm_module  = "quality"
    schema_class = _QCImport
    unique_key   = ["qc_id"]
    field_overrides: dict = {}
    example_row  = {
        "qc_id": "QC001", "production_order_no": "PO001",
        "test_type": "pH", "result": "pass", "value": "7.2",
        "unit": "pH", "status": "pass", "checked_by": "QA1",
        "date": "2026-04-01",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        po_no = row.pop("production_order_no", None)
        if po_no:
            r = await db.execute(select(_PO).where(_PO.order_no == po_no))
            po = r.scalar_one_or_none()
            if po is None:
                errors.append(f"production_order_no '{po_no}' not found")
            else:
                row["production_order_id"] = po.id
        # Map date → inspected_at
        d = row.pop("date", None)
        if d:
            row["inspected_at"] = d
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_QCI).where(_QCI.qc_id == row.get("qc_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        # Extract result row fields
        test_type   = data.pop("test_type", None)
        result_val  = data.pop("result", "pass")
        value       = data.pop("value", None)
        unit        = data.pop("unit", None)
        # Map status → inspection status
        status = data.get("status", "pass")
        data["status"] = status
        obj = _QCI(**{k: v for k, v in data.items() if v is not None and k not in ("result",)})
        db.add(obj)
        await db.flush()
        if test_type:
            from app.models.production_advanced import AdvQCResult as _QCR
            res = _QCR(
                inspection_id=obj.id,
                test_type=test_type,
                actual_value=Decimal(str(value)) if value else None,
                unit=unit,
                result=result_val,
            )
            db.add(res)
            await db.flush()
        return obj


class _WasteImport(BaseModel):
    waste_id:            str
    production_order_no: str
    material:            str
    expected_qty:        Decimal
    actual_qty:          Decimal
    loss_qty:            Optional[Decimal] = None
    reason:              Optional[str] = None


class WasteImportAdapter(BaseImportAdapter):
    module       = "waste_records"
    perm_module  = "production"
    schema_class = _WasteImport
    unique_key   = ["waste_id"]
    field_overrides: dict = {}
    example_row  = {
        "waste_id": "W001", "production_order_no": "PO001",
        "material": "SLES", "expected_qty": "1000",
        "actual_qty": "950", "loss_qty": "50", "reason": "spillage",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        po_no = row.pop("production_order_no", None)
        if po_no:
            r = await db.execute(select(_PO).where(_PO.order_no == po_no))
            po = r.scalar_one_or_none()
            if po is None:
                errors.append(f"production_order_no '{po_no}' not found")
            else:
                row["production_order_id"] = po.id
        mat_code = row.pop("material", None)
        if mat_code:
            row["material_code"] = mat_code
            from app.models.master import Material
            r2 = await db.execute(select(Material).where(Material.code == mat_code))
            mat = r2.scalar_one_or_none()
            if mat:
                row["material_id"] = mat.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_WR).where(_WR.waste_id == row.get("waste_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from decimal import Decimal as D
        obj = _WR(**{k: v for k, v in data.items() if v is not None})
        if obj.expected_qty and obj.expected_qty > 0:
            obj.loss_qty = obj.expected_qty - obj.actual_qty
            obj.loss_pct = round(obj.loss_qty / obj.expected_qty * 100, 3)
            obj.is_anomaly = obj.loss_pct > D("5.0")
        db.add(obj)
        await db.flush()
        return obj


class _BatchImport(BaseModel):
    batch_id:            str
    production_order_no: str
    product_sku:         str
    quantity:            Decimal
    manufacture_date:    Optional[date] = None
    expiry_date:         Optional[date] = None
    status:              str = "released"


class BatchLotImportAdapter(BaseImportAdapter):
    module       = "batch_lots"
    perm_module  = "production"
    schema_class = _BatchImport
    unique_key   = ["batch_id"]
    field_overrides: dict = {}
    example_row  = {
        "batch_id": "BATCH001", "production_order_no": "PO001",
        "product_sku": "DET001", "quantity": "10000",
        "manufacture_date": "2026-04-01", "expiry_date": "2028-04-01",
        "status": "released",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        po_no = row.pop("production_order_no", None)
        if po_no:
            r = await db.execute(select(_PO).where(_PO.order_no == po_no))
            po = r.scalar_one_or_none()
            if po is None:
                errors.append(f"production_order_no '{po_no}' not found")
            else:
                row["production_order_id"] = po.id
        sku = row.get("product_sku")
        if sku:
            r2 = await db.execute(select(Product).where(Product.sku == sku))
            prod = r2.scalar_one_or_none()
            if prod is None:
                errors.append(f"product_sku '{sku}' not found")
            else:
                row["product_id"] = prod.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_BL).where(_BL.batch_id == row.get("batch_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _BL(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _LaborImport(BaseModel):
    labor_id:       str
    work_order_code: str
    employee_id:    Optional[str] = None
    hours_worked:   Optional[Decimal] = None
    role:           Optional[str] = None


class LaborImportAdapter(BaseImportAdapter):
    module       = "labor_logs"
    perm_module  = "production"
    schema_class = _LaborImport
    unique_key   = ["labor_id"]
    field_overrides: dict = {}
    example_row  = {
        "labor_id": "LAB001", "work_order_code": "WO001",
        "employee_id": "E001", "hours_worked": "8", "role": "operator",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        wo_code = row.pop("work_order_code", None)
        if wo_code:
            r = await db.execute(select(_WorkOrder).where(_WorkOrder.work_order_id == wo_code))
            wo = r.scalar_one_or_none()
            if wo is None:
                errors.append(f"work_order '{wo_code}' not found")
            else:
                row["work_order_id"] = wo.id
        emp_code = row.pop("employee_id", None)
        if emp_code:
            row["employee_code"] = emp_code
            from app.models.hr import Employee
            r2 = await db.execute(select(Employee).where(Employee.employee_code == emp_code))
            emp = r2.scalar_one_or_none()
            if emp:
                row["employee_id"] = emp.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_LL).where(_LL.labor_id == row.get("labor_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _LL(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _OEEImport(BaseModel):
    oee_id:      str
    machine_id:  str
    availability: Optional[Decimal] = None
    performance:  Optional[Decimal] = None
    quality:      Optional[Decimal] = None
    oee_score:    Optional[Decimal] = None
    date:         date


class OEEImportAdapter(BaseImportAdapter):
    module       = "oee_records"
    perm_module  = "production"
    schema_class = _OEEImport
    unique_key   = ["oee_id"]
    field_overrides: dict = {}
    example_row  = {
        "oee_id": "OEE001", "machine_id": "M001",
        "availability": "0.9", "performance": "0.85",
        "quality": "0.95", "oee_score": "0.726",
        "date": "2026-04-01",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        machine_id = row.get("machine_id")
        if machine_id:
            r = await db.execute(select(_WC).where(_WC.work_center_id == machine_id))
            wc = r.scalar_one_or_none()
            if wc is None:
                errors.append(f"machine_id '{machine_id}' not found as work_center_id — create the work center first")
            else:
                row["work_center_id"] = wc.id
        d = row.pop("date", None)
        if d:
            row["record_date"] = d
        # Set a default planned time if not provided
        if "planned_production_time_min" not in row:
            row["planned_production_time_min"] = 480  # 8-hour shift default
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(select(_OEE).where(_OEE.oee_id == row.get("oee_id")))
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        from decimal import Decimal as D
        obj = _OEE(**{k: v for k, v in data.items() if v is not None})
        if obj.oee_score is not None:
            obj.is_low_oee = obj.oee_score < D("0.65")
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Management Adapters ───────────────────────────────────────────────

class _UtilityAssetCategoryImport(BaseModel):
    code: str
    name: str
    utility_type: str
    default_unit: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class UtilityAssetCategoryAdapter(BaseImportAdapter):
    module        = "utility_asset_categories"
    perm_module   = "utility_management"
    schema_class  = _UtilityAssetCategoryImport
    unique_key    = ["code"]
    field_overrides: dict = {}
    example_row   = {
        "code": "BOILER", "name": "Steam Boilers",
        "utility_type": "STEAM", "default_unit": "kg/h",
        "description": "High-pressure steam boilers", "is_active": "true",
    }

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityAssetCategory).where(
                _UtilityAssetCategory.code == (row.get("code") or "").upper()
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        data["code"] = (data.get("code") or "").upper()
        obj = _UtilityAssetCategory(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


class _UtilityAssetImport(BaseModel):
    asset_no: str
    name: str
    category_code: str          # resolved → category_id
    utility_type: str
    subsystem: Optional[str] = None
    location: Optional[str] = None
    building_area: Optional[str] = None
    department: Optional[str] = None
    line_id: Optional[str] = None
    machine_id: Optional[str] = None
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None
    serial_no: Optional[str] = None
    install_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    rated_capacity: Optional[Decimal] = None
    capacity_unit: Optional[str] = None
    rated_power: Optional[Decimal] = None
    rated_power_unit: Optional[str] = None
    flow_capacity: Optional[Decimal] = None
    pressure_capacity: Optional[Decimal] = None
    temperature_range: Optional[str] = None
    lifecycle_status: Optional[str] = None
    criticality_level: Optional[str] = None
    maintenance_strategy: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None
    status: str = "ACTIVE"


class UtilityAssetAdapter(BaseImportAdapter):
    module        = "utility_assets"
    perm_module   = "utility_management"
    schema_class  = _UtilityAssetImport
    unique_key    = ["asset_no"]
    field_overrides = {"category_id": "category_code"}
    example_row   = {
        "asset_no": "BLR-001", "name": "Boiler 1 — Main Steam",
        "category_code": "BOILER", "utility_type": "STEAM",
        "department": "Utilities", "building_area": "Boiler Room",
        "rated_capacity": "2000", "capacity_unit": "kg/h",
        "status": "ACTIVE", "criticality_level": "CRITICAL",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        code = row.pop("category_code", None)
        if code:
            r = await db.execute(
                select(_UtilityAssetCategory).where(
                    _UtilityAssetCategory.code == code.upper()
                )
            )
            cat = r.scalar_one_or_none()
            if cat is None:
                errors.append(f"category_code '{code}' not found — import categories first")
            else:
                row["category_id"] = cat.id
        else:
            errors.append("category_code is required")
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityAsset).where(
                _UtilityAsset.asset_no == (row.get("asset_no") or "").upper()
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        data["asset_no"] = (data.get("asset_no") or "").upper()
        # Map equipment_model → model column
        if "equipment_model" in data:
            data["model"] = data.pop("equipment_model")
        obj = _UtilityAsset(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Device import ──────────────────────────────────────────────────────

class _UtilityDeviceImport(BaseModel):
    device_code:     str
    name:            str
    device_type:     str  # METER / SENSOR / LOGGER / CONTROLLER / ANALYSER
    utility_type:    str
    asset_no:        Optional[str] = None   # resolved → asset_id
    department:      Optional[str] = None
    building_area:   Optional[str] = None
    location:        Optional[str] = None
    related_line_id: Optional[str] = None
    related_machine_id: Optional[str] = None
    reading_type:    Optional[str] = None
    reading_source:  Optional[str] = None
    reading_frequency: Optional[str] = None
    unit_of_measure: str = "units"
    min_value:       Optional[Decimal] = None
    max_value:       Optional[Decimal] = None
    min_alarm_limit: Optional[Decimal] = None
    max_alarm_limit: Optional[Decimal] = None
    calibration_required: bool = False
    calibration_frequency_days: Optional[int] = None
    last_calibration_date: Optional[date] = None
    next_calibration_date: Optional[date] = None
    manufacturer:    Optional[str] = None
    serial_no:       Optional[str] = None
    is_active:       bool = True
    notes:           Optional[str] = None


class UtilityDeviceAdapter(BaseImportAdapter):
    module        = "utility_devices"
    perm_module   = "utility_management"
    schema_class  = _UtilityDeviceImport
    unique_key    = ["device_code"]
    field_overrides = {"asset_id": "asset_no"}
    example_row   = {
        "device_code": "MTR-ELEC-001", "name": "Main Electricity Meter",
        "device_type": "METER", "utility_type": "ELECTRICITY",
        "reading_type": "CUMULATIVE", "unit_of_measure": "kWh",
        "department": "Utilities", "building_area": "Main Substation",
        "min_alarm_limit": "0", "max_alarm_limit": "5000",
        "calibration_required": "true", "calibration_frequency_days": "365",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(
                    _UtilityAsset.asset_no == asset_no.upper()
                )
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found")
            else:
                row["asset_id"] = asset.id
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityDevice).where(
                _UtilityDevice.device_code == (row.get("device_code") or "").upper()
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        data["device_code"] = (data.get("device_code") or "").upper()
        obj = _UtilityDevice(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Electricity Transaction import ────────────────────────────────────────────

class _ElectricityTxImport(BaseModel):
    """
    CSV schema for bulk-importing electricity consumption records.
    Maps directly to utility_transactions with utility_type=ELECTRICITY.
    Cost is auto-computed if cost_rate and quantity are provided but total_cost is blank.
    """
    transaction_date: date
    quantity:         Decimal                       # kWh consumed
    uom:              str = "kWh"
    department:       Optional[str] = None
    building_area:    Optional[str] = None
    production_line:  Optional[str] = None          # → production_line column
    machine_ref:      Optional[str] = None          # → machine_ref column
    shift_ref:        Optional[str] = None
    batch_no:         Optional[str] = None
    cost_rate:        Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    currency_code:    str = "USD"
    variance_from_standard: Optional[Decimal] = None
    source_method:    str = "IMPORTED"
    quality:          str = "GOOD"
    is_estimated:     bool = False
    is_anomaly:       bool = False
    anomaly_note:     Optional[str] = None
    notes:            Optional[str] = None
    # Optional reference
    reference_type:   Optional[str] = None          # e.g. MANUAL, METER_READING
    reference_id:     Optional[str] = None


class ElectricityTransactionAdapter(BaseImportAdapter):
    """
    Bulk-import electricity consumption records.

    Each CSV row creates one utility_transaction with utility_type=ELECTRICITY.
    transaction_no is auto-generated (TX-{date}-{5 digits}).
    Cost is auto-computed when cost_rate × quantity present but total_cost blank.

    Permission: utility_management.import
    """
    module          = "electricity_transactions"
    perm_module     = "utility_management"
    schema_class    = _ElectricityTxImport
    unique_key: list = []          # no natural key; every row inserts
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "quantity": "1200.50",         "uom": "kWh",
        "department": "Production",    "building_area": "Block A",
        "production_line": "LINE-01",  "machine_ref": "MCH-001",
        "shift_ref": "A",              "batch_no": "BATCH-2025-001",
        "cost_rate": "0.12",           "total_cost": "",
        "currency_code": "USD",        "source_method": "MANUAL",
        "quality": "GOOD",             "is_estimated": "false",
        "is_anomaly": "false",         "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []

        # Auto-compute total_cost
        qty  = row.get("quantity")
        rate = row.get("cost_rate")
        cost = row.get("total_cost")
        if qty and rate and not cost:
            row["total_cost"] = _D(str(qty)) * _D(str(rate))

        # Validate source_method / quality enums
        sm = row.get("source_method", "IMPORTED")
        if sm not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        dq = row.get("quality", "GOOD")
        if dq not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        # We never skip electricity rows — every import row is a new event.
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        d = data.get("transaction_date")
        date_str = d.strftime("%Y%m%d") if isinstance(d, _date) else str(d)[:8].replace("-", "")
        tx_no = f"TX-{date_str}-{random.randint(10000, 99999)}"
        obj = _UtilityTransaction(
            transaction_no=tx_no,
            utility_type=_UtilityType.ELECTRICITY,
            transaction_date=data.get("transaction_date"),
            quantity=data.get("quantity"),
            unit_of_measure=data.get("uom", "kWh"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            cost_rate=data.get("cost_rate"),
            total_cost=data.get("total_cost"),
            currency_code=data.get("currency_code", "USD"),
            variance_from_standard=data.get("variance_from_standard"),
            source_method=data.get("source_method", "IMPORTED"),
            quality=data.get("quality", "GOOD"),
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Water Transaction adapter ─────────────────────────────────────────────────

class _WaterTxImport(BaseModel):
    """
    CSV schema for bulk-importing water consumption records.
    utility_type field determines which sub-type to import:
      WATER | PROCESS_WATER | WASTEWATER
    """
    transaction_date: date
    utility_type:     str = "WATER"       # WATER | PROCESS_WATER | WASTEWATER
    quantity:         Decimal             # m³
    uom:              str = "m3"
    department:       Optional[str] = None
    building_area:    Optional[str] = None
    production_line:  Optional[str] = None
    machine_ref:      Optional[str] = None
    shift_ref:        Optional[str] = None
    batch_no:         Optional[str] = None
    cost_rate:        Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    currency_code:    str = "USD"
    source_method:    str = "IMPORTED"
    quality:          str = "GOOD"
    is_estimated:     bool = False
    is_anomaly:       bool = False
    anomaly_note:     Optional[str] = None
    notes:            Optional[str] = None


class WaterTransactionAdapter(BaseImportAdapter):
    """
    Bulk-import water consumption records.
    Supports WATER, PROCESS_WATER, and WASTEWATER utility types.
    """
    module          = "water_transactions"
    perm_module     = "utility_management"
    schema_class    = _WaterTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "utility_type": "WATER",       "quantity": "250.00",
        "uom": "m3",                   "department": "Production",
        "building_area": "Block A",    "production_line": "LINE-01",
        "machine_ref": "",             "shift_ref": "A",
        "batch_no": "",                "cost_rate": "1.20",
        "total_cost": "",              "currency_code": "USD",
        "source_method": "MANUAL",     "quality": "GOOD",
        "is_estimated": "false",       "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []

        # Validate utility type
        valid_water = {"WATER", "PROCESS_WATER", "WASTEWATER"}
        ut = (row.get("utility_type") or "WATER").upper()
        if ut not in valid_water:
            row["utility_type"] = "WATER"

        # Auto-compute total_cost
        qty  = row.get("quantity")
        rate = row.get("cost_rate")
        cost = row.get("total_cost")
        if qty and rate and not cost:
            row["total_cost"] = _D(str(qty)) * _D(str(rate))

        # Validate enums
        sm = row.get("source_method", "IMPORTED")
        if sm not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        dq = row.get("quality", "GOOD")
        if dq not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        d = data.get("transaction_date")
        date_str = d.strftime("%Y%m%d") if isinstance(d, _date) else str(d)[:8].replace("-", "")
        tx_no = f"WTX-{date_str}-{random.randint(10000, 99999)}"
        ut_str = (data.get("utility_type") or "WATER").upper()
        try:
            ut = _UtilityType(ut_str)
        except ValueError:
            ut = _UtilityType.WATER
        obj = _UtilityTransaction(
            transaction_no=tx_no,
            utility_type=ut,
            transaction_date=data.get("transaction_date"),
            quantity=data.get("quantity"),
            unit_of_measure=data.get("uom", "m3"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            cost_rate=data.get("cost_rate"),
            total_cost=data.get("total_cost"),
            currency_code=data.get("currency_code", "USD"),
            source_method=data.get("source_method", "IMPORTED"),
            quality=data.get("quality", "GOOD"),
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Soft Water Record adapter ─────────────────────────────────────────────────

class _SoftWaterImport(BaseModel):
    """CSV schema for bulk-importing soft water operational records."""
    record_datetime:            datetime
    asset_no:                   str         # resolved → asset_id
    volume_treated_m3:          Optional[Decimal] = None
    raw_water_input_m3:         Optional[Decimal] = None
    feed_water_hardness_ppm:    Optional[Decimal] = None
    product_water_hardness_ppm: Optional[Decimal] = None
    feed_water_tds_ppm:         Optional[Decimal] = None
    product_water_tds_ppm:      Optional[Decimal] = None
    conductivity_feed_uscm:     Optional[Decimal] = None
    conductivity_product_uscm:  Optional[Decimal] = None
    salt_consumed_kg:           Optional[Decimal] = None
    regeneration_count:         Optional[int] = None
    efficiency_pct:             Optional[Decimal] = None
    downtime_minutes:           Optional[int] = None
    maintenance_flag:           bool = False
    destination_tag:            Optional[str] = None
    department:                 Optional[str] = None
    shift_ref:                  Optional[str] = None
    source_method:              str = "IMPORTED"
    is_anomaly:                 bool = False
    notes:                      Optional[str] = None


class SoftWaterRecordAdapter(BaseImportAdapter):
    """
    Bulk-import soft water operational records.
    Links to UtilityAsset via asset_no.
    """
    module          = "soft_water_records"
    perm_module     = "utility_management"
    schema_class    = _SoftWaterImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "record_datetime": "2025-01-15 08:00",
        "asset_no": "SOFT-001",
        "volume_treated_m3": "45.00",    "raw_water_input_m3": "48.50",
        "feed_water_hardness_ppm": "280", "product_water_hardness_ppm": "12",
        "feed_water_tds_ppm": "450",      "product_water_tds_ppm": "180",
        "salt_consumed_kg": "25.00",      "regeneration_count": "1",
        "efficiency_pct": "96.50",        "downtime_minutes": "0",
        "maintenance_flag": "false",      "destination_tag": "Boiler Feed",
        "department": "Utilities",        "shift_ref": "A",
        "source_method": "MANUAL",        "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no)
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")

        sm = row.get("source_method", "IMPORTED")
        if sm not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from app.models.utility_management import SoftWaterRecord as _SWR, SoftenerStatus
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"SW-{date_str}-{random.randint(10000, 99999)}"
        sm_val = data.get("source_method", "IMPORTED")
        try:
            sm = _SourceMethod(sm_val)
        except ValueError:
            sm = _SourceMethod.IMPORTED
        obj = _SWR(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            volume_treated_m3=data.get("volume_treated_m3"),
            raw_water_input_m3=data.get("raw_water_input_m3"),
            feed_water_hardness_ppm=data.get("feed_water_hardness_ppm"),
            product_water_hardness_ppm=data.get("product_water_hardness_ppm"),
            feed_water_tds_ppm=data.get("feed_water_tds_ppm"),
            product_water_tds_ppm=data.get("product_water_tds_ppm"),
            conductivity_feed_uscm=data.get("conductivity_feed_uscm"),
            conductivity_product_uscm=data.get("conductivity_product_uscm"),
            salt_consumed_kg=data.get("salt_consumed_kg"),
            regeneration_count=data.get("regeneration_count"),
            efficiency_pct=data.get("efficiency_pct"),
            downtime_minutes=data.get("downtime_minutes"),
            maintenance_flag=bool(data.get("maintenance_flag", False)),
            destination_tag=data.get("destination_tag"),
            department=data.get("department"),
            shift_ref=data.get("shift_ref"),
            source_method=sm,
            is_anomaly=bool(data.get("is_anomaly", False)),
            notes=data.get("notes"),
            status=SoftenerStatus.ONLINE,
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Boiler Record adapter ─────────────────────────────────────────────────────

class _BoilerRecordImport(BaseModel):
    """CSV schema for bulk-importing boiler steam operational records."""
    record_datetime:         datetime
    asset_no:                str           # resolved → asset_id
    shift_ref:               Optional[str] = None
    department:              Optional[str] = None
    period_hours:            Optional[Decimal] = None
    steam_pressure_bar:      Optional[Decimal] = None
    steam_temp_c:            Optional[Decimal] = None
    steam_flow_kgh:          Optional[Decimal] = None
    steam_quality_pct:       Optional[Decimal] = None
    steam_generated_kg:      Optional[Decimal] = None
    feedwater_consumed_m3:   Optional[Decimal] = None
    condensate_returned_m3:  Optional[Decimal] = None
    feed_water_temp_c:       Optional[Decimal] = None
    feed_water_flow_lpm:     Optional[Decimal] = None
    feed_water_ph:           Optional[Decimal] = None
    feed_water_tds_ppm:      Optional[Decimal] = None
    blowdown_pct:            Optional[Decimal] = None
    blowdown_volume_litres:  Optional[Decimal] = None
    fuel_type:               Optional[str] = None
    fuel_consumption:        Optional[Decimal] = None
    fuel_unit:               Optional[str] = None
    boiler_efficiency_pct:   Optional[Decimal] = None
    flue_gas_temp_c:         Optional[Decimal] = None
    o2_pct:                  Optional[Decimal] = None
    co2_pct:                 Optional[Decimal] = None
    co_ppm:                  Optional[Decimal] = None
    boiler_tds_ppm:          Optional[Decimal] = None
    boiler_ph:               Optional[Decimal] = None
    boiler_hardness_ppm:     Optional[Decimal] = None
    conductivity_uscm:       Optional[Decimal] = None
    boiler_load_pct:         Optional[Decimal] = None
    burner_runtime_hours:    Optional[Decimal] = None
    start_stop_count:        Optional[int] = None
    running_hours_cumulative: Optional[Decimal] = None
    chemical_dosing_amount:  Optional[Decimal] = None
    chemical_dosing_unit:    Optional[str] = None
    downtime_minutes:        Optional[int] = None
    downtime_reason:         Optional[str] = None
    maintenance_flag:        bool = False
    status:                  str = "RUNNING"
    source_method:           str = "IMPORTED"
    is_anomaly:              bool = False
    anomaly_note:            Optional[str] = None
    notes:                   Optional[str] = None


class BoilerRecordAdapter(BaseImportAdapter):
    """Bulk-import boiler steam operational records. Links asset via asset_no."""
    module          = "boiler_records"
    perm_module     = "utility_management"
    schema_class    = _BoilerRecordImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "record_datetime": "2025-01-15 06:00",
        "asset_no": "BLR-001",
        "shift_ref": "A",                    "department": "Utilities",
        "period_hours": "8.00",              "steam_generated_kg": "24000",
        "feedwater_consumed_m3": "25.50",    "condensate_returned_m3": "18.00",
        "fuel_type": "NATURAL_GAS",          "fuel_consumption": "1800",
        "fuel_unit": "m3",                   "boiler_efficiency_pct": "85.50",
        "boiler_load_pct": "78.00",          "burner_runtime_hours": "7.50",
        "steam_pressure_bar": "8.5",         "steam_temp_c": "175",
        "blowdown_volume_litres": "120",     "downtime_minutes": "30",
        "maintenance_flag": "false",         "status": "RUNNING",
        "source_method": "MANUAL",           "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no)
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")

        if row.get("status") not in {e.value for e in _BoilerStatus}:
            row["status"] = "RUNNING"
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"BLR-{date_str}-{random.randint(10000, 99999)}"
        try:
            status = _BoilerStatus(data.get("status", "RUNNING"))
        except ValueError:
            status = _BoilerStatus.RUNNING
        try:
            source_method = _SourceMethod(data.get("source_method", "IMPORTED"))
        except ValueError:
            source_method = _SourceMethod.IMPORTED
        obj = _BoilerSteamRecord(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            shift_ref=data.get("shift_ref"),
            department=data.get("department"),
            period_hours=data.get("period_hours"),
            steam_pressure_bar=data.get("steam_pressure_bar"),
            steam_temp_c=data.get("steam_temp_c"),
            steam_flow_kgh=data.get("steam_flow_kgh"),
            steam_quality_pct=data.get("steam_quality_pct"),
            steam_generated_kg=data.get("steam_generated_kg"),
            feedwater_consumed_m3=data.get("feedwater_consumed_m3"),
            condensate_returned_m3=data.get("condensate_returned_m3"),
            feed_water_temp_c=data.get("feed_water_temp_c"),
            feed_water_flow_lpm=data.get("feed_water_flow_lpm"),
            feed_water_ph=data.get("feed_water_ph"),
            feed_water_tds_ppm=data.get("feed_water_tds_ppm"),
            blowdown_pct=data.get("blowdown_pct"),
            blowdown_volume_litres=data.get("blowdown_volume_litres"),
            fuel_type=data.get("fuel_type"),
            fuel_consumption=data.get("fuel_consumption"),
            fuel_unit=data.get("fuel_unit"),
            boiler_efficiency_pct=data.get("boiler_efficiency_pct"),
            flue_gas_temp_c=data.get("flue_gas_temp_c"),
            o2_pct=data.get("o2_pct"),
            co2_pct=data.get("co2_pct"),
            co_ppm=data.get("co_ppm"),
            boiler_tds_ppm=data.get("boiler_tds_ppm"),
            boiler_ph=data.get("boiler_ph"),
            boiler_hardness_ppm=data.get("boiler_hardness_ppm"),
            conductivity_uscm=data.get("conductivity_uscm"),
            boiler_load_pct=data.get("boiler_load_pct"),
            burner_runtime_hours=data.get("burner_runtime_hours"),
            start_stop_count=data.get("start_stop_count"),
            running_hours_cumulative=data.get("running_hours_cumulative"),
            chemical_dosing_amount=data.get("chemical_dosing_amount"),
            chemical_dosing_unit=data.get("chemical_dosing_unit"),
            downtime_minutes=data.get("downtime_minutes"),
            downtime_reason=data.get("downtime_reason"),
            maintenance_flag=bool(data.get("maintenance_flag", False)),
            status=status,
            source_method=source_method,
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Steam Transaction adapter ─────────────────────────────────────────────────

class _SteamTxImport(BaseModel):
    """CSV schema for bulk-importing STEAM utility transactions."""
    transaction_date:  date
    quantity:          Decimal
    uom:               str = "KG"
    unit_cost:         Optional[Decimal] = None
    total_cost:        Optional[Decimal] = None
    currency_code:     str = "USD"
    department:        Optional[str] = None
    building_area:     Optional[str] = None
    production_line:   Optional[str] = None
    machine_ref:       Optional[str] = None
    shift_ref:         Optional[str] = None
    batch_no:          Optional[str] = None
    source_method:     str = "IMPORTED"
    quality:           str = "GOOD"
    is_estimated:      bool = False
    is_anomaly:        bool = False
    anomaly_note:      Optional[str] = None
    notes:             Optional[str] = None


class SteamTransactionAdapter(BaseImportAdapter):
    """Bulk-import STEAM utility transactions (cost allocation records)."""
    module          = "steam_transactions"
    perm_module     = "utility_management"
    schema_class    = _SteamTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "quantity": "24000",            "uom": "KG",
        "unit_cost": "0.045",           "total_cost": "1080.00",
        "currency_code": "USD",         "department": "Production",
        "production_line": "LINE-01",   "machine_ref": "",
        "shift_ref": "A",              "batch_no": "",
        "source_method": "MANUAL",     "quality": "GOOD",
        "is_estimated": "false",        "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        errors: list[str] = []
        sm = row.get("source_method", "IMPORTED")
        if sm not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        q = row.get("quality", "GOOD")
        if q not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        td = data.get("transaction_date")
        date_str = td.strftime("%Y%m%d") if hasattr(td, "strftime") else str(td).replace("-", "")
        tx_no = f"STX-{date_str}-{random.randint(10000, 99999)}"
        qty = data.get("quantity") or Decimal("0")
        unit_cost = data.get("unit_cost")
        total_cost = data.get("total_cost") or (qty * unit_cost if unit_cost else None)
        try:
            sm = _SourceMethod(data.get("source_method", "IMPORTED"))
        except ValueError:
            sm = _SourceMethod.IMPORTED
        try:
            dq = _DataQuality(data.get("quality", "GOOD"))
        except ValueError:
            dq = _DataQuality.GOOD
        obj = _UtilityTransaction(
            tx_no=tx_no,
            utility_type=_UtilityType.STEAM,
            transaction_date=data.get("transaction_date"),
            quantity=qty,
            uom=data.get("uom", "KG"),
            unit_cost=unit_cost,
            total_cost=total_cost,
            currency_code=data.get("currency_code", "USD"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            source_method=sm,
            quality=dq,
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Compressor Record adapter ─────────────────────────────────────────────────

class _CompressorRecordImport(BaseModel):
    """CSV schema for bulk-importing compressor operational records."""
    record_datetime:           datetime
    asset_no:                  str              # resolved → asset_id
    shift_ref:                 Optional[str]    = None
    department:                Optional[str]    = None
    production_line:           Optional[str]    = None
    period_hours:              Optional[Decimal] = None
    air_generated_nm3:         Optional[Decimal] = None
    air_unit:                  str              = "Nm3"
    electricity_used_kwh:      Optional[Decimal] = None
    runtime_hours:             Optional[Decimal] = None
    load_time_hours:           Optional[Decimal] = None
    unload_time_hours:         Optional[Decimal] = None
    idle_time_hours:           Optional[Decimal] = None
    discharge_pressure_bar:    Optional[Decimal] = None
    system_pressure_bar:       Optional[Decimal] = None
    receiver_tank_pressure_bar: Optional[Decimal] = None
    line_pressure_bar:         Optional[Decimal] = None
    filter_dp_bar:             Optional[Decimal] = None
    dryer_status:              Optional[str]    = None
    dryer_dew_point_c:         Optional[Decimal] = None
    specific_energy_kwh_m3:    Optional[Decimal] = None
    leak_test_done:            bool             = False
    leak_estimation_pct:       Optional[Decimal] = None
    leak_volume_nm3:           Optional[Decimal] = None
    night_idle_kwh:            Optional[Decimal] = None
    night_idle_nm3:            Optional[Decimal] = None
    start_stop_count:          Optional[int]    = None
    downtime_minutes:          Optional[int]    = None
    downtime_reason:           Optional[str]    = None
    maintenance_flag:          bool             = False
    status:                    str              = "RUNNING"
    source_method:             str              = "IMPORTED"
    is_anomaly:                bool             = False
    anomaly_note:              Optional[str]    = None
    notes:                     Optional[str]    = None


class CompressorRecordAdapter(BaseImportAdapter):
    """Bulk-import compressor operational records. Links asset via asset_no."""
    module          = "compressor_records"
    perm_module     = "utility_management"
    schema_class    = _CompressorRecordImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "record_datetime": "2025-01-15 06:00",
        "asset_no": "CPR-001",
        "shift_ref": "A",               "department": "Utilities",
        "period_hours": "8.00",         "air_generated_nm3": "9600",
        "air_unit": "Nm3",              "electricity_used_kwh": "960",
        "runtime_hours": "8.00",        "load_time_hours": "6.50",
        "unload_time_hours": "0.80",    "idle_time_hours": "0.70",
        "discharge_pressure_bar": "7.5","line_pressure_bar": "7.2",
        "dryer_status": "ON",           "dryer_dew_point_c": "-20",
        "filter_dp_bar": "0.05",        "leak_test_done": "false",
        "leak_estimation_pct": "",      "night_idle_kwh": "",
        "maintenance_flag": "false",    "status": "RUNNING",
        "source_method": "MANUAL",      "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no)
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")
        if row.get("status") not in {e.value for e in _CompressorStatus}:
            row["status"] = "RUNNING"
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"CPR-{date_str}-{random.randint(10000, 99999)}"
        try:
            status = _CompressorStatus(data.get("status", "RUNNING"))
        except ValueError:
            status = _CompressorStatus.RUNNING
        try:
            sm = _SourceMethod(data.get("source_method", "IMPORTED"))
        except ValueError:
            sm = _SourceMethod.IMPORTED
        obj = _CompressorRecord(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            shift_ref=data.get("shift_ref"),
            department=data.get("department"),
            production_line=data.get("production_line"),
            period_hours=data.get("period_hours"),
            air_generated_nm3=data.get("air_generated_nm3"),
            air_unit=data.get("air_unit", "Nm3"),
            electricity_used_kwh=data.get("electricity_used_kwh"),
            runtime_hours=data.get("runtime_hours"),
            load_time_hours=data.get("load_time_hours"),
            unload_time_hours=data.get("unload_time_hours"),
            idle_time_hours=data.get("idle_time_hours"),
            discharge_pressure_bar=data.get("discharge_pressure_bar"),
            system_pressure_bar=data.get("system_pressure_bar"),
            receiver_tank_pressure_bar=data.get("receiver_tank_pressure_bar"),
            line_pressure_bar=data.get("line_pressure_bar"),
            filter_dp_bar=data.get("filter_dp_bar"),
            dryer_status=data.get("dryer_status"),
            dryer_dew_point_c=data.get("dryer_dew_point_c"),
            specific_energy_kwh_m3=data.get("specific_energy_kwh_m3"),
            leak_test_done=bool(data.get("leak_test_done", False)),
            leak_estimation_pct=data.get("leak_estimation_pct"),
            leak_volume_nm3=data.get("leak_volume_nm3"),
            night_idle_kwh=data.get("night_idle_kwh"),
            night_idle_nm3=data.get("night_idle_nm3"),
            start_stop_count=data.get("start_stop_count"),
            downtime_minutes=data.get("downtime_minutes"),
            downtime_reason=data.get("downtime_reason"),
            maintenance_flag=bool(data.get("maintenance_flag", False)),
            status=status,
            source_method=sm,
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Air Transaction adapter ───────────────────────────────────────────────────

class _AirTxImport(BaseModel):
    """CSV schema for bulk-importing COMPRESSED_AIR utility transactions."""
    transaction_date:  date
    quantity:          Decimal
    uom:               str              = "Nm3"
    unit_cost:         Optional[Decimal] = None
    total_cost:        Optional[Decimal] = None
    currency_code:     str              = "USD"
    department:        Optional[str]    = None
    building_area:     Optional[str]    = None
    production_line:   Optional[str]    = None
    machine_ref:       Optional[str]    = None
    shift_ref:         Optional[str]    = None
    batch_no:          Optional[str]    = None
    source_method:     str              = "IMPORTED"
    quality:           str              = "GOOD"
    is_estimated:      bool             = False
    is_anomaly:        bool             = False
    anomaly_note:      Optional[str]    = None
    notes:             Optional[str]    = None


class AirTransactionAdapter(BaseImportAdapter):
    """Bulk-import COMPRESSED_AIR utility transactions."""
    module          = "air_transactions"
    perm_module     = "utility_management"
    schema_class    = _AirTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "quantity": "9600",         "uom": "Nm3",
        "unit_cost": "0.012",       "total_cost": "115.20",
        "currency_code": "USD",     "department": "Production",
        "production_line": "LINE-01","machine_ref": "",
        "shift_ref": "A",           "batch_no": "",
        "source_method": "MANUAL",  "quality": "GOOD",
        "is_estimated": "false",    "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(
        self, row: dict, db: AsyncSession
    ) -> tuple[dict, list[str]]:
        errors: list[str] = []
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        if row.get("quality") not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        td = data.get("transaction_date")
        date_str = td.strftime("%Y%m%d") if hasattr(td, "strftime") else str(td).replace("-", "")
        tx_no = f"ATX-{date_str}-{random.randint(10000, 99999)}"
        qty = data.get("quantity") or Decimal("0")
        unit_cost = data.get("unit_cost")
        total_cost = data.get("total_cost") or (qty * unit_cost if unit_cost else None)
        try:
            sm = _SourceMethod(data.get("source_method", "IMPORTED"))
        except ValueError:
            sm = _SourceMethod.IMPORTED
        try:
            dq = _DataQuality(data.get("quality", "GOOD"))
        except ValueError:
            dq = _DataQuality.GOOD
        obj = _UtilityTransaction(
            tx_no=tx_no,
            utility_type=_UtilityType.COMPRESSED_AIR,
            transaction_date=data.get("transaction_date"),
            quantity=qty,
            uom=data.get("uom", "Nm3"),
            unit_cost=unit_cost,
            total_cost=total_cost,
            currency_code=data.get("currency_code", "USD"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            source_method=sm,
            quality=dq,
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Reading adapter ───────────────────────────────────────────────────

class _UtilityReadingImport(BaseModel):
    """CSV schema for bulk-importing raw meter / sensor readings."""
    device_code:      str                  # resolved → device_id
    reading_datetime: datetime
    raw_value:        Decimal
    unit_of_measure:  Optional[str] = None
    cumulative_value: Optional[Decimal] = None
    asset_no:         Optional[str] = None   # resolved → asset_id (optional)
    source_method:    str = "IMPORTED"
    source_reference: Optional[str] = None
    department:       Optional[str] = None
    building_area:    Optional[str] = None
    shift_ref:        Optional[str] = None
    batch_id:         Optional[str] = None
    notes:            Optional[str] = None


class UtilityReadingAdapter(BaseImportAdapter):
    """Bulk-import raw meter readings. Resolves device_code → device_id."""
    module          = "utility_readings"
    perm_module     = "utility_management"
    schema_class    = _UtilityReadingImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "device_code": "MTR-ELEC-001",
        "reading_datetime": "2025-01-15 08:00",
        "raw_value": "45230.50",
        "unit_of_measure": "kWh",
        "cumulative_value": "45230.50",
        "asset_no": "ELEC-PANEL-01",
        "source_method": "MANUAL",
        "department": "Production",
        "shift_ref": "A",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        device_code = row.pop("device_code", None)
        if device_code:
            r = await db.execute(
                select(_UtilityDevice).where(_UtilityDevice.device_code == device_code.upper())
            )
            dev = r.scalar_one_or_none()
            if dev is None:
                errors.append(f"device_code '{device_code}' not found in utility_devices")
            else:
                row["device_id"] = dev.id
                if not row.get("unit_of_measure"):
                    row["unit_of_measure"] = dev.unit_of_measure
        else:
            errors.append("device_code is required")

        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id

        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        dt = data.get("reading_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"RDG-{date_str}-{random.randint(10000, 99999)}"
        try:
            sm = _SourceMethod(data.get("source_method", "IMPORTED"))
        except ValueError:
            sm = _SourceMethod.IMPORTED
        obj = _UtilityReading(
            reading_no=rec_no,
            device_id=data.get("device_id"),
            asset_id=data.get("asset_id"),
            reading_datetime=data.get("reading_datetime"),
            raw_value=data.get("raw_value"),
            unit_of_measure=data.get("unit_of_measure", "units"),
            cumulative_value=data.get("cumulative_value"),
            source_method=sm,
            source_reference=data.get("source_reference"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            shift_ref=data.get("shift_ref"),
            batch_id=data.get("batch_id"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Electricity Consumption adapter (alias for electricity_transactions) ───────

class ElectricityConsumptionAdapter(BaseImportAdapter):
    """
    Bulk-import electricity consumption records (alias module name for CSV export).
    Each row creates one utility_transaction with utility_type=ELECTRICITY.
    """
    module          = "electricity_consumption"
    perm_module     = "utility_management"
    schema_class    = _ElectricityTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "quantity": "1200.50",         "uom": "kWh",
        "department": "Production",    "building_area": "Block A",
        "production_line": "LINE-01",  "machine_ref": "MCH-001",
        "shift_ref": "A",              "batch_no": "BATCH-2025-001",
        "cost_rate": "0.12",           "total_cost": "",
        "currency_code": "USD",        "source_method": "MANUAL",
        "quality": "GOOD",             "is_estimated": "false",
        "is_anomaly": "false",         "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []
        qty  = row.get("quantity")
        rate = row.get("cost_rate")
        cost = row.get("total_cost")
        if qty and rate and not cost:
            row["total_cost"] = _D(str(qty)) * _D(str(rate))
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        if row.get("quality") not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        d = data.get("transaction_date")
        date_str = d.strftime("%Y%m%d") if isinstance(d, _date) else str(d)[:8].replace("-", "")
        tx_no = f"TX-{date_str}-{random.randint(10000, 99999)}"
        obj = _UtilityTransaction(
            transaction_no=tx_no,
            utility_type=_UtilityType.ELECTRICITY,
            transaction_date=data.get("transaction_date"),
            quantity=data.get("quantity"),
            unit_of_measure=data.get("uom", "kWh"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            cost_rate=data.get("cost_rate"),
            total_cost=data.get("total_cost"),
            currency_code=data.get("currency_code", "USD"),
            variance_from_standard=data.get("variance_from_standard"),
            source_method=data.get("source_method", "IMPORTED"),
            quality=data.get("quality", "GOOD"),
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Water Consumption adapter (alias for water_transactions) ──────────────────

class WaterConsumptionAdapter(BaseImportAdapter):
    """
    Bulk-import water consumption records (alias module name for CSV export).
    Supports WATER, PROCESS_WATER, and WASTEWATER utility types.
    """
    module          = "water_consumption"
    perm_module     = "utility_management"
    schema_class    = _WaterTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "transaction_date": "2025-01-15",
        "utility_type": "WATER",       "quantity": "120.50",
        "uom": "m3",                   "department": "Production",
        "building_area": "Block A",    "shift_ref": "A",
        "cost_rate": "0.80",           "total_cost": "",
        "currency_code": "USD",        "source_method": "MANUAL",
        "quality": "GOOD",             "is_estimated": "false",
        "is_anomaly": "false",         "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []
        valid_types = {"WATER", "PROCESS_WATER", "WASTEWATER"}
        ut = (row.get("utility_type") or "WATER").upper()
        if ut not in valid_types:
            errors.append(f"utility_type must be one of {sorted(valid_types)}")
        else:
            row["utility_type"] = ut
        qty  = row.get("quantity")
        rate = row.get("cost_rate")
        cost = row.get("total_cost")
        if qty and rate and not cost:
            row["total_cost"] = _D(str(qty)) * _D(str(rate))
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        if row.get("quality") not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        d = data.get("transaction_date")
        date_str = d.strftime("%Y%m%d") if isinstance(d, _date) else str(d)[:8].replace("-", "")
        tx_no = f"WTX-{date_str}-{random.randint(10000, 99999)}"
        ut_str = (data.get("utility_type") or "WATER").upper()
        try:
            ut = _UtilityType(ut_str)
        except ValueError:
            ut = _UtilityType.WATER
        obj = _UtilityTransaction(
            transaction_no=tx_no,
            utility_type=ut,
            transaction_date=data.get("transaction_date"),
            quantity=data.get("quantity"),
            unit_of_measure=data.get("uom", "m3"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            cost_rate=data.get("cost_rate"),
            total_cost=data.get("total_cost"),
            currency_code=data.get("currency_code", "USD"),
            source_method=data.get("source_method", "IMPORTED"),
            quality=data.get("quality", "GOOD"),
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Generic Utility Transaction adapter ───────────────────────────────────────

class _GenericUtilityTxImport(BaseModel):
    """CSV schema for importing any utility type into the unified transactions table."""
    utility_type:     str               # any UtilityType value
    transaction_date: date
    quantity:         Decimal
    uom:              str
    device_code:      Optional[str] = None   # resolved → device_id
    asset_no:         Optional[str] = None   # resolved → asset_id
    tariff_code:      Optional[str] = None   # resolved → tariff_id
    department:       Optional[str] = None
    building_area:    Optional[str] = None
    production_line:  Optional[str] = None
    machine_ref:      Optional[str] = None
    shift_ref:        Optional[str] = None
    batch_no:         Optional[str] = None
    cost_rate:        Optional[Decimal] = None
    total_cost:       Optional[Decimal] = None
    currency_code:    str = "USD"
    variance_from_standard: Optional[Decimal] = None
    reference_type:   Optional[str] = None
    reference_id:     Optional[str] = None
    source_method:    str = "IMPORTED"
    quality:          str = "GOOD"
    is_estimated:     bool = False
    is_anomaly:       bool = False
    anomaly_note:     Optional[str] = None
    notes:            Optional[str] = None


class UtilityTransactionImportAdapter(BaseImportAdapter):
    """
    Generic bulk-import for any utility type into utility_transactions.
    Resolves optional device_code, asset_no, and tariff_code references.
    Auto-computes total_cost when quantity × cost_rate present but total_cost is blank.
    """
    module          = "utility_transactions"
    perm_module     = "utility_management"
    schema_class    = _GenericUtilityTxImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "utility_type": "ELECTRICITY",
        "transaction_date": "2025-01-15",
        "quantity": "1200.50",         "uom": "kWh",
        "device_code": "MTR-ELEC-001", "asset_no": "ELEC-PANEL-01",
        "tariff_code": "ELEC-FLAT-01", "department": "Production",
        "building_area": "Block A",    "production_line": "LINE-01",
        "shift_ref": "A",              "batch_no": "",
        "cost_rate": "0.12",           "total_cost": "",
        "currency_code": "USD",        "source_method": "MANUAL",
        "quality": "GOOD",             "is_estimated": "false",
        "is_anomaly": "false",         "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []

        ut_str = (row.get("utility_type") or "").upper()
        valid_ut = {e.value for e in _UtilityType}
        if ut_str not in valid_ut:
            errors.append(f"utility_type '{ut_str}' is invalid; valid: {sorted(valid_ut)}")
        else:
            row["utility_type"] = ut_str

        device_code = row.pop("device_code", None)
        if device_code:
            r = await db.execute(
                select(_UtilityDevice).where(_UtilityDevice.device_code == device_code.upper())
            )
            dev = r.scalar_one_or_none()
            if dev is None:
                errors.append(f"device_code '{device_code}' not found")
            else:
                row["device_id"] = dev.id

        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found")
            else:
                row["asset_id"] = asset.id

        tariff_code = row.pop("tariff_code", None)
        if tariff_code:
            r = await db.execute(
                select(_UtilityTariff).where(_UtilityTariff.tariff_code == tariff_code.upper())
            )
            tariff = r.scalar_one_or_none()
            if tariff is None:
                errors.append(f"tariff_code '{tariff_code}' not found — import tariffs first")
            else:
                row["tariff_id"] = tariff.id

        qty  = row.get("quantity")
        rate = row.get("cost_rate")
        cost = row.get("total_cost")
        if qty and rate and not cost:
            row["total_cost"] = _D(str(qty)) * _D(str(rate))

        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IMPORTED"
        if row.get("quality") not in {e.value for e in _DataQuality}:
            row["quality"] = "GOOD"

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        d = data.get("transaction_date")
        date_str = d.strftime("%Y%m%d") if isinstance(d, _date) else str(d)[:8].replace("-", "")
        tx_no = f"UTX-{date_str}-{random.randint(10000, 99999)}"
        try:
            ut = _UtilityType(data.get("utility_type", "ELECTRICITY"))
        except ValueError:
            ut = _UtilityType.ELECTRICITY
        obj = _UtilityTransaction(
            transaction_no=tx_no,
            utility_type=ut,
            transaction_date=data.get("transaction_date"),
            quantity=data.get("quantity"),
            unit_of_measure=data.get("uom"),
            device_id=data.get("device_id"),
            asset_id=data.get("asset_id"),
            tariff_id=data.get("tariff_id"),
            department=data.get("department"),
            building_area=data.get("building_area"),
            production_line=data.get("production_line"),
            machine_ref=data.get("machine_ref"),
            shift_ref=data.get("shift_ref"),
            batch_no=data.get("batch_no"),
            cost_rate=data.get("cost_rate"),
            total_cost=data.get("total_cost"),
            currency_code=data.get("currency_code", "USD"),
            variance_from_standard=data.get("variance_from_standard"),
            reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
            source_method=data.get("source_method", "IMPORTED"),
            quality=data.get("quality", "GOOD"),
            is_estimated=bool(data.get("is_estimated", False)),
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Solar Record adapter ───────────────────────────────────────────────────────

class _SolarRecordImport(BaseModel):
    """CSV schema for bulk-importing solar PV operational records."""
    asset_no:        str           # resolved → asset_id
    record_datetime: datetime
    irradiance_wm2:  Optional[Decimal] = None
    panel_temp_c:    Optional[Decimal] = None
    ambient_temp_c:  Optional[Decimal] = None
    dc_voltage_v:    Optional[Decimal] = None
    dc_current_a:    Optional[Decimal] = None
    dc_power_kw:     Optional[Decimal] = None
    ac_power_kw:     Optional[Decimal] = None
    energy_generated_kwh:    Optional[Decimal] = None
    grid_export_kwh:         Optional[Decimal] = None
    self_consumption_kwh:    Optional[Decimal] = None
    inverter_efficiency_pct: Optional[Decimal] = None
    pr_ratio:                Optional[Decimal] = None
    availability_pct:        Optional[Decimal] = None
    capacity_factor_pct:     Optional[Decimal] = None
    source_method:   str = "IOT"
    is_anomaly:      bool = False
    anomaly_note:    Optional[str] = None
    notes:           Optional[str] = None


class SolarRecordImportAdapter(BaseImportAdapter):
    """Bulk-import solar PV operational records. Links asset via asset_no."""
    module          = "solar_records"
    perm_module     = "utility_management"
    schema_class    = _SolarRecordImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "asset_no": "SOLAR-PV-01",
        "record_datetime": "2025-01-15 12:00",
        "irradiance_wm2": "850.00",           "panel_temp_c": "42.5",
        "ambient_temp_c": "28.0",             "dc_power_kw": "98.50",
        "ac_power_kw": "95.20",               "energy_generated_kwh": "762.00",
        "grid_export_kwh": "250.00",          "self_consumption_kwh": "512.00",
        "inverter_efficiency_pct": "96.70",   "pr_ratio": "0.8200",
        "availability_pct": "99.50",          "capacity_factor_pct": "23.50",
        "source_method": "IOT",               "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")
        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "IOT"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"SLR-{date_str}-{random.randint(10000, 99999)}"
        try:
            sm = _SourceMethod(data.get("source_method", "IOT"))
        except ValueError:
            sm = _SourceMethod.IOT
        obj = _SolarRecord(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            irradiance_wm2=data.get("irradiance_wm2"),
            panel_temp_c=data.get("panel_temp_c"),
            ambient_temp_c=data.get("ambient_temp_c"),
            dc_voltage_v=data.get("dc_voltage_v"),
            dc_current_a=data.get("dc_current_a"),
            dc_power_kw=data.get("dc_power_kw"),
            ac_power_kw=data.get("ac_power_kw"),
            energy_generated_kwh=data.get("energy_generated_kwh"),
            grid_export_kwh=data.get("grid_export_kwh"),
            self_consumption_kwh=data.get("self_consumption_kwh"),
            inverter_efficiency_pct=data.get("inverter_efficiency_pct"),
            pr_ratio=data.get("pr_ratio"),
            availability_pct=data.get("availability_pct"),
            capacity_factor_pct=data.get("capacity_factor_pct"),
            source_method=sm,
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Treatment Chemical Record adapter ─────────────────────────────────────────

class _TreatmentChemicalImport(BaseModel):
    """CSV schema for bulk-importing chemical water treatment dosing records."""
    asset_no:          str           # resolved → asset_id
    record_datetime:   datetime
    treatment_type:    str           # TreatmentType enum
    chemical_name:     str
    quantity_dosed:    Decimal
    unit:              str
    chemical_code:     Optional[str] = None   # resolved → chemical_id (optional)
    chemical_category: Optional[str] = None
    treatment_area:    Optional[str] = None
    dosing_point:      Optional[str] = None
    supplier_code:     Optional[str] = None   # resolved → supplier_id (optional)
    batch_lot_no:      Optional[str] = None
    unit_cost:         Optional[Decimal] = None
    stock_uom:         Optional[str] = None
    dosing_uom:        Optional[str] = None
    opening_stock:     Optional[Decimal] = None
    received_qty:      Optional[Decimal] = None
    consumed_qty:      Optional[Decimal] = None
    closing_stock:     Optional[Decimal] = None
    target_dose_ppm:   Optional[Decimal] = None
    actual_dose_ppm:   Optional[Decimal] = None
    water_volume_m3:   Optional[Decimal] = None
    manual_or_auto_dose: Optional[str] = "MANUAL"
    water_treated_m3:    Optional[Decimal] = None
    steam_produced_ton:  Optional[Decimal] = None
    feed_ph:               Optional[Decimal] = None
    product_ph:            Optional[Decimal] = None
    feed_turbidity_ntu:    Optional[Decimal] = None
    product_turbidity_ntu: Optional[Decimal] = None
    residual_chlorine_ppm: Optional[Decimal] = None
    tds_feed_ppm:          Optional[Decimal] = None
    tds_product_ppm:       Optional[Decimal] = None
    source_method:   str = "MANUAL"
    is_anomaly:      bool = False
    anomaly_note:    Optional[str] = None
    overdose_flag:   bool = False
    underdose_flag:  bool = False
    shift_ref:       Optional[str] = None
    notes:           Optional[str] = None


class TreatmentChemicalRecordAdapter(BaseImportAdapter):
    """Bulk-import chemical water treatment dosing records."""
    module          = "treatment_chemical_records"
    perm_module     = "utility_management"
    schema_class    = _TreatmentChemicalImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "asset_no": "BLR-001",
        "record_datetime": "2025-01-15 08:00",
        "treatment_type": "SOFTENING",
        "chemical_name": "Sodium Chloride",
        "chemical_code": "NACL-001",
        "quantity_dosed": "25.00",
        "unit": "kg",
        "chemical_category": "ANTISCALANT",
        "treatment_area": "Boiler Feed",
        "dosing_point": "Pump Skid A",
        "unit_cost": "0.85",
        "target_dose_ppm": "50.00",
        "actual_dose_ppm": "48.50",
        "water_volume_m3": "50.00",
        "manual_or_auto_dose": "MANUAL",
        "source_method": "MANUAL",
        "is_anomaly": "false",
        "shift_ref": "A",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []

        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")

        chemical_code = row.pop("chemical_code", None)
        if chemical_code:
            r = await db.execute(
                select(_WaterTreatmentChemical).where(
                    _WaterTreatmentChemical.chemical_code == chemical_code.upper()
                )
            )
            chem = r.scalar_one_or_none()
            if chem:
                row["chemical_id"] = chem.id
            else:
                row["chemical_code"] = chemical_code

        supplier_code = row.pop("supplier_code", None)
        if supplier_code:
            r = await db.execute(
                select(Supplier).where(Supplier.code == supplier_code.upper())
            )
            sup = r.scalar_one_or_none()
            if sup is None:
                errors.append(f"supplier_code '{supplier_code}' not found")
            else:
                row["supplier_id"] = sup.id

        tt = (row.get("treatment_type") or "").upper()
        if tt not in {e.value for e in _TreatmentType}:
            errors.append(
                f"treatment_type '{tt}' is invalid; valid: "
                f"{sorted(e.value for e in _TreatmentType)}"
            )
        else:
            row["treatment_type"] = tt

        dm = (row.get("manual_or_auto_dose") or "MANUAL").upper()
        if dm not in {e.value for e in _DosingMode}:
            row["manual_or_auto_dose"] = "MANUAL"
        else:
            row["manual_or_auto_dose"] = dm

        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "MANUAL"

        tgt = row.get("target_dose_ppm")
        act = row.get("actual_dose_ppm")
        if tgt and act:
            tgt_f, act_f = float(tgt), float(act)
            if act_f > tgt_f * 1.20:
                row["overdose_flag"] = True
            elif act_f < tgt_f * 0.80:
                row["underdose_flag"] = True

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        from datetime import date as _date
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"TCR-{date_str}-{random.randint(10000, 99999)}"
        rec_date = dt.date() if hasattr(dt, "date") else None
        try:
            sm = _SourceMethod(data.get("source_method", "MANUAL"))
        except ValueError:
            sm = _SourceMethod.MANUAL
        try:
            tt = _TreatmentType(data.get("treatment_type", "OTHER"))
        except ValueError:
            tt = _TreatmentType.OTHER
        try:
            dm = _DosingMode(data.get("manual_or_auto_dose", "MANUAL"))
        except ValueError:
            dm = _DosingMode.MANUAL
        obj = _TreatmentChemicalRecord(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            date=rec_date,
            treatment_type=tt,
            chemical_id=data.get("chemical_id"),
            chemical_code=data.get("chemical_code"),
            chemical_name=data.get("chemical_name"),
            chemical_category=data.get("chemical_category"),
            treatment_area=data.get("treatment_area"),
            dosing_point=data.get("dosing_point"),
            supplier_id=data.get("supplier_id"),
            batch_lot_no=data.get("batch_lot_no"),
            unit_cost=data.get("unit_cost"),
            stock_uom=data.get("stock_uom"),
            dosing_uom=data.get("dosing_uom"),
            opening_stock=data.get("opening_stock"),
            received_qty=data.get("received_qty", Decimal("0")),
            consumed_qty=data.get("consumed_qty", Decimal("0")),
            closing_stock=data.get("closing_stock"),
            quantity_dosed=data.get("quantity_dosed"),
            unit=data.get("unit"),
            target_dose_ppm=data.get("target_dose_ppm"),
            actual_dose_ppm=data.get("actual_dose_ppm"),
            water_volume_m3=data.get("water_volume_m3"),
            manual_or_auto_dose=dm,
            water_treated_m3=data.get("water_treated_m3"),
            steam_produced_ton=data.get("steam_produced_ton"),
            feed_ph=data.get("feed_ph"),
            product_ph=data.get("product_ph"),
            feed_turbidity_ntu=data.get("feed_turbidity_ntu"),
            product_turbidity_ntu=data.get("product_turbidity_ntu"),
            residual_chlorine_ppm=data.get("residual_chlorine_ppm"),
            tds_feed_ppm=data.get("tds_feed_ppm"),
            tds_product_ppm=data.get("tds_product_ppm"),
            source_method=sm,
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            overdose_flag=bool(data.get("overdose_flag", False)),
            underdose_flag=bool(data.get("underdose_flag", False)),
            shift_ref=data.get("shift_ref"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Wastewater Record adapter ─────────────────────────────────────────────────

class _WastewaterRecordImport(BaseModel):
    """CSV schema for bulk-importing wastewater treatment operational records."""
    asset_no:          str           # resolved → asset_id
    record_datetime:   datetime
    process_stage:     str = "SECONDARY"   # PRIMARY/SECONDARY/TERTIARY/SLUDGE_HANDLING
    shift_ref:         Optional[str] = None
    influent_flow_m3h: Optional[Decimal] = None
    effluent_flow_m3h: Optional[Decimal] = None
    influent_cod_mgl:  Optional[Decimal] = None
    effluent_cod_mgl:  Optional[Decimal] = None
    influent_bod_mgl:  Optional[Decimal] = None
    effluent_bod_mgl:  Optional[Decimal] = None
    influent_tss_mgl:  Optional[Decimal] = None
    effluent_tss_mgl:  Optional[Decimal] = None
    influent_ph:       Optional[Decimal] = None
    effluent_ph:       Optional[Decimal] = None
    do_mgl:            Optional[Decimal] = None
    mlss_mgl:          Optional[Decimal] = None
    mlvss_mgl:         Optional[Decimal] = None
    svi:               Optional[Decimal] = None
    srt_days:          Optional[Decimal] = None
    conductivity_us_cm:     Optional[Decimal] = None
    temperature_c:          Optional[Decimal] = None
    power_consumed_kwh:     Optional[Decimal] = None
    aeration_runtime_hours: Optional[Decimal] = None
    blower_power_kw:        Optional[Decimal] = None
    nutrient_dose_kg:       Optional[Decimal] = None
    antifoam_dose_kg:       Optional[Decimal] = None
    sludge_produced_kg:     Optional[Decimal] = None
    sludge_dewatered_pct:   Optional[Decimal] = None
    sludge_volume_m3:       Optional[Decimal] = None
    sludge_disposal_qty_kg: Optional[Decimal] = None
    compliance_status:  str = "COMPLIANT"
    permit_limit_ref:   Optional[str] = None
    deviation_reason:   Optional[str] = None
    corrective_action:  Optional[str] = None
    source_method:      str = "MANUAL"
    is_anomaly:         bool = False
    anomaly_note:       Optional[str] = None
    notes:              Optional[str] = None


class WastewaterRecordAdapter(BaseImportAdapter):
    """Bulk-import wastewater treatment operational records. Links asset via asset_no."""
    module          = "wastewater_records"
    perm_module     = "utility_management"
    schema_class    = _WastewaterRecordImport
    unique_key: list = []
    field_overrides: dict = {}
    example_row     = {
        "asset_no": "WWTP-001",
        "record_datetime": "2025-01-15 08:00",
        "process_stage": "SECONDARY",
        "shift_ref": "A",
        "influent_flow_m3h": "120.00",   "effluent_flow_m3h": "115.00",
        "influent_cod_mgl": "850.00",    "effluent_cod_mgl": "42.00",
        "influent_bod_mgl": "380.00",    "effluent_bod_mgl": "12.00",
        "influent_tss_mgl": "450.00",    "effluent_tss_mgl": "18.00",
        "influent_ph": "7.20",           "effluent_ph": "7.50",
        "do_mgl": "2.50",                "mlss_mgl": "3200.00",
        "power_consumed_kwh": "185.00",  "aeration_runtime_hours": "8.00",
        "sludge_produced_kg": "480.00",  "compliance_status": "COMPLIANT",
        "source_method": "MANUAL",       "is_anomaly": "false",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id
        else:
            errors.append("asset_no is required")

        ps = (row.get("process_stage") or "SECONDARY").upper()
        if ps not in {e.value for e in _WastewaterProcess}:
            errors.append(f"process_stage '{ps}' is invalid; valid: {sorted(e.value for e in _WastewaterProcess)}")
        else:
            row["process_stage"] = ps

        cs = (row.get("compliance_status") or "COMPLIANT").upper()
        if cs not in {e.value for e in _ComplianceStatus}:
            row["compliance_status"] = "COMPLIANT"
        else:
            row["compliance_status"] = cs

        if row.get("source_method") not in {e.value for e in _SourceMethod}:
            row["source_method"] = "MANUAL"
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        return False

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        import random
        dt = data.get("record_datetime")
        date_str = dt.strftime("%Y%m%d") if hasattr(dt, "strftime") else str(dt)[:10].replace("-", "")
        rec_no = f"WW-{date_str}-{random.randint(10000, 99999)}"
        try:
            ps = _WastewaterProcess(data.get("process_stage", "SECONDARY"))
        except ValueError:
            ps = _WastewaterProcess.SECONDARY
        try:
            cs = _ComplianceStatus(data.get("compliance_status", "COMPLIANT"))
        except ValueError:
            cs = _ComplianceStatus.COMPLIANT
        try:
            sm = _SourceMethod(data.get("source_method", "MANUAL"))
        except ValueError:
            sm = _SourceMethod.MANUAL
        obj = _WastewaterRecord(
            record_no=rec_no,
            asset_id=data.get("asset_id"),
            record_datetime=data.get("record_datetime"),
            process_stage=ps,
            shift_ref=data.get("shift_ref"),
            influent_flow_m3h=data.get("influent_flow_m3h"),
            effluent_flow_m3h=data.get("effluent_flow_m3h"),
            influent_cod_mgl=data.get("influent_cod_mgl"),
            effluent_cod_mgl=data.get("effluent_cod_mgl"),
            influent_bod_mgl=data.get("influent_bod_mgl"),
            effluent_bod_mgl=data.get("effluent_bod_mgl"),
            influent_tss_mgl=data.get("influent_tss_mgl"),
            effluent_tss_mgl=data.get("effluent_tss_mgl"),
            influent_ph=data.get("influent_ph"),
            effluent_ph=data.get("effluent_ph"),
            do_mgl=data.get("do_mgl"),
            mlss_mgl=data.get("mlss_mgl"),
            mlvss_mgl=data.get("mlvss_mgl"),
            svi=data.get("svi"),
            srt_days=data.get("srt_days"),
            conductivity_us_cm=data.get("conductivity_us_cm"),
            temperature_c=data.get("temperature_c"),
            power_consumed_kwh=data.get("power_consumed_kwh"),
            aeration_runtime_hours=data.get("aeration_runtime_hours"),
            blower_power_kw=data.get("blower_power_kw"),
            nutrient_dose_kg=data.get("nutrient_dose_kg"),
            antifoam_dose_kg=data.get("antifoam_dose_kg"),
            sludge_produced_kg=data.get("sludge_produced_kg"),
            sludge_dewatered_pct=data.get("sludge_dewatered_pct"),
            sludge_volume_m3=data.get("sludge_volume_m3"),
            sludge_disposal_qty_kg=data.get("sludge_disposal_qty_kg"),
            compliance_status=cs,
            permit_limit_ref=data.get("permit_limit_ref"),
            deviation_reason=data.get("deviation_reason"),
            corrective_action=data.get("corrective_action"),
            source_method=sm,
            is_anomaly=bool(data.get("is_anomaly", False)),
            anomaly_note=data.get("anomaly_note"),
            notes=data.get("notes"),
        )
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Tariff adapter ────────────────────────────────────────────────────

class _UtilityTariffImport(BaseModel):
    """CSV schema for bulk-importing utility tariff / pricing structures."""
    tariff_code:    str
    name:           str
    utility_type:   str
    effective_from: date
    unit:           str
    base_rate:      Decimal
    tariff_type:    str = "FLAT"
    effective_to:   Optional[date] = None
    supplier_code:  Optional[str] = None    # resolved → supplier_id
    currency_code:  str = "USD"
    peak_rate:      Optional[Decimal] = None
    offpeak_rate:   Optional[Decimal] = None
    demand_rate:    Optional[Decimal] = None
    fixed_charge:   Optional[Decimal] = None
    tax_rate_pct:   Optional[Decimal] = None
    tax_rule:       Optional[str] = None
    description:    Optional[str] = None
    is_active:      bool = True
    notes:          Optional[str] = None


class UtilityTariffAdapter(BaseImportAdapter):
    """Bulk-import utility tariff pricing structures. Unique key: tariff_code."""
    module          = "utility_tariffs"
    perm_module     = "utility_management"
    schema_class    = _UtilityTariffImport
    unique_key      = ["tariff_code"]
    field_overrides: dict = {}
    example_row     = {
        "tariff_code": "ELEC-FLAT-01",
        "name": "Electricity Flat Rate 2025",
        "utility_type": "ELECTRICITY",
        "tariff_type": "FLAT",
        "effective_from": "2025-01-01",
        "effective_to": "2025-12-31",
        "unit": "kWh",
        "currency_code": "USD",
        "base_rate": "0.1200",
        "peak_rate": "0.1800",
        "offpeak_rate": "0.0800",
        "fixed_charge": "250.00",
        "tax_rate_pct": "16.00",
        "tax_rule": "Standard VAT",
        "supplier_code": "",
        "is_active": "true",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        ut = (row.get("utility_type") or "").upper()
        if ut not in {e.value for e in _UtilityType}:
            errors.append(f"utility_type '{ut}' is invalid; valid: {sorted(e.value for e in _UtilityType)}")
        else:
            row["utility_type"] = ut

        tt = (row.get("tariff_type") or "FLAT").upper()
        valid_tt = {"FLAT", "TIME_OF_USE", "DEMAND", "STEPPED"}
        if tt not in valid_tt:
            errors.append(f"tariff_type '{tt}' is invalid; valid: {sorted(valid_tt)}")
        else:
            row["tariff_type"] = tt

        supplier_code = row.pop("supplier_code", None)
        if supplier_code:
            r = await db.execute(select(Supplier).where(Supplier.code == supplier_code.upper()))
            sup = r.scalar_one_or_none()
            if sup is None:
                errors.append(f"supplier_code '{supplier_code}' not found")
            else:
                row["supplier_id"] = sup.id

        row["tariff_code"] = (row.get("tariff_code") or "").upper()
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityTariff).where(
                _UtilityTariff.tariff_code == (row.get("tariff_code") or "").upper()
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _UtilityTariff(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Bill adapter ──────────────────────────────────────────────────────

class _UtilityBillImport(BaseModel):
    """CSV schema for bulk-importing utility supplier bills."""
    bill_no:             str
    utility_type:        str
    billing_period_from: date
    billing_period_to:   date
    total_amount:        Decimal
    provider_name:       Optional[str] = None
    supplier_code:       Optional[str] = None   # resolved → supplier_id
    tariff_code:         Optional[str] = None   # resolved → tariff_id
    bill_reference:      Optional[str] = None
    invoice_date:        Optional[date] = None
    due_date:            Optional[date] = None
    consumption_quantity: Optional[Decimal] = None
    consumption_unit:    Optional[str] = None
    unit_rate:           Optional[Decimal] = None
    base_charge:         Optional[Decimal] = None
    energy_charge:       Optional[Decimal] = None
    demand_charge:       Optional[Decimal] = None
    fixed_charge:        Optional[Decimal] = None
    surcharge_amount:    Optional[Decimal] = None
    tax_amount:          Optional[Decimal] = None
    currency_code:       str = "USD"
    status:              str = "RECEIVED"
    payment_date:        Optional[date] = None
    document_ref:        Optional[str] = None
    notes:               Optional[str] = None


class UtilityBillAdapter(BaseImportAdapter):
    """Bulk-import utility bills. Unique key: bill_no."""
    module          = "utility_bills"
    perm_module     = "utility_management"
    schema_class    = _UtilityBillImport
    unique_key      = ["bill_no"]
    field_overrides: dict = {}
    example_row     = {
        "bill_no": "BILL-2025-001",
        "utility_type": "ELECTRICITY",
        "provider_name": "Kenya Power",
        "supplier_code": "",
        "tariff_code": "ELEC-FLAT-01",
        "bill_reference": "INV-KPC-12345",
        "billing_period_from": "2025-01-01",
        "billing_period_to": "2025-01-31",
        "invoice_date": "2025-02-05",
        "due_date": "2025-02-28",
        "consumption_quantity": "48500.00",
        "consumption_unit": "kWh",
        "unit_rate": "0.1200",
        "energy_charge": "5820.00",
        "fixed_charge": "250.00",
        "tax_amount": "981.60",
        "total_amount": "7051.60",
        "currency_code": "USD",
        "status": "RECEIVED",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []
        ut = (row.get("utility_type") or "").upper()
        if ut not in {e.value for e in _UtilityType}:
            errors.append(f"utility_type '{ut}' is invalid")
        else:
            row["utility_type"] = ut

        status = (row.get("status") or "RECEIVED").upper()
        if status not in {e.value for e in _BillStatus}:
            row["status"] = "RECEIVED"
        else:
            row["status"] = status

        supplier_code = row.pop("supplier_code", None)
        if supplier_code:
            r = await db.execute(select(Supplier).where(Supplier.code == supplier_code.upper()))
            sup = r.scalar_one_or_none()
            if sup is None:
                errors.append(f"supplier_code '{supplier_code}' not found")
            else:
                row["supplier_id"] = sup.id

        tariff_code = row.pop("tariff_code", None)
        if tariff_code:
            r = await db.execute(
                select(_UtilityTariff).where(_UtilityTariff.tariff_code == tariff_code.upper())
            )
            tariff = r.scalar_one_or_none()
            if tariff is None:
                errors.append(f"tariff_code '{tariff_code}' not found — import tariffs first")
            else:
                row["tariff_id"] = tariff.id
                row["tariff_code"] = tariff_code.upper()

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityBill).where(_UtilityBill.bill_no == row.get("bill_no"))
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _UtilityBill(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Cost Allocation adapter ───────────────────────────────────────────

class _UtilityAllocationImport(BaseModel):
    """CSV schema for bulk-importing utility cost allocation records."""
    allocation_no:       str
    utility_type:        str
    allocation_date:     date
    total_cost:          Decimal
    allocated_cost:      Decimal
    period_start:        Optional[date] = None
    period_end:          Optional[date] = None
    allocation_method:   str = "METERED"
    target_type:         Optional[str] = None
    target_id:           Optional[str] = None
    target_name:         Optional[str] = None
    department:          Optional[str] = None
    production_line:     Optional[str] = None
    building_area:       Optional[str] = None
    machine_ref:         Optional[str] = None
    batch_no:            Optional[str] = None
    bill_no:             Optional[str] = None   # resolved → bill_id
    source_cost:         Optional[Decimal] = None
    allocation_basis:    Optional[Decimal] = None
    allocation_basis_unit: Optional[str] = None
    allocated_quantity:  Optional[Decimal] = None
    quantity_unit:       Optional[str] = None
    production_volume_kg: Optional[Decimal] = None
    currency_code:       str = "USD"
    cost_per_unit:       Optional[Decimal] = None
    cost_per_ton:        Optional[Decimal] = None
    source_method:       str = "CALCULATED"
    notes:               Optional[str] = None


class UtilityCostAllocationAdapter(BaseImportAdapter):
    """Bulk-import utility cost allocation records. Unique key: allocation_no."""
    module          = "utility_allocations"
    perm_module     = "utility_management"
    schema_class    = _UtilityAllocationImport
    unique_key      = ["allocation_no"]
    field_overrides: dict = {}
    example_row     = {
        "allocation_no": "ALLOC-2025-001",
        "utility_type": "ELECTRICITY",
        "allocation_date": "2025-01-31",
        "period_start": "2025-01-01",
        "period_end": "2025-01-31",
        "allocation_method": "METERED",
        "target_type": "DEPARTMENT",
        "target_id": "PRODUCTION",
        "target_name": "Production Department",
        "department": "Production",
        "production_line": "LINE-01",
        "bill_no": "BILL-2025-001",
        "allocated_quantity": "28500.00",
        "quantity_unit": "kWh",
        "total_cost": "7051.60",
        "allocated_cost": "4123.80",
        "currency_code": "USD",
        "cost_per_unit": "0.1447",
        "production_volume_kg": "95000.00",
        "cost_per_ton": "43.41",
        "source_method": "METERED",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        from decimal import Decimal as _D
        errors: list[str] = []

        ut = (row.get("utility_type") or "").upper()
        if ut not in {e.value for e in _UtilityType}:
            errors.append(f"utility_type '{ut}' is invalid")
        else:
            row["utility_type"] = ut

        am = (row.get("allocation_method") or "METERED").upper()
        if am not in {e.value for e in _AllocationMethod}:
            errors.append(f"allocation_method '{am}' is invalid; valid: {sorted(e.value for e in _AllocationMethod)}")
        else:
            row["allocation_method"] = am

        sm = (row.get("source_method") or "CALCULATED").upper()
        if sm not in {e.value for e in _SourceMethod}:
            row["source_method"] = "CALCULATED"
        else:
            row["source_method"] = sm

        bill_no = row.pop("bill_no", None)
        if bill_no:
            r = await db.execute(select(_UtilityBill).where(_UtilityBill.bill_no == bill_no))
            bill = r.scalar_one_or_none()
            if bill is None:
                errors.append(f"bill_no '{bill_no}' not found — import bills first")
            else:
                row["bill_id"] = bill.id

        aq = row.get("allocated_quantity")
        ac = row.get("allocated_cost")
        pv = row.get("production_volume_kg")
        if not row.get("cost_per_unit") and aq and ac and Decimal(str(aq)) > 0:
            row["cost_per_unit"] = Decimal(str(ac)) / Decimal(str(aq))
        if not row.get("cost_per_ton") and pv and ac and Decimal(str(pv)) > 0:
            row["cost_per_ton"] = Decimal(str(ac)) / (Decimal(str(pv)) / 1000)

        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityCostAllocation).where(
                _UtilityCostAllocation.allocation_no == row.get("allocation_no")
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _UtilityCostAllocation(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Utility Alarm Rule adapter ────────────────────────────────────────────────

class _UtilityAlarmRuleImport(BaseModel):
    """CSV schema for bulk-importing utility alarm / threshold rules."""
    rule_code:        str
    name:             str
    utility_type:     str
    parameter:        str
    operator:         str   # GT/LT/GTE/LTE/EQ/NEQ/DELTA_PCT
    threshold_value:  Decimal
    device_code:      Optional[str] = None   # resolved → device_id
    asset_no:         Optional[str] = None   # resolved → asset_id
    threshold_unit:   Optional[str] = None
    severity:         str = "WARNING"
    cooldown_minutes: int = 15
    is_active:        bool = True
    notification_emails:  Optional[str] = None
    notification_channel: Optional[str] = None
    description:      Optional[str] = None
    notes:            Optional[str] = None


class UtilityAlarmRuleAdapter(BaseImportAdapter):
    """Bulk-import utility alarm threshold rules. Unique key: rule_code."""
    module          = "utility_alarm_rules"
    perm_module     = "utility_management"
    schema_class    = _UtilityAlarmRuleImport
    unique_key      = ["rule_code"]
    field_overrides: dict = {}
    example_row     = {
        "rule_code": "ALM-ELEC-HI-001",
        "name": "Main Electricity High Consumption Alert",
        "utility_type": "ELECTRICITY",
        "device_code": "MTR-ELEC-001",
        "asset_no": "ELEC-PANEL-01",
        "parameter": "power_kw",
        "operator": "GT",
        "threshold_value": "500.00",
        "threshold_unit": "kW",
        "severity": "WARNING",
        "cooldown_minutes": "30",
        "is_active": "true",
        "notification_emails": "utilities@plant.com,manager@plant.com",
        "notification_channel": "slack_utilities",
        "description": "Alert when main power exceeds 500kW",
        "notes": "",
    }

    async def resolve_relations(self, row: dict, db: AsyncSession) -> tuple[dict, list[str]]:
        errors: list[str] = []

        ut = (row.get("utility_type") or "").upper()
        if ut not in {e.value for e in _UtilityType}:
            errors.append(f"utility_type '{ut}' is invalid")
        else:
            row["utility_type"] = ut

        op = (row.get("operator") or "").upper()
        if op not in {e.value for e in _AlarmOperator}:
            errors.append(f"operator '{op}' is invalid; valid: {sorted(e.value for e in _AlarmOperator)}")
        else:
            row["operator"] = op

        sev = (row.get("severity") or "WARNING").upper()
        if sev not in {e.value for e in _AlarmSeverity}:
            row["severity"] = "WARNING"
        else:
            row["severity"] = sev

        device_code = row.pop("device_code", None)
        if device_code:
            r = await db.execute(
                select(_UtilityDevice).where(_UtilityDevice.device_code == device_code.upper())
            )
            dev = r.scalar_one_or_none()
            if dev is None:
                errors.append(f"device_code '{device_code}' not found in utility_devices")
            else:
                row["device_id"] = dev.id

        asset_no = row.pop("asset_no", None)
        if asset_no:
            r = await db.execute(
                select(_UtilityAsset).where(_UtilityAsset.asset_no == asset_no.upper())
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                errors.append(f"asset_no '{asset_no}' not found in utility_assets")
            else:
                row["asset_id"] = asset.id

        row["rule_code"] = (row.get("rule_code") or "").upper()
        return row, errors

    async def exists_in_db(self, row: dict, db: AsyncSession) -> bool:
        r = await db.execute(
            select(_UtilityAlarmRule).where(
                _UtilityAlarmRule.rule_code == (row.get("rule_code") or "").upper()
            )
        )
        return r.scalar_one_or_none() is not None

    async def insert(self, data: dict, db: AsyncSession) -> Any:
        obj = _UtilityAlarmRule(**{k: v for k, v in data.items() if v is not None})
        db.add(obj)
        await db.flush()
        return obj


# ── Adapter registry ──────────────────────────────────────────────────────────

ADAPTERS: dict[str, BaseImportAdapter] = {
    "products":              ProductAdapter(),
    "materials":             MaterialAdapter(),
    "suppliers":             SupplierAdapter(),
    "warehouses":            WarehouseAdapter(),
    "employees":             EmployeeAdapter(),
    "inventory_stock":       InventoryStockAdapter(),
    "recipes":               RecipeAdapter(),
    "recipe_items":          RecipeItemAdapter(),
    "recipe_steps":          RecipeStepAdapter(),
    "qc_parameters":         QCParameterAdapter(),
    # Utility Management — Master data
    "utility_asset_categories":     UtilityAssetCategoryAdapter(),
    "utility_assets":               UtilityAssetAdapter(),
    "utility_devices":              UtilityDeviceAdapter(),
    "utility_tariffs":              UtilityTariffAdapter(),
    "utility_alarm_rules":          UtilityAlarmRuleAdapter(),
    # Utility Management — Transactional (type-specific)
    "electricity_transactions":     ElectricityTransactionAdapter(),
    "electricity_consumption":      ElectricityConsumptionAdapter(),
    "water_transactions":           WaterTransactionAdapter(),
    "water_consumption":            WaterConsumptionAdapter(),
    "utility_transactions":         UtilityTransactionImportAdapter(),
    "utility_readings":             UtilityReadingAdapter(),
    "utility_bills":                UtilityBillAdapter(),
    "utility_allocations":          UtilityCostAllocationAdapter(),
    # Utility Management — Operational records
    "soft_water_records":           SoftWaterRecordAdapter(),
    "boiler_records":               BoilerRecordAdapter(),
    "steam_transactions":           SteamTransactionAdapter(),
    "compressor_records":           CompressorRecordAdapter(),
    "air_transactions":             AirTransactionAdapter(),
    "solar_records":                SolarRecordImportAdapter(),
    "treatment_chemical_records":   TreatmentChemicalRecordAdapter(),
    "wastewater_records":           WastewaterRecordAdapter(),
    # Advanced Production
    "work_centers":          WorkCenterImportAdapter(),
    "routings":              RoutingImportAdapter(),
    "work_orders":           WorkOrderImportAdapter(),
    "production_schedules":  ScheduleImportAdapter(),
    "time_tracking":         TimeTrackingImportAdapter(),
    "downtime_events":       DowntimeImportAdapter(),
    "qc_inspections":        QCInspectionImportAdapter(),
    "waste_records":         WasteImportAdapter(),
    "batch_lots":            BatchLotImportAdapter(),
    "labor_logs":            LaborImportAdapter(),
    "oee_records":           OEEImportAdapter(),
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
