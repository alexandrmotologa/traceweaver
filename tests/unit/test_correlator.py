"""Unit tests for CausalTraceDAG correlator, dwell time, and critical path."""

from traceweaver.engine.anomaly import AnomalyDetector
from traceweaver.engine.correlator import TraceCorrelator
from traceweaver.engine.store import ServiceStats
from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink


def test_correlate_synchronous_tree():
    """Verify building standard hierarchical parent-child trace."""
    spans = [
        NormalizedSpan(
            trace_id="t1",
            span_id="s1",
            parent_span_id=None,
            name="GET /api/v1/orders",
            service_name="api-gateway",
            start_time_ns=1_000_000_000,
            end_time_ns=1_100_000_000,
            duration_ms=100.0,
            status_code="OK",
        ),
        NormalizedSpan(
            trace_id="t1",
            span_id="s2",
            parent_span_id="s1",
            name="order_service.create",
            service_name="order-service",
            start_time_ns=1_010_000_000,
            end_time_ns=1_080_000_000,
            duration_ms=70.0,
            status_code="OK",
        ),
        NormalizedSpan(
            trace_id="t1",
            span_id="s3",
            parent_span_id="s2",
            name="db.insert_order",
            service_name="postgres",
            start_time_ns=1_020_000_000,
            end_time_ns=1_050_000_000,
            duration_ms=30.0,
            status_code="OK",
        ),
    ]

    correlator = TraceCorrelator()
    dag = correlator.correlate_trace(spans)

    assert dag.trace_id == "t1"
    assert dag.span_count == 3
    assert len(dag.root_nodes) == 1
    root = dag.root_nodes[0]
    assert root.span.span_id == "s1"
    assert len(root.children) == 1
    assert root.children[0].span.span_id == "s2"
    assert len(root.children[0].children) == 1
    assert root.children[0].children[0].span.span_id == "s3"
    assert "s1" in dag.critical_path_span_ids
    assert "s2" in dag.critical_path_span_ids
    assert "s3" in dag.critical_path_span_ids


def test_correlate_asynchronous_queue_boundary_and_dwell_time():
    """Verify stitching asynchronous spans using span links and calculating dwell time."""
    # Producer in order-engine completes at 1_000_000_050 ms
    # Consumer in payment-worker starts at 1_000_000_390 ms (340ms queue wait!)
    producer_span = NormalizedSpan(
        trace_id="trace_async_1",
        span_id="span_producer",
        parent_span_id="span_gateway",
        name="publish_order_created",
        service_name="order-service",
        kind="PRODUCER",
        start_time_ns=1_000_000_000_000,
        end_time_ns=1_000_000_050_000,  # 50us
        duration_ms=0.05,
        attributes={"messaging.system": "kafka", "messaging.destination": "orders.v1"},
    )

    # Consumer span has NO parent_span_id (started asynchronously in worker),
    # but links back to producer span!
    consumer_span = NormalizedSpan(
        trace_id="trace_async_1",
        span_id="span_consumer",
        parent_span_id=None,
        name="consume_order_created",
        service_name="payment-worker",
        kind="CONSUMER",
        start_time_ns=1_000_340_050_000,  # Exactly 340ms after producer finished!
        end_time_ns=1_000_420_050_000,  # 80ms processing duration
        duration_ms=80.0,
        links=[
            SpanLink(
                trace_id="trace_async_1",
                span_id="span_producer",
                attributes={"messaging.operation": "receive"},
            )
        ],
    )

    spans = [
        NormalizedSpan(
            trace_id="trace_async_1",
            span_id="span_gateway",
            parent_span_id=None,
            name="POST /checkout",
            service_name="gateway",
            start_time_ns=999_900_000_000,
            end_time_ns=1_000_050_000_000,
            duration_ms=150.0,
        ),
        producer_span,
        consumer_span,
    ]

    correlator = TraceCorrelator()
    dag = correlator.correlate_trace(spans)

    # The consumer span should be successfully stitched as a child of the producer span!
    assert len(dag.root_nodes) == 1
    root = dag.root_nodes[0]
    assert root.span.span_id == "span_gateway"
    assert len(root.children) == 1
    prod_node = root.children[0]
    assert prod_node.span.span_id == "span_producer"
    assert len(prod_node.children) == 1
    cons_node = prod_node.children[0]
    assert cons_node.span.span_id == "span_consumer"

    # Verify dwell time was calculated accurately
    assert len(cons_node.dwell_intervals) == 1
    dwell = cons_node.dwell_intervals[0]
    assert dwell.dwell_time_ms == 340.0
    assert dwell.queue_name == "orders.v1"
    assert dag.total_dwell_time_ms == 340.0


def test_anomaly_detection():
    """Verify anomaly detection against statistical baseline."""
    detector = AnomalyDetector(multiplier=2.0, min_threshold_ms=50.0)
    stats = ServiceStats(
        service_name="fraud-check",
        span_count=100,
        avg_duration_ms=20.0,
        p50_duration_ms=18.0,
        p90_duration_ms=25.0,
        p99_duration_ms=45.0,
        error_count=0,
        error_rate=0.0,
    )

    # Normal span (22ms, under p90 * 2.0 threshold)
    normal_span = NormalizedSpan(
        trace_id="t",
        span_id="s_norm",
        name="verify",
        service_name="fraud-check",
        start_time_ns=0,
        end_time_ns=22_000_000,
        duration_ms=22.0,
    )
    is_anomaly, reason = detector.inspect_span(normal_span, stats)
    assert is_anomaly is False
    assert reason is None

    # Anomalous span (150ms, way above baseline)
    slow_span = NormalizedSpan(
        trace_id="t",
        span_id="s_slow",
        name="verify",
        service_name="fraud-check",
        start_time_ns=0,
        end_time_ns=150_000_000,
        duration_ms=150.0,
    )
    is_anomaly, reason = detector.inspect_span(slow_span, stats)
    assert is_anomaly is True
    assert "Latency 150.0ms is 6.0x above service p90 baseline" in reason
