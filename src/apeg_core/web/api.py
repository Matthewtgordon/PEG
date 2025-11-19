"""
APEG Web API - FastAPI application and endpoints.

Provides HTTP endpoints for:
- POST /api/run - Execute workflow with a goal
- GET /api/health - Health check
- GET / - Serve web UI (static files)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from apeg_core.orchestrator import APEGOrchestrator

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


# Create FastAPI app
app = FastAPI(
    title="APEG Orchestrator API",
    description="HTTP API for APEG Autonomous Prompt Engineering Graph",
    version="1.0.0",
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status and version information
    """
    from apeg_core import __version__

    return HealthResponse(status="ok", version=__version__)


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
        # TODO[APEG-PH-1]: Enhance orchestrator to accept goal parameter
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


# Mount static files for web UI
# This will serve the web UI at the root path
try:
    webui_path = Path(__file__).parent.parent.parent.parent / "webui" / "static"
    if webui_path.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(webui_path), html=True),
            name="static",
        )
        logger.info("Web UI mounted at / from %s", webui_path)
    else:
        logger.warning("Web UI directory not found at %s", webui_path)
except Exception as e:
    logger.warning("Failed to mount static files: %s", e)
