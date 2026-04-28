from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.gmail import EmailMessage
from workspace_tui.utils.date_utils import format_relative, parse_date
from workspace_tui.utils.text_utils import truncate

FROM_COL_WIDTH = 22
DATE_COL_WIDTH = 14


class EmailSelected(Message):
    def __init__(self, message: EmailMessage) -> None:
        self.message = message
        super().__init__()


def _extract_sender_name(from_address: str) -> str:
    """Extract display name from 'Name <email>' format, fallback to email user."""
    if "<" in from_address:
        name = from_address.split("<")[0].strip().strip('"')
        if name:
            return name
    if "@" in from_address:
        return from_address.split("@")[0]
    return from_address


class EmailListItem(ListItem):
    def __init__(self, message: EmailMessage, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        if message.is_unread:
            self.add_class("unread")

    def compose(self) -> ComposeResult:
        m = self.message
        is_unread = m.is_unread
        base_style = "bold" if is_unread else ""
        muted_style = "dim" if not is_unread else ""

        sender_name = truncate(
            _extract_sender_name(m.header.from_address),
            max_length=FROM_COL_WIDTH,
        )

        dt = parse_date(m.header.date)
        date_str = format_relative(dt) if dt else ""

        subject_display = m.header.subject or "(nessun oggetto)"
        snippet = m.snippet or ""

        content = Text()
        if is_unread:
            content.append(" ● ", style="bold dodger_blue1")
        else:
            content.append("   ")
        if m.is_starred:
            content.append("★ ", style="yellow")
        else:
            content.append("  ")
        content.append(sender_name.ljust(FROM_COL_WIDTH), style=base_style)
        content.append("  ")
        content.append(date_str.rjust(DATE_COL_WIDTH), style="italic " + muted_style)

        content.append("\n")

        content.append("     ")
        remaining_width = max(10, FROM_COL_WIDTH + DATE_COL_WIDTH + 2)
        subj_text = truncate(subject_display, max_length=remaining_width)
        content.append(subj_text, style=base_style)
        if snippet and len(subj_text) < remaining_width - 5:
            snip = truncate(snippet, max_length=remaining_width - len(subj_text) - 3)
            content.append(f" — {snip}", style="dim italic")

        yield Static(content)


class EmailListView(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Giù", show=False),
        Binding("k", "cursor_up", "Su", show=False),
    ]

    messages: reactive[list[EmailMessage]] = reactive(list, init=False)

    def set_messages(self, messages: list[EmailMessage]) -> None:
        self.clear()
        self.messages = messages
        for msg in messages:
            self.append(EmailListItem(message=msg))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, EmailListItem):
            self.post_message(EmailSelected(message=event.item.message))
