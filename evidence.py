
from typing import Any


def generate_evidence(
    applicant: dict[str, Any],
    eligibility_result: dict[str, Any],
) -> dict[str, Any]:
    """Generate explanations for the demo eligibility decision."""

    scheme_id = applicant.get("scheme_id")
    annual_income = applicant.get("annual_income")
    age = applicant.get("age")
    residence = applicant.get("residence")

    scheme_limits = {
        1: {"name": "Student Education Assistance", "min_age": 16, "max_income": 300000},
        2: {"name": "Household Welfare Support", "min_age": 18, "max_income": 200000},
        3: {"name": "Rural Livelihood Assistance", "min_age": 18, "max_income": 250000},
    }

    scheme = scheme_limits.get(scheme_id)

    if not scheme:
        return {
            "scheme_name": eligibility_result.get("scheme_name"),
            "status": eligibility_result.get("status", "NEEDS_VERIFICATION"),
            "evidence": [],
            "note": "Scheme could not be verified using the configured demo rules.",
        }

    evidence = []

    if annual_income is not None:
        passed = annual_income <= scheme["max_income"]
        evidence.append({
            "condition": "Annual income",
            "provided_value": annual_income,
            "required_condition": f"Income must be at most ₹{scheme['max_income']}",
            "result": "PASS" if passed else "FAIL",
            "explanation": (
                "Income is within the demo limit."
                if passed else "Income exceeds the demo limit."
            ),
        })

    if age is not None:
        passed = age >= scheme["min_age"]
        evidence.append({
            "condition": "Age",
            "provided_value": age,
            "required_condition": f"Age must be at least {scheme['min_age']}",
            "result": "PASS" if passed else "FAIL",
            "explanation": (
                "Age meets the demo condition."
                if passed else "Age is below the demo minimum."
            ),
        })

    if residence is not None:
        passed = residence.strip().lower() in {"uttar pradesh", "up"}
        evidence.append({
            "condition": "Residence",
            "provided_value": residence,
            "required_condition": "Must be Uttar Pradesh resident",
            "result": "PASS" if passed else "FAIL",
            "explanation": (
                "Residence meets the demo condition."
                if passed else "Residence does not meet the demo condition."
            ),
        })

    return {
        "scheme_name": scheme["name"],
        "status": eligibility_result.get("status", "NEEDS_VERIFICATION"),
        "evidence": evidence,
        "note": "These are synthetic demo rules, not official government eligibility criteria.",
    }
