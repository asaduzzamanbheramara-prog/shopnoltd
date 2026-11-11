from uuid import uuid4

import pytest
from app.api.social_automation import ScheduleCreate
from pydantic import ValidationError


def test_schedule_create_accepts_multiple_owned_connection_ids():
    first, second = uuid4(), uuid4()
    body = ScheduleCreate(
        connection_ids=[first, second],
        content_template="Approved content template",
        times=["09:00", "21:00"],
    )
    assert body.selected_connection_ids == [first, second]


def test_schedule_create_preserves_single_connection_compatibility():
    connection_id = uuid4()
    body = ScheduleCreate(connection_id=connection_id, content_template="Content")
    assert body.selected_connection_ids == [connection_id]


def test_schedule_create_rejects_duplicate_connection_ids():
    connection_id = uuid4()
    with pytest.raises(ValidationError):
        ScheduleCreate(
            connection_ids=[connection_id, connection_id],
            content_template="Content",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"content_template": "Content"},
        {"connection_id": str(uuid4()), "connection_ids": [str(uuid4())], "content_template": "Content"},
        {"connection_ids": [], "content_template": "Content"},
        {"connection_ids": [str(uuid4()), str(uuid4())], "content_template": "Content", "extra": "no"},
    ],
)
def test_schedule_create_rejects_ambiguous_or_invalid_account_selection(payload):
    with pytest.raises(ValidationError):
        ScheduleCreate.model_validate(payload)
