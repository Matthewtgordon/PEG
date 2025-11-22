"""Tests for the APEG Monitoring module.

Tests cover:
- MetricsRecorder initialization
- Counter operations
- Gauge operations
- Histogram operations
- Prometheus export format
- Global recorder singleton
"""

import pytest

from apeg_core.monitoring import (
    MetricsRecorder,
    get_global_recorder,
    reset_global_recorder,
)
from apeg_core.monitoring.metrics import HistogramData, HistogramBucket


class TestMetricsRecorder:
    """Tests for MetricsRecorder class."""

    def setup_method(self):
        """Reset global recorder before each test."""
        reset_global_recorder()

    def test_recorder_initialization(self):
        """Test MetricsRecorder initialization."""
        recorder = MetricsRecorder(prefix="test")
        assert recorder.prefix == "test"

    def test_counter_increment(self):
        """Test counter increment."""
        recorder = MetricsRecorder()
        recorder.inc_counter("requests_total")

        value = recorder.get_counter("requests_total")
        assert value == 1.0

    def test_counter_increment_by_value(self):
        """Test counter increment by specific value."""
        recorder = MetricsRecorder()
        recorder.inc_counter("bytes_processed", value=1024.0)

        value = recorder.get_counter("bytes_processed")
        assert value == 1024.0

    def test_counter_with_labels(self):
        """Test counter with labels."""
        recorder = MetricsRecorder()
        recorder.inc_counter("requests_total", {"method": "GET"})
        recorder.inc_counter("requests_total", {"method": "POST"})
        recorder.inc_counter("requests_total", {"method": "GET"})

        get_count = recorder.get_counter("requests_total", {"method": "GET"})
        post_count = recorder.get_counter("requests_total", {"method": "POST"})

        assert get_count == 2.0
        assert post_count == 1.0

    def test_gauge_set(self):
        """Test gauge set operation."""
        recorder = MetricsRecorder()
        recorder.set_gauge("temperature", 23.5)

        value = recorder.get_gauge("temperature")
        assert value == 23.5

    def test_gauge_with_labels(self):
        """Test gauge with labels."""
        recorder = MetricsRecorder()
        recorder.set_gauge("queue_depth", 10, {"queue": "main"})
        recorder.set_gauge("queue_depth", 5, {"queue": "retry"})

        main = recorder.get_gauge("queue_depth", {"queue": "main"})
        retry = recorder.get_gauge("queue_depth", {"queue": "retry"})

        assert main == 10
        assert retry == 5

    def test_histogram_observe(self):
        """Test histogram observation."""
        recorder = MetricsRecorder()
        recorder.observe_histogram("latency_seconds", 0.05)
        recorder.observe_histogram("latency_seconds", 0.15)
        recorder.observe_histogram("latency_seconds", 0.25)

        stats = recorder.get_histogram_stats("latency_seconds")
        assert stats["count"] == 3
        assert abs(stats["sum"] - 0.45) < 0.01
        assert abs(stats["mean"] - 0.15) < 0.01

    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        recorder = MetricsRecorder()
        recorder.observe_histogram("response_time", 0.1, {"endpoint": "/api"})
        recorder.observe_histogram("response_time", 0.2, {"endpoint": "/api"})

        stats = recorder.get_histogram_stats("response_time", {"endpoint": "/api"})
        assert stats["count"] == 2

    def test_histogram_buckets(self):
        """Test histogram bucket distribution."""
        recorder = MetricsRecorder()
        # Add values that fall into different buckets
        recorder.observe_histogram("latency", 0.001)  # <= 0.005
        recorder.observe_histogram("latency", 0.02)   # <= 0.025
        recorder.observe_histogram("latency", 0.5)    # <= 0.5

        stats = recorder.get_histogram_stats("latency")
        buckets = {b["le"]: b["count"] for b in stats["buckets"]}

        # Values accumulate in buckets
        assert buckets[0.005] == 1  # one value <= 0.005
        assert buckets[0.025] == 2  # two values <= 0.025
        assert buckets[0.5] == 3    # three values <= 0.5

    def test_get_metrics_all(self):
        """Test getting all metrics."""
        recorder = MetricsRecorder()
        recorder.inc_counter("counter1")
        recorder.set_gauge("gauge1", 42)
        recorder.observe_histogram("hist1", 0.1)

        metrics = recorder.get_metrics()

        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert "metadata" in metrics

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        recorder = MetricsRecorder()
        recorder.inc_counter("test_counter")

        recorder.reset()

        value = recorder.get_counter("test_counter")
        assert value == 0.0

    def test_prefix_normalization(self):
        """Test metric name prefix normalization."""
        recorder = MetricsRecorder(prefix="myapp")

        # Should add prefix
        recorder.inc_counter("requests")
        value = recorder.get_counter("myapp_requests")
        assert value == 1.0

        # Should not double prefix
        recorder.inc_counter("myapp_errors")
        value = recorder.get_counter("myapp_errors")
        assert value == 1.0

    def test_register_metric_help(self):
        """Test registering metric help text."""
        recorder = MetricsRecorder()
        recorder.register_metric("requests_total", "Total number of requests")

        # Help text is used in Prometheus export
        output = recorder.export_prometheus_format()
        # If we have the counter, help should be included
        recorder.inc_counter("requests_total")
        output = recorder.export_prometheus_format()
        assert "# HELP" in output


