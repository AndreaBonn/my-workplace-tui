from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.gmail import EmailMessage
from workspace_tui.utils.date_utils import format_relative, parse_date
from workspace_tui.utils.text_utils import truncate


class EmailSelected(Message):
    def __init__(self, message: EmailMessage) -> None:
        self.message = message
        super().__init__()


class EmailListItem(ListItem):
    def __init__(self, message: EmailMessage, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        m = self.message
        indicator = " ● " if m.is_unread else "   "
        star = " ★" if m.is_starred else ""
        from_display = truncate(m.header.from_address, max_length=25)
        subject_display = truncate(m.header.subject, max_length=40)

        date_str = ""
        dt = parse_date(m.header.date)
        if dt:
            date_str = format_relative(dt)

        line = f"{indicator}{from_display}{star}\n   {subject_display}  {date_str}"
        yield Static(line)


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
