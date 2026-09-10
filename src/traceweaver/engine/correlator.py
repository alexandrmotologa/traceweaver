"""Causal correlation and DAG assembly engine for distributed traces."""

from pydantic import BaseModel, Field

from traceweaver.engine.anomaly import AnomalyDetector
from traceweaver.engine.dwell_time import DwellInterval, calculate_dwell_time
from traceweaver.engine.store import ServiceStats
from traceweaver.receiver.span_normalizer import NormalizedSpan


class CausalNode(BaseModel):
    """A node in the causal trace DAG with timing offsets, dwell intervals, and children."""

    span: NormalizedSpan
    children: list["CausalNode"] = Field(default_factory=list)
    dwell_intervals: list[DwellInterval] = Field(default_factory=list)
    is_critical_path: bool = False
    is_anomaly: bool = False
    anomaly_reason: str | None = None
    depth: int = 0
    offset_ms: float = 0.0


class CausalTraceDAG(BaseModel):
    """Unified causal directed acyclic graph for a distributed trace."""

    trace_id: str
    root_nodes: list[CausalNode] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    total_dwell_time_ms: float = 0.0
    critical_path_span_ids: list[str] = Field(default_factory=list)
    dwell_intervals: list[DwellInterval] = Field(default_factory=list)
    service_durations: dict[str, float] = Field(default_factory=dict)
    span_count: int = 0
    has_error: bool = False


class TraceCorrelator:
    """Assembles disjoint spans into a unified causal DAG across asynchronous boundaries."""

    def __init__(
        self,
        anomaly_detector: AnomalyDetector | None = None,
        service_stats_map: dict[str, ServiceStats] | None = None,
    ):
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.service_stats_map = service_stats_map or {}

    def correlate_trace(self, spans: list[NormalizedSpan]) -> CausalTraceDAG:
        """Assemble spans into a causal execution graph, computing dwell times and critical path."""
        if not spans:
            return CausalTraceDAG(trace_id="empty")

        trace_id = spans[0].trace_id
        min_start_ns = min(s.start_time_ns for s in spans)
        max_end_ns = max(s.end_time_ns for s in spans)
        total_duration_ms = round(max(0.0, (max_end_ns - min_start_ns) / 1_000_000.0), 2)

        span_map: dict[str, NormalizedSpan] = {s.span_id: s for s in spans}
        children_map: dict[str, list[str]] = {s.span_id: [] for s in spans}
        incoming_edges: set[str] = set()
        all_dwell_intervals: list[DwellInterval] = []
        dwell_by_consumer: dict[str, list[DwellInterval]] = {}

        # Step 1: Link spans by standard parent_span_id
        for s in spans:
            if s.parent_span_id and s.parent_span_id in span_map:
                children_map[s.parent_span_id].append(s.span_id)
                incoming_edges.add(s.span_id)

        # Step 2: Stitch asynchronous boundaries using span links
        for s in spans:
            for lk in s.links:
                if lk.span_id in span_map:
                    producer = span_map[lk.span_id]
                    dwell = calculate_dwell_time(consumer_span=s, producer_span=producer)
                    if dwell:
                        all_dwell_intervals.append(dwell)
                        dwell_by_consumer.setdefault(s.span_id, []).append(dwell)

                    # If this consumer span has no synchronous parent, stitch it to producer
                    if s.span_id not in incoming_edges and s.span_id != producer.span_id:
                        children_map[producer.span_id].append(s.span_id)
                        incoming_edges.add(s.span_id)

        # Step 3: Identify root spans (no incoming synchronous or asynchronous parent)
        root_span_ids = [s.span_id for s in spans if s.span_id not in incoming_edges]
        if not root_span_ids:
            # Fallback if circular dependency or all have parents
            root_span_ids = [spans[0].span_id]

        # Step 4: Build CausalNode tree recursively
        def build_node(span_id: str, depth: int) -> CausalNode:
            span = span_map[span_id]
            offset_ms = round(max(0.0, (span.start_time_ns - min_start_ns) / 1_000_000.0), 2)
            node_dwells = dwell_by_consumer.get(span_id, [])

            stats = self.service_stats_map.get(span.service_name)
            is_anomaly, reason = self.anomaly_detector.inspect_span(span, stats)

            child_nodes = [
                build_node(child_id, depth + 1)
                for child_id in children_map.get(span_id, [])
                if child_id in span_map
            ]

            return CausalNode(
                span=span,
                children=child_nodes,
                dwell_intervals=node_dwells,
                is_critical_path=False,
                is_anomaly=is_anomaly,
                anomaly_reason=reason,
                depth=depth,
                offset_ms=offset_ms,
            )

        root_nodes = [build_node(r_id, 0) for r_id in root_span_ids]

        # Step 5: Critical path analysis (longest weighted path through tree)
        critical_path_ids: list[str] = []

        def find_longest_path(node: CausalNode) -> tuple[float, list[str]]:
            if not node.children:
                return node.span.duration_ms, [node.span.span_id]

            best_child_dur = 0.0
            best_child_path: list[str] = []
            for child in node.children:
                dur, path = find_longest_path(child)
                if dur > best_child_dur:
                    best_child_dur = dur
                    best_child_path = path

            return node.span.duration_ms + best_child_dur, [node.span.span_id] + best_child_path

        best_root_dur = 0.0
        for r_node in root_nodes:
            dur, path = find_longest_path(r_node)
            if dur > best_root_dur:
                best_root_dur = dur
                critical_path_ids = path

        # Mark nodes on critical path
        critical_set = set(critical_path_ids)

        def mark_critical(node: CausalNode) -> None:
            if node.span.span_id in critical_set:
                node.is_critical_path = True
            for ch in node.children:
                mark_critical(ch)

        for r_node in root_nodes:
            mark_critical(r_node)

        # Compute service duration aggregates
        service_durations: dict[str, float] = {}
        for s in spans:
            service_durations[s.service_name] = round(
                service_durations.get(s.service_name, 0.0) + s.duration_ms, 2
            )

        total_dwell_ms = round(sum(d.dwell_time_ms for d in all_dwell_intervals), 2)
        has_error = any(s.status_code == "ERROR" for s in spans)

        return CausalTraceDAG(
            trace_id=trace_id,
            root_nodes=root_nodes,
            total_duration_ms=total_duration_ms,
            total_dwell_time_ms=total_dwell_ms,
            critical_path_span_ids=critical_path_ids,
            dwell_intervals=all_dwell_intervals,
            service_durations=service_durations,
            span_count=len(spans),
            has_error=has_error,
        )
