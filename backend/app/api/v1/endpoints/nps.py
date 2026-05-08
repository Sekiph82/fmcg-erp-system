"""NPS (Net Promoter Score) Tracking endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.nps import NPSSurvey, NPSResponse

router = APIRouter()


def _classify(score: int) -> str:
    if score >= 9:
        return "PROMOTER"
    if score >= 7:
        return "PASSIVE"
    return "DETRACTOR"


def _nps_score(responses: list) -> float:
    if not responses:
        return 0.0
    n = len(responses)
    promoters = sum(1 for r in responses if r.score >= 9)
    detractors = sum(1 for r in responses if r.score <= 6)
    return round((promoters - detractors) / n * 100, 1)


# ── Surveys ────────────────────────────────────────────────────────────────────

@router.get("/surveys", response_model=list)
async def list_surveys(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(NPSSurvey).options(selectinload(NPSSurvey.responses))
        .order_by(NPSSurvey.created_at.desc())
    )
    surveys = list(r.scalars())
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "target_type": s.target_type,
            "trigger": s.trigger,
            "question_text": s.question_text,
            "is_active": s.is_active,
            "response_count": len(s.responses),
            "nps_score": _nps_score(s.responses),
        }
        for s in surveys
    ]


@router.post("/surveys", status_code=201)
async def create_survey(body: dict, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    s = NPSSurvey(
        title=body["title"],
        target_type=body.get("target_type", "CUSTOMER"),
        trigger=body.get("trigger", "MANUAL"),
        question_text=body.get("question_text", "How likely are you to recommend us? (0-10)"),
        follow_up_text=body.get("follow_up_text"),
        created_by_id=current_user.id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return {"id": str(s.id), "title": s.title}


# ── Responses ──────────────────────────────────────────────────────────────────

@router.post("/responses", status_code=201)
async def submit_response(body: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    score = int(body["score"])
    if not 0 <= score <= 10:
        raise HTTPException(422, "Score must be 0-10")
    resp = NPSResponse(
        survey_id=uuid.UUID(body["survey_id"]),
        customer_id=uuid.UUID(body["customer_id"]),
        product_id=uuid.UUID(body["product_id"]) if body.get("product_id") else None,
        so_id=uuid.UUID(body["so_id"]) if body.get("so_id") else None,
        score=score,
        comment=body.get("comment"),
        channel=body.get("channel", "manual"),
        responded_at=datetime.utcnow(),
    )
    db.add(resp)
    await db.commit()
    return {
        "id": str(resp.id),
        "classification": _classify(score),
        "score": score,
    }


@router.get("/responses", response_model=list)
async def list_responses(
    survey_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(NPSResponse).options(
        selectinload(NPSResponse.customer),
        selectinload(NPSResponse.product),
    )
    if survey_id:
        q = q.where(NPSResponse.survey_id == survey_id)
    if customer_id:
        q = q.where(NPSResponse.customer_id == customer_id)
    if product_id:
        q = q.where(NPSResponse.product_id == product_id)
    r = await db.execute(q.order_by(NPSResponse.responded_at.desc()).limit(limit))
    return [
        {
            "id": str(resp.id),
            "survey_id": str(resp.survey_id),
            "customer_id": str(resp.customer_id),
            "customer_name": resp.customer.name if resp.customer else None,
            "product_id": str(resp.product_id) if resp.product_id else None,
            "product_name": resp.product.name if resp.product else None,
            "score": resp.score,
            "classification": _classify(resp.score),
            "comment": resp.comment,
            "channel": resp.channel,
            "responded_at": resp.responded_at.isoformat(),
        }
        for resp in r.scalars()
    ]


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def nps_analytics(
    survey_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(NPSResponse).options(
        selectinload(NPSResponse.customer),
        selectinload(NPSResponse.product),
    )
    if survey_id:
        q = q.where(NPSResponse.survey_id == survey_id)
    if product_id:
        q = q.where(NPSResponse.product_id == product_id)
    r = await db.execute(q)
    responses = list(r.scalars())

    if not responses:
        return {
            "nps_score": None,
            "total_responses": 0,
            "promoters": 0, "passives": 0, "detractors": 0,
            "score_distribution": {},
            "avg_score": None,
            "top_detractors": [],
            "top_promoters": [],
        }

    promoters = [r for r in responses if r.score >= 9]
    passives = [r for r in responses if 7 <= r.score <= 8]
    detractors = [r for r in responses if r.score <= 6]

    distribution: dict = {}
    for rr in responses:
        k = str(rr.score)
        distribution[k] = distribution.get(k, 0) + 1

    nps = round((len(promoters) - len(detractors)) / len(responses) * 100, 1)
    avg_score = round(sum(r.score for r in responses) / len(responses), 2)

    top_detractors = sorted(
        [r for r in detractors if r.comment],
        key=lambda x: x.score
    )[:5]
    top_promoters = sorted(
        [r for r in promoters if r.comment],
        key=lambda x: -x.score
    )[:5]

    return {
        "nps_score": nps,
        "total_responses": len(responses),
        "promoters": len(promoters),
        "passives": len(passives),
        "detractors": len(detractors),
        "promoter_pct": round(len(promoters) / len(responses) * 100, 1),
        "detractor_pct": round(len(detractors) / len(responses) * 100, 1),
        "score_distribution": distribution,
        "avg_score": avg_score,
        "top_detractors": [
            {"customer_name": r.customer.name if r.customer else None, "score": r.score, "comment": r.comment}
            for r in top_detractors
        ],
        "top_promoters": [
            {"customer_name": r.customer.name if r.customer else None, "score": r.score, "comment": r.comment}
            for r in top_promoters
        ],
    }


@router.get("/analytics/by-customer")
async def nps_by_customer(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(
            NPSResponse.customer_id,
            func.avg(NPSResponse.score).label("avg_score"),
            func.count().label("response_count"),
        )
        .group_by(NPSResponse.customer_id)
        .order_by(func.avg(NPSResponse.score))
        .limit(limit)
    )
    rows = r.all()
    from app.models.sales import Customer
    result = []
    for row in rows:
        cust_r = await db.execute(select(Customer).where(Customer.id == row.customer_id))
        cust = cust_r.scalar_one_or_none()
        result.append({
            "customer_id": str(row.customer_id),
            "customer_name": cust.name if cust else None,
            "avg_score": round(float(row.avg_score), 2),
            "response_count": row.response_count,
            "classification": _classify(round(float(row.avg_score))),
        })
    return result
