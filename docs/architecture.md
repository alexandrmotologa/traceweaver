# TraceWeaver Architecture

TraceWeaver is an in-memory distributed trace correlator and causal waterfall visualizer. This document describes the internal components, ingestion pipelines, storage schema, and analytical algorithms.

## System Overview

```
                         OpenTelemetry Tracing Clients
                      (Java, Python, Go, Node, Rust SDKs)
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
           OTLP HTTP (Port 4318)                 OTLP gRPC (Port 4317)
           /v1/traces (JSON / Proto)             TraceService / Export
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │    OTLP Span Normalizer       │
                       │ - W3C traceparent extraction  │
                       │ - Tag and attribute flattening│
                       │ - Millisecond & ns alignment  │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │    DuckDB Columnar Store      │
                       │ - In-memory rolling buffer    │
                       │ - spans, links, attributes    │
                       │ - Sub-millisecond aggregations│
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   Causal Correlation Engine   │
                       │ - Parent-child DAG assembly   │
                       │ - Asynchronous link stitching │
                       │ - Queue dwell time calculation│
                       │ - Critical path detection     │
                       └───────┬───────────────┬───────┘
                               │               │
            ┌──────────────────┴──┐         ┌──┴──────────────────┐
            ▼                     ▼         ▼                     ▼
     FastAPI REST API        WebSocket   Textual TUI         CLI Reports
    /api/v1/traces/*         Live Feed   Terminal Client     Stdout & Export
```

## Component Breakdown

### 1. Ingestion Layer

The ingestion layer implements standard OpenTelemetry OTLP specifications:

* **HTTP Receiver (`receiver/otlp_http.py`)**: A FastAPI router mounted at `/v1/traces`. It accepts `application/json` and `application/x-protobuf` payloads.
* **gRPC Receiver (`receiver/otlp_grpc.py`)**: An asynchronous gRPC server running on port `4317` that implements `opentelemetry.proto.collector.trace.v1.TraceService`.
* **Span Normalizer (`receiver/span_normalizer.py`)**: Parses heterogeneous payloads from different language SDKs into a clean Pydantic model (`NormalizedSpan`). It extracts:
  * W3C trace identifiers: `trace_id` and `span_id` formatted as lowercase hexadecimal strings.
  * Hierarchical relationships: `parent_span_id`.
  * OpenTelemetry span links: explicitly declared links between producer and consumer spans.
  * Context attributes: standard messaging tags (`messaging.system`, `messaging.destination`, `queue_entry_ts`, `kafka.partition`).
  * Nanosecond timestamps: converted to float milliseconds relative to trace start.

### 2. Columnar Storage Layer

TraceWeaver uses an embedded DuckDB instance (`engine/store.py`) configured in-memory or persisted to a local file. DuckDB provides vectorized execution for aggregation queries without requiring an external database.

#### Schema

The database maintains three core tables:

1. **`spans`**:
   * `trace_id` (VARCHAR): 32-character trace identifier.
   * `span_id` (VARCHAR): 16-character span identifier.
   * `parent_span_id` (VARCHAR, NULL): Parent span identifier.
   * `name` (VARCHAR): Operation name (e.g. `POST /orders`, `kafka.consume`).
   * `service_name` (VARCHAR): Service that emitted the span.
   * `kind` (VARCHAR): SpanKind (`SERVER`, `CLIENT`, `PRODUCER`, `CONSUMER`, `INTERNAL`).
   * `start_time_ns` (BIGINT): Unix epoch start time in nanoseconds.
   * `end_time_ns` (BIGINT): Unix epoch end time in nanoseconds.
   * `duration_ms` (DOUBLE): Precomputed duration in milliseconds.
   * `status_code` (VARCHAR): `OK`, `ERROR`, or `UNSET`.
   * `status_message` (VARCHAR, NULL): Error message if present.
   * `attributes_json` (VARCHAR): Serialized span attributes.

2. **`span_links`**:
   * `trace_id` (VARCHAR)
   * `span_id` (VARCHAR)
   * `linked_trace_id` (VARCHAR)
   * `linked_span_id` (VARCHAR)
   * `attributes_json` (VARCHAR)

3. **`rolling_retention`**:
   When the span count exceeds `max_spans` (default: 100,000), TraceWeaver drops the oldest traces in batches, maintaining a constant memory footprint.

### 3. Causal Correlation and Dwell Time Engine

Distributed requests often branch across asynchronous boundaries where parent-child identifiers are either lost or explicitly separated. TraceWeaver resolves these connections using a two-pass correlation algorithm:

1. **Hierarchy Pass**: Organizes spans by `parent_span_id` to build synchronous call trees.
2. **Link Stitching Pass**: Traverses span links and messaging attributes to connect consumer spans with the exact producer span that enqueued the message.
3. **Dwell Time Calculation**: Computes the elapsed duration between when an event was published to a queue or topic and when a consumer began processing it.

### 4. User Interfaces

* **Terminal User Interface (TUI)**: Uses Textual to render interactive screens. A scrolling trace table provides immediate sorting by duration, service count, and error flags. Selecting a trace opens a Gantt waterfall rendering span bars and highlighted queue dwell intervals using Unicode blocks.
* **Web Dashboard**: An embedded FastAPI web interface serving static HTML and SVG without Node.js runtime dependencies. It connects to a WebSocket endpoint for live trace streaming and renders interactive Gantt charts with pan and zoom capabilities.
