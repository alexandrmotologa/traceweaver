"""FastAPI web server serving REST endpoints, WebSocket live feed, and SVG dashboard."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from traceweaver.config import settings
from traceweaver.engine.correlator import CausalTraceDAG, TraceCorrelator
from traceweaver.engine.store import ServiceStats, TraceStore, TraceSummary
from traceweaver.receiver.otlp_http import router as otlp_router
from traceweaver.receiver.otlp_http import set_trace_store
from traceweaver.receiver.span_normalizer import NormalizedSpan

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class ConnectionManager:
    """Manages active WebSocket connections for live trace streaming."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for s in stale:
            self.disconnect(s)


def create_app(store: TraceStore | None = None) -> FastAPI:
    """Create and configure FastAPI application."""
    app_store = store or TraceStore(db_path=settings.db_path, max_spans=settings.max_spans)
    ws_manager = ConnectionManager()
    correlator = TraceCorrelator()

    # Define broadcast callback for incoming spans
    def on_spans_received(spans: list[NormalizedSpan]) -> None:
        if not ws_manager.active_connections or not spans:
            return
        summary_payload = {
            "type": "spans_ingested",
            "count": len(spans),
            "trace_ids": list({s.trace_id for s in spans}),
        }
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(ws_manager.broadcast_json(summary_payload), loop)
        except Exception:
            pass

    set_trace_store(app_store, broadcast_callback=on_spans_received)

    app = FastAPI(
        title="TraceWeaver",
        description="Distributed Trace Correlator & Causal Event Waterfall Visualizer",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount OTLP HTTP receiver
    app.include_router(otlp_router)

    # Store reference on app state
    app.state.store = app_store
    app.state.ws_manager = ws_manager
    app.state.correlator = correlator

    # REST Endpoints
    @app.get("/healthz")
    async def health_check() -> dict[str, Any]:
        """Health check and high-level storage stats."""
        return {
            "status": "healthy",
            "total_spans": app_store.total_spans_count(),
            "version": "0.1.0",
        }

    @app.get("/api/v1/traces", response_model=list[TraceSummary])
    async def list_traces(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        service: str | None = None,
        min_duration_ms: float | None = None,
        error_only: bool = False,
    ) -> list[TraceSummary]:
        """Retrieve paginated list of root traces with status and duration."""
        return app_store.get_traces(
            limit=limit,
            offset=offset,
            service_name=service,
            min_duration_ms=min_duration_ms,
            error_only=error_only,
        )

    @app.get("/api/v1/traces/{trace_id}", response_model=CausalTraceDAG)
    async def get_trace_dag(trace_id: str) -> CausalTraceDAG:
        """Retrieve full causal DAG, dwell times, and critical path for a trace."""
        spans = app_store.get_trace_spans(trace_id)
        if not spans:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        # Update correlator with fresh service stats
        stats_list = app_store.get_service_analytics()
        stats_map = {s.service_name: s for s in stats_list}
        app.state.correlator.service_stats_map = stats_map

        return app.state.correlator.correlate_trace(spans)

    @app.get("/api/v1/analytics/services", response_model=list[ServiceStats])
    async def get_service_analytics() -> list[ServiceStats]:
        """Retrieve latency percentiles and error metrics aggregated by service."""
        return app_store.get_service_analytics()

    @app.get("/api/v1/analytics/overview")
    async def get_overview_analytics() -> dict[str, Any]:
        """Retrieve high-level system overview analytics."""
        traces = app_store.get_traces(limit=100)
        services = app_store.get_service_analytics()

        total_traces = len(traces)
        err_traces = sum(1 for t in traces if t.has_error)
        avg_trace_dur = (
            round(sum(t.duration_ms for t in traces) / total_traces, 2) if total_traces > 0 else 0.0
        )

        return {
            "total_spans": app_store.total_spans_count(),
            "recent_traces_count": total_traces,
            "error_trace_rate": round(err_traces * 100.0 / max(1, total_traces), 1),
            "avg_trace_duration_ms": avg_trace_dur,
            "active_services_count": len(services),
        }

    @app.websocket("/api/v1/ws/traces")
    async def websocket_traces_feed(websocket: WebSocket) -> None:
        """WebSocket endpoint for live trace streaming."""
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keepalive ping/pong
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception:
            ws_manager.disconnect(websocket)

    # Static web dashboard
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        @app.get("/ui", include_in_schema=False)
        async def serve_dashboard() -> FileResponse:
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return JSONResponse({"message": "Web UI index.html not found"}, status_code=404)

    return app
