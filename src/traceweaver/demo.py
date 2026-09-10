"""Synthetic distributed trace generator for multi-service architectures."""

import random
import time
import uuid

from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanLink


def generate_demo_trace(
    trace_idx: int = 1,
    base_dwell_ms: float = 320.0,
    inject_error: bool = False,
) -> list[NormalizedSpan]:
    """Generate a realistic distributed trace across gateway, outbox, Kafka, and worker services.

    Simulates the flow:
    IdemGate (REST) -> OrderEngine (Outbox) -> WalPulse (CDC) -> Kafka (Dwell) -> PaymentWorker
    """
    trace_id = uuid.uuid4().hex
    now_ns = time.time_ns()

    # Span 1: API Gateway (IdemGate)
    s1_id = uuid.uuid4().hex[:16]
    s1_dur_ms = random.uniform(15.0, 30.0)
    s1_start = now_ns
    s1_end = s1_start + int(s1_dur_ms * 1_000_000)

    span_gateway = NormalizedSpan(
        trace_id=trace_id,
        span_id=s1_id,
        parent_span_id=None,
        name="POST /api/v1/orders",
        service_name="idemgate",
        kind="SERVER",
        start_time_ns=s1_start,
        end_time_ns=s1_end,
        duration_ms=round(s1_dur_ms, 2),
        status_code="OK",
        attributes={
            "http.method": "POST",
            "http.route": "/api/v1/orders",
            "http.status_code": 201,
            "idempotency.key": f"key_{trace_idx}_{s1_id[:6]}",
        },
    )

    # Span 2: Order Engine (Core transactional processing)
    s2_id = uuid.uuid4().hex[:16]
    s2_dur_ms = random.uniform(35.0, 60.0)
    s2_start = s1_start + int(2.0 * 1_000_000)
    s2_end = s2_start + int(s2_dur_ms * 1_000_000)

    span_order = NormalizedSpan(
        trace_id=trace_id,
        span_id=s2_id,
        parent_span_id=s1_id,
        name="order_engine.process_checkout",
        service_name="order-engine",
        kind="INTERNAL",
        start_time_ns=s2_start,
        end_time_ns=s2_end,
        duration_ms=round(s2_dur_ms, 2),
        status_code="OK",
        attributes={
            "order.id": f"ord_{1000 + trace_idx}",
            "order.total_amount": round(random.uniform(25.0, 450.0), 2),
            "order.items_count": random.randint(1, 5),
        },
    )

    # Span 3: Transactional Outbox Insert (PostgreSQL)
    s3_id = uuid.uuid4().hex[:16]
    s3_dur_ms = random.uniform(4.0, 10.0)
    s3_start = s2_end - int((s3_dur_ms + 1.0) * 1_000_000)
    s3_end = s3_start + int(s3_dur_ms * 1_000_000)

    span_outbox = NormalizedSpan(
        trace_id=trace_id,
        span_id=s3_id,
        parent_span_id=s2_id,
        name="db.insert_outbox_event",
        service_name="order-engine",
        kind="CLIENT",
        start_time_ns=s3_start,
        end_time_ns=s3_end,
        duration_ms=round(s3_dur_ms, 2),
        status_code="OK",
        attributes={
            "db.system": "postgresql",
            "db.statement": "INSERT INTO outbox_table (event_type, payload) VALUES ($1, $2)",
        },
    )

    # Span 4: WalPulse CDC Relaying to Kafka
    s4_id = uuid.uuid4().hex[:16]
    s4_dur_ms = random.uniform(3.0, 8.0)
    s4_start = s3_end + int(random.uniform(1.0, 3.0) * 1_000_000)
    s4_end = s4_start + int(s4_dur_ms * 1_000_000)

    span_cdc = NormalizedSpan(
        trace_id=trace_id,
        span_id=s4_id,
        parent_span_id=s3_id,
        name="walpulse.publish_to_kafka",
        service_name="walpulse",
        kind="PRODUCER",
        start_time_ns=s4_start,
        end_time_ns=s4_end,
        duration_ms=round(s4_dur_ms, 2),
        status_code="OK",
        attributes={
            "messaging.system": "kafka",
            "messaging.destination": "orders.events",
            "kafka.partition": random.randint(0, 3),
            "queue_entry_ts": s4_end,
        },
    )

    # ASYNCHRONOUS BOUNDARY: Event sits in Kafka partition for dwell_time_ms!
    dwell_variation = random.uniform(-40.0, 60.0)
    actual_dwell_ms = max(50.0, base_dwell_ms + dwell_variation)
    s5_start = s4_end + int(actual_dwell_ms * 1_000_000)

    # Span 5: PaymentWorker consuming event from Kafka
    s5_id = uuid.uuid4().hex[:16]
    s5_dur_ms = random.uniform(45.0, 95.0)
    s5_end = s5_start + int(s5_dur_ms * 1_000_000)

    status_code = "ERROR" if inject_error else "OK"
    status_msg = "Payment authorization gateway timeout" if inject_error else None

    span_payment = NormalizedSpan(
        trace_id=trace_id,
        span_id=s5_id,
        parent_span_id=None,  # Asynchronous! No synchronous parent span!
        name="payment_worker.charge_card",
        service_name="payment-worker",
        kind="CONSUMER",
        start_time_ns=s5_start,
        end_time_ns=s5_end,
        duration_ms=round(s5_dur_ms, 2),
        status_code=status_code,
        status_message=status_msg,
        attributes={
            "messaging.system": "kafka",
            "messaging.destination": "orders.events",
            "messaging.consumer.group": "payment-processors",
            "payment.gateway": "stripe",
        },
        links=[
            SpanLink(
                trace_id=trace_id,
                span_id=s4_id,
                attributes={"messaging.operation": "receive"},
            )
        ],
    )

    return [span_gateway, span_order, span_outbox, span_cdc, span_payment]
