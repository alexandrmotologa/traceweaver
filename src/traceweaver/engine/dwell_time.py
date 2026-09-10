"""Queue dwell time calculation engine for asynchronous message boundaries."""

from typing import Any

from pydantic import BaseModel

from traceweaver.receiver.span_normalizer import NormalizedSpan


class DwellInterval(BaseModel):
    """Represents an idle/dwell interval in an asynchronous queue or buffer."""

    producer_span_id: str
    consumer_span_id: str
    queue_name: str
    dwell_time_ms: float
    start_time_ns: int
    end_time_ns: int


def extract_enqueue_timestamp_ns(attributes: dict[str, Any]) -> int | None:
    """Look for standard enqueue timestamps in span attributes."""
    candidate_keys = [
        "queue_entry_ts",
        "messaging.kafka.message.timestamp",
        "messaging.publish_time",
        "messaging.enqueue_time",
        "queue.entry_time",
    ]

    for key in candidate_keys:
        val = attributes.get(key)
        if val is not None:
            try:
                num = int(val)
                # If milliseconds (e.g. 13 digits ~ 1700000000000), convert to ns
                if num < 10_000_000_000_000:
                    return num * 1_000_000
                return num
            except (ValueError, TypeError):
                continue

    return None


def extract_queue_name(producer: NormalizedSpan | None, consumer: NormalizedSpan) -> str:
    """Derive destination queue or topic name from span attributes."""
    for s in (consumer, producer):
        if s is None:
            continue
        for key in (
            "messaging.destination",
            "messaging.destination.name",
            "kafka.topic",
            "messaging.kafka.topic",
            "queue.name",
        ):
            val = s.attributes.get(key)
            if val:
                return str(val)

    return "event-queue"


def calculate_dwell_time(
    consumer_span: NormalizedSpan,
    producer_span: NormalizedSpan | None = None,
) -> DwellInterval | None:
    """Calculate asynchronous queue dwell time between message production and consumption.

    Returns a DwellInterval if a positive delay is detected.
    """
    queue_name = extract_queue_name(producer_span, consumer_span)

    # Method 1: Gap between producer span end time and consumer span start time
    if producer_span is not None and consumer_span.start_time_ns > producer_span.end_time_ns:
        dwell_ns = consumer_span.start_time_ns - producer_span.end_time_ns
        dwell_ms = round(dwell_ns / 1_000_000.0, 2)
        if dwell_ms > 0.0:
            return DwellInterval(
                producer_span_id=producer_span.span_id,
                consumer_span_id=consumer_span.span_id,
                queue_name=queue_name,
                dwell_time_ms=dwell_ms,
                start_time_ns=producer_span.end_time_ns,
                end_time_ns=consumer_span.start_time_ns,
            )

    # Method 2: Enqueue timestamp attribute in consumer attributes
    enqueue_ts_ns = extract_enqueue_timestamp_ns(consumer_span.attributes)
    if enqueue_ts_ns and consumer_span.start_time_ns > enqueue_ts_ns:
        dwell_ns = consumer_span.start_time_ns - enqueue_ts_ns
        dwell_ms = round(dwell_ns / 1_000_000.0, 2)
        if dwell_ms > 0.0:
            prod_id = producer_span.span_id if producer_span else "async-producer"
            return DwellInterval(
                producer_span_id=prod_id,
                consumer_span_id=consumer_span.span_id,
                queue_name=queue_name,
                dwell_time_ms=dwell_ms,
                start_time_ns=enqueue_ts_ns,
                end_time_ns=consumer_span.start_time_ns,
            )

    return None
