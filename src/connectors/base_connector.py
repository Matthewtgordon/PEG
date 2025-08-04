"""
Abstract connector interface providing auth, retry, rate limiting,
and logging for PEGGPT connectors.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseConnector(ABC):
    """Base class for external service connectors."""

    def __init__(self, auth: Optional[str] = None, rate_limit: float = 0.0, retries: int = 3):
        self.auth = auth
        self.rate_limit = rate_limit
        self.retries = retries
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_call = 0.0

    def _throttle(self) -> None:
        if self.rate_limit:
            now = time.time()
            remaining = self.rate_limit - (now - self._last_call)
            if remaining > 0:
                time.sleep(remaining)
            self._last_call = time.time()

    def query(self, *args, **kwargs) -> Any:
        for attempt in range(1, self.retries + 1):
            try:
                self._throttle()
                return self._query(*args, **kwargs)
            except Exception as exc:
                self.handle_error(exc, attempt)
        raise RuntimeError("Max retries exceeded")

    @abstractmethod
    def _query(self, *args, **kwargs) -> Any:
        """Perform the connector-specific query."""

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Terminate the connection."""

    def handle_error(self, error: Exception, attempt: int) -> None:
        self.logger.error("Error on attempt %s: %s", attempt, error)
