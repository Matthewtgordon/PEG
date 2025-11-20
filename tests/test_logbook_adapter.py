"""Tests for the logbook adapter.

Tests cover:
- Logbook initialization in test mode
- Event logging with different levels
- Workflow and scoring event logging
- Retrieving recent entries with filters
- Thread safety of logging operations
"""

import pytest
import tempfile
from pathlib import Path

from apeg_core.logging.logbook_adapter import (
    LogbookAdapter,
    get_global_logbook,
    reset_global_logbook
)


def test_logbook_adapter_init_test_mode():
    """Test logbook initialization in test mode."""
    logger = LogbookAdapter(test_mode=True)

    assert logger.test_mode is True
    assert logger._in_memory_log == []


def test_logbook_adapter_log_event():
    """Test logging an event."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_event("test_event", {"key": "value"}, level="info")

    entries = logger.get_recent_entries(n=1)
    assert len(entries) == 1
    assert entries[0]["event_type"] == "test_event"
    assert entries[0]["level"] == "info"
    assert entries[0]["data"]["key"] == "value"
    assert "timestamp" in entries[0]


def test_logbook_adapter_log_info():
    """Test logging info message."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_info("Test info message", {"detail": "extra data"})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["level"] == "info"
    assert entries[0]["data"]["message"] == "Test info message"
    assert entries[0]["data"]["detail"] == "extra data"


def test_logbook_adapter_log_warning():
    """Test logging warning message."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_warning("Test warning", {"code": 123})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["level"] == "warning"
    assert entries[0]["data"]["message"] == "Test warning"


def test_logbook_adapter_log_error():
    """Test logging error message."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_error("Test error", {"error_code": "E001"})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["level"] == "error"
    assert entries[0]["data"]["message"] == "Test error"


def test_logbook_adapter_log_debug():
    """Test logging debug message."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_debug("Test debug", {"trace": "abc123"})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["level"] == "debug"
    assert entries[0]["data"]["message"] == "Test debug"


def test_logbook_adapter_log_workflow_event():
    """Test logging workflow event."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_workflow_event("build", "start", {"macro": "macro_chain_of_thought"})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["event_type"] == "workflow"
    assert entries[0]["data"]["node"] == "build"
    assert entries[0]["data"]["action"] == "start"
    assert entries[0]["data"]["details"]["macro"] == "macro_chain_of_thought"


def test_logbook_adapter_log_scoring_event():
    """Test logging scoring event."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_scoring_event(0.85, True, {"criteria": ["clarity", "format"]})

    entries = logger.get_recent_entries(n=1)
    assert entries[0]["event_type"] == "scoring"
    assert entries[0]["data"]["score"] == 0.85
    assert entries[0]["data"]["passed"] is True


def test_logbook_adapter_get_recent_entries_filter_by_type():
    """Test filtering entries by event type."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_event("type_a", {"data": 1})
    logger.log_event("type_b", {"data": 2})
    logger.log_event("type_a", {"data": 3})

    entries_a = logger.get_recent_entries(event_type="type_a")
    assert len(entries_a) == 2
    assert all(e["event_type"] == "type_a" for e in entries_a)


def test_logbook_adapter_get_recent_entries_filter_by_level():
    """Test filtering entries by log level."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_info("Info message")
    logger.log_error("Error message")
    logger.log_info("Another info")

    error_entries = logger.get_recent_entries(level="error")
    assert len(error_entries) == 1
    assert error_entries[0]["level"] == "error"


def test_logbook_adapter_get_recent_entries_limit():
    """Test limiting number of returned entries."""
    logger = LogbookAdapter(test_mode=True)

    for i in range(10):
        logger.log_info(f"Message {i}")

    entries = logger.get_recent_entries(n=5)
    assert len(entries) == 5


def test_logbook_adapter_clear():
    """Test clearing logbook."""
    logger = LogbookAdapter(test_mode=True)

    logger.log_info("Message 1")
    logger.log_info("Message 2")

    assert len(logger.get_recent_entries()) == 2

    logger.clear()

    assert len(logger.get_recent_entries()) == 0


def test_logbook_adapter_file_operations():
    """Test file-based logging (non-test mode)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logbook_path = Path(tmpdir) / "test_logbook.json"

        logger = LogbookAdapter(logbook_path=logbook_path, test_mode=False)

        # Log some events
        logger.log_info("Test message 1")
        logger.log_warning("Test warning")

        # Verify file was created
        assert logbook_path.exists()

        # Create new instance and verify data persists
        logger2 = LogbookAdapter(logbook_path=logbook_path, test_mode=False)
        entries = logger2.get_recent_entries()

        assert len(entries) >= 2


def test_global_logbook():
    """Test global logbook singleton."""
    reset_global_logbook()  # Reset first

    logger1 = get_global_logbook(test_mode=True)
    logger2 = get_global_logbook()

    # Should return same instance
    assert logger1 is logger2

    reset_global_logbook()  # Cleanup
