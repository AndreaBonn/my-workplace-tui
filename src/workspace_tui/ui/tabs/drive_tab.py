from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.drive import DriveFile, DriveService, SharedDrive
from workspace_tui.utils.date_utils import format_relative, parse_date
from workspace_tui.utils.text_utils import format_size, mime_to_label

VIEW_HOME = "home"
VIEW_MY_DRIVE = "my_drive"
VIEW_SHARED_DRIVE = "shared_drive"
VIEW_SHARED_WITH_ME = "shared_with_me"
VIEW_RECENT = "recent"


class FileItem(ListItem):
    def __init__(self, file: DriveFile, **kwargs) -> None:
        super().__init__(**kwargs)
        self.file = file

    def compose(self) -> ComposeResult:
        if self.file.is_folder:
            label = f"[bold]{self.file.icon}  {self.file.name}[/bold]"
        else:
            size_str = format_size(self.file.size) if self.file.size else ""
            label = f"{self.file.icon}  {self.file.name}  [dim]{size_str}[/dim]"
        yield Static(label, markup=True)


class NavItem(ListItem):
    """Virtual navigation entry for home view."""

    def __init__(
        self,
        nav_id: str,
        label: str,
        shared_drive: SharedDrive | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.nav_id = nav_id
        self.nav_label = label
        self.shared_drive = shared_drive

    def compose(self) -> ComposeResult:
        yield Static(self.nav_label, markup=True)


class DriveTab(Vertical):
    BINDINGS = [
        Binding("o", "open_selected", "Apri", show=True),
        Binding("b", "go_up", "Indietro", show=True),
        Binding("d", "download", "Scarica", show=True),
        Binding("u", "upload", "Carica", show=True),
        Binding("R", "view_recent", "Recenti", show=True),
        Binding("S", "view_shared", "Condivisi", show=True),
        Binding("M", "view_root", "Il mio Drive", show=True),
        Binding("H", "view_home", "Home", show=True),
    ]

    drive_service: reactive[DriveService | None] = reactive(None, init=False)
    current_view: reactive[str] = reactive(VIEW_HOME)
    current_folder: reactive[str] = reactive("root")
    current_drive_id: reactive[str] = reactive("")
    folder_stack: reactive[list[str]] = reactive(list, init=False)
    selected_file: reactive[DriveFile | None] = reactive(None, init=False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="drive-layout"):
            with Vertical(id="drive-browser"):
                yield Static("Drive", id="drive-breadcrumb", classes="panel-title")
                yield ListView(id="drive-file-list")
            with Vertical(id="drive-detail"):
                yield Static(
                    "[dim]Seleziona un elemento[/dim]",
                    id="drive-file-detail",
                    markup=True,
                )

    def set_service(self, service: DriveService) -> None:
        self.drive_service = service
        self._show_home()

    def reload(self) -> None:
        if self.current_view == VIEW_HOME:
            self._show_home()
        elif self.current_view == VIEW_RECENT:
            self.action_view_recent()
        elif self.current_view == VIEW_SHARED_WITH_ME:
            self.action_view_shared()
        elif self.current_view in (VIEW_MY_DRIVE, VIEW_SHARED_DRIVE):
            self._load_files(self.current_folder)

    # ── Home view ──────────────────────────────────────────────

    def _show_home(self) -> None:
        self.current_view = VIEW_HOME
        self.folder_stack = []
        self.selected_file = None
        self._update_breadcrumb("Drive")
        if not self.drive_service:
            return
        self.app.run_worker(self._build_home_worker, thread=True)

    def _build_home_worker(self) -> None:
        if not self.drive_service:
            return
        shared_drives = self.drive_service.list_shared_drives()
        self.app.call_from_thread(self._render_home, shared_drives)

    def _render_home(self, shared_drives: list[SharedDrive]) -> None:
        file_list = self.query_one("#drive-file-list", ListView)
        file_list.clear()

        file_list.append(
            NavItem(
                nav_id=VIEW_MY_DRIVE,
                label="[bold]🏠  Il mio Drive[/bold]",
            )
        )
        file_list.append(
            NavItem(
                nav_id=VIEW_SHARED_WITH_ME,
                label="[bold]🤝  Condivisi con me[/bold]",
            )
        )
        file_list.append(
            NavItem(
                nav_id=VIEW_RECENT,
                label="[bold]🕐  Recenti[/bold]",
            )
        )

        if shared_drives:
            file_list.append(
                NavItem(
                    nav_id="_separator",
                    label="[dim]── Drive condivisi ──[/dim]",
                )
            )
            for sd in shared_drives:
                file_list.append(
                    NavItem(
                        nav_id=VIEW_SHARED_DRIVE,
                        label=f"[bold]🏢  {sd.name}[/bold]",
                        shared_drive=sd,
                    )
                )

        detail = self.query_one("#drive-file-detail", Static)
        detail.update(
            "[bold]Drive[/bold]\n\n"
            "  Naviga tra i tuoi Drive.\n"
            "  Seleziona una voce per aprirla.\n\n"
            "─" * 36 + "\n\n"
            "  [bold reverse] H [/] Home  "
            "[bold reverse] M [/] Il mio Drive\n"
            "  [bold reverse] S [/] Condivisi  "
            "[bold reverse] R [/] Recenti"
        )

    # ── File listing ───────────────────────────────────────────

    def _load_files(self, folder_id: str = "root") -> None:
        self.current_folder = folder_id
        if not self.drive_service:
            return
        self.app.run_worker(lambda: self._load_files_worker(folder_id), thread=True)

    def _load_files_worker(self, folder_id: str) -> None:
        if not self.drive_service:
            return
        files, _next = self.drive_service.list_files(folder_id=folder_id)
        self.app.call_from_thread(self._update_file_list, files)

    def _update_file_list(self, files: list[DriveFile]) -> None:
        file_list = self.query_one("#drive-file-list", ListView)
        file_list.clear()
        for f in files:
            file_list.append(FileItem(file=f))

    # ── Events ─────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, FileItem):
            self.selected_file = event.item.file
            self._update_detail(event.item.file)
        elif isinstance(event.item, NavItem):
            self.selected_file = None
            self._update_nav_detail(event.item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, NavItem):
            self._handle_nav_selected(event.item)
        elif isinstance(event.item, FileItem):
            self._handle_file_selected(event.item.file)

    def _handle_nav_selected(self, item: NavItem) -> None:
        if item.nav_id == "_separator":
            return
        if item.nav_id == VIEW_MY_DRIVE:
            self.current_view = VIEW_MY_DRIVE
            self.current_drive_id = ""
            self.folder_stack = []
            self._update_breadcrumb("Il mio Drive")
            self._load_files("root")
        elif item.nav_id == VIEW_SHARED_WITH_ME:
            self.action_view_shared()
        elif item.nav_id == VIEW_RECENT:
            self.action_view_recent()
        elif item.nav_id == VIEW_SHARED_DRIVE and item.shared_drive:
            self.current_view = VIEW_SHARED_DRIVE
            self.current_drive_id = item.shared_drive.drive_id
            self.folder_stack = []
            self._update_breadcrumb(item.shared_drive.name)
            self._load_files(item.shared_drive.drive_id)

    def _handle_file_selected(self, file: DriveFile) -> None:
        if file.is_folder:
            self.folder_stack = [*self.folder_stack, self.current_folder]
            self._load_files(file.file_id)
            self._update_breadcrumb(file.name)

    # ── Detail panel ───────────────────────────────────────────

    def _format_modified_time(self, raw_time: str) -> str:
        dt = parse_date(raw_time)
        if dt:
            return format_relative(dt)
        return raw_time if raw_time else "-"

    def _update_detail(self, file: DriveFile) -> None:
        detail = self.query_one("#drive-file-detail", Static)
        size_str = format_size(file.size) if file.size else "-"
        type_label = mime_to_label(file.mime_type)
        modified = self._format_modified_time(file.modified_time)

        lines = [
            f"[bold]{file.icon}  {file.name}[/bold]",
            "",
            f"  [dim]Tipo[/dim]     {type_label}",
            f"  [dim]Dim.[/dim]     {size_str}",
            f"  [dim]Modifica[/dim] {modified}",
            f"  [dim]Propri.[/dim]  {file.owner}",
            "",
            "─" * 36,
            "",
            "  [bold reverse] o [/] Apri    [bold reverse] d [/] Download",
            "  [bold reverse] b [/] Indietro  [bold reverse] H [/] Home",
            "",
            "  [bold reverse] R [/] Recenti "
            "[bold reverse] S [/] Condivisi "
            "[bold reverse] M [/] Root",
        ]
        detail.update("\n".join(lines))

    def _update_nav_detail(self, item: NavItem) -> None:
        detail = self.query_one("#drive-file-detail", Static)
        descriptions = {
            VIEW_MY_DRIVE: "File e cartelle nel tuo Drive personale.",
            VIEW_SHARED_WITH_ME: "File e cartelle condivisi da altri con te.",
            VIEW_RECENT: "File aperti o modificati di recente.",
            VIEW_SHARED_DRIVE: "",
        }
        desc = descriptions.get(item.nav_id, "")
        if item.nav_id == VIEW_SHARED_DRIVE and item.shared_drive:
            desc = f"Drive condiviso del team: {item.shared_drive.name}"
        if item.nav_id == "_separator":
            return
        detail.update(
            f"[bold]{item.nav_label}[/bold]\n\n  {desc}\n\n  Premi [bold]Invio[/bold] per aprire."
        )

    # ── Actions ────────────────────────────────────────────────

    def action_open_selected(self) -> None:
        if self.selected_file and self.selected_file.is_folder:
            self.folder_stack = [*self.folder_stack, self.current_folder]
            self._load_files(self.selected_file.file_id)
            self._update_breadcrumb(self.selected_file.name)

    def action_go_up(self) -> None:
        if self.current_view == VIEW_HOME:
            self.app.notify("Già nella Home", timeout=2)
            return
        if self.folder_stack:
            parent = self.folder_stack[-1]
            self.folder_stack = self.folder_stack[:-1]
            self._load_files(parent)
            if not self.folder_stack:
                if self.current_view == VIEW_MY_DRIVE:
                    self._update_breadcrumb("Il mio Drive")
                elif self.current_view == VIEW_SHARED_DRIVE:
                    self._update_breadcrumb("Drive condiviso")
            else:
                self._update_breadcrumb("")
        else:
            self._show_home()

    def action_download(self) -> None:
        if not self.selected_file or not self.drive_service:
            self.app.notify("Seleziona un file", severity="warning")
            return
        if self.selected_file.is_folder:
            self.app.notify("Non puoi scaricare una cartella", severity="warning")
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
        self.current_view = VIEW_RECENT
        self.folder_stack = []
        self._update_breadcrumb("Recenti")
        self.app.run_worker(self._load_recent_worker, thread=True)

    def _load_recent_worker(self) -> None:
        if not self.drive_service:
            return
        files = self.drive_service.list_recent()
        self.app.call_from_thread(self._update_file_list, files)

    def action_view_shared(self) -> None:
        if not self.drive_service:
            return
        self.current_view = VIEW_SHARED_WITH_ME
        self.folder_stack = []
        self._update_breadcrumb("Condivisi con me")
        self.app.run_worker(self._load_shared_worker, thread=True)

    def _load_shared_worker(self) -> None:
        if not self.drive_service:
            return
        files = self.drive_service.list_shared()
        self.app.call_from_thread(self._update_file_list, files)

    def action_view_root(self) -> None:
        self.current_view = VIEW_MY_DRIVE
        self.current_drive_id = ""
        self.folder_stack = []
        self._load_files("root")
        self._update_breadcrumb("Il mio Drive")

    def action_view_home(self) -> None:
        self._show_home()

    # ── Helpers ────────────────────────────────────────────────

    def _update_breadcrumb(self, text: str) -> None:
        self.query_one("#drive-breadcrumb", Static).update(text)
