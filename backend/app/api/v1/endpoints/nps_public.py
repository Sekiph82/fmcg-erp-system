"""Public one-time NPS survey (M40.S01.T001): the token in the link is the only credential."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import customer_feedback_service as fb

router = APIRouter()


class AnswerIn(BaseModel):
    score: int = Field(ge=0, le=10)
    comment: Optional[str] = Field(None, max_length=2000)


@router.get("/{token}")
async def get_survey(token: str, db: AsyncSession = Depends(get_db)):
    try:
        return await fb.public_survey(db, token[:100])
    except fb.FeedbackError as e:
        raise HTTPException(e.status, e.detail)


@router.post("/{token}")
async def answer_survey(token: str, body: AnswerIn, db: AsyncSession = Depends(get_db)):
    try:
        await fb.public_answer(db, token[:100], body.score, body.comment)
    except fb.FeedbackError as e:
        await db.rollback()
        raise HTTPException(e.status, e.detail)
    await db.commit()
    return {"detail": "Thank you for your feedback."}
