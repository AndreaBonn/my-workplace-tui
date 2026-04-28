from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, TextArea


class ComposeData(Message):
    """Result of the compose modal."""

    def __init__(
        self,
        to: str,
        cc: str,
        subject: str,
        body: str,
        *,
        save_draft: bool = False,
    ) -> None:
        self.to = to
        self.cc = cc
        self.subject = subject
        self.body = body
        self.save_draft = save_draft
        super().__init__()


class ComposeModal(ModalScreen):
    BINDINGS = [
        Binding("ctrl+s", "save_draft", "Salva bozza", show=True),
        Binding("escape", "cancel", "Annulla", show=True),
    ]

    def __init__(
        self,
        to: str = "",
        cc: str = "",
        subject: str = "",
        body: str = "",
        title: str = "Nuova email",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._initial_to = to
        self._initial_cc = cc
        self._initial_subject = subject
        self._initial_body = body
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="compose-container"):
            yield Label(self._title, id="compose-title")
            yield Label("A:")
            yield Input(
                value=self._initial_to, id="compose-to", placeholder="destinatario@email.com"
            )
            yield Label("CC:")
            yield Input(value=self._initial_cc, id="compose-cc", placeholder="cc@email.com")
            yield Label("Oggetto:")
            yield Input(value=self._initial_subject, id="compose-subject")
            yield TextArea(text=self._initial_body, id="compose-body")
            yield Label("[Ctrl+Enter] Invia  [Ctrl+S] Bozza  [Esc] Annulla")

    def key_ctrl_enter(self) -> None:
        self._submit(save_draft=False)

    def action_save_draft(self) -> None:
        self._submit(save_draft=True)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self, *, save_draft: bool) -> None:
        to = self.query_one("#compose-to", Input).value
        cc = self.query_one("#compose-cc", Input).value
        subject = self.query_one("#compose-subject", Input).value
        body = self.query_one("#compose-body", TextArea).text

        self.dismiss(ComposeData(to=to, cc=cc, subject=subject, body=body, save_draft=save_draft))
