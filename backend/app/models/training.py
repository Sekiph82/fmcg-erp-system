from __future__ import annotations
import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class SkillCategory(str, PyEnum):
    TECHNICAL = "technical"
    SOFT = "soft"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    MANAGEMENT = "management"


class SkillLevel(str, PyEnum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TrainingType(str, PyEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    ONLINE = "online"
    CLASSROOM = "classroom"
    ON_JOB = "on_job"


class SessionStatus(str, PyEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentStatus(str, PyEnum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    WAIVED = "waived"


class CertificationStatus(str, PyEnum):
    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    REVOKED = "revoked"


class TRAIAgentType(str, PyEnum):
    SKILL_GAP_ADVISOR = "skill_gap_advisor"
    EFFECTIVENESS_ANALYZER = "effectiveness_analyzer"
    COMPLIANCE_RISK = "compliance_risk"


class TRAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class SkillMaster(Base):
    __tablename__ = "training_skills"

    skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_code = Column(String(50), unique=True, nullable=False)
    skill_name = Column(String(200), nullable=False)
    category = Column(Enum(SkillCategory), nullable=False)
    description = Column(Text, nullable=True)
    active_flag = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee_profiles = relationship("EmployeeSkillProfile", back_populates="skill", lazy="dynamic")


class EmployeeSkillProfile(Base):
    __tablename__ = "employee_skill_profiles"

    employee_skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    department_id = Column(String(100), nullable=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("training_skills.skill_id"), nullable=False)
    current_level = Column(Enum(SkillLevel, name="training_skilllevel"), nullable=True)
    required_level = Column(Enum(SkillLevel, name="training_skilllevel"), nullable=True)
    last_assessed_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skill = relationship("SkillMaster", back_populates="employee_profiles")

    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id", name="uq_employee_skill"),
    )


class TrainingProgram(Base):
    __tablename__ = "training_programs"

    training_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_code = Column(String(50), unique=True, nullable=False)
    training_name = Column(String(300), nullable=False)
    training_type = Column(Enum(TrainingType), nullable=False)
    category = Column(Enum(SkillCategory), nullable=False)
    duration_hours = Column(Numeric(6, 2), nullable=True)
    provider = Column(String(200), nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)
    mandatory_flag = Column(Boolean, default=False)
    validity_period_days = Column(Integer, nullable=True)
    active_flag = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("TrainingSession", back_populates="program", lazy="dynamic")
    assignments = relationship("TrainingAssignment", back_populates="program", lazy="dynamic")
    certifications = relationship("CertificationRecord", back_populates="program", lazy="dynamic")


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_id = Column(UUID(as_uuid=True), ForeignKey("training_programs.training_id"), nullable=False)
    session_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    location = Column(String(300), nullable=True)
    trainer_id = Column(String(100), nullable=True)
    trainer_name = Column(String(200), nullable=True)
    capacity = Column(Integer, nullable=True)
    enrolled_count = Column(Integer, default=0)
    status = Column(Enum(SessionStatus), default=SessionStatus.PLANNED, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    program = relationship("TrainingProgram", back_populates="sessions")
    assignments = relationship("TrainingAssignment", back_populates="session", lazy="dynamic")


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"

    assignment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    department_id = Column(String(100), nullable=True)
    training_id = Column(UUID(as_uuid=True), ForeignKey("training_programs.training_id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("training_sessions.session_id"), nullable=True)
    assigned_by = Column(String(200), nullable=True)
    due_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    status = Column(Enum(AssignmentStatus), default=AssignmentStatus.ASSIGNED, nullable=False)
    score = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    program = relationship("TrainingProgram", back_populates="assignments")
    session = relationship("TrainingSession", back_populates="assignments")

    __table_args__ = (
        UniqueConstraint("employee_id", "training_id", "session_id", name="uq_assignment_employee_training_session"),
    )


class CertificationRecord(Base):
    __tablename__ = "certification_records"

    certification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    training_id = Column(UUID(as_uuid=True), ForeignKey("training_programs.training_id"), nullable=True)
    certificate_name = Column(String(300), nullable=False)
    certificate_no = Column(String(100), nullable=True)
    issuer = Column(String(200), nullable=True)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    status = Column(Enum(CertificationStatus), default=CertificationStatus.VALID, nullable=False)
    document_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    program = relationship("TrainingProgram", back_populates="certifications")


class TrainingFeedback(Base):
    __tablename__ = "training_feedback"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(100), nullable=False)
    employee_name = Column(String(200), nullable=True)
    training_id = Column(UUID(as_uuid=True), ForeignKey("training_programs.training_id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("training_sessions.session_id"), nullable=True)
    rating = Column(Integer, nullable=False)
    content_rating = Column(Integer, nullable=True)
    trainer_rating = Column(Integer, nullable=True)
    relevance_rating = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employee_id", "training_id", "session_id", name="uq_feedback_employee_training_session"),
    )


class TRAIRecommendation(Base):
    __tablename__ = "tr_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(TRAIAgentType), nullable=False)
    status = Column(Enum(TRAIRecStatus), default=TRAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    employee_id = Column(String(100), nullable=True)
    department_id = Column(String(100), nullable=True)
    training_id = Column(UUID(as_uuid=True), nullable=True)
    certification_id = Column(UUID(as_uuid=True), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
