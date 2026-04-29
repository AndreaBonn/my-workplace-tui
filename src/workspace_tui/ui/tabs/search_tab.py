from __future__ import annotations

from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Input, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.timer import Timer

from workspace_tui.services.search import (
    SOURCE_ICONS,
    SOURCE_LABELS,
    SearchResponse,
    SearchResult,
    SearchService,
    SearchSource,
)
from workspace_tui.ui.widgets.search_results import (
    SearchResultSelected,
    SearchResultsList,
)
from workspace_tui.utils.url_utils import open_google_url

DEBOUNCE_MS = 300


class SearchTab(Vertical):
    BINDINGS = [
        Binding("slash", "focus_search", "Cerca", show=True),
        Binding("o", "open_in_browser", "Apri browser", show=True),
        Binding("enter", "select_result", "Seleziona", show=False),
    ]

    search_service: reactive[SearchService | None] = reactive(None, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._debounce_timer: Timer | None = None
        self._selected_result: SearchResult | None = None
        self._last_response: SearchResponse | None = None

    def compose(self) -> ComposeResult:
        yield Static("🔍 Ricerca Globale", classes="panel-title")
        yield Input(
            placeholder="Cerca in Email, Jira, Drive, Chat...",
            id="search-input",
        )
        with Horizontal(id="search-layout"):
            with Vertical(id="search-results-panel"):
                yield Static("Risultati", classes="panel-title")
                yield SearchResultsList(id="search-results")
            with Vertical(id="search-preview-panel"):
                yield Static("Dettaglio", classes="panel-title")
                yield Static("", id="search-preview")
                yield Static("", id="search-errors")

    def set_service(self, service: SearchService) -> None:
        self.search_service = service

    def reload(self) -> None:
        search_input = self.query_one("#search-input", Input)
        if search_input.value.strip():
            self._execute_search(search_input.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        if self._debounce_timer:
            self._debounce_timer.stop()
        query = event.value.strip()
        if len(query) < 2:
            self._clear_results()
            return
        self._debounce_timer = self.set_timer(
            DEBOUNCE_MS / 1000,
            lambda: self._execute_search(query),
        )

    def _execute_search(self, query: str) -> None:
        if not self.search_service:
            return
        self._show_loading()
        self.app.run_worker(
            lambda: self._search_worker(query),
            thread=True,
        )

    def _search_worker(self, query: str) -> None:
        if not self.search_service:
            return
        try:
            response = self.search_service.search(query)
            self.app.call_from_thread(self._update_results, response)
        except Exception as exc:
            self.app.call_from_thread(self._show_error, f"Errore ricerca: {exc}")

    def _show_error(self, message: str) -> None:
        preview = self.query_one("#search-preview", Static)
        preview.update(message)

    def _update_results(self, response: SearchResponse) -> None:
        self._last_response = response

        results_list = self.query_one("#search-results", SearchResultsList)
        results_list.set_results(response.results)

        total = len(response.results)
        sources_hit = len({r.source for r in response.results})
        status = f"Risultati: {total} da {sources_hit} fonti"
        if not response.results:
            status = f'Nessun risultato per "{response.query}"'

        preview = self.query_one("#search-preview", Static)
        preview.update(status)

        errors_widget = self.query_one("#search-errors", Static)
        if response.errors:
            error_lines = []
            for source, error in response.errors.items():
                icon = SOURCE_ICONS.get(source, "❌")
                label = SOURCE_LABELS.get(source, source.value)
                error_lines.append(f"{icon} {label}: {error}")
            errors_widget.update("\n".join(error_lines))
        else:
            errors_widget.update("")

    def _show_loading(self) -> None:
        preview = self.query_one("#search-preview", Static)
        preview.update("⏳ Ricerca in corso...")

    def _clear_results(self) -> None:
        results_list = self.query_one("#search-results", SearchResultsList)
        results_list.clear()
        preview = self.query_one("#search-preview", Static)
        preview.update("Digita almeno 2 caratteri per cercare")
        errors_widget = self.query_one("#search-errors", Static)
        errors_widget.update("")
        self._selected_result = None

    def on_search_result_selected(self, event: SearchResultSelected) -> None:
        self._selected_result = event.result
        self._show_result_detail(event.result)

    def _show_result_detail(self, result: SearchResult) -> None:
        icon = SOURCE_ICONS.get(result.source, "🔍")
        label = SOURCE_LABELS.get(result.source, result.source.value)

        lines = [
            f"{icon} [{label}]",
            "",
            f"  {result.title}",
            "",
            f"  {result.snippet}",
        ]
        if result.timestamp:
            lines.append(f"\n  📅 {result.timestamp}")
        if result.url:
            lines.append(f"  🔗 {result.url}")
        lines.append(f"\n  ID: {result.identifier}")

        preview = self.query_one("#search-preview", Static)
        preview.update("\n".join(lines))

    def _get_account_email(self) -> str:
        return (
            getattr(self.app, "settings", None) and self.app.settings.google_account_email
        ) or ""

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_open_in_browser(self) -> None:
        result = self._selected_result
        if not result or not result.url:
            self.app.notify("Nessun link disponibile", severity="warning")
            return
        email = self._get_account_email()
        open_google_url(result.url, google_account_email=email)
        self.app.notify("Aperto nel browser", timeout=2)

    def action_select_result(self) -> None:
        result = self._selected_result
        if not result:
            return
        self._navigate_to_source(result)

    def _navigate_to_source(self, result: SearchResult) -> None:
        """Switch to the source tab for the selected result."""
        tab_map = {
            SearchSource.GMAIL: "gmail",
            SearchSource.JIRA: "jira",
            SearchSource.DRIVE: "drive",
            SearchSource.CHAT: "chat",
        }
        tab_id = tab_map.get(result.source)
        if tab_id:
            self.app.action_switch_tab(tab_id)
