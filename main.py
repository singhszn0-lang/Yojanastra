import os
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, func
from sqlalchemy.orm import Session

import models
from database import get_db
from models import Application, Scheme, DuplicateFlag, OfficerReview
from evidence import generate_evidence
from eligibility import check_eligibility, check_csss_eligibility

load_dotenv()

app = FastAPI(
    title="Yojanastra API",
    description="Public Benefit Application Verification System",
    version="1.0.0",
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()


# Development demo account only.
# Replace with database-backed users before deployment.
DEMO_USERS = {
    "officer": {
        "username": "officer",
        "password_hash": password_hash.hash("DemoPass123!"),
        "role": "OFFICER",
    }
}

def create_access_token(username: str, role: str):
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": username, "role": role, "exp": expires}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = DEMO_USERS.get(form.username)

    if not user or not password_hash.verify(
        form.password, user["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        username = payload.get("sub")
        role = payload.get("role")

        if not username or not role:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"username": username, "role": role}

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_officer(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "OFFICER":
        raise HTTPException(
            status_code=403,
            detail="Officer access required",
        )
    return current_user

# Development only. Restrict origins before public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# TEMPORARY MOCK DATA — DATABASE WILL BE ADDED LATER
# Data resets whenever the server process restarts.
# --------------------------------------------------




# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1, max_length=100)
    scheme_id: int = Field(gt=0)
    household_id: Optional[str] = Field(default=None, max_length=100)


class CitizenCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    state: str = Field(min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=30)
    annual_income: Optional[float] = Field(default=None, ge=0)
    phone: Optional[str] = Field(default=None, max_length=20)
    aadhaar_last4: Optional[str] = Field(default=None, pattern=r"^\d{4}$")
    family_annual_income: Optional[float] = Field(default=None, ge=0)
    class_12_percentile: Optional[float] = Field(default=None, ge=0, le=100)
    regular_course: Optional[bool] = None
    receives_other_scholarship: Optional[bool] = None

    @field_validator("full_name", "state")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value is not None else None


class FamilyCreate(BaseModel):
    household_id: str = Field(min_length=1, max_length=100)
    members: list[CitizenCreate] = Field(min_length=1)


class CsssEligibilityRequest(BaseModel):
    family_annual_income: Optional[float] = Field(default=None, ge=0)
    class_12_percentile: Optional[float] = Field(default=None, ge=0, le=100)
    regular_course: Optional[bool] = None
    receives_other_scholarship: Optional[bool] = None


class EligibilityCheckRequest(BaseModel):
    scheme_id: Optional[int] = None
    annual_income: Optional[float] = None
    age: Optional[int] = None
    residence: Optional[str] = None

class OfficerReviewCreate(BaseModel):
    application_id: int = Field(gt=0)
    officer_name: str = Field(min_length=1, max_length=150)
    decision: Literal[
        "NEEDS_INFO",
        "CONFIRMED_DUPLICATE",
        "NOT_DUPLICATE",
        "APPROVE",
        "REJECT",
    ]
    remarks: str = Field(min_length=1, max_length=2000)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def add_audit(db, action, entity_type, entity_id, details):
    db.add(models.AuditLog(
        actor_role=details.get("actor_role", "SYSTEM"),
        actor_id=details.get("actor_id", "system"),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------
@app.post("/eligibility/check")
def eligibility_check_api(
    applicant: EligibilityCheckRequest
):
    applicant_data = applicant.model_dump()

    result = check_eligibility(applicant_data)

    evidence_result = generate_evidence(
        applicant_data,
        result
    )

    return {
        **result,
        "evidence": evidence_result["evidence"],
        "evidence_note": evidence_result["note"]
    }


@app.post("/eligibility/csss-preview")
def csss_eligibility_preview(applicant: CsssEligibilityRequest):
    return check_csss_eligibility(applicant.model_dump())


@app.get("/")
def home():
    return {
        "project": "Yojanastra",
        "message": "Backend is running!",
        "status": "success",
       "mode": "postgresql",
      "database_connected": True,
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(func.now().select())
    return {
        "status": "healthy",
        "database": "connected",
    }
# --------------------------------------------------
# SCHEMES
# --------------------------------------------------

@app.get("/citizens")
def get_citizens(db: Session = Depends(get_db)):
    citizens = (
        db.query(models.Citizen)
        .order_by(models.Citizen.citizen_id.desc())
        .all()
    )
    return [
        {
            "citizen_id": citizen.citizen_id,
            "full_name": citizen.full_name,
            "state": citizen.state,
            "household_id": citizen.household_id,
        }
        for citizen in citizens
    ]


@app.post("/citizens", status_code=201)
def register_citizen(citizen: CitizenCreate, db: Session = Depends(get_db)):
    record = models.Citizen(
        full_name=citizen.full_name.strip(),
        age=citizen.age,
        state=citizen.state.strip(),
        category=citizen.category.strip() if citizen.category else None,
        annual_income=citizen.annual_income,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(record)
    db.flush()
    add_audit(
        db,
        "CITIZEN_REGISTERED",
        "CITIZEN",
        record.citizen_id,
        {"actor_role": "SYSTEM", "actor_id": str(record.citizen_id)},
    )
    db.commit()
    db.refresh(record)
    return {
        "citizen_id": record.citizen_id,
        "full_name": record.full_name,
        "state": record.state,
    }


@app.post("/families", status_code=201)
def register_family(family: FamilyCreate, db: Session = Depends(get_db)):
    household_id = family.household_id.strip()
    if not household_id:
        raise HTTPException(
            status_code=422,
            detail="Household ID cannot be blank",
        )

    records = [
        models.Citizen(
            full_name=member.full_name.strip(),
            age=member.age,
            state=member.state.strip(),
            category=member.category.strip() if member.category else None,
            annual_income=member.annual_income,
            household_id=household_id,
            phone=member.phone.strip() if member.phone else None,
            aadhaar_last4=member.aadhaar_last4,
            family_annual_income=member.family_annual_income,
            class_12_percentile=member.class_12_percentile,
            regular_course=member.regular_course,
            receives_other_scholarship=member.receives_other_scholarship,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        for member in family.members
    ]
    db.add_all(records)
    db.flush()

    for record in records:
        add_audit(
            db,
            "CITIZEN_REGISTERED",
            "CITIZEN",
            record.citizen_id,
            {
                "actor_role": "SYSTEM",
                "actor_id": str(record.citizen_id),
                "household_id": household_id,
            },
        )

    db.commit()
    return {
        "message": f"{len(records)} family member(s) registered successfully",
        "household_id": household_id,
        "members": [
            {
                "citizen_id": record.citizen_id,
                "full_name": record.full_name,
                "state": record.state,
            }
            for record in records
        ],
    }


@app.get("/schemes")
def get_schemes(db: Session = Depends(get_db)):
    schemes = (
        db.query(Scheme)
        .order_by(Scheme.scheme_id)
        .all()
    )
    return [
        {
            "scheme_id": scheme.scheme_id,
            "name": scheme.scheme_name,
            "category": scheme.eligible_categories,
            "description": scheme.benefit_description,
            "is_active": scheme.is_active,
            "state": scheme.state,
            "min_age": scheme.min_age,
            "max_age": scheme.max_age,
            "max_annual_income": scheme.max_annual_income,
        }
        for scheme in schemes
    ]


@app.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: int, db: Session = Depends(get_db)):
    scheme = db.query(Scheme).filter(
        Scheme.scheme_id == scheme_id
    ).first()

    if not scheme:
        raise HTTPException(404, "Scheme not found")

    return {
        "scheme_id": scheme.scheme_id,
        "name": scheme.scheme_name,
        "category": scheme.eligible_categories,
        "description": scheme.benefit_description,
        "is_active": scheme.is_active,
        "state": scheme.state,
        "min_age": scheme.min_age,
        "max_age": scheme.max_age,
        "max_annual_income": scheme.max_annual_income,
    }


# --------------------------------------------------
# DASHBOARD STATISTICS
# --------------------------------------------------

@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return {
        "total_applications":
            db.query(Application).count(),

        "pending_applications":
            db.query(Application)
            .filter(Application.status == "PENDING")
            .count(),

        "total_duplicate_flags":
            db.query(DuplicateFlag).count(),

        "pending_reviews":
            db.query(DuplicateFlag)
            .filter(DuplicateFlag.review_status == "PENDING")
            .count(),

        "completed_reviews":
            db.query(OfficerReview).count(),

        "total_schemes":
            db.query(Scheme)
            .filter(Scheme.is_active == True)
            .count(),
    }


# --------------------------------------------------
# SUBMIT APPLICATION
# --------------------------------------------------


@app.post("/applications", status_code=201)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
):
    try:
        citizen_id = int(application.citizen_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="citizen_id must be a valid integer",
        )

    citizen = (
        db.query(models.Citizen)
        .filter(models.Citizen.citizen_id == citizen_id)
        .first()
    )

    if not citizen:
        raise HTTPException(
            status_code=404,
            detail="Citizen not found. Register the citizen first.",
        )

    scheme = (
        db.query(models.Scheme)
        .filter(
            models.Scheme.scheme_id == application.scheme_id,
            models.Scheme.is_active.is_(True),
        )
        .first()
    )

    if not scheme:
        raise HTTPException(
            status_code=404,
            detail="Active scheme not found",
        )

    previous = (
        db.query(Application)
        .filter(
            Application.citizen_id == citizen_id,
            Application.scheme_id == application.scheme_id,
        )
        .order_by(Application.application_id.desc())
        .first()
    )
    record = Application(
        citizen_id=citizen_id,
        scheme_id=application.scheme_id,
        household_id=application.household_id,
        application_date=datetime.now(timezone.utc).replace(tzinfo=None),
        status="PENDING",
    )
    db.add(record)
    db.flush()

    flag = None
    if previous:
        flag = DuplicateFlag(
            application_id=record.application_id,
            matched_application_id=previous.application_id,
            rule_code="R1",
            reason=(
                "Same citizen and scheme found in an earlier application. "
                "Human review required before any decision."
            ),
            review_status="PENDING",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(flag)
        db.flush()
        add_audit(
            db,
            "POSSIBLE_DUPLICATE_FLAGGED",
            "APPLICATION",
            record.application_id,
            {
                "actor_role": "SYSTEM",
                "actor_id": "duplicate_checker",
                "flag_id": flag.flag_id,
                "matched_application_id": previous.application_id,
            },
        )

    add_audit(
        db,
        "APPLICATION_SUBMITTED",
        "APPLICATION",
        record.application_id,
        {
            "actor_role": "SYSTEM",
            "actor_id": str(citizen_id),
            "scheme_id": application.scheme_id,
        },
    )
    db.commit()

    return {
        "message": "Application submitted successfully",
        "application_id": record.application_id,
        "status": "PENDING",
        "possible_duplicate": previous is not None,
        "flag_id": flag.flag_id if flag else None,
        "review_status": "PENDING" if previous else None,
    }


# --------------------------------------------------
# LIST AND VIEW APPLICATIONS
# --------------------------------------------------

@app.get("/applications")
def get_applications(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Application, models.Citizen, Scheme)
        .join(models.Citizen, Application.citizen_id == models.Citizen.citizen_id)
        .join(Scheme, Application.scheme_id == Scheme.scheme_id)
    )
    if status:
        query = query.filter(func.upper(Application.status) == status.upper())
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            models.Citizen.full_name.ilike(pattern)
            | func.cast(models.Citizen.citizen_id, String).ilike(pattern)
            | func.cast(Application.application_id, String).ilike(pattern)
            | Scheme.scheme_name.ilike(pattern)
        )

    return [
        _application_response(application, citizen, scheme, db)
        for application, citizen, scheme in
        query.order_by(Application.application_id.desc()).all()
    ]


@app.get("/applications/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(Application, models.Citizen, Scheme)
        .join(models.Citizen, Application.citizen_id == models.Citizen.citizen_id)
        .join(Scheme, Application.scheme_id == Scheme.scheme_id)
        .filter(Application.application_id == application_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return _application_response(*row, db)


def _application_response(application, citizen, scheme, db):
    has_duplicate = (
        db.query(DuplicateFlag.flag_id)
        .filter(DuplicateFlag.application_id == application.application_id)
        .first()
        is not None
    )
    return {
        "application_id": application.application_id,
        "citizen_id": str(citizen.citizen_id),
        "applicant_name": citizen.full_name,
        "annual_income": citizen.annual_income,
        "scheme_id": scheme.scheme_id,
        "scheme_name": scheme.scheme_name,
        "household_id": application.household_id,
        "status": application.status,
        "possible_duplicate": has_duplicate,
        "created_at": application.application_date,
    }


# --------------------------------------------------
# DUPLICATE REVIEW QUEUE
# --------------------------------------------------

@app.get("/duplicate-flags")
def get_duplicate_flags(
    review_status: Optional[str] = "PENDING",
    db: Session = Depends(get_db),
):
    query = db.query(DuplicateFlag)
    if review_status:
        query = query.filter(
            func.upper(DuplicateFlag.review_status) == review_status.upper()
        )
    return [
        {
            "flag_id": flag.flag_id,
            "application_id": flag.application_id,
            "matched_application_id": flag.matched_application_id,
            "rule_code": flag.rule_code,
            "reason": flag.reason,
            "review_status": flag.review_status,
            "created_at": flag.created_at,
        }
        for flag in query.order_by(DuplicateFlag.flag_id.desc()).all()
    ]


# --------------------------------------------------
# OFFICER REVIEW
# --------------------------------------------------

@app.post("/officer-reviews", status_code=201)
def create_officer_review(
    review: OfficerReviewCreate,
    current_user: dict = Depends(require_officer),
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(
        Application.application_id == review.application_id
    ).first()
    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    flag = (
        db.query(DuplicateFlag)
        .filter(DuplicateFlag.application_id == review.application_id)
        .order_by(DuplicateFlag.flag_id.desc())
        .first()
    )
    flag_pending = flag and flag.review_status in ("PENDING", "NEEDS_INFO")
    if flag and not flag_pending and review.decision not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=409,
            detail="This flag has already received a final review",
        )

    if application.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="This application has already received a decision",
        )

    if not flag_pending and review.decision not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=422,
            detail="This application only accepts approve or reject decisions",
        )

    saved_review = OfficerReview(
        application_id=review.application_id,
        officer_name=current_user["username"],
        decision=review.decision,
        remarks=review.remarks,
        reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(saved_review)
    if flag_pending:
        flag.review_status = review.decision

    if review.decision == "APPROVE":
        application.status = "APPROVED"
    elif review.decision == "REJECT":
        application.status = "REJECTED"
    else:
        application.status = "PENDING"

    add_audit(
        db,
        "OFFICER_REVIEW_SUBMITTED",
        "APPLICATION",
        review.application_id,
        {
            "actor_role": current_user["role"],
            "actor_id": current_user["username"],
            "decision": review.decision,
            "remarks": review.remarks,
            "flag_id": flag.flag_id if flag else None,
        },
    )
    db.commit()

    return {
        "message": "Officer review saved successfully",
        "review_id": saved_review.review_id,
        "application_id": review.application_id,
        "decision": review.decision,
        "review_status": flag.review_status if flag else application.status,
        "application_status": application.status,
    }


@app.get("/officer-reviews")
def get_officer_reviews(
    current_user: dict = Depends(require_officer),
    db: Session = Depends(get_db),
):
    reviews = (
        db.query(OfficerReview)
        .order_by(OfficerReview.review_id.desc())
        .all()
    )
    return [
        {
            "review_id": review.review_id,
            "application_id": review.application_id,
            "officer_name": review.officer_name,
            "decision": review.decision,
            "remarks": review.remarks,
            "created_at": review.reviewed_at,
        }
        for review in reviews
    ]


# --------------------------------------------------
# AUDIT LOGS
# --------------------------------------------------

@app.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.log_id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "log_id": log.log_id,
            "actor_role": log.actor_role,
            "actor_id": log.actor_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@app.get("/auth/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return current_user
