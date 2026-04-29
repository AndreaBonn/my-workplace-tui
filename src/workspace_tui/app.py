from pathlib import Path

from loguru import logger
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, TabbedContent, TabPane

from workspace_tui.auth.jira_auth import create_jira_session
from workspace_tui.auth.oauth import load_or_create_credentials
from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.config.settings import Settings
from workspace_tui.notifications.notifier import Notifier
from workspace_tui.notifications.poll_manager import PollManager, PollResult
from workspace_tui.services.calendar import CalendarService
from workspace_tui.services.chat import ChatService
from workspace_tui.services.drive import DriveService
from workspace_tui.services.errors import ConfigurationError
from workspace_tui.services.gmail import GmailService
from workspace_tui.services.jira import JiraService
from workspace_tui.services.search import SearchService
from workspace_tui.ui.tabs.calendar_tab import CalendarTab
from workspace_tui.ui.tabs.chat_tab import ChatTab
from workspace_tui.ui.tabs.drive_tab import DriveTab
from workspace_tui.ui.tabs.gmail_tab import GmailTab
from workspace_tui.ui.tabs.jira_tab import JiraTab
from workspace_tui.ui.tabs.search_tab import SearchTab
from workspace_tui.ui.widgets.status_bar import StatusBar
from workspace_tui.ui.widgets.wrapping_footer import WrappingFooter

MIN_COLUMNS = 120
MIN_ROWS = 30


