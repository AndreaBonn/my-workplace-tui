from rich.text import Text
from textual.widget import Widget


class WrappingFooter(Widget):
    """Footer that wraps key bindings across multiple lines."""

    DEFAULT_CSS = """
    WrappingFooter {
        dock: bottom;
        height: auto;
        max-height: 5;
        background: $footer-background;
        color: $footer-foreground;
    }
    """

    def render(self) -> Text:
        bindings = self.app.active_bindings
        width = self.size.width or 80

        text = Text()
        current_line_len = 0

        first = True
        for _key, active_binding in bindings.items():
            binding = active_binding.binding
            if not binding.show:
                continue

            key_display = binding.key_display or binding.key
            gap = "  " if not first else ""
            segment = f"{gap} {key_display}  {binding.description} "
            segment_len = len(segment)

            # Wrap to next line if segment doesn't fit
            if current_line_len > 0 and current_line_len + segment_len > width:
                text.append("\n")
                current_line_len = 0
                gap = ""
                segment = f" {key_display}  {binding.description} "
                segment_len = len(segment)

            if gap:
                text.append(gap)

            text.append(f" {key_display} ", style="bold reverse")
            text.append(f" {binding.description} ")
            current_line_len += segment_len
            first = False

        return text

    def _on_mount(self) -> None:
        self.screen.bindings_updated_signal.subscribe(self, self._bindings_changed)
        self.watch(self.app, "focused", self._bindings_changed)

    def _bindings_changed(self, *_args: object) -> None:
        self.refresh()

    def _on_resize(self) -> None:
        self.refresh()
