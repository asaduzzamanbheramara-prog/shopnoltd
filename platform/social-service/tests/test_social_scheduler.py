from datetime import UTC, datetime, time

import pytest
from app.workers.social_scheduler import next_occurrence


def test_next_occurrence_uses_dhaka_local_wall_clock_and_converts_to_utc():
    now = datetime(2026, 11, 9, 2, 0, tzinfo=UTC)
    result = next_occurrence(now, time(9, 0), "Asia/Dhaka", [0, 1, 2, 3, 4, 5, 6])
    assert result == datetime(2026, 11, 9, 3, 0, tzinfo=UTC)


def test_next_occurrence_rolls_to_next_selected_weekday():
    now = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)
    result = next_occurrence(now, time(9, 0), "Asia/Dhaka", [1])
    assert result == datetime(2026, 11, 10, 3, 0, tzinfo=UTC)


def test_next_occurrence_rejects_unknown_timezone_and_empty_days():
    with pytest.raises(ValueError, match="unknown_timezone"):
        next_occurrence(datetime.now(UTC), time(9), "No/Such_Zone", [0])
    with pytest.raises(ValueError, match="invalid_days_of_week"):
        next_occurrence(datetime.now(UTC), time(9), "Asia/Dhaka", [])


def test_next_occurrence_during_second_fold_skips_the_past_first_fold():
    now = datetime(2026, 11, 1, 6, 15, tzinfo=UTC)
    result = next_occurrence(now, time(1, 30), "America/New_York", [6])
    assert result == datetime(2026, 11, 8, 6, 30, tzinfo=UTC)


def test_nonexistent_spring_forward_time_moves_to_first_valid_minute():
    now = datetime(2026, 3, 8, 6, 0, tzinfo=UTC)
    result = next_occurrence(now, time(2, 30), "America/New_York", [6])
    assert result == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)


def test_next_occurrence_rejects_duplicate_days_and_non_minute_times():
    with pytest.raises(ValueError, match="duplicate_days_of_week"):
        next_occurrence(datetime.now(UTC), time(9), "Asia/Dhaka", [0, 0])
    with pytest.raises(ValueError, match="invalid_local_time"):
        next_occurrence(datetime.now(UTC), time(9, 1, 1), "Asia/Dhaka", [0])
