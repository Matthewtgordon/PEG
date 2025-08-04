"""Example OpenAI connector using BaseConnector."""
from __future__ import annotations

from typing import Any

from .base_connector import BaseConnector


class OpenAIConnector(BaseConnector):
    """Stub connector for the OpenAI API."""

    def connect(self) -> None:  # pragma: no cover - no real connection
        self.logger.info("Connecting to OpenAI")

    def disconnect(self) -> None:  # pragma: no cover
        self.logger.info("Disconnecting from OpenAI")

    def _query(self, prompt: str) -> Any:
        return f"OpenAI response to: {prompt}"
