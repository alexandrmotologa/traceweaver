<div align="center">

<img src="docs/images/logo.png" alt="TraceWeaver Logo" width="160" />

# TraceWeaver

**Distributed trace correlator and causal event waterfall visualizer with sub-millisecond DuckDB analytics.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org)
[![Textual](https://img.shields.io/badge/Textual-TUI-purple.svg)](https://textual.textualize.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

TraceWeaver correlates distributed traces across asynchronous message boundaries, database outbox tables, and event brokers. When requests transition through Kafka partitions, RabbitMQ exchanges, or worker queues, traditional tracing views separate spans into disconnected trees. TraceWeaver stitches these spans into a single causal directed acyclic graph (DAG), measures queue dwell time, flags latency bottlenecks, and displays the execution path through an interactive terminal TUI, a CLI analyzer, and a high-performance web dashboard.

---

## Visual Tour

### Web Console & Causal Waterfall
Live distributed trace stream with async broker dwell time metrics, Gantt timeline, and OpenTelemetry cross-boundary link inspector.

<p align="center">
  <img src="docs/images/web_dashboard_overview.png" alt="TraceWeaver Web Dashboard Overview" width="100%" />
</p>

<p align="center">
  <img src="docs/images/web_dashboard_dwell.png" alt="TraceWeaver Async Queue Dwell & Link Details" width="100%" />
</p>

### Terminal Causal Analyzer
Sub-millisecond trace DAG correlation directly in your terminal with critical path highlighting (`🔥 CP`) and message broker dwell interval computation.

<p align="center">
  <img src="docs/images/cli_analyze.png" alt="TraceWeaver CLI Causal Waterfall" width="100%" />
</p>

---

## Overview

In microservice environments combining REST endpoints, transactional outbox patterns, and message brokers, measuring end-to-end user latency requires understanding how long messages sit waiting in queues before consumer threads pick them up.

Standard OpenTelemetry spans track synchronous parent-child calls cleanly, but asynchronous boundaries break this relationship. TraceWeaver accepts standard OTLP traces over HTTP (`/v1/traces`) and gRPC (`4317`), correlates spans using both hierarchy and trace links, and calculates queue dwell time directly:

```
[S1: Gateway POST /orders (15ms)]
  └── [S2: OrderEngine Process (45ms)]
        └── [S3: Outbox Transaction (5ms)]
              ░░░░░ QUEUE DWELL TIME: 320ms in Kafka ░░░░░
                    └── [S4: PaymentWorker Consume (75ms)]
```

## Features

* **Dual OTLP ingestion**: Ingests traces over HTTP (`/v1/traces`) and gRPC (`4317`) supporting both JSON and Protobuf encodings.
* **Causal correlation**: Connects parent spans, span links, and message broker context attributes into unified causal traces.
* **Queue dwell time detection**: Computes the exact time gap between event production and consumer execution, separating processing duration from queue wait time.
* **Columnar DuckDB engine**: Stores spans in an embedded DuckDB database with rolling retention buffers, enabling sub-millisecond percentile calculations (`p50`, `p90`, `p99`).
* **Interactive terminal TUI & CLI**: Terminal interface built with Textual and Rich, featuring live trace tables, full-screen waterfall views, and ASCII dwell time indicators.
* **Web Gantt dashboard**: Embedded zero-dependency SVG waterfall viewer with collapsible spans, zoom controls, and span attribute inspectors.
* **Synthetic demo generator**: Built-in simulator generating multi-service commerce traces with synthetic queue dwell times for immediate local evaluation.
* **Critical path analysis**: Automatically highlights the spans contributing the most to end-to-end request duration.

## Architecture

```
                       ┌────────────────────────────┐
                       │   Microservices & Tools    │
                       └─────────────┬──────────────┘
                                     │ OTLP HTTP (/v1/traces) / gRPC (4317)
                                     ▼
                       ┌────────────────────────────┐
                       │  TraceWeaver Ingestion     │
                       │  (Normalizer & Validator)  │
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │  Embedded DuckDB Store     │
                       │  (Columnar Ring Buffer)    │
                       └─────────────┬──────────────┘
                                     │
              ┌──────────────────────┴──────────────────────┐
              ▼                                             ▼
┌───────────────────────────┐                 ┌───────────────────────────┐
│ Causal Correlation Engine │                 │ Percentile Analytics API  │
│ - DAG Link Stitcher       │                 │ - p50 / p90 / p99 Latency │
│ - Queue Dwell Time Calc   │                 │ - Service Topology Counts │
│ - Anomaly Detection       │                 │ - Error Rate Analysis     │
└─────────────┬─────────────┘                 └─────────────┬─────────────┘
              │                                             │
              └──────────────────────┬──────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │   Interactive Textual     │   │   FastAPI Web Console     │
       │   Terminal TUI & CLI      │   │   (SVG Gantt Dashboard)   │
       └───────────────────────────┘   └───────────────────────────┘
```

## Quick Start

### Installation

Requires Python 3.12 or newer.

```bash
git clone https://github.com/alexandrmotologa/traceweaver.git
cd traceweaver
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Starting the Server

Launch the OTLP receivers and the web dashboard:

```bash
traceweaver serve --web-port 8080 --grpc-port 4317
```

The web dashboard is available at `http://localhost:8080`.

### Running the Synthetic Demo

In a separate terminal, stream realistic distributed traces through TraceWeaver:

```bash
# Emit synthetic traces to the running server:
traceweaver demo --endpoint http://localhost:8080/v1/traces --rate 2.0 --count 20
```

### Analyzing Traces in the Terminal

Inspect causal relationships and dwell times in any terminal session:

```bash
traceweaver analyze <trace_id> --db-path traces.duckdb
```

### Launching the Terminal TUI

Open the interactive terminal dashboard:

```bash
traceweaver tui --db-path traces.duckdb
```

Keyboard shortcuts:
* `q`: Quit application
* `r`: Refresh trace list
* `/`: Filter traces by service name or status
* `Enter`: Drill down into selected trace waterfall
* `Escape`: Return to trace list

## REST API

TraceWeaver provides HTTP endpoints for automated inspection and analytics:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/traces` | POST | OTLP trace ingestion endpoint (JSON and Protobuf) |
| `/api/v1/traces` | GET | List recent root traces with duration and error filters |
| `/api/v1/traces/{trace_id}` | GET | Retrieve full causal DAG and dwell time breakdown for a trace |
| `/api/v1/analytics/services` | GET | Aggregate latency percentiles, error rates, and dwell averages |
| `/api/v1/ws/traces` | WS | Real-time WebSocket stream for incoming traces |
| `/healthz` | GET | Health check endpoint |

## Configuration

Settings can be set via command-line flags or environment variables:

| Variable | Flag | Default | Description |
|---|---|---|---|
| `TW_WEB_PORT` | `--web-port` / `-w` | `8080` | Web console and OTLP HTTP receiver port |
| `TW_GRPC_PORT` | `--grpc-port` / `-g` | `4317` | OTLP gRPC receiver port |
| `TW_MAX_SPANS` | `--max-spans` / `-m` | `100000` | In-memory DuckDB rolling retention limit |
| `TW_DB_PATH` | `--db-path` / `-d` | `:memory:` | DuckDB database path (`:memory:` or file path) |

## Development and Testing

Run the test suite:

```bash
pytest
```

Run code formatting and linting:

```bash
ruff check src tests
ruff format --check src tests
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
