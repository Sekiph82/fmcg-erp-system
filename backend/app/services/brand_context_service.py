"""M48.S01.T006 canonical POVU brand and product context for sales and content copy.

Everything comes from database records, each with a citation:
- products: active products only (there is no separate product approval state; inactive = withdrawn), grouped by
  category and catalogue line (the line is the part of `description` before " · ", as written by seed_catalogue);
- brand assets: latest APPROVED / PRINT_READY brand_assets (Brand Vault);
- claims: approved evidence of the content-studio brand profiles (cs_brand_profiles.evidence) — the only claim table;
- target: CRM territory and segment of a lead, or region and segment of an imported prospect row.
An empty catalogue gives empty lists: callers write neutral copy ("our home and personal care range") and never
invent products or claims.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_BRAND = "POVU"          # company brand when no approved Brand Vault asset names one
NEUTRAL_RANGE = "our home and personal care range"
CATEGORY_LABEL = {"HOUSEHOLD": "home care and cleaning", "PERSONAL_CARE": "personal care"}


async def context(db: AsyncSession, *, target_kind: Optional[str] = None, target_id: Optional[str] = None,
                  max_products: int = 500) -> dict:
    from app.models.brand_assets import AssetStatus, BrandAsset
    from app.models.cms import CsBrandProfile
    from app.models.master import Product

    products = list((await db.execute(select(Product).where(Product.is_active.is_(True))
                                      .order_by(Product.category, Product.sku).limit(max_products))).scalars())
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in products:
        cat = getattr(p.category, "value", p.category) or "OTHER"
        line = (p.description or "").split(" · ")[0].strip() or p.name
        groups.setdefault((cat, line), []).append({"sku": p.sku, "name": p.name})
    lines = [{"category": c, "line": ln, "products": ps} for (c, ln), ps in groups.items()]

    assets = list((await db.execute(select(BrandAsset).where(
        BrandAsset.is_latest.is_(True), BrandAsset.status.in_([AssetStatus.APPROVED, AssetStatus.PRINT_READY]))
        .order_by(BrandAsset.asset_ref).limit(50))).scalars())
    brand = next((a.brand for a in assets if a.brand), None)

    claims = [{"id": str(e.get("id")), "text": e.get("text"), "source": e.get("source"), "profile": prof.key}
              for prof in (await db.execute(select(CsBrandProfile).order_by(CsBrandProfile.key))).scalars()
              for e in prof.evidence or [] if e.get("id") and e.get("text")]

    return {"brand": brand or DEFAULT_BRAND,
            "brand_source": "brand_assets" if brand else "system default",
            "assets": [{"asset_ref": a.asset_ref, "name": a.name, "type": getattr(a.asset_type, "value", a.asset_type),
                        "status": getattr(a.status, "value", a.status), "file_url": a.file_url} for a in assets],
            "lines": lines,
            "claims": claims,
            "target": await _target(db, target_kind, target_id)}


async def _target(db: AsyncSession, kind: Optional[str], rid: Optional[str]) -> Optional[dict]:
    if not kind or not rid:
        return None
    try:
        rid_u = uuid.UUID(str(rid))
    except ValueError:
        return None
    if kind == "lead":
        from app.models.crm import CRMRecord, CRMTerritory
        r = await db.get(CRMRecord, rid_u)
        if r is None:
            return None
        t = await db.get(CRMTerritory, r.territory_id) if r.territory_id else None
        return {"territory": t.territory_name if t else None, "region": t.region if t else None,
                "segment": r.industry_segment, "citation": f"CRM lead {r.lead_code or r.id}"
                + (f", territory {t.territory_code}" if t else "")}
    if kind == "prospect":
        from app.models.customer_data import DataSource, ProspectRecord
        row = (await db.execute(select(ProspectRecord, DataSource).join(DataSource, DataSource.id == ProspectRecord.source_id)
                                .where(ProspectRecord.id == rid_u))).first()
        if row is None:
            return None
        p, src = row
        return {"territory": None, "region": p.region, "segment": p.segment, "citation": f"{src.name}, row {p.row_no}"}
    return None


def range_text(ctx: dict, per_line: int = 1, max_lines: int = 6) -> str:
    """Short description of the range from the context, or neutral words when the catalogue is empty."""
    if not ctx["lines"]:
        return NEUTRAL_RANGE
    cats = list(dict.fromkeys(CATEGORY_LABEL.get(ln["category"], ln["category"].replace("_", " ").lower()) for ln in ctx["lines"]))
    shown = [f'{ln["line"]} ({", ".join(p["sku"] for p in ln["products"][:per_line])})' for ln in ctx["lines"][:max_lines]]
    more = len(ctx["lines"]) - len(shown)
    return f"{' and '.join(cats)} products such as {', '.join(shown)}" + (f" and {more} more lines" if more > 0 else "")


def citations(ctx: dict, per_line: int = 1, max_lines: int = 6) -> list[str]:
    """The records the copy used: SKUs shown, brand assets, target record."""
    out = [f'product {p["sku"]}' for ln in ctx["lines"][:max_lines] for p in ln["products"][:per_line]]
    out += [f'brand asset {a["asset_ref"]}' for a in ctx["assets"]]
    if ctx.get("target"):
        out.append(ctx["target"]["citation"])
    return out
