from rich.text import Text
from textual.widget import Widget


class WrappingFooter(Widget):
    """Footer that wraps key bindings across multiple lines."""

    DEFAULT_CSS = """
    WrappingFooter {
        dock: bottom;
        height: auto;
        max-height: 4;
        background: $footer-background;
        color: $footer-foreground;
    }
    """

    def render(self) -> Text:
        bindings = self.app.active_bindings
        text = Text(no_wrap=False, overflow="fold")

        first = True
        for _key, active_binding in bindings.items():
            binding = active_binding.binding
            if not binding.show:
                continue

            if not first:
                text.append("  ")
            first = False

            key_display = binding.key_display or active_binding.binding.key
            text.append(f" {key_display} ", style="bold reverse")
            text.append(f" {binding.description} ")

        return text

    def _on_mount(self) -> None:
        self.screen.bindings_updated_signal.subscribe(self, self._bindings_changed)
        self.watch(self.app, "focused", self._bindings_changed)

    def _bindings_changed(self, *_args: object) -> None:
        self.refresh()
