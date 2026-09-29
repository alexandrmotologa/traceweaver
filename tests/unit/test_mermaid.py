"""Unit tests for Mermaid exporter."""

from traceweaver.engine.correlator import TraceCorrelator
from traceweaver.engine.mermaid import export_mermaid_sequence
from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink


def test_export_mermaid_sequence():
    """Verify Mermaid sequence diagram includes participants and dwell notes."""
    spans = [
        NormalizedSpan(
            trace_id="t_mermaid",
            span_id="s1",
            name="POST /checkout",
            service_name="api-gateway",
            start_time_ns=1_000_000_000_000,
            end_time_ns=1_000_020_000_000,
            duration_ms=20.0,
        ),
        NormalizedSpan(
            trace_id="t_mermaid",
            span_id="s2",
            name="charge_card",
            service_name="payment-worker",
            start_time_ns=1_000_150_000_000,
            end_time_ns=1_000_200_000_000,
            duration_ms=50.0,
            attributes={"messaging.destination": "orders.kafka"},
            links=[SpanLink(trace_id="t_mermaid", span_id="s1")],
        ),
    ]

    correlator = TraceCorrelator()
    dag = correlator.correlate_trace(spans)
    mermaid = export_mermaid_sequence(dag)

    assert "sequenceDiagram" in mermaid
    assert "participant api_gateway as api-gateway" in mermaid
    assert "participant payment_worker as payment-worker" in mermaid
    assert "Queue Dwell: 130.0ms (orders.kafka)" in mermaid
