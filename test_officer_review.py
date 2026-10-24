import pytest

import main
from models import Application, DuplicateFlag, OfficerReview


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, application, flag=None):
        self.application = application
        self.flag = flag
        self.added = []

    def query(self, model):
        if model is Application:
            return FakeQuery(self.application)
        if model is DuplicateFlag:
            return FakeQuery(self.flag)
        raise AssertionError(f"Unexpected model queried: {model}")

    def add(self, record):
        self.added.append(record)

    def commit(self):
        pass


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("APPROVE", "APPROVED"), ("REJECT", "REJECTED")],
)
def test_officer_can_decide_unflagged_pending_application(
    decision, expected_status
):
    application = Application(application_id=1, status="PENDING")
    db = FakeSession(application)
    review = main.OfficerReviewCreate(
        application_id=1,
        officer_name="Officer",
        decision=decision,
        remarks="Application reviewed.",
    )

    result = main.create_officer_review(
        review,
        current_user={"username": "officer", "role": "OFFICER"},
        db=db,
    )

    assert application.status == expected_status
    assert result["application_status"] == expected_status
    assert any(isinstance(record, OfficerReview) for record in db.added)


def test_unflagged_application_rejects_duplicate_only_decisions():
    application = Application(application_id=1, status="PENDING")
    db = FakeSession(application)
    review = main.OfficerReviewCreate(
        application_id=1,
        officer_name="Officer",
        decision="NEEDS_INFO",
        remarks="More information is required.",
    )

    with pytest.raises(main.HTTPException) as error:
        main.create_officer_review(
            review,
            current_user={"username": "officer", "role": "OFFICER"},
            db=db,
        )

    assert error.value.status_code == 422


def test_pending_application_can_be_decided_after_duplicate_flag_is_resolved():
    application = Application(application_id=1, status="PENDING")
    flag = DuplicateFlag(
        application_id=1,
        review_status="NOT_DUPLICATE",
    )
    db = FakeSession(application, flag)
    review = main.OfficerReviewCreate(
        application_id=1,
        officer_name="Officer",
        decision="APPROVE",
        remarks="Duplicate check passed; application is eligible.",
    )

    result = main.create_officer_review(
        review,
        current_user={"username": "officer", "role": "OFFICER"},
        db=db,
    )

    assert application.status == "APPROVED"
    assert flag.review_status == "NOT_DUPLICATE"
    assert result["application_status"] == "APPROVED"
