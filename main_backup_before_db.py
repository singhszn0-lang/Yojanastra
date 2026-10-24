
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Depends
from sqlalchemy.orm import Session

import models
from database import get_db

from database import get_db
from models import (
    Citizen,
    Scheme,
    Application,
    DuplicateFlag,
    OfficerReview,
    AuditLog,
)


app = FastAPI(
    title="Yojanastra API",
    description="Public Benefit Application Verification System",
    version="1.0.0",
)

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
    applicant_name: str = Field(min_length=1, max_length=150)
    annual_income: Optional[float] = Field(default=None, ge=0)
    household_id: Optional[str] = Field(default=None, max_length=100)


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


def add_audit(action, entity_type, entity_id, details):
    global next_log_id

    audit_logs.append({
        "log_id": next_log_id,
        "actor_role": details.get("actor_role", "SYSTEM"),
        "actor_id": details.get("actor_id", "system"),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "created_at": now_utc(),
    })

    next_log_id += 1


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------

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

@app.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: int, db: Session = Depends(get_db)):
    scheme = db.query(Scheme).filter(
        Scheme.scheme_id == scheme_id
    ).first()

    if not scheme:
        raise HTTPException(404, "Scheme not found")

    return scheme

@app.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: int):
    for scheme in schemes:
        if scheme["scheme_id"] == scheme_id:
            return scheme

    raise HTTPException(status_code=404, detail="Scheme not found")


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
def create_application(application: ApplicationCreate):
    global next_application_id, next_flag_id

    scheme = next(
        (
            s for s in schemes
            if s["scheme_id"] == application.scheme_id
            and s["is_active"]
        ),
        None,
    )

    if not scheme:
        raise HTTPException(
            status_code=404,
            detail="Active scheme not found",
        )

    # Possible repeat application: same citizen + same scheme.
    # This flags the case; it does NOT automatically reject it.
    previous = next(
        (
            a for a in applications
            if a["citizen_id"] == application.citizen_id
            and a["scheme_id"] == application.scheme_id
        ),
        None,
    )

    application_id = next_application_id
    next_application_id += 1

    record = {
        "application_id": application_id,
        "citizen_id": application.citizen_id,
        "scheme_id": application.scheme_id,
        "scheme_name": scheme["name"],
        "applicant_name": application.applicant_name,
        "annual_income": application.annual_income,
        "household_id": application.household_id,
        "status": "PENDING",
        "possible_duplicate": previous is not None,
        "created_at": now_utc(),
    }

    applications.append(record)

    flag_id = None

    if previous:
        flag_id = next_flag_id
        next_flag_id += 1

        duplicate_flags.append({
            "flag_id": flag_id,
            "application_id": application_id,
            "matched_application_id": previous["application_id"],
            "rule_code": "R1",
            "reason": (
                "Same citizen and scheme found in an earlier application. "
                "Human review required before any decision."
            ),
            "review_status": "PENDING",
            "created_at": now_utc(),
        })

        add_audit(
            "POSSIBLE_DUPLICATE_FLAGGED",
            "APPLICATION",
            application_id,
            {
                "actor_role": "SYSTEM",
                "actor_id": "duplicate_checker",
                "flag_id": flag_id,
                "matched_application_id": previous["application_id"],
            },
        )

    add_audit(
        "APPLICATION_SUBMITTED",
        "APPLICATION",
        application_id,
        {
            "actor_role": "SYSTEM",
            "actor_id": application.citizen_id,
            "scheme_id": application.scheme_id,
        },
    )

    return {
        "message": "Application submitted successfully",
        "application_id": application_id,
        "status": "PENDING",
        "possible_duplicate": previous is not None,
        "flag_id": flag_id,
        "review_status": "PENDING" if previous else None,
    }


# --------------------------------------------------
# LIST AND VIEW APPLICATIONS
# --------------------------------------------------

@app.get("/applications")
def get_applications(
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    result = applications

    if status:
        result = [
            a for a in result
            if a["status"].upper() == status.upper()
        ]

    if search:
        query = search.casefold()
        result = [
            a for a in result
            if query in a["applicant_name"].casefold()
            or query in a["citizen_id"].casefold()
            or query in str(a["application_id"])
        ]

    return list(reversed(result))


@app.get("/applications/{application_id}")
def get_application(application_id: int):
    for application in applications:
        if application["application_id"] == application_id:
            return application

    raise HTTPException(
        status_code=404,
        detail="Application not found",
    )


# --------------------------------------------------
# DUPLICATE REVIEW QUEUE
# --------------------------------------------------

@app.get("/duplicate-flags")
def get_duplicate_flags(review_status: Optional[str] = "PENDING"):
    result = duplicate_flags

    if review_status:
        result = [
            f for f in result
            if f["review_status"].upper() == review_status.upper()
        ]

    return list(reversed(result))


# --------------------------------------------------
# OFFICER REVIEW
# --------------------------------------------------

@app.post("/officer-reviews", status_code=201)
def create_officer_review(review: OfficerReviewCreate):
    global next_review_id

    flag = next(
        (
            f for f in reversed(duplicate_flags)
            if f["application_id"] == review.application_id
        ),
        None,
    )

    if not flag:
        raise HTTPException(
            status_code=404,
            detail="No duplicate flag found for this application",
        )

    if flag["review_status"] not in ("PENDING", "NEEDS_INFO"):
        raise HTTPException(
            status_code=409,
            detail="This flag has already received a final review",
        )

    review_id = next_review_id
    next_review_id += 1

    saved_review = {
        "review_id": review_id,
        "application_id": review.application_id,
        "officer_name": review.officer_name,
        "decision": review.decision,
        "remarks": review.remarks,
        "created_at": now_utc(),
    }

    officer_reviews.append(saved_review)

    flag["review_status"] = review.decision

    application = next(
        (
            a for a in applications
            if a["application_id"] == review.application_id
        ),
        None,
    )

    # Update application status only for explicit final decisions.
    if application:
        if review.decision == "APPROVE":
            application["status"] = "APPROVED"
        elif review.decision == "REJECT":
            application["status"] = "REJECTED"
        elif review.decision == "CONFIRMED_DUPLICATE":
            application["status"] = "PENDING"
        elif review.decision == "NOT_DUPLICATE":
            application["possible_duplicate"] = False
            application["status"] = "PENDING"

    add_audit(
        "OFFICER_REVIEW_SUBMITTED",
        "APPLICATION",
        review.application_id,
        {
            "actor_role": "OFFICER",
            "actor_id": review.officer_name,
            "decision": review.decision,
            "remarks": review.remarks,
            "flag_id": flag["flag_id"],
        },
    )

    return {
        "message": "Officer review saved successfully",
        "review_id": review_id,
        "application_id": review.application_id,
        "decision": review.decision,
        "review_status": flag["review_status"],
    }


@app.get("/officer-reviews")
def get_officer_reviews():
    return list(reversed(officer_reviews))


# --------------------------------------------------
# AUDIT LOGS
# --------------------------------------------------

@app.get("/audit-logs")
def get_audit_logs():
    return list(reversed(audit_logs[-100:]))
