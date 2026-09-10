"""Command-line interface for TraceWeaver."""

import asyncio
import sys
import time

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from traceweaver.config import settings
from traceweaver.demo import generate_demo_trace
from traceweaver.engine.correlator import CausalNode, TraceCorrelator
from traceweaver.engine.store import TraceStore
from traceweaver.receiver.otlp_grpc import start_grpc_server
from traceweaver.tui.app import TraceWeaverApp
from traceweaver.web.server import create_app

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="traceweaver",
    help="Distributed trace correlator and causal event waterfall visualizer.",
    add_completion=False,
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option(settings.host, "--host", "-h", help="Host interface to bind"),
    web_port: int = typer.Option(settings.web_port, "--web-port", "-w", help="Web console port"),
    grpc_port: int = typer.Option(settings.grpc_port, "--grpc-port", "-g", help="OTLP gRPC port"),
    db_path: str = typer.Option(settings.db_path, "--db-path", "-d", help="DuckDB database path"),
    max_spans: int = typer.Option(
        settings.max_spans, "--max-spans", "-m", help="Rolling retention buffer limit"
    ),
) -> None:
    """Launch TraceWeaver OTLP receivers and web console."""
    console.print(
        Panel(
            f"[bold cyan]TraceWeaver[/] — Distributed Trace Correlator & Waterfall Visualizer\n"
            f"[dim]Web Dashboard & OTLP HTTP:[/] [bold green]http://{host}:{web_port}[/]\n"
            f"[dim]OTLP gRPC Receiver:[/]        [bold green]{host}:{grpc_port}[/]\n"
            f"[dim]DuckDB Columnar Store:[/]     [bold yellow]{db_path}[/] (max {max_spans:,} spans)",
            title="[bold white]Service Initializing[/]",
            border_style="cyan",
        )
    )

    store = TraceStore(db_path=db_path, max_spans=max_spans)
    fastapi_app = create_app(store)

    async def run_servers() -> None:
        grpc_server = await start_grpc_server(store=store, host=host, port=grpc_port)
        config = uvicorn.Config(app=fastapi_app, host=host, port=web_port, log_level="info")
        server = uvicorn.Server(config)
        try:
            await server.serve()
        finally:
            await grpc_server.stop(grace=1.0)
            store.close()

    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        console.print("\n[yellow]TraceWeaver stopped by user.[/]")


@app.command()
def tui(
    db_path: str = typer.Option(settings.db_path, "--db-path", "-d", help="DuckDB database path"),
) -> None:
    """Launch the interactive terminal TUI dashboard."""
    store = TraceStore(db_path=db_path)
    tui_app = TraceWeaverApp(store=store)
    tui_app.run()


@app.command()
def demo(
    count: int = typer.Option(10, "--count", "-n", help="Number of demo traces to emit"),
    rate: float = typer.Option(2.0, "--rate", "-r", help="Traces per second"),
    dwell_ms: float = typer.Option(340.0, "--dwell", help="Target queue dwell time in ms"),
    endpoint: str | None = typer.Option(
        None,
        "--endpoint",
        "-e",
        help="Optional OTLP HTTP endpoint (e.g. http://localhost:8080/v1/traces)",
    ),
    db_path: str = typer.Option(
        settings.db_path, "--db-path", "-d", help="DuckDB database path if local"
    ),
) -> None:
    """Stream realistic synthetic distributed traces with queue dwell times."""
    import httpx

    console.print(
        f"[cyan]Generating {count} synthetic distributed traces "
        f"with ~{dwell_ms}ms queue dwell times...[/]"
    )

    store = None if endpoint else TraceStore(db_path=db_path)
    client = httpx.Client(timeout=5.0) if endpoint else None

    try:
        for idx in range(1, count + 1):
            has_error = idx % 4 == 0
            spans = generate_demo_trace(
                trace_idx=idx,
                base_dwell_ms=dwell_ms,
                inject_error=has_error,
            )

            if endpoint and client:
                payload = {
                    "resourceSpans": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "service.name",
                                        "value": {"stringValue": s.service_name},
                                    }
                                ]
                            },
                            "scopeSpans": [
                                {
                                    "spans": [
                                        {
                                            "traceId": s.trace_id,
                                            "spanId": s.span_id,
                                            "parentSpanId": s.parent_span_id,
                                            "name": s.name,
                                            "startTimeUnixNano": str(s.start_time_ns),
                                            "endTimeUnixNano": str(s.end_time_ns),
                                            "status": {
                                                "code": 2 if s.status_code == "ERROR" else 1
                                            },
                                            "attributes": [
                                                {"key": k, "value": {"stringValue": str(v)}}
                                                for k, v in s.attributes.items()
                                            ],
                                            "links": [
                                                {
                                                    "traceId": lk.trace_id,
                                                    "spanId": lk.span_id,
                                                    "attributes": [
                                                        {"key": k, "value": {"stringValue": str(v)}}
                                                        for k, v in lk.attributes.items()
                                                    ],
                                                }
                                                for lk in s.links
                                            ],
                                        }
                                    ]
                                }
                            ],
                        }
                        for s in spans
                    ]
                }
                res = client.post(endpoint, json=payload)
                if res.status_code != 200:
                    console.print(f"[red]Error sending trace {idx}: {res.text}[/]")
            elif store:
                store.insert_spans(spans)

            trace_id = spans[0].trace_id
            status = "[bold red]ERR[/]" if has_error else "[bold green]OK[/]"
            console.print(
                f"  [{idx}/{count}] Emitted trace [cyan]{trace_id[:12]}...[/] "
                f"({len(spans)} spans) Status: {status}"
            )

            if idx < count and rate > 0:
                time.sleep(1.0 / rate)

        console.print("[bold green]Success:[/] All synthetic traces successfully generated.")
    finally:
        if client:
            client.close()
        if store:
            store.close()


