from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.training import (
    SkillMaster, EmployeeSkillProfile, TrainingProgram, TrainingSession,
    TrainingAssignment, CertificationRecord, TrainingFeedback, TRAIRecommendation,
    SkillLevel, SessionStatus, AssignmentStatus, CertificationStatus,
    TRAIAgentType, TRAIRecStatus,
)
from app.schemas.training import (
    SkillCreate, SkillUpdate,
    EmployeeSkillCreate, EmployeeSkillUpdate,
    TrainingProgramCreate, TrainingProgramUpdate,
    SessionCreate, SessionUpdate,
    AssignmentCreate, AssignmentComplete,
    CertificationCreate, CertificationUpdate,
    FeedbackCreate, TRAIRecAck,
)

SKILL_LEVEL_ORDER = {
    SkillLevel.BASIC: 1,
    SkillLevel.INTERMEDIATE: 2,
    SkillLevel.ADVANCED: 3,
    SkillLevel.EXPERT: 4,
}

EXPIRY_WARNING_DAYS = 30


def _has_gap(current: Optional[SkillLevel], required: Optional[SkillLevel]) -> bool:
    if required is None:
        return False
    if current is None:
        return True
    return SKILL_LEVEL_ORDER.get(current, 0) < SKILL_LEVEL_ORDER.get(required, 0)


def _days_to_expiry(expiry_date: Optional[date]) -> Optional[int]:
    if expiry_date is None:
        return None
    return (expiry_date - date.today()).days


def _cert_status_from_expiry(expiry_date: Optional[date]) -> CertificationStatus:
    if expiry_date is None:
        return CertificationStatus.VALID
    days = _days_to_expiry(expiry_date)
    if days is None or days > EXPIRY_WARNING_DAYS:
        return CertificationStatus.VALID
    if days <= 0:
        return CertificationStatus.EXPIRED
    return CertificationStatus.EXPIRING


# ── Skill Master ──────────────────────────────────────────────────────────────

