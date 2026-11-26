"""M48.S01.T006 canonical POVU brand/product context; no beverage placeholders (DB part needs M48_DB=1).

Unit: neutral copy for an empty catalogue, agent templates take the range from the brand_context tool, and a
regression scan that fails when a beverage reference appears in backend/app or frontend/src.
DB: empty catalogue → no products; synthetic catalogue → the prospect draft and the agent tool cite real active SKUs,
approved Brand Vault assets and the lead's CRM territory/segment; inactive SKUs and unapproved assets are never used.
"""
import os
import re
import uuid
from pathlib import Path

import pytest

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
ROOT = Path(__file__).resolve().parents[2]
BEVERAGE = re.compile(r"\b(drinks?|beverages?|juices?|cola|soda|mango|sugar|softdrinks?)\b|water\s*500|povu\s+(water|juice)", re.I)
# Genuinely generic uses: BEVERAGE is a generic industry product category (never a POVU default).
ALLOW = {
    "backend/app/models/master.py": ['BEVERAGE = "BEVERAGE"'],
    "frontend/src/lib/products.ts": ['"FOOD" | "BEVERAGE" | "PERSONAL_CARE"'],
    "frontend/src/app/dashboard/products/page.tsx": ['{ value: "BEVERAGE", label: "Beverage" }'],
}


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _scan() -> list[str]:
    hits = []
    for base, exts in (("backend/app", {".py"}), ("frontend/src", {".ts", ".tsx", ".js", ".jsx", ".json", ".md"})):
        for p in (ROOT / base).rglob("*"):
            if p.suffix not in exts or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(ROOT).as_posix()
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if BEVERAGE.search(line) and not any(a in line for a in ALLOW.get(rel, [])):
                    hits.append(f"{rel}:{n}: {line.strip()[:120]}")
    return hits


def test_no_beverage_references_in_app_or_frontend():
    assert _scan() == []


def test_scan_catches_a_new_beverage_reference(tmp_path):
    assert BEVERAGE.search("We supply POVU drinks") and BEVERAGE.search("POVU Water 500 ml") and BEVERAGE.search("Mango Juice")
    assert not BEVERAGE.search("Rinse with water; POVU AllClean 1 L (POVU-ALC-1L)")      # generic "water" is fine


def test_empty_catalogue_gives_neutral_copy_and_no_products():
    from app.services import brand_context_service as bcs
    from app.services import customer_data_service as cds
    empty = {"brand": "POVU", "assets": [], "lines": [], "claims": [], "target": None}
    assert bcs.range_text(empty) == bcs.NEUTRAL_RANGE and bcs.citations(empty) == []
    d = cds.compose({"company_name": "Duka Moja", "evidence": []}, "Rep", empty)
    assert "home and personal care range" in d["body"] and d["catalogue_empty"] and d["sources"] == []
    assert not BEVERAGE.search(d["subject"] + d["body"]) and "POVU-" not in d["body"]


def test_agent_templates_use_brand_context_not_hard_coded_products():
    from app.services import agent_service as ags
    for key in ("campaign_planner", "nurture_sequence"):
        defn = ags.TEMPLATES[key]["definition"]
        assert defn["steps"][0]["tool"] == "brand_context" and "{{s1.range}}" in str(defn) and "{{s1.sources}}" in str(defn)
        assert not BEVERAGE.search(str(defn)) and "POVU-" not in str(defn)
    assert ags.TOOLS["brand_context"]["write"] is False


