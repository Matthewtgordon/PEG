"""
APEG HTTP API Server with WebSocket Support

Provides REST API and WebSocket endpoints for APEG workflow orchestration.
Designed for deployment on Raspberry Pi and small Linux servers.

Features:
    - REST API for workflow execution
    - WebSocket for real-time status updates
    - Static file serving for Web UI
    - CORS support for cross-origin requests

Usage:
    python -m apeg_core.server

Environment Variables:
    APEG_TEST_MODE: Enable test mode (default: true)
    APEG_DEBUG: Enable debug logging (default: false)
    APEG_HOST: Server bind address (default: 0.0.0.0)
    APEG_PORT: Server port (default: 8000)
    OPENAI_API_KEY: OpenAI API key (required for production)
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Check for FastAPI dependencies
try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
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
            workflow_path=str(workflow_path),
            test_mode=TEST_MODE
        )

        # Execute workflow
        result = orchestrator.run(
            goal=request.goal,
            initial_state=request.initial_state or {}
        )

        # Extract results
        final_output = result.get("final_output", "")
        state = result.get("state", {})
        history = result.get("history", [])
        score = result.get("score", 0.0)

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


# ============================================================================
# WebSocket Support for Real-time Updates
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections for real-time UI updates.

    Allows server to broadcast system events to all connected clients.
    Thread-safe for concurrent connection handling.
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._server_start_time = datetime.now()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected, total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove closed WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected, total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Send message to all connected clients.

        Args:
            message: Dictionary to send as JSON

        Handles disconnected clients gracefully.
        """
        disconnected = []
        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

    def get_uptime_seconds(self) -> int:
        """Get server uptime in seconds."""
        return int((datetime.now() - self._server_start_time).total_seconds())


# Global connection manager
manager = ConnectionManager()


async def get_system_status() -> Dict[str, Any]:
    """
    Get current system status for UI.

    Returns:
        Dictionary with system health, agent statuses, metrics
    """
    try:
        from apeg_core.agents.shopify_agent import ShopifyAgent
        from apeg_core.agents.etsy_agent import EtsyAgent

        status = {
            "system_health": "healthy",
            "agents": {
                "shopify": {
                    "name": "ShopifyAgent",
                    "status": "available",
                    "test_mode": True,
                },
                "etsy": {
                    "name": "EtsyAgent",
                    "status": "available",
                    "test_mode": True,
                }
            },
            "active_workflows": 0,
            "total_workflows": 0,
            "uptime_seconds": manager.get_uptime_seconds(),
            "test_mode": TEST_MODE,
        }
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "system_health": "degraded",
            "error": str(e),
            "uptime_seconds": manager.get_uptime_seconds(),
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time updates.

    Clients connect to receive:
    - Agent status changes
    - Workflow execution updates
    - System health metrics
    - Error notifications

    Message format:
    {
        "type": "status_update" | "workflow_event" | "metric" | "error",
        "timestamp": "ISO8601",
        "data": {...}
    }
    """
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await manager.send_personal({
            "type": "connection",
            "timestamp": datetime.now().isoformat(),
            "data": {"status": "connected", "message": "WebSocket established"}
        }, websocket)

        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (for bidirectional communication)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal({
                    "type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "data": {"message": "Invalid JSON"}
                }, websocket)
                continue

            # Handle client commands
            if message.get("type") == "ping":
                await manager.send_personal({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif message.get("type") == "get_status":
                # Send current system status
                status = await get_system_status()
                await manager.send_personal({
                    "type": "status_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": status
                }, websocket)

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def broadcast_workflow_event(event: Dict[str, Any]) -> None:
    """
    Broadcast workflow event to all connected WebSocket clients.

    Call this from orchestrator when workflows execute.
    """
    message = {
        "type": "workflow_event",
        "timestamp": datetime.now().isoformat(),
        "data": event
    }
    await manager.broadcast(message)


# Background task for periodic status broadcasts
_periodic_task: Optional[asyncio.Task] = None


async def periodic_status_broadcast() -> None:
    """
    Periodically broadcast system status to all connected clients.

    Runs every 10 seconds to keep UI updated.
    """
    while True:
        try:
            await asyncio.sleep(10)

            if manager.active_connections:
                status = await get_system_status()
                await manager.broadcast({
                    "type": "status_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": status
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic broadcast: {e}")


@app.on_event("startup")
async def startup_event() -> None:
    """Server startup tasks."""
    global _periodic_task
    logger.info("APEG FastAPI server starting up...")

    # Mount static files for web UI if directory exists
    webui_path = Path(__file__).parent.parent.parent.parent / "webui" / "static"
    if webui_path.exists():
        app.mount("/static", StaticFiles(directory=str(webui_path)), name="static")
        logger.info(f"Mounted static files from {webui_path}")
    else:
        logger.warning(f"Web UI static directory not found: {webui_path}")

    # Start background task for periodic status broadcasts
    _periodic_task = asyncio.create_task(periodic_status_broadcast())
    logger.info("Started periodic status broadcast task")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Server shutdown tasks."""
    global _periodic_task
    if _periodic_task:
        _periodic_task.cancel()
        try:
            await _periodic_task
        except asyncio.CancelledError:
            pass
    logger.info("APEG server shutting down")


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
