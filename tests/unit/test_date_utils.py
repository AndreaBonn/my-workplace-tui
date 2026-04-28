from datetime import UTC, datetime, timedelta

from workspace_tui.utils.date_utils import (
    format_date_short,
    format_datetime_short,
    format_day_header,
    format_relative,
    format_time,
    is_today,
    is_tomorrow,
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

    def test_one_week_ago(self):
        one_week_ago = datetime.now(tz=UTC) - timedelta(days=7)
        result = format_relative(one_week_ago)
        assert result == "1 settimana fa"

    def test_one_month_ago(self):
        one_month_ago = datetime.now(tz=UTC) - timedelta(days=35)
        result = format_relative(one_month_ago)
        assert result == "1 mese fa"

    def test_months_ago(self):
        two_months_ago = datetime.now(tz=UTC) - timedelta(days=60)
        result = format_relative(two_months_ago)
        assert "mesi fa" in result

    def test_old_date(self):
        old = datetime(2020, 1, 15, tzinfo=UTC)
        result = format_relative(old)
        assert result == "15/01/2020"


class TestFormatDayHeader:
    def test_formats_italian_day_header(self):
        dt = datetime(2026, 4, 28)  # Martedì
        result = format_day_header(dt)
        assert result == "Mar 28 Apr"

    def test_monday(self):
        dt = datetime(2026, 4, 27)  # Lunedì
        result = format_day_header(dt)
        assert result.startswith("Lun")

    def test_december(self):
        dt = datetime(2026, 12, 25)
        result = format_day_header(dt)
        assert "Dic" in result


class TestIsToday:
    def test_now_is_today(self):
        assert is_today(datetime.now(tz=UTC)) is True

    def test_yesterday_is_not_today(self):
        yesterday = datetime.now(tz=UTC) - timedelta(days=1)
        assert is_today(yesterday) is False


class TestIsTomorrow:
    def test_tomorrow_is_tomorrow(self):
        tomorrow = datetime.now(tz=UTC) + timedelta(days=1)
        assert is_tomorrow(tomorrow) is True

    def test_today_is_not_tomorrow(self):
        assert is_tomorrow(datetime.now(tz=UTC)) is False


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

    def test_negative(self):
        assert seconds_to_jira_duration(-100) == "0m"
