from unittest.mock import MagicMock

import pytest

from workspace_tui.notifications.poll_manager import (
    PollManager,
    PollResult,
    PollState,
    _truncate,
)
from workspace_tui.services.errors import ServiceError


@pytest.fixture
def notifier():
    return MagicMock()


@pytest.fixture
def on_update():
    return MagicMock()


@pytest.fixture
def poll_manager(notifier, on_update):
    return PollManager(notifier=notifier, on_update=on_update)


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("ciao", max_len=10) == "ciao"

    def test_exact_length_unchanged(self):
        assert _truncate("12345", max_len=5) == "12345"

    def test_long_text_truncated_with_ellipsis(self):
        result = _truncate("abcdefghij", max_len=5)
        assert result == "abcd…"
        assert len(result) == 5

    def test_empty_string(self):
        assert _truncate("", max_len=10) == ""


class TestPollState:
    def test_initial_state_not_initialized(self):
        state = PollState()
        assert not state.gmail_initialized
        assert not state.chat_initialized
        assert not state.jira_initialized
        assert state.gmail_unread_ids == set()
        assert state.chat_last_message == {}
        assert state.jira_known_keys == set()


class TestPollResult:
    def test_defaults_none_for_counts(self):
        result = PollResult()
        assert result.gmail_unread is None
        assert result.jira_assigned is None
        assert result.calendar_upcoming is None
        assert result.timestamp == ""

    def test_partial_update_preserves_none(self):
        result = PollResult(gmail_unread=5)
        assert result.gmail_unread == 5
        assert result.jira_assigned is None


class TestPollManagerLifecycle:
    def test_start_without_services_does_nothing(self, poll_manager):
        poll_manager.start()
        poll_manager.stop()

    def test_stop_sets_event(self, poll_manager):
        poll_manager.stop()
        assert poll_manager._stop.is_set()

    def test_stop_cancels_timers(self, poll_manager, notifier, on_update):
        gmail_svc = MagicMock()
        gmail_svc.list_messages.return_value = ([], None)

        poll_manager.configure(gmail_service=gmail_svc, gmail_interval=3600)
        poll_manager.start()
        assert len(poll_manager._timers) > 0

        poll_manager.stop()
        assert len(poll_manager._timers) == 0


class TestPollGmail:
    def _make_message(self, msg_id: str, sender: str = "a@b.com", subject: str = "Test"):
        msg = MagicMock()
        msg.message_id = msg_id
        msg.header = MagicMock()
        msg.header.from_address = sender
        msg.header.subject = subject
        return msg

    def test_first_poll_initializes_without_notification(self, poll_manager, notifier, on_update):
        gmail_svc = MagicMock()
        gmail_svc.list_messages.return_value = (
            [self._make_message("m1"), self._make_message("m2")],
            None,
        )
        poll_manager._gmail_service = gmail_svc

        poll_manager._poll_gmail()

        notifier.notify.assert_not_called()
        assert poll_manager._state.gmail_initialized
        assert poll_manager._state.gmail_unread_ids == {"m1", "m2"}

    def test_second_poll_notifies_new_messages(self, poll_manager, notifier, on_update):
        gmail_svc = MagicMock()
        poll_manager._gmail_service = gmail_svc

        # Prima poll: 2 messaggi
        gmail_svc.list_messages.return_value = (
            [self._make_message("m1"), self._make_message("m2")],
            None,
        )
        poll_manager._poll_gmail()

        # Seconda poll: m3 è nuovo
        gmail_svc.list_messages.return_value = (
            [
                self._make_message("m1"),
                self._make_message("m3", sender="nuovo@test.com", subject="Nuovo!"),
            ],
            None,
        )
        poll_manager._poll_gmail()

        notifier.notify.assert_called_once()
        call_kwargs = notifier.notify.call_args.kwargs
        assert "nuovo@test.com" in call_kwargs["title"]
        assert "Nuovo!" in call_kwargs["message"]

    def test_poll_handles_service_error(self, poll_manager, notifier, on_update):
        gmail_svc = MagicMock()
        gmail_svc.list_messages.side_effect = ServiceError("API down")
        poll_manager._gmail_service = gmail_svc

        poll_manager._poll_gmail()

        notifier.notify.assert_not_called()
        on_update.assert_not_called()

    def test_poll_emits_unread_count(self, poll_manager, notifier, on_update):
        gmail_svc = MagicMock()
        gmail_svc.list_messages.return_value = (
            [self._make_message("m1"), self._make_message("m2"), self._make_message("m3")],
            None,
        )
        poll_manager._gmail_service = gmail_svc

        poll_manager._poll_gmail()

        on_update.assert_called_once()
        result = on_update.call_args.args[0]
        assert result.gmail_unread == 3


