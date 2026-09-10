"""Unit tests for DuckDB trace storage and analytics."""

import pytest

from traceweaver.engine.store import TraceStore
from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink


@pytest.fixture
def store():
    """Create in-memory DuckDB store for testing."""
    s = TraceStore(db_path=":memory:", max_spans=10)
    yield s
    s.close()


def test_insert_and_get_trace_spans(store):
    """Test inserting spans and retrieving them by trace_id."""
    spans = [
        NormalizedSpan(
            trace_id="trace1",
            span_id="span1",
            parent_span_id=None,
            name="GET /api/users",
            service_name="gateway",
            kind="SERVER",
            start_time_ns=1000000000,
            end_time_ns=1050000000,
            duration_ms=50.0,
            status_code="OK",
            attributes={"http.method": "GET"},
        ),
        NormalizedSpan(
            trace_id="trace1",
            span_id="span2",
            parent_span_id="span1",
            name="SELECT users",
            service_name="user-db",
            kind="CLIENT",
            start_time_ns=1010000000,
            end_time_ns=1040000000,
            duration_ms=30.0,
            status_code="OK",
            attributes={"db.statement": "SELECT * FROM users"},
            links=[SpanLink(trace_id="trace1", span_id="span1", attributes={"source": "upstream"})],
        ),
    ]

    inserted = store.insert_spans(spans)
    assert inserted == 2

    retrieved = store.get_trace_spans("trace1")
    assert len(retrieved) == 2
    assert retrieved[0].span_id == "span1"
    assert retrieved[1].span_id == "span2"
    assert retrieved[1].parent_span_id == "span1"
    assert len(retrieved[1].links) == 1
    assert retrieved[1].links[0].span_id == "span1"


def test_get_traces_summary_and_filters(store):
    """Test trace list summaries and filters."""
    spans = [
        NormalizedSpan(
            trace_id="t1",
            span_id="s1",
            name="req1",
            service_name="auth",
            start_time_ns=100,
            end_time_ns=200,
            duration_ms=0.0001,
            status_code="OK",
        ),
        NormalizedSpan(
            trace_id="t2",
            span_id="s2",
            name="req2",
            service_name="orders",
            start_time_ns=300,
            end_time_ns=500,
            duration_ms=0.0002,
            status_code="ERROR",
        ),
    ]
    store.insert_spans(spans)

    # All traces
    all_traces = store.get_traces()
    assert len(all_traces) == 2

    # Filter error_only
    err_traces = store.get_traces(error_only=True)
    assert len(err_traces) == 1
    assert err_traces[0].trace_id == "t2"
    assert err_traces[0].has_error is True

    # Filter by service_name
    auth_traces = store.get_traces(service_name="auth")
    assert len(auth_traces) == 1
    assert auth_traces[0].trace_id == "t1"


def test_service_analytics(store):
    """Test DuckDB aggregation calculations for p50, p90, p99 and error rates."""
    spans = [
        NormalizedSpan(
            trace_id=f"t{i}",
            span_id=f"s{i}",
            name="call",
            service_name="search",
            start_time_ns=1000 * i,
            end_time_ns=1000 * i + int(duration * 1_000_000),
            duration_ms=duration,
            status_code="ERROR" if i == 5 else "OK",
        )
        for i, duration in enumerate([10.0, 20.0, 30.0, 40.0, 50.0, 100.0])
    ]
    store.insert_spans(spans)

    stats = store.get_service_analytics()
    assert len(stats) == 1
    search_stat = stats[0]
    assert search_stat.service_name == "search"
    assert search_stat.span_count == 6
    assert search_stat.p50_duration_ms > 0
    assert search_stat.error_count == 1
    assert round(search_stat.error_rate, 1) == 16.7
