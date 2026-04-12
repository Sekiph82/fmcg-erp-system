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
