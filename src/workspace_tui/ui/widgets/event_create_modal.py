from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label


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
        height: 80%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    #event-create-scroll {
        height: 1fr;
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

    #event-allday {
        height: auto;
        min-height: 3;
        margin-top: 1;
    }

    #create-title {
        text-style: bold;
        padding-bottom: 1;
        margin-top: 0;
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

    #event-actions {
        height: auto;
        margin-top: 1;
        align: right middle;
    }

    #event-actions Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="event-create-container"):
            yield Label("Nuovo evento", id="create-title")
            with VerticalScroll(id="event-create-scroll"):
                yield Label("Titolo:")
                yield Input(id="event-summary", placeholder="Titolo evento")
                yield Label("Data (GG/MM/AAAA):")
                yield Input(id="event-date", placeholder="29/04/2026")
                yield Checkbox("Tutto il giorno", id="event-allday")
                yield Label("Ora inizio - fine (HH:MM):")
                with Horizontal(classes="time-row"):
                    yield Input(id="event-start", placeholder="09:00", value="09:00")
                    yield Input(id="event-end", placeholder="10:00", value="10:00")
                yield Label("Luogo:")
                yield Input(id="event-location", placeholder="Opzionale")
                yield Label("Partecipanti (email separate da virgola):")
                yield Input(id="event-attendees", placeholder="a@email.com, b@email.com")
                yield Label("Descrizione:")
                yield Input(id="event-description", placeholder="Opzionale")
            with Horizontal(id="event-actions"):
                yield Button("Crea", variant="primary", id="btn-create")
                yield Button("Annulla", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#event-summary", Input).focus()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "event-allday":
            self.query_one("#event-start", Input).disabled = event.value
            self.query_one("#event-end", Input).disabled = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self._submit()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        summary = self.query_one("#event-summary", Input).value.strip()
        date = self.query_one("#event-date", Input).value.strip()
        start_time = self.query_one("#event-start", Input).value.strip()
        end_time = self.query_one("#event-end", Input).value.strip()
        all_day = self.query_one("#event-allday", Checkbox).value
        location = self.query_one("#event-location", Input).value.strip()
        attendees = self.query_one("#event-attendees", Input).value.strip()
        description = self.query_one("#event-description", Input).value.strip()

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
