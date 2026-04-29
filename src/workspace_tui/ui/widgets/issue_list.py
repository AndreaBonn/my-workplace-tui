from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.jira import JiraIssue
from workspace_tui.utils.text_utils import truncate

STATUS_ICONS = {
    "Da completare": "○",
    "To Do": "○",
    "In corso": "◉",
    "In Progress": "◉",
    "In Review": "◈",
    "Done": "●",
    "Completato": "●",
}

PRIORITY_ICONS = {
    "Highest": "⬆⬆",
    "High": "⬆",
    "Grave": "⬆",
    "Medium": "─",
    "Low": "⬇",
    "Lowest": "⬇⬇",
}


class IssueSelected(Message):
    def __init__(self, issue: JiraIssue) -> None:
        self.issue = issue
        super().__init__()


class IssueListItem(ListItem):
    def __init__(self, issue: JiraIssue, **kwargs) -> None:
        super().__init__(**kwargs)
        self.issue = issue

    def compose(self) -> ComposeResult:
        status_icon = STATUS_ICONS.get(self.issue.status, "◌")
        priority_icon = PRIORITY_ICONS.get(self.issue.priority, " ")
        summary = truncate(self.issue.summary, max_length=42)
        account_tag = ""
        if self.issue.account_name and self.issue.account_name != "default":
            account_tag = f"  [{self.issue.account_name}]"
        epic_tag = f"  ⚡{self.issue.epic_key}" if self.issue.epic_key else ""
        first_line = f" {status_icon} {self.issue.key:<12} {priority_icon}{account_tag}{epic_tag}"
        yield Static(f"{first_line}\n   {summary}", markup=False)


class IssueListView(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Giù", show=True),
        Binding("k", "cursor_up", "Su", show=True),
        Binding("g", "scroll_home", "Inizio", show=True),
        Binding("G", "scroll_end", "Fine", show=True),
    ]

    issues: reactive[list[JiraIssue]] = reactive(list, init=False)

    def set_issues(self, issues: list[JiraIssue]) -> None:
        self.clear()
        self.issues = issues
        for issue in issues:
            self.append(IssueListItem(issue=issue))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, IssueListItem):
            self.post_message(IssueSelected(issue=event.item.issue))

    def action_scroll_home(self) -> None:
        if self.children:
            self.index = 0

    def action_scroll_end(self) -> None:
        if self.children:
            self.index = len(self.children) - 1
