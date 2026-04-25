"""GS1 Barcode + Label Printing Service — check digits, AI strings, SSCC, images."""
from __future__ import annotations

import base64
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gs1 import (
    GS1CompanyConfig, ProductGS1Config, LotBarcodeRecord,
    SSCCPallet, SSCCPalletLot, GS1LabelTemplate, LabelPrintJob,
    LabelPrintJobItem, GS1AIRecommendation,
    BarcodeType, PackagingLevel, PrintJobStatus, SSCCStatus,
    LabelTemplateStatus, PrintTrigger, GS1AIAgentType, GS1AIRecStatus,
)
from app.models.inventory import Lot
from app.models.master import Product


# ── Check Digit Helpers ───────────────────────────────────────────────────────

def _gs1_check_digit(digits: str) -> int:
    """GS1 standard mod-10 check digit. Input: N-1 digit string."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        w = 3 if i % 2 == 0 else 1
        total += int(ch) * w
    return (10 - (total % 10)) % 10


def compute_ean13_check(ean12: str) -> str:
    if len(ean12) != 12 or not ean12.isdigit():
        raise ValueError("EAN-12 must be 12 numeric digits")
    return ean12 + str(_gs1_check_digit(ean12))


def compute_gtin14_check(gtin13: str) -> str:
    if len(gtin13) != 13 or not gtin13.isdigit():
        raise ValueError("GTIN-13 must be 13 numeric digits")
    return gtin13 + str(_gs1_check_digit(gtin13))


def validate_gtin(gtin: str) -> bool:
    if not gtin.isdigit() or len(gtin) not in (8, 12, 13, 14):
        return False
    return _gs1_check_digit(gtin[:-1]) == int(gtin[-1])


def compute_sscc_check(sscc17: str) -> int:
    if len(sscc17) != 17 or not sscc17.isdigit():
        raise ValueError("SSCC prefix must be 17 numeric digits")
    return _gs1_check_digit(sscc17)


# ── GS1 AI String Builder ─────────────────────────────────────────────────────

def _fmt_date(d: Optional[date]) -> Optional[str]:
    return d.strftime("%y%m%d") if d else None


def build_gs1_ai_string(
    gtin: str,
    lot_number: Optional[str] = None,
    expiry_date: Optional[date] = None,
    production_date: Optional[date] = None,
    serial_number: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (human_readable, raw_scannable) GS1 AI string."""
    hr_parts: List[str] = []
    raw_parts: List[str] = []

    hr_parts.append(f"(01){gtin}")
    raw_parts.append(f"\x1d01{gtin}")

    if lot_number:
        hr_parts.append(f"(10){lot_number}")
        raw_parts.append(f"\x1d10{lot_number}")

    if expiry_date:
        ed = _fmt_date(expiry_date)
        hr_parts.append(f"(17){ed}")
        raw_parts.append(f"\x1d17{ed}")

    if production_date:
        pd = _fmt_date(production_date)
        hr_parts.append(f"(11){pd}")
        raw_parts.append(f"\x1d11{pd}")

    if serial_number:
        hr_parts.append(f"(21){serial_number}")
        raw_parts.append(f"\x1d21{serial_number}")

    return "".join(hr_parts), "".join(raw_parts)


def build_sscc_gs1_string(sscc_code: str) -> Tuple[str, str]:
    return f"(00){sscc_code}", f"\x1d00{sscc_code}"


# ── GS1 String Parser ─────────────────────────────────────────────────────────

_AI_LENGTHS: Dict[str, int] = {
    "00": 18, "01": 14, "02": 14,
    "10": -1, "11": 6, "13": 6, "15": 6, "17": 6,
    "20": 2, "21": -1, "22": -1,
    "30": -1, "310": 6, "311": 6,
    "37": -1,
}

