from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable

PROVIDER_TIMEOUT = 30


@dataclass
class TasksByStatus:
    to_do: int = 0
    in_progress: int = 0
    done: int = 0


@dataclass
class TasksByPriority:
    highest: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    lowest: int = 0


@dataclass
class WorklogEntry:
    date: str
    seconds: int
    issue_key: str


@dataclass
class DashboardMetrics:
    # Jira workload
    open_tasks: int = 0
    tasks_by_status: TasksByStatus = field(default_factory=TasksByStatus)
    tasks_by_priority: TasksByPriority = field(default_factory=TasksByPriority)

    # Time tracking
    logged_today_seconds: int = 0
    logged_week_seconds: int = 0
    estimated_week_seconds: int = 0
    weekly_worklogs: list[WorklogEntry] = field(default_factory=list)

    # Quick stats
    gmail_unread: int = 0
    meetings_today_remaining: int = 0
    meetings_today_total: int = 0
    meetings_today_done_seconds: int = 0
    meetings_today_total_seconds: int = 0
    meetings_week_remaining: int = 0
    meetings_week_total: int = 0
    meetings_week_done_seconds: int = 0
    meetings_week_total_seconds: int = 0

    # Meta
    jira_available: bool = False
    errors: dict[str, str] = field(default_factory=dict)


MEETING_LINK_PATTERNS = (
    "meet.google.com",
    "teams.microsoft.com",
    "zoom.us",
    "webex.com",
    "gotomeeting.com",
    "whereby.com",
    "bluejeans.com",
    "chime.aws",
)

PRIORITY_MAP = {
    "Highest": "highest",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Lowest": "lowest",
}

STATUS_CATEGORY_MAP = {
    "To Do": "to_do",
    "In Progress": "in_progress",
    "Done": "done",
}


def _parse_event_time(iso_str: str) -> datetime | None:
    """Parse an ISO datetime string to a timezone-aware datetime."""
    if not iso_str or len(iso_str) <= 10:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        return None


def _event_duration_seconds(event) -> int:
    """Return event duration in seconds, 0 if unparseable."""
    start = _parse_event_time(event.start)
    end = _parse_event_time(event.end)
    if not start or not end:
        return 0
    delta = (end - start).total_seconds()
    return int(max(delta, 0))


def _meeting_duration_seconds(
    meetings: list,
    now_iso: str,
) -> tuple[int, int]:
    """Return (done_seconds, total_seconds) for a list of meetings."""
    done = 0
    total = 0
    for event in meetings:
        duration = _event_duration_seconds(event)
        total += duration
        if event.end <= now_iso:
            done += duration
    return done, total


def _is_meeting(event) -> bool:
    """Return True if the event contains a video call link."""
    searchable = f"{event.meet_link} {event.location} {event.description}".lower()
    return any(pattern in searchable for pattern in MEETING_LINK_PATTERNS)