class TestPrometheusExport:
    """Tests for Prometheus format export."""

    def test_export_counters(self):
        """Test counter export in Prometheus format."""
        recorder = MetricsRecorder(prefix="test")
        recorder.inc_counter("requests", value=5)

        output = recorder.export_prometheus_format()
        assert "# TYPE test_requests counter" in output
        assert "test_requests" in output

    def test_export_with_labels(self):
        """Test export with labels."""
        recorder = MetricsRecorder(prefix="test")
        recorder.inc_counter("http_requests", {"method": "GET", "status": "200"})

        output = recorder.export_prometheus_format()
        assert 'method="GET"' in output
        assert 'status="200"' in output

    def test_export_histogram(self):
        """Test histogram export in Prometheus format."""
        recorder = MetricsRecorder(prefix="test")
        recorder.observe_histogram("latency", 0.1)

        output = recorder.export_prometheus_format()
        assert "# TYPE test_latency histogram" in output
        assert "test_latency_bucket" in output
        assert "test_latency_sum" in output
        assert "test_latency_count" in output


class TestHistogramData:
    """Tests for HistogramData class."""

    def test_default_buckets(self):
        """Test default bucket creation."""
        hist = HistogramData.with_default_buckets()

        assert len(hist.buckets) > 0
        # Should include +Inf bucket
        assert hist.buckets[-1].le == float('inf')

    def test_observe_updates_buckets(self):
        """Test that observe updates appropriate buckets."""
        hist = HistogramData.with_default_buckets()
        hist.observe(0.003)  # Should be in 0.005 and all higher buckets

        # Check that appropriate buckets were updated
        assert hist.buckets[0].count == 1  # 0.005 bucket
        assert hist.count == 1
        assert hist.sum == 0.003


class TestGlobalRecorder:
    """Tests for global recorder singleton."""

    def setup_method(self):
        """Reset before each test."""
        reset_global_recorder()

    def teardown_method(self):
        """Clean up."""
        reset_global_recorder()

    def test_global_singleton(self):
        """Test global recorder is singleton."""
        r1 = get_global_recorder()
        r2 = get_global_recorder()
        assert r1 is r2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        r1 = get_global_recorder()
        reset_global_recorder()
        r2 = get_global_recorder()
        assert r1 is not r2

    def test_global_prefix(self):
        """Test global recorder uses default prefix."""
        recorder = get_global_recorder()
        assert recorder.prefix == "apeg"
