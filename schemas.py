
from pydantic import BaseModel, Field
from typing import Optional, Literal


class ApplicationCreate(BaseModel):
    citizen_id: int = Field(gt=0)
    scheme_id: int = Field(gt=0)


class ApplicationResponse(BaseModel):
    message: str
    application_id: int
    status: str
    possible_duplicate: bool
    review_status: Optional[str] = None


class OfficerReviewCreate(BaseModel):
    application_id: int = Field(gt=0)
    officer_name: str = Field(min_length=2, max_length=100)
    decision: Literal[
        "NEEDS_INFO",
        "NOT_DUPLICATE",
        "CONFIRMED_DUPLICATE"
    ]
    remarks: str = Field(min_length=3, max_length=2000)


class OfficerReviewResponse(BaseModel):
    message: str
    review_id: int
    application_id: int
    decision: str
    review_status: str
