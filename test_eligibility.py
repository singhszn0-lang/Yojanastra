
from eligibility import check_eligibility


def test_eligible_applicant():
    result = check_eligibility({
        "scheme_id": 1,
        "annual_income": 150000,
        "age": 20,
        "residence": "Uttar Pradesh",
    })

    assert result["status"] == "ELIGIBLE"
    assert result["reasons"]


def test_income_exceeds_limit():
    result = check_eligibility({
        "scheme_id": 2,
        "annual_income": 300000,
        "age": 25,
        "residence": "Uttar Pradesh",
    })

    assert result["status"] == "NOT_ELIGIBLE"
    assert any("Income exceeds" in reason for reason in result["reasons"])


def test_missing_information():
    result = check_eligibility({
        "scheme_id": 1,
        "annual_income": None,
        "age": 20,
        "residence": "Uttar Pradesh",
    })

    assert result["status"] == "NEEDS_VERIFICATION"
    assert "annual_income" in result["missing_fields"]


def test_unknown_scheme():
    result = check_eligibility({
        "scheme_id": 99,
        "annual_income": 100000,
        "age": 20,
        "residence": "Uttar Pradesh",
    })

    assert result["status"] == "NEEDS_VERIFICATION"
