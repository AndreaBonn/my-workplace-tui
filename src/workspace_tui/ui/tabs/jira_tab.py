import webbrowser

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Static

from workspace_tui.config.settings import Settings
from workspace_tui.services.jira import JiraIssue, JiraService, JiraWorklog
from workspace_tui.ui.widgets.issue_create_modal import IssueCreateData, IssueCreateModal
from workspace_tui.ui.widgets.issue_detail import IssueDetail
from workspace_tui.ui.widgets.issue_list import IssueListView, IssueSelected
from workspace_tui.ui.widgets.worklog_modal import WorklogData, WorklogModal

JIRA_DISABLED_MESSAGE = (
    "Configura JIRA_USERNAME, JIRA_API_TOKEN e JIRA_BASE_URL "
    "nel file .env per abilitare questa tab."
)


class JiraTab(Vertical):
    BINDINGS = [
        Binding("c", "create_issue", "Crea issue", show=True),
        Binding("t", "transition", "Cambia stato", show=True),
        Binding("w", "worklog", "Log ore", show=True),
        Binding("C", "add_comment", "Commento", show=True),
        Binding("o", "open_browser", "Apri browser", show=True),
        Binding("slash", "search_jql", "Cerca/JQL", show=True),
        Binding("f1", "saved_jql_1", "F1", show=True),
        Binding("f2", "saved_jql_2", "F2", show=True),
        Binding("f3", "saved_jql_3", "F3", show=True),
        Binding("f4", "saved_jql_4", "F4", show=True),
        Binding("f5", "saved_jql_5", "F5", show=True),
    ]

    jira_service: reactive[JiraService | None] = reactive(None, init=False)
    selected_issue: reactive[JiraIssue | None] = reactive(None, init=False)

    def __init__(
        self, *, enabled: bool = False, settings: Settings | None = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._enabled = enabled
        self._settings = settings
        self._current_jql = ""

    def compose(self) -> ComposeResult:
        if not self._enabled:
            yield Static(JIRA_DISABLED_MESSAGE, classes="disabled-tab")
            return

        with Horizontal(id="jira-layout"):
            with Vertical(id="jira-left-panel"):
                with Vertical(id="jira-filters"):
                    yield Static(" FILTRI (Enter per cercare)", classes="panel-title")
                    yield Input(
                        placeholder="Progetto: es. TAGAIT",
                        id="filter-project",
                        value=self._settings.jira_default_project if self._settings else "",
                    )
                    yield Input(placeholder="Testo: parola chiave", id="filter-text")
                    yield Input(placeholder="Assegnato: nome persona", id="filter-assignee")
                    yield Input(placeholder="Stato: es. In corso", id="filter-status")
                    yield Checkbox("Assegnati a me", id="filter-my-issues")
                    yield Input(placeholder="JQL: query diretta", id="filter-jql")
                yield Static("Issue", classes="panel-title")
                yield IssueListView(id="issue-list")
            with Vertical(id="jira-right-panel"):
                yield IssueDetail(id="issue-detail")

    def set_service(self, service: JiraService) -> None:
        self.jira_service = service
        self._load_default_issues()

    def reload(self) -> None:
        self._load_default_issues()

    def _load_default_issues(self) -> None:
        if not self.jira_service or not self._settings:
            return
        project = self._settings.jira_default_project
        if project:
            jql = f"project = {project} AND status != Done ORDER BY updated DESC"
        else:
            jql = "status != Done ORDER BY updated DESC"
        self._execute_jql(jql)

    def _execute_jql(self, jql: str) -> None:
        self._current_jql = jql
        self.app.run_worker(lambda: self._search_worker(jql), thread=True)

    def _search_worker(self, jql: str) -> None:
        if not self.jira_service:
            return
        try:
            max_results = self._settings.jira_max_results if self._settings else 50
            issues, _total = self.jira_service.search_issues(jql=jql, max_results=max_results)
            self.app.call_from_thread(self._update_issue_list, issues)
        except Exception as exc:
            from loguru import logger

            logger.error("Jira search failed: {}", exc)
            self.app.call_from_thread(
                self.app.notify, f"Errore Jira: {exc}", severity="error", timeout=5
            )

    def _update_issue_list(self, issues: list[JiraIssue]) -> None:
        issue_list = self.query_one("#issue-list", IssueListView)
        issue_list.set_issues(issues)

    def on_issue_selected(self, event: IssueSelected) -> None:
        if not self.jira_service:
            return
        self.app.run_worker(
            lambda: self._load_issue_detail_worker(event.issue.key),
            thread=True,
        )

    def _load_issue_detail_worker(self, issue_key: str) -> None:
        if not self.jira_service:
            return
        try:
            issue = self.jira_service.get_issue(issue_key)
            worklogs = self.jira_service.get_worklogs(issue_key)
            self.app.call_from_thread(self._update_issue_detail, issue, worklogs)
        except Exception as exc:
            self.app.call_from_thread(
                self.app.notify, f"Errore caricamento issue: {exc}", severity="error", timeout=5
            )

    def _update_issue_detail(self, issue: JiraIssue, worklogs: list[JiraWorklog]) -> None:
        self.selected_issue = issue
        detail = self.query_one("#issue-detail", IssueDetail)
        detail.jira_base_url = self._settings.jira_base_url if self._settings else ""
        detail.issue = issue
        detail.set_worklogs(worklogs)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "filter-my-issues":
            self._execute_filter_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-jql":
            jql = event.value.strip()
            if jql:
                self._execute_jql(jql)
            return

        if event.input.id in ("filter-project", "filter-text", "filter-assignee", "filter-status"):
            self._execute_filter_search()
            return

    def _execute_filter_search(self) -> None:
        project = self.query_one("#filter-project", Input).value.strip()
        text = self.query_one("#filter-text", Input).value.strip()
        my_issues = self.query_one("#filter-my-issues", Checkbox).value
        assignee = self.query_one("#filter-assignee", Input).value.strip()
        status = self.query_one("#filter-status", Input).value.strip()

        conditions = []

        if project:
            project_condition = self._resolve_project_filter(project)
            if project_condition:
                conditions.append(project_condition)
        if text:
            safe_text = text.replace('"', '\\"')
            conditions.append(f'(summary ~ "{safe_text}*" OR description ~ "{safe_text}*")')
        if my_issues:
            conditions.append("assignee = currentUser()")
        elif assignee:
            safe_name = assignee.replace('"', '\\"')
            conditions.append(f'assignee = "{safe_name}"')
        if status:
            safe_status = status.replace('"', '\\"')
            conditions.append(f'status = "{safe_status}"')

        if not conditions:
            self._load_default_issues()
            return

        jql = " AND ".join(conditions) + " ORDER BY updated DESC"
        self._execute_jql(jql)

    def _resolve_project_filter(self, project_input: str) -> str:
        """Resolve partial project codes to JQL condition.

        Exact match: "TAGAIT" → project = TAGAIT
        Partial match: "TAG" → project in (TAGAIT, TAGOPS, ...) using API project list
        """
        upper_input = project_input.upper()

        if not self.jira_service:
            return f"project = {upper_input}"

        try:
            projects = self.jira_service.list_projects()
            exact = [p for p in projects if p.get("key", "").upper() == upper_input]
            if exact:
                return f"project = {exact[0]['key']}"

            partial = [
                p["key"]
                for p in projects
                if upper_input in p.get("key", "").upper()
                or upper_input in p.get("name", "").upper()
            ]
            if len(partial) == 1:
                return f"project = {partial[0]}"
            if len(partial) > 1:
                keys = ", ".join(partial)
                return f"project in ({keys})"
        except Exception:
            pass

        return f"project = {upper_input}"

    def action_create_issue(self) -> None:
        if not self.jira_service:
            return
        default_project = self._settings.jira_default_project if self._settings else ""
        self.app.push_screen(
            IssueCreateModal(default_project=default_project),
            callback=self._handle_create_result,
        )

    def _handle_create_result(self, result: IssueCreateData | None) -> None:
        if result is None or not self.jira_service:
            return
        self.app.run_worker(
            lambda: self._create_issue_worker(result),
            thread=True,
        )

    def _create_issue_worker(self, data: IssueCreateData) -> None:
        if not self.jira_service:
            return
        key = self.jira_service.create_issue(
            project_key=data.project_key,
            summary=data.summary,
            issue_type=data.issue_type,
            priority=data.priority,
            assignee_id=data.assignee_id,
            description=data.description,
        )
        self.app.call_from_thread(self.app.notify, f"Issue {key} creata")
        self.app.call_from_thread(self._execute_jql, self._current_jql)

    def action_transition(self) -> None:
        issue = self.selected_issue
        if not issue or not self.jira_service:
            self.app.notify("Seleziona un'issue", severity="warning")
            return
        self.app.run_worker(
            lambda: self._show_transitions_worker(issue.key),
            thread=True,
        )

    def _show_transitions_worker(self, issue_key: str) -> None:
        if not self.jira_service:
            return
        transitions = self.jira_service.get_transitions(issue_key)
        if not transitions:
            self.app.call_from_thread(
                self.app.notify, "Nessuna transizione disponibile", severity="warning"
            )
            return

        options = "\n".join(f"  {i + 1}. {t.name}" for i, t in enumerate(transitions))
        self.app.call_from_thread(
            self.app.notify,
            f"Transizioni per {issue_key}:\n{options}",
            timeout=10,
        )

    def action_worklog(self) -> None:
        issue = self.selected_issue
        if not issue:
            self.app.notify("Seleziona un'issue", severity="warning")
            return
        self.app.push_screen(
            WorklogModal(issue_key=issue.key),
            callback=self._handle_worklog_result,
        )

    def _handle_worklog_result(self, result: WorklogData | None) -> None:
        if result is None or not self.jira_service or not self.selected_issue:
            return
        issue_key = self.selected_issue.key
        self.app.run_worker(
            lambda: self.jira_service.add_worklog(
                issue_key=issue_key,
                time_spent_seconds=result.time_spent_seconds,
                started=result.started,
                comment=result.comment,
            ),
            thread=True,
        )
        self.app.notify("Ore registrate")

    def action_add_comment(self) -> None:
        issue = self.selected_issue
        if not issue:
            self.app.notify("Seleziona un'issue", severity="warning")
            return
        self.app.notify("Commento: funzionalità in arrivo", timeout=3)

    def action_open_browser(self) -> None:
        issue = self.selected_issue
        if not issue or not self._settings:
            return
        url = f"{self._settings.jira_base_url}/browse/{issue.key}"
        webbrowser.open(url)

    def action_search_jql(self) -> None:
        self.query_one("#filter-project", Input).focus()

    def _apply_saved_jql(self, index: int) -> None:
        if not self._settings:
            return
        filters = self._settings.saved_jql_filters
        if index in filters:
            self._execute_jql(filters[index])
        else:
            self.app.notify(f"Filtro F{index} non configurato", severity="warning")

    def action_saved_jql_1(self) -> None:
        self._apply_saved_jql(1)

    def action_saved_jql_2(self) -> None:
        self._apply_saved_jql(2)

    def action_saved_jql_3(self) -> None:
        self._apply_saved_jql(3)

    def action_saved_jql_4(self) -> None:
        self._apply_saved_jql(4)

    def action_saved_jql_5(self) -> None:
        self._apply_saved_jql(5)
