from __future__ import annotations

from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from workspace_tui.services.dashboard import DashboardMetrics, DashboardService

HOURS_PER_DAY = 8
DAYS_PER_WEEK = 5
WEEKLY_CAPACITY_SECONDS = HOURS_PER_DAY * DAYS_PER_WEEK * 3600


def _fmt_hours(seconds: int) -> str:
    """Format seconds as 'Xh Ym'."""
    if seconds <= 0:
        return "0h"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    """Render a text progress bar: [████████░░░░] 65%."""
    if total <= 0:
        return f"[{'░' * width}] --"
    ratio = min(current / total, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    pct = int(ratio * 100)
    return f"[{'█' * filled}{'░' * empty}] {pct}%"


def _status_breakdown(metrics: DashboardMetrics) -> str:
    s = metrics.tasks_by_status
    parts = []
    if s.to_do:
        parts.append(f"📋 Da fare: {s.to_do}")
    if s.in_progress:
        parts.append(f"🔄 In corso: {s.in_progress}")
    if s.done:
        parts.append(f"✅ Completati: {s.done}")
    return "\n".join(parts) if parts else "Nessun task"


def _priority_breakdown(metrics: DashboardMetrics) -> str:
    p = metrics.tasks_by_priority
    parts = []
    if p.highest:
        parts.append(f"🔴 Highest: {p.highest}")
    if p.high:
        parts.append(f"🟠 High: {p.high}")
    if p.medium:
        parts.append(f"🟡 Medium: {p.medium}")
    if p.low:
        parts.append(f"🟢 Low: {p.low}")
    if p.lowest:
        parts.append(f"⚪ Lowest: {p.lowest}")
    return "\n".join(parts) if parts else "—"


def _weekly_heatmap(metrics: DashboardMetrics) -> str:
    """Build a daily breakdown of logged hours for the week."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(tz=UTC)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    day_names = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    daily: dict[str, int] = {}
    for i in range(7):
        day = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        daily[day] = 0

    for wl in metrics.weekly_worklogs:
        if wl.date in daily:
            daily[wl.date] += wl.seconds

    lines = []
    for i, (date, seconds) in enumerate(daily.items()):
        name = day_names[i]
        hours_logged = seconds / 3600
        bar_len = int(min(hours_logged / HOURS_PER_DAY, 1.0) * 12)
        bar = "▓" * bar_len + "░" * (12 - bar_len)
        marker = " ◀ oggi" if date == now.strftime("%Y-%m-%d") else ""
        lines.append(f"  {name} {bar} {_fmt_hours(seconds)}{marker}")

    return "\n".join(lines)


class DashboardTab(Vertical):
    BINDINGS = [
        Binding("r", "reload", "Ricarica", show=True),
    ]

    dashboard_service: reactive[DashboardService | None] = reactive(None, init=False)

    def compose(self) -> ComposeResult:
        yield Static("📊 Dashboard", classes="panel-title")
        with Horizontal(id="dashboard-layout"):
            with Vertical(id="dashboard-left"):
                yield Static("", id="dash-time-tracking")
                yield Static("", id="dash-weekly-chart")
            with Vertical(id="dashboard-right"):
                yield Static("", id="dash-tasks")
                yield Static("", id="dash-quick-stats")
                yield Static("", id="dash-errors")

    def set_service(self, service: DashboardService) -> None:
        self.dashboard_service = service
        self._load_metrics()

    def reload(self) -> None:
        self._load_metrics()

    def _load_metrics(self) -> None:
        if not self.dashboard_service:
            return
        self._show_loading()
        self.app.run_worker(self._load_worker, thread=True)

    def _load_worker(self) -> None:
        if not self.dashboard_service:
            return
        try:
            metrics = self.dashboard_service.collect()
            self.app.call_from_thread(self._render_metrics, metrics)
        except Exception as exc:
            self.app.call_from_thread(self._show_error, str(exc))

    def _show_loading(self) -> None:
        self.query_one("#dash-time-tracking", Static).update("⏳ Caricamento metriche...")

    def _show_error(self, message: str) -> None:
        self.query_one("#dash-time-tracking", Static).update(f"❌ Errore: {message}")

    def _render_metrics(self, metrics: DashboardMetrics) -> None:
        self._render_time_tracking(metrics)
        self._render_weekly_chart(metrics)
        self._render_tasks(metrics)
        self._render_quick_stats(metrics)
        self._render_errors(metrics)

    def _render_time_tracking(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-time-tracking", Static)

        if not metrics.jira_available:
            widget.update("⏱ Time Tracking\n\n  Jira non configurato")
            return

        today_bar = _progress_bar(
            metrics.logged_today_seconds,
            HOURS_PER_DAY * 3600,
        )
        week_bar = _progress_bar(
            metrics.logged_week_seconds,
            WEEKLY_CAPACITY_SECONDS,
        )

        lines = [
            "⏱  Time Tracking",
            "",
            f"  Oggi:      {_fmt_hours(metrics.logged_today_seconds)} / {HOURS_PER_DAY}h",
            f"  {today_bar}",
            "",
            f"  Settimana: {_fmt_hours(metrics.logged_week_seconds)}"
            f" / {HOURS_PER_DAY * DAYS_PER_WEEK}h",
            f"  {week_bar}",
        ]

        if metrics.estimated_week_seconds > 0:
            lines.append("")
            lines.append(f"  Stimato: {_fmt_hours(metrics.estimated_week_seconds)}")

        widget.update("\n".join(lines))

    def _render_weekly_chart(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-weekly-chart", Static)

        if not metrics.jira_available:
            widget.update("")
            return

        lines = ["📅 Carico Settimanale", ""]
        lines.append(_weekly_heatmap(metrics))
        widget.update("\n".join(lines))

    def _render_tasks(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-tasks", Static)

        if not metrics.jira_available:
            widget.update("🎫 Task\n\n  Jira non configurato")
            return

        lines = [
            f"🎫 Task Aperti: {metrics.open_tasks}",
            "",
            "  Per stato:",
            _indent(_status_breakdown(metrics)),
            "",
            "  Per priorità:",
            _indent(_priority_breakdown(metrics)),
        ]
        widget.update("\n".join(lines))

    def _render_quick_stats(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-quick-stats", Static)

        lines = ["⚡ Quick Stats", ""]
        lines.append(f"  📧 Email non lette: {metrics.gmail_unread}")
        lines.append(f"  📅 Meeting oggi: {metrics.meetings_today}")
        lines.append(f"  📅 Meeting settimana: {metrics.meetings_week}")

        if metrics.jira_available:
            lines.append(f"  🎫 Task assegnati: {metrics.open_tasks}")

        widget.update("\n".join(lines))

    def _render_errors(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-errors", Static)
        if not metrics.errors:
            widget.update("")
            return

        lines = ["⚠️  Errori"]
        for source, error in metrics.errors.items():
            lines.append(f"  {source}: {error}")
        widget.update("\n".join(lines))

    def action_reload(self) -> None:
        self.reload()


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.split("\n"))
