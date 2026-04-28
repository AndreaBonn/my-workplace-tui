from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, TextArea


class EventCreateData(Message):
    def __init__(
        self,
        summary: str,
        date: str,
        start_time: str,
        end_time: str,
        location: str,
        description: str,
        attendees: str,
        all_day: bool,
    ) -> None:
        self.summary = summary
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.description = description
        self.attendees = attendees
        self.all_day = all_day
        super().__init__()


class EventCreateModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Annulla", show=True),
    ]

    DEFAULT_CSS = """
    EventCreateModal {
        align: center middle;
    }

    #event-create-container {
        width: 70%;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    #event-create-container Label {
        margin-top: 1;
    }

    #event-create-container Input {
        height: 1;
        border: none;
        background: $primary 10%;
        padding: 0 1;
    }

    #event-create-container Input:focus {
        background: $primary 20%;
    }

    #event-create-container TextArea {
        height: 4;
        min-height: 3;
    }

    #event-create-container Checkbox {
        height: 1;
        margin-top: 1;
    }

    #create-title {
        text-style: bold;
        padding-bottom: 1;
    }

    .time-row {
        layout: horizontal;
        height: auto;
    }

    .time-row Input {
        width: 1fr;
    }

    .time-row Label {
        width: auto;
        padding: 0 1;
        margin-top: 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="event-create-container"):
            yield Label("Nuovo evento", id="create-title")
            yield Label("Titolo:")
            yield Input(id="event-summary", placeholder="Titolo evento")
            yield Label("Data (GG/MM/AAAA):")
            yield Input(id="event-date", placeholder="29/04/2026")
            yield Checkbox("Tutto il giorno", id="event-allday")
            yield Label("Ora inizio - fine (HH:MM):")
            with Vertical(classes="time-row"):
                yield Input(id="event-start", placeholder="09:00", value="09:00")
                yield Input(id="event-end", placeholder="10:00", value="10:00")
            yield Label("Luogo:")
            yield Input(id="event-location", placeholder="Opzionale")
            yield Label("Partecipanti (email separate da virgola):")
            yield Input(id="event-attendees", placeholder="a@email.com, b@email.com")
            yield Label("Descrizione:")
            yield TextArea(id="event-description")
            yield Label("[Ctrl+Enter] Crea   [Esc] Annulla")

    def on_mount(self) -> None:
        self.query_one("#event-summary", Input).focus()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "event-allday":
            start_input = self.query_one("#event-start", Input)
            end_input = self.query_one("#event-end", Input)
            start_input.disabled = event.value
            end_input.disabled = event.value

    def key_ctrl_enter(self) -> None:
        summary = self.query_one("#event-summary", Input).value.strip()
        date = self.query_one("#event-date", Input).value.strip()
        start_time = self.query_one("#event-start", Input).value.strip()
        end_time = self.query_one("#event-end", Input).value.strip()
        all_day = self.query_one("#event-allday", Checkbox).value
        location = self.query_one("#event-location", Input).value.strip()
        attendees = self.query_one("#event-attendees", Input).value.strip()
        description = self.query_one("#event-description", TextArea).text

        if not summary:
            self.app.notify("Titolo obbligatorio", severity="error")
            return
        if not date:
            self.app.notify("Data obbligatoria", severity="error")
            return
        if not all_day and (not start_time or not end_time):
            self.app.notify("Orario inizio e fine obbligatori", severity="error")
            return

        self.dismiss(
            EventCreateData(
                summary=summary,
                date=date,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                attendees=attendees,
                all_day=all_day,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
