from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax_regulatory import (
    CountryTaxConfig, TaxCategory, TaxRule,
    ProductTaxMapping, RegulatoryFlag, TransactionTax,
    TaxAppliesTo, TxTaxStatus,
)
from app.schemas.tax_regulatory import (
    TaxSummaryRow, RegulatoryStatusRow,
    ApplyTaxRequest, TransactionTaxCreate,
)


async def apply_taxes(
    db: AsyncSession,
    req: ApplyTaxRequest,
    created_by_id: Optional[UUID] = None,
) -> List[TransactionTax]:
    """
    Find all active applicable tax rules for country + applies_to,
    optionally filtered by product/material mapping, and create
    TransactionTax records (DRAFT status).
    Returns list of created TransactionTax objects.
    """
    today = date.today()

    # Determine effective tax categories for this product/material
    exempt_category_ids: set[UUID] = set()
    zero_rated_category_ids: set[UUID] = set()

    mapping_filters = [ProductTaxMapping.country_code == req.country_code]
    if req.product_id:
        mapping_filters.append(ProductTaxMapping.product_id == req.product_id)
    elif req.material_id:
        mapping_filters.append(ProductTaxMapping.material_id == req.material_id)
    elif req.hs_code:
        mapping_filters.append(ProductTaxMapping.hs_code == req.hs_code)

    map_result = await db.execute(
        select(ProductTaxMapping).where(and_(*mapping_filters))
    )
    mappings = list(map_result.scalars().all())
    for m in mappings:
        if m.is_exempt:
            exempt_category_ids.add(m.tax_category_id)
        if m.is_zero_rated:
            zero_rated_category_ids.add(m.tax_category_id)

    # Fetch applicable tax rules
    rule_filters = [
        TaxRule.country_code == req.country_code,
        TaxRule.is_active == True,
        TaxRule.applies_to.in_([req.applies_to, TaxAppliesTo.ALL]),
    ]
    # effective date window
    rule_filters.append(
        (TaxRule.effective_from == None) | (TaxRule.effective_from <= today)
    )
    rule_filters.append(
        (TaxRule.effective_to == None) | (TaxRule.effective_to >= today)
    )

    rules_result = await db.execute(select(TaxRule).where(and_(*rule_filters)))
    rules = list(rules_result.scalars().all())

    created_taxes: List[TransactionTax] = []
    running_total = req.taxable_amount  # for compound calculation

    for rule in rules:
        # Skip if exempt
        if rule.tax_category_id in exempt_category_ids:
            continue

        effective_rate = Decimal("0") if rule.tax_category_id in zero_rated_category_ids else rule.rate
        base = running_total if rule.is_compound else req.taxable_amount
        tax_amount = (base * effective_rate / Decimal("100")).quantize(Decimal("0.0001"))

        tx = TransactionTax(
            entity_type=req.entity_type,
            entity_id=req.entity_id,
            country_code=req.country_code,
            tax_rule_id=rule.id,
            tax_type=rule.tax_type,
            tax_category_code=None,  # will be filled after category load if needed
            taxable_amount=base,
            rate=effective_rate,
            tax_amount=tax_amount,
            currency=req.currency,
            status=TxTaxStatus.DRAFT,
            created_by_id=created_by_id,
        )
        db.add(tx)
        if rule.is_compound:
            running_total += tax_amount
        created_taxes.append(tx)

    if created_taxes:
        await db.commit()
        for tx in created_taxes:
            await db.refresh(tx)

    return created_taxes


async def tax_summary_by_country(
    db: AsyncSession,
    country_code: Optional[str] = None,
) -> List[TaxSummaryRow]:
    filters = [TransactionTax.status.in_([TxTaxStatus.CONFIRMED, TxTaxStatus.POSTED])]
    if country_code:
        filters.append(TransactionTax.country_code == country_code)

    result = await db.execute(
        select(
            TransactionTax.country_code,
            TransactionTax.tax_type,
            TransactionTax.currency,
            func.sum(TransactionTax.taxable_amount).label("total_taxable_amount"),
            func.sum(TransactionTax.tax_amount).label("total_tax_amount"),
            func.count(TransactionTax.id).label("transaction_count"),
        )
        .where(and_(*filters))
        .group_by(
            TransactionTax.country_code,
            TransactionTax.tax_type,
            TransactionTax.currency,
        )
        .order_by(TransactionTax.country_code, TransactionTax.tax_type)
    )

    rows = []
    for r in result.all():
        rows.append(TaxSummaryRow(
            country_code=r.country_code,
            tax_type=r.tax_type.value if hasattr(r.tax_type, "value") else str(r.tax_type),
            currency=r.currency,
            total_taxable_amount=r.total_taxable_amount or Decimal("0"),
            total_tax_amount=r.total_tax_amount or Decimal("0"),
            transaction_count=r.transaction_count,
        ))
    return rows


async def regulatory_status_dashboard(
    db: AsyncSession,
    country_code: Optional[str] = None,
) -> List[RegulatoryStatusRow]:
    today = date.today()
    soon = today + timedelta(days=30)

    filters = []
    if country_code:
        filters.append(RegulatoryFlag.country_code == country_code)

    result = await db.execute(
        select(
            RegulatoryFlag.country_code,
            RegulatoryFlag.flag_type,
            RegulatoryFlag.status,
            func.count(RegulatoryFlag.id).label("count"),
        )
        .where(and_(*filters) if filters else True)
        .group_by(
            RegulatoryFlag.country_code,
            RegulatoryFlag.flag_type,
            RegulatoryFlag.status,
        )
        .order_by(RegulatoryFlag.country_code, RegulatoryFlag.flag_type)
    )

    # Fetch expiring flag ids separately to compute expiring_soon per group
    expiring_result = await db.execute(
        select(
            RegulatoryFlag.country_code,
            RegulatoryFlag.flag_type,
            RegulatoryFlag.status,
            func.count(RegulatoryFlag.id).label("expiring_count"),
        )
        .where(
            and_(
                *(filters or [True]),
                RegulatoryFlag.expiry_date != None,
                RegulatoryFlag.expiry_date >= today,
                RegulatoryFlag.expiry_date <= soon,
            )
        )
        .group_by(
            RegulatoryFlag.country_code,
            RegulatoryFlag.flag_type,
            RegulatoryFlag.status,
        )
    )
    expiring_map: dict[tuple, int] = {}
    for er in expiring_result.all():
        expiring_map[(er.country_code, str(er.flag_type), str(er.status))] = er.expiring_count

    rows = []
    for r in result.all():
        flag_type_str = r.flag_type.value if hasattr(r.flag_type, "value") else str(r.flag_type)
        status_str = r.status.value if hasattr(r.status, "value") else str(r.status)
        rows.append(RegulatoryStatusRow(
            country_code=r.country_code,
            flag_type=flag_type_str,
            status=status_str,
            count=r.count,
            expiring_soon=expiring_map.get((r.country_code, flag_type_str, status_str), 0),
        ))
    return rows


async def expiring_flags(db: AsyncSession, days_ahead: int = 30) -> List[RegulatoryFlag]:
    """Flags that expire within days_ahead days."""
    today = date.today()
    soon = today + timedelta(days=days_ahead)
    result = await db.execute(
        select(RegulatoryFlag)
        .where(
            and_(
                RegulatoryFlag.expiry_date != None,
                RegulatoryFlag.expiry_date >= today,
                RegulatoryFlag.expiry_date <= soon,
                RegulatoryFlag.status != "EXPIRED",
            )
        )
        .order_by(RegulatoryFlag.expiry_date)
    )
    return list(result.scalars().all())
