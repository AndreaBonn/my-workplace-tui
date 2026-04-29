from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from workspace_tui.services.dashboard import _is_meeting, _parse_event_time

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from workspace_tui.services.dashboard import DashboardMetrics, DashboardService

STATUS_ICONS = {"To Do": "📋", "In Progress": "🔄", "Done": "✅"}


def _escape(text: str) -> str:
    """Escape square brackets for Textual markup parser."""
    return text.replace("[", r"\[")


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
    """Render a text progress bar: [████░░░░] 65%."""
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


class DashboardTab(Vertical):
    BINDINGS = [
        Binding("r", "reload", "Ricarica", show=True),
    ]

    dashboard_service: reactive[DashboardService | None] = reactive(None, init=False)

    def compose(self) -> ComposeResult:
        yield Static("📊 Dashboard", classes="panel-title")
        with Horizontal(id="dashboard-layout"):
            with Vertical(id="dashboard-left"):
                yield Static("", id="dash-upcoming")
                yield Static("", id="dash-recent-tasks")
                yield Static("", id="dash-recent-emails")
                yield Static("", id="dash-recent-files")
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
        self.query_one("#dash-upcoming", Static).update(
            "⏳ Caricamento metriche...",
        )

    def _show_error(self, message: str) -> None:
        self.query_one("#dash-upcoming", Static).update(
            f"❌ Errore: {message}",
        )

    def _render_metrics(self, metrics: DashboardMetrics) -> None:
        self._render_upcoming(metrics)
        self._render_recent_tasks(metrics)
        self._render_recent_emails(metrics)
        self._render_recent_files(metrics)
        if metrics.jira_available:
            self._render_tasks(metrics)
        else:
            self.query_one("#dash-tasks", Static).update("")
        self._render_quick_stats(metrics)
        self._render_errors(metrics)

    # ── Left panel ──────────────────────────────────────

    def _render_upcoming(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-upcoming", Static)
        now = datetime.now(tz=UTC)
        now_iso = now.isoformat()

        upcoming = [e for e in metrics.today_events if not e.all_day and e.end > now_iso][:3]

        lines = ["📅 Prossimi Eventi", ""]
        if not upcoming:
            lines.append("  Nessun evento in programma")
            widget.update("\n".join(lines))
            return

        for i, event in enumerate(upcoming):
            start = _parse_event_time(event.start)
            icon = "📹" if _is_meeting(event) else "📌"
            summary = _escape(event.summary)[:45]

            if not start:
                lines.append(f"  {icon} {summary}")
                continue

            time_str = start.strftime("%H:%M")
            if i == 0:
                delta = start - now
                total_min = max(int(delta.total_seconds()) // 60, 0)
                h, m = divmod(total_min, 60)
                cd = f"tra {h}h {m}m" if h else f"tra {m}m"
                lines.append(f"  {time_str} {icon} {summary} ({cd})")
                link = event.meet_link or event.html_link
                if link:
                    lines.append(f"         {link}")
            else:
                lines.append(f"  {time_str} {icon} {summary}")

        widget.update("\n".join(lines))

    def _render_recent_tasks(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-recent-tasks", Static)
        lines = ["🎫 Task Recenti", ""]
        if not metrics.recent_tasks:
            lines.append("  Nessun task")
        else:
            for issue in metrics.recent_tasks:
                icon = STATUS_ICONS.get(issue.status_category, "📋")
                summary = _escape(issue.summary)[:38]
                lines.append(f"  {icon} {issue.key}: {summary}")
        widget.update("\n".join(lines))

    def _render_recent_emails(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-recent-emails", Static)
        lines = ["📧 Email Recenti", ""]
        if not metrics.recent_emails:
            lines.append("  Nessuna email non letta")
        else:
            for msg in metrics.recent_emails:
                sender = msg.header.from_address.split("<")[0].strip()
                sender = _escape(sender[:20])
                subject = _escape(msg.header.subject[:35])
                dot = "●" if msg.is_unread else "○"
                lines.append(f"  {dot} {sender} — {subject}")
        widget.update("\n".join(lines))

    def _render_recent_files(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-recent-files", Static)
        lines = ["📁 File Recenti", ""]
        if not metrics.recent_files:
            lines.append("  Nessun file recente")
        else:
            for f in metrics.recent_files:
                lines.append(f"  {f.icon} {_escape(f.name[:45])}")
        widget.update("\n".join(lines))

    # ── Right panel ─────────────────────────────────────

    def _render_tasks(self, metrics: DashboardMetrics) -> None:
        widget = self.query_one("#dash-tasks", Static)
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

        today_cnt = f"{metrics.meetings_today_remaining}/{metrics.meetings_today_total}"
        today_bar = _progress_bar(
            metrics.meetings_today_done_seconds,
            metrics.meetings_today_total_seconds,
            width=12,
        )
        today_hrs = (
            f"{_fmt_hours(metrics.meetings_today_done_seconds)}"
            f" / {_fmt_hours(metrics.meetings_today_total_seconds)}"
        )
        lines.append(f"  📅 Meeting oggi: {today_cnt}  {today_bar}")
        lines.append(f"     {today_hrs}")

        week_cnt = f"{metrics.meetings_week_remaining}/{metrics.meetings_week_total}"
        week_bar = _progress_bar(
            metrics.meetings_week_done_seconds,
            metrics.meetings_week_total_seconds,
            width=12,
        )
        week_hrs = (
            f"{_fmt_hours(metrics.meetings_week_done_seconds)}"
            f" / {_fmt_hours(metrics.meetings_week_total_seconds)}"
        )
        lines.append(f"  📅 Meeting settimana: {week_cnt}  {week_bar}")
        lines.append(f"     {week_hrs}")

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
