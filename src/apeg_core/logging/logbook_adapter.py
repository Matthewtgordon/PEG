"""Logbook adapter for APEG runtime logging.

This module provides thread-safe logging to Logbook.json with:
- Atomic writes to prevent corruption
- Structured log entries with timestamps
- Multiple log levels (info, warning, error, debug)
- Automatic file creation and initialization

Usage:
    logger = LogbookAdapter(logbook_path="Logbook.json")
    logger.log_event("build", {"macro": "macro_chain_of_thought", "score": 0.85})
    logger.log_error("Node execution failed", {"node": "review", "error": "..."})
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LogbookAdapter:
    """Thread-safe adapter for writing to Logbook.json.

    Attributes:
        logbook_path: Path to Logbook.json file
        test_mode: If True, don't actually write to file
        _lock: Thread lock for atomic writes
    """

    def __init__(
        self,
        logbook_path: str | Path = "Logbook.json",
        test_mode: bool = False
    ):
        """Initialize logbook adapter.

        Args:
            logbook_path: Path to Logbook.json
            test_mode: If True, log to memory instead of file
        """
        self.logbook_path = Path(logbook_path)
        self.test_mode = test_mode
        self._lock = Lock()
        self._in_memory_log: List[Dict[str, Any]] = []

        # Initialize logbook file if it doesn't exist
        if not test_mode and not self.logbook_path.exists():
            self._initialize_logbook()

        logger.info(
            "LogbookAdapter initialized (path=%s, test_mode=%s)",
            self.logbook_path,
            test_mode
        )

    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        level: str = "info"
    ) -> None:
        """Log an event to the logbook.

        Args:
            event_type: Type of event (e.g., "build", "review", "export")
            data: Event data dictionary
            level: Log level (info, warning, error, debug)
        """
        entry = {
            "timestamp": self._get_timestamp(),
            "level": level,
            "event_type": event_type,
            "data": data
        }

        self._append_entry(entry)

        logger.debug("Logged %s event: %s", level, event_type)

    def log_info(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log an info-level message.

        Args:
            message: Log message
            data: Optional additional data
        """
        self.log_event("info", {"message": message, **(data or {})}, level="info")

    def log_warning(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning-level message.

        Args:
            message: Warning message
            data: Optional additional data
        """
        self.log_event("warning", {"message": message, **(data or {})}, level="warning")

    def log_error(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error-level message.

        Args:
            message: Error message
            data: Optional additional data
        """
        self.log_event("error", {"message": message, **(data or {})}, level="error")

    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug-level message.

        Args:
            message: Debug message
            data: Optional additional data
        """
        self.log_event("debug", {"message": message, **(data or {})}, level="debug")

    def log_workflow_event(
        self,
        node: str,
        action: str,
        details: Dict[str, Any]
    ) -> None:
        """Log a workflow execution event.

        Args:
            node: Workflow node name (e.g., "build", "review")
            action: Action taken (e.g., "start", "complete", "fail")
            details: Event details
        """
        self.log_event(
            "workflow",
            {
                "node": node,
                "action": action,
                "details": details
            },
            level="info"
        )

    def log_scoring_event(
        self,
        score: float,
        passed: bool,
        details: Dict[str, Any]
    ) -> None:
        """Log a scoring event.

        Args:
            score: Overall score
            passed: Whether score passed threshold
            details: Scoring details
        """
        self.log_event(
            "scoring",
            {
                "score": score,
                "passed": passed,
                "details": details
            },
            level="info"
        )

    def get_recent_entries(
        self,
        n: int = 10,
        event_type: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent log entries.

        Args:
            n: Number of entries to retrieve
            event_type: Filter by event type (optional)
            level: Filter by log level (optional)

        Returns:
            List of log entries
        """
        if self.test_mode:
            entries = self._in_memory_log
        else:
            entries = self._read_logbook()

        # Filter by event_type if specified
        if event_type:
            entries = [e for e in entries if e.get("event_type") == event_type]

        # Filter by level if specified
        if level:
            entries = [e for e in entries if e.get("level") == level]

        # Return last n entries
        return entries[-n:]

    def clear(self) -> None:
        """Clear all log entries.

        Warning: This is destructive. Use only for testing.
        """
        if self.test_mode:
            self._in_memory_log.clear()
        else:
            with self._lock:
                self._write_logbook([])

        logger.warning("Logbook cleared")

    def _append_entry(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the logbook atomically.

        Args:
            entry: Log entry to append
        """
        if self.test_mode:
            self._in_memory_log.append(entry)
            return

        with self._lock:
            # Read current logbook
            entries = self._read_logbook()

            # Append new entry
            entries.append(entry)

            # Write back atomically
            self._write_logbook(entries)

    def _read_logbook(self) -> List[Dict[str, Any]]:
        """Read logbook from file.

        Returns:
            List of log entries
        """
        if not self.logbook_path.exists():
            return []

        try:
            with open(self.logbook_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("entries", [])
            else:
                logger.warning("Unexpected logbook format, returning empty list")
                return []

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse logbook: %s", exc)
            return []
        except Exception as exc:
            logger.error("Failed to read logbook: %s", exc)
            return []

    def _write_logbook(self, entries: List[Dict[str, Any]]) -> None:
        """Write logbook to file atomically.

        Args:
            entries: List of log entries
        """
        try:
            # Write to temporary file first
            temp_path = self.logbook_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)

            # Atomic replace
            temp_path.replace(self.logbook_path)

        except Exception as exc:
            logger.error("Failed to write logbook: %s", exc)
            raise

    def _initialize_logbook(self) -> None:
        """Initialize empty logbook file."""
        try:
            self.logbook_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.logbook_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

            logger.info("Initialized new logbook at %s", self.logbook_path)

        except Exception as exc:
            logger.error("Failed to initialize logbook: %s", exc)
            raise

    def _get_timestamp(self) -> str:
        """Get ISO 8601 timestamp.

        Returns:
            Timestamp string
        """
        return datetime.utcnow().isoformat() + "Z"


# Convenience singleton for global access
_global_logbook: Optional[LogbookAdapter] = None


def get_global_logbook(
    logbook_path: str | Path = "Logbook.json",
    test_mode: bool = False
) -> LogbookAdapter:
    """Get or create global logbook adapter instance.

    Args:
        logbook_path: Path to Logbook.json
        test_mode: If True, use in-memory logging

    Returns:
        Global LogbookAdapter instance
    """
    global _global_logbook

    if _global_logbook is None:
        _global_logbook = LogbookAdapter(logbook_path, test_mode)

    return _global_logbook


def reset_global_logbook() -> None:
    """Reset global logbook instance (for testing)."""
    global _global_logbook
    _global_logbook = None


__all__ = [
    "LogbookAdapter",
    "get_global_logbook",
    "reset_global_logbook",
]
