import pytest

import main
from models import Citizen
from eligibility import check_csss_eligibility


class FakeSession:
    def __init__(self):
        self.records = []
        self.audit_records = []

    def add_all(self, records):
        self.records.extend(records)

    def add(self, record):
        self.audit_records.append(record)

    def flush(self):
        for index, record in enumerate(self.records, start=1):
            record.citizen_id = index

    def commit(self):
        pass


def test_register_family_assigns_shared_household_id(monkeypatch):
    audit_events = []
    monkeypatch.setattr(
        main,
        "add_audit",
        lambda _db, action, _entity_type, entity_id, details:
            audit_events.append((action, entity_id, details)),
    )
    db = FakeSession()
    family = main.FamilyCreate(
        household_id="FAM-123",
        members=[
            main.CitizenCreate(
                full_name="Shreya",
                age=19,
                state="West Bengal",
                category="General",
                annual_income=50000,
                phone=" 9876543210 ",
                aadhaar_last4="1234",
                family_annual_income=300000,
                class_12_percentile=85,
                regular_course=True,
                receives_other_scholarship=False,
            ),
            *[
                main.CitizenCreate(full_name=f"Member {index}", state="West Bengal")
                for index in range(2, 8)
            ],
        ],
    )

    result = main.register_family(family, db)

    assert result["household_id"] == "FAM-123"
    assert [member["citizen_id"] for member in result["members"]] == list(range(1, 8))
    assert all(isinstance(record, Citizen) for record in db.records)
    assert {record.household_id for record in db.records} == {"FAM-123"}
    assert db.records[0].phone == "9876543210"
    assert db.records[0].aadhaar_last4 == "1234"
    assert db.records[0].family_annual_income == 300000
    assert len(audit_events) == 7


def test_family_registration_requires_at_least_one_member_without_a_fixed_cap():
    member = {"full_name": "Shreya", "state": "West Bengal"}

    with pytest.raises(ValueError):
        main.FamilyCreate(household_id="FAM-123", members=[])

    family = main.FamilyCreate(household_id="FAM-123", members=[member] * 12)
    assert len(family.members) == 12


def test_family_member_name_and_state_cannot_be_blank():
    with pytest.raises(ValueError):
        main.CitizenCreate(full_name="  ", state="West Bengal")
    with pytest.raises(ValueError):
        main.CitizenCreate(full_name="Shreya", state=" ")

def test_aadhaar_field_accepts_only_last_four_digits_and_normalizes_phone():
    citizen = main.CitizenCreate(
        full_name="Shreya",
        state="West Bengal",
        phone=" 9876543210 ",
        aadhaar_last4="1234",
    )

    assert citizen.phone == "9876543210"
    assert citizen.aadhaar_last4 == "1234"
    with pytest.raises(ValueError):
        main.CitizenCreate(
            full_name="Shreya",
            state="West Bengal",
            aadhaar_last4="123456789012",
        )


def test_csss_preview_flags_missing_and_failed_rules():
    result = check_csss_eligibility({
        "family_annual_income": 500000,
        "class_12_percentile": None,
        "regular_course": False,
        "receives_other_scholarship": None,
    })

    assert result["status"] == "NOT_ELIGIBLE"
    assert result["failed_checks"] == [
        "Annual family income",
        "Regular degree course",
    ]
    assert result["missing_fields"] == [
        "Class XII board percentile",
        "Other scholarship",
    ]


def test_csss_preview_passes_when_all_demo_conditions_pass():
    result = check_csss_eligibility({
        "family_annual_income": 300000,
        "class_12_percentile": 85,
        "regular_course": True,
        "receives_other_scholarship": False,
    })

    assert result["status"] == "ELIGIBLE"
    assert all(flag["status"] == "PASS" for flag in result["flags"])
