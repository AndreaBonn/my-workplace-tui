from unittest.mock import MagicMock

import pytest

from workspace_tui.services.chat import ChatMessage, ChatSpace
from workspace_tui.services.drive import DriveFile
from workspace_tui.services.gmail import EmailHeader, EmailMessage
from workspace_tui.services.jira import JiraIssue
from workspace_tui.services.search import (
    SearchService,
    SearchSource,
)


def _make_email(msg_id: str = "m1", subject: str = "Test email") -> EmailMessage:
    return EmailMessage(
        message_id=msg_id,
        thread_id="t1",
        header=EmailHeader(
            from_address="alice@test.com",
            to_address="me@test.com",
            subject=subject,
            date="2026-04-28",
        ),
        snippet="This is a test email",
    )


def _make_issue(key: str = "PROJ-1", summary: str = "Fix bug") -> JiraIssue:
    return JiraIssue(
        key=key,
        summary=summary,
        status="In Progress",
        status_category="In Progress",
        issue_type="Bug",
        priority="High",
        assignee="Alice",
        reporter="Bob",
        sprint="Sprint 5",
        description_text="A bug to fix",
        created="2026-04-20",
        updated="2026-04-28",
        estimate_seconds=3600,
        logged_seconds=1800,
    )


def _make_drive_file(file_id: str = "f1", name: str = "report.pdf") -> DriveFile:
    return DriveFile(
        file_id=file_id,
        name=name,
        mime_type="application/pdf",
        size=1024,
        modified_time="2026-04-28T10:00:00Z",
        owner="alice@test.com",
        icon="📕",
    )


def _make_space(name: str = "spaces/abc", display_name: str = "General") -> ChatSpace:
    return ChatSpace(
        name=name,
        display_name=display_name,
        space_type="ROOM",
    )


def _make_chat_message(text: str = "hello world") -> ChatMessage:
    return ChatMessage(
        name="spaces/abc/messages/1",
        sender_name="users/alice",
        sender_display_name="Alice",
        text=text,
        create_time="2026-04-28T10:00:00Z",
    )


@pytest.fixture
def mock_gmail():
    service = MagicMock()
    service.list_messages.return_value = ([_make_email()], None)
    return service


@pytest.fixture
def mock_jira():
    service = MagicMock()
    service.search_issues.return_value = ([_make_issue()], 1)
    return service


@pytest.fixture
def mock_drive():
    service = MagicMock()
    service.search_files.return_value = [_make_drive_file()]
    return service


@pytest.fixture
def mock_chat():
    service = MagicMock()
    service.list_spaces.return_value = [_make_space()]
    service.list_messages.return_value = [_make_chat_message()]
    return service


class TestSearchHappyPath:
    def test_returns_results_from_all_sources(self, mock_gmail, mock_jira, mock_drive, mock_chat):
        svc = SearchService(
            gmail_service=mock_gmail,
            jira_service=mock_jira,
            drive_service=mock_drive,
            chat_service=mock_chat,
        )
        response = svc.search("hello")

        sources = {r.source for r in response.results}
        assert SearchSource.GMAIL in sources
        assert SearchSource.JIRA in sources
        assert SearchSource.DRIVE in sources
        assert SearchSource.CHAT in sources
        assert not response.errors

    def test_gmail_result_has_correct_fields(self, mock_gmail):
        svc = SearchService(gmail_service=mock_gmail)
        response = svc.search("test")

        gmail_results = [r for r in response.results if r.source == SearchSource.GMAIL]
        assert len(gmail_results) == 1
        assert gmail_results[0].title == "Test email"
        assert "alice@test.com" in gmail_results[0].snippet
        assert gmail_results[0].identifier == "m1"

    def test_jira_result_has_key_and_summary(self, mock_jira):
        svc = SearchService(jira_service=mock_jira)
        response = svc.search("bug")

        jira_results = [r for r in response.results if r.source == SearchSource.JIRA]
        assert len(jira_results) == 1
        assert "PROJ-1" in jira_results[0].title
        assert "Fix bug" in jira_results[0].title
        assert "In Progress" in jira_results[0].snippet

    def test_drive_result_has_file_info(self, mock_drive):
        svc = SearchService(drive_service=mock_drive)
        response = svc.search("report")

        drive_results = [r for r in response.results if r.source == SearchSource.DRIVE]
        assert len(drive_results) == 1
        assert "report.pdf" in drive_results[0].title
        assert drive_results[0].identifier == "f1"

    def test_chat_result_filters_by_text(self, mock_chat):
        svc = SearchService(chat_service=mock_chat)
        response = svc.search("hello")

        chat_results = [r for r in response.results if r.source == SearchSource.CHAT]
        assert len(chat_results) == 1
        assert "Alice" in chat_results[0].snippet


class TestSearchEdgeCases:
    def test_short_query_returns_empty(self):
        svc = SearchService(gmail_service=MagicMock())
        response = svc.search("a")

        assert response.results == []
        assert not response.errors

    def test_empty_query_returns_empty(self):
        svc = SearchService(gmail_service=MagicMock())
        response = svc.search("")

        assert response.results == []

    def test_no_services_returns_empty(self):
        svc = SearchService()
        response = svc.search("test")

        assert response.results == []
        assert not response.errors


class TestSearchProviderFailure:
    def test_single_provider_failure_returns_partial_results(self, mock_gmail, mock_drive):
        failing_jira = MagicMock()
        failing_jira.search_issues.side_effect = RuntimeError("Connection refused")

        svc = SearchService(
            gmail_service=mock_gmail,
            jira_service=failing_jira,
            drive_service=mock_drive,
        )
        response = svc.search("test")

        assert len(response.results) >= 2
        assert SearchSource.JIRA in response.errors
        assert "Connection refused" in response.errors[SearchSource.JIRA]

        sources = {r.source for r in response.results}
        assert SearchSource.GMAIL in sources
        assert SearchSource.DRIVE in sources

    def test_all_providers_fail_returns_all_errors(self):
        failing_gmail = MagicMock()
        failing_gmail.list_messages.side_effect = RuntimeError("Gmail down")

        failing_jira = MagicMock()
        failing_jira.search_issues.side_effect = RuntimeError("Jira down")

        svc = SearchService(
            gmail_service=failing_gmail,
            jira_service=failing_jira,
        )
        response = svc.search("test")

        assert response.results == []
        assert len(response.errors) == 2


class TestSearchChatClientSide:
    def test_chat_no_match_returns_empty(self, mock_chat):
        mock_chat.list_messages.return_value = [_make_chat_message(text="goodbye")]

        svc = SearchService(chat_service=mock_chat)
        response = svc.search("zzz_nonexistent")

        chat_results = [r for r in response.results if r.source == SearchSource.CHAT]
        assert chat_results == []

    def test_chat_case_insensitive(self, mock_chat):
        mock_chat.list_messages.return_value = [_make_chat_message(text="Hello World")]

        svc = SearchService(chat_service=mock_chat)
        response = svc.search("hello")

        chat_results = [r for r in response.results if r.source == SearchSource.CHAT]
        assert len(chat_results) == 1

    def test_chat_space_failure_skips_silently(self, mock_chat):
        mock_chat.list_spaces.return_value = [_make_space(), _make_space(name="spaces/xyz")]
        mock_chat.list_messages.side_effect = [
            RuntimeError("forbidden"),
            [_make_chat_message(text="hello")],
        ]

        svc = SearchService(chat_service=mock_chat)
        response = svc.search("hello")

        chat_results = [r for r in response.results if r.source == SearchSource.CHAT]
        assert len(chat_results) == 1
