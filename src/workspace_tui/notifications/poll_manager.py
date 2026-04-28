from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from workspace_tui.services.errors import ServiceError

if TYPE_CHECKING:
    from collections.abc import Callable

    from workspace_tui.notifications.notifier import Notifier


@dataclass
class PollState:
    """Tracks last-known state per service to detect changes."""

    gmail_unread_ids: set[str] = field(default_factory=set)
    gmail_initialized: bool = False
    calendar_notified_ids: set[str] = field(default_factory=set)
    chat_last_message: dict[str, str] = field(default_factory=dict)
    chat_initialized: bool = False
    jira_known_keys: set[str] = field(default_factory=set)
    jira_initialized: bool = False


@dataclass
class PollResult:
    """Result of a poll cycle, consumed by the app to update UI."""

    gmail_unread: int = 0
    jira_assigned: int = 0
    calendar_upcoming: int = 0
    timestamp: str = ""


class PollManager:
    """Periodic background poller for all services.

    Detects new items by comparing current state against previous state.
    Sends OS notifications for genuinely new items and reports counts
    back to the app via a callback.

    Parameters
    ----------
    notifier : Notifier
        Desktop notification sender.
    on_update : Callable[[PollResult], None]
        Called from the polling thread with updated counts.
        The app must use ``call_from_thread`` to marshal UI updates.
    """

    def __init__(
        self,
        *,
        notifier: Notifier,
        on_update: Callable[[PollResult], None],
    ) -> None:
        self._notifier = notifier
        self._on_update = on_update
        self._state = PollState()
        self._stop = threading.Event()
        self._timers: list[threading.Timer] = []

        self._gmail_service = None
        self._calendar_service = None
        self._chat_service = None
        self._jira_service = None

        self._gmail_interval = 60
        self._calendar_interval = 300
        self._chat_interval = 30
        self._jira_interval = 120

    def configure(
        self,
        *,
        gmail_service=None,
        calendar_service=None,
        chat_service=None,
        jira_service=None,
        gmail_interval: int = 60,
        calendar_interval: int = 300,
        chat_interval: int = 30,
        jira_interval: int = 120,
    ) -> None:
        self._gmail_service = gmail_service
        self._calendar_service = calendar_service
        self._chat_service = chat_service
        self._jira_service = jira_service
        self._gmail_interval = gmail_interval
        self._calendar_interval = calendar_interval
        self._chat_interval = chat_interval
        self._jira_interval = jira_interval

    def start(self) -> None:
        self._stop.clear()
        if self._gmail_service:
            self._schedule(self._poll_gmail, self._gmail_interval)
        if self._calendar_service:
            self._schedule(self._poll_calendar, self._calendar_interval)
        if self._chat_service:
            self._schedule(self._poll_chat, self._chat_interval)
        if self._jira_service:
            self._schedule(self._poll_jira, self._jira_interval)
        logger.info("PollManager started")

    def stop(self) -> None:
        self._stop.set()
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        logger.info("PollManager stopped")

    def _schedule(self, target: Callable[[], None], interval: int) -> None:
        def loop() -> None:
            if self._stop.is_set():
                return
            try:
                target()
            except Exception as exc:
                logger.error("Poll error in {}: {}", target.__name__, exc)
            if not self._stop.is_set():
                timer = threading.Timer(interval, loop)
                timer.daemon = True
                self._timers.append(timer)
                timer.start()

        timer = threading.Timer(interval, loop)
        timer.daemon = True
        self._timers.append(timer)
        timer.start()

    def _poll_gmail(self) -> None:
        try:
            messages, _ = self._gmail_service.list_messages(
                label_id="INBOX", query="is:unread", max_results=20
            )
        except ServiceError as exc:
            logger.warning("Gmail poll failed: {}", exc.message)
            return

        current_ids = {m.message_id for m in messages}

        if self._state.gmail_initialized:
            new_ids = current_ids - self._state.gmail_unread_ids
            for msg in messages:
                if msg.message_id in new_ids:
                    sender = _truncate(msg.header.from_address, max_len=40)
                    subject = _truncate(msg.header.subject, max_len=60)
                    self._notifier.notify(
                        title=f"📧 {sender}",
                        message=subject,
                    )
            if new_ids:
                logger.info("Gmail: {} nuove mail non lette", len(new_ids))

        self._state.gmail_unread_ids = current_ids
        self._state.gmail_initialized = True

        self._emit_update(gmail_unread=len(current_ids))

    def _poll_calendar(self) -> None:
        now = datetime.now(tz=UTC)
        window = now + timedelta(minutes=15)

        try:
            events = self._calendar_service.list_events(
                time_min=now, time_max=window, max_results=10
            )
        except ServiceError as exc:
            logger.warning("Calendar poll failed: {}", exc.message)
            return

        for event in events:
            if event.event_id not in self._state.calendar_notified_ids:
                self._state.calendar_notified_ids.add(event.event_id)
                self._notifier.notify(
                    title="📅 Evento imminente",
                    message=_truncate(event.summary, max_len=80),
                    timeout=10,
                )

        # Pulizia ID vecchi (max 200)
        if len(self._state.calendar_notified_ids) > 200:
            self._state.calendar_notified_ids = set(list(self._state.calendar_notified_ids)[-100:])

        self._emit_update(calendar_upcoming=len(events))

    def _poll_chat(self) -> None:
        try:
            spaces = self._chat_service.list_spaces()
        except ServiceError as exc:
            logger.warning("Chat poll failed: {}", exc.message)
            return

        for space in spaces:
            try:
                messages = self._chat_service.list_messages(space_name=space.name, max_results=1)
            except ServiceError:
                continue

            if not messages:
                continue

            latest = messages[-1]
            previous = self._state.chat_last_message.get(space.name)

            if self._state.chat_initialized and previous and latest.name != previous:
                self._notifier.notify(
                    title=f"💬 {_truncate(space.display_name, max_len=30)}",
                    message=_truncate(latest.text, max_len=80),
                )

            self._state.chat_last_message[space.name] = latest.name

        self._state.chat_initialized = True

    def _poll_jira(self) -> None:
        try:
            issues, total = self._jira_service.search_issues(
                jql="assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC",
                max_results=20,
            )
        except ServiceError as exc:
            logger.warning("Jira poll failed: {}", exc.message)
            return

        current_keys = {i.key for i in issues}

        if self._state.jira_initialized:
            new_keys = current_keys - self._state.jira_known_keys
            for issue in issues:
                if issue.key in new_keys:
                    self._notifier.notify(
                        title=f"🎫 {issue.key}",
                        message=_truncate(issue.summary, max_len=80),
                    )
            if new_keys:
                logger.info("Jira: {} nuove issue assegnate", len(new_keys))

        self._state.jira_known_keys = current_keys
        self._state.jira_initialized = True

        self._emit_update(jira_assigned=total)

    def _emit_update(self, **counts: int) -> None:
        result = PollResult(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            **counts,
        )
        try:
            self._on_update(result)
        except Exception as exc:
            logger.warning("Failed to emit poll update: {}", exc)


def _truncate(text: str, *, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
