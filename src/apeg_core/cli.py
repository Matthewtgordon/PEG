#!/usr/bin/env python3
"""
APEG CLI - Command-line interface for APEG runtime.

Usage:
    python -m apeg_core
    python -m apeg_core --workflow demo
    python -m apeg_core validate
    python src/apeg_core/cli.py
    apeg  # If installed via pip
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def validate_environment() -> Tuple[bool, List[str]]:
    """
    Validate APEG environment configuration.

    Checks:
    - Required environment variables
    - API key presence (with masking)
    - Configuration files
    - Python dependencies

    Returns:
        Tuple of (success: bool, messages: List[str])
    """
    messages = []
    all_valid = True

    # Determine mode
    test_mode = os.environ.get("APEG_TEST_MODE", "false").lower() == "true"
    mode = "TEST" if test_mode else "PRODUCTION"
    messages.append(f"🔧 Mode: {mode}")

    # Required env vars for production
    if not test_mode:
        required_vars = [
            ("OPENAI_API_KEY", "OpenAI API integration", True),
        ]

        optional_vars = [
            ("SHOPIFY_SHOP_URL", "Shopify integration", False),
            ("SHOPIFY_ACCESS_TOKEN", "Shopify integration", False),
            ("ETSY_API_KEY", "Etsy integration", False),
            ("ETSY_SHOP_ID", "Etsy integration", False),
            ("GITHUB_PAT", "GitHub integration", False),
        ]
    else:
        # In test mode, API keys are optional
        required_vars = []
        optional_vars = [
            ("OPENAI_API_KEY", "OpenAI API (optional in test mode)", False),
        ]

    messages.append("\n📋 Required Environment Variables:")
    for var_name, description, required in required_vars:
        value = os.environ.get(var_name)
        if value:
            # Mask API key for security
            masked = value[:10] + "..." if len(value) > 10 else "***"
            messages.append(f"  ✅ {var_name}: {masked} ({description})")
        else:
            messages.append(f"  ❌ {var_name}: NOT SET ({description})")
            all_valid = False if required else all_valid

    if optional_vars:
        messages.append("\n📋 Optional Environment Variables:")
        for var_name, description, _ in optional_vars:
            value = os.environ.get(var_name)
            if value:
                masked = value[:10] + "..." if len(value) > 10 else "***"
                messages.append(f"  ✅ {var_name}: {masked} ({description})")
            else:
                messages.append(f"  ⚠️  {var_name}: not set ({description})")

    # Check configuration environment variables
    messages.append("\n⚙️  Configuration Settings:")
    config_vars = [
        ("APEG_TEST_MODE", os.environ.get("APEG_TEST_MODE", "false")),
        ("APEG_USE_LLM_SCORING", os.environ.get("APEG_USE_LLM_SCORING", "default (true)")),
        ("APEG_RULE_WEIGHT", os.environ.get("APEG_RULE_WEIGHT", "default (0.6)")),
        ("OPENAI_DEFAULT_MODEL", os.environ.get("OPENAI_DEFAULT_MODEL", "default (gpt-4)")),
        ("OPENAI_TEMPERATURE", os.environ.get("OPENAI_TEMPERATURE", "default (0.7)")),
    ]

    for var_name, value in config_vars:
        messages.append(f"  • {var_name}: {value}")

    # Check for .env file
    messages.append("\n📄 Configuration Files:")
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        messages.append(f"  ✅ .env file found at {env_file}")
    else:
        messages.append(f"  ⚠️  No .env file (using environment variables)")

    env_sample = Path.cwd() / ".env.sample"
    if env_sample.exists():
        messages.append(f"  ✅ .env.sample template found")
    else:
        messages.append(f"  ⚠️  No .env.sample template")

    # Check required JSON config files
    required_configs = [
        "SessionConfig.json",
        "WorkflowGraph.json",
        "Knowledge.json",
        "PromptScoreModel.json",
    ]

    for config_file in required_configs:
        config_path = Path.cwd() / config_file
        if config_path.exists():
            messages.append(f"  ✅ {config_file}")
        else:
            messages.append(f"  ❌ {config_file} - MISSING")
            all_valid = False

    # Check Python dependencies
    messages.append("\n📦 Python Dependencies:")
    dependencies = [
        ("openai", "OpenAI API client"),
        ("fastapi", "Web server"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("pytest", "Testing"),
    ]

    for package, description in dependencies:
        try:
            __import__(package)
            messages.append(f"  ✅ {package}: installed ({description})")
        except ImportError:
            messages.append(f"  ❌ {package}: NOT INSTALLED ({description})")
            all_valid = False

    # Final summary
    messages.append("\n" + "="*60)
    if all_valid:
        messages.append("✅ Environment validation PASSED")
        messages.append("\nYou can now run:")
        if test_mode:
            messages.append("  python -m apeg_core           # Run workflow (test mode)")
            messages.append("  python -m apeg_core serve     # Start web server (test mode)")
        else:
            messages.append("  python -m apeg_core           # Run workflow")
            messages.append("  python -m apeg_core serve     # Start web server")
    else:
        messages.append("❌ Environment validation FAILED")
        messages.append("\nPlease fix the issues above before running APEG.")
        messages.append("See .env.sample for required environment variables.")

    return all_valid, messages


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

    # Subcommands
    parser.add_argument(
        "command",
        nargs="?",
        choices=["serve", "validate"],
        help="Command to execute (serve = start web server, validate = check environment)",
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
        # Handle 'validate' command
        if args.command == "validate":
            logger.info("APEG Environment Validation")
            logger.info("="*60)

            success, messages = validate_environment()

            # Print all messages
            for message in messages:
                print(message)

            return 0 if success else 1

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
