"""Service analytics screen for Textual TUI."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label

from traceweaver.engine.store import TraceStore


class StatsScreen(Screen):
    """Service-level latency percentiles and error metrics screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back to Traces"),
        Binding("r", "refresh_stats", "Refresh"),
    ]

    def __init__(self, store: TraceStore):
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Service Analytics & Latency Percentiles", id="stats_title"),
            DataTable(id="stats_table", cursor_type="row"),
            id="stats_container",
        )

    def on_mount(self) -> None:
        table = self.query_one("#stats_table", DataTable)
        table.add_columns(
            "Service Name",
            "Total Spans",
            "Avg Latency",
            "p50",
            "p90",
            "p99",
            "Errors",
            "Error Rate",
        )
        self.action_refresh_stats()

    def action_refresh_stats(self) -> None:
        table = self.query_one("#stats_table", DataTable)
        table.clear()
        stats = self.store.get_service_analytics()

        for s in stats:
            err_text = Text(f"{s.error_rate}%", style="red" if s.error_rate > 0 else "green")
            table.add_row(
                Text(s.service_name, style="bold cyan"),
                str(s.span_count),
                f"{s.avg_duration_ms}ms",
                f"{s.p50_duration_ms}ms",
                f"{s.p90_duration_ms}ms",
                f"{s.p99_duration_ms}ms",
                str(s.error_count),
                err_text,
            )
