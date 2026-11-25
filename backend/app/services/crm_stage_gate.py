"""One place that decides whether a CRM record may leave its pipeline stage (M43.S01.T010; T014 and T016 add
approval gates and required fields here). Called by every stage-changing write in crm_pipeline_service."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMPlaybook, CRMPlaybookRun, CRMRecord


async def check_stage_exit(db: AsyncSession, rec: CRMRecord, new_stage_id=None, closing: bool = False) -> None:
    """Raise 409 when the current stage has an unmet exit condition. No-op when the stage is unchanged."""
    if rec.stage_id is None or (new_stage_id is not None and str(new_stage_id) == str(rec.stage_id) and not closing):
        return
    blocking = (await db.execute(select(CRMPlaybook).where(
        CRMPlaybook.stage_id == rec.stage_id, CRMPlaybook.status == "PUBLISHED",
        CRMPlaybook.blocks_stage_exit.is_(True)))).scalars().all()
    for pb in blocking:
        done = (await db.execute(select(CRMPlaybookRun.id).join(CRMPlaybook, CRMPlaybook.id == CRMPlaybookRun.playbook_id)
                                 .where(CRMPlaybook.family_id == pb.family_id, CRMPlaybookRun.crm_record_id == rec.id,
                                        CRMPlaybookRun.completed.is_(True)).limit(1))).first()
        if done is None:
            raise HTTPException(409, {"code": "stage_gate", "message": f"Complete the playbook '{pb.name}' before "
                                      "moving this deal on.", "playbook_id": str(pb.id)})
