"""Waterfall screen for Textual TUI displaying causal DAG and dwell times."""

import json

from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label, Static

from traceweaver.engine.correlator import CausalNode, CausalTraceDAG, TraceCorrelator
from traceweaver.engine.store import TraceStore
from traceweaver.receiver.span_normalizer import NormalizedSpan


class WaterfallScreen(Screen):
    """Interactive Gantt-style causal waterfall screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back to Traces"),
        Binding("r", "refresh_dag", "Refresh"),
    ]

    def __init__(self, trace_id: str, store: TraceStore):
        super().__init__()
        self.trace_id = trace_id
        self.store = store
        self.dag: CausalTraceDAG | None = None
        self.node_by_span_id: dict[str, CausalNode] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Horizontal(
                Label(f"Trace: {self.trace_id}", id="trace_title"),
                Label("", id="trace_metrics"),
                id="waterfall_header",
            ),
            DataTable(id="waterfall_table", cursor_type="row"),
            Static(id="span_detail_panel"),
            id="waterfall_main",
        )

    def on_mount(self) -> None:
        table = self.query_one("#waterfall_table", DataTable)
        table.add_columns("Causal Hierarchy & Operations", "Duration", "Timeline Gantt")
        self.action_refresh_dag()

    def action_refresh_dag(self) -> None:
        spans = self.store.get_trace_spans(self.trace_id)
        if not spans:
            self.query_one("#trace_title", Label).update(f"Trace {self.trace_id} not found")
            return

        correlator = TraceCorrelator()
        self.dag = correlator.correlate_trace(spans)

        metrics_label = self.query_one("#trace_metrics", Label)
        metrics_label.update(
            f"Total Duration: {self.dag.total_duration_ms}ms | "
            f"Queue Dwell: {self.dag.total_dwell_time_ms}ms | "
            f"Spans: {self.dag.span_count}"
        )

        table = self.query_one("#waterfall_table", DataTable)
        table.clear()
        self.node_by_span_id.clear()

        max_dur = max(1.0, self.dag.total_duration_ms)
        timeline_cols = 40

        def traverse(node: CausalNode) -> None:
            span = node.span
            self.node_by_span_id[span.span_id] = node

            # If node has dwell intervals, render yellow hatched dwell bar first
            for dwell in node.dwell_intervals:
                dwell_offset = max(0.0, node.offset_ms - dwell.dwell_time_ms)
                dw_off_chars = int((dwell_offset / max_dur) * timeline_cols)
                dw_len_chars = max(2, int((dwell.dwell_time_ms / max_dur) * timeline_cols))
                dw_bar_str = " " * dw_off_chars + "░" * dw_len_chars

                table.add_row(
                    Text(
                        "  " * node.depth + f"░░ Dwell in {dwell.queue_name}", style="bold yellow"
                    ),
                    Text(f"{dwell.dwell_time_ms}ms", style="bold yellow"),
                    Text(dw_bar_str, style="yellow"),
                    key=f"dwell_{dwell.consumer_span_id}",
                )

            # Format span hierarchy label
            indent = "  " * node.depth + ("└── " if node.depth > 0 else "")
            label_text = Text()
            label_text.append(indent)
            label_text.append(f"[{span.service_name}] ", style="bold cyan")
            label_text.append(span.name, style="white")

            if node.is_critical_path:
                label_text.append(" 🔥", style="bold red")
            if node.is_anomaly:
                label_text.append(" ⚠️", style="bold yellow")
            if span.status_code == "ERROR":
                label_text.append(" [ERR]", style="bold red")

            # Format timeline bar
            off_chars = int((node.offset_ms / max_dur) * timeline_cols)
            len_chars = max(1, int((span.duration_ms / max_dur) * timeline_cols))
            bar_str = " " * off_chars + "█" * len_chars

            bar_style = (
                "red"
                if span.status_code == "ERROR"
                else ("bold red" if node.is_critical_path else "green")
            )

            table.add_row(
                label_text,
                f"{span.duration_ms}ms",
                Text(bar_str, style=bar_style),
                key=span.span_id,
            )

            for child in node.children:
                traverse(child)

        for root in self.dag.root_nodes:
            traverse(root)

        if self.dag.root_nodes:
            self.display_span_detail(self.dag.root_nodes[0].span)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key_str = str(event.row_key.value)
        if key_str in self.node_by_span_id:
            node = self.node_by_span_id[key_str]
            self.display_span_detail(node.span)

    def display_span_detail(self, span: NormalizedSpan) -> None:
        panel_widget = self.query_one("#span_detail_panel", Static)
        attrs_formatted = json.dumps(span.attributes, indent=2)
        content = (
            f"[bold cyan]{span.service_name}[/] : [bold white]{span.name}[/]\n"
            f"Span ID: {span.span_id} | Kind: {span.kind} | Status: {span.status_code}\n"
            f"Duration: {span.duration_ms}ms\n"
            f"[dim]Attributes:[/]\n{attrs_formatted}"
        )
        panel_widget.update(Panel(content, title="Span Inspector", border_style="blue"))