@DB
@pytest.mark.asyncio
async def test_empty_catalogue_context_has_no_products():
    from sqlalchemy import update
    from app.db.session import AsyncSessionLocal
    from app.models.master import Product
    from app.services import brand_context_service as bcs
    async with AsyncSessionLocal() as db:
        await db.execute(update(Product).values(is_active=False))       # rolled back below
        ctx = await bcs.context(db)
        assert ctx["lines"] == [] and bcs.range_text(ctx) == bcs.NEUTRAL_RANGE
        assert not any(c.startswith("product ") for c in bcs.citations(ctx))
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_synthetic_catalogue_draft_cites_real_skus_assets_and_territory(monkeypatch):
    from types import SimpleNamespace
    from app.api.v1.endpoints import customer_data as api
    from app.db.session import AsyncSessionLocal
    from app.models.brand_assets import AssetStatus, AssetType, BrandAsset
    from app.models.crm import CRMRecord, CRMRecordType, CRMStatus, CRMTerritory
    from app.models.customer_data import ProspectRun
    from app.models.master import Product, ProductCategory, UnitOfMeasure
    from app.services import agent_service as ags
    from app.services import brand_context_service as bcs
    s = uuid.uuid4().hex[:6].upper()
    async with AsyncSessionLocal() as db:
        alc = Product(sku=f"POVU-ALC-1L-{s}", name="POVU AllClean Multi-Purpose Cleaner 1 L Bottle", category=ProductCategory.HOUSEHOLD,
                      description="AllClean · 1 L bottle", uom=UnitOfMeasure.PCS, is_active=True)
        plc = Product(sku=f"POVU-PLC-500ML-{s}", name="POVU PalmCare Liquid Hand Soap 500 ml Bottle", category=ProductCategory.PERSONAL_CARE,
                      description="PalmCare · 500 ml bottle", uom=UnitOfMeasure.PCS, is_active=True)
        old = Product(sku=f"POVU-OLD-{s}", name="POVU withdrawn line", category=ProductCategory.HOUSEHOLD,
                      description="Withdrawn · 1 L", uom=UnitOfMeasure.PCS, is_active=False)
        logo = BrandAsset(asset_ref=f"BV-LOGO-{s}", name="POVU logo", asset_type=AssetType.LOGO, brand="POVU", status=AssetStatus.APPROVED)
        draft_asset = BrandAsset(asset_ref=f"BV-DRAFT-{s}", name="POVU draft label", asset_type=AssetType.LABEL, brand="POVU", status=AssetStatus.DRAFT)
        terr = CRMTerritory(territory_code=f"NBO-W-{s}", territory_name="Nairobi West", region="Nairobi")
        db.add_all([alc, plc, old, logo, draft_asset, terr])
        await db.flush()
        lead = CRMRecord(record_type=CRMRecordType.LEAD, status=CRMStatus.OPEN, company_name=f"Duka Moja {s}",
                         industry_segment="supermarket", territory_id=terr.id, contact_email=f"buy{s.lower()}@example.com")
        db.add(lead)
        await db.flush()

        ctx = await bcs.context(db, target_kind="lead", target_id=str(lead.id), max_products=100000)
        skus = {p["sku"] for ln in ctx["lines"] for p in ln["products"]}
        assert {alc.sku, plc.sku} <= skus and old.sku not in skus
        assert logo.asset_ref in {a["asset_ref"] for a in ctx["assets"]} and draft_asset.asset_ref not in {a["asset_ref"] for a in ctx["assets"]}
        assert ctx["target"]["territory"] == "Nairobi West" and ctx["target"]["segment"] == "supermarket"
        assert {"AllClean", "PalmCare"} <= {ln["line"] for ln in ctx["lines"]}

        # prospect draft through the endpoint, restricted to our synthetic lines so the citations are predictable
        mine = {**ctx, "lines": [ln for ln in ctx["lines"] if any(p["sku"] in (alc.sku, plc.sku) for p in ln["products"])]}

        async def only_mine(_db, **kw):
            return mine
        monkeypatch.setattr(bcs, "context", only_mine)
        res = {"kind": "lead", "id": str(lead.id), "company_name": lead.company_name, "email": lead.contact_email,
               "can_email": True, "evidence": [{"criterion": "segment", "value": "supermarket", "citation": f"CRM lead {lead.id}"}]}
        run = ProspectRun(criteria={"segment": "supermarket"}, results=[res], created_by="tester")
        db.add(run)
        await db.flush()
        user = SimpleNamespace(full_name="Asha Rep", username="asha")
        d = await api.outreach_draft(run.id, api.OutreachIn(result_id=str(lead.id)), db, user)
        tool = await ags.tool_brand_context(db, user, {})
        assert alc.sku in d["body"] and plc.sku in d["body"] and not d["catalogue_empty"]
        assert f"product {alc.sku}" in d["sources"] and f"brand asset {logo.asset_ref}" in d["sources"]
        assert any("territory NBO-W-" in x for x in d["sources"]) and old.sku not in d["body"]
        assert not BEVERAGE.search(d["subject"] + d["body"])
        assert alc.sku in tool["range"] and alc.sku in tool["sources"] and not BEVERAGE.search(str(tool))
        await db.rollback()
