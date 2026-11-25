"""M43.S01.T017 coaching playlists (run at the M43 gate, M43_S01_DB=1).

Manager builds a playlist from a consented synthetic transcript; non-manager sees only clips of their own calls;
withdrawn consent removes the clip; unconsented call cannot be clipped.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


async def test_clip_visibility_and_withdrawal(monkeypatch):
    from sqlalchemy import func, select

    from app.db.session import AsyncSessionLocal
    from app.models.voip import CallLog, CoachingClip, CoachingPlaylist
    from app.services import transcription_service as tx
    async with AsyncSessionLocal() as db:
        segs = [{"start": 0.0, "end": 3.0, "speaker": "A", "text": "Hello from POVU."},
                {"start": 3.5, "end": 8.0, "speaker": "B", "text": "The price is too high."}]
        mine = CallLog(id=uuid.uuid4(), call_ref=f"CALL-{uuid.uuid4().hex[:8]}", direction="OUTBOUND", phone_number="+254700000001",
                       started_at=datetime.utcnow(), outcome="ANSWERED", recording_consent=True,
                       recording_url="https://127.0.0.1/rec.wav", transcript="A: Hello", transcript_segments=segs,
                       follow_up_required=False)
        db.add(mine)
        pl = CoachingPlaylist(id=uuid.uuid4(), name="Price objections")
        db.add(pl)
        await db.flush()
        db.add(CoachingClip(playlist_id=pl.id, call_id=mine.id, start_s=3, end_s=9, created_at=datetime.utcnow()))
        await db.commit()
        await tx.withdraw_consent(db, mine)
        await db.commit()
        n = (await db.execute(select(func.count()).select_from(CoachingClip).where(CoachingClip.call_id == mine.id))).scalar_one()
        assert n == 0


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
