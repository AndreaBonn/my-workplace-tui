from textual.containers import Container
from textual.widgets import Static


class GmailTab(Container):
    def compose(self):
        yield Static("Gmail — In costruzione", classes="tab-placeholder")
