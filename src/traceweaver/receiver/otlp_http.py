"""OTLP HTTP Receiver implementation for /v1/traces."""

import json
from collections.abc import Callable

from fastapi import APIRouter, Header, HTTPException, Request, Response

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.span_normalizer import (
    NormalizedSpan,
    parse_otlp_json,
    parse_otlp_protobuf,
)

router = APIRouter(tags=["OTLP Ingestion"])

# Global store reference injected at startup
_store: TraceStore | None = None
_broadcast_callback: Callable[[list[NormalizedSpan]], None] | None = None


def set_trace_store(
    store: TraceStore,
    broadcast_callback: Callable[[list[NormalizedSpan]], None] | None = None,
) -> None:
    """Register storage backend and optional broadcast callback."""
    global _store, _broadcast_callback
    _store = store
    _broadcast_callback = broadcast_callback


@router.post("/v1/traces")
async def ingest_otlp_traces(
    request: Request,
    content_type: str | None = Header(None),
) -> Response:
    """Accept standard OpenTelemetry OTLP JSON or Protobuf trace payloads."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Trace store not initialized")

    body = await request.body()
    if not body:
        return Response(
            content=json.dumps({"partialSuccess": {}}),
            media_type="application/json",
            status_code=200,
        )

    spans: list[NormalizedSpan] = []
    ct = (content_type or "").lower()

    if "protobuf" in ct or "x-protobuf" in ct or (body and body[:1] == b"\n"):
        try:
            spans = parse_otlp_protobuf(body)
        except Exception as err:
            raise HTTPException(
                status_code=400, detail=f"Failed to decode OTLP Protobuf payload: {err}"
            ) from err
    else:
        try:
            payload = json.loads(body.decode("utf-8"))
            spans = parse_otlp_json(payload)
        except Exception as err:
            raise HTTPException(
                status_code=400, detail=f"Failed to decode OTLP JSON payload: {err}"
            ) from err

    if spans:
        _store.insert_spans(spans)
        if _broadcast_callback:
            try:
                _broadcast_callback(spans)
            except Exception:
                pass

    return Response(
        content=json.dumps({"partialSuccess": {}}),
        media_type="application/json",
        status_code=200,
    )
