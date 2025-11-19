#!/usr/bin/env python3
"""
APEG CLI - Command-line interface for APEG runtime.

Usage:
    python -m apeg_core
    python -m apeg_core --workflow demo
    python src/apeg_core/cli.py
    apeg  # If installed via pip
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from apeg_core import APEGOrchestrator, __version__


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def find_config_file(filename: str, search_path: Optional[Path] = None) -> Path:
    """Find a configuration file in the current directory or search path."""
    if search_path is None:
        search_path = Path.cwd()

    config_file = search_path / filename
    if config_file.exists():
        return config_file

    raise FileNotFoundError(
        f"Configuration file '{filename}' not found in {search_path}. "
        f"Please ensure all required config files are present."
    )


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="APEG - Autonomous Prompt Engineering Graph Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run default workflow
  %(prog)s --workflow demo    # Run demo workflow
  %(prog)s --debug            # Enable debug logging
  %(prog)s --config-dir /path # Use configs from specific directory
  %(prog)s serve              # Start web server
  %(prog)s serve --port 8080  # Start web server on custom port

Commands:
  (none)    Run workflow once (default behavior)
  serve     Start web server with API and UI

Configuration Files:
  The following files must be present in the config directory:
  - SessionConfig.json
  - WorkflowGraph.json
  - Knowledge.json
  - TagEnum.json
  - PromptModules.json
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"APEG v{__version__}",
    )

    # Subcommand for 'serve'
    parser.add_argument(
        "command",
        nargs="?",
        choices=["serve"],
        help="Command to execute (serve = start web server)",
    )

    parser.add_argument(
        "--workflow",
        type=str,
        default="default",
        help="Workflow to execute (default: default)",
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory containing configuration files (default: current directory)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Web server options
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Web server host (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web server port (default: 8000)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development (web server only)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    try:
        # Handle 'serve' command
        if args.command == "serve":
            logger.info("APEG Web Server v%s starting...", __version__)
            logger.info("Config directory: %s", args.config_dir)

            # Import web server module
            from apeg_core.web.server import main as serve_main

            # Change to config directory
            import os
            os.chdir(args.config_dir)

            # Start web server
            serve_main(
                host=args.host,
                port=args.port,
                reload=args.reload,
                log_level="debug" if args.debug else "info",
            )
            return 0

        # Default: run workflow once
        logger.info("APEG Runtime v%s starting...", __version__)
        logger.info("Config directory: %s", args.config_dir)
        logger.info("Workflow: %s", args.workflow)

        # Find required configuration files
        config_path = find_config_file("SessionConfig.json", args.config_dir)
        workflow_path = find_config_file("WorkflowGraph.json", args.config_dir)

        logger.info("Loading configurations...")
        logger.info("  SessionConfig: %s", config_path)
        logger.info("  WorkflowGraph: %s", workflow_path)

        # Initialize orchestrator
        orchestrator = APEGOrchestrator(
            config_path=config_path,
            workflow_graph_path=workflow_path,
        )

        # Execute workflow
        logger.info("Executing workflow...")
        orchestrator.execute_graph()

        logger.info("✅ Workflow complete!")
        return 0

    except FileNotFoundError as e:
        logger.error("❌ Configuration error: %s", e)
        return 1

    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.exception("❌ Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
