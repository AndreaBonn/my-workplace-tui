from textual.containers import Container
from textual.widgets import Static


class ChatTab(Container):
    def compose(self):
        yield Static("Google Chat — In costruzione", classes="tab-placeholder")
