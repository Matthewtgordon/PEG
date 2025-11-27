"""
APEG HTTP API Server with WebSocket Support

Provides REST API and WebSocket endpoints for APEG workflow orchestration.
Designed for deployment on Raspberry Pi and small Linux servers.

Features:
    - REST API for workflow execution
    - WebSocket for real-time status updates
    - Static file serving for Web UI
    - CORS support for cross-origin requests
    - JWT authentication and RBAC
    - Rate limiting (enterprise security)
    - MCP-compliant audit logging

Usage:
    python -m apeg_core.server

Environment Variables:
    APEG_TEST_MODE: Enable test mode (default: true)
    APEG_DEBUG: Enable debug logging (default: false)
    APEG_HOST: Server bind address (default: 0.0.0.0)
    APEG_PORT: Server port (default: 8000)
    APEG_RATE_LIMIT: Requests per minute (default: 60)
    JWT_SECRET: Secret key for JWT tokens
    OPENAI_API_KEY: OpenAI API key (required for production)
"""

import asyncio
import json
import os
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Check for FastAPI dependencies
try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
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

# Import security modules
from apeg_core.security.audit import get_audit_logger, AuditLogger
from apeg_core.security.auth import get_current_user, require_auth, require_role, TokenPayload
from apeg_core.security.input_validation import validate_workflow_goal, sanitize_input
from apeg_core.security.key_management import get_key_manager

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
RATE_LIMIT = int(os.getenv("APEG_RATE_LIMIT", "60"))  # Requests per minute

# Initialize audit logger
audit_logger = get_audit_logger(test_mode=TEST_MODE)


# Rate limiting implementation
class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    Attributes:
        requests_per_minute: Maximum requests allowed per minute
        window_size: Window size in seconds (60)
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for client.

        Args:
            client_id: Client identifier (IP or user ID)

        Returns:
            True if request is allowed
        """
        now = time.time()
        window_start = now - self.window_size

        # Clean old requests
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        # Check limit
        if len(self._requests[client_id]) >= self.requests_per_minute:
            return False

        # Record request
        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        window_start = now - self.window_size
        recent = [t for t in self._requests[client_id] if t > window_start]
        return max(0, self.requests_per_minute - len(recent))


# Global rate limiter
rate_limiter = RateLimiter(RATE_LIMIT)

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


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for all HTTP requests.

    Returns 429 Too Many Requests if limit exceeded.
    """
    # Get client identifier (IP address)
    client_ip = request.client.host if request.client else "unknown"

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Check rate limit
    if not rate_limiter.is_allowed(client_ip):
        audit_logger.log_security_incident(
            incident_type="rate_limit_exceeded",
            severity="medium",
            description=f"Rate limit exceeded for {client_ip}",
            source_ip=client_ip,
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "retry_after": 60,
            },
            headers={"Retry-After": "60"},
        )

    response = await call_next(request)

    # Add rate limit headers
    remaining = rate_limiter.get_remaining(client_ip)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    return response


