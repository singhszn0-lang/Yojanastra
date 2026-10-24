from sqlalchemy import select

from database import SessionLocal
from models import Scheme


SCHEMES = [
    {
        "scheme_name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "state": "Central",
        "eligible_categories": (
            "Eligible landholding farmer families; exclusions and land-record "
            "verification apply."
        ),
        "benefit_description": (
            "Income support for eligible farmer families. Confirm current "
            "eligibility and payment details on the official portal: "
            "https://pmkisan.gov.in/"
        ),
    },
    {
        "scheme_name": "Pradhan Mantri Ujjwala Yojana (PMUY)",
        "state": "Central",
        "eligible_categories": (
            "Eligible women from deprived households that meet the current "
            "scheme conditions."
        ),
        "benefit_description": (
            "Supports access to LPG connections for eligible households. "
            "Check current eligibility and application conditions with the "
            "official portal: https://www.pmuy.gov.in/"
        ),
    },
    {
        "scheme_name": "PM Vishwakarma",
        "state": "Central",
        "eligible_categories": (
            "Artisans and craftspeople working in a notified traditional trade; "
            "scheme conditions apply."
        ),
        "benefit_description": (
            "Support can include skill training, toolkit assistance, and "
            "credit-related benefits for eligible artisans. Verify notified "
            "trades and current rules: https://pmvishwakarma.gov.in/"
        ),
    },
    {
        "scheme_name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB PM-JAY)",
        "state": "Central",
        "eligible_categories": (
            "Eligible families identified under applicable government "
            "beneficiary databases and state rules."
        ),
        "benefit_description": (
            "Health coverage for eligible families for covered hospital care. "
            "Check beneficiary status and current state-specific rules with "
            "the National Health Authority: https://nha.gov.in/PM-JAY"
        ),
    },
    {
        "scheme_name": "Pradhan Mantri Jan-Dhan Yojana (PMJDY)",
        "state": "Central",
        "eligible_categories": (
            "Individuals seeking access to basic banking services; account "
            "opening and benefit conditions apply."
        ),
        "benefit_description": (
            "Financial inclusion initiative providing access to basic banking "
            "services. Confirm current facilities and conditions with the "
            "Department of Financial Services: https://pmjdy.gov.in/"
        ),
    },
]


def seed_schemes():
    added = 0
    with SessionLocal() as db:
        for scheme_data in SCHEMES:
            existing = db.scalar(
                select(Scheme).where(
                    Scheme.scheme_name == scheme_data["scheme_name"]
                )
            )
            if existing:
                continue

            db.add(Scheme(**scheme_data, is_active=True))
            added += 1

        db.commit()

    print(f"Added {added} schemes; skipped {len(SCHEMES) - added} already present.")


if __name__ == "__main__":
    seed_schemes()
