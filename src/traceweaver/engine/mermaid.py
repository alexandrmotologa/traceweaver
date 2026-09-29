"""Mermaid sequence diagram and graph exporter for CausalTraceDAG."""

from traceweaver.engine.correlator import CausalNode, CausalTraceDAG


def export_mermaid_sequence(dag: CausalTraceDAG) -> str:
    """Generate a Mermaid sequence diagram representing the causal flow and dwell times."""
    lines: list[str] = [
        "sequenceDiagram",
        "    autonumber",
    ]

    # Gather participants in order of appearance
    participants: list[str] = []
    seen_services: set[str] = set()

    def collect_services(node: CausalNode) -> None:
        svc = node.span.service_name
        if svc not in seen_services:
            seen_services.add(svc)
            participants.append(svc)
        for dwell in node.dwell_intervals:
            q_name = f"queue_{dwell.queue_name.replace('.', '_').replace('-', '_')}"
            if q_name not in seen_services:
                seen_services.add(q_name)
                participants.append(q_name)
        for ch in node.children:
            collect_services(ch)

    for r in dag.root_nodes:
        collect_services(r)

    # Participant declarations
    for p in participants:
        safe_alias = p.replace("-", "_").replace(".", "_")
        label = p.replace("queue_", "Queue: ") if p.startswith("queue_") else p
        lines.append(f"    participant {safe_alias} as {label}")

    def render_interactions(node: CausalNode, caller: str | None = None) -> None:
        curr_svc = node.span.service_name.replace("-", "_").replace(".", "_")

        # If incoming dwell intervals exist, display queue wait
        for dwell in node.dwell_intervals:
            q_alias = f"queue_{dwell.queue_name.replace('.', '_').replace('-', '_')}"
            lines.append(
                f"    Note over {q_alias}: ░░ Queue Dwell: {dwell.dwell_time_ms}ms ({dwell.queue_name})"
            )
            lines.append(f"    {q_alias}->>+{curr_svc}: Consume ({node.span.name})")

        if caller and not node.dwell_intervals:
            op_label = f"{node.span.name} ({node.span.duration_ms}ms)"
            if node.is_critical_path:
                op_label += " [CP]"
            lines.append(f"    {caller}->>+{curr_svc}: {op_label}")

        for ch in node.children:
            render_interactions(ch, caller=curr_svc)

        if caller and not node.dwell_intervals:
            status = "ERR" if node.span.status_code == "ERROR" else "OK"
            lines.append(f"    {curr_svc}-->>-{caller}: {status}")
        elif node.dwell_intervals:
            lines.append(f"    deactivate {curr_svc}")

    for r in dag.root_nodes:
        render_interactions(r, caller=None)

    return "\n".join(lines)