# Audit logging middleware
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """
    Audit logging middleware for all HTTP requests.
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    response = await call_next(request)

    # Log API access
    duration_ms = (time.time() - start_time) * 1000
    audit_logger.log_api_access(
        endpoint=str(request.url.path),
        method=request.method,
        user_id=None,  # Could be extracted from JWT if available
        status_code=response.status_code,
        duration_ms=duration_ms,
        request_id=response.headers.get("X-Request-ID"),
    )

    return response


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


# ============================================================================
# MCP (Model Context Protocol) Compliance Endpoints
# ============================================================================

@app.get("/mcp/serverInfo")
async def mcp_server_info() -> Dict[str, Any]:
    """
    MCP-compliant server information endpoint.

    Provides tool discovery and capability reporting for MCP clients.
    See: https://github.com/slowmist/mcp-security-checklist

    Returns:
        Server metadata, available tools, and capabilities
    """
    return {
        "name": "PEG-MCP",
        "version": "1.0.0",
        "description": "Autonomous Prompt Engineering Graph with MCP compliance",
        "tools": [
            {
                "name": "shopify_agent",
                "description": "E-commerce operations for Shopify stores",
                "capabilities": [
                    "list_products", "get_product", "create_product", "update_product",
                    "list_inventory", "update_inventory",
                    "list_orders", "get_order", "create_order", "fulfill_order",
                ],
            },
            {
                "name": "etsy_agent",
                "description": "E-commerce operations for Etsy marketplace",
                "capabilities": [
                    "list_listings", "create_listing", "update_listing",
                    "update_inventory", "list_orders", "ship_order",
                    "get_shop_analytics", "get_seo_suggestions",
                ],
            },
            {
                "name": "workflow_executor",
                "description": "Execute APEG workflow graphs",
                "capabilities": ["run_workflow", "get_status"],
            },
            {
                "name": "scoring_engine",
                "description": "Quality scoring for outputs",
                "capabilities": ["evaluate_output", "get_metrics"],
            },
        ],
        "security": {
            "authentication": ["bearer_token", "jwt"],
            "rate_limiting": True,
            "audit_logging": True,
            "encryption": True,
        },
        "capabilities": [
            "authentication",
            "authorization",
            "audit_trail",
            "rate_limiting",
            "input_validation",
            "encrypted_key_storage",
        ],
        "compliance": {
            "mcp_version": "1.0",
            "gdpr_ready": True,
            "audit_retention_days": 90,
        },
    }


@app.get("/mcp/tools")
async def mcp_list_tools() -> Dict[str, Any]:
    """
    List all available MCP tools with their schemas.
    """
    return {
        "tools": [
            {
                "name": "run_workflow",
                "description": "Execute an APEG workflow with a goal",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string", "description": "Workflow objective"},
                        "workflow_path": {"type": "string", "default": "WorkflowGraph.json"},
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "shopify_operation",
                "description": "Execute a Shopify operation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["list_products", "get_product", "update_inventory"]},
                        "params": {"type": "object"},
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "etsy_operation",
                "description": "Execute an Etsy operation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["list_listings", "create_listing", "list_orders"]},
                        "params": {"type": "object"},
                    },
                    "required": ["action"],
                },
            },
        ],
    }


# ============================================================================
# Secure Key Management Endpoints
# ============================================================================

class KeySetupRequest(BaseModel):
    """Request model for storing API keys."""
    service: str = Field(..., description="Service name (shopify, etsy, openai)")
    key_name: str = Field(..., description="Key identifier (api_key, access_token)")
    key_value: str = Field(..., description="The API key value", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


@app.post("/setup/keys")
async def setup_keys(
    request: KeySetupRequest,
    user: TokenPayload = Depends(require_role("manage_keys")),
) -> Dict[str, Any]:
    """
    Securely store API keys with encryption.

    Requires 'manage_keys' permission.
    Keys are encrypted using Fernet (AES-128-CBC) and stored locally.
    """
    key_manager = get_key_manager(test_mode=TEST_MODE)

    try:
        key_manager.store_key(
            service=request.service,
            key_name=request.key_name,
            key_value=request.key_value,
            metadata=request.metadata,
        )

        audit_logger.log_invocation(
            tool="key_management",
            user_id=user.sub,
            params={"service": request.service, "key_name": request.key_name},
            outcome="success",
            session_id=user.jti,
        )

        return {
            "status": "success",
            "message": f"Key '{request.key_name}' for '{request.service}' stored securely",
        }

    except Exception as e:
        audit_logger.log_security_incident(
            incident_type="key_storage_failure",
            severity="high",
            description=f"Failed to store key: {e}",
            user_id=user.sub,
        )
        raise HTTPException(status_code=500, detail=f"Failed to store key: {e}")


@app.get("/setup/keys")
async def list_keys(
    service: Optional[str] = None,
    user: TokenPayload = Depends(require_role("manage_keys")),
) -> Dict[str, Any]:
    """
    List stored API keys (without revealing values).

    Requires 'manage_keys' permission.
    """
    key_manager = get_key_manager(test_mode=TEST_MODE)
    return {
        "keys": key_manager.list_keys(service=service),
    }


@app.delete("/setup/keys/{service}/{key_name}")
async def delete_key(
    service: str,
    key_name: str,
    user: TokenPayload = Depends(require_role("manage_keys")),
) -> Dict[str, Any]:
    """
    Delete a stored API key.

    Requires 'manage_keys' permission.
    """
    key_manager = get_key_manager(test_mode=TEST_MODE)

    if key_manager.delete_key(service, key_name):
        audit_logger.log_invocation(
            tool="key_management",
            user_id=user.sub,
            params={"service": service, "key_name": key_name, "action": "delete"},
            outcome="success",
        )
        return {"status": "success", "message": f"Key '{key_name}' deleted"}

    raise HTTPException(status_code=404, detail=f"Key '{key_name}' not found")


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
