from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.calendar import CalendarEvent, CalendarService
from workspace_tui.utils.date_utils import format_datetime_short, parse_date


class CalendarTab(Vertical):
    BINDINGS = [
        Binding("h", "prev_period", "Precedente", show=True),
        Binding("l", "next_period", "Successivo", show=True),
        Binding("t", "go_today", "Oggi", show=True),
        Binding("c", "create_event", "Crea evento", show=True),
        Binding("d", "delete_event", "Elimina", show=False),
        Binding("v", "toggle_view", "Cambia vista", show=True),
    ]

    calendar_service: reactive[CalendarService | None] = reactive(None, init=False)
    events: reactive[list[CalendarEvent]] = reactive(list, init=False)
    current_view: reactive[str] = reactive("agenda")

    def compose(self) -> ComposeResult:
        with Vertical(id="calendar-layout"):
            yield Static("[Agenda]  Settimana  Mese", id="calendar-view-selector")
            yield VerticalScroll(Static("Caricamento eventi...", id="calendar-events"))

    def set_service(self, service: CalendarService) -> None:
        self.calendar_service = service
        self._load_events()

    def _load_events(self) -> None:
        if not self.calendar_service:
            return
        self.app.run_worker(self._load_events_worker, thread=True)

    async def _load_events_worker(self) -> None:
        if not self.calendar_service:
            return
        events = self.calendar_service.list_events()
        self.events = events
        self._render_events()

    def _render_events(self) -> None:
        events_widget = self.query_one("#calendar-events", Static)
        if not self.events:
            events_widget.update("Nessun evento nei prossimi 30 giorni")
            return

        lines = []
        for event in self.events:
            dt = parse_date(event.start)
            time_str = format_datetime_short(dt) if dt else event.start
            location = f" 📍 {event.location}" if event.location else ""
            meet = " 🔗 Meet" if event.meet_link else ""
            lines.append(f"  {time_str}  {event.summary}{location}{meet}")
            if event.attendees:
                lines.append(f"    Partecipanti: {', '.join(event.attendees[:3])}")
            lines.append("")

        events_widget.update("\n".join(lines))

    def action_prev_period(self) -> None:
        self.app.notify("Periodo precedente", timeout=2)

    def action_next_period(self) -> None:
        self.app.notify("Periodo successivo", timeout=2)

    def action_go_today(self) -> None:
        self._load_events()

    def action_create_event(self) -> None:
        self.app.notify("Creazione evento: funzionalità in arrivo", timeout=3)

    def action_delete_event(self) -> None:
        self.app.notify("Seleziona un evento per eliminarlo", severity="warning")

    def action_toggle_view(self) -> None:
        views = ["agenda", "settimana", "mese"]
        idx = views.index(self.current_view)
        self.current_view = views[(idx + 1) % len(views)]
        labels = {
            "agenda": "[Agenda]  Settimana  Mese",
            "settimana": "Agenda  [Settimana]  Mese",
            "mese": "Agenda  Settimana  [Mese]",
        }
        self.query_one("#calendar-view-selector", Static).update(labels[self.current_view])
