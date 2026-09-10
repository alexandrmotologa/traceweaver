"""Main Textual TUI Application for TraceWeaver."""

from textual.app import App

from traceweaver.config import settings
from traceweaver.engine.store import TraceStore
from traceweaver.tui.screens.trace_list import TraceListScreen

TUI_CSS = """
Screen {
    background: #0b0f19;
}

Header {
    background: #111827;
    color: #38bdf8;
    dock: top;
}

#main_container, #waterfall_main, #stats_container {
    padding: 1 2;
}

#search_bar, #waterfall_header {
    height: 3;
    margin-bottom: 1;
    align: left middle;
}

#app_heading, #trace_title, #stats_title {
    color: #38bdf8;
    text-style: bold;
    width: 40%;
}

#search_input {
    width: 60%;
    border: tall #1f2937;
    background: #0f172a;
    color: #f1f5f9;
}

DataTable {
    background: #0f172a;
    border: round #1f2937;
    color: #e2e8f0;
}

DataTable > .datatable--cursor {
    background: #1e293b;
    color: #38bdf8;
    text-style: bold;
}

#span_detail_panel {
    height: 12;
    margin-top: 1;
}
"""


class TraceWeaverApp(App):
    """Interactive terminal user interface for TraceWeaver."""

    CSS = TUI_CSS
    TITLE = "TraceWeaver"
    SUB_TITLE = "Distributed Tracing Correlator"

    def __init__(self, store: TraceStore | None = None):
        super().__init__()
        self.store = store or TraceStore(db_path=settings.db_path, max_spans=settings.max_spans)

    def on_mount(self) -> None:
        self.push_screen(TraceListScreen(store=self.store))
