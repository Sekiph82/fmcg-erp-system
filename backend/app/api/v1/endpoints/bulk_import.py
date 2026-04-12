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


# ── Adapter registry ──────────────────────────────────────────────────────────

ADAPTERS: dict[str, BaseImportAdapter] = {
    "products":              ProductAdapter(),
    "materials":             MaterialAdapter(),
    "suppliers":             SupplierAdapter(),
    "warehouses":            WarehouseAdapter(),
    "employees":             EmployeeAdapter(),
    "inventory_stock":       InventoryStockAdapter(),
    "recipes":               RecipeAdapter(),
    "qc_parameters":         QCParameterAdapter(),
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
