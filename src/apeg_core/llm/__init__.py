"""
APEG LLM Integration Package - Abstraction layer for LLM-based agent roles.

This package provides a clean abstraction over LLM providers (OpenAI, Agents SDK)
for use by the APEG orchestrator and scoring components. It separates the
orchestration logic from specific LLM implementation details.

Components:
- roles: Role definitions and configurations (ENGINEER, VALIDATOR, SCORER, etc.)
- agent_bridge: Main integration class for calling LLM roles
- openai_agents_adapter: OpenAI Agents SDK integration layer

Usage:
    from apeg_core.llm import AgentsBridge, LLMRole

    bridge = AgentsBridge(config)
    result = bridge.run_role(LLMRole.ENGINEER, "Design a workflow", context)

    # Or use the OpenAI Agents SDK adapter directly:
    from apeg_core.llm import OpenAIAgentsAdapter, AgentMode

    adapter = OpenAIAgentsAdapter(config, mode=AgentMode.SDK)
    result = adapter.run_agent(LLMRole.ENGINEER, "Design a workflow", context)
"""

from apeg_core.llm.roles import LLMRole, RoleConfig, ROLE_CONFIGS
from apeg_core.llm.agent_bridge import AgentsBridge, AgentsBridgeError
from apeg_core.llm.openai_agents_adapter import (
    OpenAIAgentsAdapter,
    AgentMode,
    AgentRunResult,
    APEGAgentConfig,
    get_adapter,
    reset_adapter,
)

__all__ = [
    # Role definitions
    "LLMRole",
    "RoleConfig",
    "ROLE_CONFIGS",
    # Agent bridge (facade)
    "AgentsBridge",
    "AgentsBridgeError",
    # OpenAI Agents SDK adapter
    "OpenAIAgentsAdapter",
    "AgentMode",
    "AgentRunResult",
    "APEGAgentConfig",
    "get_adapter",
    "reset_adapter",
]
