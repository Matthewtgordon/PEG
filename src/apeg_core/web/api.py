"""
APEG Web API - FastAPI application and endpoints.

Provides HTTP endpoints for:
- POST /api/run - Execute workflow with a goal
- GET /api/health - Health check
- GET /api/keys/status - Check API key configuration status
- POST /setup/keys - Configure API keys
- GET /dashboard - Serve interactive dashboard
- GET /ready - Quick readiness probe
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from apeg_core.orchestrator import APEGOrchestrator
from apeg_core.utils.errors import PEGError, APIError

logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    """Request model for running a workflow."""

    goal: str = Field(..., description="The goal or task for APEG to accomplish")
    workflow_name: Optional[str] = Field(None, description="Workflow to execute (default: 'default')")
    max_steps: Optional[int] = Field(None, description="Maximum execution steps (default: from config)")


class RunResponse(BaseModel):
    """Response model for workflow execution."""

    success: bool = Field(..., description="Whether the workflow completed successfully")
    final_output: str = Field(..., description="Final output from the workflow")
    score: Optional[float] = Field(None, description="Quality score (if available)")
    history: Optional[List[Dict[str, Any]]] = Field(None, description="Execution history")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="APEG version")
    keys_configured: Optional[bool] = Field(None, description="Whether API keys are configured")
    agents_count: Optional[int] = Field(None, description="Number of loaded agents")


class KeysSetupRequest(BaseModel):
    """Request model for setting up API keys."""

    shopify_token: Optional[str] = Field(None, description="Shopify Admin API access token")
    shopify_domain: Optional[str] = Field(None, description="Shopify store domain")
    etsy_key: Optional[str] = Field(None, description="Etsy API key")
    etsy_access_token: Optional[str] = Field(None, description="Etsy OAuth access token")
    etsy_shop_id: Optional[str] = Field(None, description="Etsy shop ID")


class KeysStatusResponse(BaseModel):
    """Response model for key status check."""

    shopify: Dict[str, Any] = Field(..., description="Shopify configuration status")
    etsy: Dict[str, Any] = Field(..., description="Etsy configuration status")


# Create FastAPI app
app = FastAPI(
    title="APEG Orchestrator API",
    description="HTTP API for APEG Autonomous Prompt Engineering Graph - Enterprise Edition",
    version="1.0.0",
)


# Global exception handler for PEGError
@app.exception_handler(PEGError)
async def peg_error_handler(request: Request, exc: PEGError) -> JSONResponse:
    """Handle PEG-specific errors with structured response."""
    logger.error("PEG error: %s", exc)
    return JSONResponse(
        status_code=502,
        content=exc.to_dict(),
    )


# Global exception handler for generic exceptions
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.exception("Unexpected error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint with extended status information.

    Returns:
        Health status, version, and configuration info
    """
    from apeg_core import __version__

    # Check if keys are configured
    keys_configured = False
    try:
        from apeg_core.connectors.ecomm import EcommConnector
        status = EcommConnector.get_keys_status()
        keys_configured = status.get("shopify", {}).get("configured", False) or \
                         status.get("etsy", {}).get("configured", False)
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version=__version__,
        keys_configured=keys_configured,
        agents_count=0,  # Will be populated by orchestrator if available
    )


