"""Embedded DuckDB columnar storage engine for traces and spans."""

import json
import threading
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from traceweaver.receiver.span_normalizer import NormalizedSpan, SpanEvent, SpanLink


class TraceSummary(BaseModel):
    """Aggregated summary of a distributed trace."""

    trace_id: str
    root_service: str
    root_name: str
    start_time_ns: int
    duration_ms: float
    span_count: int
    service_count: int
    has_error: bool
    services: list[str] = Field(default_factory=list)


class ServiceStats(BaseModel):
    """Aggregated service-level performance and latency percentiles."""

    service_name: str
    span_count: int
    avg_duration_ms: float
    p50_duration_ms: float
    p90_duration_ms: float
    p99_duration_ms: float
    error_count: int
    error_rate: float


class TraceStore:
    """Embedded DuckDB trace and span store supporting sub-millisecond aggregations."""

    def __init__(self, db_path: str = ":memory:", max_spans: int = 100_000):
        self.db_path = db_path
        self.max_spans = max_spans
        self._lock = threading.Lock()
        self._conn = duckdb.connect(database=db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create database tables and indexes."""
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS spans (
                    trace_id VARCHAR NOT NULL,
                    span_id VARCHAR NOT NULL,
                    parent_span_id VARCHAR,
                    name VARCHAR NOT NULL,
                    service_name VARCHAR NOT NULL,
                    kind VARCHAR NOT NULL,
                    start_time_ns BIGINT NOT NULL,
                    end_time_ns BIGINT NOT NULL,
                    duration_ms DOUBLE NOT NULL,
                    status_code VARCHAR NOT NULL,
                    status_message VARCHAR,
                    attributes_json VARCHAR NOT NULL,
                    events_json VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (trace_id, span_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS span_links (
                    trace_id VARCHAR NOT NULL,
                    span_id VARCHAR NOT NULL,
                    linked_trace_id VARCHAR NOT NULL,
                    linked_span_id VARCHAR NOT NULL,
                    attributes_json VARCHAR NOT NULL
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans (trace_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_spans_service ON spans (service_name);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_spans_start ON spans (start_time_ns);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_links_trace ON span_links (trace_id, span_id);"
            )

    def insert_spans(self, spans: list[NormalizedSpan]) -> int:
        """Insert a batch of normalized spans and associated links into DuckDB."""
        if not spans:
            return 0

        span_rows = []
        link_rows = []

        for s in spans:
            span_rows.append(
                (
                    s.trace_id,
                    s.span_id,
                    s.parent_span_id,
                    s.name,
                    s.service_name,
                    s.kind,
                    s.start_time_ns,
                    s.end_time_ns,
                    s.duration_ms,
                    s.status_code,
                    s.status_message,
                    json.dumps(s.attributes),
                    json.dumps([e.model_dump() for e in s.events]),
                )
            )

            for lk in s.links:
                link_rows.append(
                    (
                        s.trace_id,
                        s.span_id,
                        lk.trace_id,
                        lk.span_id,
                        json.dumps(lk.attributes),
                    )
                )

        with self._lock:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO spans (
                    trace_id, span_id, parent_span_id, name, service_name, kind,
                    start_time_ns, end_time_ns, duration_ms, status_code, status_message,
                    attributes_json, events_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                span_rows,
            )

            if link_rows:
                self._conn.executemany(
                    """
                    INSERT INTO span_links (
                        trace_id, span_id, linked_trace_id, linked_span_id, attributes_json
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    link_rows,
                )

        self._prune_if_needed()
        return len(span_rows)

    def _prune_if_needed(self) -> None:
        """Evict oldest traces if total span count exceeds max_spans threshold."""
        with self._lock:
            count_res = self._conn.execute("SELECT COUNT(*) FROM spans;").fetchone()
            total_spans = count_res[0] if count_res else 0

            if total_spans > self.max_spans:
                excess = total_spans - self.max_spans
                # Find oldest trace IDs to drop
                old_traces = self._conn.execute(
                    """
                    SELECT trace_id
                    FROM spans
                    GROUP BY trace_id
                    ORDER BY MIN(start_time_ns) ASC
                    LIMIT ?;
                    """,
                    [max(10, excess // 5)],
                ).fetchall()

                if old_traces:
                    trace_ids = [r[0] for r in old_traces]
                    placeholders = ", ".join(["?"] * len(trace_ids))
                    self._conn.execute(
                        f"DELETE FROM span_links WHERE trace_id IN ({placeholders});",
                        trace_ids,
                    )
                    self._conn.execute(
                        f"DELETE FROM spans WHERE trace_id IN ({placeholders});",
                        trace_ids,
                    )

    def get_trace_spans(self, trace_id: str) -> list[NormalizedSpan]:
        """Retrieve all normalized spans for a specific trace ID."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT
                    trace_id, span_id, parent_span_id, name, service_name, kind,
                    start_time_ns, end_time_ns, duration_ms, status_code, status_message,
                    attributes_json, events_json
                FROM spans
                WHERE trace_id = ?
                ORDER BY start_time_ns ASC;
                """,
                [trace_id],
            ).fetchall()

            links_rows = self._conn.execute(
                """
                SELECT trace_id, span_id, linked_trace_id, linked_span_id, attributes_json
                FROM span_links
                WHERE trace_id = ?;
                """,
                [trace_id],
            ).fetchall()

        links_by_span: dict[str, list[SpanLink]] = {}
        for lr in links_rows:
            s_id = lr[1]
            try:
                attrs = json.loads(lr[4])
            except Exception:
                attrs = {}
            lk = SpanLink(trace_id=lr[2], span_id=lr[3], attributes=attrs)
            links_by_span.setdefault(s_id, []).append(lk)

        spans: list[NormalizedSpan] = []
        for r in rows:
            try:
                attrs = json.loads(r[11])
            except Exception:
                attrs = {}

            try:
                raw_events = json.loads(r[12])
                events = [SpanEvent(**e) for e in raw_events]
            except Exception:
                events = []

            span_id = r[1]
            spans.append(
                NormalizedSpan(
                    trace_id=r[0],
                    span_id=span_id,
                    parent_span_id=r[2],
                    name=r[3],
                    service_name=r[4],
                    kind=r[5],
                    start_time_ns=r[6],
                    end_time_ns=r[7],
                    duration_ms=r[8],
                    status_code=r[9],
                    status_message=r[10],
                    attributes=attrs,
                    events=events,
                    links=links_by_span.get(span_id, []),
                )
            )

        return spans

    def get_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        service_name: str | None = None,
        min_duration_ms: float | None = None,
        error_only: bool = False,
    ) -> list[TraceSummary]:
        """Query aggregated trace list with filtering and pagination."""
        query = """
            SELECT
                trace_id,
                FIRST(service_name) AS root_service,
                FIRST(name) AS root_name,
                MIN(start_time_ns) AS start_time_ns,
                ROUND((MAX(end_time_ns) - MIN(start_time_ns)) / 1000000.0, 2) AS duration_ms,
                COUNT(*) AS span_count,
                COUNT(DISTINCT service_name) AS service_count,
                BOOL_OR(status_code = 'ERROR') AS has_error,
                LIST(DISTINCT service_name) AS services
            FROM spans
            GROUP BY trace_id
            HAVING 1=1
        """
        params: list[Any] = []

        if service_name:
            query += " AND LIST_CONTAINS(LIST(DISTINCT service_name), ?)"
            params.append(service_name)

        if min_duration_ms is not None:
            query += " AND ROUND((MAX(end_time_ns) - MIN(start_time_ns)) / 1000000.0, 2) >= ?"
            params.append(min_duration_ms)

        if error_only:
            query += " AND BOOL_OR(status_code = 'ERROR') = true"

        query += " ORDER BY MIN(start_time_ns) DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        summaries: list[TraceSummary] = []
        for r in rows:
            summaries.append(
                TraceSummary(
                    trace_id=r[0],
                    root_service=r[1],
                    root_name=r[2],
                    start_time_ns=r[3],
                    duration_ms=max(0.0, float(r[4])),
                    span_count=r[5],
                    service_count=r[6],
                    has_error=bool(r[7]),
                    services=r[8] if isinstance(r[8], list) else [],
                )
            )

        return summaries

    def get_service_analytics(self) -> list[ServiceStats]:
        """Compute service-level latency percentiles and error metrics using DuckDB vectorized execution."""
        query = """
            SELECT
                service_name,
                COUNT(*) AS span_count,
                ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
                ROUND(QUANTILE_CONT(duration_ms, 0.50), 2) AS p50_duration_ms,
                ROUND(QUANTILE_CONT(duration_ms, 0.90), 2) AS p90_duration_ms,
                ROUND(QUANTILE_CONT(duration_ms, 0.99), 2) AS p99_duration_ms,
                COUNT(*) FILTER (WHERE status_code = 'ERROR') AS error_count,
                ROUND(COUNT(*) FILTER (WHERE status_code = 'ERROR') * 100.0 / COUNT(*), 2) AS error_rate
            FROM spans
            GROUP BY service_name
            ORDER BY span_count DESC;
        """

        with self._lock:
            rows = self._conn.execute(query).fetchall()

        stats: list[ServiceStats] = []
        for r in rows:
            stats.append(
                ServiceStats(
                    service_name=r[0],
                    span_count=r[1],
                    avg_duration_ms=float(r[2] or 0.0),
                    p50_duration_ms=float(r[3] or 0.0),
                    p90_duration_ms=float(r[4] or 0.0),
                    p99_duration_ms=float(r[5] or 0.0),
                    error_count=r[6],
                    error_rate=float(r[7] or 0.0),
                )
            )

        return stats

    def total_spans_count(self) -> int:
        """Return the current total number of spans in the store."""
        with self._lock:
            res = self._conn.execute("SELECT COUNT(*) FROM spans;").fetchone()
            return res[0] if res else 0

    def close(self) -> None:
        """Close the DuckDB connection."""
        with self._lock:
            self._conn.close()
