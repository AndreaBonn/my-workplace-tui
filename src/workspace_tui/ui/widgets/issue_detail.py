from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.jira import JiraComment, JiraIssue, JiraWorklog
from workspace_tui.utils.date_utils import format_relative, parse_date, seconds_to_jira_duration

SEPARATOR = "─" * 50


class IssueDetail(VerticalScroll):
    issue: reactive[JiraIssue | None] = reactive(None)
    comments: reactive[list[JiraComment]] = reactive(list, init=False)
    jira_base_url: str = ""
    worklogs: reactive[list[JiraWorklog]] = reactive(list, init=False)

    def compose(self) -> ComposeResult:
        yield Static("", id="issue-header", markup=False)
        yield Static("", id="issue-description", markup=False)
        yield Static("", id="issue-worklogs", markup=False)
        yield Static("", id="issue-links", markup=False)
        yield Static("", id="issue-comments", markup=False)

    def watch_issue(self, issue: JiraIssue | None) -> None:
        if issue is None:
            self.query_one("#issue-header", Static).update("Seleziona un'issue per visualizzarla")
            for widget_id in (
                "#issue-description",
                "#issue-worklogs",
                "#issue-links",
                "#issue-comments",
            ):
                self.query_one(widget_id, Static).update("")
            return

        estimate = (
            seconds_to_jira_duration(issue.estimate_seconds) if issue.estimate_seconds else "-"
        )
        logged = seconds_to_jira_duration(issue.logged_seconds) if issue.logged_seconds else "-"

        project_key = issue.key.split("-")[0] if "-" in issue.key else ""
        issue_url = f"{self.jira_base_url}/browse/{issue.key}" if self.jira_base_url else ""
        board_url = (
            f"{self.jira_base_url}/jira/software/projects/{project_key}/board"
            if self.jira_base_url and project_key
            else ""
        )

        header = (
            f"  {issue.key}\n"
            f"  {issue.summary}\n"
            f"\n"
            f"{SEPARATOR}\n"
            f"  Tipo:       {issue.issue_type}\n"
            f"  Priorita:   {issue.priority}\n"
            f"  Stato:      {issue.status}\n"
            f"{SEPARATOR}\n"
            f"  Assegnato:  {issue.assignee or 'Non assegnato'}\n"
            f"  Reporter:   {issue.reporter}\n"
            f"  Sprint:     {issue.sprint or '-'}\n"
            f"{SEPARATOR}\n"
            f"  Stima:      {estimate}\n"
            f"  Logged:     {logged}\n"
        )
        if issue.labels:
            header += f"  Label:      {', '.join(issue.labels)}\n"
        if issue_url:
            header += (
                f"{SEPARATOR}\n"
                f"  Issue:      {issue_url}\n"
                f"  Board:      {board_url}\n"
                f"              (premi 'o' per aprire nel browser)\n"
            )

        description = ""
        if issue.description_text:
            description = f"\n{SEPARATOR}\n  DESCRIZIONE\n{SEPARATOR}\n\n{issue.description_text}\n"

        links_text = ""
        if issue.subtasks:
            lines = [
                f"\n{SEPARATOR}",
                "  SUBTASK",
                SEPARATOR,
                "",
            ]
            for st in issue.subtasks:
                status_str = st["status"]
                lines.append(f"  {st['key']:<12} {status_str:<15} {st['summary']}")
            links_text += "\n".join(lines) + "\n"

        if issue.links:
            lines = [
                f"\n{SEPARATOR}",
                "  LINK",
                SEPARATOR,
                "",
            ]
            for link in issue.links:
                lines.append(f"  {link['issue_key']:<12} {link['type']:<15} {link['summary']}")
            links_text += "\n".join(lines) + "\n"

        self.query_one("#issue-header", Static).update(header)
        self.query_one("#issue-description", Static).update(description)
        self.query_one("#issue-links", Static).update(links_text)

    def set_worklogs(self, worklogs: list[JiraWorklog]) -> None:
        self.worklogs = worklogs
        if not worklogs:
            self.query_one("#issue-worklogs", Static).update("")
            return

        lines = [
            f"\n{SEPARATOR}",
            "  WORKLOGS",
            SEPARATOR,
            "",
        ]
        for wl in worklogs:
            date_str = ""
            dt = parse_date(wl.started)
            if dt:
                date_str = format_relative(dt)
            lines.append(f"  {wl.time_spent:<10} {wl.author:<20} {date_str}")
            if wl.comment:
                lines.append(f"             {wl.comment}")
            lines.append("")
        self.query_one("#issue-worklogs", Static).update("\n".join(lines))

    def set_comments(self, comments: list[JiraComment]) -> None:
        if not comments:
            self.query_one("#issue-comments", Static).update("")
            return

        lines = [
            f"\n{SEPARATOR}",
            f"  COMMENTI ({len(comments)})",
            SEPARATOR,
            "",
        ]
        for c in comments:
            date_str = ""
            dt = parse_date(c.created)
            if dt:
                date_str = format_relative(dt)
            lines.append(f"  {c.author}  —  {date_str}")
            lines.append(f"  {SEPARATOR}")
            for body_line in c.body.splitlines():
                lines.append(f"  {body_line}")
            lines.append("")
        self.query_one("#issue-comments", Static).update("\n".join(lines))
