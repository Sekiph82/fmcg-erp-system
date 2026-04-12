"""
Barcode generation and scanning service.

Generation: Produces a unique barcode value + minimal SVG rendering hint.
Scanning: Looks up the associated entity (product, lot, location, material) by barcode value.
Printing: Returns a print job record (placeholder — integrate with label printer SDK).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import BarcodeLabel, BarcodeFormat
from app.models.master import Product, Material, Warehouse
from app.models.inventory import Lot


# ── Barcode value generation ──────────────────────────────────────────────────

def _generate_barcode_value(entity_type: str, entity_id: str) -> str:
    """
    Generate a deterministic, unique barcode value.
    Format: <TYPE_PREFIX>-<SHORT_UUID>
    Prefixes: PRD, LOT, LOC, MAT
    """
    prefix_map = {
        "PRODUCT": "PRD",
        "LOT": "LOT",
        "LOCATION": "LOC",
        "MATERIAL": "MAT",
    }
    prefix = prefix_map.get(entity_type.upper(), "ENT")
    # Use the first 12 hex chars of the entity UUID for compactness
    short = entity_id.replace("-", "")[:12].upper()
    return f"{prefix}{short}"


def _build_svg(barcode_value: str) -> str:
    """
    Generate a minimal CODE128-style SVG barcode for UI rendering.
    Uses a simple bar-width encoding based on character codes.
    This is a visual approximation suitable for display; for production printing
    replace with a proper CODE128 library or label printer SDK output.
    """
    bar_width = 2
    space_width = 2
    height = 60
    quiet_zone = 10

    bars: list[tuple[bool, int]] = []
    for char in barcode_value:
        code = ord(char)
        # Encode each character as 9 alternating bars/spaces (simplified)
        bits = format(code & 0x7F, "07b")
        for bit in bits:
            bars.append((bit == "1", bar_width if bit == "1" else space_width))

    total_width = quiet_zone * 2 + sum(w for _, w in bars)
    rects = []
    x = quiet_zone
    for is_bar, width in bars:
        if is_bar:
            rects.append(f'<rect x="{x}" y="0" width="{width}" height="{height}" fill="#000"/>')
        x += width

    text_y = height + 14
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height + 20}" '
        f'viewBox="0 0 {total_width} {height + 20}">'
        f'<rect width="{total_width}" height="{height + 20}" fill="white"/>'
        + "".join(rects)
        + f'<text x="{total_width // 2}" y="{text_y}" text-anchor="middle" '
        f'font-family="monospace" font-size="10">{barcode_value}</text>'
        f"</svg>"
    )
    return svg


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_barcode(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    barcode_format: BarcodeFormat = BarcodeFormat.CODE128,
    label_template: str = "standard",
) -> BarcodeLabel:
    """
    Get or create a BarcodeLabel for the given entity.
    Idempotent: returns the existing label if one already exists.
    """
    entity_uuid = uuid.UUID(entity_id)

    # Check for existing
    existing = await db.execute(
        select(BarcodeLabel).where(
            BarcodeLabel.entity_type == entity_type.upper(),
            BarcodeLabel.entity_id == entity_uuid,
        )
    )
    label = existing.scalar_one_or_none()
    if label:
        return label

    # Resolve entity name for label printing
    entity_name = await _resolve_entity_name(db, entity_type.upper(), entity_uuid)

    barcode_value = _generate_barcode_value(entity_type, entity_id)

    label = BarcodeLabel(
        entity_type=entity_type.upper(),
        entity_id=entity_uuid,
        entity_name=entity_name,
        barcode_value=barcode_value,
        barcode_format=barcode_format,
        label_template=label_template,
    )
    db.add(label)
    await db.flush()
    await db.refresh(label)
    return label


async def scan_barcode(
    db: AsyncSession,
    barcode_value: str,
) -> Optional[Dict[str, Any]]:
    """
    Look up entity by barcode value and return contextual data.
    Returns None if barcode not found.
    """
    result = await db.execute(
        select(BarcodeLabel).where(BarcodeLabel.barcode_value == barcode_value)
    )
    label = result.scalar_one_or_none()
    if not label:
        return None

    details = await _fetch_entity_details(db, label.entity_type, label.entity_id)
    return {
        "barcode_value": label.barcode_value,
        "entity_type": label.entity_type,
        "entity_id": str(label.entity_id),
        "entity_name": label.entity_name,
        "details": details,
    }


async def record_print(db: AsyncSession, label: BarcodeLabel) -> BarcodeLabel:
    """Increment print counter and record timestamp."""
    label.print_count += 1
    label.last_printed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(label)
    return label


async def get_label(db: AsyncSession, label_id: uuid.UUID) -> Optional[BarcodeLabel]:
    result = await db.execute(select(BarcodeLabel).where(BarcodeLabel.id == label_id))
    return result.scalar_one_or_none()


async def get_label_by_barcode(db: AsyncSession, barcode_value: str) -> Optional[BarcodeLabel]:
    result = await db.execute(select(BarcodeLabel).where(BarcodeLabel.barcode_value == barcode_value))
    return result.scalar_one_or_none()


async def list_labels(db: AsyncSession, entity_type: Optional[str] = None, limit: int = 100) -> list:
    q = select(BarcodeLabel).order_by(BarcodeLabel.created_at.desc())
    if entity_type:
        q = q.where(BarcodeLabel.entity_type == entity_type.upper())
    result = await db.execute(q.limit(limit))
    return list(result.scalars().all())


# ── Private helpers ───────────────────────────────────────────────────────────

async def _resolve_entity_name(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> Optional[str]:
    if entity_type == "PRODUCT":
        r = await db.execute(select(Product.name).where(Product.id == entity_id))
        return r.scalar_one_or_none()
    if entity_type == "MATERIAL":
        r = await db.execute(select(Material.name).where(Material.id == entity_id))
        return r.scalar_one_or_none()
    if entity_type == "LOT":
        r = await db.execute(select(Lot.lot_number).where(Lot.id == entity_id))
        return r.scalar_one_or_none()
    if entity_type == "LOCATION":
        r = await db.execute(select(Warehouse.name).where(Warehouse.id == entity_id))
        return r.scalar_one_or_none()
    return None


async def _fetch_entity_details(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> Dict[str, Any]:
    if entity_type == "PRODUCT":
        r = await db.execute(
            select(Product.name, Product.sku, Product.barcode, Product.standard_cost, Product.reorder_point)
            .where(Product.id == entity_id)
        )
        row = r.one_or_none()
        if row:
            return {"name": row[0], "sku": row[1], "barcode": row[2],
                    "standard_cost": float(row[3]) if row[3] else None,
                    "reorder_point": float(row[4]) if row[4] else None}
    if entity_type == "MATERIAL":
        r = await db.execute(
            select(Material.name, Material.code, Material.uom, Material.reorder_point)
            .where(Material.id == entity_id)
        )
        row = r.one_or_none()
        if row:
            return {"name": row[0], "code": row[1], "uom": str(row[2]), "reorder_point": float(row[3]) if row[3] else None}
    if entity_type == "LOT":
        r = await db.execute(
            select(Lot.lot_number, Lot.batch_number, Lot.expiry_date, Lot.is_quarantine)
            .where(Lot.id == entity_id)
        )
        row = r.one_or_none()
        if row:
            return {"lot_number": row[0], "batch_number": row[1],
                    "expiry_date": str(row[2]) if row[2] else None,
                    "is_quarantine": row[3]}
    if entity_type == "LOCATION":
        r = await db.execute(
            select(Warehouse.name, Warehouse.code, Warehouse.warehouse_type)
            .where(Warehouse.id == entity_id)
        )
        row = r.one_or_none()
        if row:
            return {"name": row[0], "code": row[1], "type": str(row[2])}
    return {}