class WorkspaceTUI(App):
    TITLE = "Workspace TUI"
    CSS_PATH = Path("ui/styles/main.tcss")

    BINDINGS = [
        Binding("1", "switch_tab('gmail')", "Gmail", show=True),
        Binding("2", "switch_tab('chat')", "Chat", show=True),
        Binding("3", "switch_tab('calendar')", "Calendar", show=True),
        Binding("4", "switch_tab('drive')", "Drive", show=True),
        Binding("5", "switch_tab('jira')", "Jira", show=True),
        Binding("6", "switch_tab('search')", "Search", show=True),
        Binding("q", "request_quit", "Esci", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("r", "reload_tab", "Ricarica", show=True),
    ]

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings = settings
        self._cache = CacheManager(enabled=settings.cache_enabled)
        self._notifier = Notifier(enabled=settings.notifications_enabled)
        self._poll_manager = PollManager(
            notifier=self._notifier,
            on_update=self._handle_poll_update,
        )
        self._gmail_service: GmailService | None = None
        self._calendar_service: CalendarService | None = None
        self._drive_service: DriveService | None = None
        self._chat_service: ChatService | None = None
        self._jira_service: JiraService | None = None
        self._search_service: SearchService | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="gmail"):
            with TabPane("[1] Gmail", id="gmail"):
                yield GmailTab()
            with TabPane("[2] Chat", id="chat"):
                yield ChatTab()
            with TabPane("[3] Calendar", id="calendar"):
                yield CalendarTab()
            with TabPane("[4] Drive", id="drive"):
                yield DriveTab(
                    workspace_domain=self.settings.workspace_domain,
                    download_dir=self.settings.drive_download_dir,
                )
            with TabPane("[5] Jira", id="jira"):
                yield JiraTab(
                    enabled=self.settings.jira_configured,
                    settings=self.settings,
                )
            with TabPane("[6] Search", id="search"):
                yield SearchTab()
        yield StatusBar()
        yield WrappingFooter()

    def on_mount(self) -> None:
        self.run_worker(self._initialize_services, thread=True)

    def _initialize_services(self) -> None:
        self.app.call_from_thread(self._set_status, "Connessione...")

        try:
            creds = load_or_create_credentials(
                client_secret_path=self.settings.google_client_secret_path,
                token_path=self.settings.google_token_path,
            )

            self._gmail_service = GmailService(credentials=creds, cache=self._cache)
            self._calendar_service = CalendarService(credentials=creds, cache=self._cache)
            self._drive_service = DriveService(credentials=creds, cache=self._cache)
            self._chat_service = ChatService(credentials=creds, cache=self._cache)

            self.app.call_from_thread(self._wire_google_services)
            logger.info("Google services initialized")
        except ConfigurationError as exc:
            self.app.call_from_thread(self._set_status, "Errore config")
            self.app.call_from_thread(self.notify, str(exc.message), severity="error", timeout=10)
            logger.error("Configuration error: {}", exc.message)
        except Exception as exc:
            self.app.call_from_thread(self._set_status, "Errore")
            self.app.call_from_thread(
                self.notify, f"Errore connessione Google: {exc}", severity="error", timeout=10
            )
            logger.error("Failed to initialize Google services: {}", exc)

        if self.settings.jira_configured:
            try:
                session = create_jira_session(
                    username=self.settings.jira_username,
                    api_token=self.settings.jira_api_token,
                    base_url=self.settings.jira_base_url,
                    allow_http=self.settings.jira_allow_http,
                )
                self._jira_service = JiraService(session=session, cache=self._cache)
                self.app.call_from_thread(self._wire_jira_service)
                logger.info("Jira service initialized")
            except Exception as exc:
                self.app.call_from_thread(
                    self.notify, f"Errore Jira: {exc}", severity="warning", timeout=5
                )
                logger.error("Failed to initialize Jira: {}", exc)

        self._start_polling()

    def _start_polling(self) -> None:
        self._poll_manager.configure(
            gmail_service=self._gmail_service,
            calendar_service=self._calendar_service,
            chat_service=self._chat_service,
            jira_service=self._jira_service,
            gmail_interval=self.settings.gmail_poll_interval,
            calendar_interval=self.settings.calendar_poll_interval,
            chat_interval=self.settings.chat_poll_interval,
            jira_interval=self.settings.jira_poll_interval,
        )
        self._poll_manager.start()

    def _handle_poll_update(self, result: PollResult) -> None:
        def update_ui() -> None:
            status_bar = self.query_one(StatusBar)
            if result.gmail_unread is not None:
                status_bar.unread_count = result.gmail_unread
            if result.jira_assigned is not None:
                status_bar.jira_count = result.jira_assigned
            if result.timestamp:
                status_bar.last_update = result.timestamp

        self.call_from_thread(update_ui)

    def _set_status(self, status: str) -> None:
        self.query_one(StatusBar).connection_status = status

    def _wire_google_services(self) -> None:
        self._set_status("Connesso")
        if self._gmail_service:
            self.query_one(GmailTab).set_service(self._gmail_service)
        if self._calendar_service:
            self.query_one(CalendarTab).set_service(self._calendar_service)
        if self._drive_service:
            self.query_one(DriveTab).set_service(self._drive_service)
        if self._chat_service:
            self.query_one(ChatTab).set_service(self._chat_service)
        self._wire_search_service()

    def _wire_jira_service(self) -> None:
        if self._jira_service:
            self.query_one(JiraTab).set_service(self._jira_service)
            self.query_one(StatusBar).jira_count = 0
        self._wire_search_service()

    def _wire_search_service(self) -> None:
        self._search_service = SearchService(
            gmail_service=self._gmail_service,
            jira_service=self._jira_service,
            drive_service=self._drive_service,
            chat_service=self._chat_service,
        )
        self.query_one(SearchTab).set_service(self._search_service)

    def action_switch_tab(self, tab_id: str) -> None:
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id

    def action_request_quit(self) -> None:
        self._poll_manager.stop()
        self._cache.close()
        self.exit()

    def action_show_help(self) -> None:
        self.notify(
            "1-6: Cambia tab │ Tab/S-Tab: Pannello │ r: Ricarica │ q: Esci │ ?: Help",
            title="Shortcut",
            timeout=5,
        )

    def action_reload_tab(self) -> None:
        active = self.query_one(TabbedContent).active
        if active == "gmail" and self._gmail_service:
            self._cache.invalidate_prefix("gmail:")
            self.query_one(GmailTab).load_labels()
        elif active == "calendar" and self._calendar_service:
            self._cache.invalidate_prefix("calendar:")
            self.query_one(CalendarTab).reload()
        elif active == "drive" and self._drive_service:
            self._cache.invalidate_prefix("drive:")
            self.query_one(DriveTab).reload()
        elif active == "chat" and self._chat_service:
            self._cache.invalidate_prefix("chat:")
            self.query_one(ChatTab).reload()
        elif active == "jira" and self._jira_service:
            self._cache.invalidate_prefix("jira:")
            self.query_one(JiraTab).reload()
        elif active == "search" and self._search_service:
            self.query_one(SearchTab).reload()
        self.notify("Ricarica dati...", timeout=2)