def parse_gs1_string(gs1_str: str) -> Dict[str, str]:
    """Parse a GS1 string (human-readable with parens or FNC1-separated)."""
    result: Dict[str, str] = {}
    s = gs1_str.strip()

    if "(" in s:
        # human-readable: (AI)VALUE(AI)VALUE...
        import re
        parts = re.split(r"\((\d{2,4})\)", s)
        parts = [p for p in parts if p]
        i = 0
        while i < len(parts) - 1:
            ai = parts[i]
            val = parts[i + 1]
            result[ai] = val.split("(")[0].strip()
            i += 2
    else:
        # strip FNC1 chars
        s = s.replace("\x1d", "")
        pos = 0
        while pos < len(s):
            found = False
            for ai_len in (4, 3, 2):
                if pos + ai_len > len(s):
                    continue
                ai = s[pos: pos + ai_len]
                if ai in _AI_LENGTHS:
                    vlen = _AI_LENGTHS[ai]
                    pos += ai_len
                    if vlen == -1:
                        end = s.find("\x1d", pos)
                        val = s[pos:] if end == -1 else s[pos:end]
                        pos = end + 1 if end != -1 else len(s)
                    else:
                        val = s[pos: pos + vlen]
                        pos += vlen
                    result[ai] = val
                    found = True
                    break
            if not found:
                break

    return result


# ── SSCC Generator ────────────────────────────────────────────────────────────

async def generate_sscc(
    db: AsyncSession,
    config: GS1CompanyConfig,
) -> Tuple[str, str, str, int]:
    """Increment SSCC counter and return (sscc_code, extension, serial_ref, check)."""
    config.sscc_serial_counter += 1
    await db.flush()
    serial = str(config.sscc_serial_counter).zfill(9)
    prefix = config.gs1_company_prefix.ljust(7, "0")[:7]
    ext = str(config.extension_digit)
    sscc17 = ext + prefix + serial
    check = compute_sscc_check(sscc17)
    sscc_code = sscc17 + str(check)
    return sscc_code, ext, serial, check


# ── Barcode Image Generation ──────────────────────────────────────────────────

def _generate_barcode_b64(value: str, barcode_type: str) -> Optional[str]:
    try:
        import barcode as bc
        from barcode.writer import SVGWriter
        buf = io.BytesIO()
        if barcode_type == "EAN13" and len(value) >= 12:
            cls = bc.get_barcode_class("ean13")
            b = cls(value[:12], writer=SVGWriter())
            b.write(buf)
            return base64.b64encode(buf.getvalue()).decode()
        else:
            cls = bc.get_barcode_class("code128")
            b = cls(value, writer=SVGWriter())
            b.write(buf)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return _generate_svg_barcode(value)


def _generate_qr_b64(payload: str) -> Optional[str]:
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _generate_svg_barcode(value: str) -> str:
    """Minimal SVG barcode representation for display when python-barcode not available."""
    bars = []
    x = 10
    for i, ch in enumerate(value):
        w = 2 if int(ch) % 2 == 0 else 3
        if i % 2 == 0:
            bars.append(f'<rect x="{x}" y="10" width="{w}" height="60" fill="black"/>')
        x += w + 1
    total_w = x + 10
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="80">'
        f'<rect width="{total_w}" height="80" fill="white"/>'
        + "".join(bars)
        + f'<text x="{total_w//2}" y="78" text-anchor="middle" font-size="9">{value}</text>'
        + "</svg>"
    )
    return base64.b64encode(svg.encode()).decode()


# ── Sequence Helper ───────────────────────────────────────────────────────────

async def _next_job_no(db: AsyncSession) -> str:
    r = await db.execute(select(func.count()).select_from(LabelPrintJob))
    count = r.scalar() or 0
    return f"LPJ-{str(count + 1).zfill(6)}"


# ── Company Config CRUD ───────────────────────────────────────────────────────

async def create_company_config(db: AsyncSession, data: dict) -> GS1CompanyConfig:
    cfg = GS1CompanyConfig(**data)
    db.add(cfg)
    await db.flush()
    return cfg


