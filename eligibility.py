
from typing import Any


# Synthetic demo rules only — not official government scheme rules.
SCHEME_RULES = {
    1: {
        "name": "Student Education Assistance",
        "min_age": 16,
        "max_income": 300000,
    },
    2: {
        "name": "Household Welfare Support",
        "min_age": 18,
        "max_income": 200000,
    },
    3: {
        "name": "Rural Livelihood Assistance",
        "min_age": 18,
        "max_income": 250000,
    },
}


def check_eligibility(applicant: dict[str, Any]) -> dict[str, Any]:
    required_fields = ["scheme_id", "annual_income", "age", "residence"]

    missing_fields = [
        field for field in required_fields
        if applicant.get(field) is None
    ]

    if missing_fields:
        return {
            "status": "NEEDS_VERIFICATION",
            "scheme_name": None,
            "reasons": ["Required applicant information is missing."],
            "missing_fields": missing_fields,
        }

    scheme_id = applicant["scheme_id"]
    scheme = SCHEME_RULES.get(scheme_id)

    if scheme is None:
        return {
            "status": "NEEDS_VERIFICATION",
            "scheme_name": None,
            "reasons": [f"Unknown demo scheme ID: {scheme_id}."],
            "missing_fields": [],
        }

    reasons = []

    if applicant["age"] < scheme["min_age"]:
        reasons.append(
            f"Age is below the demo minimum of {scheme['min_age']}."
        )

    if applicant["annual_income"] > scheme["max_income"]:
        reasons.append(
            f"Income exceeds the demo limit of ₹{scheme['max_income']}."
        )

    residence = applicant["residence"].strip().lower()
    if residence not in {"uttar pradesh", "up"}:
        reasons.append(
            "Applicant does not meet the demo residence condition."
        )

    return {
        "status": "NOT_ELIGIBLE" if reasons else "ELIGIBLE",
        "scheme_name": scheme["name"],
        "reasons": reasons or [
            "All configured demo conditions are satisfied."
        ],
        "missing_fields": [],
    }
