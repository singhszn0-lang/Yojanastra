
from eligibility import check_eligibility
from evidence import generate_evidence


def test_income_evidence_fails_when_over_limit():
    applicant = {
        "scheme_id": 2,
        "annual_income": 300000,
        "age": 25,
        "residence": "Uttar Pradesh",
    }

    result = check_eligibility(applicant)
    evidence = generate_evidence(applicant, result)

    income_evidence = next(
        item for item in evidence["evidence"]
        if item["condition"] == "Annual income"
    )

    assert income_evidence["result"] == "FAIL"


def test_evidence_contains_demo_disclaimer():
    applicant = {
        "scheme_id": 1,
        "annual_income": 150000,
        "age": 20,
        "residence": "Uttar Pradesh",
    }

    result = check_eligibility(applicant)
    evidence = generate_evidence(applicant, result)

    assert "synthetic demo rules" in evidence["note"]
