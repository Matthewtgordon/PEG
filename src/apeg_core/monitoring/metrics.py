"""
APEG Metrics Recorder - Lightweight metrics collection for observability.

This module provides a simple in-memory metrics collector that can be
extended to export to external systems (Prometheus, CloudWatch, etc.)
in production environments.

Supported metric types:
- Counters: Monotonically increasing values (e.g., request counts)
- Histograms: Distribution of values (e.g., latency)
- Gauges: Point-in-time values (e.g., queue depth)

The implementation is intentionally minimal to avoid dependencies,
but follows Prometheus naming conventions for easy integration.

Usage:
    recorder = MetricsRecorder()
    recorder.inc_counter("apeg_llm_calls_total", {"role": "ENGINEER"})
    recorder.observe_histogram("apeg_llm_latency_seconds", 0.5, {"role": "ENGINEER"})
    metrics = recorder.get_metrics()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HistogramBucket:
    """
    Histogram bucket for tracking value distributions.

    Attributes:
        le: Less-than-or-equal boundary
        count: Number of observations <= le
    """
    le: float
    count: int = 0


@dataclass
class HistogramData:
    """
    Histogram data with configurable buckets.

    Attributes:
        buckets: List of histogram buckets
        sum: Sum of all observed values
        count: Total number of observations
    """
    buckets: List[HistogramBucket] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0

    @classmethod
    def with_default_buckets(cls) -> "HistogramData":
        """Create histogram with default latency buckets."""
        # Default buckets suitable for latency in seconds
        boundaries = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        buckets = [HistogramBucket(le=b) for b in boundaries]
        buckets.append(HistogramBucket(le=float('inf')))  # +Inf bucket
        return cls(buckets=buckets)

    def observe(self, value: float) -> None:
        """Record an observation."""
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket.le:
                bucket.count += 1


class MetricsRecorder:
    """
    Thread-safe metrics recorder with counter and histogram support.

    This is a lightweight implementation suitable for development and
    small-scale production. For high-scale production, consider
    integrating with Prometheus client or similar.

    Attributes:
        counters: Dictionary of counter metrics
        histograms: Dictionary of histogram metrics
        gauges: Dictionary of gauge metrics
    """

    def __init__(self, prefix: str = "apeg"):
        """
        Initialize the metrics recorder.

        Args:
            prefix: Prefix for all metric names (default: "apeg")
        """
        self.prefix = prefix
        self._lock = threading.Lock()

        # Metrics storage: metric_name -> labels_tuple -> value
        self._counters: Dict[str, Dict[Tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[Tuple, HistogramData]] = defaultdict(dict)
        self._gauges: Dict[str, Dict[Tuple, float]] = defaultdict(lambda: defaultdict(float))

        # Metadata
        self._metric_help: Dict[str, str] = {}
        self._start_time = time.time()

        logger.debug("MetricsRecorder initialized with prefix: %s", prefix)

    def _normalize_name(self, name: str) -> str:
        """Ensure metric name has prefix."""
        if not name.startswith(self.prefix):
            return f"{self.prefix}_{name}"
        return name

    def _labels_to_tuple(self, labels: Optional[Dict[str, str]]) -> Tuple:
        """Convert labels dict to hashable tuple."""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def register_metric(self, name: str, help_text: str) -> None:
        """
        Register a metric with help text.

        Args:
            name: Metric name
            help_text: Description of the metric
        """
        name = self._normalize_name(name)
        self._metric_help[name] = help_text

    def inc_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            labels: Optional label dictionary
            value: Increment value (default: 1.0)
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            self._counters[name][labels_key] += value

        logger.debug("Counter %s%s incremented by %.2f", name, labels or {}, value)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Set a gauge metric to a specific value.

        Args:
            name: Gauge name
            value: Value to set
            labels: Optional label dictionary
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            self._gauges[name][labels_key] = value

        logger.debug("Gauge %s%s set to %.2f", name, labels or {}, value)

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record an observation in a histogram.

        Args:
            name: Histogram name
            value: Value to observe
            labels: Optional label dictionary
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            if labels_key not in self._histograms[name]:
                self._histograms[name][labels_key] = HistogramData.with_default_buckets()
            self._histograms[name][labels_key].observe(value)

        logger.debug("Histogram %s%s observed %.4f", name, labels or {}, value)

    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """
        Get current counter value.

        Args:
            name: Counter name
            labels: Optional label dictionary

        Returns:
            Current counter value
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            return self._counters[name][labels_key]

    def get_gauge(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """
        Get current gauge value.

        Args:
            name: Gauge name
            labels: Optional label dictionary

        Returns:
            Current gauge value
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            return self._gauges[name][labels_key]

    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get histogram statistics.

        Args:
            name: Histogram name
            labels: Optional label dictionary

        Returns:
            Dictionary with count, sum, and bucket data
        """
        name = self._normalize_name(name)
        labels_key = self._labels_to_tuple(labels)

        with self._lock:
            if labels_key not in self._histograms[name]:
                return {"count": 0, "sum": 0.0, "buckets": []}

            hist = self._histograms[name][labels_key]
            return {
                "count": hist.count,
                "sum": hist.sum,
                "mean": hist.sum / hist.count if hist.count > 0 else 0.0,
                "buckets": [
                    {"le": b.le, "count": b.count}
                    for b in hist.buckets
                ],
            }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.

        Returns:
            Dictionary with all metrics organized by type
        """
        with self._lock:
            result = {
                "counters": {},
                "gauges": {},
                "histograms": {},
                "metadata": {
                    "uptime_seconds": time.time() - self._start_time,
                    "prefix": self.prefix,
                },
            }

            # Counters
            for name, label_values in self._counters.items():
                result["counters"][name] = {
                    str(dict(labels)): value
                    for labels, value in label_values.items()
                }

            # Gauges
            for name, label_values in self._gauges.items():
                result["gauges"][name] = {
                    str(dict(labels)): value
                    for labels, value in label_values.items()
                }

            # Histograms
            for name, label_values in self._histograms.items():
                result["histograms"][name] = {}
                for labels, hist in label_values.items():
                    result["histograms"][name][str(dict(labels))] = {
                        "count": hist.count,
                        "sum": hist.sum,
                        "mean": hist.sum / hist.count if hist.count > 0 else 0.0,
                    }

            return result

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self._start_time = time.time()

        logger.info("MetricsRecorder reset")

    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-compatible text output
        """
        lines = []

        with self._lock:
            # Export counters
            for name, label_values in self._counters.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} counter")
                for labels, value in label_values.items():
                    labels_str = self._format_labels(labels)
                    lines.append(f"{name}{labels_str} {value}")

            # Export gauges
            for name, label_values in self._gauges.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} gauge")
                for labels, value in label_values.items():
                    labels_str = self._format_labels(labels)
                    lines.append(f"{name}{labels_str} {value}")

            # Export histograms
            for name, label_values in self._histograms.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} histogram")
                for labels, hist in label_values.items():
                    labels_str = self._format_labels(labels)
                    for bucket in hist.buckets:
                        le_label = f',le="{bucket.le}"' if labels else f'le="{bucket.le}"'
                        bucket_labels = labels_str.rstrip("}") + le_label + "}" if labels_str else "{" + le_label.lstrip(",") + "}"
                        lines.append(f"{name}_bucket{bucket_labels} {bucket.count}")
                    lines.append(f"{name}_sum{labels_str} {hist.sum}")
                    lines.append(f"{name}_count{labels_str} {hist.count}")

        return "\n".join(lines)

    def _format_labels(self, labels: Tuple) -> str:
        """Format labels tuple as Prometheus label string."""
        if not labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in labels]
        return "{" + ",".join(parts) + "}"


# Global singleton
_global_recorder: Optional[MetricsRecorder] = None


def get_global_recorder(prefix: str = "apeg") -> MetricsRecorder:
    """
    Get or create global metrics recorder.

    Args:
        prefix: Metric name prefix (only used on first call)

    Returns:
        Global MetricsRecorder instance
    """
    global _global_recorder

    if _global_recorder is None:
        _global_recorder = MetricsRecorder(prefix)

    return _global_recorder


def reset_global_recorder() -> None:
    """Reset global recorder (for testing)."""
    global _global_recorder
    _global_recorder = None


__all__ = [
    "MetricsRecorder",
    "HistogramData",
    "HistogramBucket",
    "get_global_recorder",
    "reset_global_recorder",
]
