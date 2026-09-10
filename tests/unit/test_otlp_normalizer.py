"""Unit tests for OpenTelemetry span normalization."""

from opentelemetry.proto.trace.v1.trace_pb2 import (
    Status,
    TracesData,
)

from traceweaver.receiver.span_normalizer import (
    normalize_id,
    parse_otlp_json,
    parse_otlp_protobuf,
)


def test_normalize_id():
    """Verify trace and span ID normalization across hex and base64 strings."""
    # 32-character hex trace ID
    hex_trace = "4bf92f3577b34da6a3ce929d0e0e4736"
    assert normalize_id(hex_trace, expected_bytes=16) == hex_trace.lower()

    # Raw 16 bytes
    raw_bytes = bytes.fromhex(hex_trace)
    assert normalize_id(raw_bytes, expected_bytes=16) == hex_trace.lower()

    # 16-character hex span ID
    hex_span = "00f067aa0ba902b7"
    assert normalize_id(hex_span, expected_bytes=8) == hex_span.lower()


def test_parse_otlp_json():
    """Verify parsing standard OTLP JSON payload."""
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "order-service"}},
                        {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                                "spanId": "00f067aa0ba902b7",
                                "parentSpanId": "5fb397be34d23b0f",
                                "name": "POST /orders",
                                "kind": 2,  # SERVER
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000000050000000",  # 50ms
                                "attributes": [
                                    {"key": "http.status_code", "value": {"intValue": 201}},
                                    {"key": "http.route", "value": {"stringValue": "/orders"}},
                                ],
                                "status": {"code": 1},  # OK
                                "links": [
                                    {
                                        "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                                        "spanId": "1234567890abcdef",
                                        "attributes": [
                                            {
                                                "key": "messaging.system",
                                                "value": {"stringValue": "kafka"},
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    spans = parse_otlp_json(payload)
    assert len(spans) == 1

    span = spans[0]
    assert span.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert span.span_id == "00f067aa0ba902b7"
    assert span.parent_span_id == "5fb397be34d23b0f"
    assert span.name == "POST /orders"
    assert span.service_name == "order-service"
    assert span.kind == "SERVER"
    assert span.duration_ms == 50.0
    assert span.status_code == "OK"
    assert span.attributes["http.status_code"] == 201
    assert span.attributes["deployment.environment"] == "production"
    assert len(span.links) == 1
    assert span.links[0].span_id == "1234567890abcdef"
    assert span.links[0].attributes["messaging.system"] == "kafka"


def test_parse_otlp_protobuf():
    """Verify parsing OTLP Protobuf serialized payload."""
    traces_data = TracesData()
    rs = traces_data.resource_spans.add()

    kv_service = rs.resource.attributes.add()
    kv_service.key = "service.name"
    kv_service.value.string_value = "payment-worker"

    ss = rs.scope_spans.add()
    span = ss.spans.add()
    span.trace_id = bytes.fromhex("11112222333344445555666677778888")
    span.span_id = bytes.fromhex("aaaa5555aaaa5555")
    span.name = "process_payment"
    span.kind = 5  # CONSUMER
    span.start_time_unix_nano = 1700000000000000000
    span.end_time_unix_nano = 1700000000080000000  # 80ms
    span.status.code = Status.STATUS_CODE_OK

    kv_amount = span.attributes.add()
    kv_amount.key = "payment.amount"
    kv_amount.value.double_value = 149.99

    payload_bytes = traces_data.SerializeToString()
    spans = parse_otlp_protobuf(payload_bytes)

    assert len(spans) == 1
    s = spans[0]
    assert s.trace_id == "11112222333344445555666677778888"
    assert s.span_id == "aaaa5555aaaa5555"
    assert s.service_name == "payment-worker"
    assert s.name == "process_payment"
    assert s.kind == "CONSUMER"
    assert s.duration_ms == 80.0
    assert s.attributes["payment.amount"] == 149.99
