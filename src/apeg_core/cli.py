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

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    try:
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