async def get_company_config(db: AsyncSession, cfg_id: uuid.UUID) -> Optional[GS1CompanyConfig]:
    r = await db.execute(select(GS1CompanyConfig).where(GS1CompanyConfig.id == cfg_id))
    return r.scalar_one_or_none()


async def list_company_configs(db: AsyncSession) -> List[GS1CompanyConfig]:
    r = await db.execute(select(GS1CompanyConfig).order_by(GS1CompanyConfig.company_name))
    return list(r.scalars())


async def get_active_config(db: AsyncSession) -> Optional[GS1CompanyConfig]:
    r = await db.execute(
        select(GS1CompanyConfig).where(GS1CompanyConfig.is_active == True).limit(1)
    )
    return r.scalar_one_or_none()


# ── Product GS1 Config CRUD ───────────────────────────────────────────────────

async def create_product_config(db: AsyncSession, data: dict) -> ProductGS1Config:
    cfg = ProductGS1Config(**data)
    db.add(cfg)
    await db.flush()
    return cfg


async def get_product_config(db: AsyncSession, cfg_id: uuid.UUID) -> Optional[ProductGS1Config]:
    r = await db.execute(select(ProductGS1Config).where(ProductGS1Config.id == cfg_id))
    return r.scalar_one_or_none()


async def get_product_config_by_product(db: AsyncSession, product_id: uuid.UUID) -> Optional[ProductGS1Config]:
    r = await db.execute(
        select(ProductGS1Config).where(ProductGS1Config.product_id == product_id)
    )
    return r.scalar_one_or_none()


async def list_product_configs(db: AsyncSession) -> List[dict]:
    r = await db.execute(
        select(ProductGS1Config, Product.name.label("product_name"))
        .join(Product, ProductGS1Config.product_id == Product.id)
        .order_by(Product.name)
    )
    rows = r.all()
    result = []
    for cfg, pname in rows:
        d = {c.name: getattr(cfg, c.name) for c in cfg.__table__.columns}
        d["product_name"] = pname
        result.append(d)
    return result


async def update_product_config(db: AsyncSession, cfg_id: uuid.UUID, data: dict) -> Optional[ProductGS1Config]:
    cfg = await get_product_config(db, cfg_id)
    if not cfg:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(cfg, k, v)
    return cfg


# ── Barcode Generation ────────────────────────────────────────────────────────

async def generate_barcode(
    db: AsyncSession,
    gtin: str,
    lot_number: Optional[str] = None,
    expiry_date: Optional[date] = None,
    production_date: Optional[date] = None,
    serial_number: Optional[str] = None,
    barcode_type: str = "GS1_128",
    lot_id: Optional[uuid.UUID] = None,
    product_config_id: Optional[uuid.UUID] = None,
    quantity: Optional[Decimal] = None,
    packaging_level: Optional[str] = None,
    save_record: bool = True,
) -> dict:
    hr_string, raw_string = build_gs1_ai_string(
        gtin, lot_number, expiry_date, production_date, serial_number
    )
    qr_payload = hr_string

    barcode_img = _generate_barcode_b64(
        gtin if barcode_type == "EAN13" else hr_string.replace("(", "").replace(")", ""),
        barcode_type,
    )
    qr_img = _generate_qr_b64(qr_payload)

    record_id = None
    if save_record and product_config_id:
        rec = LotBarcodeRecord(
            product_config_id=product_config_id,
            lot_id=lot_id,
            gtin=gtin,
            lot_number=lot_number or "",
            production_date=production_date,
            expiry_date=expiry_date,
            serial_number=serial_number,
            barcode_type=barcode_type,
            gs1_ai_string=hr_string,
            gs1_raw_string=raw_string,
            qr_payload=qr_payload,
            barcode_image_b64=barcode_img,
            qr_image_b64=qr_img,
            quantity=quantity,
            packaging_level=packaging_level,
        )
        db.add(rec)
        await db.flush()
        record_id = rec.id

    return {
        "gs1_ai_string": hr_string,
        "gs1_raw_string": raw_string,
        "qr_payload": qr_payload,
        "barcode_image_b64": barcode_img,
        "qr_image_b64": qr_img,
        "check_digit_valid": validate_gtin(gtin),
        "record_id": record_id,
        "gtin": gtin,
        "lot_number": lot_number,
        "expiry_date": expiry_date,
        "production_date": production_date,
    }


