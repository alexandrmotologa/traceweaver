"""Unit tests for TraceDiffEngine."""

from traceweaver.engine.diff import TraceDiffEngine
from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink


def test_trace_diff_identifies_queue_dwell_regression():
    """Verify trace diff accurately identifies queue dwell regressions."""
    engine = TraceDiffEngine()

    # Fast Trace A (50ms dwell in Kafka)
    spans_a = [
        NormalizedSpan(
            trace_id="trace_fast",
            span_id="s1",
            parent_span_id=None,
            name="POST /orders",
            service_name="gateway",
            start_time_ns=1_000_000_000_000,
            end_time_ns=1_000_020_000_000,
            duration_ms=20.0,
        ),
        NormalizedSpan(
            trace_id="trace_fast",
            span_id="s2",
            parent_span_id=None,
            name="process_payment",
            service_name="payment-worker",
            start_time_ns=1_000_070_000_000,  # 50ms dwell
            end_time_ns=1_000_120_000_000,
            duration_ms=50.0,
            attributes={"messaging.destination": "orders.events"},
            links=[SpanLink(trace_id="trace_fast", span_id="s1")],
        ),
    ]

    # Slow Trace B (350ms dwell in Kafka - 300ms regression!)
    spans_b = [
        NormalizedSpan(
            trace_id="trace_slow",
            span_id="sb1",
            parent_span_id=None,
            name="POST /orders",
            service_name="gateway",
            start_time_ns=2_000_000_000_000,
            end_time_ns=2_000_020_000_000,
            duration_ms=20.0,
        ),
        NormalizedSpan(
            trace_id="trace_slow",
            span_id="sb2",
            parent_span_id=None,
            name="process_payment",
            service_name="payment-worker",
            start_time_ns=2_000_370_000_000,  # 350ms dwell!
            end_time_ns=2_000_420_000_000,
            duration_ms=50.0,
            attributes={"messaging.destination": "orders.events"},
            links=[SpanLink(trace_id="trace_slow", span_id="sb1")],
        ),
    ]

    diff = engine.compare_traces(spans_a, spans_b)

    assert diff.trace_a_id == "trace_fast"
    assert diff.trace_b_id == "trace_slow"
    assert diff.duration_a_ms == 120.0
    assert diff.duration_b_ms == 420.0
    assert diff.duration_delta_ms == 300.0
    assert diff.dwell_delta_ms == 300.0
    assert len(diff.queues) == 1
    assert diff.queues[0].queue_name == "orders.events"
    assert diff.queues[0].delta_ms == 300.0
    assert "Queue dwell latency regression in 'orders.events'" in diff.primary_bottleneck
