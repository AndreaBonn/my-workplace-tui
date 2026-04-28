from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.drive import DriveFile, DriveService
from workspace_tui.utils.text_utils import format_size


class FileSelected(Message):
    def __init__(self, file: DriveFile) -> None:
        self.file = file
        super().__init__()


class FileItem(ListItem):
    def __init__(self, file: DriveFile, **kwargs) -> None:
        super().__init__(**kwargs)
        self.file = file

    def compose(self) -> ComposeResult:
        size_str = f"  {format_size(self.file.size)}" if self.file.size else ""
        yield Static(f"{self.file.icon} {self.file.name}{size_str}")


class DriveTab(Vertical):
    BINDINGS = [
        Binding("enter", "open_file", "Apri", show=True),
        Binding("backspace", "go_up", "Su", show=True),
        Binding("d", "download", "Scarica", show=True),
        Binding("u", "upload", "Carica", show=False),
        Binding("R", "view_recent", "Recenti", show=True),
        Binding("S", "view_shared", "Condivisi", show=False),
        Binding("M", "view_root", "Il mio Drive", show=False),
        Binding("slash", "search_drive", "Cerca", show=True),
    ]

    drive_service: reactive[DriveService | None] = reactive(None, init=False)
    current_folder: reactive[str] = reactive("root")
    folder_stack: reactive[list[str]] = reactive(list, init=False)
    selected_file: reactive[DriveFile | None] = reactive(None, init=False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="drive-layout"):
            with Vertical(id="drive-browser"):
                yield Static("Il mio Drive", id="drive-breadcrumb", classes="panel-title")
                yield ListView(id="drive-file-list")
            with Vertical(id="drive-detail"):
                yield Static("Seleziona un file", id="drive-file-detail")

    def set_service(self, service: DriveService) -> None:
        self.drive_service = service
        self._load_files()

    def _load_files(self, folder_id: str = "root") -> None:
        self.current_folder = folder_id
        if not self.drive_service:
            return
        self.app.run_worker(lambda: self._load_files_worker(folder_id), thread=True)

    async def _load_files_worker(self, folder_id: str) -> None:
        if not self.drive_service:
            return
        files, _next = self.drive_service.list_files(folder_id=folder_id)
        file_list = self.query_one("#drive-file-list", ListView)
        file_list.clear()
        for f in files:
            file_list.append(FileItem(file=f))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, FileItem):
            return
        file = event.item.file
        self.selected_file = file
        self._update_detail(file)

        if file.is_folder:
            self.folder_stack = [*self.folder_stack, self.current_folder]
            self._load_files(file.file_id)

    def _update_detail(self, file: DriveFile) -> None:
        detail = self.query_one("#drive-file-detail", Static)
        size_str = format_size(file.size) if file.size else "-"
        detail.update(
            f"Nome:    {file.name}\n"
            f"Tipo:    {file.mime_type}\n"
            f"Dim.:    {size_str}\n"
            f"Modif.:  {file.modified_time}\n"
            f"Prop.:   {file.owner}\n\n"
            f"[Invio] Apri  [d] Download  [Backspace] Indietro"
        )

    def action_open_file(self) -> None:
        if self.selected_file and self.selected_file.is_folder:
            self.folder_stack = [*self.folder_stack, self.current_folder]
            self._load_files(self.selected_file.file_id)

    def action_go_up(self) -> None:
        if self.folder_stack:
            parent = self.folder_stack[-1]
            self.folder_stack = self.folder_stack[:-1]
            self._load_files(parent)

    def action_download(self) -> None:
        if not self.selected_file or not self.drive_service:
            self.app.notify("Seleziona un file", severity="warning")
            return
        file = self.selected_file
        dest = Path.home() / "Downloads"
        dest.mkdir(exist_ok=True)
        self.app.run_worker(
            lambda: self.drive_service.download_file(
                file_id=file.file_id,
                dest_dir=dest,
                filename=file.name,
            ),
            thread=True,
        )
        self.app.notify(f"Download di {file.name} in ~/Downloads/")

    def action_upload(self) -> None:
        self.app.notify("Upload: inserisci percorso file", timeout=3)

    def action_view_recent(self) -> None:
        if not self.drive_service:
            return
        self.app.run_worker(self._load_recent, thread=True)

    async def _load_recent(self) -> None:
        if not self.drive_service:
            return
        files = self.drive_service.list_recent()
        file_list = self.query_one("#drive-file-list", ListView)
        file_list.clear()
        for f in files:
            file_list.append(FileItem(file=f))
        self.query_one("#drive-breadcrumb", Static).update("Recenti")

    def action_view_shared(self) -> None:
        if not self.drive_service:
            return
        self.app.run_worker(self._load_shared, thread=True)

    async def _load_shared(self) -> None:
        if not self.drive_service:
            return
        files = self.drive_service.list_shared()
        file_list = self.query_one("#drive-file-list", ListView)
        file_list.clear()
        for f in files:
            file_list.append(FileItem(file=f))
        self.query_one("#drive-breadcrumb", Static).update("Condivisi con me")

    def action_view_root(self) -> None:
        self.folder_stack = []
        self._load_files("root")
        self.query_one("#drive-breadcrumb", Static).update("Il mio Drive")

    def action_search_drive(self) -> None:
        self.app.notify("Ricerca Drive: funzionalità in arrivo", timeout=3)
