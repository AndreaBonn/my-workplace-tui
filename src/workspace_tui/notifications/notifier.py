from loguru import logger


class Notifier:
    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        if not enabled:
            logger.warning("Notifier disabled via settings (NOTIFICATIONS_ENABLED=false)")

    def notify(self, title: str, message: str, timeout: int = 5) -> None:
        if not self._enabled:
            logger.debug("Notification skipped (disabled): {}", title)
            return
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message,
                app_name="Workspace TUI",
                timeout=timeout,
            )
            logger.debug("Notification sent: {}", title)
        except Exception as exc:
            logger.warning("Failed to send notification: {}", exc)