@app.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Quick readiness probe for container orchestration.

    Returns:
        Simple ready status and key configuration check
    """
    keys_exist = os.path.exists(".keys.enc")
    return {
        "ready": True,
        "keys_configured": keys_exist,
    }


@app.get("/api/keys/status", response_model=KeysStatusResponse)
async def get_keys_status() -> KeysStatusResponse:
    """
    Check the configuration status of API keys.

    Returns:
        Status of Shopify and Etsy key configuration
    """
    try:
        from apeg_core.connectors.ecomm import EcommConnector
        status = EcommConnector.get_keys_status()
        return KeysStatusResponse(**status)
    except Exception as e:
        logger.error("Failed to check keys status: %s", e)
        return KeysStatusResponse(
            shopify={"configured": False, "error": str(e)},
            etsy={"configured": False, "error": str(e)},
        )


@app.post("/setup/keys")
async def setup_keys(payload: KeysSetupRequest) -> Dict[str, Any]:
    """
    Configure API keys with encryption.

    This endpoint saves API keys securely using Fernet encryption.
    Keys are stored in .keys.enc file.

    Args:
        payload: KeysSetupRequest with API credentials

    Returns:
        Dictionary with saved/skipped key status
    """
    try:
        from apeg_core.connectors.ecomm import EcommConnector

        result = EcommConnector.save_keys(
            shopify_token=payload.shopify_token,
            shopify_domain=payload.shopify_domain,
            etsy_key=payload.etsy_key,
            etsy_access_token=payload.etsy_access_token,
            etsy_shop_id=payload.etsy_shop_id,
        )

        logger.info("Keys configured: saved=%s", result.get("saved", []))

        return {
            "success": True,
            "message": "Keys saved and encrypted successfully",
            **result,
        }

    except Exception as e:
        logger.error("Failed to save keys: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save keys: {e}")


@app.post("/api/run", response_model=RunResponse)
async def run_workflow(payload: RunRequest) -> RunResponse:
    """
    Run the configured workflow graph once for a single goal.

    This endpoint:
    1. Initializes APEGOrchestrator with configuration
    2. Executes the workflow for the given goal
    3. Returns the final output, score, and history

    Args:
        payload: RunRequest with goal, optional workflow_name and max_steps

    Returns:
        RunResponse with execution results

    Raises:
        HTTPException: If workflow execution fails
    """
    logger.info("Received workflow run request: goal='%s'", payload.goal[:100])

    try:
        # Find config files in current working directory
        config_path = Path.cwd() / "SessionConfig.json"
        workflow_path = Path.cwd() / "WorkflowGraph.json"

        if not config_path.exists():
            raise FileNotFoundError(f"SessionConfig.json not found at {config_path}")
        if not workflow_path.exists():
            raise FileNotFoundError(f"WorkflowGraph.json not found at {workflow_path}")

        # Initialize orchestrator
        orchestrator = APEGOrchestrator(
            config_path=config_path,
            workflow_graph_path=workflow_path,
        )

        # Store goal in orchestrator state for nodes to access
        orchestrator.state["goal"] = payload.goal
        if payload.max_steps:
            orchestrator.state["max_steps"] = payload.max_steps

        # Execute workflow
        logger.info("Executing workflow...")
        orchestrator.execute_graph()

        # Extract results
        state = orchestrator.get_state()
        history = orchestrator.get_history()

        # Determine success based on whether we reached export or encountered errors
        success = any(
            entry.get("node") == "export" and entry.get("result") == "__end__"
            for entry in history
        )

        final_output = state.get("output", "")
        score = state.get("last_score")

        logger.info("Workflow complete: success=%s, score=%s", success, score)

        return RunResponse(
            success=success,
            final_output=str(final_output),
            score=float(score) if score is not None else None,
            history=history,
        )

    except FileNotFoundError as e:
        logger.error("Configuration file not found: %s", e)
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")

    except Exception as exc:
        logger.exception("Workflow execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    """
    Serve the interactive dashboard.

    Returns:
        HTML file for the dashboard UI
    """
    static_path = Path(__file__).parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path, media_type="text/html")

    # Fallback to minimal HTML if static file not found
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <body style="font-family:sans-serif;background:#1a1a2e;color:#fff;padding:40px">
        <h1>PEG Dashboard</h1>
        <p>Static files not found. Please ensure src/apeg_core/web/static/index.html exists.</p>
        <p><a href="/api/health" style="color:#00d9ff">Check API Health</a></p>
        </body>
        </html>
        """,
        status_code=200,
    )


@app.on_event("startup")
async def startup_check():
    """
    Startup event handler - check configuration.
    """
    logger.info("APEG API starting up...")

    # Check for API keys
    if not os.path.exists(".keys.enc"):
        logger.warning(
            "No API keys found! Configure keys via:\n"
            "  POST /setup/keys with shopify_token, etsy_key, etc.\n"
            "  Or visit /dashboard for interactive setup."
        )

    # Check for config files
    config_path = Path.cwd() / "SessionConfig.json"
    workflow_path = Path.cwd() / "WorkflowGraph.json"

    if not config_path.exists():
        logger.warning("SessionConfig.json not found in current directory")
    if not workflow_path.exists():
        logger.warning("WorkflowGraph.json not found in current directory")

    logger.info("APEG API ready. Dashboard available at /dashboard")


# Mount static files for web UI
# Try multiple potential locations for static files
static_paths = [
    Path(__file__).parent / "static",  # src/apeg_core/web/static
    Path(__file__).parent.parent.parent.parent / "webui" / "static",  # webui/static
]

for static_path in static_paths:
    if static_path.exists():
        try:
            app.mount(
                "/static",
                StaticFiles(directory=str(static_path)),
                name="static",
            )
            logger.info("Static files mounted from %s", static_path)
            break
        except Exception as e:
            logger.warning("Failed to mount static files from %s: %s", static_path, e)


# Root route - redirect to dashboard
@app.get("/")
async def root() -> FileResponse:
    """Root endpoint - serve dashboard."""
    return await dashboard()
