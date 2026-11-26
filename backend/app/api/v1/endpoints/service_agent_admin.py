"""Service-agent QA for staff (M50.S01.T006). Mounted by service_desk.py under /api/v1/service-desk/agent.
Reads: helpdesk view rights. Reviews and gap proposals: helpdesk edit rights or a service-agent profile. Approving or
rejecting a gap (it publishes a customer-visible article): service administrators, and never the proposer."""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.m50_service_agent import KBGapProposal, ServiceAgentTurn
from app.services import service_qa as qa

router = APIRouter()


def _sd():
    from app.api.v1.endpoints import service_desk
    return service_desk


async def _can_read(current_user=Depends(get_current_user)):
    _sd()._view(current_user)
    return current_user


async def _can_edit(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await _sd()._edit(db, current_user)
    return current_user


async def _can_decide(current_user=Depends(get_current_user)):
    _sd()._admin(current_user)
    return current_user


def _gap(p: KBGapProposal) -> dict:
    return {"id": str(p.id), "cluster_key": p.cluster_key, "topic": p.topic, "samples": p.sample_questions, "count": p.question_count,
            "languages": p.languages, "status": p.status, "title": p.proposed_title, "summary": p.proposed_summary,
            "content_md": p.proposed_content_md, "target_article_id": str(p.target_article_id) if p.target_article_id else None,
            "article_id": str(p.article_id) if p.article_id else None, "created_by": p.created_by, "decided_by": p.decided_by,
            "decision_note": p.decision_note, "created_at": p.created_at.isoformat() if p.created_at else None}


async def _run(db, coro):
    try:
        out = await coro
    except qa.QAError as e:
        await db.rollback()
        raise HTTPException(409, str(e))
    await db.commit()
    return out


@router.get("/metrics")
async def metrics(days: int = 30, db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    return await qa.metrics(db, max(1, min(days, 365)))


@router.get("/clusters")
async def clusters(days: int = 30, db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    props = {p.cluster_key: p for p in (await db.execute(select(KBGapProposal).order_by(KBGapProposal.created_at))).scalars()}
    return [{**c, "proposal": {"id": str(props[c["key"]].id), "status": props[c["key"]].status} if c["key"] in props else None}
            for c in await qa.unresolved_clusters(db, max(1, min(days, 365)))]


@router.get("/reviews/queue")
async def review_queue(db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    return await qa.review_queue(db)


class ReviewIn(BaseModel):
    verdict: Literal["CORRECT", "WRONG_CITATION", "INACCURATE", "UNSUPPORTED"]
    note: Optional[str] = Field(None, max_length=1000)


@router.post("/turns/{turn_id}/review")
async def review(turn_id: uuid.UUID, body: ReviewIn, db: AsyncSession = Depends(get_db), user=Depends(_can_edit)):
    t = await _run(db, qa.review(db, user, turn_id, body.verdict, body.note))
    return {"id": str(t.id), "verdict": t.review_verdict}


class GapIn(BaseModel):
    cluster_key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=3, max_length=300)
    summary: Optional[str] = Field(None, max_length=1000)
    content_md: str = Field(min_length=1, max_length=20000)
    target_article_id: Optional[uuid.UUID] = None
    days: int = Field(30, ge=1, le=365)


@router.post("/gaps", status_code=201)
async def propose(body: GapIn, db: AsyncSession = Depends(get_db), user=Depends(_can_edit)):
    p = await _run(db, qa.propose_gap(db, user, cluster_key=body.cluster_key, title=body.title, summary=body.summary,
                                      content_md=body.content_md, days=body.days, target_article_id=body.target_article_id))
    return _gap(p)


@router.get("/gaps")
async def gaps(db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    return [_gap(p) for p in (await db.execute(select(KBGapProposal).order_by(KBGapProposal.created_at.desc()).limit(200))).scalars()]


class GapEditIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    summary: Optional[str] = Field(None, max_length=1000)
    content_md: str = Field(min_length=1, max_length=20000)


@router.put("/gaps/{gap_id}")
async def edit_gap(gap_id: uuid.UUID, body: GapEditIn, db: AsyncSession = Depends(get_db), user=Depends(_can_edit)):
    return _gap(await _run(db, qa.edit_gap(db, user, gap_id, title=body.title, summary=body.summary, content_md=body.content_md)))


class GapDecisionIn(BaseModel):
    approve: bool
    note: Optional[str] = Field(None, max_length=500)


@router.post("/gaps/{gap_id}/decision")
async def decide(gap_id: uuid.UUID, body: GapDecisionIn, db: AsyncSession = Depends(get_db), user=Depends(_can_decide)):
    return _gap(await _run(db, qa.decide_gap(db, user, gap_id, body.approve, body.note)))


class RetestIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@router.post("/retest")
async def retest(body: RetestIn, db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    return await qa.retest(db, body.question)


@router.get("/safety")
async def safety(days: int = 90, db: AsyncSession = Depends(get_db), _u=Depends(_can_read)):
    return await qa.safety_cases(db, max(1, min(days, 365)))
