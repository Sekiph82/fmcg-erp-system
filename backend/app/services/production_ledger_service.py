"""Production ↔ warehouses ↔ ledger (M39, owner 2026-11-20).

Warehouse links: which warehouse holds raw materials, packaging, semi-finished goods (WIP) and finished goods ready
to ship. A production order's own source/target warehouses win; the links fill the gaps and route packaging and
semi-finished materials to their own warehouse at completion. Stored in system_configs (no schema change).

Ledger: when a production order completes, one journal books the stock flow at cost
  Dr Work in progress        / Cr Raw-material inventory      (raw + consumables, standard cost × qty consumed)
  Dr Work in progress        / Cr Packaging inventory         (packaging; falls back to the raw-material rule)
  Dr Work in progress        / Cr Semi-finished inventory     (semi-finished; falls back to the raw-material rule)
  Dr Work in progress        / Cr Applied labour & overhead   (labour, machine and energy cost of the order)
  Dr Finished-goods inventory / Cr Work in progress           (everything above: finished goods at actual cost)
Rules (finance → posting rules, module "production"): RAW_MATERIAL_ISSUE and FINISHED_GOODS_RECEIPT are needed;
PACKAGING_ISSUE, SEMI_FINISHED_ISSUE and CONVERSION_APPLIED are optional. Without the two needed rules nothing is
posted and it is logged, like the other operational postings.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

from app.models.master import MaterialType, Warehouse

log = logging.getLogger(__name__)

LINK_KEYS = {
    "raw_material_warehouse_id": "production.raw_material_warehouse_id",
    "packaging_warehouse_id": "production.packaging_warehouse_id",
    "wip_warehouse_id": "production.wip_warehouse_id",
    "finished_goods_warehouse_id": "production.finished_goods_warehouse_id",
}


async def get_warehouse_links(db) -> dict[str, Optional[uuid.UUID]]:
    from app.models.utilities import SystemConfig

    rows = {c.key: c.value for c in (await db.execute(
        select(SystemConfig).where(SystemConfig.key.in_(list(LINK_KEYS.values()))))).scalars()}
    out: dict[str, Optional[uuid.UUID]] = {}
    for name, key in LINK_KEYS.items():
        try:
            out[name] = uuid.UUID(rows[key]) if rows.get(key) else None
        except ValueError:
            out[name] = None
    return out


async def set_warehouse_links(db, data: dict, user_id) -> dict[str, Optional[uuid.UUID]]:
    from app.models.utilities import ConfigCategory, SystemConfig

    unknown = set(data) - set(LINK_KEYS)
    if unknown:
        raise HTTPException(422, f"Unknown warehouse links: {', '.join(sorted(unknown))}")
    for name, value in data.items():
        try:
            wh_id = uuid.UUID(str(value)) if value else None
        except ValueError:
            raise HTTPException(422, f"{name}: not a warehouse id") from None
        if wh_id is not None:
            wh = await db.get(Warehouse, wh_id)
            if wh is None or not wh.is_active:
                raise HTTPException(422, f"{name}: warehouse not found or inactive")
        key = LINK_KEYS[name]
        cfg = (await db.execute(select(SystemConfig).where(SystemConfig.key == key))).scalar_one_or_none()
        if cfg is None:
            cfg = SystemConfig(key=key, category=ConfigCategory.OPERATIONS,
                               description=f"Production warehouse link: {name.replace('_', ' ')}")
            db.add(cfg)
        cfg.value = str(wh_id) if wh_id else None
        cfg.updated_by_id = user_id
    await db.flush()
    return await get_warehouse_links(db)


def material_warehouse(material_type, source_wh_id, links: dict) -> Optional[uuid.UUID]:
    """Packaging comes from the packaging warehouse, semi-finished goods from the WIP warehouse, the rest from source."""
    if material_type == MaterialType.PACKAGING and links.get("packaging_warehouse_id"):
        return links["packaging_warehouse_id"]
    if material_type == MaterialType.SEMI_FINISHED and links.get("wip_warehouse_id"):
        return links["wip_warehouse_id"]
    return source_wh_id


async def _rule(db, event: str):
    from app.models.finance import AccountingPostingRule

    return (await db.execute(select(AccountingPostingRule).where(
        AccountingPostingRule.source_module == "production", AccountingPostingRule.source_event == event,
        AccountingPostingRule.is_active.is_(True)).order_by(AccountingPostingRule.priority).limit(1))).scalar_one_or_none()


async def material_cost_by_type(db, order_id) -> dict:
    """Standard cost × quantity consumed per material type: recipe auto-consumption and reserved (dispensed) issues."""
    from app.models.material_flow import ProductionConsumption
    from app.models.master import Material
    from app.models.production import MaterialConsumption

    totals: dict = {}
    rows = (await db.execute(select(MaterialConsumption.actual_quantity, Material.standard_cost, Material.material_type)
                             .join(Material, MaterialConsumption.material_id == Material.id)
                             .where(MaterialConsumption.production_order_id == order_id))).all()
    rows += (await db.execute(select(ProductionConsumption.quantity_consumed, Material.standard_cost, Material.material_type)
                              .join(Material, ProductionConsumption.material_id == Material.id)
                              .where(ProductionConsumption.production_order_id == order_id,
                                     ProductionConsumption.quantity_consumed > 0))).all()
    for qty, cost, mtype in rows:
        totals[mtype] = totals.get(mtype, Decimal("0")) + Decimal(qty or 0) * Decimal(cost or 0)
    return {k: v.quantize(Decimal("0.01")) for k, v in totals.items()}


async def post_production_completion(db, order, user_id):
    """Book a completed production order (see module docstring). Returns the journal or None."""
    from app.models.finance import AccountType
    from app.services.production_cost_service import compute_order_cost
    from app.services.sales_service import _post_sales_journal, _require_sales_account_types

    raw_rule, fg_rule = await _rule(db, "RAW_MATERIAL_ISSUE"), await _rule(db, "FINISHED_GOODS_RECEIPT")
    if raw_rule is None or fg_rule is None:
        log.warning("production order %s completed without GL entry: production posting rules missing", order.id)
        return None
    by_type = await material_cost_by_type(db, order.id)
    cost = await compute_order_cost(db, order)
    conversion = (Decimal(str(cost["total_labor_cost"])) + Decimal(str(cost["total_machine_cost"]))
                  + Decimal(str(cost["total_energy_cost"]))).quantize(Decimal("0.01"))

    issue_rules = {MaterialType.PACKAGING: await _rule(db, "PACKAGING_ISSUE") or raw_rule,
                   MaterialType.SEMI_FINISHED: await _rule(db, "SEMI_FINISHED_ISSUE") or raw_rule}
    debit_lines, credit_lines, checks = [], [], []
    labels = {MaterialType.RAW: "Raw materials", MaterialType.CONSUMABLE: "Consumables",
              MaterialType.PACKAGING: "Packaging", MaterialType.SEMI_FINISHED: "Semi-finished goods"}
    for mtype, amount in by_type.items():
        if amount <= 0:
            continue
        rule = issue_rules.get(mtype, raw_rule)
        if not rule.debit_account_id or not rule.credit_account_id:
            raise HTTPException(422, f"The production rule {rule.source_event} needs the WIP and inventory accounts.")
        debit_lines.append((rule.debit_account_id, amount, f"{labels.get(mtype, 'Materials')} to WIP"))
        credit_lines.append((rule.credit_account_id, amount, f"{labels.get(mtype, 'Materials')} issued"))
        checks += [(rule.debit_account_id, AccountType.ASSET, "work in progress"),
                   (rule.credit_account_id, AccountType.ASSET, "inventory")]
    if conversion > 0:
        conv_rule = await _rule(db, "CONVERSION_APPLIED")
        if conv_rule is None:
            log.warning("production order %s: conversion cost %s not booked (no CONVERSION_APPLIED rule)", order.id, conversion)
            conversion = Decimal("0")
        elif not conv_rule.debit_account_id or not conv_rule.credit_account_id:
            raise HTTPException(422, "The production rule CONVERSION_APPLIED needs the WIP and applied-overhead accounts.")
        else:
            debit_lines.append((conv_rule.debit_account_id, conversion, "Labour, machine and energy to WIP"))
            credit_lines.append((conv_rule.credit_account_id, conversion, "Production overhead applied"))
    total = sum((a for _, a, _ in debit_lines), Decimal("0"))
    if total <= 0:
        return None
    if not fg_rule.debit_account_id or not fg_rule.credit_account_id:
        raise HTTPException(422, "The production rule FINISHED_GOODS_RECEIPT needs the finished-goods and WIP accounts.")
    checks += [(fg_rule.debit_account_id, AccountType.ASSET, "finished-goods inventory"),
               (fg_rule.credit_account_id, AccountType.ASSET, "work in progress")]
    await _require_sales_account_types(db, checks)
    debit_lines.append((fg_rule.debit_account_id, total, f"Finished goods {order.order_no}"))
    credit_lines.append((fg_rule.credit_account_id, total, "WIP to finished goods"))
    return await _post_sales_journal(
        db, source_event="PRODUCTION_COMPLETED", source_id=order.id, source_ref=order.order_no, entry_date=date.today(),
        description=f"Production {order.order_no}: materials and conversion to finished goods", amount=total,
        currency="KES", debit_lines=debit_lines, credit_lines=credit_lines, user_id=user_id,
        source_module="production", entry_prefix="AUTO-PRD")
