
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

CSSS_RULES_NOTE = (
    "Preliminary demo screening only. This does not verify board-specific "
    "cut-offs, course exclusions, documents, or current rules. Confirm "
    "eligibility on the National Scholarship Portal before applying."
)


def check_csss_eligibility(applicant: dict[str, Any]) -> dict[str, Any]:
    checks = [
        (
            "Class XII board percentile",
            applicant.get("class_12_percentile"),
            lambda value: value >= 80,
            "Must be in the top 20 percentile of the relevant board.",
        ),
        (
            "Annual family income",
            applicant.get("family_annual_income"),
            lambda value: value <= 450000,
            "Must not exceed ₹4,50,000 per year.",
        ),
        (
            "Regular degree course",
            applicant.get("regular_course"),
            lambda value: value is True,
            "The student must be pursuing a regular degree course.",
        ),
        (
            "Other scholarship",
            applicant.get("receives_other_scholarship"),
            lambda value: value is False,
            "The student must not receive another scholarship.",
        ),
    ]

    flags = []
    missing_fields = []
    failed_checks = []

    for label, value, passes, requirement in checks:
        if value is None:
            missing_fields.append(label)
            flags.append({
                "rule": label,
                "status": "NEEDS_VERIFICATION",
                "requirement": requirement,
            })
        elif passes(value):
            flags.append({
                "rule": label,
                "status": "PASS",
                "requirement": requirement,
            })
        else:
            failed_checks.append(label)
            flags.append({
                "rule": label,
                "status": "FAIL",
                "requirement": requirement,
            })

    status = (
        "NOT_ELIGIBLE" if failed_checks else
        "NEEDS_VERIFICATION" if missing_fields else
        "ELIGIBLE"
    )
    return {
        "scheme": "PM-USP Central Sector Scheme of Scholarship (CSSS)",
        "status": status,
        "flags": flags,
        "missing_fields": missing_fields,
        "failed_checks": failed_checks,
        "note": CSSS_RULES_NOTE,
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
