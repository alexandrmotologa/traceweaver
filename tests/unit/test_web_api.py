"""Unit tests for TraceWeaver web server and REST API."""

import pytest
from httpx import ASGITransport, AsyncClient

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink
from traceweaver.web.server import create_app


@pytest.fixture
def web_test_app():
    """Create test FastAPI application with pre-populated in-memory TraceStore."""
    store = TraceStore(db_path=":memory:")
    spans = [
        NormalizedSpan(
            trace_id="test_trace_123",
            span_id="span_root",
            parent_span_id=None,
            name="POST /checkout",
            service_name="api-gateway",
            kind="SERVER",
            start_time_ns=1_000_000_000_000,
            end_time_ns=1_000_050_000_000,
            duration_ms=50.0,
            status_code="OK",
            attributes={"http.method": "POST"},
        ),
        NormalizedSpan(
            trace_id="test_trace_123",
            span_id="span_worker",
            parent_span_id=None,
            name="process_order",
            service_name="worker-service",
            kind="CONSUMER",
            start_time_ns=1_000_200_000_000,  # 150ms dwell time
            end_time_ns=1_000_280_000_000,  # 80ms processing
            duration_ms=80.0,
            status_code="OK",
            attributes={"messaging.destination": "orders.topic"},
            links=[
                SpanLink(
                    trace_id="test_trace_123",
                    span_id="span_root",
                    attributes={"messaging.operation": "receive"},
                )
            ],
        ),
    ]
    store.insert_spans(spans)
    app = create_app(store)
    yield app, store
    store.close()


@pytest.mark.asyncio
async def test_healthz_endpoint(web_test_app):
    """Verify /healthz endpoint returns store count."""
    app, _store = web_test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["total_spans"] == 2


@pytest.mark.asyncio
async def test_list_traces_endpoint(web_test_app):
    """Verify /api/v1/traces returns trace summaries."""
    app, _store = web_test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/traces")
    assert res.status_code == 200
    traces = res.json()
    assert len(traces) == 1
    assert traces[0]["trace_id"] == "test_trace_123"
    assert traces[0]["span_count"] == 2


@pytest.mark.asyncio
async def test_get_trace_dag_endpoint(web_test_app):
    """Verify /api/v1/traces/{trace_id} returns full causal DAG with dwell time."""
    app, _store = web_test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/traces/test_trace_123")
    assert res.status_code == 200
    dag = res.json()
    assert dag["trace_id"] == "test_trace_123"
    assert dag["total_dwell_time_ms"] == 150.0
    assert len(dag["root_nodes"]) == 1
    root = dag["root_nodes"][0]
    assert root["span"]["span_id"] == "span_root"
    assert len(root["children"]) == 1
    child = root["children"][0]
    assert child["span"]["span_id"] == "span_worker"
    assert len(child["dwell_intervals"]) == 1
    assert child["dwell_intervals"][0]["dwell_time_ms"] == 150.0


@pytest.mark.asyncio
async def test_analytics_endpoints(web_test_app):
    """Verify analytics endpoints return valid metrics."""
    app, _store = web_test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        services_res = await client.get("/api/v1/analytics/services")
        overview_res = await client.get("/api/v1/analytics/overview")

    assert services_res.status_code == 200
    services = services_res.json()
    assert len(services) == 2

    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["total_spans"] == 2
    assert overview["recent_traces_count"] == 1
