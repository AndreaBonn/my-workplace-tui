from textual.containers import Container
from textual.widgets import Static


class CalendarTab(Container):
    def compose(self):
        yield Static("Google Calendar — In costruzione", classes="tab-placeholder")
