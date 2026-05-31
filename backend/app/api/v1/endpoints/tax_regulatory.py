from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.tax_regulatory import (
    CountryTaxConfigCreate, CountryTaxConfigUpdate, CountryTaxConfigRead,
    TaxCategoryCreate, TaxCategoryUpdate, TaxCategoryRead,
    TaxRuleCreate, TaxRuleUpdate, TaxRuleRead,
    ProductTaxMappingCreate, ProductTaxMappingUpdate, ProductTaxMappingRead,
    RegulatoryFlagCreate, RegulatoryFlagUpdate, RegulatoryFlagRead,
    TransactionTaxCreate, TransactionTaxUpdate, TransactionTaxRead,
    TaxSummaryRow, RegulatoryStatusRow, ApplyTaxRequest,
    ETimsSubmissionRead, VATReturnCreate, VATReturnRead,
    WithholdingTaxCreate, WithholdingTaxRead,
)
import app.crud.tax_regulatory as crud
import app.services.tax_service as svc

router = APIRouter()


# ── Country Tax Config ─────────────────────────────────────────────────────────

@router.get("/countries", response_model=List[CountryTaxConfigRead])
async def list_country_configs(db: AsyncSession = Depends(get_db)):
    return await crud.list_country_configs(db)


@router.post("/countries", response_model=CountryTaxConfigRead, status_code=201)
async def create_country_config(
    data: CountryTaxConfigCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.create_country_config(db, data)


@router.get("/countries/{country_code}", response_model=CountryTaxConfigRead)
async def get_country_config(country_code: str, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_country_config(db, country_code)
    if not obj:
        raise HTTPException(404, "Country config not found")
    return obj


@router.patch("/countries/{country_code}", response_model=CountryTaxConfigRead)
async def update_country_config(
    country_code: str,
    data: CountryTaxConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_country_config(db, country_code, data)
    if not obj:
        raise HTTPException(404, "Country config not found")
    return obj


# ── Tax Categories ─────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[TaxCategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await crud.list_categories(db)


@router.post("/categories", response_model=TaxCategoryRead, status_code=201)
async def create_category(
    data: TaxCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.create_category(db, data)


@router.patch("/categories/{category_id}", response_model=TaxCategoryRead)
async def update_category(
    category_id: UUID,
    data: TaxCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_category(db, category_id, data)
    if not obj:
        raise HTTPException(404, "Category not found")
    return obj


# ── Tax Rules ──────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=List[TaxRuleRead])
async def list_rules(
    country_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_rules(db, country_code=country_code)


@router.post("/rules", response_model=TaxRuleRead, status_code=201)
async def create_rule(
    data: TaxRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.create_rule(db, data)


@router.get("/rules/{rule_id}", response_model=TaxRuleRead)
async def get_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_rule(db, rule_id)
    if not obj:
        raise HTTPException(404, "Rule not found")
    return obj


@router.patch("/rules/{rule_id}", response_model=TaxRuleRead)
async def update_rule(
    rule_id: UUID,
    data: TaxRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_rule(db, rule_id, data)
    if not obj:
        raise HTTPException(404, "Rule not found")
    return obj


# ── Product Tax Mappings ───────────────────────────────────────────────────────

@router.get("/mappings", response_model=List[ProductTaxMappingRead])
async def list_mappings(
    country_code: Optional[str] = Query(None),
    product_id: Optional[UUID] = Query(None),
    material_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_mappings(db, country_code=country_code, product_id=product_id, material_id=material_id)


@router.post("/mappings", response_model=ProductTaxMappingRead, status_code=201)
async def create_mapping(
    data: ProductTaxMappingCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.create_mapping(db, data)


@router.patch("/mappings/{mapping_id}", response_model=ProductTaxMappingRead)
async def update_mapping(
    mapping_id: UUID,
    data: ProductTaxMappingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_mapping(db, mapping_id, data)
    if not obj:
        raise HTTPException(404, "Mapping not found")
    return obj


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ok = await crud.delete_mapping(db, mapping_id)
    if not ok:
        raise HTTPException(404, "Mapping not found")


# ── Regulatory Flags ───────────────────────────────────────────────────────────

@router.get("/regulatory-flags", response_model=List[RegulatoryFlagRead])
async def list_flags(
    country_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_flags(db, country_code=country_code, status=status)


@router.post("/regulatory-flags", response_model=RegulatoryFlagRead, status_code=201)
async def create_flag(
    data: RegulatoryFlagCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.create_flag(db, data)


@router.get("/regulatory-flags/expiring", response_model=List[RegulatoryFlagRead])
async def expiring_flags(
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    return await svc.expiring_flags(db, days_ahead=days)


@router.get("/regulatory-flags/{flag_id}", response_model=RegulatoryFlagRead)
async def get_flag(flag_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_flag(db, flag_id)
    if not obj:
        raise HTTPException(404, "Flag not found")
    return obj


@router.patch("/regulatory-flags/{flag_id}", response_model=RegulatoryFlagRead)
async def update_flag(
    flag_id: UUID,
    data: RegulatoryFlagUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_flag(db, flag_id, data)
    if not obj:
        raise HTTPException(404, "Flag not found")
    return obj


@router.delete("/regulatory-flags/{flag_id}", status_code=204)
async def delete_flag(
    flag_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ok = await crud.delete_flag(db, flag_id)
    if not ok:
        raise HTTPException(404, "Flag not found")


# ── Transaction Taxes ──────────────────────────────────────────────────────────

@router.get("/transaction-taxes", response_model=List[TransactionTaxRead])
async def list_transaction_taxes(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[UUID] = Query(None),
    country_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_transaction_taxes(db, entity_type=entity_type, entity_id=entity_id, country_code=country_code)


@router.post("/transaction-taxes", response_model=TransactionTaxRead, status_code=201)
async def create_transaction_tax(
    data: TransactionTaxCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.create_transaction_tax(db, data, created_by_id=current_user.id)


@router.post("/transaction-taxes/apply", response_model=List[TransactionTaxRead], status_code=201)
async def apply_taxes(
    req: ApplyTaxRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-apply all matching tax rules to an entity."""
    return await svc.apply_taxes(db, req, created_by_id=current_user.id)


@router.patch("/transaction-taxes/{tax_id}", response_model=TransactionTaxRead)
async def update_transaction_tax(
    tax_id: UUID,
    data: TransactionTaxUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = await crud.update_transaction_tax(db, tax_id, data)
    if not obj:
        raise HTTPException(404, "Transaction tax not found")
    return obj


@router.post("/transaction-taxes/post/{entity_type}/{entity_id}", response_model=dict)
async def bulk_post_taxes(
    entity_type: str,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await crud.bulk_post_transaction_taxes(db, entity_type, entity_id)
    return {"posted": count}


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/tax-summary", response_model=List[TaxSummaryRow])
async def tax_summary(
    country_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.tax_summary_by_country(db, country_code=country_code)


@router.get("/reports/regulatory-status", response_model=List[RegulatoryStatusRow])
async def regulatory_status(
    country_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.regulatory_status_dashboard(db, country_code=country_code)


# ── eTIMS / KRA e-Invoice ─────────────────────────────────────────────────────

from datetime import datetime, timezone
from sqlalchemy import select as _tsel
from app.models.tax_regulatory import (
    ETimsSubmission, ETimsStatus,
    VATReturn, VATReturnStatus,
    WithholdingTaxRecord,
)


@router.get("/etims/submissions", response_model=List[ETimsSubmissionRead])
async def list_etims_submissions(
    status: Optional[ETimsStatus] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = _tsel(ETimsSubmission).order_by(ETimsSubmission.created_at.desc()).limit(limit)
    if status:
        q = q.where(ETimsSubmission.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [ETimsSubmissionRead.model_validate(r) for r in rows]


@router.get("/etims/submissions/{invoice_id}", response_model=ETimsSubmissionRead)
async def get_etims_submission(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        _tsel(ETimsSubmission).where(ETimsSubmission.invoice_id == invoice_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "No eTIMS submission for this invoice")
    return ETimsSubmissionRead.model_validate(row)


@router.post("/etims/submit/{invoice_id}", response_model=ETimsSubmissionRead)
async def submit_etims(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit invoice to KRA eTIMS via connector-ready adapter layer.

    Routes to SimulationETIMSConnector (demo) or HttpETIMSConnector (live)
    based on ETIMS_PROVIDER and ETIMS_CONFIGURED settings.
    Live provider/middleware decision is still pending — not production-ready.
    """
    from app.models.sales import Invoice, InvoiceLine
    from sqlalchemy.orm import selectinload
    from app.core.config import settings
    from app.services.etims_connector import build_etims_payload, get_etims_connector

    invoice = (await db.execute(
        _tsel(Invoice)
        .options(selectinload(Invoice.lines).selectinload(InvoiceLine.product))
        .where(Invoice.id == invoice_id)
    )).scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    sub = (await db.execute(
        _tsel(ETimsSubmission).where(ETimsSubmission.invoice_id == invoice_id)
    )).scalar_one_or_none()

    if sub and sub.status == ETimsStatus.ACCEPTED:
        raise HTTPException(422, "Invoice already accepted by KRA")

    if not sub:
        sub = ETimsSubmission(invoice_id=invoice_id, submitted_by_id=current_user.id)
        db.add(sub)

    payload = build_etims_payload(invoice, settings)
    connector = get_etims_connector(settings)
    result = await connector.submit_sales_invoice(payload)

    sub.status = ETimsStatus(result.status)
    sub.transmitted_at = datetime.now(timezone.utc)
    sub.control_unit_invoice_no = result.control_unit_invoice_no
    sub.signed_invoice_hash = result.signed_invoice_hash
    sub.invoice_qr_data = result.invoice_qr_data
    sub.kra_response_code = result.response_code
    sub.kra_response_message = result.response_message
    sub.retry_count += 1

    await db.commit()
    await db.refresh(sub)
    return ETimsSubmissionRead.model_validate(sub)


# ── VAT Returns ───────────────────────────────────────────────────────────────

@router.get("/vat-returns", response_model=List[VATReturnRead])
async def list_vat_returns(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        _tsel(VATReturn).order_by(VATReturn.period_ym.desc())
    )).scalars().all()
    return [VATReturnRead.model_validate(r) for r in rows]


@router.post("/vat-returns/generate", response_model=VATReturnRead, status_code=201)
async def generate_vat_return(
    body: VATReturnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generate VAT3 return from invoices for the given period."""
    from app.models.sales import Invoice, InvoiceStatus
    from app.models.finance import PurchaseInvoice
    from sqlalchemy import func, and_, extract

    year, month = int(body.period_ym[:4]), int(body.period_ym[5:])

    # Sales invoices for period
    sales_q = await db.execute(
        _tsel(
            func.coalesce(func.sum(Invoice.subtotal), 0).label("sales"),
            func.coalesce(func.sum(Invoice.tax_amount), 0).label("output_vat"),
        )
        .where(
            Invoice.status.notin_([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]),
            extract("year", Invoice.invoice_date) == year,
            extract("month", Invoice.invoice_date) == month,
        )
    )
    s = sales_q.one()

    # Purchase invoices for period
    from app.models.finance import PurchaseInvoiceStatus as PIStatus
    purch_q = await db.execute(
        _tsel(
            func.coalesce(func.sum(PurchaseInvoice.subtotal), 0).label("purchases"),
            func.coalesce(func.sum(PurchaseInvoice.tax_amount), 0).label("input_vat"),
        )
        .where(
            PurchaseInvoice.status.notin_([PIStatus.CANCELLED, PIStatus.DRAFT]),
            extract("year", PurchaseInvoice.invoice_date) == year,
            extract("month", PurchaseInvoice.invoice_date) == month,
        )
    )
    p = purch_q.one()

    output_vat = float(s.output_vat or 0)
    input_vat = float(p.input_vat or 0)
    net_vat = output_vat - input_vat

    # Upsert
    existing = (await db.execute(
        _tsel(VATReturn).where(VATReturn.period_ym == body.period_ym)
    )).scalar_one_or_none()

    if existing:
        vr = existing
    else:
        vr = VATReturn(period_ym=body.period_ym, filed_by_id=current_user.id)
        db.add(vr)

    vr.standard_rated_sales = float(s.sales or 0)
    vr.output_vat = output_vat
    vr.standard_rated_purchases = float(p.purchases or 0)
    vr.input_vat = input_vat
    vr.net_vat_payable = net_vat
    vr.notes = body.notes

    await db.commit()
    await db.refresh(vr)
    return VATReturnRead.model_validate(vr)


@router.post("/vat-returns/{vat_return_id}/file", response_model=VATReturnRead)
async def file_vat_return(
    vat_return_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vr = (await db.execute(_tsel(VATReturn).where(VATReturn.id == vat_return_id))).scalar_one_or_none()
    if not vr:
        raise HTTPException(404, "VAT return not found")
    vr.status = VATReturnStatus.SUBMITTED
    vr.filed_at = datetime.now(timezone.utc)
    vr.filed_by_id = current_user.id
    await db.commit()
    await db.refresh(vr)
    return VATReturnRead.model_validate(vr)


# ── Withholding Tax ───────────────────────────────────────────────────────────

@router.get("/withholding-tax", response_model=List[WithholdingTaxRead])
async def list_wht(
    period_ym: Optional[str] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    q = _tsel(WithholdingTaxRecord).order_by(WithholdingTaxRecord.payment_date.desc()).limit(limit)
    if period_ym:
        q = q.where(WithholdingTaxRecord.period_ym == period_ym)
    rows = (await db.execute(q)).scalars().all()
    return [WithholdingTaxRead.model_validate(r) for r in rows]


@router.post("/withholding-tax", response_model=WithholdingTaxRead, status_code=201)
async def create_wht(
    body: WithholdingTaxCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from decimal import Decimal
    wht_amount = (body.gross_amount * body.wht_rate / 100).quantize(Decimal("0.01"))
    net_amount = body.gross_amount - wht_amount
    rec = WithholdingTaxRecord(
        direction=body.direction,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        invoice_id=body.invoice_id,
        payment_date=body.payment_date,
        gross_amount=body.gross_amount,
        wht_rate=body.wht_rate,
        wht_amount=wht_amount,
        net_amount=net_amount,
        certificate_no=body.certificate_no,
        period_ym=body.period_ym,
        notes=body.notes,
        created_by_id=current_user.id,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return WithholdingTaxRead.model_validate(rec)
