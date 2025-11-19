"""
APEG Web API - HTTP interface for APEG Orchestrator.

This module provides a FastAPI-based web interface for:
- Running workflows via HTTP API
- Serving the web UI
- Managing workflow state and history
"""

from apeg_core.web.api import app
from apeg_core.web.server import main

__all__ = ["app", "main"]
