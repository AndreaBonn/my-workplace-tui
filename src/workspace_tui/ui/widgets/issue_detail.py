from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.jira import JiraComment, JiraIssue, JiraWorklog
from workspace_tui.utils.date_utils import format_relative, parse_date, seconds_to_jira_duration


class IssueDetail(VerticalScroll):
    issue: reactive[JiraIssue | None] = reactive(None)
    comments: reactive[list[JiraComment]] = reactive(list, init=False)
    worklogs: reactive[list[JiraWorklog]] = reactive(list, init=False)

    def compose(self) -> ComposeResult:
        yield Static("", id="issue-header", markup=False)
        yield Static("", id="issue-description", markup=False)
        yield Static("", id="issue-worklogs", markup=False)
        yield Static("", id="issue-links", markup=False)

    def watch_issue(self, issue: JiraIssue | None) -> None:
        if issue is None:
            self.query_one("#issue-header", Static).update("Seleziona un'issue per visualizzarla")
            for widget_id in ("#issue-description", "#issue-worklogs", "#issue-links"):
                self.query_one(widget_id, Static).update("")
            return

        estimate = (
            seconds_to_jira_duration(issue.estimate_seconds) if issue.estimate_seconds else "-"
        )
        logged = seconds_to_jira_duration(issue.logged_seconds) if issue.logged_seconds else "-"

        header = (
            f"{issue.key} · {issue.issue_type} · Priorità: {issue.priority}\n"
            f"{issue.summary}\n\n"
            f"Assegnato: {issue.assignee or 'Non assegnato'}\n"
            f"Reporter: {issue.reporter}\n"
            f"Sprint: {issue.sprint or '-'}\n"
            f"Stima: {estimate}  │  Logged: {logged}\n"
            f"Stato: {issue.status}"
        )

        description = ""
        if issue.description_text:
            description = f"── Descrizione ──\n{issue.description_text}"

        links_text = ""
        if issue.subtasks:
            lines = ["── Subtask ──"]
            for st in issue.subtasks:
                lines.append(f"  {st['key']} [{st['status']}] {st['summary']}")
            links_text += "\n".join(lines)

        if issue.links:
            lines = ["── Link ──"]
            for link in issue.links:
                lines.append(f"  {link['type']}: {link['issue_key']} — {link['summary']}")
            if links_text:
                links_text += "\n\n"
            links_text += "\n".join(lines)

        self.query_one("#issue-header", Static).update(header)
        self.query_one("#issue-description", Static).update(description)
        self.query_one("#issue-links", Static).update(links_text)

    def set_worklogs(self, worklogs: list[JiraWorklog]) -> None:
        self.worklogs = worklogs
        if not worklogs:
            self.query_one("#issue-worklogs", Static).update("")
            return

        lines = ["── Worklogs ──"]
        for wl in worklogs:
            date_str = ""
            dt = parse_date(wl.started)
            if dt:
                date_str = format_relative(dt)
            comment = f"  {wl.comment}" if wl.comment else ""
            lines.append(f"  {wl.time_spent} · {wl.author} · {date_str}{comment}")
        self.query_one("#issue-worklogs", Static).update("\n".join(lines))