class TestPollCalendar:
    def _make_event(self, event_id: str, summary: str = "Meeting"):
        event = MagicMock()
        event.event_id = event_id
        event.summary = summary
        return event

    def test_notifies_upcoming_events(self, poll_manager, notifier, on_update):
        cal_svc = MagicMock()
        cal_svc.list_events.return_value = [self._make_event("e1", "Standup")]
        poll_manager._calendar_service = cal_svc

        poll_manager._poll_calendar()

        notifier.notify.assert_called_once()
        call_kwargs = notifier.notify.call_args.kwargs
        assert "Standup" in call_kwargs["message"]

    def test_does_not_re_notify_same_event(self, poll_manager, notifier, on_update):
        cal_svc = MagicMock()
        cal_svc.list_events.return_value = [self._make_event("e1")]
        poll_manager._calendar_service = cal_svc

        poll_manager._poll_calendar()
        poll_manager._poll_calendar()

        assert notifier.notify.call_count == 1

    def test_cleans_old_notified_ids(self, poll_manager, notifier, on_update):
        cal_svc = MagicMock()
        cal_svc.list_events.return_value = []
        poll_manager._calendar_service = cal_svc

        poll_manager._state.calendar_notified_ids = {f"e{i}" for i in range(250)}
        poll_manager._poll_calendar()

        assert len(poll_manager._state.calendar_notified_ids) <= 100

    def test_poll_handles_service_error(self, poll_manager, notifier, on_update):
        cal_svc = MagicMock()
        cal_svc.list_events.side_effect = ServiceError("Calendar API down")
        poll_manager._calendar_service = cal_svc

        poll_manager._poll_calendar()

        notifier.notify.assert_not_called()


class TestPollChat:
    def _make_space(self, name: str, display_name: str = "General"):
        space = MagicMock()
        space.name = name
        space.display_name = display_name
        return space

    def _make_message(self, name: str, text: str = "Hello"):
        msg = MagicMock()
        msg.name = name
        msg.text = text
        return msg

    def test_first_poll_no_notification(self, poll_manager, notifier, on_update):
        chat_svc = MagicMock()
        chat_svc.list_spaces.return_value = [self._make_space("spaces/1")]
        chat_svc.list_messages.return_value = [self._make_message("msg/1")]
        poll_manager._chat_service = chat_svc

        poll_manager._poll_chat()

        notifier.notify.assert_not_called()
        assert poll_manager._state.chat_initialized

    def test_new_message_triggers_notification(self, poll_manager, notifier, on_update):
        chat_svc = MagicMock()
        chat_svc.list_spaces.return_value = [self._make_space("spaces/1", "Dev Team")]
        poll_manager._chat_service = chat_svc

        # Prima poll
        chat_svc.list_messages.return_value = [self._make_message("msg/1")]
        poll_manager._poll_chat()

        # Seconda poll — nuovo messaggio
        chat_svc.list_messages.return_value = [self._make_message("msg/2", "Nuova feature!")]
        poll_manager._poll_chat()

        notifier.notify.assert_called_once()
        call_kwargs = notifier.notify.call_args.kwargs
        assert "Dev Team" in call_kwargs["title"]
        assert "Nuova feature!" in call_kwargs["message"]

    def test_same_message_no_notification(self, poll_manager, notifier, on_update):
        chat_svc = MagicMock()
        chat_svc.list_spaces.return_value = [self._make_space("spaces/1")]
        chat_svc.list_messages.return_value = [self._make_message("msg/1")]
        poll_manager._chat_service = chat_svc

        poll_manager._poll_chat()
        poll_manager._poll_chat()

        notifier.notify.assert_not_called()


class TestPollJira:
    def _make_issue(self, key: str, summary: str = "Bug fix"):
        issue = MagicMock()
        issue.key = key
        issue.summary = summary
        return issue

    def test_first_poll_no_notification(self, poll_manager, notifier, on_update):
        jira_svc = MagicMock()
        jira_svc.search_issues.return_value = ([self._make_issue("PROJ-1")], 1)
        poll_manager._jira_service = jira_svc

        poll_manager._poll_jira()

        notifier.notify.assert_not_called()
        assert poll_manager._state.jira_initialized

    def test_new_issue_triggers_notification(self, poll_manager, notifier, on_update):
        jira_svc = MagicMock()
        poll_manager._jira_service = jira_svc

        # Prima poll
        jira_svc.search_issues.return_value = ([self._make_issue("PROJ-1")], 1)
        poll_manager._poll_jira()

        # Seconda poll — nuova issue
        jira_svc.search_issues.return_value = (
            [self._make_issue("PROJ-1"), self._make_issue("PROJ-2", "Urgent task")],
            2,
        )
        poll_manager._poll_jira()

        notifier.notify.assert_called_once()
        call_kwargs = notifier.notify.call_args.kwargs
        assert "PROJ-2" in call_kwargs["title"]
        assert "Urgent task" in call_kwargs["message"]

    def test_emits_total_count(self, poll_manager, notifier, on_update):
        jira_svc = MagicMock()
        jira_svc.search_issues.return_value = ([self._make_issue("PROJ-1")], 42)
        poll_manager._jira_service = jira_svc

        poll_manager._poll_jira()

        result = on_update.call_args.args[0]
        assert result.jira_assigned == 42

    def test_poll_handles_service_error(self, poll_manager, notifier, on_update):
        jira_svc = MagicMock()
        jira_svc.search_issues.side_effect = ServiceError("Jira down")
        poll_manager._jira_service = jira_svc

        poll_manager._poll_jira()

        notifier.notify.assert_not_called()
