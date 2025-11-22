"""
APEG Monitoring Package - Metrics collection and observability.

This package provides lightweight metrics collection for APEG runtime,
designed to be extended with external monitoring systems (Prometheus, etc.)
in production environments.

Components:
- MetricsRecorder: In-memory metrics collector with counter/histogram support
- get_global_recorder: Singleton access to global recorder

Usage:
    from apeg_core.monitoring import get_global_recorder

    recorder = get_global_recorder()
    recorder.inc_counter("llm_calls_total", {"role": "ENGINEER"})
    recorder.observe_histogram("llm_latency_seconds", 0.5, {"role": "ENGINEER"})
"""

from apeg_core.monitoring.metrics import (
    MetricsRecorder,
    get_global_recorder,
    reset_global_recorder,
)

__all__ = [
    "MetricsRecorder",
    "get_global_recorder",
    "reset_global_recorder",
]
