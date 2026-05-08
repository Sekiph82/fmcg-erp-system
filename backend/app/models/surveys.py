import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Date, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class SurveyType(str, enum.Enum):
    PULSE = "PULSE"
    ENGAGEMENT = "ENGAGEMENT"
    EXIT = "EXIT"
    ONBOARDING = "ONBOARDING"
    CUSTOM = "CUSTOM"


class SurveyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class QuestionType(str, enum.Enum):
    RATING = "RATING"          # 1-5 or 1-10 scale
    NPS = "NPS"                # 0-10 NPS scale
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TEXT = "TEXT"              # free text
    YES_NO = "YES_NO"
    LIKERT = "LIKERT"          # Strongly agree to Strongly disagree


class EmployeeSurvey(Base, TimestampMixin):
    __tablename__ = "employee_surveys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    survey_type = Column(String(30), nullable=False, default="PULSE")
    status = Column(String(20), nullable=False, default="DRAFT")
    anonymous_flag = Column(Boolean, default=True, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    target_department = Column(String(100), nullable=True)
    target_all = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    response_count = Column(Integer, default=0, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    questions = relationship("SurveyQuestion", back_populates="survey",
                             cascade="all, delete-orphan",
                             order_by="SurveyQuestion.display_order")
    responses = relationship("SurveyResponse", back_populates="survey",
                             cascade="all, delete-orphan")


class SurveyQuestion(Base, TimestampMixin):
    __tablename__ = "survey_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("employee_surveys.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False, default="RATING")
    required_flag = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    options = Column(JSON, nullable=True)       # for MULTIPLE_CHOICE: ["option1", "option2"]
    scale_min = Column(Integer, nullable=True)   # for RATING / NPS
    scale_max = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)  # e.g. "Work Environment", "Management"

    survey = relationship("EmployeeSurvey", back_populates="questions")


class SurveyResponse(Base, TimestampMixin):
    __tablename__ = "survey_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("employee_surveys.id", ondelete="CASCADE"), nullable=False)
    respondent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answers = Column(JSON, nullable=False, default=dict)   # {question_id: answer_value}
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_pct = Column(Integer, default=100, nullable=False)

    survey = relationship("EmployeeSurvey", back_populates="responses")
    respondent = relationship("User", foreign_keys=[respondent_id])
