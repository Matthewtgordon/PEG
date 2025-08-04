"""Example GitHub connector using BaseConnector."""
from __future__ import annotations

from typing import Any, Dict

from .base_connector import BaseConnector


class GitHubConnector(BaseConnector):
    """Stub connector for the GitHub API."""

    def connect(self) -> None:  # pragma: no cover
        self.logger.info("Connecting to GitHub")

    def disconnect(self) -> None:  # pragma: no cover
        self.logger.info("Disconnecting from GitHub")

    def _query(self, repo: str) -> Dict[str, Any]:
        return {"repo": repo, "status": "ok"}
