from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, TextArea


class IssueCreateData(Message):
    def __init__(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        priority: str,
        assignee_id: str,
        description: str,
    ) -> None:
        self.project_key = project_key
        self.summary = summary
        self.issue_type = issue_type
        self.priority = priority
        self.assignee_id = assignee_id
        self.description = description
        super().__init__()


class IssueCreateModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Annulla", show=True),
    ]

    def __init__(
        self,
        default_project: str = "",
        issue_types: list[str] | None = None,
        priorities: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._default_project = default_project
        self._issue_types = issue_types or ["Task", "Bug", "Story", "Epic"]
        self._priorities = priorities or ["Highest", "High", "Medium", "Low", "Lowest"]

    def compose(self) -> ComposeResult:
        with Vertical(id="issue-create-container"):
            yield Label("Nuova issue", id="create-title")
            yield Label("Progetto:")
            yield Input(value=self._default_project, id="create-project")
            yield Label("Tipo:")
            yield Select(
                [(t, t) for t in self._issue_types],
                value=self._issue_types[0],
                id="create-type",
            )
            yield Label("Summary:")
            yield Input(id="create-summary")
            yield Label("Priorità:")
            yield Select(
                [(p, p) for p in self._priorities],
                value="Medium",
                id="create-priority",
            )
            yield Label("Descrizione:")
            yield TextArea(id="create-description")
            yield Label("[Ctrl+Enter] Crea   [Esc] Annulla")

    def key_ctrl_enter(self) -> None:
        project = self.query_one("#create-project", Input).value.strip()
        summary = self.query_one("#create-summary", Input).value.strip()
        issue_type = self.query_one("#create-type", Select).value
        priority = self.query_one("#create-priority", Select).value
        description = self.query_one("#create-description", TextArea).text

        if not project:
            self.app.notify("Progetto obbligatorio", severity="error")
            return
        if not summary:
            self.app.notify("Summary obbligatoria", severity="error")
            return

        self.dismiss(
            IssueCreateData(
                project_key=project,
                summary=summary,
                issue_type=str(issue_type),
                priority=str(priority),
                assignee_id="",
                description=description,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
