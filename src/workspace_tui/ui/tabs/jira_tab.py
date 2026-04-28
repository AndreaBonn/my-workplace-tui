from textual.containers import Container
from textual.widgets import Static

JIRA_DISABLED_MESSAGE = (
    "Configura JIRA_USERNAME, JIRA_API_TOKEN e JIRA_BASE_URL "
    "nel file .env per abilitare questa tab."
)


class JiraTab(Container):
    def __init__(self, *, enabled: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._enabled = enabled

    def compose(self):
        if not self._enabled:
            yield Static(JIRA_DISABLED_MESSAGE, classes="disabled-tab")
        else:
            yield Static("Jira — In costruzione", classes="tab-placeholder")
