"""Trace comparison and regression diff engine."""

from pydantic import BaseModel, Field

from traceweaver.engine.correlator import TraceCorrelator
from traceweaver.receiver.span_normalizer import NormalizedSpan


class ServiceDelta(BaseModel):
    """Latency comparison for a single service across two traces."""

    service_name: str
    duration_a_ms: float
    duration_b_ms: float
    delta_ms: float
    pct_change: float


class QueueDwellDelta(BaseModel):
    """Queue dwell latency comparison across two traces."""

    queue_name: str
    dwell_a_ms: float
    dwell_b_ms: float
    delta_ms: float


class SpanDelta(BaseModel):
    """Latency comparison for matched spans by service and operation name."""

    service_name: str
    operation_name: str
    duration_a_ms: float
    duration_b_ms: float
    delta_ms: float
    is_regression: bool = False


class TraceDiffResult(BaseModel):
    """Comprehensive causal diff comparing two traces."""

    trace_a_id: str
    trace_b_id: str
    duration_a_ms: float
    duration_b_ms: float
    duration_delta_ms: float
    duration_pct_change: float
    dwell_a_ms: float
    dwell_b_ms: float
    dwell_delta_ms: float
    span_count_a: int
    span_count_b: int
    services: list[ServiceDelta] = Field(default_factory=list)
    queues: list[QueueDwellDelta] = Field(default_factory=list)
    spans: list[SpanDelta] = Field(default_factory=list)
    primary_bottleneck: str = ""


class TraceDiffEngine:
    """Calculates structured latency and causal DAG diffs between two traces."""

    def __init__(self, correlator: TraceCorrelator | None = None):
        self.correlator = correlator or TraceCorrelator()

    def compare_traces(
        self,
        spans_a: list[NormalizedSpan],
        spans_b: list[NormalizedSpan],
    ) -> TraceDiffResult:
        """Compare two trace executions and determine root causes of latency divergence."""
        dag_a = self.correlator.correlate_trace(spans_a)
        dag_b = self.correlator.correlate_trace(spans_b)

        dur_a = dag_a.total_duration_ms
        dur_b = dag_b.total_duration_ms
        dur_delta = round(dur_b - dur_a, 2)
        pct_change = round(((dur_b - dur_a) / max(0.01, dur_a)) * 100.0, 1)

        dwell_a = dag_a.total_dwell_time_ms
        dwell_b = dag_b.total_dwell_time_ms
        dwell_delta = round(dwell_b - dwell_a, 2)

        # Service-level comparison
        all_services = sorted(
            set(dag_a.service_durations.keys()) | set(dag_b.service_durations.keys())
        )
        service_deltas: list[ServiceDelta] = []
        for svc in all_services:
            s_a = dag_a.service_durations.get(svc, 0.0)
            s_b = dag_b.service_durations.get(svc, 0.0)
            s_delta = round(s_b - s_a, 2)
            s_pct = round(((s_b - s_a) / max(0.01, s_a)) * 100.0, 1) if s_a > 0 else 100.0
            service_deltas.append(
                ServiceDelta(
                    service_name=svc,
                    duration_a_ms=s_a,
                    duration_b_ms=s_b,
                    delta_ms=s_delta,
                    pct_change=s_pct,
                )
            )
        service_deltas.sort(key=lambda s: abs(s.delta_ms), reverse=True)

        # Queue-level comparison
        queues_a: dict[str, float] = {}
        for dw in dag_a.dwell_intervals:
            queues_a[dw.queue_name] = round(queues_a.get(dw.queue_name, 0.0) + dw.dwell_time_ms, 2)

        queues_b: dict[str, float] = {}
        for dw in dag_b.dwell_intervals:
            queues_b[dw.queue_name] = round(queues_b.get(dw.queue_name, 0.0) + dw.dwell_time_ms, 2)

        all_queues = sorted(set(queues_a.keys()) | set(queues_b.keys()))
        queue_deltas: list[QueueDwellDelta] = []
        for q in all_queues:
            qa = queues_a.get(q, 0.0)
            qb = queues_b.get(q, 0.0)
            queue_deltas.append(
                QueueDwellDelta(
                    queue_name=q,
                    dwell_a_ms=qa,
                    dwell_b_ms=qb,
                    delta_ms=round(qb - qa, 2),
                )
            )
        queue_deltas.sort(key=lambda q: abs(q.delta_ms), reverse=True)

        # Span-level matching (match by service + operation name)
        spans_map_a: dict[tuple[str, str], float] = {}
        for s in spans_a:
            key = (s.service_name, s.name)
            spans_map_a[key] = spans_map_a.get(key, 0.0) + s.duration_ms

        spans_map_b: dict[tuple[str, str], float] = {}
        for s in spans_b:
            key = (s.service_name, s.name)
            spans_map_b[key] = spans_map_b.get(key, 0.0) + s.duration_ms

        all_span_keys = sorted(set(spans_map_a.keys()) | set(spans_map_b.keys()))
        span_deltas: list[SpanDelta] = []
        for svc, op in all_span_keys:
            sa_dur = round(spans_map_a.get((svc, op), 0.0), 2)
            sb_dur = round(spans_map_b.get((svc, op), 0.0), 2)
            s_diff = round(sb_dur - sa_dur, 2)
            is_reg = s_diff > 15.0 or (sa_dur > 0 and (sb_dur / sa_dur) >= 1.5)
            span_deltas.append(
                SpanDelta(
                    service_name=svc,
                    operation_name=op,
                    duration_a_ms=sa_dur,
                    duration_b_ms=sb_dur,
                    delta_ms=s_diff,
                    is_regression=is_reg,
                )
            )
        span_deltas.sort(key=lambda s: s.delta_ms, reverse=True)

        # Identify primary bottleneck
        primary_bottleneck = "No significant divergence detected"
        if dwell_delta > 20.0 and (not service_deltas or dwell_delta >= service_deltas[0].delta_ms):
            top_q = queue_deltas[0].queue_name if queue_deltas else "broker"
            primary_bottleneck = f"Queue dwell latency regression in '{top_q}' (+{dwell_delta}ms)"
        elif service_deltas and service_deltas[0].delta_ms > 10.0:
            top_s = service_deltas[0]
            primary_bottleneck = (
                f"Service execution regression in '{top_s.service_name}' (+{top_s.delta_ms}ms)"
            )
        elif dur_delta < -20.0:
            primary_bottleneck = f"Trace B was faster by {abs(dur_delta)}ms"

        return TraceDiffResult(
            trace_a_id=dag_a.trace_id,
            trace_b_id=dag_b.trace_id,
            duration_a_ms=dur_a,
            duration_b_ms=dur_b,
            duration_delta_ms=dur_delta,
            duration_pct_change=pct_change,
            dwell_a_ms=dwell_a,
            dwell_b_ms=dwell_b,
            dwell_delta_ms=dwell_delta,
            span_count_a=len(spans_a),
            span_count_b=len(spans_b),
            services=service_deltas,
            queues=queue_deltas,
            spans=span_deltas,
            primary_bottleneck=primary_bottleneck,
        )
