"""M50.S01.T012 AI evaluation: corpora, runs, review. Mounted under /api/v1/ai-agents/evals (see ai_agents.py).

View: ai.view (inherited from the parent router). Run: ai.create or ai.edit. Review: ai.approve, and not the person who
started the run. Every stored run is labelled SYNTHETIC: it measures behaviour on the synthetic corpus, not production accuracy.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m50_ai_platform import AIEvalCaseResult, AIEvalRun
from app.services import ai_eval
from app.services import pat_service as pats
from app.services.ai_eval.adapters import ADAPTERS

router = APIRouter()
LABEL = "SYNTHETIC: behaviour on synthetic POVU test data. Not a measure of real-world accuracy; real calibration is stored separately."


def _can(u, *perms):
    if not (u.is_superuser or has_any_permission(u, perms)):
        raise HTTPException(403, f"Needs {' or '.join(perms)}.")


def _run(r: AIEvalRun) -> dict:
    return {"id": str(r.id), "corpus_id": r.corpus_id, "corpus_version": r.corpus_version, "corpus_sha256": r.corpus_sha256,
            "adapter": r.adapter, "model_id": r.model_id, "provider": r.provider, "config_hash": r.config_hash, "config": r.config,
            "data_kind": r.data_kind, "label": LABEL if r.data_kind == "SYNTHETIC" else None, "real_calibration": r.real_calibration,
            "status": r.status, "note": r.note, "total": r.total, "passed": r.passed, "summary": r.summary,
            "review_status": r.review_status, "reviewed_by": r.reviewed_by, "review_note": r.review_note,
            "created_by": r.created_by, "created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/corpora")
async def corpora(db: AsyncSession = Depends(get_db)):
    ctx = {"db": db}
    return {"label": LABEL, "corpora": ai_eval.list_corpora(),
            "adapters": {k: {"model_id": v["model_id"], "provider": v["provider"], "tasks": v["tasks"],
                             "available": v["available"](ctx)[0], "unavailable_reason": v["available"](ctx)[1] or None}
                         for k, v in ADAPTERS.items()}}


@router.get("/corpora/{corpus_id}/verify")
async def verify(corpus_id: str):
    try:
        problems = ai_eval.verify_corpus(ai_eval.load_corpus(corpus_id))
    except ai_eval.EvalError as e:
        raise HTTPException(404, str(e))
    return {"corpus_id": corpus_id, "ok": not problems, "problems": problems}


class RunIn(BaseModel):
    corpus_id: str = Field(max_length=40)
    adapter: Literal["golden", "simulator", "service_policy", "agent_tools", "prospecting", "research", "kb", "llm"]


@router.post("/runs", status_code=201)
async def start(body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "ai.create", "ai.edit")
    try:
        run = await ai_eval.run_and_store(db, body.corpus_id, body.adapter, current_user.username, {"db": db})
    except ai_eval.EvalError as e:
        raise HTTPException(404, str(e))
    pats.audit(db, current_user, "AI_EVAL_RUN", "ai_eval_run", str(run.id),
               {"corpus": body.corpus_id, "adapter": body.adapter, "status": run.status, "passed": run.passed, "total": run.total})
    await db.commit()
    await db.refresh(run)
    return _run(run)


@router.get("/runs")
async def runs(corpus_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(AIEvalRun).order_by(AIEvalRun.created_at.desc()).limit(100)
    if corpus_id:
        q = q.where(AIEvalRun.corpus_id == corpus_id)
    return {"label": LABEL, "runs": [_run(r) for r in (await db.execute(q)).scalars()]}


@router.get("/runs/{rid}")
async def run_detail(rid: uuid.UUID, failed_only: bool = False, db: AsyncSession = Depends(get_db)):
    r = await db.get(AIEvalRun, rid)
    if r is None:
        raise HTTPException(404, "Run not found")
    q = select(AIEvalCaseResult).where(AIEvalCaseResult.run_id == rid).order_by(AIEvalCaseResult.case_id)
    if failed_only:
        q = q.where(AIEvalCaseResult.passed.is_(False))
    return {**_run(r), "results": [{"case_id": c.case_id, "passed": c.passed, "scores": c.scores, "expected": c.expected, "actual": c.actual,
                                    "latency_ms": c.latency_ms, "tokens": c.tokens, "cost": str(c.cost), "error": c.error}
                                   for c in (await db.execute(q)).scalars()]}


class ReviewIn(BaseModel):
    verdict: Literal["ACCEPTED", "REJECTED"]
    note: str = Field(min_length=3, max_length=500)


@router.post("/runs/{rid}/review")
async def review(rid: uuid.UUID, body: ReviewIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "ai.approve")
    r = await db.get(AIEvalRun, rid, with_for_update=True)
    if r is None:
        raise HTTPException(404, "Run not found")
    if r.created_by == current_user.username:
        raise HTTPException(403, "A second person must review an evaluation run.")
    r.review_status, r.reviewed_by, r.review_note = body.verdict, current_user.username, body.note
    pats.audit(db, current_user, "AI_EVAL_REVIEW", "ai_eval_run", str(r.id), {"verdict": body.verdict})
    await db.commit()
    return _run(r)


@router.get("/compare")
async def compare(a: uuid.UUID, b: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Per-case difference between two runs of the same corpus (regressions = passed in A, failed in B)."""
    ra, rb = await db.get(AIEvalRun, a), await db.get(AIEvalRun, b)
    if ra is None or rb is None:
        raise HTTPException(404, "Run not found")
    if ra.corpus_id != rb.corpus_id:
        raise HTTPException(422, "Runs are of different corpora.")

    async def res(rid):
        return {c.case_id: c.passed for c in (await db.execute(select(AIEvalCaseResult).where(AIEvalCaseResult.run_id == rid))).scalars()}
    xa, xb = await res(a), await res(b)
    return {"corpus_id": ra.corpus_id, "same_digest": (ra.summary or {}).get("digest") == (rb.summary or {}).get("digest"),
            "same_config": ra.config_hash == rb.config_hash,
            "regressions": sorted(k for k in xa if xa[k] and xb.get(k) is False), "fixed": sorted(k for k in xa if xa[k] is False and xb.get(k))}
