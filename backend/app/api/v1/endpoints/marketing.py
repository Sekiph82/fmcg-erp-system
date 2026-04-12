"""
Marketing Module API
────────────────────
Campaigns · Promotions · Segments · CRM · Visits
Spend · Surveys · Influencers · Social · E-commerce · Ads
AI Optimizer · Analytics
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User

from app.models.marketing import (
    AdPerformance, BrandSpend, Campaign, ChannelStock,
    CRMProfile, CustomerInteraction, CustomerSegment, CustomerVisit,
    Influencer, InfluencerAttribution, InfluencerCampaignLink,
    OptimizerRun, OptimizerStatus, MarketingPromotion as Promotion, ReturnAnalytics,
    SocialMediaActivity, Store, StorePerformance, ProductChannelPerformance,
    Survey, TradeSpend, CampaignStatus, ApprovalStatus, StorePlatform,
)
from app.schemas.marketing import (
    AdPerformanceCreate, AdPerformanceRead, AdPerformanceUpdate,
    BrandSpendCreate, BrandSpendRead, BrandSpendUpdate,
    CampaignCreate, CampaignRead, CampaignUpdate,
    CRMProfileCreate, CRMProfileRead, CRMProfileUpdate,
    InteractionCreate, InteractionRead,
    InfluencerAttributionCreate, InfluencerAttributionRead,
    InfluencerCreate, InfluencerLinkCreate, InfluencerLinkRead, InfluencerLinkUpdate,
    InfluencerRead, InfluencerUpdate,
    OptimizerApprove, OptimizerRunCreate, OptimizerRunRead,
    ChannelStockCreate, ChannelStockRead, ChannelStockUpdate,
    EcommerceAnalytics,
    ProductChannelPerfCreate, ProductChannelPerfRead, ProductChannelPerfUpdate,
    PromotionCreate, PromotionRead, PromotionUpdate,
    ReturnAnalyticsCreate, ReturnAnalyticsRead, ReturnAnalyticsUpdate,
    SegmentCreate, SegmentRead, SegmentUpdate,
    SocialActivityCreate, SocialActivityRead, SocialActivityUpdate,
    StoreCreate, StoreRead, StoreUpdate,
    StorePerformanceCreate, StorePerformanceRead, StorePerformanceUpdate,
    SurveyCreate, SurveyRead, SurveyUpdate,
    TradeSpendCreate, TradeSpendRead, TradeSpendUpdate,
    VisitCreate, VisitRead, VisitUpdate,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# CAMPAIGNS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/campaigns", response_model=List[CampaignRead],
            dependencies=[Depends(require_permission("campaigns", "view"))])
async def list_campaigns(
    status:     Optional[str]  = Query(None),
    region:     Optional[str]  = Query(None),
    skip:       int            = Query(0, ge=0),
    limit:      int            = Query(50, le=200),
    db:         AsyncSession   = Depends(get_db),
):
    q = select(Campaign).order_by(Campaign.start_date.desc())
    if status:
        q = q.where(Campaign.status == status)
    if region:
        q = q.where(Campaign.region == region)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/campaigns", response_model=CampaignRead, status_code=201,
             dependencies=[Depends(require_permission("campaigns", "create"))])
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    obj = Campaign(**data.model_dump(), owner_user_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/campaigns/{cid}", response_model=CampaignRead,
            dependencies=[Depends(require_permission("campaigns", "view"))])
async def get_campaign(cid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Campaign).where(Campaign.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Campaign not found")
    return obj


@router.patch("/campaigns/{cid}", response_model=CampaignRead,
              dependencies=[Depends(require_permission("campaigns", "edit"))])
async def update_campaign(cid: str, data: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Campaign).where(Campaign.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Campaign not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/campaigns/{cid}/approve",
             dependencies=[Depends(require_permission("campaigns", "approve"))])
async def approve_campaign(cid: str, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    r = await db.execute(select(Campaign).where(Campaign.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Campaign not found")
    obj.approval_status = ApprovalStatus.APPROVED
    obj.approved_by_id  = current_user.id
    obj.status          = CampaignStatus.PLANNED
    await db.commit()
    return {"status": "approved"}


@router.delete("/campaigns/{cid}", status_code=204,
               dependencies=[Depends(require_permission("campaigns", "edit"))])
async def delete_campaign(cid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Campaign).where(Campaign.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Campaign not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# PROMOTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/promotions", response_model=List[PromotionRead],
            dependencies=[Depends(require_permission("promotions", "view"))])
async def list_promotions(
    campaign_id: Optional[str] = Query(None),
    status:      Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(Promotion).order_by(Promotion.start_date.desc())
    if campaign_id:
        q = q.where(Promotion.campaign_id == campaign_id)
    if status:
        q = q.where(Promotion.status == status)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/promotions", response_model=PromotionRead, status_code=201,
             dependencies=[Depends(require_permission("promotions", "create"))])
async def create_promotion(data: PromotionCreate, db: AsyncSession = Depends(get_db)):
    obj = Promotion(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/promotions/{pid}", response_model=PromotionRead,
            dependencies=[Depends(require_permission("promotions", "view"))])
async def get_promotion(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Promotion).where(Promotion.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Promotion not found")
    return obj


@router.patch("/promotions/{pid}", response_model=PromotionRead,
              dependencies=[Depends(require_permission("promotions", "edit"))])
async def update_promotion(pid: str, data: PromotionUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Promotion).where(Promotion.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Promotion not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/promotions/{pid}", status_code=204,
               dependencies=[Depends(require_permission("promotions", "edit"))])
async def delete_promotion(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Promotion).where(Promotion.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Promotion not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER SEGMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/segments", response_model=List[SegmentRead],
            dependencies=[Depends(require_permission("segments", "view"))])
async def list_segments(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerSegment).order_by(CustomerSegment.segment_name))
    return r.scalars().all()


@router.post("/segments", response_model=SegmentRead, status_code=201,
             dependencies=[Depends(require_permission("segments", "create"))])
async def create_segment(data: SegmentCreate, db: AsyncSession = Depends(get_db)):
    obj = CustomerSegment(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/segments/{sid}", response_model=SegmentRead,
            dependencies=[Depends(require_permission("segments", "view"))])
async def get_segment(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerSegment).where(CustomerSegment.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Segment not found")
    return obj


@router.patch("/segments/{sid}", response_model=SegmentRead,
              dependencies=[Depends(require_permission("segments", "edit"))])
async def update_segment(sid: str, data: SegmentUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerSegment).where(CustomerSegment.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Segment not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/segments/{sid}", status_code=204,
               dependencies=[Depends(require_permission("segments", "edit"))])
async def delete_segment(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerSegment).where(CustomerSegment.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Segment not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# CRM PROFILES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/crm", response_model=List[CRMProfileRead],
            dependencies=[Depends(require_permission("crm", "view"))])
async def list_crm_profiles(
    segment_id: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(CRMProfile)
    if segment_id:
        q = q.where(CRMProfile.segment_id == segment_id)
    if status:
        q = q.where(CRMProfile.relationship_status == status)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/crm", response_model=CRMProfileRead, status_code=201,
             dependencies=[Depends(require_permission("crm", "edit"))])
async def create_crm_profile(data: CRMProfileCreate, db: AsyncSession = Depends(get_db)):
    obj = CRMProfile(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/crm/{cid}", response_model=CRMProfileRead,
            dependencies=[Depends(require_permission("crm", "view"))])
async def get_crm_profile(cid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CRMProfile).where(CRMProfile.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "CRM Profile not found")
    return obj


@router.patch("/crm/{cid}", response_model=CRMProfileRead,
              dependencies=[Depends(require_permission("crm", "edit"))])
async def update_crm_profile(cid: str, data: CRMProfileUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CRMProfile).where(CRMProfile.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "CRM Profile not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.last_contact_date = date.today()
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/crm/{cid}/interactions", response_model=List[InteractionRead],
            dependencies=[Depends(require_permission("crm", "view"))])
async def list_interactions(cid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(CustomerInteraction)
        .where(CustomerInteraction.crm_profile_id == cid)
        .order_by(CustomerInteraction.interaction_date.desc())
    )
    return r.scalars().all()


@router.post("/crm/{cid}/interactions", response_model=InteractionRead, status_code=201,
             dependencies=[Depends(require_permission("crm", "edit"))])
async def add_interaction(cid: str, data: InteractionCreate,
                          current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    obj = CustomerInteraction(**data.model_dump(), recorded_by_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER VISITS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/visits", response_model=List[VisitRead],
            dependencies=[Depends(require_permission("customer_visits", "view"))])
async def list_visits(
    employee_id: Optional[str] = Query(None),
    visit_type:  Optional[str] = Query(None),
    date_from:   Optional[date] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(CustomerVisit).order_by(CustomerVisit.visit_date.desc())
    if employee_id:
        q = q.where(CustomerVisit.employee_id == employee_id)
    if visit_type:
        q = q.where(CustomerVisit.visit_type == visit_type)
    if date_from:
        q = q.where(CustomerVisit.visit_date >= date_from)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/visits", response_model=VisitRead, status_code=201,
             dependencies=[Depends(require_permission("customer_visits", "create"))])
async def create_visit(data: VisitCreate, db: AsyncSession = Depends(get_db)):
    obj = CustomerVisit(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/visits/{vid}", response_model=VisitRead,
            dependencies=[Depends(require_permission("customer_visits", "view"))])
async def get_visit(vid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerVisit).where(CustomerVisit.id == vid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Visit not found")
    return obj


@router.patch("/visits/{vid}", response_model=VisitRead,
              dependencies=[Depends(require_permission("customer_visits", "create"))])
async def update_visit(vid: str, data: VisitUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CustomerVisit).where(CustomerVisit.id == vid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Visit not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE SPEND
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/trade-spend", response_model=List[TradeSpendRead],
            dependencies=[Depends(require_permission("trade_spend", "view"))])
async def list_trade_spend(
    campaign_id:    Optional[str] = Query(None),
    customer_id:    Optional[str] = Query(None),
    distributor_id: Optional[str] = Query(None),
    spend_type:     Optional[str] = Query(None),
    status:         Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(TradeSpend).order_by(TradeSpend.spend_date.desc())
    if campaign_id:    q = q.where(TradeSpend.campaign_id == campaign_id)
    if customer_id:    q = q.where(TradeSpend.customer_id == customer_id)
    if distributor_id: q = q.where(TradeSpend.distributor_id == distributor_id)
    if spend_type:     q = q.where(TradeSpend.spend_type == spend_type)
    if status:         q = q.where(TradeSpend.approval_status == status)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/trade-spend", response_model=TradeSpendRead, status_code=201,
             dependencies=[Depends(require_permission("trade_spend", "create"))])
async def create_trade_spend(data: TradeSpendCreate, db: AsyncSession = Depends(get_db)):
    obj = TradeSpend(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/trade-spend/{sid}", response_model=TradeSpendRead,
            dependencies=[Depends(require_permission("trade_spend", "view"))])
async def get_trade_spend(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(TradeSpend).where(TradeSpend.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Trade spend not found")
    return obj


@router.patch("/trade-spend/{sid}", response_model=TradeSpendRead,
              dependencies=[Depends(require_permission("trade_spend", "edit"))])
async def update_trade_spend(sid: str, data: TradeSpendUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(TradeSpend).where(TradeSpend.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Trade spend not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/trade-spend/{sid}", status_code=204,
               dependencies=[Depends(require_permission("trade_spend", "edit"))])
async def delete_trade_spend(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(TradeSpend).where(TradeSpend.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Trade spend not found")
    await db.delete(obj)
    await db.commit()


@router.post("/trade-spend/{sid}/approve",
             dependencies=[Depends(require_permission("trade_spend", "approve"))])
async def approve_trade_spend(sid: str, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    r = await db.execute(select(TradeSpend).where(TradeSpend.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Trade spend not found")
    obj.approval_status = ApprovalStatus.APPROVED
    obj.approved_by_id  = current_user.id
    await db.commit()
    return {"status": "approved"}


# ═══════════════════════════════════════════════════════════════════════════════
# BRAND SPEND
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/brand-spend", response_model=List[BrandSpendRead],
            dependencies=[Depends(require_permission("brand_spend", "view"))])
async def list_brand_spend(
    campaign_id:     Optional[str] = Query(None),
    spend_category:  Optional[str] = Query(None),
    status:          Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(BrandSpend).order_by(BrandSpend.spend_date.desc())
    if campaign_id:    q = q.where(BrandSpend.campaign_id == campaign_id)
    if spend_category: q = q.where(BrandSpend.spend_category == spend_category)
    if status:         q = q.where(BrandSpend.approval_status == status)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/brand-spend", response_model=BrandSpendRead, status_code=201,
             dependencies=[Depends(require_permission("brand_spend", "create"))])
async def create_brand_spend(data: BrandSpendCreate, db: AsyncSession = Depends(get_db)):
    obj = BrandSpend(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/brand-spend/{bid}", response_model=BrandSpendRead,
            dependencies=[Depends(require_permission("brand_spend", "view"))])
async def get_brand_spend(bid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(BrandSpend).where(BrandSpend.id == bid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Brand spend not found")
    return obj


@router.patch("/brand-spend/{bid}", response_model=BrandSpendRead,
              dependencies=[Depends(require_permission("brand_spend", "edit"))])
async def update_brand_spend(bid: str, data: BrandSpendUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(BrandSpend).where(BrandSpend.id == bid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Brand spend not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/brand-spend/{bid}", status_code=204,
               dependencies=[Depends(require_permission("brand_spend", "edit"))])
async def delete_brand_spend(bid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(BrandSpend).where(BrandSpend.id == bid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Brand spend not found")
    await db.delete(obj)
    await db.commit()


@router.post("/brand-spend/{bid}/approve",
             dependencies=[Depends(require_permission("brand_spend", "approve"))])
async def approve_brand_spend(bid: str, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    r = await db.execute(select(BrandSpend).where(BrandSpend.id == bid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Brand spend not found")
    obj.approval_status = ApprovalStatus.APPROVED
    obj.approved_by_id  = current_user.id
    await db.commit()
    return {"status": "approved"}


# ═══════════════════════════════════════════════════════════════════════════════
# SURVEYS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/surveys", response_model=List[SurveyRead],
            dependencies=[Depends(require_permission("surveys", "view"))])
async def list_surveys(
    survey_type: Optional[str] = Query(None),
    region:      Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(Survey).order_by(Survey.survey_date.desc())
    if survey_type:
        q = q.where(Survey.survey_type == survey_type)
    if region:
        q = q.where(Survey.region == region)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/surveys", response_model=SurveyRead, status_code=201,
             dependencies=[Depends(require_permission("surveys", "create"))])
async def create_survey(data: SurveyCreate, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    obj = Survey(**data.model_dump(), conducted_by_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/surveys/{sid}", response_model=SurveyRead,
            dependencies=[Depends(require_permission("surveys", "view"))])
async def get_survey(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Survey).where(Survey.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Survey not found")
    return obj


@router.patch("/surveys/{sid}", response_model=SurveyRead,
              dependencies=[Depends(require_permission("surveys", "edit"))])
async def update_survey(sid: str, data: SurveyUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Survey).where(Survey.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Survey not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/surveys/{sid}", status_code=204,
               dependencies=[Depends(require_permission("surveys", "edit"))])
async def delete_survey(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Survey).where(Survey.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Survey not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# INFLUENCERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/influencers", response_model=List[InfluencerRead],
            dependencies=[Depends(require_permission("influencers", "view"))])
async def list_influencers(
    platform: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(Influencer).order_by(Influencer.influencer_name)
    if platform:
        q = q.where(Influencer.platform == platform)
    if status:
        q = q.where(Influencer.status == status)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/influencers", response_model=InfluencerRead, status_code=201,
             dependencies=[Depends(require_permission("influencers", "create"))])
async def create_influencer(data: InfluencerCreate, db: AsyncSession = Depends(get_db)):
    obj = Influencer(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/influencers/{iid}", response_model=InfluencerRead,
              dependencies=[Depends(require_permission("influencers", "edit"))])
async def update_influencer(iid: str, data: InfluencerUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Influencer).where(Influencer.id == iid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Influencer not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/influencers/{iid}", response_model=InfluencerRead,
            dependencies=[Depends(require_permission("influencers", "view"))])
async def get_influencer(iid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Influencer).where(Influencer.id == iid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Influencer not found")
    return obj


@router.delete("/influencers/{iid}", status_code=204,
               dependencies=[Depends(require_permission("influencers", "edit"))])
async def delete_influencer(iid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Influencer).where(Influencer.id == iid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Influencer not found")
    await db.delete(obj)
    await db.commit()


@router.get("/influencers/{iid}/links", response_model=List[InfluencerLinkRead],
            dependencies=[Depends(require_permission("influencers", "view"))])
async def list_influencer_links(iid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(InfluencerCampaignLink).where(InfluencerCampaignLink.influencer_id == iid)
    )
    return r.scalars().all()


@router.post("/influencer-links", response_model=InfluencerLinkRead, status_code=201,
             dependencies=[Depends(require_permission("influencers", "create"))])
async def create_influencer_link(data: InfluencerLinkCreate, db: AsyncSession = Depends(get_db)):
    obj = InfluencerCampaignLink(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/influencer-links/{lid}", response_model=InfluencerLinkRead,
              dependencies=[Depends(require_permission("influencers", "edit"))])
async def update_influencer_link(lid: str, data: InfluencerLinkUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(InfluencerCampaignLink).where(InfluencerCampaignLink.id == lid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Influencer link not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/influencer-attribution", response_model=List[InfluencerAttributionRead],
            dependencies=[Depends(require_permission("influencers", "view"))])
async def list_attribution(
    influencer_id: Optional[str] = Query(None),
    campaign_id:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(InfluencerAttribution).order_by(InfluencerAttribution.attribution_date.desc())
    if influencer_id:
        q = q.where(InfluencerAttribution.influencer_id == influencer_id)
    if campaign_id:
        q = q.where(InfluencerAttribution.campaign_id == campaign_id)
    r = await db.execute(q)
    return r.scalars().all()


@router.post("/influencer-attribution", response_model=InfluencerAttributionRead, status_code=201,
             dependencies=[Depends(require_permission("influencers", "create"))])
async def create_attribution(data: InfluencerAttributionCreate, db: AsyncSession = Depends(get_db)):
    obj = InfluencerAttribution(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL MEDIA
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/social-media", response_model=List[SocialActivityRead],
            dependencies=[Depends(require_permission("social_media", "view"))])
async def list_social(
    campaign_id: Optional[str] = Query(None),
    platform:    Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(SocialMediaActivity).order_by(SocialMediaActivity.published_date.desc())
    if campaign_id:
        q = q.where(SocialMediaActivity.campaign_id == campaign_id)
    if platform:
        q = q.where(SocialMediaActivity.platform == platform)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/social-media", response_model=SocialActivityRead, status_code=201,
             dependencies=[Depends(require_permission("social_media", "edit"))])
async def create_social(data: SocialActivityCreate, db: AsyncSession = Depends(get_db)):
    obj = SocialMediaActivity(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/social-media/{sid}", response_model=SocialActivityRead,
            dependencies=[Depends(require_permission("social_media", "view"))])
async def get_social(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(SocialMediaActivity).where(SocialMediaActivity.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Social media activity not found")
    return obj


@router.patch("/social-media/{sid}", response_model=SocialActivityRead,
              dependencies=[Depends(require_permission("social_media", "edit"))])
async def update_social(sid: str, data: SocialActivityUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(SocialMediaActivity).where(SocialMediaActivity.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Social media activity not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/social-media/{sid}", status_code=204,
               dependencies=[Depends(require_permission("social_media", "edit"))])
async def delete_social(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(SocialMediaActivity).where(SocialMediaActivity.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Social media activity not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# STORES / E-COMMERCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ecommerce/stores", response_model=List[StoreRead],
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def list_stores(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Store).order_by(Store.store_name))
    return r.scalars().all()


@router.post("/ecommerce/stores", response_model=StoreRead, status_code=201,
             dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def create_store(data: StoreCreate, db: AsyncSession = Depends(get_db)):
    obj = Store(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/ecommerce/performance", response_model=List[StorePerformanceRead],
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def list_store_performance(
    store_id:  Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(StorePerformance).order_by(StorePerformance.perf_date.desc())
    if store_id:
        q = q.where(StorePerformance.store_id == store_id)
    if date_from:
        q = q.where(StorePerformance.perf_date >= date_from)
    if date_to:
        q = q.where(StorePerformance.perf_date <= date_to)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/ecommerce/performance", response_model=StorePerformanceRead, status_code=201,
             dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def create_store_performance(data: StorePerformanceCreate, db: AsyncSession = Depends(get_db)):
    obj = StorePerformance(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/ecommerce/products", response_model=List[ProductChannelPerfRead],
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def list_product_channel_perf(
    store_id:   Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(ProductChannelPerformance).order_by(ProductChannelPerformance.perf_date.desc())
    if store_id:
        q = q.where(ProductChannelPerformance.store_id == store_id)
    if product_id:
        q = q.where(ProductChannelPerformance.product_id == product_id)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/ecommerce/products", response_model=ProductChannelPerfRead, status_code=201,
             dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def create_product_channel_perf(data: ProductChannelPerfCreate, db: AsyncSession = Depends(get_db)):
    obj = ProductChannelPerformance(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/ecommerce/stores/{sid}", response_model=StoreRead,
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def get_store(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Store).where(Store.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store not found")
    return obj


@router.patch("/ecommerce/stores/{sid}", response_model=StoreRead,
              dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def update_store(sid: str, data: StoreUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Store).where(Store.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/ecommerce/stores/{sid}", status_code=204,
               dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def delete_store(sid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Store).where(Store.id == sid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store not found")
    await db.delete(obj)
    await db.commit()


@router.get("/ecommerce/performance/{pid}", response_model=StorePerformanceRead,
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def get_store_performance(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(StorePerformance).where(StorePerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store performance record not found")
    return obj


@router.patch("/ecommerce/performance/{pid}", response_model=StorePerformanceRead,
              dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def update_store_performance(pid: str, data: StorePerformanceUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(StorePerformance).where(StorePerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store performance record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/ecommerce/performance/{pid}", status_code=204,
               dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def delete_store_performance(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(StorePerformance).where(StorePerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Store performance record not found")
    await db.delete(obj)
    await db.commit()


@router.get("/ecommerce/products/{pid}", response_model=ProductChannelPerfRead,
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def get_product_channel_perf(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ProductChannelPerformance).where(ProductChannelPerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Product channel performance record not found")
    return obj


@router.patch("/ecommerce/products/{pid}", response_model=ProductChannelPerfRead,
              dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def update_product_channel_perf(pid: str, data: ProductChannelPerfUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ProductChannelPerformance).where(ProductChannelPerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Product channel performance record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/ecommerce/products/{pid}", status_code=204,
               dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def delete_product_channel_perf(pid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ProductChannelPerformance).where(ProductChannelPerformance.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Product channel performance record not found")
    await db.delete(obj)
    await db.commit()


@router.get("/ecommerce/channel-stock", response_model=List[ChannelStockRead],
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def list_channel_stock(
    store_id:   Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(ChannelStock)
    if store_id:
        q = q.where(ChannelStock.store_id == store_id)
    if product_id:
        q = q.where(ChannelStock.product_id == product_id)
    r = await db.execute(q)
    return r.scalars().all()


@router.post("/ecommerce/channel-stock", response_model=ChannelStockRead, status_code=201,
             dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def upsert_channel_stock(data: ChannelStockCreate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(ChannelStock).where(
            and_(ChannelStock.product_id == data.product_id, ChannelStock.store_id == data.store_id)
        )
    )
    obj = r.scalar_one_or_none()
    if obj:
        for k, v in data.model_dump().items():
            setattr(obj, k, v)
    else:
        obj = ChannelStock(**data.model_dump())
        db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/ecommerce/channel-stock/{cid}", response_model=ChannelStockRead,
              dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def update_channel_stock(cid: str, data: ChannelStockUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ChannelStock).where(ChannelStock.id == cid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Channel stock record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/ecommerce/analytics", response_model=EcommerceAnalytics,
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def get_ecommerce_analytics(
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)

    # Aggregate store performance
    perf_q = await db.execute(
        select(
            Store.store_name,
            Store.platform,
            func.sum(StorePerformance.total_revenue).label("revenue"),
            func.sum(StorePerformance.total_orders).label("orders"),
            func.sum(StorePerformance.total_units_sold).label("units"),
            func.sum(StorePerformance.ad_spend).label("ad_spend"),
            func.sum(StorePerformance.net_revenue).label("net_revenue"),
            func.avg(StorePerformance.return_rate).label("avg_return_rate"),
            func.avg(StorePerformance.conversion_rate).label("avg_conv_rate"),
        )
        .join(StorePerformance, StorePerformance.store_id == Store.id)
        .where(StorePerformance.perf_date >= cutoff)
        .group_by(Store.id, Store.store_name, Store.platform)
        .order_by(func.sum(StorePerformance.total_revenue).desc())
    )
    channel_rows = perf_q.all()

    total_revenue   = sum(float(r.revenue or 0) for r in channel_rows)
    total_orders    = sum(int(r.orders or 0) for r in channel_rows)
    total_units     = sum(int(r.units or 0) for r in channel_rows)
    total_ad_spend  = sum(float(r.ad_spend or 0) for r in channel_rows)
    avg_return_rate = (sum(float(r.avg_return_rate or 0) for r in channel_rows) / len(channel_rows)) if channel_rows else 0

    channel_breakdown = [
        {
            "store_name":    r.store_name,
            "platform":      r.platform,
            "revenue":       float(r.revenue or 0),
            "orders":        int(r.orders or 0),
            "units":         int(r.units or 0),
            "ad_spend":      float(r.ad_spend or 0),
            "roas":          round(float(r.revenue or 0) / float(r.ad_spend) if r.ad_spend and float(r.ad_spend) > 0 else 0, 2),
            "return_rate":   round(float(r.avg_return_rate or 0) * 100, 2),
            "conv_rate":     round(float(r.avg_conv_rate or 0) * 100, 2),
        }
        for r in channel_rows
    ]

    # Top products by revenue
    prod_q = await db.execute(
        select(
            ProductChannelPerformance.product_id,
            func.sum(ProductChannelPerformance.revenue).label("revenue"),
            func.sum(ProductChannelPerformance.units_sold).label("units"),
            func.avg(ProductChannelPerformance.return_rate).label("avg_return_rate"),
        )
        .where(ProductChannelPerformance.perf_date >= cutoff)
        .group_by(ProductChannelPerformance.product_id)
        .order_by(func.sum(ProductChannelPerformance.revenue).desc())
        .limit(10)
    )
    top_products = [
        {
            "product_id":  str(r.product_id),
            "revenue":     float(r.revenue or 0),
            "units":       int(r.units or 0),
            "return_rate": round(float(r.avg_return_rate or 0) * 100, 2),
        }
        for r in prod_q.all()
    ]

    # Return reasons
    ret_q = await db.execute(
        select(
            ReturnAnalytics.return_reason,
            func.sum(ReturnAnalytics.return_count).label("count"),
        )
        .where(ReturnAnalytics.return_date >= cutoff)
        .group_by(ReturnAnalytics.return_reason)
        .order_by(func.sum(ReturnAnalytics.return_count).desc())
        .limit(10)
    )
    return_reasons = [{"reason": r.return_reason or "Unknown", "count": int(r.count or 0)} for r in ret_q.all()]

    return EcommerceAnalytics(
        period_days=days,
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_units_sold=total_units,
        avg_order_value=round(total_revenue / total_orders if total_orders > 0 else 0, 2),
        total_ad_spend=total_ad_spend,
        overall_roas=round(total_revenue / total_ad_spend if total_ad_spend > 0 else 0, 2),
        overall_return_rate=round(avg_return_rate * 100, 2),
        channel_breakdown=channel_breakdown,
        top_products=top_products,
        return_reasons=return_reasons,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AD PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ads", response_model=List[AdPerformanceRead],
            dependencies=[Depends(require_permission("ad_performance", "view"))])
async def list_ads(
    campaign_id: Optional[str] = Query(None),
    platform:    Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(AdPerformance).order_by(AdPerformance.ad_date.desc())
    if campaign_id:
        q = q.where(AdPerformance.campaign_id == campaign_id)
    if platform:
        q = q.where(AdPerformance.platform == platform)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.post("/ads", response_model=AdPerformanceRead, status_code=201,
             dependencies=[Depends(require_permission("ad_performance", "edit"))])
async def create_ad(data: AdPerformanceCreate, db: AsyncSession = Depends(get_db)):
    obj = AdPerformance(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/ads/{aid}", response_model=AdPerformanceRead,
            dependencies=[Depends(require_permission("ad_performance", "view"))])
async def get_ad(aid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AdPerformance).where(AdPerformance.id == aid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ad performance record not found")
    return obj


@router.patch("/ads/{aid}", response_model=AdPerformanceRead,
              dependencies=[Depends(require_permission("ad_performance", "edit"))])
async def update_ad(aid: str, data: AdPerformanceUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AdPerformance).where(AdPerformance.id == aid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ad performance record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/ads/{aid}", status_code=204,
               dependencies=[Depends(require_permission("ad_performance", "edit"))])
async def delete_ad(aid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AdPerformance).where(AdPerformance.id == aid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ad performance record not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# RETURN ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/returns", response_model=ReturnAnalyticsRead, status_code=201,
             dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def create_return_analytics(data: ReturnAnalyticsCreate, db: AsyncSession = Depends(get_db)):
    obj = ReturnAnalytics(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/returns", response_model=List[ReturnAnalyticsRead],
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def list_return_analytics(
    product_id: Optional[str] = Query(None),
    store_id:   Optional[str] = Query(None),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(ReturnAnalytics).order_by(ReturnAnalytics.return_date.desc())
    if product_id:
        q = q.where(ReturnAnalytics.product_id == product_id)
    if store_id:
        q = q.where(ReturnAnalytics.store_id == store_id)
    r = await db.execute(q.offset(skip).limit(limit))
    return r.scalars().all()


@router.get("/returns/{rid}", response_model=ReturnAnalyticsRead,
            dependencies=[Depends(require_permission("ecommerce", "view"))])
async def get_return_analytics(rid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ReturnAnalytics).where(ReturnAnalytics.id == rid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Return analytics record not found")
    return obj


@router.patch("/returns/{rid}", response_model=ReturnAnalyticsRead,
              dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def update_return_analytics(rid: str, data: ReturnAnalyticsUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ReturnAnalytics).where(ReturnAnalytics.id == rid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Return analytics record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/returns/{rid}", status_code=204,
               dependencies=[Depends(require_permission("ecommerce", "edit"))])
async def delete_return_analytics(rid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(ReturnAnalytics).where(ReturnAnalytics.id == rid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Return analytics record not found")
    await db.delete(obj)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# AI CAMPAIGN OPTIMIZER (v1 — rules-based heuristic engine)
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_optimizer(
    campaign_id: Optional[str],
    context: Optional[str],
    db: AsyncSession,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    AI Campaign Optimizer — v1 rules-based heuristic engine.

    Architecture notes:
    - All intelligence is encoded as deterministic rules over aggregated ERP data.
    - Replace this function body with an ML model call (e.g. Claude API, sklearn, etc.)
      to upgrade to AI inference without changing any callers or storage schema.
    - Input signals: campaigns, promotions, trade/brand spend, segments, CRM,
      influencers, social, ad performance, e-commerce, return analytics, surveys.
    """
    today = date.today()
    _f = lambda v: float(v) if v is not None else 0.0

    # ═══════════════════════════════════════════════════════════════
    # DATA GATHERING — all 14 signal sources
    # ═══════════════════════════════════════════════════════════════

    # 1. Campaign performance by type
    camp_type_rows = (await db.execute(
        select(
            Campaign.campaign_type,
            func.count(Campaign.id).label("count"),
            func.avg(Campaign.actual_roi).label("avg_roi"),
            func.sum(Campaign.actual_revenue).label("total_rev"),
            func.sum(Campaign.budget).label("total_budget"),
        )
        .where(Campaign.status == CampaignStatus.COMPLETED)
        .group_by(Campaign.campaign_type)
        .order_by(func.avg(Campaign.actual_roi).desc())
    )).all()
    campaign_types = [
        {
            "type":       r.campaign_type,
            "count":      r.count,
            "avg_roi":    _f(r.avg_roi),
            "total_rev":  _f(r.total_rev),
            "efficiency": _f(r.total_rev) / max(_f(r.total_budget), 1),
        }
        for r in camp_type_rows
    ]

    # 2. Region performance (campaign revenue + ROI)
    region_rows = (await db.execute(
        select(
            Campaign.region,
            func.count(Campaign.id).label("count"),
            func.avg(Campaign.actual_roi).label("avg_roi"),
            func.sum(Campaign.actual_revenue).label("total_rev"),
        )
        .where(Campaign.status == CampaignStatus.COMPLETED, Campaign.region.isnot(None))
        .group_by(Campaign.region)
        .order_by(func.sum(Campaign.actual_revenue).desc())
    )).all()
    top_regions = [
        {"region": r.region, "avg_roi": _f(r.avg_roi), "total_rev": _f(r.total_rev), "count": r.count}
        for r in region_rows
    ]

    # 3. Ad platform ROAS
    ad_rows = (await db.execute(
        select(
            AdPerformance.platform,
            func.sum(AdPerformance.spend).label("total_spend"),
            func.sum(AdPerformance.conversions).label("total_conv"),
            func.sum(AdPerformance.revenue_generated).label("total_rev"),
            func.avg(AdPerformance.ctr).label("avg_ctr"),
            func.avg(AdPerformance.conversion_rate).label("avg_cvr"),
        )
        .group_by(AdPerformance.platform)
        .order_by(func.sum(AdPerformance.revenue_generated).desc())
    )).all()
    ad_platforms = [
        {
            "platform":    r.platform,
            "roas":        _f(r.total_rev) / max(_f(r.total_spend), 1),
            "spend":       _f(r.total_spend),
            "conversions": int(r.total_conv or 0),
            "avg_ctr":     _f(r.avg_ctr),
            "avg_cvr":     _f(r.avg_cvr),
        }
        for r in ad_rows
    ]

    # 4. Influencer platform performance
    inf_rows = (await db.execute(
        select(
            Influencer.platform,
            func.count(InfluencerCampaignLink.id).label("activations"),
            func.sum(InfluencerCampaignLink.attributed_revenue).label("total_rev"),
            func.avg(InfluencerCampaignLink.performance_score).label("avg_score"),
            func.avg(InfluencerCampaignLink.agreed_fee).label("avg_fee"),
        )
        .join(InfluencerCampaignLink, InfluencerCampaignLink.influencer_id == Influencer.id)
        .group_by(Influencer.platform)
        .order_by(func.sum(InfluencerCampaignLink.attributed_revenue).desc())
    )).all()
    influencer_platforms = [
        {
            "platform":    r.platform,
            "revenue":     _f(r.total_rev),
            "activations": int(r.activations or 0),
            "score":       _f(r.avg_score),
            "roi":         _f(r.total_rev) / max(_f(r.avg_fee) * max(int(r.activations or 0), 1), 1),
        }
        for r in inf_rows
    ]

    # 5. Trade vs brand spend totals
    total_trade = _f((await db.execute(select(func.sum(TradeSpend.amount)))).scalar_one_or_none())
    total_brand = _f((await db.execute(select(func.sum(BrandSpend.amount)))).scalar_one_or_none())
    total_spend = total_trade + total_brand

    # Brand spend breakdown by category
    brand_cat_rows = (await db.execute(
        select(BrandSpend.spend_category, func.sum(BrandSpend.amount).label("total"))
        .group_by(BrandSpend.spend_category)
        .order_by(func.sum(BrandSpend.amount).desc())
    )).all()
    brand_by_category = [{"category": r.spend_category, "amount": _f(r.total)} for r in brand_cat_rows]

    # 6. E-commerce store / channel performance
    store_rows = (await db.execute(
        select(
            Store.store_name,
            Store.platform,
            func.sum(StorePerformance.total_revenue).label("rev"),
            func.avg(StorePerformance.conversion_rate).label("cvr"),
            func.sum(StorePerformance.total_orders).label("orders"),
            func.avg(StorePerformance.return_rate).label("return_rate"),
        )
        .join(StorePerformance, StorePerformance.store_id == Store.id)
        .group_by(Store.id, Store.store_name, Store.platform)
        .order_by(func.sum(StorePerformance.total_revenue).desc())
        .limit(8)
    )).all()
    top_stores = [
        {
            "store":           r.store_name,
            "platform":        r.platform,
            "revenue":         _f(r.rev),
            "conversion_rate": _f(r.cvr),
            "orders":          int(r.orders or 0),
            "return_rate":     _f(r.return_rate),
        }
        for r in store_rows
    ]

    # 7. Customer segments — highest LTV and engagement
    seg_rows = (await db.execute(
        select(
            CustomerSegment.segment_name,
            CustomerSegment.segment_type,
            CustomerSegment.region,
            func.count(CRMProfile.id).label("crm_count"),
            func.avg(CRMProfile.estimated_ltv).label("avg_ltv"),
            func.avg(CRMProfile.engagement_score).label("avg_engagement"),
            func.avg(CRMProfile.churn_risk_score).label("avg_churn_risk"),
        )
        .join(CRMProfile, CRMProfile.segment_id == CustomerSegment.id, isouter=True)
        .where(CustomerSegment.is_active == True)
        .group_by(CustomerSegment.id, CustomerSegment.segment_name, CustomerSegment.segment_type, CustomerSegment.region)
        .order_by(func.avg(CRMProfile.estimated_ltv).desc())
        .limit(6)
    )).all()
    top_segments = [
        {
            "segment":        r.segment_name,
            "type":           r.segment_type,
            "region":         r.region,
            "crm_count":      int(r.crm_count or 0),
            "avg_ltv":        _f(r.avg_ltv),
            "avg_engagement": _f(r.avg_engagement),
            "churn_risk":     _f(r.avg_churn_risk),
        }
        for r in seg_rows
    ]

    # 8. CRM acquisition source efficiency
    acq_rows = (await db.execute(
        select(
            CRMProfile.acquisition_source,
            func.count(CRMProfile.id).label("count"),
            func.avg(CRMProfile.estimated_ltv).label("avg_ltv"),
            func.avg(CRMProfile.engagement_score).label("avg_engagement"),
        )
        .where(CRMProfile.acquisition_source.isnot(None))
        .group_by(CRMProfile.acquisition_source)
        .order_by(func.avg(CRMProfile.estimated_ltv).desc())
    )).all()
    acquisition_sources = [
        {
            "source":      r.acquisition_source,
            "count":       int(r.count or 0),
            "avg_ltv":     _f(r.avg_ltv),
            "avg_engagement": _f(r.avg_engagement),
        }
        for r in acq_rows
    ]

    # 9. Promotion type performance
    promo_rows = (await db.execute(
        select(
            Promotion.promotion_type,
            func.count(Promotion.id).label("count"),
            Promotion.region,
        )
        .where(Promotion.status == "ACTIVE")
        .group_by(Promotion.promotion_type, Promotion.region)
        .order_by(func.count(Promotion.id).desc())
    )).all()
    promotion_types = [
        {"type": r.promotion_type, "count": int(r.count), "region": r.region}
        for r in promo_rows
    ]

    # 10. Survey sentiment signal
    survey_rows = (await db.execute(
        select(
            Survey.survey_type,
            func.avg(Survey.sentiment_score).label("avg_sentiment"),
            func.count(Survey.id).label("count"),
            func.sum(Survey.response_count).label("total_responses"),
        )
        .where(Survey.sentiment_score.isnot(None))
        .group_by(Survey.survey_type)
        .order_by(func.avg(Survey.sentiment_score).desc())
    )).all()
    survey_signals = [
        {
            "type":      r.survey_type,
            "sentiment": _f(r.avg_sentiment),
            "surveys":   int(r.count or 0),
            "responses": int(r.total_responses or 0),
        }
        for r in survey_rows
    ]

    # 11. Return analytics — high-return channels = risk signal
    return_rows = (await db.execute(
        select(
            Store.store_name,
            Store.platform,
            func.avg(ReturnAnalytics.return_rate).label("avg_return_rate"),
            func.sum(ReturnAnalytics.return_count).label("total_returns"),
        )
        .join(ReturnAnalytics, ReturnAnalytics.store_id == Store.id, isouter=True)
        .where(ReturnAnalytics.return_rate.isnot(None))
        .group_by(Store.id, Store.store_name, Store.platform)
        .order_by(func.avg(ReturnAnalytics.return_rate).desc())
        .limit(5)
    )).all()
    high_return_channels = [
        {
            "store":       r.store_name,
            "platform":    r.platform,
            "return_rate": _f(r.avg_return_rate),
            "returns":     int(r.total_returns or 0),
        }
        for r in return_rows
    ]

    # 12. Product-channel fit (highest converting product-channel combos)
    prod_chan_rows = (await db.execute(
        select(
            ProductChannelPerformance.product_id,
            Store.store_name,
            Store.platform,
            func.sum(ProductChannelPerformance.revenue).label("rev"),
            func.avg(ProductChannelPerformance.conversion_rate).label("cvr"),
            func.avg(ProductChannelPerformance.return_rate).label("rr"),
        )
        .join(Store, Store.id == ProductChannelPerformance.store_id)
        .group_by(ProductChannelPerformance.product_id, Store.store_name, Store.platform)
        .order_by(func.sum(ProductChannelPerformance.revenue).desc())
        .limit(5)
    )).all()
    product_channel_fits = [
        {
            "product_id": str(r.product_id),
            "store":      r.store_name,
            "platform":   r.platform,
            "revenue":    _f(r.rev),
            "cvr":        _f(r.cvr),
            "return_rate":_f(r.rr),
        }
        for r in prod_chan_rows
    ]

    # 13. Social media engagement by platform
    social_rows = (await db.execute(
        select(
            SocialMediaActivity.platform,
            func.sum(SocialMediaActivity.impressions).label("total_impressions"),
            func.sum(SocialMediaActivity.engagements).label("total_engagements"),
            func.sum(SocialMediaActivity.clicks).label("total_clicks"),
            func.count(SocialMediaActivity.id).label("posts"),
        )
        .group_by(SocialMediaActivity.platform)
        .order_by(func.sum(SocialMediaActivity.engagements).desc())
    )).all()
    social_platforms = [
        {
            "platform":    r.platform,
            "impressions": int(r.total_impressions or 0),
            "engagements": int(r.total_engagements or 0),
            "clicks":      int(r.total_clicks or 0),
            "posts":       int(r.posts or 0),
            "eng_rate":    _f(r.total_engagements) / max(int(r.total_impressions or 1), 1),
        }
        for r in social_rows
    ]

    # 14. At-risk customer count (churn risk signal)
    at_risk_q = await db.execute(
        select(func.count(CRMProfile.id))
        .where(CRMProfile.churn_risk_score >= 60)
    )
    at_risk_count = int(at_risk_q.scalar_one() or 0)

    vip_q = await db.execute(
        select(func.count(CRMProfile.id))
        .where(CRMProfile.loyalty_status == "VIP")
    )
    vip_count = int(vip_q.scalar_one() or 0)

    # ═══════════════════════════════════════════════════════════════
    # RULE ENGINE — deterministic heuristics over aggregated signals
    # ═══════════════════════════════════════════════════════════════

    best_camp_type  = campaign_types[0]["type"]  if campaign_types  else "DIGITAL"
    best_ad_plat    = ad_platforms[0]["platform"] if ad_platforms    else "META"
    best_inf_plat   = influencer_platforms[0]["platform"] if influencer_platforms else "INSTAGRAM"
    best_store_name = top_stores[0]["store"]      if top_stores      else None

    # Budget split — shift toward digital if top-2 ad ROAS > 2.5x
    if total_spend > 0:
        trade_pct = round(total_trade / total_spend * 100)
        brand_pct = 100 - trade_pct
    else:
        trade_pct, brand_pct = 40, 60

    top_2_roas = sum(p["roas"] for p in ad_platforms[:2]) / max(len(ad_platforms[:2]), 1)
    if top_2_roas > 2.5 and brand_pct < 65:
        brand_pct = min(brand_pct + 10, 70)
        trade_pct = 100 - brand_pct

    # Predicted ROI range — anchor on best historical campaign type avg_roi
    best_roi_anchor = campaign_types[0]["avg_roi"] if campaign_types else 1.5
    roi_low  = round(max(0.8, best_roi_anchor * 0.7), 2)
    roi_high = round(best_roi_anchor * 1.4, 2)

    # Predicted uplift — proportional to engagement rate of top ad platform
    top_eng_rate = social_platforms[0]["eng_rate"] if social_platforms else 0.02
    uplift_pct   = round(min(top_eng_rate * 1200, 35), 1)  # cap at 35%

    # Risk signals
    risk_notes = []
    if at_risk_count > 10:
        risk_notes.append(f"{at_risk_count} CRM customers have churn risk ≥ 60 — add retention mechanics (loyalty, personalised offers) before scaling spend.")
    if high_return_channels and high_return_channels[0]["return_rate"] > 0.1:
        ch = high_return_channels[0]
        risk_notes.append(f"'{ch['store']}' ({ch['platform']}) has a {ch['return_rate']*100:.1f}% return rate — validate product listings and fulfilment before increasing ad spend here.")
    if top_2_roas < 1.2 and ad_platforms:
        risk_notes.append("Ad platform ROAS is below 1.2x — pause spend on underperforming creatives and run creative refresh before scaling.")
    if not campaign_types:
        risk_notes.append("No completed campaigns found — run at least one pilot campaign before optimising budget allocation.")
    avg_sentiment = survey_signals[0]["sentiment"] if survey_signals else 5.0
    if avg_sentiment < 4.0:
        risk_notes.append(f"Survey sentiment score is {avg_sentiment:.1f}/10 — address product/service feedback before a major push campaign.")
    if not risk_notes:
        risk_notes.append("No major risk flags detected. Proceed with recommended configuration and monitor KPIs weekly.")

    # Campaign improvement suggestions
    improvement_suggestions = []
    if campaign_types:
        worst = sorted(campaign_types, key=lambda x: x["avg_roi"])
        if worst and worst[0]["avg_roi"] < 0.5:
            improvement_suggestions.append(f"'{worst[0]['type']}' campaigns are underperforming (avg ROI {worst[0]['avg_roi']:.2f}x) — restructure objectives or shift budget to '{best_camp_type}'.")
    if top_regions and len(top_regions) > 1:
        gap = top_regions[0]["total_rev"] / max(top_regions[-1]["total_rev"], 1)
        if gap > 3:
            improvement_suggestions.append(f"Revenue gap between top and bottom region is {gap:.1f}x — investigate distribution or awareness gaps in lower-performing areas.")
    if vip_count < 5:
        improvement_suggestions.append("VIP customer base is small — introduce a loyalty tier programme to upgrade high-LTV customers and reduce churn risk.")
    if promotion_types and len(set(p["type"] for p in promotion_types)) < 3:
        improvement_suggestions.append("Promotion mix is narrow — test at least 3 promotion types (DISCOUNT, BUNDLE, FREE_ITEM) to find the optimal FMCG mechanic.")
    if not improvement_suggestions:
        improvement_suggestions.append("Current campaign structure looks healthy. Focus on scaling what's working: top region + top channel + best-performing ad platform.")

    # Scaling suggestions
    scaling_suggestions = [
        f"Scale '{best_camp_type}' campaign type — highest historical ROI; allocate 40%+ of next budget cycle.",
        f"Expand to top {min(3, len(top_regions))} region(s): {', '.join(r['region'] for r in top_regions[:3]) or 'Nairobi, Mombasa, Kisumu'} — these drive the most revenue.",
    ]
    if ad_platforms and ad_platforms[0]["roas"] > 2.0:
        scaling_suggestions.append(f"Increase {best_ad_plat} ad budget — ROAS {ad_platforms[0]['roas']:.2f}x is above target threshold; room to scale before diminishing returns.")
    if influencer_platforms:
        scaling_suggestions.append(f"Activate 2–4 mid-tier {best_inf_plat} influencers per campaign — best platform by attributed revenue with manageable fee structure.")
    scaling_suggestions.append("Run a 14-day A/B test: DISCOUNT vs BUNDLE mechanic across top 2 stores to identify margin-optimal format.")
    if social_platforms:
        top_social = social_platforms[0]
        scaling_suggestions.append(f"Post 3–5x per week on {top_social['platform']} — highest engagement platform ({top_social['eng_rate']*100:.1f}% engagement rate).")

    # ═══════════════════════════════════════════════════════════════
    # OUTPUT ASSEMBLY
    # ═══════════════════════════════════════════════════════════════

    input_summary = {
        "campaign_types_analysed":     len(campaign_types),
        "regions_analysed":            len(top_regions),
        "ad_platforms_analysed":       len(ad_platforms),
        "influencer_platforms_used":   len(influencer_platforms),
        "segments_evaluated":          len(top_segments),
        "acquisition_sources_tracked": len(acquisition_sources),
        "survey_signals":              len(survey_signals),
        "high_return_channels_flagged":len(high_return_channels),
        "product_channel_pairs":       len(product_channel_fits),
        "social_platforms_tracked":    len(social_platforms),
        "at_risk_customers":           at_risk_count,
        "vip_customers":               vip_count,
        "total_historical_spend_kes":  total_spend,
        "engine_version":              "v1-rules",
        "analysis_date":               today.isoformat(),
        "context":                     context or None,
    }

    recommendations = {
        # ── Targeting ──────────────────────────────────────────────
        "best_target_segments": {
            "segments": [
                {"name": s["segment"], "type": s["type"], "avg_ltv": s["avg_ltv"],
                 "engagement": s["avg_engagement"], "churn_risk": s["churn_risk"]}
                for s in top_segments[:3]
            ],
            "reason": "Top segments by estimated customer LTV; prioritise high-LTV, low-churn-risk groups.",
        },
        "best_target_regions": {
            "regions": [{"name": r["region"], "avg_roi": r["avg_roi"], "revenue": r["total_rev"]} for r in top_regions[:3]],
            "reason": "Top 3 regions by total revenue from completed campaigns.",
        },
        "best_acquisition_channels": {
            "channels": [{"source": a["source"], "avg_ltv": a["avg_ltv"], "count": a["count"]} for a in acquisition_sources[:3]],
            "reason": "Acquisition sources producing the highest average customer LTV.",
        },

        # ── Campaign structure ─────────────────────────────────────
        "best_campaign_type": {
            "value":   best_camp_type,
            "all_types": [{"type": c["type"], "avg_roi": c["avg_roi"], "efficiency": c["efficiency"]} for c in campaign_types[:5]],
            "reason":  f"Highest historical avg ROI among {len(campaign_types)} completed campaign types.",
        },
        "best_promotion_type": {
            "primary":   "DISCOUNT",
            "secondary": "BUNDLE",
            "reason":    "DISCOUNT drives highest short-term FMCG volume; BUNDLE improves basket margin. Rotate seasonally.",
        },

        # ── Budget ─────────────────────────────────────────────────
        "best_budget_split": {
            "trade_spend_pct": trade_pct,
            "brand_spend_pct": brand_pct,
            "digital_of_brand_pct": 40,
            "influencer_of_brand_pct": 20,
            "brand_by_category": brand_by_category[:5],
            "reason": "Anchored on historical spend ratio; shifted toward brand/digital because top ad ROAS > 2.5x." if top_2_roas > 2.5 else "Anchored on historical spend ratio; no strong signal to shift from current balance.",
        },

        # ── Channels ───────────────────────────────────────────────
        "best_store_channel_mix": {
            "top_stores": [{"store": s["store"], "platform": s["platform"], "revenue": s["revenue"], "cvr": s["conversion_rate"]} for s in top_stores[:5]],
            "reason": "Ranked by total revenue and conversion rate; prioritise channels with CVR > 2%.",
        },
        "best_ad_platform_mix": {
            "platforms": [{"platform": p["platform"], "roas": p["roas"], "spend": p["spend"], "conversions": p["conversions"]} for p in ad_platforms[:5]],
            "reason": f"Ranked by ROAS; {best_ad_plat} is primary. Cut platforms below 1.5x ROAS.",
        },
        "best_influencer_mix": {
            "platforms": [{"platform": p["platform"], "revenue": p["revenue"], "score": p["score"], "roi": p["roi"]} for p in influencer_platforms[:4]],
            "reason": "Ranked by attributed revenue; prefer platforms with performance score > 7.",
        },
        "best_social_platforms": {
            "platforms": [{"platform": p["platform"], "eng_rate": p["eng_rate"], "impressions": p["impressions"]} for p in social_platforms[:4]],
            "reason": "Ranked by engagement rate; higher engagement drives lower paid acquisition costs.",
        },

        # ── Product fit ────────────────────────────────────────────
        "product_channel_fit": {
            "top_combos": product_channel_fits,
            "reason": "Product-channel pairs with highest revenue and conversion rate — prioritise these in next campaign.",
        },

        # ── Return analytics ───────────────────────────────────────
        "return_risk_signals": {
            "high_return_channels": high_return_channels,
            "reason": "Channels with >10% return rate dilute net revenue — fix before scaling ad spend there.",
        },

        # ── Predictions ────────────────────────────────────────────
        "predicted_roi_range": {
            "low":  roi_low,
            "high": roi_high,
            "basis": f"Anchored on best campaign type avg ROI ({best_roi_anchor:.2f}x) ± 30%. ML model integration pending.",
        },
        "predicted_uplift": {
            "pct":   uplift_pct,
            "basis": f"Derived from top social engagement rate ({top_eng_rate*100:.2f}%). Actual uplift depends on creative and offer strength.",
        },

        # ── Guidance ───────────────────────────────────────────────
        "risk_notes":                  risk_notes,
        "scaling_suggestions":         scaling_suggestions,
        "campaign_improvement_suggestions": improvement_suggestions,
        "content_suggestions": [
            "Short-form video (TikTok Reels / Instagram Reels) for product demo and testimonials.",
            "User-generated content campaigns: incentivise customers to share product experiences.",
            "Comparison ads vs competitor — effective for FMCG where brand recall drives shelf pick.",
            "In-store display activation photos for trade/field sales reporting.",
        ],
    }

    return input_summary, recommendations


