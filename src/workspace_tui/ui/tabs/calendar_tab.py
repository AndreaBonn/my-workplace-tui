from itertools import groupby

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

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


def _render_event_label(ev: CalendarEvent) -> str:
    """Build Rich markup label for a single event."""
    dt = parse_date(ev.start)

    if ev.all_day:
        return f"[bold yellow]▪ TUTTO IL GIORNO[/]  [bold]{ev.summary}[/]"

    time_str = format_time(dt) if dt else "??:??"

    badges = ""
    if ev.location:
        badges += f"  [dim]📍 {ev.location}[/]"
    if ev.meet_link:
        badges += "  [green]🔗 Meet[/]"

    line = f"[bold cyan]{time_str}[/]  [bold]{ev.summary}[/]{badges}"

    if ev.attendees:
        names = ", ".join(_attendee_name(a) for a in ev.attendees[:4])
        if len(ev.attendees) > 4:
            names += f" +{len(ev.attendees) - 4}"
        line += f"\n       [dim]👥 {names}[/]"

    if ev.description:
        line += "  [dim italic]📝[/]"

    return line


class EventItem(ListItem):
    """Selectable calendar event item."""

    def __init__(self, event: CalendarEvent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event = event

    def compose(self) -> ComposeResult:
        yield Static(_render_event_label(self.event), markup=True)


class DayHeader(ListItem):
    """Non-interactive day separator."""

    DEFAULT_CSS = """
    DayHeader {
        height: 2;
    }
    """

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(disabled=True, **kwargs)
        self.day_label = label

    def compose(self) -> ComposeResult:
        separator = "─" * 3
        trail = "─" * (LINE_W - len(self.day_label) - 5)
        yield Static(
            f"\n[bold cyan]{separator} {self.day_label} {trail}[/]",
            markup=True,
        )


class CalendarTab(Vertical):
    BINDINGS = [
        Binding("h", "prev_period", "Precedente", show=True),
        Binding("l", "next_period", "Successivo", show=True),
        Binding("t", "go_today", "Oggi", show=True),
        Binding("c", "create_event", "Crea evento", show=True),
        Binding("d", "delete_event", "Elimina", show=True),
        Binding("v", "toggle_view", "Cambia vista", show=True),
        Binding("o", "open_link", "Apri link", show=True),
        Binding("g", "open_calendar_web", "Calendar web", show=True),
        Binding("n", "show_notes", "Note", show=True),
    ]

    calendar_service: reactive[CalendarService | None] = reactive(None, init=False)
    events: reactive[list[CalendarEvent]] = reactive(list, init=False)
    current_view: reactive[str] = reactive("agenda")

    def compose(self) -> ComposeResult:
        with Vertical(id="calendar-layout"):
            yield Static("[Agenda]  Settimana  Mese", id="calendar-view-selector")
            yield ListView(id="calendar-events-list")

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
        event_list = self.query_one("#calendar-events-list", ListView)
        event_list.clear()

        if not events:
            event_list.append(ListItem(Static("Nessun evento nei prossimi 30 giorni")))
            return

        def _event_date(ev: CalendarEvent) -> str:
            dt = parse_date(ev.start)
            return dt.strftime("%Y-%m-%d") if dt else ""

        for _day_key, day_events in groupby(events, key=_event_date):
            day_list = list(day_events)
            dt_day = parse_date(day_list[0].start)
            if not dt_day:
                continue

            # Day header
            event_list.append(DayHeader(label=_day_label(dt_day)))

            # All-day events first, then timed
            for ev in sorted(day_list, key=lambda e: (not e.all_day, e.start)):
                event_list.append(EventItem(event=ev))

    @property
    def _selected_event(self) -> CalendarEvent | None:
        event_list = self.query_one("#calendar-events-list", ListView)
        highlighted = event_list.highlighted_child
        if isinstance(highlighted, EventItem):
            return highlighted.event
        return None

    @property
    def _google_account(self) -> str:
        return (
            getattr(self.app, "settings", None) and self.app.settings.google_account_email
        ) or ""

    def action_open_link(self) -> None:
        ev = self._selected_event
        if not ev:
            return
        from workspace_tui.utils.url_utils import open_google_url

        url = ev.meet_link or ev.html_link
        if url:
            open_google_url(url, google_account_email=self._google_account)
            self.app.notify(f"Aperto: {ev.summary}", timeout=2)
        else:
            self.app.notify("Nessun link per questo evento", severity="warning")

    def action_open_calendar_web(self) -> None:
        from workspace_tui.utils.url_utils import open_google_url

        url = "https://calendar.google.com/calendar/r/week"
        open_google_url(url, google_account_email=self._google_account)

    def action_show_notes(self) -> None:
        ev = self._selected_event
        if not ev:
            return
        if ev.description:
            # Truncate long descriptions for notification
            desc = ev.description[:500]
            if len(ev.description) > 500:
                desc += "…"
            self.app.notify(
                f"[bold]{ev.summary}[/]\n\n{desc}",
                title="📝 Note evento",
                timeout=10,
            )
        else:
            self.app.notify("Nessuna nota per questo evento", severity="warning")

    def action_prev_period(self) -> None:
        self.app.notify("Periodo precedente", timeout=2)

    def action_next_period(self) -> None:
        self.app.notify("Periodo successivo", timeout=2)

    def action_go_today(self) -> None:
        self._load_events()

    def action_create_event(self) -> None:
        from workspace_tui.ui.widgets.event_create_modal import EventCreateModal

        self.app.push_screen(
            EventCreateModal(),
            callback=self._handle_create_result,
        )

    def _handle_create_result(self, result: object) -> None:
        from workspace_tui.ui.widgets.event_create_modal import EventCreateData

        if not isinstance(result, EventCreateData) or not self.calendar_service:
            return

        # Parse date DD/MM/YYYY → ISO format
        try:
            parts = result.date.split("/")
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except (IndexError, ValueError):
            self.app.notify("Formato data non valido (GG/MM/AAAA)", severity="error")
            return

        if result.all_day:
            start = iso_date
            end = iso_date
        else:
            start = f"{iso_date}T{result.start_time}:00"
            end = f"{iso_date}T{result.end_time}:00"

        attendees = [a.strip() for a in result.attendees.split(",") if a.strip()] or None

        def _create() -> None:
            if not self.calendar_service:
                return
            try:
                self.calendar_service.create_event(
                    summary=result.summary,
                    start=start,
                    end=end,
                    location=result.location,
                    description=result.description,
                    attendees=attendees,
                )
                self.app.call_from_thread(
                    self.app.notify, f"Evento creato: {result.summary}", timeout=3
                )
                self.app.call_from_thread(self._load_events)
            except Exception as exc:
                self.app.call_from_thread(self.app.notify, f"Errore: {exc}", severity="error")

        self.app.run_worker(_create, thread=True)

    _pending_delete: CalendarEvent | None = None

    def action_delete_event(self) -> None:
        # Seconda pressione entro 5s = conferma eliminazione
        if self._pending_delete is not None:
            self._do_delete(self._pending_delete)
            self._pending_delete = None
            return

        ev = self._selected_event
        if not ev:
            self.app.notify("Seleziona un evento per eliminarlo", severity="warning")
            return

        self._pending_delete = ev
        self.app.notify(
            f"Eliminare '{ev.summary}'? Premi [bold]d[/] di nuovo per confermare.",
            title="Conferma eliminazione",
            severity="warning",
            timeout=5,
        )
        self.set_timer(delay=5.0, callback=self._reset_pending_delete)

    def _reset_pending_delete(self) -> None:
        self._pending_delete = None

    def _do_delete(self, ev: CalendarEvent) -> None:
        if not self.calendar_service:
            return
        service = self.calendar_service
        summary = ev.summary

        def _delete() -> None:
            try:
                service.delete_event(
                    event_id=ev.event_id,
                    calendar_id=ev.calendar_id or "primary",
                )
                self.app.call_from_thread(self.app.notify, f"Eliminato: {summary}", timeout=3)
                self.app.call_from_thread(self._load_events)
            except Exception as exc:
                self.app.call_from_thread(self.app.notify, f"Errore: {exc}", severity="error")

        self.app.run_worker(_delete, thread=True)

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
