"""M47.S01.T002 one synthetic POVU flow through the real services and public endpoints (DB part needs M46_DB=1).

website lead form -> scored + routed -> sequence enrolment -> opportunity (rule-based AI prioritisation) -> customer
-> quotation with a discount needing a second person -> share link + signer code -> e-sign ACCEPTED -> sales order ->
confirm / allocate stock made by a production run (approved recipe, released, started, completed, FG QC accepted,
quarantine released) -> pick -> dispatch -> POD (invoice + GL journal) -> M-Pesa payment link with a simulated Daraja
callback -> finance confirms -> AR cleared, loyalty points; side channels: distributor portal order and field-visit
order for the same customer; SAFETY complaint -> recall -> forward/backward trace reaches the customer; NPS answer;
attribution credits the lead's UTM campaign; copilot brief with the MockProvider (no provider keys).
Plus focused tests for the integration fixes: close-won creates the customer, chat leads are routed and scored,
MRP suggestion -> production order, complaint recall refusals.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = "Povu-Portal-Pass-2026"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    import random
    ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"   # per-IP limits: re-runs stay apart
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 50000)), base_url="http://erp.test")


def _guard_db():
    from app.db.session import engine
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
    assert engine.url.port != 5432, "never the dev database"


async def _actor(db, *codes, name="POVU staff"):
    from app.models.role import Permission, Role
    from app.models.user import User
    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, module=code.split(".")[0], action=code.split(".", 1)[1], name=code, is_active=True)
            db.add(p)
            await db.flush()
        perms.append(p)
    tag = uuid.uuid4().hex
    u = User(email=f"m47-{tag[:12]}@example.com", username=f"m47{tag}", full_name=name,
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False,
             roles=[Role(name=f"POVU m47 role {tag}", is_active=True, permissions=perms)])
    db.add(u)
    await db.flush()
    return u.id


async def _load(db, uid):
    from app.models.role import Role
    from app.models.user import User
    return (await db.execute(select(User).where(User.id == uid).execution_options(populate_existing=True).options(
        selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.access_scopes),
        selectinload(User.access_scopes)))).scalar_one()


def _as(user):
    """Request user for dependency overrides (same id, same permissions as the real row)."""
    perms = [SimpleNamespace(code=p.code, module=p.module, action=p.action, is_active=True)
             for r in user.roles for p in r.permissions]
    return SimpleNamespace(id=user.id, username=user.username, email=user.email, full_name=user.full_name,
                           is_superuser=False, is_active=True, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def _callback(checkout, receipt):
    item = [{"Name": "MpesaReceiptNumber", "Value": receipt}, {"Name": "Amount", "Value": 1}]
    return {"Body": {"stkCallback": {"MerchantRequestID": "m", "CheckoutRequestID": checkout, "ResultCode": 0,
                                     "ResultDesc": "ok", "CallbackMetadata": {"Item": item}}}}


async def _balance(db, account_id) -> Decimal:
    from app.models.finance import JournalEntry, JournalLine, JournalStatus
    v = (await db.execute(select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
                          .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
                          .where(JournalLine.account_id == account_id, JournalEntry.status == JournalStatus.POSTED))).scalar_one()
    return Decimal(v)


async def _qc_template(db, name, qc_type):
    from app.models.quality import ParameterType, QCTemplate, QCTemplateParameter
    t = QCTemplate(name=name, qc_type=qc_type, is_mandatory=True, blocks_progression=True, release_required=True, is_active=True)
    db.add(t)
    await db.flush()
    db.add(QCTemplateParameter(template_id=t.id, parameter_name=f"{name} pH", parameter_type=ParameterType.NUMERIC,
                               unit="pH", target_value="7", min_value=Decimal("6"), max_value=Decimal("8"), is_critical=True))
    await db.flush()
    return t


@DB
@pytest.mark.asyncio
async def test_integrated_povu_flow(monkeypatch):
    from app.api.v1.endpoints import collections as collections_api
    from app.api.v1.endpoints import crm_pipeline as crm_api
    from app.api.v1.endpoints import quotation as quote_api
    from app.api.v1.endpoints import sales as sales_api
    from app.core.config import settings
    from app.core.deps import get_current_user
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.company import Company
    from app.models.crm import (CRMAIRecommendation, CRMLeadForm, CRMLeadSubmission, CRMOutboundMessage, CRMRecord,
                                CRMRoutingRule, CRMScoreHistory, CRMSequence, CRMSequenceEnrollment, CRMSequenceStep)
    from app.models.field_ops import CashCollection
    from app.models.field_sales import RouteStop, SalesRep, SalesRoute
    from app.models.finance import (AccountingPeriod, AccountingPostingRule, AccountType, ChartOfAccount,
                                    InventoryAccountMapping, JournalEntry, PeriodStatus)
    from app.models.inventory import Lot, Stock
    from app.models.loyalty import CustomerLoyaltyAccount, LoyaltyTier, LoyaltyTransaction
    from app.models.master import (Material, MaterialType, Product, ProductCategory, Supplier, UnitOfMeasure, Warehouse,
                                   WarehouseType)
    from app.models.nps import NPSResponse, NPSSurvey
    from app.models.payments_hub import PaymentLink
    from app.models.portal import PortalAccount, PortalAccountStatus, PortalAccountType, PortalUser, PortalUserRole
    from app.models.procurement import GoodsReceipt, GRNLine, POLine, POStatus, PurchaseOrder
    from app.models.production import ProductionOrder, ProductionOrderStatus
    from app.models.quality import QCDecision, QCInspection, QCTemplateParameter, QCTestResult, QCType
    from app.models.quotation import Quotation, QuoteStatus
    from app.models.recipe import Recipe, RecipeItem, RecipeStatus
    from app.models.sales import (Customer, Invoice, InvoiceStatus, OrderSource, SalesOrder, Shipment, ShipmentLine,
                                  ShipmentStatus, SOLine, SOStatus)
    from app.models.traceability import RecallHeader
    from app.schemas.crm import CRMCloseWonRequest, CRMConvertRequest
    from app.schemas.production import CompleteOrderRequest
    from app.schemas.quotation import QuotationCreate, QuotationLineCreate
    from app.schemas.sales import AllocateSORequest, DispatchShipmentRequest, ShipmentCreate, ShipmentLineCreate
    from app.services import ai_provider, crm_attribution_service as attribution, crm_copilot_service as copilot
    from app.services import crm_document_service as docs, crm_intelligence_service as intel
    from app.services import crm_pipeline_service as pipeline, crm_sequence_service as sequences
    from app.services import customer_feedback_service as fb, mpesa_daraja_service as daraja
    from app.services import payment_link_service as pls, production_service, recall_service, traceability_service
    from app.services.procurement_service import post_grn
    from app.services.qms_service import create_quality_gate_definition, release_lot
    from app.services.quality_service import make_decision, release_qc_quarantine

    _guard_db()
    s = uuid.uuid4().hex[:8]
    today = date.today()
    email = f"duka-{s}@example.com"
    campaign = f"povu-launch-{s}"
    # deterministic AI: no provider keys, simulators only
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(settings, "AI_PROVIDER", "auto")
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(ai_provider, "_instance", None)
    monkeypatch.setattr(settings, "MPESA_CALLBACK_SECRET", "cb-secret")
    pushes = []

    async def live_push(phone, amount, reference, description="Payment"):   # the Daraja simulator accepts the push
        cid = f"ws_CO_LIVE_{uuid.uuid4().hex[:12]}"
        pushes.append(cid)
        return cid, "MR1", {"ResponseCode": "0", "CheckoutRequestID": cid}
    monkeypatch.setattr(daraja, "_stk_push_request", live_push)

    # ── set-up: people, ledger, routing, form, sequence, product, factory ─────────────────────────────────────
    async with AsyncSessionLocal() as db:
        rep_id = await _actor(db, "crm.view_all", "crm.create_all", "crm.edit_all", "sales.view_all", "sales.create_all",
                              "sales.edit_all", "sales.convert_all", name="POVU Rep")
        mgr_id = await _actor(db, "sales.view_all", "sales.approve", "sales.approve_all", name="POVU Sales Manager")
        fin_id = await _actor(db, "finance.approve", "sales.view", name="POVU Finance")
        qa_id = await _actor(db, "quality.view", "quality.approve", "consumer_complaints.create", "consumer_complaints.view",
                             name="POVU QA Head")
        op_id = await _actor(db, name="POVU Operator")
        drv_id = await _actor(db, "sales.view", "sales.create", name="POVU Driver")
        fld_id = await _actor(db, name="POVU Field Rep")
        ar = ChartOfAccount(code=f"M47AR{s}", name="POVU trade receivables", account_type=AccountType.ASSET, currency="KES")
        rev = ChartOfAccount(code=f"M47RV{s}", name="POVU sales revenue", account_type=AccountType.REVENUE, currency="KES")
        vat = ChartOfAccount(code=f"M47TX{s}", name="POVU output VAT", account_type=AccountType.LIABILITY, currency="KES")
        mp = ChartOfAccount(code=f"M47MP{s}", name="POVU M-Pesa clearing", account_type=AccountType.ASSET, currency="KES")
        inv_acc = ChartOfAccount(code=f"M47IN{s}", name="POVU raw inventory", account_type=AccountType.ASSET)
        grni = ChartOfAccount(code=f"M47GR{s}", name="POVU GRNI", account_type=AccountType.LIABILITY)
        db.add_all([ar, rev, vat, mp, inv_acc, grni])
        await db.flush()
        prio = -int(time.time())          # this run's rules win over any left by an earlier run
        db.add_all([
            AccountingPostingRule(source_module="sales", source_event="SALES_INVOICE_ISSUED", rule_name=f"POVU invoice {s}",
                                  debit_account_id=ar.id, credit_account_id=rev.id, tax_account_id=vat.id, priority=prio,
                                  is_active=True),
            AccountingPostingRule(source_module="sales", source_event="CUSTOMER_PAYMENT_RECEIVED_MPESA",
                                  rule_name=f"POVU M-Pesa {s}", credit_account_id=ar.id, clearing_account_id=mp.id,
                                  priority=prio, is_active=True)])
        period = today.strftime("%Y-%m")
        if not await db.scalar(select(AccountingPeriod.id).where(AccountingPeriod.period_ym == period)):
            db.add(AccountingPeriod(period_ym=period, period_start=today.replace(day=1),
                                    period_end=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                                    status=PeriodStatus.OPEN, notes="Synthetic M47 period."))
        db.add(CRMRoutingRule(name=f"POVU website leads {s}", priority=prio, active=True, conditions={"source_type": "WEBSITE"},
                              method="ROUND_ROBIN", user_ids=[str(rep_id)]))
        form = CRMLeadForm(slug=f"povu-shop-{s}", name=f"POVU shop sign-up {s}", title="Stock POVU in your shop",
                           consent_text="I agree that POVU may contact me about its products.", require_consent=True)
        seq = CRMSequence(name=f"POVU welcome {s}", active_flag=True)
        db.add_all([form, seq])
        await db.flush()
        db.add(CRMSequenceStep(sequence_id=seq.id, step_no=1, delay_days=0, subject="Welcome {company_name}",
                               body="Hello {contact_name}, thank you for your interest in POVU."))
        company = Company(name=f"POVU Factory {s}", short_code=f"PV{s[:6].upper()}", country="Kenya", base_currency="KES")
        supplier = Supplier(code=f"M47-SUP-{s}", name=f"POVU base supplier {s}")
        raw_wh = Warehouse(code=f"M47-RAW-{s}", name=f"POVU raw {s}", warehouse_type=WarehouseType.RAW_MATERIAL)
        fg_wh = Warehouse(code=f"M47-FG-{s}", name=f"POVU FG {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        material = Material(code=f"M47-MAT-{s}", name=f"POVU cleaning base {s}", material_type=MaterialType.RAW,
                            uom=UnitOfMeasure.KG)
        product = Product(sku=f"POVU-ALC-1L-{s}", name=f"POVU AllClean 1 L {s}", category=ProductCategory.HOUSEHOLD,
                          uom=UnitOfMeasure.PCS, selling_price=Decimal("200"), standard_cost=Decimal("120"))
        db.add_all([company, supplier, raw_wh, fg_wh, material, product])
        await db.flush()
        raw_wh.company_id = company.id
        db.add(InventoryAccountMapping(material_id=material.id, stock_type="MATERIAL", valuation_method="FIFO",
                                       inventory_account_id=inv_acc.id, grni_account_id=grni.id, is_active=True))
        recipe = Recipe(product_id=product.id, version="1", name=f"POVU AllClean recipe {s}", status=RecipeStatus.APPROVED,
                        is_active=True)
        db.add(recipe)
        await db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, material_id=material.id, line_no=1, quantity=Decimal("1"), unit="KG"))
        fg_t = await _qc_template(db, f"POVU FG {s}", QCType.FINISHED_GOODS)
        for code, gtype, event, module in ((f"M47FGR_{s}", "FINISHED_GOODS_QUALITY", "on_finished_goods_release", "Inventory"),
                                           (f"M47DSP_{s}", "FINISHED_GOODS_DISPATCH_QUALITY", "on_dispatch", "SALES")):
            await create_quality_gate_definition(db, {
                "code": code, "name": f"POVU {code}", "gate_type": gtype, "trigger_event": event, "target_module": module,
                "effective_from": today, "is_active": True, "is_mandatory": True, "required_template_ids": [fg_t.id]})
        delivery_survey = NPSSurvey(title=f"POVU delivery {s}", target_type="CUSTOMER", trigger="DELIVERY",
                                    question_text="How was your POVU delivery?")
        tier = LoyaltyTier(tier_code=f"PV-{s}", tier_name=f"POVU Bronze {s}", min_lifetime_points=0,
                           points_per_100_spend=Decimal("1"))
        db.add_all([delivery_survey, tier])
        # raw material received through a purchase order and GRN
        po = PurchaseOrder(po_no=f"M47-PO-{s}", supplier_id=supplier.id, company_id=company.id, currency="KES",
                           exchange_rate=Decimal("1"), order_date=today, expected_delivery_date=today,
                           status=POStatus.ORDERED, created_by_id=op_id)
        db.add(po)
        await db.flush()
        po_line = POLine(po_id=po.id, line_no=1, material_id=material.id, ordered_quantity=Decimal("100"), unit="KG",
                         unit_price=Decimal("1"))
        db.add(po_line)
        await db.flush()
        grn = GoodsReceipt(grn_no=f"M47-GRN-{s}", po_id=po.id, company_id=company.id, received_date=today,
                           received_by_id=op_id, warehouse_id=raw_wh.id)
        db.add(grn)
        await db.flush()
        db.add(GRNLine(grn_id=grn.id, po_line_id=po_line.id, material_id=material.id, unit="KG",
                       received_quantity=Decimal("100"), accepted_quantity=Decimal("100"), rejected_quantity=Decimal("0"),
                       lot_number=f"POVU-RAW-{s}"))
        await db.commit()
        ids = SimpleNamespace(form=form.id, seq=seq.id, product=product.id, material=material.id, raw_wh=raw_wh.id,
                              fg_wh=fg_wh.id, recipe=recipe.id, grn=grn.id, ar=ar.id, rev=rev.id, vat=vat.id, mp=mp.id,
                              survey=delivery_survey.id, tier=tier.id)
        await post_grn(db, await db.get(GoodsReceipt, ids.grn), op_id)
        await db.commit()
        raw_lot_id = (await db.execute(select(Lot.id).where(Lot.lot_number == f"POVU-RAW-{s}"))).scalar_one()

    async with _client() as c:
        # ── 1. website lead form → scored + routed ──────────────────────────────────────────────────────────────
        r = await c.post(f"/api/v1/public/lead-forms/povu-shop-{s}/submit", json={
            "company_name": f"Duka Moja {s}", "contact_person_name": "Achieng Otieno", "contact_email": email,
            "contact_phone": "0712345678", "consent": True, "utm_source": "facebook", "utm_medium": "cpc",
            "utm_campaign": campaign, "message": "We want POVU AllClean for our shop."})
        assert r.status_code == 202, r.text
    async with AsyncSessionLocal() as db:
        sub = (await db.execute(select(CRMLeadSubmission).where(CRMLeadSubmission.form_id == ids.form))).scalar_one()
        assert sub.status == "ACCEPTED" and sub.crm_record_id and sub.utm_campaign == campaign
        lead = await db.get(CRMRecord, sub.crm_record_id)
        lead_id = lead.id
        assert lead.assigned_rep_id == str(rep_id) and "[Routing]" in lead.notes          # FIX 2: form leads are routed
        hist = (await db.execute(select(CRMScoreHistory).where(CRMScoreHistory.crm_record_id == lead_id))).scalars().all()
        assert len(hist) == 1 and hist[0].score == lead.lead_score and lead.temperature is not None
        expected_score, _, _ = intel.compute_score((await intel._records_for_scoring(db, CRMRecord.id == lead_id))[0],
                                                   await intel.active_rules(db))
        assert lead.lead_score == expected_score

        # ── 2. sequence enrolment, first step queued ────────────────────────────────────────────────────────────
        enr = await sequences.enroll(db, await db.get(CRMSequence, ids.seq), lead, "povu-rep")
        await db.commit()
        assert enr.status == "ACTIVE"
        counts = await sequences.advance(db, datetime.now(timezone.utc) + timedelta(minutes=1))
        assert counts["queued"] >= 1
        msg = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.crm_record_id == lead_id,
                                                                 CRMOutboundMessage.purpose == "SEQUENCE"))).scalar_one()
        assert msg.subject == f"Welcome Duka Moja {s}" and msg.status != "SUPPRESSED"
        enr = (await db.execute(select(CRMSequenceEnrollment).where(CRMSequenceEnrollment.id == enr.id)
                                .execution_options(populate_existing=True))).scalar_one()
        assert enr.status == "COMPLETED"

        # ── 3. opportunity + rule-based AI prioritisation (no provider) ─────────────────────────────────────────
        opp = await pipeline.convert_to_opportunity(db, str(lead_id), CRMConvertRequest(
            expected_revenue=Decimal("3400"), expected_close_date=today + timedelta(days=14)))
        assert opp.record_type.value == "OPPORTUNITY" and opp.opportunity_code
        recs = await pipeline.run_lead_prioritization(db)
        assert any(x.crm_record_id == lead_id and x.title.startswith("Closing Soon") for x in recs)
        assert (await db.execute(select(func.count()).select_from(CRMAIRecommendation).where(
            CRMAIRecommendation.crm_record_id == lead_id))).scalar_one() >= 1
        assert type(ai_provider.get_ai_provider()).__name__ == "MockProvider"

        # ── 4. lead → customer (FIX 1 endpoint), idempotent ─────────────────────────────────────────────────────
        rep = await _load(db, rep_id)
        out = await crm_api.ensure_record_customer(str(lead_id), db, rep)
        assert out["created"] is True and out["customer_name"] == f"Duka Moja {s}"
        again = await crm_api.ensure_record_customer(str(lead_id), db, await _load(db, rep_id))
        assert again == {**out, "created": False}
        cust_id = uuid.UUID(out["customer_id"])
        cust = await db.get(Customer, cust_id)
        assert cust.email == email and cust.currency == "KES"
        assert (await db.get(CRMRecord, lead_id)).assigned_customer_id == cust_id

        # ── 5. production run: approved recipe → released → started → completed → FG QC → quarantine release ──
        order = ProductionOrder(order_no=f"M47-MO-{s}", product_id=ids.product, recipe_id=ids.recipe,
                                planned_quantity=Decimal("50"), uom="PCS", status=ProductionOrderStatus.PLANNED,
                                target_warehouse_id=ids.fg_wh, source_warehouse_id=ids.raw_wh, created_by=op_id,
                                scheduled_start=datetime.now(timezone.utc), scheduled_end=datetime.now(timezone.utc),
                                batch_no=f"POVU-FG-{s}")
        db.add(order)
        await db.commit()
        mo = order.id
        await production_service.approve_order(db, await db.get(ProductionOrder, mo), qa_id)
        await db.commit()
        await production_service.release_order(db, await db.get(ProductionOrder, mo), op_id)
        await db.commit()
        await production_service.start_order(db, await db.get(ProductionOrder, mo),
                                             datetime.now(timezone.utc) - timedelta(minutes=30), op_id)
        await db.commit()
        await production_service.complete_order(db, await db.get(ProductionOrder, mo), CompleteOrderRequest(
            actual_quantity=Decimal("50"), source_warehouse_id=ids.raw_wh, material_lot_ids={ids.material: raw_lot_id}), op_id)
        await db.commit()
        assert (await db.get(ProductionOrder, mo)).status == ProductionOrderStatus.COMPLETED
        fg_lot = (await db.execute(select(Lot).where(Lot.lot_number == f"POVU-FG-{s}", Lot.product_id == ids.product))).scalar_one()
        fg_lot_id = fg_lot.id
        fg_stock = (await db.execute(select(Stock).where(Stock.lot_id == fg_lot_id))).scalar_one()
        fg_stock_id = fg_stock.id
        assert fg_stock.quantity_on_hand == Decimal("50") and fg_stock.is_blocked is True            # quarantined
        # one FG inspection per required template (a re-run on the same database adds the earlier run's gate too)
        insp_ids = (await db.execute(select(QCInspection.id).where(QCInspection.production_order_id == mo,
                                                                   QCInspection.qc_type == QCType.FINISHED_GOODS))).scalars().all()
        assert insp_ids
        for insp_id in insp_ids:
            insp = await db.get(QCInspection, insp_id)
            for param in (await db.execute(select(QCTemplateParameter).where(
                    QCTemplateParameter.template_id == insp.template_id))).scalars():
                db.add(QCTestResult(inspection_id=insp_id, template_parameter_id=param.id, parameter_name=param.parameter_name,
                                    parameter_type=param.parameter_type, unit=param.unit, numeric_value=Decimal("7"),
                                    min_spec=param.min_value, max_spec=param.max_value, is_passed=True,
                                    is_critical=param.is_critical, tested_by_id=qa_id))
            await db.commit()
            await make_decision(db, await db.get(QCInspection, insp_id), QCDecision.ACCEPT, qa_id, "POVU FG accepted", False, False)
            await db.commit()
        await release_qc_quarantine(db, await db.get(QCInspection, insp_ids[0]), qa_id, "FG release")
        await db.commit()
        await release_lot(db, fg_lot_id, qa_id, "POVU QA lot release")
        await db.commit()
        fg_stock = await db.get(Stock, fg_stock_id)
        await db.refresh(fg_stock)
        assert fg_stock.is_blocked is False
        backward = await traceability_service.backward_trace(db, fg_lot_id)
        assert str(raw_lot_id) in repr(backward)

        # ── 6. quotation with a discount that needs a second person ─────────────────────────────────────────────
        rep, mgr = await _load(db, rep_id), await _load(db, mgr_id)
        q = await quote_api.create_quote(QuotationCreate(
            customer_id=cust_id, crm_record_id=lead_id, quote_date=today, valid_until=today + timedelta(days=30), currency="KES",
            lines=[QuotationLineCreate(line_no=1, product_id=ids.product, qty=Decimal("20"), unit="PCS",
                                       unit_price=Decimal("200"), discount_pct=Decimal("15"), tax_rate=Decimal("16"))]), db, rep)
        quote_id = q.id
        assert q.approval_status == "PENDING_DISCOUNT" and q.discount_approval_required is True
        with pytest.raises(HTTPException) as e:
            await quote_api.send_quote(quote_id, db, rep)
        assert e.value.status_code == 409
        await db.rollback()
        with pytest.raises(HTTPException) as e:
            await quote_api.approve_discount(quote_id, quote_api.DiscountDecisionIn(), db, await _load(db, rep_id))
        assert e.value.status_code == 403
        await db.rollback()
        ok = await quote_api.approve_discount(quote_id, quote_api.DiscountDecisionIn(), db, await _load(db, mgr_id))
        assert ok.approval_status == "DISCOUNT_APPROVED"
        # CPQ multi-step levels read the same percentages: 15 % needs level 1 only (above 10 %), not finance (above 25 %)
        from app.services import cpq_service as cpq
        st = await cpq.approval_state(db, await cpq._quote(db, quote_id))
        assert st["discount_pct"] == "15.00" and [lv["level"] for lv in st["levels"]] == [1] and not st["complete"]
        with pytest.raises(cpq.CPQError):
            await cpq.approve_level(db, quote_id, await _load(db, rep_id))              # the price setter
        await db.rollback()
        assert (await cpq.approve_level(db, quote_id, await _load(db, mgr_id)))["complete"] is True
        await db.commit()
        q_row = await cpq._quote(db, quote_id)
        assert (q_row.total_amount, q_row.tax_amount, q_row.grand_total) == (Decimal("3400.0000"), Decimal("544.0000"), Decimal("3944.0000"))
        sent = await quote_api.send_quote(quote_id, db, await _load(db, rep_id))
        assert sent.status == QuoteStatus.SENT
        token = (await quote_api.create_share_link(quote_id, quote_api.ShareLinkIn(), db, await _load(db, rep_id)))["url"].rsplit("/d/", 1)[1]
        link = await docs.resolve(db, token)
        code = await docs.request_signer_code(db, link, email)        # the code e-mailed to the address on file
        await db.commit()
        assert code and len(code) == 6

    # ── 7. customer opens the link and e-signs ──────────────────────────────────────────────────────────────────
    async with _client() as c:
        doc = await c.get(f"/api/v1/public/documents/{token}")
        assert doc.status_code == 200, doc.text
        d = await c.post(f"/api/v1/public/documents/{token}/decision", json={
            "decision": "ACCEPTED", "signer_name": "Achieng Otieno", "signer_email": email,
            "document_hash": doc.json()["document_hash"], "agree": True, "code": code})
        assert d.status_code == 200 and d.json()["decision"] == "ACCEPTED", d.text

    async with AsyncSessionLocal() as db:
        assert (await db.get(Quotation, quote_id)).status == QuoteStatus.ACCEPTED
        won = await pipeline.close_won(db, str(lead_id), CRMCloseWonRequest(final_revenue=Decimal("3400")))
        assert won.status.value == "WON" and won.assigned_customer_id == cust_id    # already linked: not duplicated
        # ── 8. sales order → confirm → allocate from the produced FG lot ───────────────────────────────────────
        conv = await quote_api.convert_to_so(quote_id, db, await _load(db, rep_id))
        so_id = uuid.UUID(str(conv["so_id"]))
        line = (await db.execute(select(SOLine).where(SOLine.so_id == so_id))).scalar_one()
        assert (line.ordered_quantity, line.discount_pct, line.tax_rate) == (Decimal("20"), Decimal("0.1500"), Decimal("0.1600"))
        assert (await sales_api.confirm_order(so_id, db, await _load(db, rep_id))).status == SOStatus.CONFIRMED
        alloc = await sales_api.allocate_order(so_id, AllocateSORequest(warehouse_id=ids.fg_wh), db, await _load(db, rep_id))
        assert alloc.status == SOStatus.ALLOCATED
        fg_stock = await db.get(Stock, fg_stock_id)
        await db.refresh(fg_stock)
        assert fg_stock.quantity_reserved == Decimal("20")
        # ── 9. pick → dispatch ──────────────────────────────────────────────────────────────────────────────────
        ship = await sales_api.create_shipment(ShipmentCreate(
            shipment_no=f"M47-SH-{s}", so_id=so_id, warehouse_id=ids.fg_wh, scheduled_date=today,
            lines=[ShipmentLineCreate(so_line_id=line.id, product_id=ids.product, lot_id=fg_lot_id, quantity=Decimal("20"),
                                      unit="PCS")]), db, await _load(db, op_id))
        ship_id = ship.id
        await sales_api.start_picking(ship_id, db, await _load(db, op_id))
        ship_line_id = (await db.execute(select(ShipmentLine.id).where(ShipmentLine.shipment_id == ship_id))).scalar_one()
        await sales_api.pick_line(ship_id, ship_line_id, db, await _load(db, op_id))
        assert (await db.get(Shipment, ship_id)).status == ShipmentStatus.PACKED
        disp = await sales_api.dispatch_shipment(ship_id, DispatchShipmentRequest(), db, await _load(db, op_id))
        assert disp.status == ShipmentStatus.DISPATCHED
        fg_stock = await db.get(Stock, fg_stock_id)
        await db.refresh(fg_stock)
        assert fg_stock.quantity_on_hand == Decimal("30") and fg_stock.quantity_reserved == Decimal("0")
        drv = _as(await _load(db, drv_id))

    # ── 10. proof of delivery on the office route invoices (FIX 5), idempotent ─────────────────────────────────────
    app.dependency_overrides[get_current_user] = lambda: drv
    try:
        async with _client() as c:
            body = {"shipment_id": str(ship_id), "received_by": "Achieng Otieno", "signature_text": "AO"}
            p1 = await c.post("/api/v1/delivery/pod", json=body)
            assert p1.status_code == 201, p1.text
            p2 = await c.post("/api/v1/delivery/pod", json=body)
            assert p2.json()["id"] == p1.json()["id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        assert (await db.get(Shipment, ship_id)).status == ShipmentStatus.DELIVERED
        invs = (await db.execute(select(Invoice).where(Invoice.shipment_id == ship_id))).scalars().all()
        assert len(invs) == 1
        inv = invs[0]
        inv_id = inv.id
        assert (inv.status, inv.subtotal, inv.tax_amount, inv.total_amount) == (
            InvoiceStatus.ISSUED, Decimal("3400.00"), Decimal("544.00"), Decimal("3944.00"))
        je = (await db.execute(select(JournalEntry).where(JournalEntry.source_event == "SALES_INVOICE_ISSUED",
                                                          JournalEntry.source_id == inv_id))).scalar_one()
        assert je.is_posted
        assert await _balance(db, ids.ar) == Decimal("3944.00")
        assert await _balance(db, ids.rev) == Decimal("-3400.00") and await _balance(db, ids.vat) == Decimal("-544.00")
        assert (await db.get(SalesOrder, so_id)).status == SOStatus.INVOICED
        # loyalty enrolment before the customer pays
        db.add(CustomerLoyaltyAccount(customer_id=cust_id, tier_id=ids.tier, total_points=0, lifetime_points=0))
        link, pay_token = await pls.create(db, inv_id, fin_id, 14, False)
        await db.commit()
        link_id = link.id

    # ── 11. M-Pesa payment link, simulated Daraja callback ─────────────────────────────────────────────────────────
    async with _client() as c:
        page = (await c.get(f"/api/v1/public/pay/{pay_token}")).json()
        assert page["amount_due"] == "3944.00"
        r = await c.post(f"/api/v1/public/pay/{pay_token}/mpesa", json={"phone": "0712345678"})
        assert r.status_code == 200 and r.json()["simulated"] is False, r.text
        cb = await c.post("/api/v1/integrations/mpesa/callback?token=cb-secret", json=_callback(pushes[0], f"QP{s.upper()}"))
        assert cb.status_code == 200
        assert (await c.get(f"/api/v1/public/pay/{pay_token}")).json()["status"] == "PAID"
    async with AsyncSessionLocal() as db:
        col = (await db.execute(select(CashCollection).where(CashCollection.invoice_id == inv_id))).scalar_one()
        assert col.status == "PENDING" and col.amount == Decimal("3944.00") and col.method == "MPESA"
        assert (await db.get(Invoice, inv_id)).paid_amount == Decimal("0")            # not money in the books yet
        confirmed = await collections_api.confirm(col.id, db, await _load(db, fin_id))
        assert confirmed["status"] == "CONFIRMED"
        inv = await db.get(Invoice, inv_id)
        await db.refresh(inv)
        assert inv.status == InvoiceStatus.PAID and inv.paid_amount == inv.total_amount
        assert await _balance(db, ids.ar) == Decimal("0")                              # AR cleared in the ledger
        assert await _balance(db, ids.mp) == Decimal("3944.00")
        assert (await db.get(PaymentLink, link_id)).status == "PAID"
        # ── 12. loyalty points for the paid invoice ─────────────────────────────────────────────────────────────
        txs = (await db.execute(select(LoyaltyTransaction).where(LoyaltyTransaction.reference_id == str(inv_id)))).scalars().all()
        assert [t.points_delta for t in txs] == [39]                                   # 3944 / 100 x 1 point
        assert (await fb.loyalty_summary(db, cust_id))["balance"] == 39
        # ── 13. NPS for the delivered order ─────────────────────────────────────────────────────────────────────
        offered = {(o["survey_id"], o["so_id"]) for o in await fb.open_surveys(db, cust_id)}
        assert (str(ids.survey), str(so_id)) in offered
        await fb.answer(db, cust_id, ids.survey, so_id, 9, "On time, POVU AllClean cartons complete", "portal")
        await db.commit()
        assert (await db.execute(select(NPSResponse.score).where(NPSResponse.customer_id == cust_id,
                                                                 NPSResponse.so_id == so_id))).scalar_one() == 9
        # side-channel set-up: portal login for the shop, field rep route with the shop on it
        acc = PortalAccount(account_code=f"PA-{s}", account_type=PortalAccountType.DISTRIBUTOR,
                            linked_customer_id=str(cust_id), portal_status=PortalAccountStatus.ACTIVE)
        db.add(acc)
        await db.flush()
        db.add(PortalUser(portal_account_id=acc.id, full_name="Achieng Otieno", email=f"portal-{s}@example.com",
                          password_hash=hash_password(PW), role_type=PortalUserRole.BUYER, is_active=True))
        frep = SalesRep(code=f"M47-REP-{s}", name="POVU Field Rep", user_id=fld_id)
        db.add(frep)
        await db.flush()
        route = SalesRoute(code=f"M47-RT-{s}", name="Westlands route", assigned_rep_id=frep.id)
        db.add(route)
        await db.flush()
        db.add(RouteStop(route_id=route.id, customer_id=cust_id, stop_sequence=1))
        await db.commit()
        fld = _as(await _load(db, fld_id))
        qa = _as(await _load(db, qa_id))

    # ── 14. distributor portal order and 15. field-visit order for the same customer ───────────────────────────────
    tomorrow = (today + timedelta(days=1)).isoformat()
    async with _client() as c:
        assert (await c.post("/api/v1/portal-self/auth/login", json={"email": f"portal-{s}@example.com", "password": PW})).status_code == 200
        po_r = await c.post("/api/v1/portal-self/orders", json={"client_ref": f"portal-{s}", "requested_delivery_date": tomorrow,
                                                                 "lines": [{"product_id": str(ids.product), "quantity": "10"}]})
        assert po_r.status_code == 201, po_r.text
        portal_so = uuid.UUID(po_r.json()["id"])
    app.dependency_overrides[get_current_user] = lambda: fld
    try:
        async with _client() as c:
            v = await c.post("/api/v1/field/visits", json={"client_ref": f"visit-{s}", "customer_id": str(cust_id),
                                                           "outcome": "ORDERED", "lat": "-1.2650", "lng": "36.8040"})
            assert v.status_code == 201, v.text
            fo = await c.post("/api/v1/field/orders", json={"client_ref": f"field-{s}", "customer_id": str(cust_id),
                                                            "requested_delivery_date": tomorrow, "visit_id": v.json()["id"],
                                                            "lines": [{"product_id": str(ids.product), "quantity": "5"}]})
            assert fo.status_code == 201, fo.text
            field_so = uuid.UUID(fo.json()["id"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        for oid, src in ((portal_so, None), (field_so, OrderSource.FIELD_SALES)):
            so = await db.get(SalesOrder, oid)
            assert so.customer_id == cust_id and so.status == SOStatus.DRAFT
            if src:
                assert so.source == src
            assert (await sales_api.confirm_order(oid, db, await _load(db, rep_id))).status == SOStatus.CONFIRMED

    # ── 16. SAFETY complaint on the FG lot → recall (FIX 4) → trace reaches the customer ──────────────────────────
    app.dependency_overrides[get_current_user] = lambda: qa
    try:
        async with _client() as c:
            cc = await c.post("/api/v1/consumer-complaints/", json={
                "consumer_name": "Wanjiku", "channel": "PHONE", "product_name": f"POVU AllClean 1 L {s}",
                "lot_number": f"POVU-FG-{s}", "severity": "SAFETY", "description": "Skin irritation after use"})
            assert cc.status_code == 201 and cc.json()["recall_triggered_flag"] is True, cc.text
            rc = await c.post(f"/api/v1/consumer-complaints/{cc.json()['id']}/initiate-recall")
            assert rc.status_code == 201, rc.text
            assert rc.json()["source_lot_id"] == str(fg_lot_id) and rc.json()["complaint"]["recall_ref"] == rc.json()["recall_no"]
            assert (await c.post(f"/api/v1/consumer-complaints/{cc.json()['id']}/initiate-recall")).status_code == 409
            recall_id = uuid.UUID(rc.json()["recall_id"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        recall = await db.get(RecallHeader, recall_id)
        assert str(recall.linked_complaint_id) == cc.json()["id"] and recall.source_lot_id == fg_lot_id
        scope = await recall_service.calculate_scope(db, recall_id)
        await db.commit()
        assert fg_lot_id in {ln.affected_lot_id for ln in scope}
        await recall_service.contain_recall(db, recall_id)
        await db.commit()
        impacts = await recall_service.build_customer_impact(db, recall_id)
        await db.commit()
        assert cust_id in {i.customer_id for i in impacts}
        forward = await traceability_service.forward_trace(db, fg_lot_id)
        assert str(cust_id) in repr(forward)
        forward_raw = await traceability_service.forward_trace(db, raw_lot_id)       # raw material lot reaches the shop too
        assert str(cust_id) in repr(forward_raw)

        # ── 17. attribution credits the lead's UTM campaign ─────────────────────────────────────────────────────
        rows = (await db.execute(select(SOLine.ordered_quantity, SOLine.unit_price, SOLine.discount_pct).where(
            SOLine.so_id.in_([so_id, portal_so, field_so])))).all()
        expected = sum((q * p * (1 - (d or 0)) for q, p, d in rows), Decimal("0")).quantize(Decimal("0.01"))
        assert expected == Decimal("6400.00")                                          # 3400 quote + 2000 portal + 1000 field
        rep_first = await attribution.report(db, today - timedelta(days=1), today + timedelta(days=1), "first")
        assert rep_first["reconciled"] is True
        row = next(x for x in rep_first["rows"] if x["source"] == f"facebook / {campaign}")
        assert row["revenue"] == {"KES": "6400.00"} and row["orders"] == 3 and row["won"] == 1 and row["repeat_customers"] == 1

        # ── 18. copilot brief, deterministic (MockProvider, no keys) ────────────────────────────────────────────
        brief = await copilot.brief(db, await db.get(Customer, cust_id), await _load(db, mgr_id))
        assert brief["mode"] == "rule_based" and brief["evidence"] and brief["draft"]["subject"].endswith(f"Duka Moja {s}")


@DB
@pytest.mark.asyncio
async def test_close_won_creates_customer_and_endpoint_links_existing():
    from app.api.v1.endpoints import crm_pipeline as crm_api
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.crm import CRMRecord, CRMRecordType, CRMSourceType
    from app.models.sales import Customer
    from app.schemas.crm import CRMCloseWonRequest
    from app.services import crm_pipeline_service as pipeline

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        rep_id = await _actor(db, "crm.view_all", "crm.edit_all")
        a = CRMRecord(record_type=CRMRecordType.OPPORTUNITY, company_name=f"Duka Mbili {s}", lead_code=f"L-M47A-{s}",
                      opportunity_code=f"O-M47A-{s}", contact_email=f"mbili-{s}@example.com", source_type=CRMSourceType.EVENT,
                      activities=[], interest_lines=[])
        existing = Customer(code=f"M47-EX-{s}", name=f"Duka Tatu Ltd {s}", email=f"tatu-{s}@example.com", currency="KES")
        b = CRMRecord(record_type=CRMRecordType.LEAD, company_name=f"Duka Tatu {s}", lead_code=f"L-M47B-{s}",
                      contact_email=f"TATU-{s}@example.com", activities=[], interest_lines=[])
        for row in (a, existing, b):     # one at a time: the stage-history rows are written in before_flush
            db.add(row)
            await db.flush()
        await db.commit()
        won = await pipeline.close_won(db, str(a.id), CRMCloseWonRequest())
        assert won.assigned_customer_id is not None
        cust = await db.get(Customer, won.assigned_customer_id)
        assert cust.name == f"Duka Mbili {s}" and cust.code == f"C-O-M47A-{s}" and cust.email == f"mbili-{s}@example.com"
        out = await crm_api.ensure_record_customer(str(b.id), db, await _load(db, rep_id))   # e-mail match, case-insensitive
        assert out == {"customer_id": str(existing.id), "customer_code": existing.code, "customer_name": existing.name,
                       "created": False}
        events = (await db.execute(select(AuditLog.event_type).where(AuditLog.target_id.in_([str(a.id), str(b.id)])))).scalars().all()
        assert sorted(events) == ["crm.customer_created", "crm.customer_linked"]
        viewer_id = await _actor(db, "crm.view_all")
        await db.commit()
        with pytest.raises(HTTPException) as e:          # the dependency needs crm.edit; scope check refuses a view-only user
            await crm_api.ensure_record_customer(str(b.id), db, await _load(db, viewer_id))
        assert e.value.status_code == 403


@DB
@pytest.mark.asyncio
async def test_chat_lead_is_routed_and_scored():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord, CRMRoutingRule, CRMScoreHistory
    from app.services import crm_chat_service as chat

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        rep_id = await _actor(db, "crm.view")
        db.add(CRMRoutingRule(name=f"POVU chat {s}", priority=-int(time.time()), active=True,
                              conditions={"source_type": "WEBSITE", "source_detail": "live chat"}, method="FIXED",
                              user_ids=[str(rep_id)]))
        await db.commit()
        sess, _ = await chat.start(db, ip=f"10.9.{int(s[:2], 16)}.{int(s[2:4], 16)}", name="Baraka", email=f"chat-{s}@example.com", consent=True,
                                   page_url="https://povu-demo.test/shop", honeypot=None)
        await db.commit()
        lead = await db.get(CRMRecord, sess.crm_record_id)
        assert lead.assigned_rep_id == str(rep_id) and "[Routing]" in lead.notes
        assert (await db.execute(select(func.count()).select_from(CRMScoreHistory).where(
            CRMScoreHistory.crm_record_id == lead.id))).scalar_one() == 1


@DB
@pytest.mark.asyncio
async def test_mrp_suggestion_converts_to_a_valid_production_order():
    from app.db.session import AsyncSessionLocal
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
    from app.models.mrp import MRPRun, MRPRunStatus, MRPSuggestion, SuggestionStatus, SuggestionType
    from app.models.production import ProductionOrder, ProductionOrderStatus
    from app.models.recipe import Recipe, RecipeStatus
    from app.services.mrp_service import convert_suggestion_to_production_order

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        user_id = await _actor(db)
        wh = Warehouse(code=f"M47-MRPWH-{s}", name="POVU FG Ruiru", warehouse_type=WarehouseType.FINISHED_GOODS)
        prod = Product(sku=f"POVU-ALC-1L-{s}", name=f"POVU AllClean 1 L {s}", category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        bare = Product(sku=f"POVU-WCP-1KG-{s}", name=f"POVU WhiteCare 1 kg {s}", category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        db.add_all([wh, prod, bare])
        await db.flush()
        recipe = Recipe(product_id=prod.id, version="1", name=f"POVU AllClean recipe {s}", status=RecipeStatus.APPROVED, is_active=True)
        run = MRPRun(run_no=f"MRP-M47-{s}", run_date=date.today(), status=MRPRunStatus.COMPLETED, warehouse_id=wh.id)
        db.add_all([recipe, run])
        await db.flush()
        need = date.today() + timedelta(days=5)
        sug = MRPSuggestion(run_id=run.id, suggestion_type=SuggestionType.PRODUCTION, status=SuggestionStatus.APPROVED,
                            product_id=prod.id, suggested_qty=Decimal("240"), uom="PCS", required_date=need,
                            planned_start_date=date.today() + timedelta(days=2))
        no_recipe = MRPSuggestion(run_id=run.id, suggestion_type=SuggestionType.PRODUCTION, status=SuggestionStatus.APPROVED,
                                  product_id=bare.id, suggested_qty=Decimal("10"), uom="PCS", required_date=need)
        db.add_all([sug, no_recipe])
        await db.commit()
        order = await convert_suggestion_to_production_order(db, sug, user_id)
        await db.commit()
        order = await db.get(ProductionOrder, order.id)
        assert (order.planned_quantity, order.recipe_id, order.target_warehouse_id, order.status) == (
            Decimal("240.000"), recipe.id, wh.id, ProductionOrderStatus.PLANNED)
        assert order.scheduled_start.date() == date.today() + timedelta(days=2) and order.scheduled_end.date() == need
        assert sug.status == SuggestionStatus.CONVERTED and sug.converted_production_order_id == order.id
        with pytest.raises(HTTPException) as e:
            await convert_suggestion_to_production_order(db, no_recipe, user_id)
        assert e.value.status_code == 422


@DB
@pytest.mark.asyncio
async def test_complaint_recall_refusals():
    from app.api.v1.endpoints import consumer_complaints as cc_api
    from app.db.session import AsyncSessionLocal
    from app.models.consumer_complaints import ComplaintSeverity, ConsumerComplaint

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        qa_id = await _actor(db, "quality.approve")
        quality = ConsumerComplaint(complaint_ref=f"CC-M47-Q-{s}", product_name="POVU AllClean 1 L", lot_number=f"NOPE-{s}",
                                    severity=ComplaintSeverity.QUALITY, description="Cap loose")
        unknown = ConsumerComplaint(complaint_ref=f"CC-M47-S-{s}", product_name="POVU AllClean 1 L", lot_number=f"NOPE-{s}",
                                    severity=ComplaintSeverity.SAFETY, description="Odd smell", recall_triggered_flag=True)
        db.add_all([quality, unknown])
        await db.commit()
        qa = await _load(db, qa_id)
        for row_id, status in ((quality.id, 409), (unknown.id, 422)):
            with pytest.raises(HTTPException) as e:
                await cc_api.initiate_recall_from_complaint(row_id, db, qa)
            assert e.value.status_code == status
            await db.rollback()
