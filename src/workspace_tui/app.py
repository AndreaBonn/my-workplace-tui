from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from workspace_tui.config.settings import Settings
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
                yield JiraTab(enabled=self.settings.jira_configured)
        yield StatusBar()
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id

    def action_request_quit(self) -> None:
        self.exit()

    def action_show_help(self) -> None:
        self.notify(
            "1-5: Cambia tab │ Tab/S-Tab: Pannello │ r: Ricarica │ q: Esci │ ?: Help",
            title="Shortcut",
            timeout=5,
        )

    def action_reload_tab(self) -> None:
        self.notify("Ricarica dati...", timeout=2)
