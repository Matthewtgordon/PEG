"""
OpenAI Agents SDK Adapter - Integration layer for OpenAI Agents SDK with APEG.

This module provides an adapter that bridges APEG's LLM roles with the OpenAI Agents SDK,
enabling multi-agent workflows, handoffs, tools, guardrails, and session management.

Key Features:
- Maps APEG LLM roles to OpenAI Agent instances
- Supports handoffs between agents for complex workflows
- Integrates APEG domain agents (Shopify, Etsy) as function tools
- Provides guardrails for input/output validation
- Session management for conversation history
- Graceful fallback when SDK not available

Architecture:
    APEG Orchestrator
           |
           v
    AgentsBridge (facade)
           |
           v
    OpenAIAgentsAdapter (this module)
           |
           +---> OpenAI Agents SDK
           |         |
           |         +---> Agent (with instructions, tools, handoffs)
           |         +---> Runner (execution engine)
           |         +---> Session (conversation history)
           |
           +---> Fallback: OpenAI Chat Completions API

Usage:
    from apeg_core.llm.openai_agents_adapter import OpenAIAgentsAdapter

    adapter = OpenAIAgentsAdapter(config)
    result = adapter.run_agent("ENGINEER", "Design a workflow", context)

References:
- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
- ADR-001: OpenAI Agents as Primary LLM Runtime
- APEG Phase 8 Requirements
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from apeg_core.llm.roles import LLMRole, RoleConfig, get_role_config

logger = logging.getLogger(__name__)


# Check if OpenAI Agents SDK is available
_AGENTS_SDK_AVAILABLE = False
try:
    from agents import (
        Agent,
        Runner,
        function_tool,
        FunctionTool,
        handoff,
        Handoff,
        InputGuardrail,
        OutputGuardrail,
        GuardrailFunctionOutput,
        SQLiteSession,
        RunResult,
        RunConfig,
        ModelSettings,
    )
    _AGENTS_SDK_AVAILABLE = True
    logger.info("OpenAI Agents SDK is available")
except ImportError:
    logger.warning("OpenAI Agents SDK not installed. Install with: pip install openai-agents")


class AgentMode(str, Enum):
    """Execution mode for agents."""
    SDK = "sdk"           # Use OpenAI Agents SDK
    API = "api"           # Use OpenAI Chat Completions API
    TEST = "test"         # Use test mode (no real API calls)
    HYBRID = "hybrid"     # Try SDK first, fallback to API


@dataclass
class AgentRunResult:
    """Result from running an agent."""
    content: str
    role: str
    model: str
    success: bool
    test_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Additional SDK-specific fields
    final_output: Optional[Any] = None
    items: List[Any] = field(default_factory=list)
    tokens_used: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "role": self.role,
            "model": self.model,
            "success": self.success,
            "test_mode": self.test_mode,
            "metadata": self.metadata,
            "tokens_used": self.tokens_used,
        }


@dataclass
class APEGAgentConfig:
    """Configuration for an APEG agent in the SDK."""
    name: str
    instructions: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: List[Any] = field(default_factory=list)
    handoffs: List[Any] = field(default_factory=list)
    handoff_description: Optional[str] = None
    output_type: Optional[Type] = None


class OpenAIAgentsAdapter:
    """
    Adapter for integrating OpenAI Agents SDK with APEG.

    This adapter provides:
    - Agent creation from APEG role configurations
    - Multi-agent orchestration with handoffs
    - Tool integration for domain agents
    - Guardrail support for validation
    - Session management for conversation history

    Attributes:
        config: Configuration dictionary
        mode: Execution mode (SDK, API, TEST, HYBRID)
        session_dir: Directory for session storage
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        mode: Optional[AgentMode] = None,
    ):
        """
        Initialize the adapter.

        Args:
            config: Configuration dictionary with:
                - mode: Execution mode (sdk, api, test, hybrid)
                - session_dir: Directory for session databases
                - default_model: Default model to use
                - openai_api_key: API key (or use OPENAI_API_KEY env)
            mode: Override mode from config
        """
        self.config = config or {}
        self._agents: Dict[str, Any] = {}  # Cached Agent instances
        self._sessions: Dict[str, Any] = {}  # Session cache

        # Determine mode
        if mode:
            self.mode = mode
        else:
            mode_str = self.config.get("mode", "hybrid").lower()
            self.mode = AgentMode(mode_str) if mode_str in [m.value for m in AgentMode] else AgentMode.HYBRID

        # Check test mode from environment
        if os.environ.get("APEG_TEST_MODE", "").lower() in ("true", "1", "yes"):
            self.mode = AgentMode.TEST

        # Session configuration
        self.session_dir = self.config.get("session_dir", ".apeg_sessions")

        # SDK availability check
        if self.mode == AgentMode.SDK and not _AGENTS_SDK_AVAILABLE:
            logger.warning("SDK mode requested but SDK not available, falling back to HYBRID")
            self.mode = AgentMode.HYBRID

        logger.info(f"OpenAIAgentsAdapter initialized (mode={self.mode.value})")

    def is_sdk_available(self) -> bool:
        """Check if OpenAI Agents SDK is available."""
        return _AGENTS_SDK_AVAILABLE

    def _create_agent_from_role(self, role: LLMRole) -> Optional[Any]:
        """
        Create an OpenAI Agent from an APEG role configuration.

        Args:
            role: APEG LLM role

        Returns:
            Agent instance or None if SDK not available
        """
        if not _AGENTS_SDK_AVAILABLE:
            return None

        role_config = get_role_config(role)

        # Create agent with role configuration
        agent = Agent(
            name=f"APEG-{role_config.name}",
            instructions=role_config.system_prompt,
            model=role_config.model,
            model_settings=ModelSettings(
                temperature=role_config.temperature,
                max_tokens=role_config.max_tokens,
            ),
            handoff_description=role_config.description,
        )

        return agent

    def get_or_create_agent(self, role: LLMRole | str) -> Optional[Any]:
        """
        Get or create an agent for a role.

        Args:
            role: APEG LLM role or role name

        Returns:
            Agent instance or None if SDK not available
        """
        if isinstance(role, str):
            role = LLMRole(role.upper())

        cache_key = role.value

        if cache_key not in self._agents:
            self._agents[cache_key] = self._create_agent_from_role(role)

        return self._agents[cache_key]

    def create_orchestrator_agent(
        self,
        name: str = "APEG-Orchestrator",
        specialist_roles: Optional[List[LLMRole]] = None,
    ) -> Optional[Any]:
        """
        Create an orchestrator agent with handoffs to specialist agents.

        This implements the triage pattern where a main agent decides
        which specialist to hand off to based on the task.

        Args:
            name: Orchestrator name
            specialist_roles: List of specialist roles for handoffs

        Returns:
            Orchestrator Agent with configured handoffs
        """
        if not _AGENTS_SDK_AVAILABLE:
            return None

        specialist_roles = specialist_roles or [
            LLMRole.ENGINEER,
            LLMRole.VALIDATOR,
            LLMRole.SCORER,
            LLMRole.CHALLENGER,
        ]

        # Create specialist agents
        specialists = [self.get_or_create_agent(role) for role in specialist_roles]
        specialists = [s for s in specialists if s is not None]

        # Create orchestrator with handoffs
        orchestrator = Agent(
            name=name,
            instructions="""You are the APEG orchestrator. Your role is to:
- Analyze incoming tasks and determine which specialist agent should handle them
- Hand off to the appropriate specialist based on the task requirements
- Coordinate multi-step workflows by routing between specialists

Available specialists:
- ENGINEER: For designing prompts, workflows, and macro chains
- VALIDATOR: For validating outputs against requirements
- SCORER: For quality evaluation and scoring
- CHALLENGER: For stress-testing and finding flaws

Analyze the task and hand off to the most appropriate specialist.""",
            handoffs=specialists,
        )

        return orchestrator

    async def run_agent_async(
        self,
        role: LLMRole | str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentRunResult:
        """
        Run an agent asynchronously.

        Args:
            role: APEG LLM role or role name
            prompt: User prompt/instruction
            context: Optional context dictionary
            session_id: Optional session ID for conversation history
            **kwargs: Additional parameters (max_turns, run_config, etc.)

        Returns:
            AgentRunResult with execution results
        """
        if isinstance(role, str):
            role = LLMRole(role.upper())

        role_config = get_role_config(role)

        # Test mode - return deterministic response
        if self.mode == AgentMode.TEST:
            return self._test_mode_response(role, role_config, prompt, context)

        # SDK mode
        if self.mode in (AgentMode.SDK, AgentMode.HYBRID) and _AGENTS_SDK_AVAILABLE:
            try:
                return await self._run_via_sdk(role, role_config, prompt, context, session_id, **kwargs)
            except Exception as e:
                logger.warning(f"SDK execution failed: {e}")
                if self.mode == AgentMode.SDK:
                    raise
                # Fall through to API mode for HYBRID

        # API mode (fallback)
        return await self._run_via_api(role, role_config, prompt, context, **kwargs)

    def run_agent(
        self,
        role: LLMRole | str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentRunResult:
        """
        Run an agent synchronously.

        Args:
            role: APEG LLM role or role name
            prompt: User prompt/instruction
            context: Optional context dictionary
            session_id: Optional session ID for conversation history
            **kwargs: Additional parameters

        Returns:
            AgentRunResult with execution results
        """
        if isinstance(role, str):
            role = LLMRole(role.upper())

        role_config = get_role_config(role)

        # Test mode
        if self.mode == AgentMode.TEST:
            return self._test_mode_response(role, role_config, prompt, context)

        # SDK mode with sync runner
        if self.mode in (AgentMode.SDK, AgentMode.HYBRID) and _AGENTS_SDK_AVAILABLE:
            try:
                return self._run_via_sdk_sync(role, role_config, prompt, context, session_id, **kwargs)
            except Exception as e:
                logger.warning(f"SDK sync execution failed: {e}")
                if self.mode == AgentMode.SDK:
                    raise

        # API mode (fallback) - run async in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._run_via_api(role, role_config, prompt, context, **kwargs)
        )

    async def _run_via_sdk(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
        session_id: Optional[str],
        **kwargs: Any,
    ) -> AgentRunResult:
        """Execute via OpenAI Agents SDK."""
        logger.info(f"Running agent {role.value} via SDK")

        # Get or create agent
        agent = self.get_or_create_agent(role)
        if agent is None:
            raise RuntimeError("Failed to create agent")

        # Build input with context
        input_text = prompt
        if context:
            input_text += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        # Get or create session
        session = None
        if session_id:
            session = self._get_or_create_session(session_id)

        # Run the agent
        max_turns = kwargs.get("max_turns", 10)

        result: RunResult = await Runner.run(
            agent,
            input=input_text,
            session=session,
            max_turns=max_turns,
        )

        # Extract output
        final_output = result.final_output if result.final_output else ""

        return AgentRunResult(
            content=str(final_output),
            role=role.value,
            model=role_config.model,
            success=True,
            test_mode=False,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "backend": "openai_agents_sdk",
                "session_id": session_id,
            },
            final_output=final_output,
            items=[],  # Could extract items from result if needed
        )

    def _run_via_sdk_sync(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
        session_id: Optional[str],
        **kwargs: Any,
    ) -> AgentRunResult:
        """Execute via OpenAI Agents SDK synchronously."""
        logger.info(f"Running agent {role.value} via SDK (sync)")

        # Get or create agent
        agent = self.get_or_create_agent(role)
        if agent is None:
            raise RuntimeError("Failed to create agent")

        # Build input with context
        input_text = prompt
        if context:
            input_text += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        # Get or create session
        session = None
        if session_id:
            session = self._get_or_create_session(session_id)

        # Run the agent synchronously
        max_turns = kwargs.get("max_turns", 10)

        result: RunResult = Runner.run_sync(
            agent,
            input=input_text,
            session=session,
            max_turns=max_turns,
        )

        # Extract output
        final_output = result.final_output if result.final_output else ""

        return AgentRunResult(
            content=str(final_output),
            role=role.value,
            model=role_config.model,
            success=True,
            test_mode=False,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "backend": "openai_agents_sdk_sync",
                "session_id": session_id,
            },
            final_output=final_output,
            items=[],
        )

    async def _run_via_api(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> AgentRunResult:
        """Execute via OpenAI Chat Completions API (fallback)."""
        logger.info(f"Running agent {role.value} via Chat API (fallback)")

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("OpenAI SDK not installed")

        api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        client = AsyncOpenAI(api_key=api_key)

        # Build messages
        system_prompt = role_config.system_prompt
        if context:
            system_prompt += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Make API call
        response = await client.chat.completions.create(
            model=kwargs.get("model", role_config.model),
            messages=messages,
            temperature=kwargs.get("temperature", role_config.temperature),
            max_tokens=kwargs.get("max_tokens", role_config.max_tokens),
        )

        content = response.choices[0].message.content or ""

        return AgentRunResult(
            content=content,
            role=role.value,
            model=role_config.model,
            success=True,
            test_mode=False,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "backend": "openai_chat_api",
            },
            tokens_used={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def _test_mode_response(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
    ) -> AgentRunResult:
        """Generate deterministic test mode response."""
        logger.info(f"Test mode: generating stub response for {role.value}")

        # Role-specific test responses
        if role == LLMRole.SCORER:
            content = json.dumps({
                "overall_score": 0.85,
                "metrics": {
                    "completeness": 0.9,
                    "format_valid": 0.8,
                    "quality": 0.85,
                },
                "feedback": "Test mode scoring - output appears valid",
            })
        elif role == LLMRole.VALIDATOR:
            content = json.dumps({
                "valid": True,
                "score": 0.85,
                "issues": [],
                "recommendations": ["Test mode validation"],
            })
        elif role == LLMRole.CHALLENGER:
            content = json.dumps({
                "critical_issues": [],
                "warnings": ["Test mode - no real adversarial testing"],
                "edge_cases": ["Test edge case"],
                "stress_test_results": {"coverage": "limited"},
            })
        elif role == LLMRole.TESTER:
            content = json.dumps({
                "test_cases": [
                    {"name": "test_basic", "type": "unit", "status": "generated"}
                ],
                "coverage": "limited",
                "recommendations": ["Add integration tests"],
            })
        elif role == LLMRole.ENGINEER:
            content = f"Test mode ENGINEER response: Designed workflow for prompt: {prompt[:50]}..."
        else:
            content = f"Test mode response for {role.value}: Processed prompt successfully"

        return AgentRunResult(
            content=content,
            role=role.value,
            model="test-mode",
            success=True,
            test_mode=True,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "prompt_preview": prompt[:100],
            },
        )

    def _get_or_create_session(self, session_id: str) -> Optional[Any]:
        """Get or create a session for conversation history."""
        if not _AGENTS_SDK_AVAILABLE:
            return None

        if session_id not in self._sessions:
            # Ensure session directory exists
            os.makedirs(self.session_dir, exist_ok=True)
            db_path = os.path.join(self.session_dir, "sessions.db")
            self._sessions[session_id] = SQLiteSession(session_id, db_path)

        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear a session's conversation history."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def register_domain_agent_tools(
        self,
        agent: Any,
        domain_agents: List[Any],
    ) -> None:
        """
        Register domain agents (Shopify, Etsy) as tools for an agent.

        This allows LLM agents to call domain-specific operations
        through function tools.

        Args:
            agent: The Agent to add tools to
            domain_agents: List of APEG domain agents (BaseAgent subclasses)
        """
        if not _AGENTS_SDK_AVAILABLE:
            return

        for domain_agent in domain_agents:
            # Create a function tool for each capability
            for capability in domain_agent.describe_capabilities():
                tool = self._create_domain_tool(domain_agent, capability)
                if tool and hasattr(agent, 'tools'):
                    agent.tools.append(tool)

    def _create_domain_tool(self, domain_agent: Any, capability: str) -> Optional[Any]:
        """Create a function tool for a domain agent capability."""
        if not _AGENTS_SDK_AVAILABLE:
            return None

        # Create a wrapper function for the capability
        def make_tool_func(agent, cap):
            async def tool_func(context: Dict[str, Any] = {}) -> str:
                """Execute domain agent capability."""
                result = agent.execute(cap, context)
                return json.dumps(result, default=str)

            tool_func.__name__ = f"{agent.name}_{cap}"
            tool_func.__doc__ = f"Execute {cap} on {agent.name}"
            return tool_func

        func = make_tool_func(domain_agent, capability)
        return function_tool(func)

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of adapter configuration."""
        return {
            "mode": self.mode.value,
            "sdk_available": _AGENTS_SDK_AVAILABLE,
            "session_dir": self.session_dir,
            "cached_agents": list(self._agents.keys()),
            "active_sessions": list(self._sessions.keys()),
        }


# Convenience functions for module-level access

_global_adapter: Optional[OpenAIAgentsAdapter] = None


def get_adapter(config: Optional[Dict[str, Any]] = None) -> OpenAIAgentsAdapter:
    """Get or create the global adapter instance."""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = OpenAIAgentsAdapter(config)
    return _global_adapter


def reset_adapter() -> None:
    """Reset the global adapter (for testing)."""
    global _global_adapter
    _global_adapter = None


__all__ = [
    "OpenAIAgentsAdapter",
    "AgentMode",
    "AgentRunResult",
    "APEGAgentConfig",
    "get_adapter",
    "reset_adapter",
]
