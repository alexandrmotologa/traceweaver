"""Unit tests for OTLP HTTP receiver."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry.proto.trace.v1.trace_pb2 import TracesData

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.otlp_http import router, set_trace_store


@pytest.fixture
def app_with_store():
    """Create test FastAPI application with configured TraceStore."""
    store = TraceStore(db_path=":memory:")
    set_trace_store(store)
    app = FastAPI()
    app.include_router(router)
    yield app, store
    store.close()


@pytest.mark.asyncio
async def test_otlp_http_json_ingestion(app_with_store):
    """Test receiving OTLP traces formatted as JSON."""
    app, store = app_with_store
    transport = ASGITransport(app=app)

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "api-gateway"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "0123456789abcdef0123456789abcdef",
                                "spanId": "abcdef0123456789",
                                "name": "GET /health",
                                "kind": 2,
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000000010000000",
                                "status": {"code": 1},
                            }
                        ]
                    }
                ],
            }
        ]
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/traces",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json() == {"partialSuccess": {}}

    spans = store.get_trace_spans("0123456789abcdef0123456789abcdef")
    assert len(spans) == 1
    assert spans[0].service_name == "api-gateway"
    assert spans[0].duration_ms == 10.0


@pytest.mark.asyncio
async def test_otlp_http_protobuf_ingestion(app_with_store):
    """Test receiving OTLP traces formatted as Protobuf."""
    app, store = app_with_store
    transport = ASGITransport(app=app)

    traces_data = TracesData()
    rs = traces_data.resource_spans.add()
    kv = rs.resource.attributes.add()
    kv.key = "service.name"
    kv.value.string_value = "order-engine"

    ss = rs.scope_spans.add()
    span = ss.spans.add()
    span.trace_id = bytes.fromhex("fedcba9876543210fedcba9876543210")
    span.span_id = bytes.fromhex("9876543210fedcba")
    span.name = "process_order"
    span.start_time_unix_nano = 1700000000000000000
    span.end_time_unix_nano = 1700000000045000000

    raw_bytes = traces_data.SerializeToString()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/traces",
            content=raw_bytes,
            headers={"Content-Type": "application/x-protobuf"},
        )

    assert response.status_code == 200
    spans = store.get_trace_spans("fedcba9876543210fedcba9876543210")
    assert len(spans) == 1
    assert spans[0].service_name == "order-engine"
    assert spans[0].duration_ms == 45.0
