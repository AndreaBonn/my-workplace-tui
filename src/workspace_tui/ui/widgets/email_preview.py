from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.gmail import EmailMessage
from workspace_tui.utils.text_utils import format_size, html_to_text


class EmailPreview(VerticalScroll):
    message: reactive[EmailMessage | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("", id="preview-headers")
        yield Static("", id="preview-body")
        yield Static("", id="preview-attachments")

    def watch_message(self, message: EmailMessage | None) -> None:
        if message is None:
            self.query_one("#preview-headers", Static).update("")
            self.query_one("#preview-body", Static).update("Seleziona un'email per visualizzarla")
            self.query_one("#preview-attachments", Static).update("")
            return

        h = message.header
        headers_text = f"Da: {h.from_address}\nA: {h.to_address}\n"
        if h.cc_address:
            headers_text += f"CC: {h.cc_address}\n"
        headers_text += f"Data: {h.date}\nOggetto: {h.subject}"

        body = message.body_text
        if not body and message.body_html:
            body = html_to_text(message.body_html)
        if not body:
            body = message.snippet or "(nessun contenuto)"

        attachments_text = ""
        if message.attachments:
            lines = ["Allegati:"]
            for att in message.attachments:
                lines.append(f"  📎 {att.filename} ({format_size(att.size)})")
            attachments_text = "\n".join(lines)

        self.query_one("#preview-headers", Static).update(headers_text)
        self.query_one("#preview-body", Static).update(body)
        self.query_one("#preview-attachments", Static).update(attachments_text)
