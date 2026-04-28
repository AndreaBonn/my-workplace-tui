from itertools import groupby

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.calendar import CalendarEvent, CalendarService
from workspace_tui.utils.date_utils import (
    format_day_header,
    format_time,
    is_today,
    is_tomorrow,
    parse_date,
)

LINE_W = 60


def _attendee_name(email: str) -> str:
    """Extract readable name from email: 'mario.rossi@x.it' → 'Mario Rossi'."""
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


def _day_label(dt) -> str:
    header = format_day_header(dt)
    if is_today(dt):
        return f"{header}  (OGGI)"
    if is_tomorrow(dt):
        return f"{header}  (DOMANI)"
    return header


class CalendarTab(Vertical):
    BINDINGS = [
        Binding("h", "prev_period", "Precedente", show=True),
        Binding("l", "next_period", "Successivo", show=True),
        Binding("t", "go_today", "Oggi", show=True),
        Binding("c", "create_event", "Crea evento", show=True),
        Binding("d", "delete_event", "Elimina", show=True),
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

    def reload(self) -> None:
        self._load_events()

    def _load_events(self) -> None:
        if not self.calendar_service:
            return
        self.app.run_worker(self._load_events_worker, thread=True)

    def _load_events_worker(self) -> None:
        if not self.calendar_service:
            return
        events = self.calendar_service.list_events()
        self.app.call_from_thread(self._render_events, events)

    def _render_events(self, events: list[CalendarEvent]) -> None:
        self.events = events
        events_widget = self.query_one("#calendar-events", Static)
        if not events:
            events_widget.update("Nessun evento nei prossimi 30 giorni")
            return

        def _event_date(ev: CalendarEvent) -> str:
            dt = parse_date(ev.start)
            return dt.strftime("%Y-%m-%d") if dt else ""

        lines: list[str] = []
        for day_key, day_events in groupby(events, key=_event_date):
            day_list = list(day_events)
            dt_day = parse_date(day_list[0].start)
            if not dt_day:
                continue

            # Header giorno
            label = _day_label(dt_day)
            lines.append(f"[bold cyan]{'─' * 3} {label} {'─' * (LINE_W - len(label) - 5)}[/]")

            # Prima eventi all-day
            for ev in day_list:
                if ev.all_day:
                    lines.append(f"  [bold yellow]▪ TUTTO IL GIORNO[/]  [bold]{ev.summary}[/]")

            # Poi eventi con orario
            for ev in day_list:
                if ev.all_day:
                    continue
                dt = parse_date(ev.start)
                time_str = format_time(dt) if dt else "??:??"
                # Badges: location e meet
                badges = ""
                if ev.location:
                    badges += f"  [dim]📍 {ev.location}[/]"
                if ev.meet_link:
                    badges += "  [green]🔗 Meet[/]"
                lines.append(f"  [bold cyan]{time_str}[/]  [bold]{ev.summary}[/]{badges}")
                # Partecipanti come nomi leggibili
                if ev.attendees:
                    names = ", ".join(_attendee_name(a) for a in ev.attendees[:4])
                    if len(ev.attendees) > 4:
                        names += f" +{len(ev.attendees) - 4}"
                    lines.append(f"         [dim]👥 {names}[/]")

            lines.append("")  # Riga vuota tra giorni

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
