"""OpenTelemetry span normalization utilities for JSON and Protobuf encodings."""

import base64
from typing import Any

from pydantic import BaseModel, Field


class SpanLink(BaseModel):
    """OpenTelemetry span link representing cross-boundary causal connection."""

    trace_id: str
    span_id: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class SpanEvent(BaseModel):
    """Point-in-time event recorded within a span."""

    name: str
    timestamp_ns: int
    attributes: dict[str, Any] = Field(default_factory=dict)


class NormalizedSpan(BaseModel):
    """Canonical internal representation of an OpenTelemetry span."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    service_name: str = "unknown-service"
    kind: str = "INTERNAL"
    start_time_ns: int
    end_time_ns: int
    duration_ms: float
    status_code: str = "UNSET"
    status_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[SpanEvent] = Field(default_factory=list)
    links: list[SpanLink] = Field(default_factory=list)


SPAN_KIND_MAP = {
    0: "INTERNAL",
    1: "INTERNAL",
    2: "SERVER",
    3: "CLIENT",
    4: "PRODUCER",
    5: "CONSUMER",
    "SPAN_KIND_UNSPECIFIED": "INTERNAL",
    "SPAN_KIND_INTERNAL": "INTERNAL",
    "SPAN_KIND_SERVER": "SERVER",
    "SPAN_KIND_CLIENT": "CLIENT",
    "SPAN_KIND_PRODUCER": "PRODUCER",
    "SPAN_KIND_CONSUMER": "CONSUMER",
}

STATUS_CODE_MAP = {
    0: "UNSET",
    1: "OK",
    2: "ERROR",
    "STATUS_CODE_UNSET": "UNSET",
    "STATUS_CODE_OK": "OK",
    "STATUS_CODE_ERROR": "ERROR",
}


def normalize_id(id_val: Any, expected_bytes: int = 16) -> str:
    """Normalize trace_id or span_id from bytes, hex, or base64 into a clean lowercase hex string."""
    if not id_val:
        return ""

    if isinstance(id_val, bytes):
        return id_val.hex().lower()

    if isinstance(id_val, str):
        cleaned = id_val.strip()
        expected_hex_len = expected_bytes * 2

        # Check if already a hex string of expected length
        if len(cleaned) == expected_hex_len and all(c in "0123456789abcdefABCDEF" for c in cleaned):
            return cleaned.lower()

        # Try base64 decoding
        try:
            decoded = base64.b64decode(cleaned)
            if len(decoded) == expected_bytes:
                return decoded.hex().lower()
        except Exception:
            pass

        return cleaned.lower()

    return str(id_val).lower()


def unpack_otlp_json_any_value(val_obj: Any) -> Any:
    """Extract primitive Python value from OTLP JSON AnyValue container."""
    if not isinstance(val_obj, dict):
        return val_obj

    if "stringValue" in val_obj:
        return val_obj["stringValue"]
    if "intValue" in val_obj:
        try:
            return int(val_obj["intValue"])
        except (ValueError, TypeError):
            return val_obj["intValue"]
    if "boolValue" in val_obj:
        return bool(val_obj["boolValue"])
    if "doubleValue" in val_obj:
        return float(val_obj["doubleValue"])
    if "arrayValue" in val_obj:
        values = val_obj["arrayValue"].get("values", [])
        return [unpack_otlp_json_any_value(v) for v in values]
    if "kvlistValue" in val_obj:
        entries = val_obj["kvlistValue"].get("values", [])
        res = {}
        for entry in entries:
            k = entry.get("key", "")
            v = unpack_otlp_json_any_value(entry.get("value", {}))
            if k:
                res[k] = v
        return res

    # Direct value without container wrapper
    return val_obj


def unpack_otlp_json_attributes(attrs_list: Any) -> dict[str, Any]:
    """Parse list of key-value attribute objects from OTLP JSON."""
    if isinstance(attrs_list, dict):
        return attrs_list

    result: dict[str, Any] = {}
    if not isinstance(attrs_list, list):
        return result

    for item in attrs_list:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not key:
            continue
        val = item.get("value")
        result[key] = unpack_otlp_json_any_value(val)

    return result


def unpack_proto_any_value(any_val: Any) -> Any:
    """Extract primitive value from protobuf AnyValue message."""
    which = any_val.WhichOneof("value")
    if which == "string_value":
        return any_val.string_value
    if which == "int_value":
        return any_val.int_value
    if which == "double_value":
        return any_val.double_value
    if which == "bool_value":
        return any_val.bool_value
    if which == "array_value":
        return [unpack_proto_any_value(v) for v in any_val.array_value.values]
    if which == "kvlist_value":
        return {kv.key: unpack_proto_any_value(kv.value) for kv in any_val.kvlist_value.values}
    if which == "bytes_value":
        return any_val.bytes_value.hex()
    return None


def unpack_proto_attributes(proto_key_values: Any) -> dict[str, Any]:
    """Parse KeyValue protobuf objects into standard python dict."""
    result: dict[str, Any] = {}
    for kv in proto_key_values:
        result[kv.key] = unpack_proto_any_value(kv.value)
    return result


def parse_otlp_json(payload: dict[str, Any]) -> list[NormalizedSpan]:
    """Parse OTLP JSON traces payload into list of NormalizedSpan models."""
    normalized: list[NormalizedSpan] = []

    resource_spans = payload.get("resourceSpans", [])
    if not isinstance(resource_spans, list):
        return normalized

    for rs in resource_spans:
        resource = rs.get("resource", {})
        resource_attrs = unpack_otlp_json_attributes(resource.get("attributes", []))
        service_name = str(
            resource_attrs.get("service.name")
            or resource_attrs.get("service_name")
            or "unknown-service"
        )

        scope_spans = rs.get("scopeSpans", [])
        if not isinstance(scope_spans, list):
            continue

        for ss in scope_spans:
            spans = ss.get("spans", [])
            if not isinstance(spans, list):
                continue

            for span_data in spans:
                trace_id = normalize_id(span_data.get("traceId", ""), expected_bytes=16)
                span_id = normalize_id(span_data.get("spanId", ""), expected_bytes=8)

                if not trace_id or not span_id:
                    continue

                raw_parent = span_data.get("parentSpanId")
                parent_span_id = normalize_id(raw_parent, expected_bytes=8) if raw_parent else None

                name = span_data.get("name", "unnamed-span")

                raw_kind = span_data.get("kind", 0)
                kind = SPAN_KIND_MAP.get(raw_kind, "INTERNAL")

                # Parse timestamps (support strings or ints)
                start_ns = int(span_data.get("startTimeUnixNano", 0))
                end_ns = int(span_data.get("endTimeUnixNano", start_ns))
                duration_ms = max(0.0, (end_ns - start_ns) / 1_000_000.0)

                # Parse status
                status_obj = span_data.get("status", {})
                raw_code = status_obj.get("code", 0)
                status_code = STATUS_CODE_MAP.get(raw_code, "UNSET")
                status_message = status_obj.get("message")

                # Parse span attributes and merge with resource attributes
                span_attrs = unpack_otlp_json_attributes(span_data.get("attributes", []))
                merged_attrs = {**resource_attrs, **span_attrs}

                # Parse events
                events: list[SpanEvent] = []
                for ev in span_data.get("events", []):
                    ev_name = ev.get("name", "")
                    ev_time = int(ev.get("timeUnixNano", 0))
                    ev_attrs = unpack_otlp_json_attributes(ev.get("attributes", []))
                    events.append(
                        SpanEvent(name=ev_name, timestamp_ns=ev_time, attributes=ev_attrs)
                    )

                # Parse links
                links: list[SpanLink] = []
                for lk in span_data.get("links", []):
                    l_trace_id = normalize_id(lk.get("traceId", ""), expected_bytes=16)
                    l_span_id = normalize_id(lk.get("spanId", ""), expected_bytes=8)
                    l_attrs = unpack_otlp_json_attributes(lk.get("attributes", []))
                    if l_trace_id and l_span_id:
                        links.append(
                            SpanLink(trace_id=l_trace_id, span_id=l_span_id, attributes=l_attrs)
                        )

                normalized.append(
                    NormalizedSpan(
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_span_id=parent_span_id,
                        name=name,
                        service_name=service_name,
                        kind=kind,
                        start_time_ns=start_ns,
                        end_time_ns=end_ns,
                        duration_ms=duration_ms,
                        status_code=status_code,
                        status_message=status_message,
                        attributes=merged_attrs,
                        events=events,
                        links=links,
                    )
                )

    return normalized


def parse_otlp_protobuf(payload_bytes: bytes) -> list[NormalizedSpan]:
    """Parse OTLP Protobuf bytes into list of NormalizedSpan models."""
    from opentelemetry.proto.trace.v1.trace_pb2 import TracesData

    traces_data = TracesData()
    traces_data.ParseFromString(payload_bytes)

    normalized: list[NormalizedSpan] = []

    for rs in traces_data.resource_spans:
        resource_attrs = unpack_proto_attributes(rs.resource.attributes)
        service_name = str(
            resource_attrs.get("service.name")
            or resource_attrs.get("service_name")
            or "unknown-service"
        )

        for ss in rs.scope_spans:
            for span in ss.spans:
                trace_id = span.trace_id.hex().lower()
                span_id = span.span_id.hex().lower()

                if not trace_id or not span_id:
                    continue

                parent_span_id = span.parent_span_id.hex().lower() if span.parent_span_id else None
                name = span.name or "unnamed-span"
                kind = SPAN_KIND_MAP.get(span.kind, "INTERNAL")

                start_ns = span.start_time_unix_nano
                end_ns = span.end_time_unix_nano or start_ns
                duration_ms = max(0.0, (end_ns - start_ns) / 1_000_000.0)

                status_code = STATUS_CODE_MAP.get(span.status.code, "UNSET")
                status_message = span.status.message or None

                span_attrs = unpack_proto_attributes(span.attributes)
                merged_attrs = {**resource_attrs, **span_attrs}

                events: list[SpanEvent] = []
                for ev in span.events:
                    events.append(
                        SpanEvent(
                            name=ev.name,
                            timestamp_ns=ev.time_unix_nano,
                            attributes=unpack_proto_attributes(ev.attributes),
                        )
                    )

                links: list[SpanLink] = []
                for lk in span.links:
                    l_trace_id = lk.trace_id.hex().lower()
                    l_span_id = lk.span_id.hex().lower()
                    if l_trace_id and l_span_id:
                        links.append(
                            SpanLink(
                                trace_id=l_trace_id,
                                span_id=l_span_id,
                                attributes=unpack_proto_attributes(lk.attributes),
                            )
                        )

                normalized.append(
                    NormalizedSpan(
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_span_id=parent_span_id,
                        name=name,
                        service_name=service_name,
                        kind=kind,
                        start_time_ns=start_ns,
                        end_time_ns=end_ns,
                        duration_ms=duration_ms,
                        status_code=status_code,
                        status_message=status_message,
                        attributes=merged_attrs,
                        events=events,
                        links=links,
                    )
                )

    return normalized
