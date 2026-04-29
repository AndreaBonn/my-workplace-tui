from unittest.mock import MagicMock

import pytest

from workspace_tui.services.calendar import CalendarEvent
from workspace_tui.services.dashboard import (
    DashboardMetrics,
    DashboardService,
    _event_duration_seconds,
    _is_meeting,
    _meeting_duration_seconds,
)
from workspace_tui.services.drive import DriveFile
from workspace_tui.services.gmail import EmailHeader, EmailMessage, GmailLabel
from workspace_tui.services.jira import JiraIssue


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


def _make_gmail_label(label_id: str = "INBOX", unread: int = 5) -> GmailLabel:
    return GmailLabel(
        label_id=label_id,
        name="In arrivo",
        label_type="system",
        unread_count=unread,
    )


def _make_email(subject: str = "Test email") -> EmailMessage:
    return EmailMessage(
        message_id="msg1",
        thread_id="thr1",
        header=EmailHeader(
            from_address="Sender <sender@test.com>",
            subject=subject,
        ),
        is_unread=True,
    )


def _make_event(
    meet_link: str = "",
    location: str = "",
    description: str = "",
    start: str = "2099-01-01T10:00:00Z",
    end: str = "2099-01-01T11:00:00Z",
    summary: str = "Evento",
) -> CalendarEvent:
    return CalendarEvent(
        event_id="evt1",
        summary=summary,
        start=start,
        end=end,
        meet_link=meet_link,
        location=location,
        description=description,
    )


def _make_drive_file(name: str = "doc.txt") -> DriveFile:
    return DriveFile(file_id="f1", name=name, mime_type="text/plain")


@pytest.fixture
def mock_jira():
    service = MagicMock()
    service.search_issues.return_value = (
        [
            _make_issue(),
            _make_issue(
                key="PROJ-2",
                priority="High",
                status_category="To Do",
            ),
        ],
        2,
    )
    return service


@pytest.fixture
def mock_gmail():
    service = MagicMock()
    service.list_labels.return_value = [_make_gmail_label()]
    service.list_messages.return_value = ([_make_email()], None)
    return service


@pytest.fixture
def mock_calendar():
    service = MagicMock()
    service.list_events.return_value = [
        _make_event(meet_link="https://meet.google.com/abc"),
        _make_event(location="https://teams.microsoft.com/l/meetup"),
        _make_event(meet_link="https://zoom.us/j/123"),
    ]
    return service


@pytest.fixture
def mock_drive():
    service = MagicMock()
    service.list_recent.return_value = [_make_drive_file()]
    return service


class TestDashboardHappyPath:
    def test_collects_all_metrics(
        self,
        mock_jira,
        mock_gmail,
        mock_calendar,
        mock_drive,
    ):
        svc = DashboardService(
            jira_service=mock_jira,
            gmail_service=mock_gmail,
            calendar_service=mock_calendar,
            drive_service=mock_drive,
        )
        metrics = svc.collect()

        assert metrics.jira_available is True
        assert metrics.open_tasks == 2
        assert metrics.gmail_unread == 5
        assert metrics.meetings_today_total == 3
        assert len(metrics.recent_emails) == 1
        assert len(metrics.recent_files) == 1
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

    def test_recent_tasks_collected(self, mock_jira):
        svc = DashboardService(jira_service=mock_jira)
        metrics = svc.collect()

        assert len(metrics.recent_tasks) == 2


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
        failing_drive = MagicMock()
        failing_drive.list_recent.side_effect = RuntimeError("down")

        svc = DashboardService(
            jira_service=failing_jira,
            gmail_service=failing_gmail,
            calendar_service=failing_calendar,
            drive_service=failing_drive,
        )
        metrics = svc.collect()

        assert len(metrics.errors) >= 4


class TestDashboardEdgeCases:
    def test_gmail_no_inbox_label(self, mock_gmail):
        mock_gmail.list_labels.return_value = [
            GmailLabel(
                label_id="SENT",
                name="Inviati",
                label_type="system",
                unread_count=0,
            )
        ]
        svc = DashboardService(gmail_service=mock_gmail)
        metrics = svc.collect()

        assert metrics.gmail_unread == 0

    def test_recent_emails_collected(self, mock_gmail):
        mock_gmail.list_messages.return_value = (
            [_make_email("Subj 1"), _make_email("Subj 2")],
            None,
        )
        svc = DashboardService(gmail_service=mock_gmail)
        metrics = svc.collect()

        assert len(metrics.recent_emails) == 2

    def test_drive_files_collected(self, mock_drive):
        svc = DashboardService(drive_service=mock_drive)
        metrics = svc.collect()

        assert len(metrics.recent_files) == 1

    def test_next_meeting_is_first_future(self):
        cal = MagicMock()
        cal.list_events.return_value = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2099-01-01T10:00:00Z",
                end="2099-01-01T11:00:00Z",
                summary="First",
            ),
            _make_event(
                meet_link="https://zoom.us/j/123",
                start="2099-01-01T14:00:00Z",
                end="2099-01-01T15:00:00Z",
                summary="Second",
            ),
        ]
        svc = DashboardService(calendar_service=cal)
        metrics = svc.collect()

        assert metrics.next_meeting is not None
        assert metrics.next_meeting.summary == "First"

    def test_no_next_meeting_when_all_past(self):
        cal = MagicMock()
        cal.list_events.return_value = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2000-01-01T10:00:00Z",
                end="2000-01-01T11:00:00Z",
            ),
        ]
        svc = DashboardService(calendar_service=cal)
        metrics = svc.collect()

        assert metrics.next_meeting is None