async def list_lot_barcodes(
    db: AsyncSession,
    product_config_id: Optional[uuid.UUID] = None,
    lot_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[LotBarcodeRecord]:
    q = select(LotBarcodeRecord)
    if product_config_id:
        q = q.where(LotBarcodeRecord.product_config_id == product_config_id)
    if lot_id:
        q = q.where(LotBarcodeRecord.lot_id == lot_id)
    q = q.order_by(LotBarcodeRecord.created_at.desc()).limit(limit).offset(offset)
    r = await db.execute(q)
    return list(r.scalars())


# ── SSCC Pallet Management ────────────────────────────────────────────────────

async def create_sscc_pallet(
    db: AsyncSession,
    company_config_id: Optional[uuid.UUID] = None,
    pallet_id: Optional[str] = None,
    warehouse_location: Optional[str] = None,
    notes: Optional[str] = None,
) -> SSCCPallet:
    config = None
    if company_config_id:
        config = await get_company_config(db, company_config_id)
    if not config:
        config = await get_active_config(db)
    if not config:
        config = GS1CompanyConfig(
            company_name="Default",
            gs1_company_prefix="0000000",
        )
        db.add(config)
        await db.flush()

    sscc_code, ext, serial, check = await generate_sscc(db, config)
    sscc_img = _generate_barcode_b64(sscc_code, "GS1_128")

    pallet = SSCCPallet(
        company_config_id=config.id,
        sscc_code=sscc_code,
        extension_digit=int(ext),
        company_prefix=config.gs1_company_prefix,
        serial_reference=serial,
        check_digit=check,
        pallet_id=pallet_id or f"PLT-{sscc_code[-6:]}",
        status=SSCCStatus.ACTIVE,
        warehouse_location=warehouse_location,
        sscc_image_b64=sscc_img,
        notes=notes,
    )
    db.add(pallet)
    await db.flush()
    return pallet


async def get_sscc_pallet(db: AsyncSession, sscc_id: uuid.UUID) -> Optional[SSCCPallet]:
    r = await db.execute(select(SSCCPallet).where(SSCCPallet.id == sscc_id))
    return r.scalar_one_or_none()


async def list_sscc_pallets(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[SSCCPallet]:
    q = select(SSCCPallet)
    if status:
        q = q.where(SSCCPallet.status == status)
    q = q.order_by(SSCCPallet.created_at.desc()).limit(limit).offset(offset)
    r = await db.execute(q)
    return list(r.scalars())


async def add_lot_to_sscc(
    db: AsyncSession,
    sscc_id: uuid.UUID,
    lot_barcode_id: uuid.UUID,
    quantity: Optional[Decimal] = None,
    packaging_level: Optional[str] = None,
) -> SSCCPalletLot:
    link = SSCCPalletLot(
        sscc_id=sscc_id,
        lot_barcode_id=lot_barcode_id,
        quantity=quantity,
        packaging_level=packaging_level,
    )
    db.add(link)
    await db.flush()
    return link


async def get_sscc_lot_count(db: AsyncSession, sscc_id: uuid.UUID) -> int:
    r = await db.execute(
        select(func.count()).select_from(SSCCPalletLot).where(SSCCPalletLot.sscc_id == sscc_id)
    )
    return r.scalar() or 0


# ── Label Template CRUD ───────────────────────────────────────────────────────

async def create_label_template(db: AsyncSession, data: dict) -> GS1LabelTemplate:
    t = GS1LabelTemplate(**data)
    db.add(t)
    await db.flush()
    return t


async def get_label_template(db: AsyncSession, tmpl_id: uuid.UUID) -> Optional[GS1LabelTemplate]:
    r = await db.execute(select(GS1LabelTemplate).where(GS1LabelTemplate.id == tmpl_id))
    return r.scalar_one_or_none()


async def list_label_templates(
    db: AsyncSession,
    packaging_level: Optional[str] = None,
    active_only: bool = True,
) -> List[GS1LabelTemplate]:
    q = select(GS1LabelTemplate)
    if active_only:
        q = q.where(GS1LabelTemplate.is_active == True)
    if packaging_level:
        q = q.where(GS1LabelTemplate.packaging_level == packaging_level)
    r = await db.execute(q.order_by(GS1LabelTemplate.name))
    return list(r.scalars())


async def update_label_template(
    db: AsyncSession, tmpl_id: uuid.UUID, data: dict
) -> Optional[GS1LabelTemplate]:
    t = await get_label_template(db, tmpl_id)
    if not t:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(t, k, v)
    t.template_version += 1
    return t


# ── Print Job ─────────────────────────────────────────────────────────────────

async def create_print_job(db: AsyncSession, data: dict) -> LabelPrintJob:
    items_data = data.pop("items", [])
    job_no = await _next_job_no(db)
    job = LabelPrintJob(job_no=job_no, quantity=len(items_data) or 1, **data)
    db.add(job)
    await db.flush()

    for item in items_data:
        ji = LabelPrintJobItem(job_id=job.id, **item)
        db.add(ji)

    return job


async def complete_print_job(db: AsyncSession, job_id: uuid.UUID, printed_by: str) -> Optional[LabelPrintJob]:
    r = await db.execute(select(LabelPrintJob).where(LabelPrintJob.id == job_id))
    job = r.scalar_one_or_none()
    if not job:
        return None
    job.status = PrintJobStatus.COMPLETED
    job.printed_by = printed_by
    job.printed_at = datetime.now(timezone.utc)
    for item in job.items:
        item.status = PrintJobStatus.COMPLETED
    return job


async def list_print_jobs(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[LabelPrintJob]:
    q = select(LabelPrintJob)
    if status:
        q = q.where(LabelPrintJob.status == status)
    q = q.order_by(LabelPrintJob.created_at.desc()).limit(limit).offset(offset)
    r = await db.execute(q)
    return list(r.scalars())


# ── GS1 Decode / Scan ─────────────────────────────────────────────────────────

async def decode_and_validate(db: AsyncSession, gs1_string: str) -> dict:
    segments = parse_gs1_string(gs1_string)
    errors: List[str] = []

    gtin = segments.get("01")
    lot  = segments.get("10")
    exp  = segments.get("17")
    prod = segments.get("11")
    ser  = segments.get("21")
    sscc = segments.get("00")

    if gtin and not validate_gtin(gtin):
        errors.append(f"GTIN check digit invalid: {gtin}")

    matched_product = None
    matched_lot = None

    if gtin:
        rp = await db.execute(
            select(ProductGS1Config, Product.name.label("pname"))
            .join(Product, ProductGS1Config.product_id == Product.id)
            .where(ProductGS1Config.gtin == gtin)
        )
        row = rp.first()
        if row:
            cfg, pname = row
            matched_product = {"product_id": str(cfg.product_id), "product_name": pname, "gtin": gtin}
        else:
            errors.append(f"GTIN {gtin} not found in system")

    if lot:
        rl = await db.execute(select(Lot).where(Lot.lot_number == lot).limit(1))
        lot_obj = rl.scalar_one_or_none()
        if lot_obj:
            if lot_obj.expiry_date:
                from datetime import date as date_type
                today = date_type.today()
                if lot_obj.expiry_date < today:
                    errors.append(f"Lot {lot} is expired (expiry: {lot_obj.expiry_date})")
            matched_lot = {
                "lot_id": str(lot_obj.id),
                "lot_number": lot_obj.lot_number,
                "expiry_date": str(lot_obj.expiry_date) if lot_obj.expiry_date else None,
            }
        else:
            errors.append(f"Lot {lot} not found in system")

    return {
        "segments": segments,
        "gtin": gtin,
        "lot_number": lot,
        "expiry_date": exp,
        "production_date": prod,
        "serial_number": ser,
        "sscc": sscc,
        "is_valid": len(errors) == 0,
        "validation_errors": errors,
        "matched_product": matched_product,
        "matched_lot": matched_lot,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    async def _count(model, *filters):
        q = select(func.count()).select_from(model)
        for f in filters:
            q = q.where(f)
        r = await db.execute(q)
        return r.scalar() or 0

    total_configs    = await _count(ProductGS1Config)
    total_barcodes   = await _count(LotBarcodeRecord)
    printed          = await _count(LotBarcodeRecord, LotBarcodeRecord.is_printed == True)
    total_sscc       = await _count(SSCCPallet)
    active_sscc      = await _count(SSCCPallet, SSCCPallet.status == SSCCStatus.ACTIVE)
    total_jobs       = await _count(LabelPrintJob)
    pending_jobs     = await _count(LabelPrintJob, LabelPrintJob.status == PrintJobStatus.PENDING)
    total_templates  = await _count(GS1LabelTemplate, GS1LabelTemplate.is_active == True)
    ai_pending       = await _count(GS1AIRecommendation, GS1AIRecommendation.status == GS1AIRecStatus.PENDING)

    total_gtins_r = await db.execute(
        select(func.count(ProductGS1Config.gtin.distinct())).where(ProductGS1Config.gtin.isnot(None))
    )
    total_gtins = total_gtins_r.scalar() or 0

    recent_bc_r = await db.execute(
        select(LotBarcodeRecord).order_by(LotBarcodeRecord.created_at.desc()).limit(5)
    )
    recent_barcodes = list(recent_bc_r.scalars())

    recent_sscc_r = await db.execute(
        select(SSCCPallet).order_by(SSCCPallet.created_at.desc()).limit(5)
    )
    recent_sscc = list(recent_sscc_r.scalars())

    return {
        "total_products_configured": total_configs,
        "total_gtins": total_gtins,
        "total_barcodes_generated": total_barcodes,
        "total_labels_printed": printed,
        "total_sscc_pallets": total_sscc,
        "active_sscc_pallets": active_sscc,
        "total_print_jobs": total_jobs,
        "pending_print_jobs": pending_jobs,
        "total_label_templates": total_templates,
        "ai_recommendations_pending": ai_pending,
        "recent_barcodes": recent_barcodes,
        "recent_sscc": recent_sscc,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_label_validator(db: AsyncSession) -> List[GS1AIRecommendation]:
    recs: List[GS1AIRecommendation] = []

    # Find products with no GS1 config
    all_products_r = await db.execute(select(Product.id, Product.name))
    all_products = all_products_r.all()
    configured_r = await db.execute(select(ProductGS1Config.product_id))
    configured_ids = {str(r[0]) for r in configured_r.all()}

    unconfigured = [(pid, pname) for pid, pname in all_products if str(pid) not in configured_ids]
    if unconfigured:
        rec = GS1AIRecommendation(
            agent_type=GS1AIAgentType.LABEL_VALIDATOR,
            title=f"{len(unconfigured)} products missing GS1 configuration",
            description=f"Products without GTIN or barcode type: {', '.join(n for _, n in unconfigured[:5])}{'...' if len(unconfigured) > 5 else ''}",
            recommendation="Configure GS1 settings (GTIN, barcode type, packaging level) for all active products to enable traceability.",
            affected_entity_type="product",
            severity="HIGH",
            agent_metadata={"unconfigured_count": len(unconfigured)},
        )
        db.add(rec)
        recs.append(rec)

    # Find configs with no GTIN
    no_gtin_r = await db.execute(
        select(ProductGS1Config, Product.name.label("pname"))
        .join(Product, ProductGS1Config.product_id == Product.id)
        .where(ProductGS1Config.gtin.is_(None))
    )
    no_gtin = no_gtin_r.all()
    if no_gtin:
        rec = GS1AIRecommendation(
            agent_type=GS1AIAgentType.LABEL_VALIDATOR,
            title=f"{len(no_gtin)} GS1 configs missing GTIN",
            description=f"Products configured but without GTIN: {', '.join(r[1] for r in no_gtin[:5])}",
            recommendation="Assign a valid GTIN-14 to each product. Use your GS1 company prefix to build compliant GTINs.",
            affected_entity_type="product_gs1_config",
            severity="HIGH",
            agent_metadata={"count": len(no_gtin)},
        )
        db.add(rec)
        recs.append(rec)

    # Find barcodes with invalid GTIN check digits
    all_barcodes_r = await db.execute(select(LotBarcodeRecord.id, LotBarcodeRecord.gtin))
    invalid_gtins = [
        (str(bid), g) for bid, g in all_barcodes_r.all()
        if g and not validate_gtin(g)
    ]
    if invalid_gtins:
        rec = GS1AIRecommendation(
            agent_type=GS1AIAgentType.LABEL_VALIDATOR,
            title=f"{len(invalid_gtins)} barcodes with invalid GTIN check digits",
            description="Barcodes contain GTINs that fail GS1 check digit validation.",
            recommendation="Recalculate check digits for affected GTINs and regenerate barcodes.",
            affected_entity_type="lot_barcode",
            severity="CRITICAL",
            agent_metadata={"count": len(invalid_gtins)},
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


async def run_packaging_optimizer(db: AsyncSession) -> List[GS1AIRecommendation]:
    recs: List[GS1AIRecommendation] = []

    # Find configs without packaging hierarchy
    no_hierarchy_r = await db.execute(
        select(ProductGS1Config, Product.name.label("pname"))
        .join(Product, ProductGS1Config.product_id == Product.id)
        .where(
            and_(
                ProductGS1Config.cartons_per_pallet.is_(None),
                ProductGS1Config.gtin.isnot(None),
            )
        )
    )
    no_hierarchy = no_hierarchy_r.all()
    if no_hierarchy:
        rec = GS1AIRecommendation(
            agent_type=GS1AIAgentType.PACKAGING_OPTIMIZER,
            title=f"{len(no_hierarchy)} products missing packaging hierarchy",
            description=f"Products with GTIN but no cartons-per-pallet defined: {', '.join(r[1] for r in no_hierarchy[:5])}",
            recommendation="Define full packaging hierarchy (units → inner pack → carton → pallet) to enable SSCC pallet tracking and optimize warehouse operations.",
            affected_entity_type="product_gs1_config",
            severity="MEDIUM",
            agent_metadata={"count": len(no_hierarchy)},
        )
        db.add(rec)
        recs.append(rec)

    # Check SSCC pallets with many lots (sub-optimal palletization)
    sscc_r = await db.execute(
        select(SSCCPallet.id, SSCCPallet.sscc_code, func.count(SSCCPalletLot.id).label("lot_count"))
        .join(SSCCPalletLot, SSCCPallet.id == SSCCPalletLot.sscc_id, isouter=True)
        .where(SSCCPallet.status == SSCCStatus.ACTIVE)
        .group_by(SSCCPallet.id, SSCCPallet.sscc_code)
        .having(func.count(SSCCPalletLot.id) > 20)
    )
    overloaded = sscc_r.all()
    if overloaded:
        rec = GS1AIRecommendation(
            agent_type=GS1AIAgentType.PACKAGING_OPTIMIZER,
            title=f"{len(overloaded)} pallets with >20 lot links (potential over-mixing)",
            description="Pallets with many lot references may indicate poor palletization — mixed lots reduce FEFO efficiency.",
            recommendation="Review palletization policy: prefer single-lot pallets for FEFO compliance. Consider separate pallets per lot/expiry group.",
            affected_entity_type="sscc_pallet",
            severity="MEDIUM",
            agent_metadata={"overloaded_count": len(overloaded)},
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs


async def list_ai_recommendations(
    db: AsyncSession,
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[GS1AIRecommendation]:
    q = select(GS1AIRecommendation)
    if agent_type:
        q = q.where(GS1AIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(GS1AIRecommendation.status == status)
    r = await db.execute(q.order_by(GS1AIRecommendation.created_at.desc()))
    return list(r.scalars())


async def review_ai_recommendation(
    db: AsyncSession, rec_id: uuid.UUID, status: str, reviewed_by: Optional[str]
) -> Optional[GS1AIRecommendation]:
    r = await db.execute(select(GS1AIRecommendation).where(GS1AIRecommendation.id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        return None
    rec.status = status
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.now(timezone.utc)
    return rec


# ── Reports ───────────────────────────────────────────────────────────────────

async def get_print_history(db: AsyncSession, limit: int = 100) -> List[dict]:
    q = (
        select(
            LabelPrintJob.job_no,
            LabelPrintJob.trigger,
            LabelPrintJob.status,
            LabelPrintJob.printed_by,
            LabelPrintJob.printed_at,
            LabelPrintJob.quantity,
            GS1LabelTemplate.name.label("template_name"),
            LabelPrintJob.created_at,
        )
        .outerjoin(GS1LabelTemplate, LabelPrintJob.template_id == GS1LabelTemplate.id)
        .order_by(LabelPrintJob.created_at.desc())
        .limit(limit)
    )
    r = await db.execute(q)
    return [dict(row._mapping) for row in r.all()]


async def get_sscc_tracking_report(db: AsyncSession, limit: int = 100) -> List[dict]:
    q = (
        select(
            SSCCPallet.sscc_code,
            SSCCPallet.pallet_id,
            SSCCPallet.status,
            SSCCPallet.warehouse_location,
            SSCCPallet.shipment_reference,
            func.count(SSCCPalletLot.id).label("lot_count"),
            SSCCPallet.created_at,
        )
        .outerjoin(SSCCPalletLot, SSCCPallet.id == SSCCPalletLot.sscc_id)
        .group_by(
            SSCCPallet.sscc_code, SSCCPallet.pallet_id, SSCCPallet.status,
            SSCCPallet.warehouse_location, SSCCPallet.shipment_reference, SSCCPallet.created_at
        )
        .order_by(SSCCPallet.created_at.desc())
        .limit(limit)
    )
    r = await db.execute(q)
    return [dict(row._mapping) for row in r.all()]


async def get_packaging_hierarchy_report(db: AsyncSession) -> List[dict]:
    q = (
        select(
            ProductGS1Config.gtin,
            Product.name.label("product_name"),
            ProductGS1Config.packaging_level,
            ProductGS1Config.units_per_inner_pack,
            ProductGS1Config.inner_packs_per_carton,
            ProductGS1Config.cartons_per_pallet,
        )
        .join(Product, ProductGS1Config.product_id == Product.id)
        .order_by(Product.name)
    )
    r = await db.execute(q)
    rows = []
    for row in r.all():
        d = dict(row._mapping)
        uip = d.get("units_per_inner_pack") or 1
        ipc = d.get("inner_packs_per_carton") or 1
        cpp = d.get("cartons_per_pallet")
        d["total_units_per_pallet"] = int(uip * ipc * cpp) if cpp else None
        rows.append(d)
    return rows
