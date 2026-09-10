"""Trace list screen for Textual TUI."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Input, Label

from traceweaver.engine.store import TraceStore
from traceweaver.tui.screens.stats import StatsScreen
from traceweaver.tui.screens.waterfall import WaterfallScreen


class TraceListScreen(Screen):
    """Main trace exploration screen displaying real-time traces table."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("r", "refresh_traces", "Refresh"),
        Binding("s", "show_stats", "Analytics"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self, store: TraceStore):
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Horizontal(
                Label("TraceWeaver — Causal Waterfall Explorer", id="app_heading"),
                Input(placeholder="Filter by service name...", id="search_input"),
                id="search_bar",
            ),
            DataTable(id="traces_table", cursor_type="row"),
            id="main_container",
        )

    def on_mount(self) -> None:
        table = self.query_one("#traces_table", DataTable)
        table.add_columns(
            "Status",
            "Trace ID",
            "Root Service",
            "Root Operation",
            "Duration",
            "Spans",
            "Services",
        )
        self.action_refresh_traces()

    def action_refresh_traces(self) -> None:
        table = self.query_one("#traces_table", DataTable)
        table.clear()
        search_val = self.query_one("#search_input", Input).value.strip() or None

        traces = self.store.get_traces(limit=100, service_name=search_val)
        for t in traces:
            status_text = (
                Text("[ERR]", style="bold red") if t.has_error else Text("[OK]", style="bold green")
            )
            table.add_row(
                status_text,
                Text(t.trace_id[:16] + "...", style="cyan"),
                Text(t.root_service, style="bold white"),
                t.root_name,
                f"{t.duration_ms}ms",
                str(t.span_count),
                str(t.service_count),
                key=t.trace_id,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self.action_refresh_traces()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        trace_id = str(event.row_key.value)
        self.app.push_screen(WaterfallScreen(trace_id=trace_id, store=self.store))

    def action_show_stats(self) -> None:
        self.app.push_screen(StatsScreen(store=self.store))

    def action_focus_search(self) -> None:
        self.query_one("#search_input", Input).focus()
