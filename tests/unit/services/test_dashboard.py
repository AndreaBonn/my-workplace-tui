from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from workspace_tui.services.dashboard import (
    DashboardMetrics,
    DashboardService,
)
from workspace_tui.services.gmail import GmailLabel
from workspace_tui.services.jira import JiraIssue, JiraWorklog


def _make_issue(
    key: str = "PROJ-1",
    status_category: str = "In Progress",
    priority: str = "Medium",
    logged: int = 3600,
    estimated: int = 7200,
) -> JiraIssue:
    return JiraIssue(
        key=key,
        summary="Task",
        status="In Progress",
        status_category=status_category,
        issue_type="Task",
        priority=priority,
        assignee="Alice",
        reporter="Bob",
        sprint="Sprint 1",
        description_text="",
        created="2026-04-20",
        updated="2026-04-28",
        estimate_seconds=estimated,
        logged_seconds=logged,
    )


def _make_worklog(
    seconds: int = 3600,
    started: str | None = None,
) -> JiraWorklog:
    if started is None:
        started = datetime.now(tz=UTC).strftime("%Y-%m-%dT10:00:00.000+0000")
    return JiraWorklog(
        worklog_id="wl1",
        author="Alice",
        time_spent="1h",
        time_spent_seconds=seconds,
        started=started,
        comment="",
    )


def _make_gmail_label(label_id: str = "INBOX", unread: int = 5) -> GmailLabel:
    return GmailLabel(
        label_id=label_id,
        name="In arrivo",
        label_type="system",
        unread_count=unread,
    )


@pytest.fixture
def mock_jira():
    service = MagicMock()
    service.search_issues.return_value = (
        [_make_issue(), _make_issue(key="PROJ-2", priority="High", status_category="To Do")],
        2,
    )
    service.get_worklogs.return_value = [_make_worklog()]
    return service


@pytest.fixture
def mock_gmail():
    service = MagicMock()
    service.list_labels.return_value = [_make_gmail_label()]
    return service


@pytest.fixture
def mock_calendar():
    service = MagicMock()
    service.list_events.return_value = [MagicMock(), MagicMock(), MagicMock()]
    return service


class TestDashboardHappyPath:
    def test_collects_all_metrics(self, mock_jira, mock_gmail, mock_calendar):
        svc = DashboardService(
            jira_service=mock_jira,
            gmail_service=mock_gmail,
            calendar_service=mock_calendar,
        )
        metrics = svc.collect()

        assert metrics.jira_available is True
        assert metrics.open_tasks == 2
        assert metrics.gmail_unread == 5
        assert metrics.meetings_today >= 0
        assert not metrics.errors

    def test_tasks_by_status_breakdown(self, mock_jira):
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert metrics.tasks_by_status.in_progress == 1
        assert metrics.tasks_by_status.to_do == 1

    def test_tasks_by_priority_breakdown(self, mock_jira):
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert metrics.tasks_by_priority.medium == 1
        assert metrics.tasks_by_priority.high == 1

    def test_worklog_aggregation(self, mock_jira):
        today = datetime.now(tz=UTC).strftime("%Y-%m-%dT10:00:00.000+0000")
        mock_jira.get_worklogs.return_value = [
            _make_worklog(seconds=3600, started=today),
            _make_worklog(seconds=1800, started=today),
        ]
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert metrics.logged_today_seconds >= 5400
        assert metrics.logged_week_seconds >= 5400


class TestDashboardNoJira:
    def test_no_jira_returns_zero_tasks(self, mock_gmail, mock_calendar):
        svc = DashboardService(
            gmail_service=mock_gmail,
            calendar_service=mock_calendar,
        )
        metrics = svc.collect()

        assert metrics.jira_available is False
        assert metrics.open_tasks == 0
        assert metrics.gmail_unread == 5

    def test_no_services_returns_defaults(self):
        svc = DashboardService()
        metrics = svc.collect()

        assert metrics == DashboardMetrics()


class TestDashboardProviderFailures:
    def test_jira_failure_returns_partial(self, mock_gmail, mock_calendar):
        failing_jira = MagicMock()
        failing_jira.search_issues.side_effect = RuntimeError("Jira offline")

        svc = DashboardService(
            jira_service=failing_jira,
            gmail_service=mock_gmail,
            calendar_service=mock_calendar,
        )
        metrics = svc.collect()

        assert metrics.gmail_unread == 5
        assert "jira_tasks" in metrics.errors

    def test_gmail_failure_preserves_jira(self, mock_jira):
        failing_gmail = MagicMock()
        failing_gmail.list_labels.side_effect = RuntimeError("Gmail down")

        svc = DashboardService(
            jira_service=mock_jira,
            gmail_service=failing_gmail,
        )
        metrics = svc.collect()

        assert metrics.open_tasks == 2
        assert "gmail" in metrics.errors

    def test_all_fail_returns_all_errors(self):
        failing_jira = MagicMock()
        failing_jira.search_issues.side_effect = RuntimeError("down")
        failing_gmail = MagicMock()
        failing_gmail.list_labels.side_effect = RuntimeError("down")
        failing_calendar = MagicMock()
        failing_calendar.list_events.side_effect = RuntimeError("down")

        svc = DashboardService(
            jira_service=failing_jira,
            gmail_service=failing_gmail,
            calendar_service=failing_calendar,
        )
        metrics = svc.collect()

        assert len(metrics.errors) >= 3


class TestDashboardEdgeCases:
    def test_zero_worklogs(self, mock_jira):
        mock_jira.get_worklogs.return_value = []
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert metrics.logged_today_seconds == 0
        assert metrics.logged_week_seconds == 0
        assert metrics.weekly_worklogs == []

    def test_old_worklogs_excluded(self, mock_jira):
        old_date = (datetime.now(tz=UTC) - timedelta(days=14)).strftime(
            "%Y-%m-%dT10:00:00.000+0000"
        )
        mock_jira.get_worklogs.return_value = [_make_worklog(started=old_date)]
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert metrics.logged_week_seconds == 0

    def test_gmail_no_inbox_label(self, mock_gmail):
        mock_gmail.list_labels.return_value = [
            GmailLabel(label_id="SENT", name="Inviati", label_type="system", unread_count=0)
        ]
        svc = DashboardService(gmail_service=mock_gmail)
        metrics = svc.collect()

        assert metrics.gmail_unread == 0
