"""
Memory management system with short-term and long-term storage.
Includes optional vector store integration, summarization, pruning,
and per-task and per-agent namespaces.
"""
from __future__ import annotations

import logging
from typing import Dict, List


class MemoryManager:
    """Manages short-term and long-term memory for agents."""

    def __init__(self, short_term_limit: int = 10):
        self.short_term_limit = short_term_limit
        self.short_term: Dict[str, List[str]] = {}
        self.long_term: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)

    def add(self, namespace: str, message: str) -> None:
        """Add a message to short-term memory."""
        buffer = self.short_term.setdefault(namespace, [])
        buffer.append(message)
        if len(buffer) > self.short_term_limit:
            self._summarize(namespace)

    def _summarize(self, namespace: str) -> None:
        """Summarize and prune the short-term memory."""
        buffer = self.short_term.get(namespace, [])
        if not buffer:
            return
        summary = " ".join(buffer)
        lt_buffer = self.long_term.setdefault(namespace, [])
        lt_buffer.append(summary)
        self.short_term[namespace] = buffer[-self.short_term_limit:]

    def query_long_term(self, namespace: str) -> List[str]:
        """Retrieve long-term memories for a namespace."""
        return self.long_term.get(namespace, [])

    def prune(self, namespace: str) -> None:
        """Remove all memories for a namespace."""
        self.short_term.pop(namespace, None)
        self.long_term.pop(namespace, None)
