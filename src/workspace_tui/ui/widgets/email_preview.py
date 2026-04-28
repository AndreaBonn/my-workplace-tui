from rich.text import Text
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
        yield Static("", id="preview-body", markup=False)
        yield Static("", id="preview-attachments")

    def watch_message(self, message: EmailMessage | None) -> None:
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
