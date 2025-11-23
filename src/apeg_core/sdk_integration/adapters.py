"""
Adapters for bidirectional integration between APEG and OpenAI SDK.

Provides:
- APEGAgentAdapter: Wraps APEG BaseAgent as OpenAI SDK Agent
- SDKAgentWrapper: Wraps OpenAI SDK Agent for APEG orchestrator
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from agents import Agent as SDKAgent
from agents import Runner

from apeg_core.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class APEGAgentAdapter:
    """
    Wraps an APEG BaseAgent as an OpenAI SDK Agent.

    Converts APEG agent methods to SDK function tools and creates
    an SDK Agent that can participate in multi-agent workflows with
    handoffs, sessions, and tracing.

    Architecture:
        APEG Agent (Shopify/Etsy)
            |
        ToolBridge (extract methods as tools)
            |
        SDK Agent (with tools, instructions, handoffs)

    Example:
        >>> # Wrap Shopify agent
        >>> shopify = ShopifyAgent(config={"test_mode": True})
        >>> adapter = APEGAgentAdapter(shopify)
        >>>
        >>> # Get SDK agent
        >>> sdk_agent = adapter.to_sdk_agent()
        >>>
        >>> # Use in SDK workflows
        >>> result = Runner.run_sync(sdk_agent, "List all products")
        >>> print(result.final_output)
    """

    def __init__(
        self,
        apeg_agent: BaseAgent,
        instructions: Optional[str] = None,
        handoffs: Optional[List[SDKAgent]] = None,
        method_filter: Optional[Callable[[str], bool]] = None
    ):
        """
        Initialize adapter with APEG agent.

        Args:
            apeg_agent: APEG agent to wrap (e.g., ShopifyAgent, EtsyAgent)
            instructions: Custom instructions for SDK agent.
                         If None, generates from agent class docstring.
            handoffs: List of SDK agents this agent can hand off to
            method_filter: Function to filter which agent methods become tools.
                          Takes method name, returns True to include.
        """
        self.apeg_agent = apeg_agent
        self.agent_name = apeg_agent.__class__.__name__

        # Generate instructions from agent docstring if not provided
        if instructions is None:
            agent_doc = inspect.getdoc(apeg_agent.__class__)
            if agent_doc:
                # Use first paragraph of docstring
                first_para = agent_doc.split('\n\n')[0]
                instructions = f"You are the {self.agent_name}. {first_para}"
            else:
                instructions = f"You are a {self.agent_name} agent that handles domain-specific operations."

        self.instructions = instructions
        self.handoffs = handoffs or []
        self.method_filter = method_filter
        self._sdk_agent: Optional[SDKAgent] = None

        logger.info(f"APEGAgentAdapter initialized for {self.agent_name}")

    def to_sdk_agent(self) -> SDKAgent:
        """
        Convert APEG agent to OpenAI SDK Agent.

        Creates an SDK Agent with:
        - Name from APEG agent class
        - Instructions from docstring or provided
        - Tools from agent methods
        - Optional handoffs to other agents

        Returns:
            OpenAI SDK Agent ready for use with Runner

        Example:
            >>> sdk_agent = adapter.to_sdk_agent()
            >>> result = Runner.run_sync(
            ...     sdk_agent,
            ...     "Get the first 5 products from the store"
            ... )
        """
        # Import ToolBridge
        from .tool_bridge import ToolBridge

        # Create tools from APEG agent methods
        bridge = ToolBridge(self.apeg_agent)
        tools = bridge.create_tools(method_filter=self.method_filter)

        logger.info(f"Created SDK agent for {self.agent_name} with {len(tools)} tools")

        # Create SDK Agent
        self._sdk_agent = SDKAgent(
            name=self.agent_name,
            instructions=self.instructions,
            tools=tools,
            handoffs=self.handoffs,
        )

        return self._sdk_agent

    def create_with_handoffs(self, other_adapters: List["APEGAgentAdapter"]) -> SDKAgent:
        """
        Create SDK agent with handoffs to other APEG agents.

        Args:
            other_adapters: List of other APEGAgentAdapter instances to hand off to

        Returns:
            SDK Agent configured with handoffs

        Example:
            >>> shopify_adapter = APEGAgentAdapter(shopify_agent)
            >>> etsy_adapter = APEGAgentAdapter(etsy_agent)
            >>>
            >>> # Shopify can hand off to Etsy
            >>> shopify_sdk = shopify_adapter.create_with_handoffs([etsy_adapter])
        """
        # Convert other adapters to SDK agents
        handoff_agents = [adapter.to_sdk_agent() for adapter in other_adapters]

        # Create this agent with handoffs
        self.handoffs = handoff_agents
        return self.to_sdk_agent()

    @property
    def sdk_agent(self) -> Optional[SDKAgent]:
        """Get the cached SDK agent if created."""
        return self._sdk_agent

    def get_capabilities(self) -> List[str]:
        """Get list of capabilities from wrapped APEG agent."""
        return self.apeg_agent.describe_capabilities()


class SDKAgentWrapper(BaseAgent):
    """
    Wraps an OpenAI SDK Agent for use in APEG orchestrator.

    Makes SDK agents compatible with APEG's BaseAgent interface,
    allowing SDK agents to be registered in APEG's orchestrator
    and participate in APEG workflows.

    Implements BaseAgent interface:
    - execute(task, context) -> result
    - initialize() / cleanup() lifecycle methods

    Example:
        >>> # Create SDK agent
        >>> sdk_agent = Agent(
        ...     name="Assistant",
        ...     instructions="You are a helpful assistant."
        ... )
        >>>
        >>> # Wrap for APEG
        >>> apeg_agent = SDKAgentWrapper(sdk_agent)
        >>>
        >>> # Use in APEG orchestrator
        >>> orchestrator.register_agent("assistant", apeg_agent)
        >>> result = orchestrator.execute_workflow(...)
    """

    def __init__(self, sdk_agent: SDKAgent, config: Optional[Dict[str, Any]] = None):
        """
        Initialize wrapper with SDK agent.

        Args:
            sdk_agent: OpenAI SDK Agent instance
            config: Optional APEG-style configuration dict
        """
        # Extract test_mode from config if present
        test_mode = False
        if config:
            test_mode = config.get('test_mode', False)

        super().__init__(config or {}, test_mode=test_mode)

        self.sdk_agent = sdk_agent
        self._agent_name = sdk_agent.name

        logger.info(f"SDKAgentWrapper created for SDK agent: {self._agent_name}")

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return self._agent_name

    def describe_capabilities(self) -> List[str]:
        """
        Return list of capability identifiers.

        For SDK agents, this returns the tool names.
        """
        if hasattr(self.sdk_agent, 'tools') and self.sdk_agent.tools:
            return [
                getattr(tool, '__name__', str(tool))
                for tool in self.sdk_agent.tools
            ]
        return ["chat", "respond"]

    def execute(self, action: str, context: Dict) -> Dict:
        """
        Execute task using SDK agent (APEG-compatible interface).

        Args:
            action: Task description or prompt for the agent
            context: Context dictionary with additional information

        Returns:
            Dictionary containing:
                - output: Agent's final output
                - status: "completed" or "failed"
                - agent_name: Name of SDK agent that handled task
                - metadata: Additional execution metadata

        Raises:
            Exception: If SDK Runner.run() fails

        Example:
            >>> result = apeg_agent.execute(
            ...     action="summarize",
            ...     context={"prompt": "Summarize the latest orders"}
            ... )
            >>> print(result['output'])
        """
        # Build task string from action and context
        task = context.get('prompt', action)
        if action and action != task:
            task = f"{action}: {task}"

        try:
            # Run SDK agent
            logger.info(f"Executing SDK agent {self._agent_name} with task: {task[:100]}")

            # Use test mode if configured
            if self.test_mode:
                return {
                    "output": f"[TEST MODE] SDK agent {self._agent_name} would process: {task[:100]}",
                    "status": "completed",
                    "agent_name": self._agent_name,
                    "test_mode": True,
                    "metadata": {"context": context},
                }

            # Synchronous execution (APEG agents are typically sync)
            result = Runner.run_sync(self.sdk_agent, input=task)

            # Convert SDK result to APEG format
            return {
                "output": result.final_output,
                "status": "completed",
                "agent_name": self._agent_name,
                "metadata": {
                    "context": context,
                }
            }

        except Exception as e:
            logger.error(f"SDK agent {self._agent_name} execution failed: {e}")
            return {
                "output": None,
                "status": "failed",
                "agent_name": self._agent_name,
                "error": str(e),
                "metadata": {
                    "context": context,
                }
            }

    async def execute_async(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Async version of execute for async APEG workflows.

        Args:
            action: Task description
            context: Optional context

        Returns:
            Same format as execute()
        """
        context = context or {}
        task = context.get('prompt', action)
        if action and action != task:
            task = f"{action}: {task}"

        try:
            logger.info(f"Executing SDK agent {self._agent_name} async with task: {task[:100]}")

            if self.test_mode:
                return {
                    "output": f"[TEST MODE] SDK agent {self._agent_name} would process: {task[:100]}",
                    "status": "completed",
                    "agent_name": self._agent_name,
                    "test_mode": True,
                    "metadata": {"context": context},
                }

            # Async execution
            result = await Runner.run(self.sdk_agent, input=task)

            return {
                "output": result.final_output,
                "status": "completed",
                "agent_name": self._agent_name,
                "metadata": {
                    "context": context,
                }
            }

        except Exception as e:
            logger.error(f"Async SDK agent {self._agent_name} execution failed: {e}")
            return {
                "output": None,
                "status": "failed",
                "agent_name": self._agent_name,
                "error": str(e),
                "metadata": {
                    "context": context,
                }
            }