class DashboardService:
    """Aggregates metrics from Jira, Gmail and Calendar for the dashboard."""

    def __init__(
        self,
        jira_service=None,
        gmail_service=None,
        calendar_service=None,
        jira_account_id: str = "",
    ) -> None:
        self._jira = jira_service
        self._gmail = gmail_service
        self._calendar = calendar_service
        self._jira_account_id = jira_account_id

    def collect(self) -> DashboardMetrics:
        """Collect all metrics in parallel.

        Returns
        -------
        DashboardMetrics
            Aggregated metrics. Individual provider failures are captured
            in the errors dict without blocking other providers.
        """
        metrics = DashboardMetrics(jira_available=self._jira is not None)
        collectors: dict[str, Callable[[], dict]] = {}

        if self._jira:
            collectors["jira_tasks"] = self._collect_jira_tasks
            collectors["jira_worklogs"] = self._collect_jira_worklogs
        if self._gmail:
            collectors["gmail"] = self._collect_gmail
        if self._calendar:
            collectors["calendar"] = self._collect_calendar

        if not collectors:
            return metrics

        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=len(collectors)) as pool:
            future_to_name = {pool.submit(fn): name for name, fn in collectors.items()}
            try:
                for future in as_completed(future_to_name, timeout=PROVIDER_TIMEOUT):
                    name = future_to_name[future]
                    try:
                        results[name] = future.result()
                    except Exception as exc:
                        logger.warning("Dashboard collector {} failed: {}", name, exc)
                        metrics.errors[name] = str(exc)
            except TimeoutError:
                for future, name in future_to_name.items():
                    if not future.done():
                        future.cancel()
                        metrics.errors[name] = "Timeout"

        self._merge_jira_tasks(metrics, results.get("jira_tasks", {}))
        self._merge_jira_worklogs(metrics, results.get("jira_worklogs", {}))
        self._merge_gmail(metrics, results.get("gmail", {}))
        self._merge_calendar(metrics, results.get("calendar", {}))

        return metrics

    def _collect_jira_tasks(self) -> dict:
        jql = "assignee = currentUser() AND status != Done ORDER BY priority DESC"
        issues, total = self._jira.search_issues(jql=jql, max_results=100)

        by_status = TasksByStatus()
        by_priority = TasksByPriority()

        for issue in issues:
            cat = STATUS_CATEGORY_MAP.get(issue.status_category, "to_do")
            current = getattr(by_status, cat)
            setattr(by_status, cat, current + 1)

            pri = PRIORITY_MAP.get(issue.priority, "medium")
            current = getattr(by_priority, pri)
            setattr(by_priority, pri, current + 1)

        return {
            "open_tasks": total,
            "by_status": by_status,
            "by_priority": by_priority,
        }

    def _collect_jira_worklogs(self) -> dict:
        now = datetime.now(tz=UTC)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        week_str = week_start.strftime("%Y-%m-%d")
        today_str = today_start.strftime("%Y-%m-%d")
        since_ms = int(week_start.timestamp() * 1000)

        all_worklogs = self._jira.get_worklogs_since(since_ms)

        logged_today = 0
        logged_week = 0
        worklogs: list[WorklogEntry] = []

        for wl in all_worklogs:
            if not self._is_current_user_worklog(wl):
                continue

            wl_date = wl.started[:10] if wl.started else ""
            if not wl_date or wl_date < week_str:
                continue

            logged_week += wl.time_spent_seconds
            worklogs.append(
                WorklogEntry(
                    date=wl_date,
                    seconds=wl.time_spent_seconds,
                    issue_key="",
                )
            )
            if wl_date >= today_str:
                logged_today += wl.time_spent_seconds

        return {
            "logged_today": logged_today,
            "logged_week": logged_week,
            "estimated_week": 0,
            "worklogs": worklogs,
        }

    def _is_current_user_worklog(self, worklog) -> bool:
        """Check if a worklog belongs to the current user."""
        if not self._jira_account_id:
            return True
        return worklog.author_account_id == self._jira_account_id

    def _collect_gmail(self) -> dict:
        labels = self._gmail.list_labels()
        unread = 0
        for label in labels:
            if label.label_id == "INBOX":
                unread = label.unread_count
                break
        return {"unread": unread}

    def _collect_calendar(self) -> dict:
        now = datetime.now(tz=UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_start = today_start - timedelta(days=today_start.weekday())
        week_end = week_start + timedelta(days=7)

        today_events = self._calendar.list_events(
            time_min=today_start,
            time_max=today_end,
        )
        week_events = self._calendar.list_events(
            time_min=week_start,
            time_max=week_end,
        )

        today_meetings = [e for e in today_events if _is_meeting(e)]
        week_meetings = [e for e in week_events if _is_meeting(e)]
        now_iso = now.isoformat()

        today_done, today_total = _meeting_duration_seconds(
            today_meetings,
            now_iso,
        )
        week_done, week_total = _meeting_duration_seconds(
            week_meetings,
            now_iso,
        )

        return {
            "meetings_today_remaining": sum(1 for e in today_meetings if e.start > now_iso),
            "meetings_today_total": len(today_meetings),
            "meetings_today_done_seconds": today_done,
            "meetings_today_total_seconds": today_total,
            "meetings_week_remaining": sum(1 for e in week_meetings if e.start > now_iso),
            "meetings_week_total": len(week_meetings),
            "meetings_week_done_seconds": week_done,
            "meetings_week_total_seconds": week_total,
        }

    def _merge_jira_tasks(self, metrics: DashboardMetrics, data: dict) -> None:
        if not data:
            return
        metrics.open_tasks = data["open_tasks"]
        metrics.tasks_by_status = data["by_status"]
        metrics.tasks_by_priority = data["by_priority"]

    def _merge_jira_worklogs(self, metrics: DashboardMetrics, data: dict) -> None:
        if not data:
            return
        metrics.logged_today_seconds = data["logged_today"]
        metrics.logged_week_seconds = data["logged_week"]
        metrics.estimated_week_seconds = data["estimated_week"]
        metrics.weekly_worklogs = data["worklogs"]

    def _merge_gmail(self, metrics: DashboardMetrics, data: dict) -> None:
        if not data:
            return
        metrics.gmail_unread = data["unread"]

    def _merge_calendar(self, metrics: DashboardMetrics, data: dict) -> None:
        if not data:
            return
        metrics.meetings_today_remaining = data["meetings_today_remaining"]
        metrics.meetings_today_total = data["meetings_today_total"]
        metrics.meetings_today_done_seconds = data["meetings_today_done_seconds"]
        metrics.meetings_today_total_seconds = data["meetings_today_total_seconds"]
        metrics.meetings_week_remaining = data["meetings_week_remaining"]
        metrics.meetings_week_total = data["meetings_week_total"]
        metrics.meetings_week_done_seconds = data["meetings_week_done_seconds"]
        metrics.meetings_week_total_seconds = data["meetings_week_total_seconds"]
