from unittest.mock import patch

from workspace_tui.notifications.notifier import Notifier


class TestNotifier:
    def test_notify_disabled(self):
        notifier = Notifier(enabled=False)
        notifier.notify(title="Test", message="Test message")

    @patch("plyer.notification")
    def test_notify_enabled(self, mock_notification):
        notifier = Notifier(enabled=True)
        notifier.notify(title="Test", message="Test message", timeout=3)
        mock_notification.notify.assert_called_once_with(
            title="Test",
            message="Test message",
            app_name="Workspace TUI",
            timeout=3,
        )

    @patch("plyer.notification")
    def test_notify_handles_exception(self, mock_notification):
        mock_notification.notify.side_effect = RuntimeError("No display")
        notifier = Notifier(enabled=True)
        notifier.notify(title="Test", message="Test message")
