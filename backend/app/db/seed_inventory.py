"""
FMCG inventory demo seed data — lots, stock balances, movements, FIFO cost layers.

Run only when SEED_DEMO_DATA=true (enforced by caller in main.py).
Fully idempotent. Depends on seed_production_data having already run.

Idempotency notes:
  - Lot: lookup by (lot_number, material_id/product_id) — lot_number is not unique globally
  - Stock: lookup by (warehouse_id, product_id, material_id, lot_id) — no UniqueConstraint exists
  - StockMovement: lookup by (reference_number, movement_type, stock_type) — reference_number not unique
  - CostLayer: lookup by (movement_id) — one per movement
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    CostLayer,
    Lot,
    MovementType,
    Stock,
    StockMovement,
    StockType,
)
from app.models.master import Material, Product, Warehouse
from app.models.traceability import TraceEvent, TraceEventType
from app.models.wms import StorageLocation, WarehouseZone, ZoneType

logger = logging.getLogger(__name__)

_today = date.today()


# ── upstream lookup helpers ───────────────────────────────────────────────────


async def _get_warehouse(db: AsyncSession, code: str) -> Warehouse | None:
    return (await db.execute(select(Warehouse).where(Warehouse.code == code))).scalar_one_or_none()


async def _get_product(db: AsyncSession, sku: str) -> Product | None:
    return (await db.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none()


async def _get_material(db: AsyncSession, code: str) -> Material | None:
    return (await db.execute(select(Material).where(Material.code == code))).scalar_one_or_none()


# ── idempotent create helpers ─────────────────────────────────────────────────


async def _get_or_create_lot(
    db: AsyncSession, lot_number: str, material_id=None, product_id=None, **kw
) -> Lot:
    q = select(Lot).where(Lot.lot_number == lot_number)
    if material_id:
        q = q.where(Lot.material_id == material_id)
    if product_id:
        q = q.where(Lot.product_id == product_id)
    obj = (await db.execute(q)).scalar_one_or_none()
    if not obj:
        obj = Lot(lot_number=lot_number, material_id=material_id, product_id=product_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_stock(
    db: AsyncSession,
    warehouse_id,
    stock_type: StockType,
    product_id=None,
    material_id=None,
    lot_id=None,
    **kw,
) -> Stock:
    q = (
        select(Stock)
        .where(Stock.warehouse_id == warehouse_id)
        .where(Stock.stock_type == stock_type)
    )
    if product_id:
        q = q.where(Stock.product_id == product_id)
    else:
        q = q.where(Stock.product_id.is_(None))
    if material_id:
        q = q.where(Stock.material_id == material_id)
    else:
        q = q.where(Stock.material_id.is_(None))
    if lot_id:
        q = q.where(Stock.lot_id == lot_id)
    else:
        q = q.where(Stock.lot_id.is_(None))
    obj = (await db.execute(q)).scalar_one_or_none()
    if not obj:
        obj = Stock(
            warehouse_id=warehouse_id,
            stock_type=stock_type,
            product_id=product_id,
            material_id=material_id,
            lot_id=lot_id,
            **kw,
        )
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_movement(
    db: AsyncSession,
    reference_number: str,
    movement_type: MovementType,
    stock_type: StockType,
    **kw,
) -> StockMovement | None:
    q = (
        select(StockMovement)
        .where(StockMovement.reference_number == reference_number)
        .where(StockMovement.movement_type == movement_type)
        .where(StockMovement.stock_type == stock_type)
    )
    obj = (await db.execute(q)).scalar_one_or_none()
    if not obj:
        obj = StockMovement(
            reference_number=reference_number,
            movement_type=movement_type,
            stock_type=stock_type,
            **kw,
        )
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_cost_layer(
    db: AsyncSession, movement_id, **kw
) -> CostLayer:
    q = select(CostLayer).where(CostLayer.movement_id == movement_id)
    obj = (await db.execute(q)).scalar_one_or_none()
    if not obj:
        obj = CostLayer(movement_id=movement_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


# ── main seed function ────────────────────────────────────────────────────────


async def _get_or_create_zone(db: AsyncSession, warehouse_id, code: str, **kw) -> WarehouseZone:
    obj = (await db.execute(
        select(WarehouseZone).where(WarehouseZone.warehouse_id == warehouse_id, WarehouseZone.code == code)
    )).scalar_one_or_none()
    if not obj:
        obj = WarehouseZone(warehouse_id=warehouse_id, code=code, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_location(db: AsyncSession, zone_id, code: str, **kw) -> StorageLocation:
    obj = (await db.execute(
        select(StorageLocation).where(StorageLocation.zone_id == zone_id, StorageLocation.code == code)
    )).scalar_one_or_none()
    if not obj:
        obj = StorageLocation(zone_id=zone_id, code=code, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_trace_event(db: AsyncSession, reference_number: str, event_type: TraceEventType, **kw) -> TraceEvent:
    obj = (await db.execute(
        select(TraceEvent).where(
            TraceEvent.reference_number == reference_number,
            TraceEvent.trace_event_type == event_type,
        )
    )).scalar_one_or_none()
    if not obj:
        obj = TraceEvent(reference_number=reference_number, trace_event_type=event_type, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def seed_inventory_data(db: AsyncSession) -> None:
    """Seed FMCG inventory demo data. Idempotent. Requires seed_production_data first."""
    logger.info("Seeding FMCG inventory demo data …")

    # ── 0. Verify upstream TASK-015 data exists ───────────────────────────────

    wh_rm = await _get_warehouse(db, "PROD-WH")
    wh_fg = await _get_warehouse(db, "FG-WH")
    if not wh_rm or not wh_fg:
        logger.warning("Inventory seed skipped: PROD-WH / FG-WH not found — run seed_production_data first")
        return

    # Raw materials
    mat_surf  = await _get_material(db, "RAW-SURF-LAS")
    mat_frag  = await _get_material(db, "RAW-FRAG-LAV")
    mat_thick = await _get_material(db, "RAW-THICK-SALT")
    mat_b1l   = await _get_material(db, "PKG-BTL-1L")
    mat_b500  = await _get_material(db, "PKG-BTL-500")
    mat_cap   = await _get_material(db, "PKG-CAP-28")
    mat_lbl   = await _get_material(db, "PKG-LBL-ROLL")

    # Finished products
    p_ld  = await _get_product(db, "POVU-LD-1L")
    p_fs  = await _get_product(db, "POVU-FS-500ML")
    p_dw  = await _get_product(db, "POVU-DW-500ML")
    p_sc  = await _get_product(db, "POVU-SC-750ML")
    p_hs  = await _get_product(db, "POVU-HS-200ML")

    if not all([mat_surf, mat_frag, mat_thick, mat_b1l, mat_b500, mat_cap, mat_lbl,
                p_ld, p_fs, p_dw, p_sc, p_hs]):
        logger.warning("Inventory seed skipped: some products/materials missing — run seed_production_data first")
        return

    # ── 1. Lots for raw materials ─────────────────────────────────────────────

    lot_specs = [
        ("LOT-SURF-2025-001",  mat_surf,  date(2027, 6,  1)),
        ("LOT-FRAG-2025-001",  mat_frag,  date(2027, 12, 1)),
        ("LOT-THICK-2025-001", mat_thick, date(2028, 1,  1)),
        ("LOT-BTL1L-2025-001", mat_b1l,   date(2029, 1,  1)),
        ("LOT-BTL500-2025-001",mat_b500,  date(2029, 1,  1)),
        ("LOT-CAP-2025-001",   mat_cap,   date(2029, 6,  1)),
        ("LOT-LBL-2025-001",   mat_lbl,   date(2028, 6,  1)),
    ]
    lots: dict[str, Lot] = {}
    for lot_no, mat, exp in lot_specs:
        lot = await _get_or_create_lot(
            db, lot_no, material_id=mat.id,
            manufacture_date=date(2025, 1, 15),
            expiry_date=exp,
            is_quarantine=False,
        )
        lots[lot_no] = lot

    # ── 2. Raw material stock balances in PROD-WH ─────────────────────────────

    raw_stock_specs = [
        (mat_surf,  lots["LOT-SURF-2025-001"],   Decimal("5000"),  "LOT-SURF-2025-001"),
        (mat_frag,  lots["LOT-FRAG-2025-001"],   Decimal("200"),   "LOT-FRAG-2025-001"),
        (mat_thick, lots["LOT-THICK-2025-001"],  Decimal("1500"),  "LOT-THICK-2025-001"),
        (mat_b1l,   lots["LOT-BTL1L-2025-001"],  Decimal("15000"), "LOT-BTL1L-2025-001"),
        (mat_b500,  lots["LOT-BTL500-2025-001"], Decimal("25000"), "LOT-BTL500-2025-001"),
        (mat_cap,   lots["LOT-CAP-2025-001"],    Decimal("40000"), "LOT-CAP-2025-001"),
        (mat_lbl,   lots["LOT-LBL-2025-001"],    Decimal("40000"), "LOT-LBL-2025-001"),
    ]
    raw_stocks: dict[str, Stock] = {}
    for mat, lot, qty, lot_key in raw_stock_specs:
        s = await _get_or_create_stock(
            db,
            warehouse_id=wh_rm.id,
            stock_type=StockType.MATERIAL,
            material_id=mat.id,
            lot_id=lot.id,
            quantity_on_hand=qty,
            quantity_available=qty,
            quantity_reserved=Decimal("0"),
        )
        raw_stocks[lot_key] = s

    # ── 3. Finished goods stock balances in FG-WH ─────────────────────────────

    fg_stock_specs = [
        (p_ld,  Decimal("4500")),
        (p_fs,  Decimal("2800")),
        (p_dw,  Decimal("3600")),
        (p_sc,  Decimal("2300")),
        (p_hs,  Decimal("7500")),
    ]
    fg_stocks: dict[str, Stock] = {}
    for prod, qty in fg_stock_specs:
        s = await _get_or_create_stock(
            db,
            warehouse_id=wh_fg.id,
            stock_type=StockType.PRODUCT,
            product_id=prod.id,
            quantity_on_hand=qty,
            quantity_available=qty,
            quantity_reserved=Decimal("0"),
        )
        fg_stocks[prod.sku] = s

    # ── 4. Stock movements ────────────────────────────────────────────────────

    # 4a. Opening balance ADJUSTMENT for each raw material
    raw_adj_specs = [
        ("SEED-INV-OPEN-RAW-SURF",  mat_surf,  lots["LOT-SURF-2025-001"],   Decimal("5000")),
        ("SEED-INV-OPEN-RAW-FRAG",  mat_frag,  lots["LOT-FRAG-2025-001"],   Decimal("200")),
        ("SEED-INV-OPEN-RAW-THICK", mat_thick, lots["LOT-THICK-2025-001"],  Decimal("1500")),
        ("SEED-INV-OPEN-PKG-BTL1L", mat_b1l,   lots["LOT-BTL1L-2025-001"],  Decimal("15000")),
        ("SEED-INV-OPEN-PKG-BTL500",mat_b500,  lots["LOT-BTL500-2025-001"], Decimal("25000")),
        ("SEED-INV-OPEN-PKG-CAP",   mat_cap,   lots["LOT-CAP-2025-001"],    Decimal("40000")),
        ("SEED-INV-OPEN-PKG-LBL",   mat_lbl,   lots["LOT-LBL-2025-001"],    Decimal("40000")),
    ]
    open_date = _today - timedelta(days=90)
    for ref, mat, lot, qty in raw_adj_specs:
        await _get_or_create_movement(
            db, ref, MovementType.ADJUSTMENT, StockType.MATERIAL,
            movement_date=open_date,
            material_id=mat.id,
            lot_id=lot.id,
            destination_warehouse_id=wh_rm.id,
            quantity=qty,
            notes="Opening balance — production seed demo",
        )

    # 4b. GRN RECEIPT for each raw material
    raw_grn_specs = [
        ("SEED-GRN-RAW-SURF",  mat_surf,  lots["LOT-SURF-2025-001"],   Decimal("5000"),  Decimal("120.00")),
        ("SEED-GRN-RAW-FRAG",  mat_frag,  lots["LOT-FRAG-2025-001"],   Decimal("200"),   Decimal("850.00")),
        ("SEED-GRN-RAW-THICK", mat_thick, lots["LOT-THICK-2025-001"],  Decimal("1500"),  Decimal("15.00")),
        ("SEED-GRN-PKG-BTL1L", mat_b1l,   lots["LOT-BTL1L-2025-001"],  Decimal("15000"), Decimal("8.50")),
        ("SEED-GRN-PKG-BTL500",mat_b500,  lots["LOT-BTL500-2025-001"], Decimal("25000"), Decimal("5.50")),
        ("SEED-GRN-PKG-CAP",   mat_cap,   lots["LOT-CAP-2025-001"],    Decimal("40000"), Decimal("1.20")),
        ("SEED-GRN-PKG-LBL",   mat_lbl,   lots["LOT-LBL-2025-001"],    Decimal("40000"), Decimal("2.80")),
    ]
    grn_date = _today - timedelta(days=70)
    grn_movements: dict[str, StockMovement] = {}
    for ref, mat, lot, qty, unit_cost in raw_grn_specs:
        mv = await _get_or_create_movement(
            db, ref, MovementType.RECEIPT, StockType.MATERIAL,
            movement_date=grn_date,
            material_id=mat.id,
            lot_id=lot.id,
            destination_warehouse_id=wh_rm.id,
            quantity=qty,
            unit_cost=unit_cost,
            total_cost=qty * unit_cost,
            valuation_method="FIFO",
            notes="Supplier GRN — production seed demo",
        )
        grn_movements[ref] = mv

    # 4c. Production ISSUE for selected raw materials (consumed in completed orders)
    issue_specs = [
        ("SEED-PROD-ISSUE-SURF",  mat_surf,  lots["LOT-SURF-2025-001"],   Decimal("3500")),
        ("SEED-PROD-ISSUE-FRAG",  mat_frag,  lots["LOT-FRAG-2025-001"],   Decimal("50")),
        ("SEED-PROD-ISSUE-THICK", mat_thick, lots["LOT-THICK-2025-001"],  Decimal("70")),
        ("SEED-PROD-ISSUE-BTL1L", mat_b1l,   lots["LOT-BTL1L-2025-001"],  Decimal("5000")),
        ("SEED-PROD-ISSUE-BTL500",mat_b500,  lots["LOT-BTL500-2025-001"], Decimal("12000")),
        ("SEED-PROD-ISSUE-CAP",   mat_cap,   lots["LOT-CAP-2025-001"],    Decimal("17000")),
        ("SEED-PROD-ISSUE-LBL",   mat_lbl,   lots["LOT-LBL-2025-001"],    Decimal("17000")),
    ]
    issue_date = _today - timedelta(days=50)
    for ref, mat, lot, qty in issue_specs:
        await _get_or_create_movement(
            db, ref, MovementType.ISSUE, StockType.MATERIAL,
            movement_date=issue_date,
            material_id=mat.id,
            lot_id=lot.id,
            source_warehouse_id=wh_rm.id,
            quantity=qty,
            notes="Production consumption — production seed demo",
        )

    # 4d. Production RECEIPT for finished goods
    prod_rcpt_specs = [
        ("SEED-PROD-RCPT-LD",  p_ld,  Decimal("4500")),
        ("SEED-PROD-RCPT-FS",  p_fs,  Decimal("2800")),
        ("SEED-PROD-RCPT-DW",  p_dw,  Decimal("3600")),
        ("SEED-PROD-RCPT-SC",  p_sc,  Decimal("2300")),
        ("SEED-PROD-RCPT-HS",  p_hs,  Decimal("7500")),
    ]
    prod_rcpt_date = _today - timedelta(days=45)
    for ref, prod, qty in prod_rcpt_specs:
        await _get_or_create_movement(
            db, ref, MovementType.RECEIPT, StockType.PRODUCT,
            movement_date=prod_rcpt_date,
            product_id=prod.id,
            destination_warehouse_id=wh_fg.id,
            quantity=qty,
            notes="Production receipt to FG warehouse — production seed demo",
        )

    # ── 5. FIFO CostLayers for raw material GRN receipts ──────────────────────

    cl_specs = [
        ("SEED-GRN-RAW-SURF",  mat_surf,  Decimal("5000"),  Decimal("120.00")),
        ("SEED-GRN-RAW-FRAG",  mat_frag,  Decimal("200"),   Decimal("850.00")),
        ("SEED-GRN-RAW-THICK", mat_thick, Decimal("1500"),  Decimal("15.00")),
        ("SEED-GRN-PKG-BTL1L", mat_b1l,   Decimal("15000"), Decimal("8.50")),
        ("SEED-GRN-PKG-BTL500",mat_b500,  Decimal("25000"), Decimal("5.50")),
        ("SEED-GRN-PKG-CAP",   mat_cap,   Decimal("40000"), Decimal("1.20")),
        ("SEED-GRN-PKG-LBL",   mat_lbl,   Decimal("40000"), Decimal("2.80")),
    ]
    for grn_ref, mat, qty, unit_cost in cl_specs:
        mv = grn_movements.get(grn_ref)
        if mv:
            total_val = qty * unit_cost
            await _get_or_create_cost_layer(
                db, mv.id,
                stock_type=StockType.MATERIAL,
                material_id=mat.id,
                warehouse_id=wh_rm.id,
                receipt_date=grn_date,
                qty_received=qty,
                qty_remaining=qty,
                unit_cost=unit_cost,
                total_value=total_val,
                is_exhausted=False,
            )

    # ── WMS Zones and Storage Locations (TASK-016 I2) ────────────────────────

    wh_rm = await _get_warehouse(db, "PROD-WH")
    wh_fg = await _get_warehouse(db, "FG-WH")

    if wh_rm:
        # PROD-WH zones
        zone_rm = await _get_or_create_zone(db, wh_rm.id, "PROD-WH-RM",
            name="Raw Material Storage", zone_type=ZoneType.RAW_MATERIAL,
            description="Bulk raw materials and packaging components")
        zone_quar = await _get_or_create_zone(db, wh_rm.id, "PROD-WH-QR",
            name="Quarantine Zone", zone_type=ZoneType.QUARANTINE,
            description="Materials under quality hold or inspection")
        zone_stg = await _get_or_create_zone(db, wh_rm.id, "PROD-WH-STG",
            name="Production Staging", zone_type=ZoneType.STAGING,
            description="Materials staged for imminent production")

        # Bins in raw material zone (A aisle)
        for bin_no in range(1, 5):
            await _get_or_create_location(db, zone_rm.id, f"PROD-WH-RM-A{bin_no:02d}",
                name=f"Rack A Row {bin_no}",
                barcode=f"PWHRMR{bin_no:03d}",
                max_weight_kg=Decimal("2000.00"),
                is_active=True,
            )
        # Quarantine holding
        await _get_or_create_location(db, zone_quar.id, "PROD-WH-QR-H01",
            name="Quarantine Hold Bay 1",
            barcode="PWHQRH001",
            max_weight_kg=Decimal("500.00"),
            is_active=True,
        )
        # Staging area
        await _get_or_create_location(db, zone_stg.id, "PROD-WH-STG-S01",
            name="Staging Pallet Bay 1",
            barcode="PWHSTGS001",
            max_weight_kg=Decimal("1000.00"),
            is_active=True,
        )

    if wh_fg:
        # FG-WH zones
        zone_fg = await _get_or_create_zone(db, wh_fg.id, "FG-WH-FG",
            name="Finished Goods Storage", zone_type=ZoneType.FINISHED_GOODS,
            description="Packed finished goods ready for dispatch")
        zone_ret = await _get_or_create_zone(db, wh_fg.id, "FG-WH-RET",
            name="Returns Bay", zone_type=ZoneType.RETURNS,
            description="Customer returns pending quality assessment")

        # Finished goods racking (B aisle)
        for bin_no in range(1, 5):
            await _get_or_create_location(db, zone_fg.id, f"FG-WH-FG-B{bin_no:02d}",
                name=f"Rack B Row {bin_no}",
                barcode=f"FGWHFGR{bin_no:03d}",
                max_weight_kg=Decimal("3000.00"),
                is_active=True,
            )
        # Returns bay
        await _get_or_create_location(db, zone_ret.id, "FG-WH-RET-R01",
            name="Returns Assessment Bay 1",
            barcode="FGWHRETR001",
            max_weight_kg=Decimal("500.00"),
            is_active=True,
        )

    # ── Trace Events (TASK-016 I3) ────────────────────────────────────────────
    # GRN receipt events — one per raw material lot (material received from supplier)

    _now_utc = datetime.now(timezone.utc)
    _grn_date = _today - timedelta(days=60)
    _grn_dt = datetime(_grn_date.year, _grn_date.month, _grn_date.day, 8, 0, 0, tzinfo=timezone.utc)

    _raw_mat_codes = [
        "RAW-SURF-LAS", "RAW-FRAG-LAV", "RAW-THICK-SALT",
        "PKG-BTL-1L", "PKG-BTL-500", "PKG-CAP-28", "PKG-LBL-ROLL",
    ]
    for mat_code in _raw_mat_codes:
        mat = await _get_material(db, mat_code)
        if not mat:
            continue
        await _get_or_create_trace_event(
            db, f"SEED-TRACE-GRN-{mat_code}", TraceEventType.RECEIPT,
            event_datetime=_grn_dt,
            source_document_type="PURCHASE_ORDER",
            notes=f"GRN receipt of {mat.name} from supplier — opening stock",
        )

    # Production consumption events — one per completed production order
    from app.models.production import ProductionOrder, ProductionOrderStatus
    result = await db.execute(
        select(ProductionOrder).where(ProductionOrder.status == ProductionOrderStatus.COMPLETED)
    )
    completed_orders = result.scalars().all()
    for po in completed_orders:
        # consumption (material issued to production)
        await _get_or_create_trace_event(
            db, f"SEED-TRACE-ISSUE-{po.order_no}", TraceEventType.CONSUMPTION,
            event_datetime=_now_utc - timedelta(days=50),
            production_order_id=po.id,
            source_document_type="PRODUCTION_ORDER",
            notes=f"Material issue to production order {po.order_no}",
        )
        # transformation (production receipt — finished goods)
        await _get_or_create_trace_event(
            db, f"SEED-TRACE-PROD-{po.order_no}", TraceEventType.TRANSFORMATION,
            event_datetime=_now_utc - timedelta(days=45),
            production_order_id=po.id,
            source_document_type="PRODUCTION_ORDER",
            notes=f"Finished goods receipt from production order {po.order_no}",
        )

    await db.commit()
    logger.info(
        "Inventory seed complete: 7 lots, %d raw stocks, %d FG stocks, "
        "%d movements, 7 cost layers, WMS zones, storage locations, trace events",
        len(raw_stocks), len(fg_stocks),
        len(raw_adj_specs) + len(raw_grn_specs) + len(issue_specs) + len(prod_rcpt_specs),
    )