@app.command()
def analyze(
    trace_id: str = typer.Argument(..., help="Trace ID to analyze"),
    db_path: str = typer.Option(settings.db_path, "--db-path", "-d", help="DuckDB database path"),
) -> None:
    """Print ASCII causal waterfall and queue dwell time analysis for a trace."""
    store = TraceStore(db_path=db_path)
    spans = store.get_trace_spans(trace_id)
    if not spans:
        console.print(f"[bold red]Trace {trace_id} not found in store.[/]")
        sys.exit(1)

    correlator = TraceCorrelator()
    dag = correlator.correlate_trace(spans)

    console.print(
        Panel(
            f"[bold cyan]Trace:[/] {trace_id}\n"
            f"[dim]Total Duration:[/]   [bold green]{dag.total_duration_ms}ms[/]\n"
            f"[dim]Queue Dwell Time:[/] [bold yellow]{dag.total_dwell_time_ms}ms[/]\n"
            f"[dim]Spans Count:[/]      {dag.span_count}\n"
            f"[dim]Critical Path:[/]    {' -> '.join(dag.critical_path_span_ids)}",
            title="[bold white]Trace Analysis Report[/]",
            border_style="cyan",
        )
    )

    table = Table(title="Causal Execution Waterfall", border_style="dim")
    table.add_column("Causal Hierarchy & Service", style="cyan")
    table.add_column("Operation", style="white")
    table.add_column("Duration", justify="right")
    table.add_column("Timeline Gantt", justify="left")

    max_dur = max(1.0, dag.total_duration_ms)
    cols = 35

    def traverse(node: CausalNode) -> None:
        for dwell in node.dwell_intervals:
            dw_off = int((max(0.0, node.offset_ms - dwell.dwell_time_ms) / max_dur) * cols)
            dw_len = max(2, int((dwell.dwell_time_ms / max_dur) * cols))
            table.add_row(
                "  " * node.depth + f"░░ Queue: {dwell.queue_name}",
                "[italic]message waiting in broker[/]",
                f"[bold yellow]{dwell.dwell_time_ms}ms[/]",
                f"[yellow]{' ' * dw_off}{'░' * dw_len}[/]",
            )

        indent = "  " * node.depth + ("└── " if node.depth > 0 else "")
        label = f"{indent}[bold cyan]{node.span.service_name}[/]"
        op_name = node.span.name
        if node.is_critical_path:
            op_name += " [bold red]🔥 CP[/]"

        off = int((node.offset_ms / max_dur) * cols)
        length = max(1, int((node.span.duration_ms / max_dur) * cols))
        bar_color = (
            "red"
            if node.span.status_code == "ERROR"
            else ("bold red" if node.is_critical_path else "green")
        )
        bar = f"[{bar_color}]{' ' * off}{'█' * length}[/]"

        table.add_row(label, op_name, f"{node.span.duration_ms}ms", bar)
        for ch in node.children:
            traverse(ch)

    for r in dag.root_nodes:
        traverse(r)

    console.print(table)
    store.close()


if __name__ == "__main__":
    app()
