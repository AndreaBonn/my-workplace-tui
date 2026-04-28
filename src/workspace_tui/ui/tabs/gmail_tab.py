from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.gmail import EmailMessage, GmailLabel, GmailService
from workspace_tui.ui.widgets.compose_modal import ComposeData, ComposeModal
from workspace_tui.ui.widgets.email_list import EmailListView, EmailSelected
from workspace_tui.ui.widgets.email_preview import EmailPreview


class FolderItem(ListItem):
    def __init__(self, label: GmailLabel, **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        unread = f" ({self.label.unread_count})" if self.label.unread_count > 0 else ""
        yield Static(f"{self.label.name}{unread}")


class GmailTab(Vertical):
    BINDINGS = [
        Binding("c", "compose", "Componi", show=True),
        Binding("r", "reply", "Rispondi", show=True),
        Binding("R", "reply_all", "Rispondi tutti", show=False),
        Binding("f", "forward", "Inoltra", show=False),
        Binding("d", "trash", "Cestina", show=True),
        Binding("e", "archive", "Archivia", show=False),
        Binding("m", "toggle_read", "Letto/Non letto", show=False),
        Binding("s", "toggle_star", "Stella", show=False),
        Binding("slash", "search", "Cerca", show=True),
        Binding("a", "download_attachment", "Scarica allegato", show=False),
    ]

    gmail_service: reactive[GmailService | None] = reactive(None, init=False)
    current_label: reactive[str] = reactive("INBOX", init=False)
    selected_message: reactive[EmailMessage | None] = reactive(None, init=False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="gmail-layout"):
            with Vertical(id="gmail-folders", classes="gmail-panel"):
                yield Static("Cartelle", classes="panel-title")
                yield ListView(id="folder-list")
            with Vertical(id="gmail-messages", classes="gmail-panel"):
                yield Static("Email", classes="panel-title")
                yield EmailListView(id="email-list")
            with Vertical(id="gmail-preview", classes="gmail-panel"):
                yield EmailPreview(id="email-preview")

    def set_service(self, service: GmailService) -> None:
        self.gmail_service = service
        self.load_labels()

    def load_labels(self) -> None:
        if not self.gmail_service:
            return
        self.app.run_worker(self._load_labels_worker, thread=True)

    def _load_labels_worker(self) -> None:
        if not self.gmail_service:
            return
        labels = self.gmail_service.list_labels()
        system_order = ["INBOX", "SENT", "DRAFT", "STARRED", "IMPORTANT", "SPAM", "TRASH"]
        system_labels = []
        user_labels = []
        for label in labels:
            if label.label_id in system_order:
                system_labels.append(label)
            elif label.label_type == "user":
                user_labels.append(label)

        system_labels.sort(
            key=lambda lbl: (
                system_order.index(lbl.label_id) if lbl.label_id in system_order else 999
            )
        )

        sorted_labels = system_labels + user_labels
        self.app.call_from_thread(self._update_folder_list, sorted_labels)
        self.app.call_from_thread(self.load_messages)

    def _update_folder_list(self, labels: list[GmailLabel]) -> None:
        folder_list = self.query_one("#folder-list", ListView)
        folder_list.clear()
        for label in labels:
            folder_list.append(FolderItem(label=label))

    def load_messages(self) -> None:
        if not self.gmail_service:
            return
        self.app.run_worker(self._load_messages_worker, thread=True)

    def _load_messages_worker(self) -> None:
        if not self.gmail_service:
            return
        messages, _ = self.gmail_service.list_messages(label_id=self.current_label)
        self.app.call_from_thread(self._update_message_list, messages)

    def _update_message_list(self, messages: list[EmailMessage]) -> None:
        email_list = self.query_one("#email-list", EmailListView)
        email_list.set_messages(messages)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, FolderItem):
            self.current_label = event.item.label.label_id
            self.load_messages()

    def on_email_selected(self, event: EmailSelected) -> None:
        if not self.gmail_service:
            return
        msg_id = event.message.message_id
        self.app.run_worker(lambda: self._load_preview_worker(msg_id), thread=True)

    def _load_preview_worker(self, message_id: str) -> None:
        if not self.gmail_service:
            return
        full_msg = self.gmail_service.get_message(message_id)
        if full_msg:
            self.app.call_from_thread(self._update_preview, full_msg)
            if full_msg.is_unread:
                self.gmail_service.toggle_read(message_id, is_unread=True)

    def _update_preview(self, msg: EmailMessage) -> None:
        self.selected_message = msg
        preview = self.query_one("#email-preview", EmailPreview)
        preview.message = msg

    def action_compose(self) -> None:
        self.app.push_screen(
            ComposeModal(title="Nuova email"),
            callback=self._handle_compose_result,
        )

    def action_reply(self) -> None:
        msg = self.selected_message
        if not msg:
            self.app.notify("Seleziona un'email", severity="warning")
            return
        self.app.push_screen(
            ComposeModal(
                to=msg.header.from_address,
                subject=f"Re: {msg.header.subject}",
                body=f"\n\n--- Messaggio originale ---\n{msg.body_text or msg.snippet}",
                title="Rispondi",
            ),
            callback=self._handle_compose_result,
        )

    def action_reply_all(self) -> None:
        msg = self.selected_message
        if not msg:
            self.app.notify("Seleziona un'email", severity="warning")
            return
        cc_parts = [msg.header.from_address]
        if msg.header.cc_address:
            cc_parts.append(msg.header.cc_address)
        self.app.push_screen(
            ComposeModal(
                to=msg.header.to_address,
                cc=", ".join(cc_parts),
                subject=f"Re: {msg.header.subject}",
                body=f"\n\n--- Messaggio originale ---\n{msg.body_text or msg.snippet}",
                title="Rispondi a tutti",
            ),
            callback=self._handle_compose_result,
        )

    def action_forward(self) -> None:
        msg = self.selected_message
        if not msg:
            self.app.notify("Seleziona un'email", severity="warning")
            return
        self.app.push_screen(
            ComposeModal(
                subject=f"Fwd: {msg.header.subject}",
                body=f"\n\n--- Messaggio inoltrato ---\n"
                f"Da: {msg.header.from_address}\n"
                f"Data: {msg.header.date}\n\n"
                f"{msg.body_text or msg.snippet}",
                title="Inoltra",
            ),
            callback=self._handle_compose_result,
        )

    def _handle_compose_result(self, result: ComposeData | None) -> None:
        if result is None or not self.gmail_service:
            return
        if result.save_draft:
            self.app.run_worker(
                lambda: self.gmail_service.create_draft(
                    to=result.to,
                    subject=result.subject,
                    body=result.body,
                    cc=result.cc,
                ),
                thread=True,
            )
            self.app.notify("Bozza salvata")
        else:
            self.app.run_worker(
                lambda: self.gmail_service.send_message(
                    to=result.to,
                    subject=result.subject,
                    body=result.body,
                    cc=result.cc,
                ),
                thread=True,
            )
            self.app.notify("Email inviata")

    def action_trash(self) -> None:
        msg = self.selected_message
        if not msg or not self.gmail_service:
            return
        self.app.run_worker(
            lambda: self.gmail_service.trash_message(msg.message_id),
            thread=True,
        )
        self.app.notify("Email spostata nel cestino")

    def action_archive(self) -> None:
        msg = self.selected_message
        if not msg or not self.gmail_service:
            return
        self.app.run_worker(
            lambda: self.gmail_service.archive_message(msg.message_id),
            thread=True,
        )
        self.app.notify("Email archiviata")

    def action_toggle_read(self) -> None:
        msg = self.selected_message
        if not msg or not self.gmail_service:
            return
        self.app.run_worker(
            lambda: self.gmail_service.toggle_read(msg.message_id, is_unread=msg.is_unread),
            thread=True,
        )

    def action_toggle_star(self) -> None:
        msg = self.selected_message
        if not msg or not self.gmail_service:
            return
        self.app.run_worker(
            lambda: self.gmail_service.toggle_star(msg.message_id, is_starred=msg.is_starred),
            thread=True,
        )

    def action_search(self) -> None:
        self.app.notify("Ricerca: usa / nel campo email", timeout=3)

    def action_download_attachment(self) -> None:
        msg = self.selected_message
        if not msg or not msg.attachments:
            self.app.notify("Nessun allegato", severity="warning")
            return
        self.app.notify(f"{len(msg.attachments)} allegati disponibili", timeout=3)
