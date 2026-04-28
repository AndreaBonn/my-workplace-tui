from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.gmail import EmailMessage
from workspace_tui.utils.text_utils import format_size, html_to_text


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
        # Remove existing dynamic thread widgets
        for widget in self.query(".thread-message"):
            widget.remove()

        # Hide single-message widgets
        self.query_one("#preview-headers", Static).update("")
        self.query_one("#preview-body", Static).update("")
        self.query_one("#preview-attachments", Static).update("")

        if not messages:
            self.query_one("#preview-body", Static).update("Thread vuoto")
            return

        # Build full thread content as a single Text block for headers
        # and a single string for bodies — mount Static per message
        for i, msg in enumerate(messages):
            content = self._format_thread_message(msg, index=i, total=len(messages))
            widget = Static(content, classes="thread-message", markup=False)
            self.mount(widget)

        # Scroll to bottom after mount completes
        self.call_after_refresh(self.scroll_end, animate=False)

    def _format_thread_message(self, msg: EmailMessage, index: int, total: int) -> str:
        h = msg.header
        separator = f"{'─' * 60}\n" if index > 0 else ""
        header_block = f"{separator}[{index + 1}/{total}] Da: {h.from_address}\nData: {h.date}\n"
        if h.to_address:
            header_block += f"A: {h.to_address}\n"
        if h.cc_address:
            header_block += f"CC: {h.cc_address}\n"

        body = msg.body_text
        if not body and msg.body_html:
            body = html_to_text(msg.body_html)
        if not body:
            body = msg.snippet or "(nessun contenuto)"

        att_block = ""
        if msg.attachments:
            att_names = ", ".join(
                f"📎 {a.filename} ({format_size(a.size)})" for a in msg.attachments
            )
            att_block = f"\nAllegati: {att_names}\n"

        return f"{header_block}\n{body}{att_block}\n"

    def clear_thread(self) -> None:
        """Remove thread view and restore single-message mode."""
        for widget in self.query(".thread-message"):
            widget.remove()
        self.thread_messages = []
