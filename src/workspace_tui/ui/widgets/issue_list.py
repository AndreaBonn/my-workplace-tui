from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import ListItem, ListView, Static

from workspace_tui.services.jira import JiraIssue
from workspace_tui.utils.text_utils import truncate


class IssueSelected(Message):
    def __init__(self, issue: JiraIssue) -> None:
        self.issue = issue
        super().__init__()


class IssueListItem(ListItem):
    def __init__(self, issue: JiraIssue, **kwargs) -> None:
        super().__init__(**kwargs)
        self.issue = issue

    def compose(self) -> ComposeResult:
        status_badge = f"[{self.issue.status}]"
        summary = truncate(self.issue.summary, max_length=45)
        yield Static(f"{self.issue.key}  {status_badge}\n  {summary}")


class IssueListView(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Giù", show=False),
        Binding("k", "cursor_up", "Su", show=False),
        Binding("g", "scroll_home", "Inizio", show=False),
        Binding("G", "scroll_end", "Fine", show=False),
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
