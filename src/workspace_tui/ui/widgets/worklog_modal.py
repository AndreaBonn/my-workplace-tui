from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label

from workspace_tui.utils.date_utils import parse_jira_duration


class WorklogData(Message):
    def __init__(self, time_spent_seconds: int, started: str, comment: str) -> None:
        self.time_spent_seconds = time_spent_seconds
        self.started = started
        self.comment = comment
        super().__init__()


class WorklogModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Annulla", show=True),
    ]

    def __init__(self, issue_key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._issue_key = issue_key

    def compose(self) -> ComposeResult:
        today = datetime.now().strftime("%d/%m/%Y")
        with Vertical(id="worklog-container"):
            yield Label(f"Log ore — {self._issue_key}", id="worklog-title")
            yield Label("Tempo:")
            yield Input(placeholder="1h 30m", id="worklog-time")
            yield Label("Data:")
            yield Input(value=today, id="worklog-date")
            yield Label("Note:")
            yield Input(placeholder="Opzionale", id="worklog-comment")
            yield Label("[Ctrl+Enter] Salva   [Esc] Annulla")

    def key_ctrl_enter(self) -> None:
        time_str = self.query_one("#worklog-time", Input).value
        date_str = self.query_one("#worklog-date", Input).value
        comment = self.query_one("#worklog-comment", Input).value

        seconds = parse_jira_duration(time_str)
        if seconds is None or seconds <= 0:
            self.app.notify("Formato tempo non valido (es: 1h 30m)", severity="error")
            return

        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            started = dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        except ValueError:
            self.app.notify("Formato data non valido (GG/MM/AAAA)", severity="error")
            return

        self.dismiss(
            WorklogData(
                time_spent_seconds=seconds,
                started=started,
                comment=comment,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
