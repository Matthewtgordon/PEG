"""Filesystem connector for reading local files."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base_connector import BaseConnector


class FilesystemConnector(BaseConnector):
    """Connector that reads files from the local filesystem."""

    def connect(self) -> None:  # pragma: no cover
        self.logger.info("Using local filesystem")

    def disconnect(self) -> None:  # pragma: no cover
        self.logger.info("Closing filesystem connector")

    def _query(self, path: str) -> Any:
        file_path = Path(path)
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        raise FileNotFoundError(path)
