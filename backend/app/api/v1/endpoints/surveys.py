"""Employee Survey & Engagement Module endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.surveys import EmployeeSurvey, SurveyQuestion, SurveyResponse

router = APIRouter()


# ── Surveys ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list)
async def list_surveys(
    status: Optional[str] = None,
    survey_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(EmployeeSurvey).options(selectinload(EmployeeSurvey.questions))
    if status:
        q = q.where(EmployeeSurvey.status == status)
    if survey_type:
        q = q.where(EmployeeSurvey.survey_type == survey_type)
    r = await db.execute(q.order_by(EmployeeSurvey.created_at.desc()))
    surveys = list(r.scalars())
    today = date.today()
    rows = []
    for s in surveys:
        is_open = (
            s.status == "ACTIVE"
            and (s.start_date is None or s.start_date <= today)
            and (s.end_date is None or s.end_date >= today)
        )
        rows.append({
            "id": str(s.id),
            "title": s.title,
            "description": s.description,
            "survey_type": s.survey_type,
            "status": s.status,
            "anonymous_flag": s.anonymous_flag,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "target_department": s.target_department,
            "target_all": s.target_all,
            "question_count": len(s.questions),
            "response_count": s.response_count,
            "is_open": is_open,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return rows


@router.get("/{survey_id}", response_model=dict)
async def get_survey(
    survey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(EmployeeSurvey).options(
            selectinload(EmployeeSurvey.questions),
            selectinload(EmployeeSurvey.created_by),
        ).where(EmployeeSurvey.id == survey_id)
    )
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Survey not found")
    return {
        "id": str(s.id),
        "title": s.title,
        "description": s.description,
        "survey_type": s.survey_type,
        "status": s.status,
        "anonymous_flag": s.anonymous_flag,
        "start_date": s.start_date.isoformat() if s.start_date else None,
        "end_date": s.end_date.isoformat() if s.end_date else None,
        "target_department": s.target_department,
        "target_all": s.target_all,
        "response_count": s.response_count,
        "created_by_name": s.created_by.full_name if s.created_by else None,
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type,
                "required_flag": q.required_flag,
                "display_order": q.display_order,
                "options": q.options,
                "scale_min": q.scale_min,
                "scale_max": q.scale_max,
                "category": q.category,
            }
            for q in s.questions
        ],
    }


@router.post("/", status_code=201)
async def create_survey(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    survey = EmployeeSurvey(
        title=body["title"],
        description=body.get("description"),
        survey_type=body.get("survey_type", "PULSE"),
        status="DRAFT",
        anonymous_flag=body.get("anonymous_flag", True),
        start_date=date.fromisoformat(body["start_date"]) if body.get("start_date") else None,
        end_date=date.fromisoformat(body["end_date"]) if body.get("end_date") else None,
        target_department=body.get("target_department"),
        target_all=body.get("target_all", True),
        created_by_id=current_user.id,
    )
    db.add(survey)
    await db.flush()

    for i, q_data in enumerate(body.get("questions", [])):
        q = SurveyQuestion(
            survey_id=survey.id,
            question_text=q_data["question_text"],
            question_type=q_data.get("question_type", "RATING"),
            required_flag=q_data.get("required_flag", True),
            display_order=q_data.get("display_order", i),
            options=q_data.get("options"),
            scale_min=q_data.get("scale_min", 1),
            scale_max=q_data.get("scale_max", 5),
            category=q_data.get("category"),
        )
        db.add(q)

    await db.commit()
    await db.refresh(survey)
    return {"id": str(survey.id), "title": survey.title, "status": survey.status}


@router.patch("/{survey_id}")
async def update_survey(
    survey_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(EmployeeSurvey).where(EmployeeSurvey.id == survey_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Survey not found")
    for k in ["title", "description", "survey_type", "status", "anonymous_flag",
              "target_department", "target_all"]:
        if k in body:
            setattr(s, k, body[k])
    if "start_date" in body and body["start_date"]:
        s.start_date = date.fromisoformat(body["start_date"])
    if "end_date" in body and body["end_date"]:
        s.end_date = date.fromisoformat(body["end_date"])
    await db.commit()
    return {"id": str(s.id), "status": s.status}


@router.post("/{survey_id}/launch")
async def launch_survey(
    survey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(EmployeeSurvey).where(EmployeeSurvey.id == survey_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Survey not found")
    if s.status not in ("DRAFT",):
        raise HTTPException(422, "Only DRAFT surveys can be launched")
    s.status = "ACTIVE"
    await db.commit()
    return {"id": str(s.id), "status": s.status}


@router.post("/{survey_id}/close")
async def close_survey(
    survey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(EmployeeSurvey).where(EmployeeSurvey.id == survey_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Survey not found")
    s.status = "CLOSED"
    await db.commit()
    return {"id": str(s.id), "status": s.status}


# ── Questions ──────────────────────────────────────────────────────────────────

@router.post("/{survey_id}/questions", status_code=201)
async def add_question(
    survey_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(EmployeeSurvey).where(EmployeeSurvey.id == survey_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Survey not found")
    q = SurveyQuestion(
        survey_id=survey_id,
        question_text=body["question_text"],
        question_type=body.get("question_type", "RATING"),
        required_flag=body.get("required_flag", True),
        display_order=body.get("display_order", 0),
        options=body.get("options"),
        scale_min=body.get("scale_min", 1),
        scale_max=body.get("scale_max", 5),
        category=body.get("category"),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return {"id": str(q.id)}


@router.delete("/{survey_id}/questions/{question_id}")
async def delete_question(
    survey_id: uuid.UUID,
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(SurveyQuestion).where(
            SurveyQuestion.id == question_id,
            SurveyQuestion.survey_id == survey_id,
        )
    )
    q = r.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")
    await db.delete(q)
    await db.commit()
    return {"ok": True}


# ── Responses ──────────────────────────────────────────────────────────────────

@router.post("/{survey_id}/respond", status_code=201)
async def submit_response(
    survey_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(EmployeeSurvey).options(selectinload(EmployeeSurvey.questions))
        .where(EmployeeSurvey.id == survey_id)
    )
    survey = r.scalar_one_or_none()
    if not survey:
        raise HTTPException(404, "Survey not found")
    if survey.status != "ACTIVE":
        raise HTTPException(422, "Survey is not active")

    answers = body.get("answers", {})
    total_q = len(survey.questions)
    answered = sum(1 for q in survey.questions if str(q.id) in answers and answers[str(q.id)] is not None)
    completion = int(answered / total_q * 100) if total_q else 100

    resp = SurveyResponse(
        survey_id=survey_id,
        respondent_id=None if survey.anonymous_flag else current_user.id,
        answers=answers,
        submitted_at=datetime.utcnow(),
        completion_pct=completion,
    )
    db.add(resp)
    survey.response_count = (survey.response_count or 0) + 1
    await db.commit()
    return {"id": str(resp.id), "completion_pct": completion}


# ── Results / Analytics ────────────────────────────────────────────────────────

@router.get("/{survey_id}/results")
async def survey_results(
    survey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(EmployeeSurvey).options(
            selectinload(EmployeeSurvey.questions),
            selectinload(EmployeeSurvey.responses),
        ).where(EmployeeSurvey.id == survey_id)
    )
    survey = r.scalar_one_or_none()
    if not survey:
        raise HTTPException(404, "Survey not found")

    responses = survey.responses
    total_responses = len(responses)

    question_stats = []
    for q in survey.questions:
        qid = str(q.id)
        all_answers = [r.answers.get(qid) for r in responses if r.answers.get(qid) is not None]
        stat: dict = {
            "question_id": qid,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "category": q.category,
            "answer_count": len(all_answers),
        }
        if q.question_type in ("RATING", "NPS", "LIKERT") and all_answers:
            numeric = [float(a) for a in all_answers if a is not None]
            if numeric:
                stat["avg"] = round(sum(numeric) / len(numeric), 2)
                stat["min"] = min(numeric)
                stat["max"] = max(numeric)
                stat["distribution"] = {}
                for v in numeric:
                    key = str(int(v))
                    stat["distribution"][key] = stat["distribution"].get(key, 0) + 1
        elif q.question_type in ("MULTIPLE_CHOICE", "YES_NO") and all_answers:
            counts: dict = {}
            for a in all_answers:
                key = str(a)
                counts[key] = counts.get(key, 0) + 1
            stat["distribution"] = counts
        elif q.question_type == "TEXT" and all_answers:
            stat["sample_responses"] = [str(a) for a in all_answers[:10]]
        question_stats.append(stat)

    # Overall engagement score (avg of all numeric answers 1-5, normalised to 0-100)
    all_numeric = []
    for q in survey.questions:
        if q.question_type in ("RATING", "LIKERT") and q.scale_max and q.scale_max > 0:
            qid = str(q.id)
            for resp in responses:
                val = resp.answers.get(qid)
                if val is not None:
                    try:
                        normalised = (float(val) - (q.scale_min or 1)) / ((q.scale_max or 5) - (q.scale_min or 1)) * 100
                        all_numeric.append(normalised)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

    engagement_score = round(sum(all_numeric) / len(all_numeric), 1) if all_numeric else None

    return {
        "survey_id": str(survey.id),
        "title": survey.title,
        "survey_type": survey.survey_type,
        "total_responses": total_responses,
        "engagement_score": engagement_score,
        "questions": question_stats,
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
async def survey_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    total_r = await db.execute(select(func.count()).select_from(EmployeeSurvey))
    active_r = await db.execute(
        select(func.count()).select_from(EmployeeSurvey).where(EmployeeSurvey.status == "ACTIVE")
    )
    closed_r = await db.execute(
        select(func.count()).select_from(EmployeeSurvey).where(EmployeeSurvey.status == "CLOSED")
    )
    resp_r = await db.execute(select(func.count()).select_from(SurveyResponse))
    recent_r = await db.execute(
        select(EmployeeSurvey).where(EmployeeSurvey.status == "ACTIVE")
        .order_by(EmployeeSurvey.end_date).limit(5)
    )
    recent = list(recent_r.scalars())
    return {
        "total_surveys": total_r.scalar_one(),
        "active_surveys": active_r.scalar_one(),
        "closed_surveys": closed_r.scalar_one(),
        "total_responses": resp_r.scalar_one(),
        "active_surveys_list": [
            {
                "id": str(s.id),
                "title": s.title,
                "survey_type": s.survey_type,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "response_count": s.response_count,
            }
            for s in recent
        ],
    }
