from textual.reactive import reactive
from textual.widgets import Static


class StatusBar(Static):
    connection_status: reactive[str] = reactive("Connesso")
    account_email: reactive[str] = reactive("")
    unread_count: reactive[int] = reactive(0)
    jira_count: reactive[int] = reactive(0)
    last_update: reactive[str] = reactive("")
    hint: reactive[str] = reactive("")

    def render(self) -> str:
        parts: list[str] = []
        parts.append(f"Stato: {self.connection_status}")
        if self.account_email:
            parts.append(self.account_email)
        if self.unread_count > 0:
            parts.append(f"Non lette: {self.unread_count}")
        if self.jira_count > 0:
            parts.append(f"Jira: {self.jira_count}")
        if self.last_update:
            parts.append(f"Agg.: {self.last_update}")
        if self.hint:
            parts.append(self.hint)
        return " │ ".join(parts)
