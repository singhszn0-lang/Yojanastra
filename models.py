
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    BigInteger, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class Citizen(Base):
    __tablename__ = "citizens"

    citizen_id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    age = Column(Integer)
    state = Column(String(100), nullable=False)
    category = Column(String(30))
    annual_income = Column(Numeric(12, 2))
    household_id = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    aadhaar_last4 = Column(String(4), nullable=True)
    family_annual_income = Column(Numeric(12, 2), nullable=True)
    class_12_percentile = Column(Numeric(5, 2), nullable=True)
    regular_course = Column(Boolean, nullable=True)
    receives_other_scholarship = Column(Boolean, nullable=True)
    created_at = Column(DateTime)


class Scheme(Base):
    __tablename__ = "schemes"

    scheme_id = Column(Integer, primary_key=True)
    scheme_name = Column(String(200), nullable=False)
    state = Column(String(100))
    min_age = Column(Integer)
    max_age = Column(Integer)
    max_annual_income = Column(Numeric(12, 2))
    eligible_categories = Column(Text)
    benefit_description = Column(Text)
    is_active = Column(Boolean)


class Application(Base):
    __tablename__ = "applications"

    application_id = Column(Integer, primary_key=True)
    citizen_id = Column(Integer, ForeignKey("citizens.citizen_id"), nullable=False)
    scheme_id = Column(Integer, ForeignKey("schemes.scheme_id"), nullable=False)
    household_id = Column(String(100), nullable=True)
    application_date = Column(DateTime)
    status = Column(String(30))
    review_remarks = Column(Text)


class Benefit(Base):
    __tablename__ = "benefits"

    benefit_id = Column(Integer, primary_key=True)
    citizen_id = Column(Integer, ForeignKey("citizens.citizen_id"), nullable=False)
    scheme_id = Column(Integer, ForeignKey("schemes.scheme_id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.application_id"))
    benefit_period = Column(String(30))
    benefit_status = Column(String(30))
    amount = Column(Numeric(12, 2))
    paid_at = Column(DateTime)


class DuplicateFlag(Base):
    __tablename__ = "duplicate_flags"

    flag_id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.application_id"), nullable=False
    )
    matched_application_id = Column(
        Integer, ForeignKey("applications.application_id")
    )
    rule_code = Column(String(10), nullable=False)
    reason = Column(Text, nullable=False)
    review_status = Column(String(30))
    created_at = Column(DateTime)


class OfficerReview(Base):
    __tablename__ = "officer_reviews"

    review_id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer, ForeignKey("applications.application_id"), nullable=False
    )
    officer_name = Column(String(120), nullable=False)
    decision = Column(String(30), nullable=False)
    remarks = Column(Text)
    reviewed_at = Column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(BigInteger, primary_key=True)
    actor_role = Column(String(30), nullable=False)
    actor_id = Column(String(100))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    details = Column(JSONB)
    created_at = Column(DateTime)
