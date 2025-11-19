"""
APEG Web Server - Uvicorn server launcher.

This module provides the entry point for running the APEG web server.
It can be launched via:
- python -m apeg_core.web.server
- apeg serve (via CLI)
"""

import logging
import os
from pathlib import Path

import uvicorn

from apeg_core.web.api import app

logger = logging.getLogger(__name__)


def main(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """
    Run APEG Orchestrator web API server.

    Args:
        host: Host to bind to (default: 0.0.0.0 for all interfaces)
        port: Port to listen on (default: 8000)
        reload: Enable auto-reload for development (default: False)
        log_level: Logging level (default: info)
    """
    # Set working directory to repo root if SessionConfig.json not in cwd
    cwd = Path.cwd()
    config_path = cwd / "SessionConfig.json"

    if not config_path.exists():
        # Try to find repo root by looking for SessionConfig.json
        possible_roots = [
            cwd,
            cwd.parent,
            cwd.parent.parent,
            Path(__file__).parent.parent.parent.parent,
        ]

        for root in possible_roots:
            if (root / "SessionConfig.json").exists():
                os.chdir(root)
                logger.info("Changed working directory to: %s", root)
                break
        else:
            logger.warning(
                "SessionConfig.json not found. Make sure to run from repository root."
            )

    logger.info("Starting APEG Web Server...")
    logger.info("  Host: %s", host)
    logger.info("  Port: %s", port)
    logger.info("  Working directory: %s", Path.cwd())
    logger.info("  Reload mode: %s", reload)

    # Run uvicorn server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    main()
