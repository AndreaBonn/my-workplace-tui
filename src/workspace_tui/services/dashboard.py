from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable

PROVIDER_TIMEOUT = 15


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
    meetings_today: int = 0
    meetings_week: int = 0

    # Meta
    jira_available: bool = False
    errors: dict[str, str] = field(default_factory=dict)


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

        jql = (
            f"worklogDate >= '{week_start.strftime('%Y-%m-%d')}' "
            "AND worklogAuthor = currentUser() "
            "ORDER BY updated DESC"
        )
        issues, _ = self._jira.search_issues(jql=jql, max_results=50)

        logged_today = 0
        logged_week = 0
        estimated_week = 0
        worklogs: list[WorklogEntry] = []

        for issue in issues:
            estimated_week += issue.estimate_seconds

            try:
                issue_worklogs = self._jira.get_worklogs(issue.key)
            except Exception:
                continue

            for wl in issue_worklogs:
                wl_date = wl.started[:10] if wl.started else ""
                if not wl_date:
                    continue

                if wl_date >= week_start.strftime("%Y-%m-%d"):
                    logged_week += wl.time_spent_seconds
                    worklogs.append(
                        WorklogEntry(
                            date=wl_date,
                            seconds=wl.time_spent_seconds,
                            issue_key=issue.key,
                        )
                    )
                    if wl_date >= today_start.strftime("%Y-%m-%d"):
                        logged_today += wl.time_spent_seconds

        return {
            "logged_today": logged_today,
            "logged_week": logged_week,
            "estimated_week": estimated_week,
            "worklogs": worklogs,
        }

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
        week_end = today_start + timedelta(days=(7 - today_start.weekday()))

        today_events = self._calendar.list_events(
            time_min=today_start,
            time_max=today_end,
        )
        week_events = self._calendar.list_events(
            time_min=today_start,
            time_max=week_end,
        )

        return {
            "meetings_today": len(today_events),
            "meetings_week": len(week_events),
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
        metrics.meetings_today = data["meetings_today"]
        metrics.meetings_week = data["meetings_week"]
