from datetime import UTC, datetime, timedelta

from workspace_tui.utils.date_utils import (
    format_date_short,
    format_datetime_short,
    format_relative,
    format_time,
    parse_date,
    parse_jira_duration,
    seconds_to_jira_duration,
)


class TestParseDate:
    def test_iso_format(self):
        result = parse_date("2026-04-28T14:30:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4

    def test_empty_string(self):
        assert parse_date("") is None

    def test_invalid_string(self):
        assert parse_date("not a date") is None


class TestFormatRelative:
    def test_today(self):
        now = datetime.now(tz=UTC)
        result = format_relative(now)
        assert result.startswith("Oggi")

    def test_yesterday(self):
        yesterday = datetime.now(tz=UTC) - timedelta(days=1)
        result = format_relative(yesterday)
        assert result.startswith("Ieri")

    def test_days_ago(self):
        three_days_ago = datetime.now(tz=UTC) - timedelta(days=3)
        result = format_relative(three_days_ago)
        assert result == "3 giorni fa"

    def test_weeks_ago(self):
        two_weeks_ago = datetime.now(tz=UTC) - timedelta(days=14)
        result = format_relative(two_weeks_ago)
        assert result == "2 settimane fa"

    def test_months_ago(self):
        two_months_ago = datetime.now(tz=UTC) - timedelta(days=60)
        result = format_relative(two_months_ago)
        assert "mesi fa" in result

    def test_old_date(self):
        old = datetime(2020, 1, 15, tzinfo=UTC)
        result = format_relative(old)
        assert result == "15/01/2020"


class TestFormatDatetimeShort:
    def test_format(self):
        dt = datetime(2026, 4, 28, 14, 30)
        assert format_datetime_short(dt) == "28/04/2026 14:30"


class TestFormatDateShort:
    def test_format(self):
        dt = datetime(2026, 4, 28)
        assert format_date_short(dt) == "28/04/2026"


class TestFormatTime:
    def test_format(self):
        dt = datetime(2026, 4, 28, 14, 30)
        assert format_time(dt) == "14:30"


class TestParseJiraDuration:
    def test_hours_and_minutes(self):
        assert parse_jira_duration("1h 30m") == 5400

    def test_hours_only(self):
        assert parse_jira_duration("2h") == 7200

    def test_minutes_only(self):
        assert parse_jira_duration("45m") == 2700

    def test_days(self):
        assert parse_jira_duration("1d") == 28800

    def test_empty(self):
        assert parse_jira_duration("") is None

    def test_invalid(self):
        assert parse_jira_duration("abc") is None

    def test_mixed(self):
        assert parse_jira_duration("1d 2h 30m") == 28800 + 7200 + 1800


class TestSecondsToJiraDuration:
    def test_hours_and_minutes(self):
        assert seconds_to_jira_duration(5400) == "1h 30m"

    def test_hours_only(self):
        assert seconds_to_jira_duration(7200) == "2h"

    def test_minutes_only(self):
        assert seconds_to_jira_duration(2700) == "45m"

    def test_zero(self):
        assert seconds_to_jira_duration(0) == "0m"
