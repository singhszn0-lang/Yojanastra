import os
import jwt

from datetime import timedelta
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from eligibility import check_eligibility
from datetime import datetime, timezone
from typing import Literal, Optional
from evidence import generate_evidence
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import timedelta
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


app = FastAPI(
    title="Yojanastra API",
    description="Public Benefit Application Verification System",
    version="1.0.0",
)

from datetime import datetime, timezone
import jwt
import os
from pwdlib import PasswordHash

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

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is missing"
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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

schemes = [
    {
        "scheme_id": 1,
        "name": "Student Education Assistance",
        "category": "Education",
        "description": "Demo scheme for education assistance.",
        "is_active": True,
    },
    {
        "scheme_id": 2,
        "name": "Household Welfare Support",
        "category": "Welfare",
        "description": "Demo scheme for household welfare.",
        "is_active": True,
    },
    {
        "scheme_id": 3,
        "name": "Rural Livelihood Assistance",
        "category": "Livelihood",
        "description": "Demo scheme for livelihood assistance.",
        "is_active": True,
    },
]

applications = []
duplicate_flags = []
officer_reviews = []
audit_logs = []

next_application_id = 1
next_flag_id = 1
next_review_id = 1
next_log_id = 1


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1, max_length=100)
    scheme_id: int = Field(gt=0)
    applicant_name: str = Field(min_length=1, max_length=150)
    annual_income: Optional[float] = Field(default=None, ge=0)
    household_id: Optional[str] = Field(default=None, max_length=100)

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
@app.get("/")
def home():
    return {
        "project": "Yojanastra",
        "message": "Backend is running!",
        "status": "success",
        "mode": "mock_data",
        "database_connected": False,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "not_connected_yet",
    }


# --------------------------------------------------
# SCHEMES
# --------------------------------------------------

@app.get("/schemes")
def get_schemes():
    return schemes


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
def dashboard_stats():
    return {
        "total_applications": len(applications),
        "pending_applications": sum(
            a["status"] == "PENDING" for a in applications
        ),
        "total_duplicate_flags": len(duplicate_flags),
        "pending_reviews": sum(
            f["review_status"] == "PENDING" for f in duplicate_flags
        ),
        "completed_reviews": len(officer_reviews),
        "total_schemes": len(schemes),
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

# --------------------------------------------------
# OFFICER REVIEW
# --------------------------------------------------

def require_officer(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "OFFICER":
        raise HTTPException(
            status_code=403,
            detail="Officer access required",
        )
    return current_user


@app.post("/officer-reviews", status_code=201)
def create_officer_review(
    review: OfficerReviewCreate,
    current_user: dict = Depends(require_officer),
):
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
        "officer_name": current_user["username"],
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
            "actor_role": current_user["role"],
            "actor_id": current_user["username"],
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
def get_officer_reviews(
    current_user: dict = Depends(require_officer),
):
    return list(reversed(officer_reviews))

# --------------------------------------------------
# AUDIT LOGS
# --------------------------------------------------

@app.get("/audit-logs")
def get_audit_logs():
    return list(reversed(audit_logs[-100:]))
@app.get("/auth/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
):
    return current_user
