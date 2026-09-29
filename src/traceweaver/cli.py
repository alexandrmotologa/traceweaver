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
        callback = getattr(fastapi_app.state, "broadcast_callback", None)
        grpc_server = await start_grpc_server(
            store=store, host=host, port=grpc_port, broadcast_callback=callback
        )
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
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, mermaid, json"
    ),
    db_path: str = typer.Option(settings.db_path, "--db-path", "-d", help="DuckDB database path"),
) -> None:
    """Print causal waterfall, Mermaid sequence diagram, or JSON analysis for a trace."""
    store = TraceStore(db_path=db_path)
    spans = store.get_trace_spans(trace_id)
    if not spans:
        console.print(f"[bold red]Trace {trace_id} not found in store.[/]")
        sys.exit(1)

    correlator = TraceCorrelator()
    dag = correlator.correlate_trace(spans)

    if format.lower() == "json":
        print(dag.model_dump_json(indent=2))
        store.close()
        return

    if format.lower() == "mermaid":
        from traceweaver.engine.mermaid import export_mermaid_sequence

        print(export_mermaid_sequence(dag))
        store.close()
        return

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


@app.command()
def diff(
    trace_a: str = typer.Argument(..., help="Baseline trace ID (Trace A)"),
    trace_b: str = typer.Argument(..., help="Comparison trace ID (Trace B)"),
    db_path: str = typer.Option(settings.db_path, "--db-path", "-d", help="DuckDB database path"),
    json_output: bool = typer.Option(False, "--json", help="Output raw diff JSON"),
) -> None:
    """Compare two traces and identify regressions in service latency and queue dwell times."""
    from traceweaver.engine.diff import TraceDiffEngine

    store = TraceStore(db_path=db_path)
    spans_a = store.get_trace_spans(trace_a)
    spans_b = store.get_trace_spans(trace_b)

    if not spans_a:
        console.print(f"[bold red]Baseline trace {trace_a} not found.[/]")
        sys.exit(1)
    if not spans_b:
        console.print(f"[bold red]Comparison trace {trace_b} not found.[/]")
        sys.exit(1)

    engine = TraceDiffEngine()
    result = engine.compare_traces(spans_a, spans_b)

    if json_output:
        print(result.model_dump_json(indent=2))
        store.close()
        return

    delta_color = "red" if result.duration_delta_ms > 0 else "green"
    sign = "+" if result.duration_delta_ms > 0 else ""

    console.print(
        Panel(
            f"[bold cyan]Comparing Trace A ({trace_a[:12]}...) vs Trace B ({trace_b[:12]}...)[/]\n"
            f"[dim]Duration A:[/]       {result.duration_a_ms}ms\n"
            f"[dim]Duration B:[/]       {result.duration_b_ms}ms\n"
            f"[dim]Latency Delta:[/]    [{delta_color}]{sign}{result.duration_delta_ms}ms ({sign}{result.duration_pct_change}%)[/]\n"
            f"[dim]Queue Dwell Delta:[/] {sign}{result.dwell_delta_ms}ms\n"
            f"[dim]Primary Bottleneck:[/] [bold yellow]{result.primary_bottleneck}[/]",
            title="[bold white]Causal Trace Regression Diff[/]",
            border_style="cyan",
        )
    )

    if result.services:
        svc_table = Table(title="Service-Level Latency Comparison", border_style="dim")
        svc_table.add_column("Service", style="cyan")
        svc_table.add_column("Trace A", justify="right")
        svc_table.add_column("Trace B", justify="right")
        svc_table.add_column("Delta", justify="right")

        for s in result.services:
            d_col = "red" if s.delta_ms > 5.0 else ("green" if s.delta_ms < -5.0 else "dim")
            s_sign = "+" if s.delta_ms > 0 else ""
            svc_table.add_row(
                s.service_name,
                f"{s.duration_a_ms}ms",
                f"{s.duration_b_ms}ms",
                f"[{d_col}]{s_sign}{s.delta_ms}ms[/]",
            )
        console.print(svc_table)

    if result.queues:
        q_table = Table(title="Queue Dwell Latency Comparison", border_style="dim")
        q_table.add_column("Queue Name", style="yellow")
        q_table.add_column("Trace A Dwell", justify="right")
        q_table.add_column("Trace B Dwell", justify="right")
        q_table.add_column("Delta", justify="right")

        for q in result.queues:
            d_col = "red" if q.delta_ms > 5.0 else ("green" if q.delta_ms < -5.0 else "dim")
            q_sign = "+" if q.delta_ms > 0 else ""
            q_table.add_row(
                q.queue_name,
                f"{q.dwell_a_ms}ms",
                f"{q.dwell_b_ms}ms",
                f"[{d_col}]{q_sign}{q.delta_ms}ms[/]",
            )
        console.print(q_table)

    store.close()


if __name__ == "__main__":
    app()
