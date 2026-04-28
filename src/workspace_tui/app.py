from pathlib import Path

from loguru import logger
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from workspace_tui.auth.jira_auth import create_jira_session
from workspace_tui.auth.oauth import load_or_create_credentials
from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.config.settings import Settings
from workspace_tui.notifications.notifier import Notifier
from workspace_tui.services.calendar import CalendarService
from workspace_tui.services.chat import ChatService
from workspace_tui.services.drive import DriveService
from workspace_tui.services.errors import ConfigurationError
from workspace_tui.services.gmail import GmailService
from workspace_tui.services.jira import JiraService
from workspace_tui.ui.tabs.calendar_tab import CalendarTab
from workspace_tui.ui.tabs.chat_tab import ChatTab
from workspace_tui.ui.tabs.drive_tab import DriveTab
from workspace_tui.ui.tabs.gmail_tab import GmailTab
from workspace_tui.ui.tabs.jira_tab import JiraTab
from workspace_tui.ui.widgets.status_bar import StatusBar

MIN_COLUMNS = 120
MIN_ROWS = 40


class WorkspaceTUI(App):
    TITLE = "Workspace TUI"
    CSS_PATH = Path("ui/styles/main.tcss")

    BINDINGS = [
        Binding("1", "switch_tab('gmail')", "Gmail", show=True),
        Binding("2", "switch_tab('chat')", "Chat", show=True),
        Binding("3", "switch_tab('calendar')", "Calendar", show=True),
        Binding("4", "switch_tab('drive')", "Drive", show=True),
        Binding("5", "switch_tab('jira')", "Jira", show=True),
        Binding("q", "request_quit", "Esci", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("r", "reload_tab", "Ricarica", show=True),
    ]

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings = settings
        self._cache = CacheManager(enabled=settings.cache_enabled)
        self._notifier = Notifier(enabled=settings.notifications_enabled)
        self._gmail_service: GmailService | None = None
        self._calendar_service: CalendarService | None = None
        self._drive_service: DriveService | None = None
        self._chat_service: ChatService | None = None
        self._jira_service: JiraService | None = None

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
                yield DriveTab()
            with TabPane("[5] Jira", id="jira"):
                yield JiraTab(
                    enabled=self.settings.jira_configured,
                    settings=self.settings,
                )
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._initialize_services, thread=True)

    async def _initialize_services(self) -> None:
        status_bar = self.query_one(StatusBar)
        status_bar.connection_status = "Connessione..."

        try:
            creds = load_or_create_credentials(
                client_secret_path=self.settings.google_client_secret_path,
                token_path=self.settings.google_token_path,
            )

            self._gmail_service = GmailService(credentials=creds, cache=self._cache)
            gmail_tab = self.query_one(GmailTab)
            gmail_tab.set_service(self._gmail_service)

            self._calendar_service = CalendarService(credentials=creds, cache=self._cache)
            calendar_tab = self.query_one(CalendarTab)
            calendar_tab.set_service(self._calendar_service)

            self._drive_service = DriveService(credentials=creds, cache=self._cache)
            drive_tab = self.query_one(DriveTab)
            drive_tab.set_service(self._drive_service)

            self._chat_service = ChatService(credentials=creds, cache=self._cache)
            chat_tab = self.query_one(ChatTab)
            chat_tab.set_service(self._chat_service)

            status_bar.connection_status = "Connesso"
            logger.info("Google services initialized")

        except ConfigurationError as exc:
            status_bar.connection_status = "Errore config"
            self.notify(str(exc.message), severity="error", timeout=10)
            logger.error("Configuration error: {}", exc.message)
        except Exception as exc:
            status_bar.connection_status = "Errore"
            self.notify(f"Errore connessione Google: {exc}", severity="error", timeout=10)
            logger.error("Failed to initialize Google services: {}", exc)

        if self.settings.jira_configured:
            try:
                session = create_jira_session(
                    username=self.settings.jira_username,
                    api_token=self.settings.jira_api_token,
                    base_url=self.settings.jira_base_url,
                )
                self._jira_service = JiraService(session=session, cache=self._cache)
                jira_tab = self.query_one(JiraTab)
                jira_tab.set_service(self._jira_service)

                if not self.settings.jira_account_id:
                    try:
                        myself = self._jira_service.get_myself()
                        logger.info("Jira user: {}", myself.get("displayName", ""))
                    except Exception:
                        pass

                status_bar.jira_count = 0
                logger.info("Jira service initialized")
            except Exception as exc:
                self.notify(f"Errore Jira: {exc}", severity="warning", timeout=5)
                logger.error("Failed to initialize Jira: {}", exc)

    def action_switch_tab(self, tab_id: str) -> None:
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id

    def action_request_quit(self) -> None:
        self._cache.close()
        self.exit()

    def action_show_help(self) -> None:
        self.notify(
            "1-5: Cambia tab │ Tab/S-Tab: Pannello │ r: Ricarica │ q: Esci │ ?: Help",
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
        self.notify("Ricarica dati...", timeout=2)
