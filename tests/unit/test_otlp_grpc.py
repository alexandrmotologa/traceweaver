"""Unit tests for OTLP gRPC receiver."""

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.otlp_grpc import TraceServiceImpl


class DummyContext:
    """Mock gRPC context."""

    def __init__(self):
        self.aborted = False
        self.code = None
        self.details = None

    async def abort(self, code, details):
        self.aborted = True
        self.code = code
        self.details = details


@pytest.mark.asyncio
async def test_grpc_export_with_broadcast():
    """Verify TraceServiceImpl exports spans and invokes broadcast callback."""
    store = TraceStore(db_path=":memory:")
    broadcast_called = []

    def mock_broadcast(spans):
        broadcast_called.append(len(spans))

    servicer = TraceServiceImpl(store=store, broadcast_callback=mock_broadcast)

    # Build ExportTraceServiceRequest with 1 span
    req = ExportTraceServiceRequest()
    rs = req.resource_spans.add()
    kv = rs.resource.attributes.add()
    kv.key = "service.name"
    kv.value.string_value = "grpc-auth-service"

    ss = rs.scope_spans.add()
    span = ss.spans.add()
    span.trace_id = bytes.fromhex("1234567890abcdef1234567890abcdef")
    span.span_id = bytes.fromhex("abcdef1234567890")
    span.name = "Authenticate"
    span.start_time_unix_nano = 1_700_000_000_000_000_000
    span.end_time_unix_nano = 1_700_000_000_025_000_000

    ctx = DummyContext()
    await servicer.Export(req, ctx)

    assert not ctx.aborted
    assert len(broadcast_called) == 1
    assert broadcast_called[0] == 1

    stored_spans = store.get_trace_spans("1234567890abcdef1234567890abcdef")
    assert len(stored_spans) == 1
    assert stored_spans[0].service_name == "grpc-auth-service"
    assert stored_spans[0].duration_ms == 25.0

    store.close()
