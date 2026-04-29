from __future__ import annotations

from rich.text import Text
from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.search import (
    SOURCE_ICONS,
    SOURCE_LABELS,
    SearchResult,
    SearchSource,
)


class SearchResultItem(ListItem):
    def __init__(self, result: SearchResult, **kwargs) -> None:
        super().__init__(**kwargs)
        self.result = result

    def compose(self):
        icon = SOURCE_ICONS.get(self.result.source, "🔍")
        line = Text()
        line.append(f"{icon} ", style="bold")
        line.append(self.result.title, style="bold")
        line.append(f"\n  {self.result.snippet}", style="dim")
        yield Static(line)


class SourceHeader(ListItem):
    """Non-selectable header separating result groups by source."""

    def __init__(self, source: SearchSource, count: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.source = source
        self._count = count

    def compose(self):
        icon = SOURCE_ICONS.get(self.source, "🔍")
        label = SOURCE_LABELS.get(self.source, self.source.value)
        line = Text()
        line.append(f"── {icon} {label} ", style="bold cyan")
        line.append(f"({self._count})", style="dim cyan")
        line.append(" ──", style="bold cyan")
        yield Static(line)


class SearchResultSelected(Message):
    def __init__(self, result: SearchResult) -> None:
        super().__init__()
        self.result = result


class SearchResultsList(ListView):
    """Grouped list of search results with source headers."""

    def set_results(self, results: list[SearchResult]) -> None:
        self.clear()

        grouped: dict[SearchSource, list[SearchResult]] = {}
        for r in results:
            grouped.setdefault(r.source, []).append(r)

        display_order = [
            SearchSource.GMAIL,
            SearchSource.JIRA,
            SearchSource.DRIVE,
            SearchSource.CHAT,
        ]

        for source in display_order:
            source_results = grouped.get(source)
            if not source_results:
                continue
            self.append(SourceHeader(source=source, count=len(source_results)))
            for result in source_results:
                self.append(SearchResultItem(result=result))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, SearchResultItem):
            self.post_message(SearchResultSelected(result=event.item.result))
        elif isinstance(event.item, SourceHeader):
            event.prevent_default()
