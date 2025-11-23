"""
Handoff Coordinator for managing agent-to-agent transitions.

Provides coordination between APEG domain agents and SDK agents,
handling context preservation during handoffs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from agents import Agent as SDKAgent

from apeg_core.agents.base_agent import BaseAgent
from .adapters import APEGAgentAdapter, SDKAgentWrapper

logger = logging.getLogger(__name__)


class HandoffCoordinator:
    """
    Coordinates handoffs between APEG and SDK agents.

    Manages agent registration, context transfer during handoffs,
    and routing between different agent types.

    Usage:
        >>> coordinator = HandoffCoordinator()
        >>> coordinator.register_apeg_agent("shopify", shopify_agent)
        >>> coordinator.register_apeg_agent("etsy", etsy_agent)
        >>>
        >>> # Create triage agent that can hand off to domain agents
        >>> triage = coordinator.create_triage_agent(
        ...     name="E-commerce Triage",
        ...     instructions="Route to appropriate platform agent"
        ... )
    """

    def __init__(self):
        """Initialize handoff coordinator."""
        self._apeg_agents: Dict[str, BaseAgent] = {}
        self._sdk_agents: Dict[str, SDKAgent] = {}
        self._adapters: Dict[str, APEGAgentAdapter] = {}
        self._context: Dict[str, Any] = {}

        logger.info("HandoffCoordinator initialized")

    def register_apeg_agent(
        self,
        name: str,
        agent: BaseAgent,
        instructions: Optional[str] = None
    ) -> APEGAgentAdapter:
        """
        Register an APEG agent for use in handoffs.

        Args:
            name: Unique name for the agent
            agent: APEG BaseAgent instance
            instructions: Optional custom instructions

        Returns:
            APEGAgentAdapter wrapping the agent

        Example:
            >>> adapter = coordinator.register_apeg_agent(
            ...     "shopify",
            ...     ShopifyAgent(config={"test_mode": True}),
            ...     instructions="Handle Shopify operations"
            ... )
        """
        self._apeg_agents[name] = agent
        adapter = APEGAgentAdapter(agent, instructions=instructions)
        self._adapters[name] = adapter

        logger.info(f"Registered APEG agent: {name}")
        return adapter

    def register_sdk_agent(self, name: str, agent: SDKAgent) -> None:
        """
        Register an SDK agent for use in handoffs.

        Args:
            name: Unique name for the agent
            agent: OpenAI SDK Agent instance

        Example:
            >>> coordinator.register_sdk_agent(
            ...     "assistant",
            ...     Agent(name="Assistant", instructions="...")
            ... )
        """
        self._sdk_agents[name] = agent
        logger.info(f"Registered SDK agent: {name}")

    def get_agent(self, name: str) -> Optional[Union[BaseAgent, SDKAgent]]:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            APEG agent, SDK agent, or None if not found
        """
        if name in self._apeg_agents:
            return self._apeg_agents[name]
        if name in self._sdk_agents:
            return self._sdk_agents[name]
        return None

    def get_adapter(self, name: str) -> Optional[APEGAgentAdapter]:
        """
        Get adapter for an APEG agent.

        Args:
            name: APEG agent name

        Returns:
            APEGAgentAdapter or None
        """
        return self._adapters.get(name)

    def create_triage_agent(
        self,
        name: str = "Triage",
        instructions: Optional[str] = None,
        include_agents: Optional[List[str]] = None
    ) -> SDKAgent:
        """
        Create a triage agent that can hand off to registered agents.

        Args:
            name: Name for the triage agent
            instructions: Custom instructions (auto-generated if None)
            include_agents: List of agent names to include (all if None)

        Returns:
            SDK Agent with handoffs configured

        Example:
            >>> triage = coordinator.create_triage_agent(
            ...     name="E-commerce Router",
            ...     instructions="Route to the appropriate platform agent"
            ... )
        """
        # Build list of handoff agents
        handoff_agents = []
        agent_descriptions = []

        # Include APEG agents
        for agent_name, adapter in self._adapters.items():
            if include_agents is None or agent_name in include_agents:
                sdk_agent = adapter.to_sdk_agent()
                handoff_agents.append(sdk_agent)
                agent_descriptions.append(f"- {agent_name}: {adapter.apeg_agent.__class__.__name__}")

        # Include SDK agents
        for agent_name, sdk_agent in self._sdk_agents.items():
            if include_agents is None or agent_name in include_agents:
                handoff_agents.append(sdk_agent)
                agent_descriptions.append(f"- {agent_name}: {sdk_agent.name}")

        # Generate instructions if not provided
        if instructions is None:
            instructions = f"""You are a triage agent that routes requests to the appropriate specialist.

Based on the user's request, hand off to the appropriate agent:
{chr(10).join(agent_descriptions)}

Analyze the request and hand off to the most appropriate specialist."""

        # Create triage agent
        triage_agent = SDKAgent(
            name=name,
            instructions=instructions,
            handoffs=handoff_agents,
        )

        self._sdk_agents[name] = triage_agent
        logger.info(f"Created triage agent '{name}' with {len(handoff_agents)} handoffs")

        return triage_agent

    def set_context(self, key: str, value: Any) -> None:
        """
        Set shared context for handoffs.

        Args:
            key: Context key
            value: Context value
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get shared context value.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all shared context."""
        self._context.clear()

    @property
    def registered_agents(self) -> Dict[str, str]:
        """
        Get dictionary of registered agents.

        Returns:
            Dict mapping agent name to type (apeg/sdk)
        """
        agents = {}
        for name in self._apeg_agents:
            agents[name] = "apeg"
        for name in self._sdk_agents:
            agents[name] = "sdk"
        return agents

    def describe(self) -> Dict[str, Any]:
        """
        Get description of coordinator state.

        Returns:
            Dict with agent counts and names
        """
        return {
            "apeg_agents": list(self._apeg_agents.keys()),
            "sdk_agents": list(self._sdk_agents.keys()),
            "total_agents": len(self._apeg_agents) + len(self._sdk_agents),
            "context_keys": list(self._context.keys()),
        }