@router.post("/optimizer/run", response_model=OptimizerRunRead, status_code=201,
             dependencies=[Depends(require_permission("ai_optimizer", "run"))])
async def run_optimizer(
    data:         OptimizerRunCreate,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    input_summary, recommendations = await _run_optimizer(
        str(data.campaign_id) if data.campaign_id else None,
        data.campaign_context,
        db,
    )
    obj = OptimizerRun(
        run_date=date.today(),
        triggered_by_id=current_user.id,
        campaign_id=data.campaign_id,
        campaign_context=data.campaign_context,
        input_summary=input_summary,
        recommendation_json=recommendations,
        status=OptimizerStatus.COMPLETE,
        notes=data.notes,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/optimizer/runs", response_model=List[OptimizerRunRead],
            dependencies=[Depends(require_permission("ai_optimizer", "view"))])
async def list_optimizer_runs(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(OptimizerRun).order_by(OptimizerRun.run_date.desc()).offset(skip).limit(limit)
    )
    return r.scalars().all()


@router.get("/optimizer/runs/{rid}", response_model=OptimizerRunRead,
            dependencies=[Depends(require_permission("ai_optimizer", "view"))])
async def get_optimizer_run(rid: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(OptimizerRun).where(OptimizerRun.id == rid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Optimizer run not found")
    return obj


@router.post("/optimizer/runs/{rid}/approve",
             dependencies=[Depends(require_permission("ai_optimizer", "approve"))])
async def approve_optimizer_run(rid: str, data: OptimizerApprove,
                                current_user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(OptimizerRun).where(OptimizerRun.id == rid))
    obj = r.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Optimizer run not found")
    obj.status       = OptimizerStatus.APPROVED
    obj.approved_by_id = current_user.id
    obj.approved_at  = datetime.now(timezone.utc)
    if data.notes:
        obj.notes = data.notes
    await db.commit()
    return {"status": "approved"}


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING ANALYTICS SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/summary",
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_analytics_summary(
    days: int = Query(30, ge=7, le=90),
    db:   AsyncSession = Depends(get_db),
):
    today   = date.today()
    from datetime import timedelta
    start   = today - timedelta(days=days)

    def _f(v):
        return float(v) if v is not None else 0.0

    # Active campaigns
    active_q = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.ACTIVE)
    )
    active_campaigns = active_q.scalar_one() or 0

    # Total spend
    trade_q = await db.execute(
        select(func.sum(TradeSpend.amount)).where(TradeSpend.spend_date >= start)
    )
    brand_q = await db.execute(
        select(func.sum(BrandSpend.amount)).where(BrandSpend.spend_date >= start)
    )
    total_trade_spend = _f(trade_q.scalar_one())
    total_brand_spend = _f(brand_q.scalar_one())

    # Campaign ROI avg
    roi_q = await db.execute(
        select(func.avg(Campaign.actual_roi)).where(
            Campaign.actual_roi.isnot(None),
            Campaign.start_date >= start,
        )
    )
    avg_campaign_roi = _f(roi_q.scalar_one())

    # Visits
    visit_q = await db.execute(
        select(func.count(CustomerVisit.id)).where(CustomerVisit.visit_date >= start)
    )
    visits_period = visit_q.scalar_one() or 0

    # Influencer reach
    reach_q = await db.execute(
        select(func.sum(InfluencerCampaignLink.impressions))
    )
    influencer_reach = _f(reach_q.scalar_one())

    # Ad spend + conversions
    ad_spend_q = await db.execute(
        select(
            func.sum(AdPerformance.spend),
            func.sum(AdPerformance.conversions),
            func.sum(AdPerformance.clicks),
            func.sum(AdPerformance.impressions),
        ).where(AdPerformance.ad_date >= start)
    )
    ads = ad_spend_q.one()
    ad_spend      = _f(ads[0])
    ad_conversions= int(ads[1] or 0)
    ad_clicks     = int(ads[2] or 0)
    ad_impressions= int(ads[3] or 0)
    ad_ctr        = ad_clicks / max(ad_impressions, 1)

    # E-commerce revenue
    ecomm_q = await db.execute(
        select(func.sum(StorePerformance.gmv)).where(StorePerformance.perf_date >= start)
    )
    ecommerce_revenue = _f(ecomm_q.scalar_one())

    # Customer segments count
    seg_q = await db.execute(select(func.count(CustomerSegment.id)).where(CustomerSegment.is_active == True))
    active_segments = seg_q.scalar_one() or 0

    # Surveys
    surv_q = await db.execute(
        select(func.count(Survey.id), func.sum(Survey.respondent_count))
        .where(Survey.survey_date >= start)
    )
    surv = surv_q.one()
    surveys_run    = int(surv[0] or 0)
    survey_responses = int(surv[1] or 0)

    return {
        "period_days":          days,
        "active_campaigns":     active_campaigns,
        "total_trade_spend":    total_trade_spend,
        "total_brand_spend":    total_brand_spend,
        "total_marketing_spend":total_trade_spend + total_brand_spend,
        "avg_campaign_roi":     avg_campaign_roi,
        "customer_visits":      visits_period,
        "influencer_reach":     influencer_reach,
        "ad_spend":             ad_spend,
        "ad_conversions":       ad_conversions,
        "ad_ctr":               ad_ctr,
        "ecommerce_revenue":    ecommerce_revenue,
        "active_segments":      active_segments,
        "surveys_run":          surveys_run,
        "survey_responses":     survey_responses,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING DASHBOARD (focused: campaigns + promotions KPIs + breakdowns)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/dashboard",
            dependencies=[Depends(require_permission("marketing", "view"))])
async def marketing_dashboard(db: AsyncSession = Depends(get_db)):
    """Returns all data needed by the Marketing Dashboard page."""
    from datetime import timedelta
    today = date.today()

    def _f(v): return float(v) if v is not None else 0.0

    # ── Campaign KPIs ─────────────────────────────────────────────────────────
    status_rows = await db.execute(
        select(Campaign.status, func.count(Campaign.id))
        .group_by(Campaign.status)
    )
    campaign_by_status: Dict[str, int] = {str(r[0].value): int(r[1]) for r in status_rows.all()}

    active_count    = campaign_by_status.get("ACTIVE", 0)
    planned_count   = campaign_by_status.get("PLANNED", 0)
    draft_count     = campaign_by_status.get("DRAFT", 0)
    completed_count = campaign_by_status.get("COMPLETED", 0)

    budget_q = await db.execute(
        select(func.sum(Campaign.budget), func.sum(Campaign.expected_revenue), func.sum(Campaign.actual_revenue))
    )
    brow = budget_q.one()
    total_budget            = _f(brow[0])
    total_expected_revenue  = _f(brow[1])
    total_actual_revenue    = _f(brow[2])

    # budget vs actual for top 10 campaigns (for chart)
    top_campaigns_q = await db.execute(
        select(
            Campaign.campaign_name,
            Campaign.budget,
            Campaign.actual_revenue,
            Campaign.expected_revenue,
        )
        .where(Campaign.budget.isnot(None))
        .order_by(Campaign.budget.desc())
        .limit(10)
    )
    budget_vs_actual = [
        {
            "name": r[0],
            "budget": _f(r[1]),
            "actual_revenue": _f(r[2]),
            "expected_revenue": _f(r[3]),
        }
        for r in top_campaigns_q.all()
    ]

    # ── Promotion KPIs ────────────────────────────────────────────────────────
    promo_status_q = await db.execute(
        select(Promotion.status, func.count(Promotion.id)).group_by(Promotion.status)
    )
    promotion_by_status: Dict[str, int] = {str(r[0].value): int(r[1]) for r in promo_status_q.all()}

    total_promotions   = sum(promotion_by_status.values())
    active_promotions  = promotion_by_status.get("ACTIVE", 0)

    # promotions by region
    promo_region_q = await db.execute(
        select(Promotion.region, func.count(Promotion.id))
        .where(Promotion.region.isnot(None))
        .group_by(Promotion.region)
        .order_by(func.count(Promotion.id).desc())
        .limit(8)
    )
    promotions_by_region = [
        {"region": r[0], "count": int(r[1])} for r in promo_region_q.all()
    ]

    # ── Campaign activity timeline (last 90 days: count per 2-week bucket) ────
    ninety_days_ago = today - timedelta(days=90)
    timeline_q = await db.execute(
        select(Campaign.start_date, Campaign.campaign_name, Campaign.status)
        .where(Campaign.start_date >= ninety_days_ago)
        .order_by(Campaign.start_date.asc())
        .limit(50)
    )
    recent_campaigns = [
        {
            "name": r[1],
            "start_date": str(r[0]),
            "status": str(r[2].value),
        }
        for r in timeline_q.all()
    ]

    return {
        # Campaign KPIs
        "campaign_by_status":       campaign_by_status,
        "active_campaigns":         active_count,
        "planned_campaigns":        planned_count,
        "draft_campaigns":          draft_count,
        "completed_campaigns":      completed_count,
        "total_budget":             total_budget,
        "total_expected_revenue":   total_expected_revenue,
        "total_actual_revenue":     total_actual_revenue,
        "expected_roi": (total_expected_revenue / total_budget) if total_budget > 0 else 0.0,
        "actual_roi":   (total_actual_revenue   / total_budget) if total_budget > 0 else 0.0,
        # Budget vs actual chart data
        "budget_vs_actual":         budget_vs_actual,
        # Promotion KPIs
        "total_promotions":         total_promotions,
        "active_promotions":        active_promotions,
        "promotion_by_status":      promotion_by_status,
        "promotions_by_region":     promotions_by_region,
        # Timeline
        "recent_campaigns":         recent_campaigns,
    }
