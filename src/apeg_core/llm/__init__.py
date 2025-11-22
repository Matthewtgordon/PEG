"""
APEG LLM Integration Package - Abstraction layer for LLM-based agent roles.

This package provides a clean abstraction over LLM providers (OpenAI, Agents SDK)
for use by the APEG orchestrator and scoring components. It separates the
orchestration logic from specific LLM implementation details.

Components:
- roles: Role definitions and configurations (ENGINEER, VALIDATOR, SCORER, etc.)
- agent_bridge: Main integration class for calling LLM roles

Usage:
    from apeg_core.llm import AgentsBridge, LLMRole

    bridge = AgentsBridge(config)
    result = bridge.run_role(LLMRole.ENGINEER, "Design a workflow", context)
"""

from apeg_core.llm.roles import LLMRole, RoleConfig, ROLE_CONFIGS
from apeg_core.llm.agent_bridge import AgentsBridge, AgentsBridgeError

__all__ = [
    "LLMRole",
    "RoleConfig",
    "ROLE_CONFIGS",
    "AgentsBridge",
    "AgentsBridgeError",
]
