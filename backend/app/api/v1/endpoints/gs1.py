"""GS1 Barcode + Label Printing — API endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.gs1 import (
    GS1CompanyConfigCreate, GS1CompanyConfigOut,
    ProductGS1ConfigCreate, ProductGS1ConfigUpdate, ProductGS1ConfigOut,
    BarcodeGenerateRequest, BarcodeGenerateResponse,
    GS1DecodeRequest, GS1DecodeResponse,
    LotBarcodeOut,
    SSCCGenerateRequest, SSCCPalletOut, SSCCAddLotRequest,
    LabelTemplateCreate, LabelTemplateUpdate, LabelTemplateOut,
    PrintJobCreate, PrintJobOut,
    GS1AIRecOut, GS1AIRecReview,
    GS1DashboardOut,
    LabelPrintHistoryOut, SSCCTrackingOut, PackagingHierarchyOut,
)
from app.services import gs1_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=GS1DashboardOut)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Company Config ────────────────────────────────────────────────────────────

@router.post("/config", response_model=GS1CompanyConfigOut, status_code=201)
async def create_company_config(
    payload: GS1CompanyConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    cfg = await svc.create_company_config(db, payload.model_dump())
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.get("/config", response_model=List[GS1CompanyConfigOut])
async def list_company_configs(db: AsyncSession = Depends(get_db)):
    return await svc.list_company_configs(db)


@router.get("/config/{cfg_id}", response_model=GS1CompanyConfigOut)
async def get_company_config(cfg_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_company_config(db, cfg_id)
    if not cfg:
        raise HTTPException(404, "Company config not found")
    return cfg


# ── Product GS1 Config ────────────────────────────────────────────────────────

@router.post("/products", response_model=ProductGS1ConfigOut, status_code=201)
async def create_product_config(
    payload: ProductGS1ConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    cfg = await svc.create_product_config(db, payload.model_dump())
    await db.commit()
    await db.refresh(cfg)
    return ProductGS1ConfigOut.model_validate({**{c.name: getattr(cfg, c.name) for c in cfg.__table__.columns}, "product_name": None})


@router.get("/products", response_model=List[ProductGS1ConfigOut])
async def list_product_configs(db: AsyncSession = Depends(get_db)):
    rows = await svc.list_product_configs(db)
    return [ProductGS1ConfigOut.model_validate(r) for r in rows]


@router.get("/products/{cfg_id}", response_model=ProductGS1ConfigOut)
async def get_product_config(cfg_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_product_config(db, cfg_id)
    if not cfg:
        raise HTTPException(404, "Product GS1 config not found")
    return ProductGS1ConfigOut.model_validate({**{c.name: getattr(cfg, c.name) for c in cfg.__table__.columns}, "product_name": None})


@router.patch("/products/{cfg_id}", response_model=ProductGS1ConfigOut)
async def update_product_config(
    cfg_id: uuid.UUID,
    payload: ProductGS1ConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    cfg = await svc.update_product_config(db, cfg_id, payload.model_dump(exclude_none=True))
    if not cfg:
        raise HTTPException(404, "Product GS1 config not found")
    await db.commit()
    await db.refresh(cfg)
    return ProductGS1ConfigOut.model_validate({**{c.name: getattr(cfg, c.name) for c in cfg.__table__.columns}, "product_name": None})


@router.get("/products/by-product/{product_id}", response_model=ProductGS1ConfigOut)
async def get_config_by_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_product_config_by_product(db, product_id)
    if not cfg:
        raise HTTPException(404, "No GS1 config for this product")
    return ProductGS1ConfigOut.model_validate({**{c.name: getattr(cfg, c.name) for c in cfg.__table__.columns}, "product_name": None})


# ── Barcode Generation ────────────────────────────────────────────────────────

@router.post("/barcode/generate", response_model=BarcodeGenerateResponse)
async def generate_barcode(
    payload: BarcodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    gtin = payload.gtin
    product_config_id = None

    if not gtin and payload.product_id:
        cfg = await svc.get_product_config_by_product(db, payload.product_id)
        if cfg:
            gtin = cfg.gtin
            product_config_id = cfg.id
    elif payload.product_id:
        cfg = await svc.get_product_config_by_product(db, payload.product_id)
        if cfg:
            product_config_id = cfg.id

    if not gtin:
        raise HTTPException(400, "GTIN required — provide gtin or a product_id with GS1 config")

    result = await svc.generate_barcode(
        db,
        gtin=gtin,
        lot_number=payload.lot_number,
        expiry_date=payload.expiry_date,
        production_date=payload.production_date,
        serial_number=payload.serial_number,
        barcode_type=payload.barcode_type,
        lot_id=payload.lot_id,
        product_config_id=product_config_id,
        quantity=payload.quantity,
        packaging_level=payload.packaging_level,
        save_record=payload.save_record,
    )
    if payload.save_record and product_config_id:
        await db.commit()
    return BarcodeGenerateResponse.model_validate(result)


@router.get("/barcode", response_model=List[LotBarcodeOut])
async def list_barcodes(
    product_config_id: Optional[uuid.UUID] = None,
    lot_id: Optional[uuid.UUID] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_lot_barcodes(db, product_config_id, lot_id, limit, offset)


@router.get("/barcode/{record_id}", response_model=LotBarcodeOut)
async def get_barcode(record_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.gs1 import LotBarcodeRecord
    r = await db.execute(select(LotBarcodeRecord).where(LotBarcodeRecord.id == record_id))
    rec = r.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Barcode record not found")
    return rec


# ── GS1 String Decode / Scan ──────────────────────────────────────────────────

@router.post("/scan/decode", response_model=GS1DecodeResponse)
async def decode_gs1(payload: GS1DecodeRequest, db: AsyncSession = Depends(get_db)):
    return GS1DecodeResponse.model_validate(
        await svc.decode_and_validate(db, payload.gs1_string)
    )


@router.get("/scan/decode")
async def decode_gs1_get(
    gs1_string: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.decode_and_validate(db, gs1_string)


# ── SSCC / Pallet ─────────────────────────────────────────────────────────────

@router.post("/sscc/generate", response_model=SSCCPalletOut, status_code=201)
async def generate_sscc(
    payload: SSCCGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    pallet = await svc.create_sscc_pallet(
        db,
        company_config_id=payload.company_config_id,
        pallet_id=payload.pallet_id,
        warehouse_location=payload.warehouse_location,
        notes=payload.notes,
    )
    await db.commit()
    await db.refresh(pallet)
    lot_count = await svc.get_sscc_lot_count(db, pallet.id)
    return SSCCPalletOut.model_validate(
        {**{c.name: getattr(pallet, c.name) for c in pallet.__table__.columns}, "lot_count": lot_count}
    )


@router.get("/sscc", response_model=List[SSCCPalletOut])
async def list_sscc_pallets(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    pallets = await svc.list_sscc_pallets(db, status, limit, offset)
    result = []
    for p in pallets:
        lc = await svc.get_sscc_lot_count(db, p.id)
        result.append(
            SSCCPalletOut.model_validate({**{c.name: getattr(p, c.name) for c in p.__table__.columns}, "lot_count": lc})
        )
    return result


@router.get("/sscc/{sscc_id}", response_model=SSCCPalletOut)
async def get_sscc_pallet(sscc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    pallet = await svc.get_sscc_pallet(db, sscc_id)
    if not pallet:
        raise HTTPException(404, "SSCC pallet not found")
    lc = await svc.get_sscc_lot_count(db, pallet.id)
    return SSCCPalletOut.model_validate(
        {**{c.name: getattr(pallet, c.name) for c in pallet.__table__.columns}, "lot_count": lc}
    )


@router.post("/sscc/{sscc_id}/lots", status_code=201)
async def add_lot_to_sscc(
    sscc_id: uuid.UUID,
    payload: SSCCAddLotRequest,
    db: AsyncSession = Depends(get_db),
):
    link = await svc.add_lot_to_sscc(
        db, sscc_id, payload.lot_barcode_id, payload.quantity, payload.packaging_level
    )
    await db.commit()
    return {"id": str(link.id), "sscc_id": str(sscc_id), "lot_barcode_id": str(payload.lot_barcode_id)}


@router.patch("/sscc/{sscc_id}/status")
async def update_sscc_status(
    sscc_id: uuid.UUID,
    status: str = Query(...),
    shipment_reference: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    pallet = await svc.get_sscc_pallet(db, sscc_id)
    if not pallet:
        raise HTTPException(404, "SSCC pallet not found")
    pallet.status = status
    if shipment_reference:
        pallet.shipment_reference = shipment_reference
    await db.commit()
    return {"sscc_code": pallet.sscc_code, "status": status}


# ── Label Templates ───────────────────────────────────────────────────────────

@router.post("/labels/templates", response_model=LabelTemplateOut, status_code=201)
async def create_template(
    payload: LabelTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.create_label_template(db, payload.model_dump())
    await db.commit()
    await db.refresh(t)
    return t


@router.get("/labels/templates", response_model=List[LabelTemplateOut])
async def list_templates(
    packaging_level: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_label_templates(db, packaging_level, active_only)


@router.get("/labels/templates/{tmpl_id}", response_model=LabelTemplateOut)
async def get_template(tmpl_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    t = await svc.get_label_template(db, tmpl_id)
    if not t:
        raise HTTPException(404, "Label template not found")
    return t


@router.patch("/labels/templates/{tmpl_id}", response_model=LabelTemplateOut)
async def update_template(
    tmpl_id: uuid.UUID,
    payload: LabelTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    t = await svc.update_label_template(db, tmpl_id, payload.model_dump(exclude_none=True))
    if not t:
        raise HTTPException(404, "Label template not found")
    await db.commit()
    await db.refresh(t)
    return t


# ── Print Jobs ────────────────────────────────────────────────────────────────

@router.post("/labels/print", response_model=PrintJobOut, status_code=201)
async def create_print_job(
    payload: PrintJobCreate,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    job = await svc.create_print_job(db, data)
    await db.commit()
    await db.refresh(job)
    return PrintJobOut.model_validate(
        {**{c.name: getattr(job, c.name) for c in job.__table__.columns}, "item_count": len(payload.items)}
    )


@router.get("/labels/print", response_model=List[PrintJobOut])
async def list_print_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    jobs = await svc.list_print_jobs(db, status, limit, offset)
    return [
        PrintJobOut.model_validate(
            {**{c.name: getattr(j, c.name) for c in j.__table__.columns}, "item_count": 0}
        )
        for j in jobs
    ]


@router.post("/labels/print/{job_id}/complete")
async def complete_print_job(
    job_id: uuid.UUID,
    printed_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    job = await svc.complete_print_job(db, job_id, printed_by)
    if not job:
        raise HTTPException(404, "Print job not found")
    await db.commit()
    return {"job_no": job.job_no, "status": str(job.status)}


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-label-validator", status_code=201)
async def run_label_validator(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_label_validator(db)
    await db.commit()
    return {"generated": len(recs)}


@router.post("/ai/run-packaging-optimizer", status_code=201)
async def run_packaging_optimizer(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_packaging_optimizer(db)
    await db.commit()
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[GS1AIRecOut])
async def list_recommendations(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recommendations(db, agent_type, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=GS1AIRecOut)
async def review_recommendation(
    rec_id: uuid.UUID,
    payload: GS1AIRecReview,
    db: AsyncSession = Depends(get_db),
):
    rec = await svc.review_ai_recommendation(db, rec_id, payload.status, payload.reviewed_by)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/print-history")
async def print_history(limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await svc.get_print_history(db, limit)


@router.get("/reports/sscc-tracking")
async def sscc_tracking(limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await svc.get_sscc_tracking_report(db, limit)


@router.get("/reports/packaging-hierarchy")
async def packaging_hierarchy(db: AsyncSession = Depends(get_db)):
    return await svc.get_packaging_hierarchy_report(db)


@router.get("/reports/barcode-usage")
async def barcode_usage(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.gs1 import LotBarcodeRecord, ProductGS1Config
    from app.models.master import Product
    q = (
        select(
            Product.name.label("product_name"),
            ProductGS1Config.gtin,
            ProductGS1Config.barcode_type,
            func.count(LotBarcodeRecord.id).label("total_generated"),
            func.sum(
                (LotBarcodeRecord.is_printed == True).cast(type_=None)
            ).label("total_printed"),
        )
        .join(ProductGS1Config, LotBarcodeRecord.product_config_id == ProductGS1Config.id)
        .join(Product, ProductGS1Config.product_id == Product.id)
        .group_by(Product.name, ProductGS1Config.gtin, ProductGS1Config.barcode_type)
        .order_by(Product.name)
    )
    r = await db.execute(q)
    return [dict(row._mapping) for row in r.all()]