async def create_skill(db: AsyncSession, data: SkillCreate) -> SkillMaster:
    skill = SkillMaster(**data.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


async def list_skills(db: AsyncSession, category: Optional[str] = None, active_only: bool = False) -> List[SkillMaster]:
    q = select(SkillMaster).order_by(SkillMaster.skill_name)
    if category:
        q = q.where(SkillMaster.category == category)
    if active_only:
        q = q.where(SkillMaster.active_flag == True)
    result = await db.execute(q)
    return result.scalars().all()


async def get_skill(db: AsyncSession, skill_id: UUID) -> Optional[SkillMaster]:
    result = await db.execute(select(SkillMaster).where(SkillMaster.skill_id == skill_id))
    return result.scalar_one_or_none()


async def update_skill(db: AsyncSession, skill_id: UUID, data: SkillUpdate) -> Optional[SkillMaster]:
    skill = await get_skill(db, skill_id)
    if not skill:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(skill, k, v)
    skill.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(skill)
    return skill


async def seed_default_skills(db: AsyncSession) -> List[SkillMaster]:
    defaults = [
        ("SKL001", "Microsoft Excel", "technical"),
        ("SKL002", "Data Analysis", "technical"),
        ("SKL003", "Communication", "soft"),
        ("SKL004", "Leadership", "soft"),
        ("SKL005", "Teamwork", "soft"),
        ("SKL006", "Problem Solving", "soft"),
        ("SKL007", "Fire Safety", "safety"),
        ("SKL008", "First Aid", "safety"),
        ("SKL009", "Food Safety (HACCP)", "compliance"),
        ("SKL010", "ISO 9001 Quality", "compliance"),
        ("SKL011", "Project Management", "management"),
        ("SKL012", "People Management", "management"),
    ]
    created = []
    for code, name, cat in defaults:
        existing = await db.execute(select(SkillMaster).where(SkillMaster.skill_code == code))
        if not existing.scalar_one_or_none():
            s = SkillMaster(skill_code=code, skill_name=name, category=cat)
            db.add(s)
            created.append(s)
    if created:
        await db.commit()
    return created


# ── Employee Skill Profile ────────────────────────────────────────────────────

async def upsert_employee_skill(db: AsyncSession, data: EmployeeSkillCreate) -> EmployeeSkillProfile:
    result = await db.execute(
        select(EmployeeSkillProfile).where(
            and_(EmployeeSkillProfile.employee_id == data.employee_id,
                 EmployeeSkillProfile.skill_id == data.skill_id)
        )
    )
    profile = result.scalar_one_or_none()
    if profile:
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(profile, k, v)
        profile.updated_at = datetime.utcnow()
    else:
        profile = EmployeeSkillProfile(**data.model_dump())
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_employee_skill(db: AsyncSession, employee_skill_id: UUID, data: EmployeeSkillUpdate) -> Optional[EmployeeSkillProfile]:
    result = await db.execute(select(EmployeeSkillProfile).where(EmployeeSkillProfile.employee_skill_id == employee_skill_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(profile, k, v)
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_employee_skill_matrix(db: AsyncSession, employee_id: Optional[str] = None, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
    q = (
        select(EmployeeSkillProfile, SkillMaster)
        .join(SkillMaster, EmployeeSkillProfile.skill_id == SkillMaster.skill_id)
        .order_by(EmployeeSkillProfile.employee_id, SkillMaster.skill_name)
    )
    if employee_id:
        q = q.where(EmployeeSkillProfile.employee_id == employee_id)
    if department_id:
        q = q.where(EmployeeSkillProfile.department_id == department_id)
    result = await db.execute(q)
    rows = result.all()
    out = []
    for profile, skill in rows:
        gap = _has_gap(profile.current_level, profile.required_level)
        out.append({
            "employee_skill_id": str(profile.employee_skill_id),
            "employee_id": profile.employee_id,
            "employee_name": profile.employee_name,
            "department_id": profile.department_id,
            "skill_id": str(skill.skill_id),
            "skill_name": skill.skill_name,
            "skill_category": skill.category,
            "current_level": profile.current_level,
            "required_level": profile.required_level,
            "has_gap": gap,
            "last_assessed_date": str(profile.last_assessed_date) if profile.last_assessed_date else None,
            "notes": profile.notes,
            "created_at": profile.created_at.isoformat(),
        })
    return out


async def get_skill_gap_report(db: AsyncSession, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
    matrix = await get_employee_skill_matrix(db, department_id=department_id)
    return [row for row in matrix if row["has_gap"]]


# ── Training Program ──────────────────────────────────────────────────────────

async def create_program(db: AsyncSession, data: TrainingProgramCreate) -> TrainingProgram:
    program = TrainingProgram(**data.model_dump())
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def list_programs(db: AsyncSession, category: Optional[str] = None, mandatory_only: bool = False, active_only: bool = False) -> List[TrainingProgram]:
    q = select(TrainingProgram).order_by(TrainingProgram.training_name)
    if category:
        q = q.where(TrainingProgram.category == category)
    if mandatory_only:
        q = q.where(TrainingProgram.mandatory_flag == True)
    if active_only:
        q = q.where(TrainingProgram.active_flag == True)
    result = await db.execute(q)
    return result.scalars().all()


async def get_program(db: AsyncSession, training_id: UUID) -> Optional[TrainingProgram]:
    result = await db.execute(select(TrainingProgram).where(TrainingProgram.training_id == training_id))
    return result.scalar_one_or_none()


async def update_program(db: AsyncSession, training_id: UUID, data: TrainingProgramUpdate) -> Optional[TrainingProgram]:
    program = await get_program(db, training_id)
    if not program:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(program, k, v)
    program.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(program)
    return program


# ── Training Sessions ─────────────────────────────────────────────────────────

async def create_session(db: AsyncSession, data: SessionCreate) -> TrainingSession:
    session = TrainingSession(**data.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession, training_id: Optional[UUID] = None, status: Optional[str] = None, upcoming_only: bool = False, limit: int = 200) -> List[TrainingSession]:
    q = select(TrainingSession).order_by(TrainingSession.session_date)
    if training_id:
        q = q.where(TrainingSession.training_id == training_id)
    if status:
        q = q.where(TrainingSession.status == status)
    if upcoming_only:
        q = q.where(TrainingSession.session_date >= date.today())
    q = q.limit(limit)
    result = await db.execute(q)
    sessions = result.scalars().all()
    # attach training name
    for s in sessions:
        prog = await get_program(db, s.training_id)
        s._training_name = prog.training_name if prog else None
    return sessions


async def get_session(db: AsyncSession, session_id: UUID) -> Optional[TrainingSession]:
    result = await db.execute(select(TrainingSession).where(TrainingSession.session_id == session_id))
    return result.scalar_one_or_none()


async def update_session(db: AsyncSession, session_id: UUID, data: SessionUpdate) -> Optional[TrainingSession]:
    session = await get_session(db, session_id)
    if not session:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(session, k, v)
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session


async def complete_session(db: AsyncSession, session_id: UUID) -> Optional[TrainingSession]:
    session = await get_session(db, session_id)
    if not session:
        return None
    session.status = SessionStatus.COMPLETED
    session.updated_at = datetime.utcnow()
    # mark all enrolled assignments as completed
    result = await db.execute(
        select(TrainingAssignment).where(
            and_(TrainingAssignment.session_id == session_id,
                 TrainingAssignment.status == AssignmentStatus.IN_PROGRESS)
        )
    )
    for assignment in result.scalars().all():
        assignment.status = AssignmentStatus.COMPLETED
        assignment.completion_date = date.today()
        assignment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session


# ── Assignments ───────────────────────────────────────────────────────────────

async def create_assignment(db: AsyncSession, data: AssignmentCreate) -> TrainingAssignment:
    assignment = TrainingAssignment(**data.model_dump())
    db.add(assignment)
    if data.session_id:
        result = await db.execute(select(TrainingSession).where(TrainingSession.session_id == data.session_id))
        sess = result.scalar_one_or_none()
        if sess:
            sess.enrolled_count = (sess.enrolled_count or 0) + 1
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def list_assignments(db: AsyncSession, employee_id: Optional[str] = None, training_id: Optional[UUID] = None, status: Optional[str] = None, limit: int = 200) -> List[TrainingAssignment]:
    q = select(TrainingAssignment).order_by(TrainingAssignment.due_date)
    if employee_id:
        q = q.where(TrainingAssignment.employee_id == employee_id)
    if training_id:
        q = q.where(TrainingAssignment.training_id == training_id)
    if status:
        q = q.where(TrainingAssignment.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    assignments = result.scalars().all()
    for a in assignments:
        prog = await get_program(db, a.training_id)
        a._training_name = prog.training_name if prog else None
    return assignments


async def get_assignment(db: AsyncSession, assignment_id: UUID) -> Optional[TrainingAssignment]:
    result = await db.execute(select(TrainingAssignment).where(TrainingAssignment.assignment_id == assignment_id))
    return result.scalar_one_or_none()


async def complete_assignment(db: AsyncSession, assignment_id: UUID, data: AssignmentComplete) -> Optional[TrainingAssignment]:
    assignment = await get_assignment(db, assignment_id)
    if not assignment:
        return None
    assignment.status = AssignmentStatus.COMPLETED
    assignment.completion_date = data.completion_date or date.today()
    if data.score is not None:
        assignment.score = data.score
    if data.notes:
        assignment.notes = data.notes
    assignment.updated_at = datetime.utcnow()

    # auto-create cert if program has validity period
    prog = await get_program(db, assignment.training_id)
    if prog and prog.validity_period_days:
        expiry = assignment.completion_date + timedelta(days=prog.validity_period_days)
        cert = CertificationRecord(
            employee_id=assignment.employee_id,
            employee_name=assignment.employee_name,
            training_id=assignment.training_id,
            certificate_name=f"{prog.training_name} Certificate",
            issue_date=assignment.completion_date,
            expiry_date=expiry,
            status=CertificationStatus.VALID,
        )
        db.add(cert)

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def mark_overdue_assignments(db: AsyncSession) -> int:
    today = date.today()
    result = await db.execute(
        select(TrainingAssignment).where(
            and_(
                TrainingAssignment.due_date < today,
                TrainingAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS])
            )
        )
    )
    count = 0
    for a in result.scalars().all():
        a.status = AssignmentStatus.OVERDUE
        a.updated_at = datetime.utcnow()
        count += 1
    if count:
        await db.commit()
    return count


# ── Certifications ────────────────────────────────────────────────────────────

async def create_certification(db: AsyncSession, data: CertificationCreate) -> CertificationRecord:
    cert = CertificationRecord(**data.model_dump())
    cert.status = _cert_status_from_expiry(data.expiry_date)
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def list_certifications(db: AsyncSession, employee_id: Optional[str] = None, status: Optional[str] = None, expiring_days: Optional[int] = None, limit: int = 200) -> List[CertificationRecord]:
    q = select(CertificationRecord).order_by(CertificationRecord.expiry_date)
    if employee_id:
        q = q.where(CertificationRecord.employee_id == employee_id)
    if status:
        q = q.where(CertificationRecord.status == status)
    if expiring_days is not None:
        cutoff = date.today() + timedelta(days=expiring_days)
        q = q.where(and_(CertificationRecord.expiry_date <= cutoff, CertificationRecord.expiry_date >= date.today()))
    q = q.limit(limit)
    result = await db.execute(q)
    certs = result.scalars().all()
    for c in certs:
        c._days_to_expiry = _days_to_expiry(c.expiry_date)
    return certs


async def get_certification(db: AsyncSession, cert_id: UUID) -> Optional[CertificationRecord]:
    result = await db.execute(select(CertificationRecord).where(CertificationRecord.certification_id == cert_id))
    cert = result.scalar_one_or_none()
    if cert:
        cert._days_to_expiry = _days_to_expiry(cert.expiry_date)
    return cert


async def update_certification(db: AsyncSession, cert_id: UUID, data: CertificationUpdate) -> Optional[CertificationRecord]:
    cert = await get_certification(db, cert_id)
    if not cert:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cert, k, v)
    if data.expiry_date and not data.status:
        cert.status = _cert_status_from_expiry(data.expiry_date)
    cert.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cert)
    cert._days_to_expiry = _days_to_expiry(cert.expiry_date)
    return cert


async def refresh_certification_statuses(db: AsyncSession) -> int:
    result = await db.execute(select(CertificationRecord).where(CertificationRecord.status != CertificationStatus.REVOKED))
    count = 0
    for cert in result.scalars().all():
        new_status = _cert_status_from_expiry(cert.expiry_date)
        if cert.status != new_status:
            cert.status = new_status
            cert.updated_at = datetime.utcnow()
            count += 1
    if count:
        await db.commit()
    return count


# ── Feedback ──────────────────────────────────────────────────────────────────

async def submit_feedback(db: AsyncSession, data: FeedbackCreate) -> TrainingFeedback:
    feedback = TrainingFeedback(**data.model_dump())
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def list_feedback(db: AsyncSession, training_id: Optional[UUID] = None, limit: int = 200) -> List[TrainingFeedback]:
    q = select(TrainingFeedback).order_by(TrainingFeedback.created_at.desc())
    if training_id:
        q = q.where(TrainingFeedback.training_id == training_id)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_program_effectiveness(db: AsyncSession, training_id: UUID) -> Dict[str, Any]:
    result = await db.execute(select(TrainingFeedback).where(TrainingFeedback.training_id == training_id))
    feedbacks = result.scalars().all()
    if not feedbacks:
        return {"training_id": str(training_id), "feedback_count": 0, "avg_rating": None}
    avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
    avg_content = sum(f.content_rating for f in feedbacks if f.content_rating) / max(1, sum(1 for f in feedbacks if f.content_rating))
    avg_trainer = sum(f.trainer_rating for f in feedbacks if f.trainer_rating) / max(1, sum(1 for f in feedbacks if f.trainer_rating))
    return {
        "training_id": str(training_id),
        "feedback_count": len(feedbacks),
        "avg_rating": round(avg_rating, 2),
        "avg_content_rating": round(avg_content, 2),
        "avg_trainer_rating": round(avg_trainer, 2),
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    today = date.today()
    expiry_window = today + timedelta(days=EXPIRY_WARNING_DAYS)

    total_programs = (await db.execute(select(func.count(TrainingProgram.training_id)))).scalar() or 0
    active_programs = (await db.execute(select(func.count(TrainingProgram.training_id)).where(TrainingProgram.active_flag == True))).scalar() or 0
    total_sessions = (await db.execute(select(func.count(TrainingSession.session_id)))).scalar() or 0
    upcoming_sessions = (await db.execute(select(func.count(TrainingSession.session_id)).where(and_(TrainingSession.session_date >= today, TrainingSession.status == SessionStatus.PLANNED)))).scalar() or 0
    total_assignments = (await db.execute(select(func.count(TrainingAssignment.assignment_id)))).scalar() or 0
    completed_assignments = (await db.execute(select(func.count(TrainingAssignment.assignment_id)).where(TrainingAssignment.status == AssignmentStatus.COMPLETED))).scalar() or 0
    overdue_assignments = (await db.execute(select(func.count(TrainingAssignment.assignment_id)).where(TrainingAssignment.status == AssignmentStatus.OVERDUE))).scalar() or 0
    total_certs = (await db.execute(select(func.count(CertificationRecord.certification_id)))).scalar() or 0
    expiring_soon = (await db.execute(select(func.count(CertificationRecord.certification_id)).where(and_(CertificationRecord.expiry_date <= expiry_window, CertificationRecord.expiry_date >= today)))).scalar() or 0
    expired_certs = (await db.execute(select(func.count(CertificationRecord.certification_id)).where(CertificationRecord.status == CertificationStatus.EXPIRED))).scalar() or 0
    total_profiles = (await db.execute(select(func.count(EmployeeSkillProfile.employee_skill_id)))).scalar() or 0
    result = await db.execute(select(EmployeeSkillProfile))
    profiles = result.scalars().all()
    skill_gaps = sum(1 for p in profiles if _has_gap(p.current_level, p.required_level))
    feedback_result = await db.execute(select(func.avg(TrainingFeedback.rating)))
    avg_fb = feedback_result.scalar()

    return {
        "total_programs": total_programs,
        "active_programs": active_programs,
        "total_sessions": total_sessions,
        "upcoming_sessions": upcoming_sessions,
        "total_assignments": total_assignments,
        "completed_assignments": completed_assignments,
        "overdue_assignments": overdue_assignments,
        "total_certifications": total_certs,
        "expiring_soon": expiring_soon,
        "expired_certifications": expired_certs,
        "total_skill_profiles": total_profiles,
        "skill_gaps": skill_gaps,
        "avg_feedback_rating": round(float(avg_fb), 2) if avg_fb else None,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_completion(db: AsyncSession, training_id: Optional[UUID] = None) -> Dict[str, Any]:
    q = select(TrainingAssignment)
    if training_id:
        q = q.where(TrainingAssignment.training_id == training_id)
    result = await db.execute(q)
    assignments = result.scalars().all()
    total = len(assignments)
    completed = sum(1 for a in assignments if a.status == AssignmentStatus.COMPLETED)
    overdue = sum(1 for a in assignments if a.status == AssignmentStatus.OVERDUE)
    return {
        "total": total,
        "completed": completed,
        "overdue": overdue,
        "pending": total - completed - overdue,
        "completion_rate_pct": round(completed / total * 100, 1) if total else 0,
    }


async def report_certification_expiry(db: AsyncSession, days: int = 60) -> List[Dict[str, Any]]:
    certs = await list_certifications(db, expiring_days=days)
    expired_result = await db.execute(select(CertificationRecord).where(CertificationRecord.status == CertificationStatus.EXPIRED))
    expired = expired_result.scalars().all()
    all_certs = list(certs) + list(expired)
    return [
        {
            "certification_id": str(c.certification_id),
            "employee_id": c.employee_id,
            "employee_name": c.employee_name,
            "certificate_name": c.certificate_name,
            "expiry_date": str(c.expiry_date) if c.expiry_date else None,
            "days_to_expiry": _days_to_expiry(c.expiry_date),
            "status": c.status,
        }
        for c in all_certs
    ]


async def report_training_cost(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(TrainingProgram, func.count(TrainingAssignment.assignment_id)).outerjoin(TrainingAssignment, TrainingProgram.training_id == TrainingAssignment.training_id).group_by(TrainingProgram.training_id))
    rows = result.all()
    return [
        {
            "training_id": str(prog.training_id),
            "training_name": prog.training_name,
            "cost_per_head": float(prog.cost) if prog.cost else 0,
            "enrolled_count": count,
            "total_cost": float(prog.cost or 0) * count,
        }
        for prog, count in rows
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_skill_gap_advisor(db: AsyncSession) -> List[TRAIRecommendation]:
    matrix = await get_skill_gap_report(db)
    recs = []
    emp_gaps: Dict[str, List[str]] = {}
    for row in matrix:
        emp_gaps.setdefault(row["employee_id"], []).append(row["skill_name"])
    for emp_id, gaps in list(emp_gaps.items())[:10]:
        rec = TRAIRecommendation(
            agent_type=TRAIAgentType.SKILL_GAP_ADVISOR,
            title=f"Skill gaps identified: {emp_id}",
            body=(
                f"Employee {emp_id} has {len(gaps)} skill gap(s): "
                f"{', '.join(gaps[:5])}{'...' if len(gaps) > 5 else ''}. "
                f"Consider assigning relevant training programs."
            ),
            employee_id=emp_id,
            score=len(gaps),
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_effectiveness_analyzer(db: AsyncSession) -> List[TRAIRecommendation]:
    result = await db.execute(
        select(TrainingProgram.training_id, TrainingProgram.training_name, func.avg(TrainingFeedback.rating).label("avg_rating"), func.count(TrainingFeedback.feedback_id).label("count"))
        .outerjoin(TrainingFeedback, TrainingProgram.training_id == TrainingFeedback.training_id)
        .group_by(TrainingProgram.training_id, TrainingProgram.training_name)
        .having(func.count(TrainingFeedback.feedback_id) >= 3)
    )
    rows = result.all()
    recs = []
    for training_id, training_name, avg_rating, count in rows:
        if avg_rating and float(avg_rating) < 3.0:
            rec = TRAIRecommendation(
                agent_type=TRAIAgentType.EFFECTIVENESS_ANALYZER,
                title=f"Low effectiveness: {training_name}",
                body=(
                    f"Training '{training_name}' has an average feedback rating of "
                    f"{float(avg_rating):.1f}/5 from {count} participants. "
                    f"Review content quality, trainer effectiveness, or relevance."
                ),
                training_id=training_id,
                score=int(float(avg_rating) * 20),
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_compliance_risk_monitor(db: AsyncSession) -> List[TRAIRecommendation]:
    await refresh_certification_statuses(db)
    expiry_window = date.today() + timedelta(days=EXPIRY_WARNING_DAYS)
    result = await db.execute(
        select(CertificationRecord).where(
            or_(
                and_(CertificationRecord.expiry_date <= expiry_window, CertificationRecord.expiry_date >= date.today()),
                CertificationRecord.status == CertificationStatus.EXPIRED,
            )
        ).order_by(CertificationRecord.expiry_date)
    )
    certs = result.scalars().all()
    recs = []
    for cert in certs[:15]:
        days = _days_to_expiry(cert.expiry_date)
        expired = days is not None and days <= 0
        rec = TRAIRecommendation(
            agent_type=TRAIAgentType.COMPLIANCE_RISK,
            title=f"{'Expired' if expired else 'Expiring'} cert: {cert.employee_id} — {cert.certificate_name}",
            body=(
                f"{'Certificate has EXPIRED' if expired else f'Certificate expires in {days} days'}: "
                f"{cert.certificate_name} for employee {cert.employee_id}. "
                f"Initiate renewal immediately to maintain compliance."
            ),
            employee_id=cert.employee_id,
            certification_id=cert.certification_id,
            score=abs(days) if days is not None else 0,
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None, limit: int = 200) -> List[TRAIRecommendation]:
    q = select(TRAIRecommendation).order_by(TRAIRecommendation.created_at.desc())
    if status:
        q = q.where(TRAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: TRAIRecAck) -> Optional[TRAIRecommendation]:
    result = await db.execute(select(TRAIRecommendation).where(TRAIRecommendation.rec_id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    if data.actioned_by:
        rec.actioned_by = data.actioned_by
        rec.actioned_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rec)
    return rec
