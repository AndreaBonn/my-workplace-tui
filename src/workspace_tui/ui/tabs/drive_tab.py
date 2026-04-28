from textual.containers import Container
from textual.widgets import Static


class DriveTab(Container):
    def compose(self):
        yield Static("Google Drive — In costruzione", classes="tab-placeholder")
