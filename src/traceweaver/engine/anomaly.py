"""Anomaly detection engine for identifying statistical latency outliers in traces."""

from traceweaver.engine.store import ServiceStats
from traceweaver.receiver.span_normalizer import NormalizedSpan


class AnomalyDetector:
    """Detects spans exceeding statistical baselines."""

    def __init__(self, multiplier: float = 2.0, min_threshold_ms: float = 50.0):
        self.multiplier = multiplier
        self.min_threshold_ms = min_threshold_ms

    def inspect_span(
        self,
        span: NormalizedSpan,
        stats: ServiceStats | None = None,
    ) -> tuple[bool, str | None]:
        """Evaluate if span duration is an anomalous outlier relative to service history."""
        # Always flag explicit error statuses
        if span.status_code == "ERROR":
            msg = span.status_message or "Span status reported ERROR"
            return True, msg

        if not stats or stats.span_count < 5:
            # Not enough historical baseline data
            return False, None

        # Compare duration against p90 and p99
        threshold = max(self.min_threshold_ms, stats.p90_duration_ms * self.multiplier)
        if span.duration_ms > threshold:
            ratio = round(span.duration_ms / max(1.0, stats.p90_duration_ms), 1)
            reason = (
                f"Latency {span.duration_ms}ms is {ratio}x above service p90 baseline "
                f"({stats.p90_duration_ms}ms)"
            )
            return True, reason

        return False, None
