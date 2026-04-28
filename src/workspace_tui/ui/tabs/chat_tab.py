from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, ListItem, ListView, Static

from workspace_tui.services.chat import ChatMessage, ChatService, ChatSpace
from workspace_tui.utils.date_utils import format_relative, parse_date

CHAT_UNAVAILABLE_MESSAGE = (
    "Google Chat API non disponibile.\n"
    "L'admin del Workspace deve abilitare Google Chat API.\n"
    "Le altre tab funzionano normalmente."
)


class SpaceItem(ListItem):
    def __init__(self, space: ChatSpace, **kwargs) -> None:
        super().__init__(**kwargs)
        self.space = space

    def compose(self) -> ComposeResult:
        prefix = "💬" if self.space.is_dm else "🏠"
        yield Static(f"{prefix} {self.space.display_name}")


class ChatTab(Vertical):
    BINDINGS = [
        Binding("i", "focus_input", "Scrivi", show=True),
        Binding("g", "scroll_top", "Inizio", show=False),
        Binding("G", "scroll_bottom", "Fine", show=False),
    ]

    chat_service: reactive[ChatService | None] = reactive(None, init=False)
    current_space: reactive[str] = reactive("")
    chat_available: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        with Horizontal(id="chat-layout"):
            with Vertical(id="chat-spaces"):
                yield Static("Messaggi diretti", classes="panel-title")
                yield ListView(id="space-list")
            with Vertical(id="chat-conversation"):
                yield VerticalScroll(Static("Seleziona una conversazione", id="chat-messages"))
                yield Input(placeholder="Scrivi un messaggio...", id="chat-input")

    def set_service(self, service: ChatService) -> None:
        self.chat_service = service
        self._load_spaces()

    def _load_spaces(self) -> None:
        if not self.chat_service:
            return
        self.app.run_worker(self._load_spaces_worker, thread=True)

    async def _load_spaces_worker(self) -> None:
        if not self.chat_service:
            return
        try:
            spaces = self.chat_service.list_spaces()
            dm_spaces = [s for s in spaces if s.is_dm]
            group_spaces = [s for s in spaces if not s.is_dm]

            space_list = self.query_one("#space-list", ListView)
            space_list.clear()
            for space in dm_spaces + group_spaces:
                space_list.append(SpaceItem(space=space))
        except Exception:
            self.chat_available = False
            messages_widget = self.query_one("#chat-messages", Static)
            messages_widget.update(CHAT_UNAVAILABLE_MESSAGE)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, SpaceItem) or not self.chat_service:
            return
        self.current_space = event.item.space.name
        self.app.run_worker(
            lambda: self._load_messages(event.item.space.name),
            thread=True,
        )

    async def _load_messages(self, space_name: str) -> None:
        if not self.chat_service:
            return
        messages = self.chat_service.list_messages(space_name)
        self._render_messages(messages)

    def _render_messages(self, messages: list[ChatMessage]) -> None:
        widget = self.query_one("#chat-messages", Static)
        if not messages:
            widget.update("Nessun messaggio")
            return

        lines = []
        for msg in messages:
            dt = parse_date(msg.create_time)
            time_str = format_relative(dt) if dt else ""
            lines.append(f"{msg.sender_display_name} — {time_str}")
            lines.append(f"  {msg.text}")
            lines.append("")

        widget.update("\n".join(lines))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input" or not self.current_space or not self.chat_service:
            return
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        space = self.current_space
        self.app.run_worker(
            lambda: self.chat_service.send_message(space_name=space, text=text),
            thread=True,
        )

    def action_focus_input(self) -> None:
        self.query_one("#chat-input", Input).focus()

    def action_scroll_top(self) -> None:
        self.query_one("#chat-messages").scroll_home()

    def action_scroll_bottom(self) -> None:
        self.query_one("#chat-messages").scroll_end()
