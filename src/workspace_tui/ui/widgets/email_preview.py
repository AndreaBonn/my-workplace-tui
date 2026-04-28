from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.gmail import EmailMessage
from workspace_tui.utils.text_utils import format_size, html_to_text, strip_quoted_text


class EmailPreview(VerticalScroll):
    message: reactive[EmailMessage | None] = reactive(None)
    thread_messages: reactive[list[EmailMessage]] = reactive(list, init=False)

    def compose(self) -> ComposeResult:
        yield Static("", id="preview-headers")
        yield Static("", id="preview-body", markup=False)
        yield Static("", id="preview-attachments")

    def watch_message(self, message: EmailMessage | None) -> None:
        self.clear_thread()
        if message is None:
            self.query_one("#preview-headers", Static).update("")
            self.query_one("#preview-body", Static).update("Seleziona un'email per visualizzarla")
            self.query_one("#preview-attachments", Static).update("")
            return

        h = message.header
        headers = Text()
        headers.append("Da:  ", style="bold")
        headers.append(f"{h.from_address}\n")
        headers.append("A:   ", style="bold")
        headers.append(f"{h.to_address}\n")
        if h.cc_address:
            headers.append("CC:  ", style="bold")
            headers.append(f"{h.cc_address}\n")
        headers.append("Data: ", style="bold")
        headers.append(f"{h.date}\n")
        headers.append("Oggetto: ", style="bold")
        headers.append(h.subject)

        body = message.body_text
        if not body and message.body_html:
            body = html_to_text(message.body_html)
        if not body:
            body = message.snippet or "(nessun contenuto)"

        att_text = Text()
        if message.attachments:
            att_text.append("Allegati:\n", style="bold")
            for att in message.attachments:
                att_text.append(f"  📎 {att.filename} ({format_size(att.size)})\n")

        self.query_one("#preview-headers", Static).update(headers)
        self.query_one("#preview-body", Static).update(body)
        self.query_one("#preview-attachments", Static).update(att_text)

    def show_thread(self, messages: list[EmailMessage]) -> None:
        """Display all thread messages chronologically (oldest first)."""
        self.thread_messages = messages
        self._render_thread(messages)

    def _render_thread(self, messages: list[EmailMessage]) -> None:
        for widget in self.query(".thread-message"):
            widget.remove()

        self.query_one("#preview-headers", Static).update("")
        self.query_one("#preview-body", Static).update("")
        self.query_one("#preview-attachments", Static).update("")

        if not messages:
            self.query_one("#preview-body", Static).update("Thread vuoto")
            return

        for i, msg in enumerate(messages):
            content = self._format_thread_message(msg, index=i, total=len(messages))
            widget = Static(content, classes="thread-message")
            self.mount(widget)

        self.call_after_refresh(self.scroll_end, animate=False)

    def _format_thread_message(self, msg: EmailMessage, index: int, total: int) -> Text:
        h = msg.header
        text = Text()

        # Separator between messages
        if index > 0:
            text.append(f"{'─' * 60}\n", style="dim")

        # Message counter + sender
        text.append(f"[{index + 1}/{total}] ", style="bold cyan")
        text.append(f"{h.from_address}\n", style="bold")

        # Date
        text.append("  📅 ", style="dim")
        text.append(f"{h.date}\n", style="dim")

        # Recipients (compact)
        if h.to_address:
            text.append("  → ", style="dim")
            text.append(f"{h.to_address}\n", style="dim")
        if h.cc_address:
            text.append("  CC: ", style="dim")
            text.append(f"{h.cc_address}\n", style="dim")

        text.append("\n")

        # Body — strip quoted text since previous messages are shown above
        body = msg.body_text
        if not body and msg.body_html:
            body = html_to_text(msg.body_html)
        if not body:
            body = msg.snippet or "(nessun contenuto)"

        # Strip quotes for all messages except the first (oldest)
        if index > 0:
            body = strip_quoted_text(body)
            if not body.strip():
                body = "(solo testo quotato)"

        text.append(body)
        text.append("\n")

        # Attachments
        if msg.attachments:
            text.append("\n")
            for att in msg.attachments:
                text.append(f"  📎 {att.filename} ({format_size(att.size)})\n", style="italic")

        return text

    def clear_thread(self) -> None:
        """Remove thread view and restore single-message mode."""
        for widget in self.query(".thread-message"):
            widget.remove()
        self.thread_messages = []