class TestMeetingFilter:
    def test_event_with_meet_link_is_meeting(self):
        event = _make_event(meet_link="https://meet.google.com/abc-defg-hij")
        assert _is_meeting(event) is True

    def test_event_with_teams_in_location_is_meeting(self):
        event = _make_event(
            location="https://teams.microsoft.com/l/meetup-join/123",
        )
        assert _is_meeting(event) is True

    def test_event_with_zoom_in_description_is_meeting(self):
        event = _make_event(description="Join: https://zoom.us/j/123456")
        assert _is_meeting(event) is True

    def test_event_with_webex_is_meeting(self):
        event = _make_event(description="https://company.webex.com/meet/user")
        assert _is_meeting(event) is True

    def test_event_with_gotomeeting_is_meeting(self):
        event = _make_event(location="https://www.gotomeeting.com/join/123")
        assert _is_meeting(event) is True

    def test_event_with_whereby_is_meeting(self):
        event = _make_event(location="https://whereby.com/my-room")
        assert _is_meeting(event) is True

    def test_event_with_bluejeans_is_meeting(self):
        event = _make_event(description="https://bluejeans.com/123456")
        assert _is_meeting(event) is True

    def test_event_with_chime_is_meeting(self):
        event = _make_event(meet_link="https://chime.aws/123456")
        assert _is_meeting(event) is True

    def test_event_without_link_is_not_meeting(self):
        event = _make_event()
        assert _is_meeting(event) is False

    def test_event_with_unrelated_location_is_not_meeting(self):
        event = _make_event(location="Sala Riunioni 3B")
        assert _is_meeting(event) is False

    def test_event_with_unrelated_description_is_not_meeting(self):
        event = _make_event(description="Pranzo di team building")
        assert _is_meeting(event) is False

    def test_only_meetings_counted_in_dashboard(self):
        cal = MagicMock()
        cal.list_events.return_value = [
            _make_event(meet_link="https://meet.google.com/abc"),
            _make_event(location="Sala Riunioni"),
            _make_event(description="Reminder: consegna report"),
            _make_event(description="Join: https://zoom.us/j/999"),
        ]
        svc = DashboardService(calendar_service=cal)
        metrics = svc.collect()

        assert metrics.meetings_today_total == 2
        assert metrics.meetings_week_total == 2

    def test_past_meetings_not_counted_as_remaining(self):
        past = "2000-01-01T09:00:00Z"
        future = "2099-01-01T15:00:00Z"
        cal = MagicMock()
        cal.list_events.return_value = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start=past,
            ),
            _make_event(
                meet_link="https://zoom.us/j/123",
                start=past,
            ),
            _make_event(
                meet_link="https://teams.microsoft.com/l/x",
                start=future,
            ),
        ]
        svc = DashboardService(calendar_service=cal)
        metrics = svc.collect()

        assert metrics.meetings_today_total == 3
        assert metrics.meetings_today_remaining == 1
        assert metrics.meetings_week_total == 3
        assert metrics.meetings_week_remaining == 1


class TestMeetingDuration:
    def test_event_duration_one_hour(self):
        event = _make_event(
            start="2026-04-29T10:00:00Z",
            end="2026-04-29T11:00:00Z",
        )
        assert _event_duration_seconds(event) == 3600

    def test_event_duration_30_minutes(self):
        event = _make_event(
            start="2026-04-29T14:00:00Z",
            end="2026-04-29T14:30:00Z",
        )
        assert _event_duration_seconds(event) == 1800

    def test_event_duration_all_day_returns_zero(self):
        event = _make_event(start="2026-04-29", end="2026-04-30")
        assert _event_duration_seconds(event) == 0

    def test_meeting_duration_all_past(self):
        meetings = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2000-01-01T09:00:00Z",
                end="2000-01-01T10:00:00Z",
            ),
            _make_event(
                meet_link="https://zoom.us/j/123",
                start="2000-01-01T10:00:00Z",
                end="2000-01-01T10:30:00Z",
            ),
        ]
        done, total = _meeting_duration_seconds(
            meetings,
            now_iso="2026-01-01T00:00:00+00:00",
        )
        assert total == 5400
        assert done == 5400

    def test_meeting_duration_all_future(self):
        meetings = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2099-01-01T09:00:00Z",
                end="2099-01-01T10:00:00Z",
            ),
        ]
        done, total = _meeting_duration_seconds(
            meetings,
            now_iso="2026-01-01T00:00:00+00:00",
        )
        assert total == 3600
        assert done == 0

    def test_meeting_duration_mixed_past_future(self):
        meetings = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2000-01-01T09:00:00Z",
                end="2000-01-01T10:00:00Z",
            ),
            _make_event(
                meet_link="https://zoom.us/j/123",
                start="2099-01-01T09:00:00Z",
                end="2099-01-01T10:00:00Z",
            ),
        ]
        done, total = _meeting_duration_seconds(
            meetings,
            now_iso="2026-01-01T00:00:00+00:00",
        )
        assert total == 7200
        assert done == 3600

    def test_meeting_duration_empty_list(self):
        done, total = _meeting_duration_seconds(
            [],
            now_iso="2026-01-01T00:00:00+00:00",
        )
        assert total == 0
        assert done == 0

    def test_dashboard_reports_meeting_seconds(self):
        cal = MagicMock()
        cal.list_events.return_value = [
            _make_event(
                meet_link="https://meet.google.com/abc",
                start="2000-01-01T09:00:00Z",
                end="2000-01-01T10:00:00Z",
            ),
            _make_event(
                meet_link="https://zoom.us/j/123",
                start="2099-06-15T14:00:00Z",
                end="2099-06-15T15:00:00Z",
            ),
        ]
        svc = DashboardService(calendar_service=cal)
        metrics = svc.collect()

        assert metrics.meetings_today_total_seconds == 7200
        assert metrics.meetings_today_done_seconds == 3600
