"""
FMCG production demo seed data — realistic Kenyan FMCG factory dataset.

Run only when SEED_DEMO_DATA=true (enforced by caller in main.py).
Fully idempotent: each record is looked up by its unique code/id before insert.
No migrations required — all models exist.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import (
    Material,
    MaterialType,
    Product,
    ProductCategory,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)
from app.models.production import (
    ProductionOrder,
    ProductionOrderStatus,
    ProductionPlan,
    ProductionPlanLine,
    ProductionPlanStatus,
)
from app.models.production_advanced import (
    BatchLot,
    BatchLotStatus,
    Routing,
    RoutingStep,
    WorkCenter,
    WorkCenterStatus,
    WorkCenterType,
    WorkOrder,
    WorkOrderStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus

logger = logging.getLogger(__name__)

_now = datetime.now(timezone.utc)


def _d(delta_days: int) -> datetime:
    return _now + timedelta(days=delta_days)


# ── idempotent helpers ────────────────────────────────────────────────────────


async def _get_or_create_warehouse(db: AsyncSession, code: str, **kw) -> Warehouse:
    obj = (await db.execute(select(Warehouse).where(Warehouse.code == code))).scalar_one_or_none()
    if not obj:
        obj = Warehouse(code=code, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_product(db: AsyncSession, sku: str, **kw) -> Product:
    obj = (await db.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none()
    if not obj:
        obj = Product(sku=sku, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_material(db: AsyncSession, code: str, **kw) -> Material:
    obj = (await db.execute(select(Material).where(Material.code == code))).scalar_one_or_none()
    if not obj:
        obj = Material(code=code, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_recipe(db: AsyncSession, product_id, version: str, **kw) -> Recipe:
    obj = (await db.execute(
        select(Recipe).where(Recipe.product_id == product_id, Recipe.version == version)
    )).scalar_one_or_none()
    if not obj:
        obj = Recipe(product_id=product_id, version=version, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_work_center(db: AsyncSession, wc_id: str, **kw) -> WorkCenter:
    obj = (await db.execute(
        select(WorkCenter).where(WorkCenter.work_center_id == wc_id)
    )).scalar_one_or_none()
    if not obj:
        obj = WorkCenter(work_center_id=wc_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_routing(db: AsyncSession, routing_id: str, **kw) -> Routing:
    obj = (await db.execute(
        select(Routing).where(Routing.routing_id == routing_id)
    )).scalar_one_or_none()
    if not obj:
        obj = Routing(routing_id=routing_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_plan(db: AsyncSession, plan_no: str, **kw) -> ProductionPlan:
    obj = (await db.execute(
        select(ProductionPlan).where(ProductionPlan.plan_no == plan_no)
    )).scalar_one_or_none()
    if not obj:
        obj = ProductionPlan(plan_no=plan_no, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_prod_order(db: AsyncSession, order_no: str, **kw) -> ProductionOrder:
    obj = (await db.execute(
        select(ProductionOrder).where(ProductionOrder.order_no == order_no)
    )).scalar_one_or_none()
    if not obj:
        obj = ProductionOrder(order_no=order_no, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_work_order(db: AsyncSession, wo_id: str, **kw) -> WorkOrder:
    obj = (await db.execute(
        select(WorkOrder).where(WorkOrder.work_order_id == wo_id)
    )).scalar_one_or_none()
    if not obj:
        obj = WorkOrder(work_order_id=wo_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


async def _get_or_create_batch_lot(db: AsyncSession, batch_id: str, **kw) -> BatchLot:
    obj = (await db.execute(
        select(BatchLot).where(BatchLot.batch_id == batch_id)
    )).scalar_one_or_none()
    if not obj:
        obj = BatchLot(batch_id=batch_id, **kw)
        db.add(obj)
        await db.flush()
    return obj


# ── main seed function ────────────────────────────────────────────────────────


async def seed_production_data(db: AsyncSession) -> None:
    """Seed FMCG production demo data. Idempotent — safe to run on every startup."""
    logger.info("Seeding FMCG production demo data …")

    # ── 1. Warehouses ─────────────────────────────────────────────────────────

    wh_rm = await _get_or_create_warehouse(db, "PROD-WH",
        name="Production Raw Material Store",
        warehouse_type=WarehouseType.RAW_MATERIAL,
        city="Nairobi",
        country="Kenya",
    )
    wh_fg = await _get_or_create_warehouse(db, "FG-WH",
        name="Finished Goods Warehouse",
        warehouse_type=WarehouseType.FINISHED_GOODS,
        city="Nairobi",
        country="Kenya",
    )

    # ── 2. Finished Products ──────────────────────────────────────────────────

    p_ld = await _get_or_create_product(db, "POVU-LD-1L",
        name="POVU Liquid Detergent 1L",
        category=ProductCategory.HOUSEHOLD,
        uom=UnitOfMeasure.L,
        units_per_carton=12,
        shelf_life_days=730,
        standard_cost=Decimal("85.00"),
        selling_price=Decimal("120.00"),
    )
    p_fs = await _get_or_create_product(db, "POVU-FS-500ML",
        name="POVU Fabric Softener 500ml",
        category=ProductCategory.HOUSEHOLD,
        uom=UnitOfMeasure.L,
        units_per_carton=24,
        shelf_life_days=730,
        standard_cost=Decimal("60.00"),
        selling_price=Decimal("90.00"),
    )
    p_dw = await _get_or_create_product(db, "POVU-DW-500ML",
        name="POVU Dishwashing Liquid 500ml",
        category=ProductCategory.HOUSEHOLD,
        uom=UnitOfMeasure.L,
        units_per_carton=24,
        shelf_life_days=730,
        standard_cost=Decimal("45.00"),
        selling_price=Decimal("70.00"),
    )
    p_sc = await _get_or_create_product(db, "POVU-SC-750ML",
        name="POVU Surface Cleaner 750ml",
        category=ProductCategory.HOUSEHOLD,
        uom=UnitOfMeasure.L,
        units_per_carton=12,
        shelf_life_days=730,
        standard_cost=Decimal("55.00"),
        selling_price=Decimal("80.00"),
    )
    p_hs = await _get_or_create_product(db, "POVU-HS-200ML",
        name="POVU Hand Sanitizer 200ml",
        category=ProductCategory.PERSONAL_CARE,
        uom=UnitOfMeasure.ML,
        units_per_carton=48,
        shelf_life_days=365,
        standard_cost=Decimal("35.00"),
        selling_price=Decimal("55.00"),
    )
    products = [p_ld, p_fs, p_dw, p_sc, p_hs]

    # ── 3. Raw Materials ──────────────────────────────────────────────────────

    m_surf = await _get_or_create_material(db, "RAW-SURF-LAS",
        name="LAS Surfactant Blend",
        material_type=MaterialType.RAW,
        uom=UnitOfMeasure.KG,
        standard_cost=Decimal("120.00"),
        lead_time_days=14,
    )
    m_frag = await _get_or_create_material(db, "RAW-FRAG-LAV",
        name="Lavender Fragrance Oil",
        material_type=MaterialType.RAW,
        uom=UnitOfMeasure.KG,
        standard_cost=Decimal("850.00"),
        lead_time_days=21,
    )
    m_thick = await _get_or_create_material(db, "RAW-THICK-SALT",
        name="Sodium Chloride Thickener",
        material_type=MaterialType.RAW,
        uom=UnitOfMeasure.KG,
        standard_cost=Decimal("15.00"),
        lead_time_days=7,
    )
    m_btl1l = await _get_or_create_material(db, "PKG-BTL-1L",
        name="PET Bottle 1L Clear",
        material_type=MaterialType.PACKAGING,
        uom=UnitOfMeasure.PCS,
        standard_cost=Decimal("8.50"),
        lead_time_days=10,
    )
    m_btl500 = await _get_or_create_material(db, "PKG-BTL-500",
        name="PET Bottle 500ml White",
        material_type=MaterialType.PACKAGING,
        uom=UnitOfMeasure.PCS,
        standard_cost=Decimal("5.50"),
        lead_time_days=10,
    )
    m_cap = await _get_or_create_material(db, "PKG-CAP-28",
        name="HDPE Cap 28mm",
        material_type=MaterialType.PACKAGING,
        uom=UnitOfMeasure.PCS,
        standard_cost=Decimal("1.20"),
        lead_time_days=7,
    )
    m_lbl = await _get_or_create_material(db, "PKG-LBL-ROLL",
        name="Label Stock Roll (self-adhesive)",
        material_type=MaterialType.PACKAGING,
        uom=UnitOfMeasure.PCS,
        standard_cost=Decimal("2.80"),
        lead_time_days=7,
    )

    # ── 4. Recipes (one per product, version 1.0, APPROVED) ──────────────────

    recipes: list[Recipe] = []
    # product, base_material, pkg_bottle, quantity_per_L
    recipe_defs = [
        (p_ld,  m_btl1l,  "POVU-LD-1L Recipe v1.0",  Decimal("0.700"), Decimal("1.000")),
        (p_fs,  m_btl500, "POVU-FS-500ml Recipe v1.0", Decimal("0.380"), Decimal("0.500")),
        (p_dw,  m_btl500, "POVU-DW-500ml Recipe v1.0", Decimal("0.350"), Decimal("0.500")),
        (p_sc,  m_btl500, "POVU-SC-750ml Recipe v1.0", Decimal("0.500"), Decimal("0.750")),
        (p_hs,  m_btl500, "POVU-HS-200ml Recipe v1.0", Decimal("0.180"), Decimal("0.200")),
    ]
    for prod, pkg_bottle, rname, surf_qty, pkg_qty in recipe_defs:
        r = await _get_or_create_recipe(db, prod.id, "1.0",
            name=rname,
            status=RecipeStatus.APPROVED,
            is_active=True,
            valid_from=date(2025, 1, 1),
        )
        # Only add items if recipe was just created (no items yet)
        existing_items = (await db.execute(
            select(RecipeItem).where(RecipeItem.recipe_id == r.id)
        )).scalars().all()
        if not existing_items:
            db.add(RecipeItem(recipe_id=r.id, material_id=m_surf.id,  line_no=1, quantity=surf_qty,        unit="KG",  loss_percentage=Decimal("2.0"),  is_optional=False))
            db.add(RecipeItem(recipe_id=r.id, material_id=m_frag.id,  line_no=2, quantity=Decimal("0.01"), unit="KG",  loss_percentage=Decimal("0.5"),  is_optional=False))
            db.add(RecipeItem(recipe_id=r.id, material_id=m_thick.id, line_no=3, quantity=Decimal("0.02"), unit="KG",  loss_percentage=Decimal("0.0"),  is_optional=False))
            db.add(RecipeItem(recipe_id=r.id, material_id=pkg_bottle.id, line_no=4, quantity=pkg_qty,      unit="PCS", loss_percentage=Decimal("0.5"),  is_optional=False))
            db.add(RecipeItem(recipe_id=r.id, material_id=m_cap.id,   line_no=5, quantity=pkg_qty,         unit="PCS", loss_percentage=Decimal("0.5"),  is_optional=False))
            db.add(RecipeItem(recipe_id=r.id, material_id=m_lbl.id,   line_no=6, quantity=pkg_qty,         unit="PCS", loss_percentage=Decimal("1.0"),  is_optional=False))
            await db.flush()
        recipes.append(r)

    # ── 5. Work Centres ───────────────────────────────────────────────────────

    wc_mix_a = await _get_or_create_work_center(db, "WC-MIX-01",
        name="Mixing & Blending Line A",
        type=WorkCenterType.LINE,
        capacity=Decimal("5000"),
        capacity_uom="L/hr",
        location="Building A – Bay 1",
        department="Production",
        setup_time_min=30,
        status=WorkCenterStatus.ACTIVE,
    )
    wc_mix_b = await _get_or_create_work_center(db, "WC-MIX-02",
        name="Mixing & Blending Line B",
        type=WorkCenterType.LINE,
        capacity=Decimal("3000"),
        capacity_uom="L/hr",
        location="Building A – Bay 2",
        department="Production",
        setup_time_min=30,
        status=WorkCenterStatus.ACTIVE,
    )
    wc_fill_bot = await _get_or_create_work_center(db, "WC-FILL-BOT",
        name="Bottle Filling Line",
        type=WorkCenterType.MACHINE,
        capacity=Decimal("2000"),
        capacity_uom="btl/hr",
        location="Building B – Bay 1",
        department="Production",
        setup_time_min=45,
        status=WorkCenterStatus.ACTIVE,
    )
    wc_fill_sac = await _get_or_create_work_center(db, "WC-FILL-SAC",
        name="Sachet Filling Line",
        type=WorkCenterType.MACHINE,
        capacity=Decimal("10000"),
        capacity_uom="sach/hr",
        location="Building B – Bay 2",
        department="Production",
        setup_time_min=20,
        status=WorkCenterStatus.ACTIVE,
    )
    wc_pack = await _get_or_create_work_center(db, "WC-PACK-01",
        name="Packaging & Labelling",
        type=WorkCenterType.LINE,
        capacity=Decimal("3000"),
        capacity_uom="units/hr",
        location="Building C",
        department="Production",
        setup_time_min=15,
        status=WorkCenterStatus.ACTIVE,
    )

    # ── 6. Routings + Steps (one routing per product) ─────────────────────────

    routing_defs = [
        ("RT-LD-1L",    p_ld,  wc_mix_a,   wc_fill_bot),
        ("RT-FS-500",   p_fs,  wc_mix_a,   wc_fill_bot),
        ("RT-DW-500",   p_dw,  wc_mix_b,   wc_fill_bot),
        ("RT-SC-750",   p_sc,  wc_mix_b,   wc_fill_bot),
        ("RT-HS-200",   p_hs,  wc_mix_b,   wc_fill_sac),
    ]
    routings: list[Routing] = []
    for rt_id, prod, mix_wc, fill_wc in routing_defs:
        rt = await _get_or_create_routing(db, rt_id,
            product_id=prod.id,
            version=1,
            name=f"{prod.name} Standard Routing",
            is_active=True,
        )
        # Only add steps if none exist yet
        steps = (await db.execute(
            select(RoutingStep).where(RoutingStep.routing_id == rt.id)
        )).scalars().all()
        if not steps:
            db.add(RoutingStep(routing_id=rt.id, step_number=1, operation="Mixing & Blending",   work_center_id=mix_wc.id,   standard_time_minutes=90,  setup_time_minutes=30))
            db.add(RoutingStep(routing_id=rt.id, step_number=2, operation="Filling & Capping",   work_center_id=fill_wc.id,  standard_time_minutes=60,  setup_time_minutes=45))
            db.add(RoutingStep(routing_id=rt.id, step_number=3, operation="Labelling & Packing", work_center_id=wc_pack.id,  standard_time_minutes=45,  setup_time_minutes=15))
            await db.flush()
        routings.append(rt)

    # ── 7. Production Plans ───────────────────────────────────────────────────

    plan_past = await _get_or_create_plan(db, "PP-2026-04",
        name="April 2026 Production Plan",
        status=ProductionPlanStatus.COMPLETED,
        planned_date=_d(-60),
    )
    plan_curr = await _get_or_create_plan(db, "PP-2026-06",
        name="June 2026 Production Plan",
        status=ProductionPlanStatus.IN_PROGRESS,
        planned_date=_d(0),
    )
    plan_fut = await _get_or_create_plan(db, "PP-2026-07",
        name="July 2026 Production Plan",
        status=ProductionPlanStatus.CONFIRMED,
        planned_date=_d(30),
    )

    # ── 8. Production Orders ──────────────────────────────────────────────────
    # 5 COMPLETED (past), 4 IN_PROGRESS (current), 4 PLANNED (future), 2 RELEASED

    order_specs = [
        # order_no, product_idx, recipe_idx, qty, status, start_delta, end_delta, plan, batch_prefix
        ("PO-2026-0401", 0, 0, Decimal("5000"), ProductionOrderStatus.COMPLETED,   -58, -55, plan_past, "POVU-LD-202604"),
        ("PO-2026-0402", 1, 1, Decimal("3000"), ProductionOrderStatus.COMPLETED,   -52, -50, plan_past, "POVU-FS-202604"),
        ("PO-2026-0403", 2, 2, Decimal("4000"), ProductionOrderStatus.COMPLETED,   -48, -46, plan_past, "POVU-DW-202604"),
        ("PO-2026-0404", 3, 3, Decimal("2500"), ProductionOrderStatus.COMPLETED,   -44, -42, plan_past, "POVU-SC-202604"),
        ("PO-2026-0405", 4, 4, Decimal("8000"), ProductionOrderStatus.COMPLETED,   -40, -38, plan_past, "POVU-HS-202604"),
        ("PO-2026-0601", 0, 0, Decimal("6000"), ProductionOrderStatus.IN_PROGRESS, -10,  -3, plan_curr, "POVU-LD-202606"),
        ("PO-2026-0602", 1, 1, Decimal("4000"), ProductionOrderStatus.IN_PROGRESS,  -8,  -1, plan_curr, "POVU-FS-202606"),
        ("PO-2026-0603", 2, 2, Decimal("3500"), ProductionOrderStatus.RELEASED,    -3,   4, plan_curr, None),
        ("PO-2026-0604", 3, 3, Decimal("2000"), ProductionOrderStatus.RELEASED,    -2,   5, plan_curr, None),
        ("PO-2026-0605", 4, 4, Decimal("10000"), ProductionOrderStatus.IN_PROGRESS, -5,   2, plan_curr, "POVU-HS-202606"),
        ("PO-2026-0606", 0, 0, Decimal("4500"), ProductionOrderStatus.IN_PROGRESS,  -7,   0, plan_curr, "POVU-LD-202606B"),
        ("PO-2026-0701", 0, 0, Decimal("7000"), ProductionOrderStatus.PLANNED,     10,  14, plan_fut,  None),
        ("PO-2026-0702", 1, 1, Decimal("5000"), ProductionOrderStatus.PLANNED,     12,  16, plan_fut,  None),
        ("PO-2026-0703", 2, 2, Decimal("4000"), ProductionOrderStatus.PLANNED,     15,  19, plan_fut,  None),
        ("PO-2026-0704", 3, 3, Decimal("3000"), ProductionOrderStatus.PLANNED,     20,  24, plan_fut,  None),
    ]

    prod_orders: list[tuple[ProductionOrder, str | None]] = []
    for order_no, p_idx, r_idx, qty, status, sd, ed, plan, batch_pfx in order_specs:
        po = await _get_or_create_prod_order(db, order_no,
            product_id=products[p_idx].id,
            recipe_id=recipes[r_idx].id,
            planned_quantity=qty,
            actual_quantity=qty if status == ProductionOrderStatus.COMPLETED else None,
            uom="L" if p_idx < 4 else "ML",
            status=status,
            target_warehouse_id=wh_fg.id,
            source_warehouse_id=wh_rm.id,
            scheduled_start=_d(sd),
            scheduled_end=_d(ed),
            actual_start=_d(sd) if status != ProductionOrderStatus.PLANNED else None,
            actual_end=_d(ed) if status == ProductionOrderStatus.COMPLETED else None,
            batch_no=f"BN-{order_no}",
        )
        prod_orders.append((po, batch_pfx))

    # ── 9. Work Orders (Mix / Fill / Pack per production order) ──────────────

    for i, (po, _batch_pfx) in enumerate(prod_orders):
        prod = products[order_specs[i][1]]
        rt = routings[order_specs[i][1]]
        status_str = order_specs[i][4]
        sd = order_specs[i][5]
        ed = order_specs[i][6]

        if status_str == ProductionOrderStatus.COMPLETED:
            wo_statuses = [WorkOrderStatus.COMPLETED, WorkOrderStatus.COMPLETED, WorkOrderStatus.COMPLETED]
        elif status_str == ProductionOrderStatus.IN_PROGRESS:
            wo_statuses = [WorkOrderStatus.COMPLETED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.PLANNED]
        else:
            wo_statuses = [WorkOrderStatus.PLANNED, WorkOrderStatus.PLANNED, WorkOrderStatus.PLANNED]

        wc_list = [wc_mix_a, wc_fill_bot, wc_pack]
        ops = ["Mixing & Blending", "Filling & Capping", "Labelling & Packing"]
        for step_idx in range(3):
            wo_id = f"WO-{po.order_no}-{step_idx + 1:02d}"
            await _get_or_create_work_order(db, wo_id,
                production_order_id=po.id,
                work_center_id=wc_list[step_idx].id,
                operation=ops[step_idx],
                status=wo_statuses[step_idx],
                planned_quantity=po.planned_quantity,
                planned_start=_d(sd + step_idx),
                planned_end=_d(sd + step_idx + 1),
                start_time=_d(sd + step_idx) if wo_statuses[step_idx] != WorkOrderStatus.PLANNED else None,
                end_time=_d(sd + step_idx + 1) if wo_statuses[step_idx] == WorkOrderStatus.COMPLETED else None,
            )

    # ── 10. Batch Lots (completed + in-progress orders) ───────────────────────

    today = date.today()
    for i, (po, batch_pfx) in enumerate(prod_orders):
        if batch_pfx is None:
            continue
        prod = products[order_specs[i][1]]
        status_str = order_specs[i][4]
        lot_status = (
            BatchLotStatus.RELEASED if status_str == ProductionOrderStatus.COMPLETED
            else BatchLotStatus.QUARANTINE
        )
        mfg_date = (today + timedelta(days=order_specs[i][6])).replace(day=1) if status_str == ProductionOrderStatus.COMPLETED else today
        await _get_or_create_batch_lot(db, f"{batch_pfx}-001",
            production_order_id=po.id,
            product_id=prod.id,
            product_sku=prod.sku,
            quantity=po.planned_quantity,
            uom="L" if order_specs[i][1] < 4 else "ML",
            manufacture_date=mfg_date,
            expiry_date=mfg_date.replace(year=mfg_date.year + 2),
            status=lot_status,
            warehouse_id=wh_fg.id,
        )

    await db.commit()
    logger.info(
        "Production seed complete: 2 warehouses, 5 products, 7 materials, "
        "5 recipes, 5 work centres, 5 routings, 3 plans, %d orders, work orders, batch lots",
        len(prod_orders),
    )
