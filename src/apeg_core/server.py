"""
APEG HTTP API Server

Provides REST API endpoints for APEG workflow orchestration.
Designed for deployment on Raspberry Pi and small Linux servers.

Usage:
    python -m apeg_core.server

Environment Variables:
    APEG_TEST_MODE: Enable test mode (default: true)
    APEG_DEBUG: Enable debug logging (default: false)
    APEG_HOST: Server bind address (default: 0.0.0.0)
    APEG_PORT: Server port (default: 8000)
    OPENAI_API_KEY: OpenAI API key (required for production)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Check for FastAPI dependencies
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError as e:
    raise ImportError(
        "Server dependencies not installed. "
        "Run: pip install fastapi uvicorn pydantic\n"
        f"Original error: {e}"
    )

from apeg_core import APEGOrchestrator

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed, using os.environ only")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("APEG_DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
TEST_MODE = os.getenv("APEG_TEST_MODE", "true").lower() == "true"
DEBUG = os.getenv("APEG_DEBUG", "false").lower() == "true"
HOST = os.getenv("APEG_HOST", "0.0.0.0")
PORT = int(os.getenv("APEG_PORT", "8000"))
ALLOWED_ORIGINS = os.getenv("APEG_CORS_ORIGINS", "*").split(",")

# Initialize FastAPI app
app = FastAPI(
    title="APEG API",
    version="1.0.0",
    description="Agentic Prompt Engineering Graph - Autonomous Workflow Orchestration",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


# Request/Response Models
class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""
    goal: str = Field(..., description="Workflow goal or objective", min_length=1)
    workflow_path: str = Field(
        default="WorkflowGraph.json",
        description="Path to workflow graph file"
    )
    initial_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Initial workflow state"
    )


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""
    status: str = Field(..., description="Execution status: success or error")
    final_output: Optional[str] = Field(None, description="Final workflow output")
    state: Optional[Dict[str, Any]] = Field(None, description="Final workflow state")
    history: Optional[list] = Field(None, description="Execution history")
    score: Optional[float] = Field(None, description="Quality score (0-1)")
    error: Optional[str] = Field(None, description="Error message if status=error")


# API Endpoints
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "APEG API",
        "version": "1.0.0",
        "test_mode": str(TEST_MODE),
        "endpoints": {
            "health": "GET /health",
            "run": "POST /run",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.

    Returns service status and configuration info.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "test_mode": TEST_MODE,
        "debug": DEBUG,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }


@app.post("/run", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """
    Execute APEG workflow with given goal.

    Args:
        request: Workflow execution request with goal and optional parameters

    Returns:
        Workflow execution results including output, state, and score

    Raises:
        HTTPException: 404 if workflow file not found, 500 for execution errors
    """
    try:
        logger.info(f"Executing workflow: goal='{request.goal}', workflow={request.workflow_path}")

        # Validate workflow file exists
        workflow_path = Path(request.workflow_path)
        if not workflow_path.exists():
            logger.error(f"Workflow file not found: {request.workflow_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Workflow file not found: {request.workflow_path}"
            )

        # Initialize orchestrator
        orchestrator = APEGOrchestrator(
            config_path="SessionConfig.json",
            workflow_graph_path=str(workflow_path)
        )

        # Execute workflow via orchestrator API
        # Attach goal and optional initial_state into orchestrator state
        orchestrator.state.setdefault("context", {})
        orchestrator.state["context"]["goal"] = request.goal
        if request.initial_state:
            orchestrator.state["context"].update(request.initial_state)

        orchestrator.execute_graph()

        # Extract results from orchestrator
        state = orchestrator.get_state()
        history = orchestrator.get_history()
        final_output = state.get("output")
        score = state.get("last_score", 0.0)

        logger.info(f"Workflow complete: score={score}, output_length={len(str(final_output))}")

        return WorkflowResponse(
            status="success",
            final_output=final_output,
            state=state,
            history=history,
            score=score,
            error=None
        )

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return WorkflowResponse(
            status="error",
            final_output=None,
            state=None,
            history=None,
            score=None,
            error=str(e)
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": str(exc),
            "detail": "Internal server error"
        }
    )


def main():
    """
    Start the APEG API server.

    Configuration via environment variables:
        APEG_HOST: Bind address (default: 0.0.0.0)
        APEG_PORT: Port number (default: 8000)
        APEG_TEST_MODE: Enable test mode (default: true)
        APEG_DEBUG: Enable debug logging (default: false)
    """
    logger.info("=" * 60)
    logger.info("Starting APEG API Server")
    logger.info("=" * 60)
    logger.info(f"  Host: {HOST}")
    logger.info(f"  Port: {PORT}")
    logger.info(f"  Test Mode: {TEST_MODE}")
    logger.info(f"  Debug: {DEBUG}")
    logger.info(f"  API Docs: http://{HOST}:{PORT}/docs")
    logger.info(f"  Health Check: http://{HOST}:{PORT}/health")
    logger.info("=" * 60)

    # Start server
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="debug" if DEBUG else "info",
        access_log=True
    )


if __name__ == "__main__":
    main()
