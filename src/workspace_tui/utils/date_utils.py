from datetime import datetime, timedelta

from dateutil import parser as dateutil_parser


def parse_date(date_string: str) -> datetime | None:
    if not date_string:
        return None
    try:
        return dateutil_parser.parse(date_string)
    except (ValueError, TypeError):
        return None


def format_relative(dt: datetime) -> str:
    """Format datetime as relative string (e.g., 'Oggi 14:32', 'Ieri', '3 giorni fa')."""
    now = datetime.now(tz=dt.tzinfo)
    today = now.date()
    dt_date = dt.date()
    time_str = dt.strftime("%H:%M")

    if dt_date == today:
        return f"Oggi {time_str}"
    if dt_date == today - timedelta(days=1):
        return f"Ieri {time_str}"

    diff_days = (today - dt_date).days
    if diff_days < 7:
        return f"{diff_days} giorni fa"
    if diff_days < 30:
        weeks = diff_days // 7
        label = "settimana" if weeks == 1 else "settimane"
        return f"{weeks} {label} fa"
    if diff_days < 365:
        months = diff_days // 30
        label = "mese" if months == 1 else "mesi"
        return f"{months} {label} fa"

    return dt.strftime("%d/%m/%Y")


def format_datetime_short(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def format_date_short(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def parse_jira_duration(duration_str: str) -> int | None:
    """Parse Jira duration string (e.g., '1h 30m', '2h', '45m', '1d') to seconds."""
    if not duration_str:
        return None

    duration_str = duration_str.strip().lower()
    total_seconds = 0
    found = False

    import re

    for match in re.finditer(r"(\d+)\s*(d|h|m)", duration_str):
        found = True
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "d":
            total_seconds += value * 8 * 3600
        elif unit == "h":
            total_seconds += value * 3600
        elif unit == "m":
            total_seconds += value * 60

    return total_seconds if found else None


def seconds_to_jira_duration(seconds: int) -> str:
    """Convert seconds to Jira duration string (e.g., '1h 30m')."""
    if seconds <= 0:
        return "0m"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"
