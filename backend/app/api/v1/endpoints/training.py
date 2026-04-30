from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.training import (
    SkillCreate, SkillUpdate, SkillOut,
    EmployeeSkillCreate, EmployeeSkillUpdate, EmployeeSkillOut,
    TrainingProgramCreate, TrainingProgramUpdate, TrainingProgramOut,
    SessionCreate, SessionUpdate, SessionOut,
    AssignmentCreate, AssignmentComplete, AssignmentOut,
    CertificationCreate, CertificationUpdate, CertificationOut,
    FeedbackCreate, FeedbackOut,
    TrainingDashboard, TRAIRecOut, TRAIRecAck,
)
import app.services.training_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=TrainingDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Skills ────────────────────────────────────────────────────────────────────

@router.post("/skills", response_model=SkillOut, status_code=201)
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_skill(db, data)


@router.get("/skills", response_model=List[SkillOut])
async def list_skills(
    category: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_skills(db, category, active_only)


@router.get("/skills/{skill_id}", response_model=SkillOut)
async def get_skill(skill_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_skill(db, skill_id)
    if not obj:
        raise HTTPException(404, "Skill not found")
    return obj


@router.patch("/skills/{skill_id}", response_model=SkillOut)
async def update_skill(skill_id: UUID, data: SkillUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_skill(db, skill_id, data)
    if not obj:
        raise HTTPException(404, "Skill not found")
    return obj


@router.post("/skills/seed-defaults", status_code=201)
async def seed_skills(db: AsyncSession = Depends(get_db)):
    created = await svc.seed_default_skills(db)
    return {"created": len(created)}


# ── Employee Skill Profiles ───────────────────────────────────────────────────

@router.post("/skill-profiles", response_model=EmployeeSkillOut, status_code=201)
async def upsert_skill_profile(data: EmployeeSkillCreate, db: AsyncSession = Depends(get_db)):
    return await svc.upsert_employee_skill(db, data)


@router.patch("/skill-profiles/{employee_skill_id}", response_model=EmployeeSkillOut)
async def update_skill_profile(employee_skill_id: UUID, data: EmployeeSkillUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_employee_skill(db, employee_skill_id, data)
    if not obj:
        raise HTTPException(404, "Skill profile not found")
    return obj


@router.get("/skill-matrix")
async def skill_matrix(
    employee_id: Optional[str] = None,
    department_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_employee_skill_matrix(db, employee_id, department_id)


@router.get("/skill-gap-report")
async def skill_gap_report(department_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_skill_gap_report(db, department_id)


# ── Training Programs ─────────────────────────────────────────────────────────

@router.post("/programs", response_model=TrainingProgramOut, status_code=201)
async def create_program(data: TrainingProgramCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_program(db, data)


@router.get("/programs", response_model=List[TrainingProgramOut])
async def list_programs(
    category: Optional[str] = None,
    mandatory_only: bool = False,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_programs(db, category, mandatory_only, active_only)


@router.get("/programs/{training_id}", response_model=TrainingProgramOut)
async def get_program(training_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_program(db, training_id)
    if not obj:
        raise HTTPException(404, "Program not found")
    return obj


@router.patch("/programs/{training_id}", response_model=TrainingProgramOut)
async def update_program(training_id: UUID, data: TrainingProgramUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_program(db, training_id, data)
    if not obj:
        raise HTTPException(404, "Program not found")
    return obj


@router.get("/programs/{training_id}/effectiveness")
async def program_effectiveness(training_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_program_effectiveness(db, training_id)


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(data: SessionCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_session(db, data)


@router.get("/sessions", response_model=List[SessionOut])
async def list_sessions(
    training_id: Optional[UUID] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    sessions = await svc.list_sessions(db, training_id, status, upcoming_only)
    out = []
    for s in sessions:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        d["training_name"] = getattr(s, "_training_name", None)
        out.append(d)
    return out


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_session(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def update_session(session_id: UUID, data: SessionUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_session(db, session_id, data)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
async def complete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.complete_session(db, session_id)
    if not obj:
        raise HTTPException(404, "Session not found")
    return obj


# ── Assignments ───────────────────────────────────────────────────────────────

@router.post("/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(data: AssignmentCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_assignment(db, data)


@router.get("/assignments", response_model=List[AssignmentOut])
async def list_assignments(
    employee_id: Optional[str] = None,
    training_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    assignments = await svc.list_assignments(db, employee_id, training_id, status)
    out = []
    for a in assignments:
        d = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        d["training_name"] = getattr(a, "_training_name", None)
        out.append(d)
    return out


@router.post("/assignments/{assignment_id}/complete", response_model=AssignmentOut)
async def complete_assignment(assignment_id: UUID, data: AssignmentComplete, db: AsyncSession = Depends(get_db)):
    obj = await svc.complete_assignment(db, assignment_id, data)
    if not obj:
        raise HTTPException(404, "Assignment not found")
    return obj


@router.post("/assignments/mark-overdue")
async def mark_overdue(db: AsyncSession = Depends(get_db)):
    count = await svc.mark_overdue_assignments(db)
    return {"marked_overdue": count}


# ── Certifications ────────────────────────────────────────────────────────────

@router.post("/certifications", response_model=CertificationOut, status_code=201)
async def create_certification(data: CertificationCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_certification(db, data)


@router.get("/certifications", response_model=List[CertificationOut])
async def list_certifications(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    certs = await svc.list_certifications(db, employee_id, status, expiring_days)
    out = []
    for c in certs:
        d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        d["days_to_expiry"] = getattr(c, "_days_to_expiry", None)
        out.append(d)
    return out


@router.get("/certifications/{cert_id}", response_model=CertificationOut)
async def get_certification(cert_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_certification(db, cert_id)
    if not obj:
        raise HTTPException(404, "Certification not found")
    d = {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
    d["days_to_expiry"] = getattr(obj, "_days_to_expiry", None)
    return d


@router.patch("/certifications/{cert_id}", response_model=CertificationOut)
async def update_certification(cert_id: UUID, data: CertificationUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_certification(db, cert_id, data)
    if not obj:
        raise HTTPException(404, "Certification not found")
    d = {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
    d["days_to_expiry"] = getattr(obj, "_days_to_expiry", None)
    return d


@router.post("/certifications/refresh-statuses")
async def refresh_cert_statuses(db: AsyncSession = Depends(get_db)):
    count = await svc.refresh_certification_statuses(db)
    return {"updated": count}


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackOut, status_code=201)
async def submit_feedback(data: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    return await svc.submit_feedback(db, data)


@router.get("/feedback", response_model=List[FeedbackOut])
async def list_feedback(training_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_feedback(db, training_id)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/completion")
async def report_completion(training_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.report_completion(db, training_id)


@router.get("/reports/certification-expiry")
async def report_cert_expiry(days: int = 60, db: AsyncSession = Depends(get_db)):
    return await svc.report_certification_expiry(db, days)


@router.get("/reports/training-cost")
async def report_training_cost(db: AsyncSession = Depends(get_db)):
    return await svc.report_training_cost(db)


@router.get("/reports/skill-gaps")
async def report_skill_gaps(department_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_skill_gap_report(db, department_id)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-skill-gap-advisor", response_model=List[TRAIRecOut])
async def run_skill_gap_advisor(db: AsyncSession = Depends(get_db)):
    return await svc.run_skill_gap_advisor(db)


@router.post("/ai/run-effectiveness-analyzer", response_model=List[TRAIRecOut])
async def run_effectiveness_analyzer(db: AsyncSession = Depends(get_db)):
    return await svc.run_effectiveness_analyzer(db)


@router.post("/ai/run-compliance-risk", response_model=List[TRAIRecOut])
async def run_compliance_risk(db: AsyncSession = Depends(get_db)):
    return await svc.run_compliance_risk_monitor(db)


@router.get("/ai/recommendations", response_model=List[TRAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=TRAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: TRAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
