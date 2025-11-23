"""
APEG Orchestrator - Core workflow execution engine.

This module implements the APEGOrchestrator class which:
- Loads configuration from SessionConfig.json and WorkflowGraph.json
- Executes workflow graphs as defined in specs
- Integrates decision engine, scoring, and logging
- Manages agent roles and node transitions
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class APEGOrchestrator:
    """
    Executes workflows defined in WorkflowGraph.json.

    The orchestrator is the main entry point for APEG runtime. It:
    - Loads configurations from JSON files
    - Builds an internal graph representation
    - Executes nodes in order based on edges and conditions
    - Integrates with decision engine, scoring, and logging
    - Manages workflow state and history
    """

    def __init__(
        self,
        config_path: Path | str | Dict[str, Any],
        workflow_graph_path: Path | str | Dict[str, Any],
    ):
        """
        Initialize the orchestrator with configuration files or dictionaries.

        Args:
            config_path: Path to SessionConfig.json or config dictionary
            workflow_graph_path: Path to WorkflowGraph.json or workflow graph dictionary
        """
        logger.info("Initializing APEGOrchestrator...")

        # Handle config_path - can be a path or a dict
        if isinstance(config_path, dict):
            self.config_path = None
            self.config = config_path
            logger.debug("Using config dictionary directly")
        else:
            self.config_path = Path(config_path)
            self.config = self._load_json(self.config_path)
            logger.debug("Loaded config from %s", self.config_path)

        # Handle workflow_graph_path - can be a path or a dict
        if isinstance(workflow_graph_path, dict):
            self.workflow_graph_path = None
            self.workflow_graph = workflow_graph_path
            logger.debug("Using workflow graph dictionary directly")
        else:
            self.workflow_graph_path = Path(workflow_graph_path)
            self.workflow_graph = self._load_json(self.workflow_graph_path)
            logger.debug("Loaded workflow graph from %s", self.workflow_graph_path)

        # Initialize state
        self.state = {
            "current_node": self._get_entry_point(),
            "history": [],
            "last_score": 0.0,
            "output": None,
            "loop_iterations": 0,
        }

        # Circuit breaker tracking
        self.fail_counts: Dict[str, int] = {}
        self.circuit_open: Dict[str, bool] = {}

        logger.info("Orchestrator initialized. Starting at node: '%s'", self.state["current_node"])
        logger.info("Agent roles: %s", list(self.workflow_graph.get("agent_roles", {}).keys()))

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file."""
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Config file not found: %s", path)
            raise
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in %s: %s", path, e)
            raise

    def _get_entry_point(self) -> str:
        """Get the entry point node from the workflow graph."""
        # Look for explicit entry_point
        if "entry_point" in self.workflow_graph:
            return self.workflow_graph["entry_point"]

        # Look for node with type "start"
        for node in self.workflow_graph.get("nodes", []):
            if node.get("type") == "start":
                return node["id"]

        # Default to "intake" if not specified
        return "intake"

    def get_node_details(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Find the full details for a node by its ID.

        Args:
            node_id: The node ID to look up

        Returns:
            Node dictionary or None if not found
        """
        for node in self.workflow_graph.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def get_next_node(self, current_node_id: str, condition: str) -> Optional[str]:
        """
        Find the next node based on current node and condition.

        Args:
            current_node_id: Current node ID
            condition: Condition to match (e.g., "score_passed", "validation_failed")

        Returns:
            Next node ID or None if no path found
        """
        # First try to find a conditional edge
        for edge in self.workflow_graph.get("edges", []):
            if (
                edge.get("from") == current_node_id
                and edge.get("condition") == condition
            ):
                return edge.get("to")

        # If no conditional edge, try unconditional edge
        for edge in self.workflow_graph.get("edges", []):
            if edge.get("from") == current_node_id and "condition" not in edge:
                return edge.get("to")

        return None

    def _resolve_context_path(self, path: str) -> Any:
        """
        Resolve a context path like 'context.user_input' to its value.

        Args:
            path: Dot-separated path (e.g., 'context.user_input', 'state.output')

        Returns:
            Resolved value from state, or empty string if not found
        """
        parts = path.split(".")
        value = self.state

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                logger.warning(f"Context path '{path}' not found, using empty string")
                return ""

        return value

    def _resolve_result_path(self, result: Dict[str, Any], path: str) -> Any:
        """
        Resolve a result path like 'result.output' to its value.

        Args:
            result: Result dictionary from MCP call
            path: Dot-separated path (e.g., 'result.output', 'data.value')

        Returns:
            Resolved value from result, or None if not found
        """
        parts = path.split(".")
        value = result

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                logger.warning(f"Result path '{path}' not found")
                return None

        return value

    def _call_agent(self, agent_name: str, action: str, context: Dict) -> str:
        """
        Call an agent to perform an action.

        This method routes agent calls to the appropriate backend (OpenAI)
        with proper prompting based on agent role.

        Args:
            agent_name: Agent role from WorkflowGraph (PEG, ENGINEER, VALIDATOR, etc.)
            action: Action description from node
            context: Current state dictionary

        Returns:
            String response from agent

        Example:
            response = self._call_agent("ENGINEER", "Design macro chain", self.state)
        """
        from apeg_core.connectors import OpenAIClient

        # Initialize OpenAI client (will use test mode if needed)
        client = OpenAIClient()

        # Get agent role details
        agent_roles = self.workflow_graph.get("agent_roles", {})
        agent_info = agent_roles.get(agent_name, {})
        agent_description = agent_info.get("description", f"{agent_name} agent")

        # Build system prompt based on agent role
        system_prompts = {
            "PEG": "You are the PEG orchestrator. You manage workflow execution and fallback strategies.",
            "ENGINEER": "You are the ENGINEER agent. You design effective macro chains and inject constraints.",
            "VALIDATOR": "You are the VALIDATOR agent. You validate structure, schema conformance, and output format.",
            "CHALLENGER": "You are the CHALLENGER agent. You stress-test logic and trigger fallback on flaws.",
            "LOGGER": "You are the LOGGER agent. You audit file changes, mutations, and scoring logs.",
            "SCORER": "You are the SCORER agent. You evaluate outputs using the PromptScoreModel.",
            "TESTER": "You are the TESTER agent. You inject regression and edge tests.",
        }

        system_prompt = system_prompts.get(
            agent_name,
            f"You are a {agent_name} agent. {agent_description}"
        )

        # Build user prompt with context
        user_prompt = f"Action: {action}\n\nContext:\n"
        user_prompt += f"- Current output: {context.get('output', 'None')}\n"
        user_prompt += f"- Last score: {context.get('last_score', 0.0)}\n"
        user_prompt += f"- History entries: {len(context.get('history', []))}\n"

        # Call OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = client.chat_completion(messages=messages, model="gpt-4")
        logger.info("  ✓ Agent %s responded: %s", agent_name, response["content"][:100] + "...")

        return response["content"]

    def _execute_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single workflow node.

        This is a placeholder implementation that will be enhanced
        in later phases with:
        - Decision engine integration (Phase 3)
        - Agent calling (Phase 5)
        - Scoring integration (Phase 6)

        Args:
            node: Node dictionary from WorkflowGraph

        Returns:
            Dictionary with action_result and optional chosen_macro
        """
        node_id = node["id"]
        node_type = node.get("type", "process")
        agent = node.get("agent", "PEG")
        action = node.get("action", "")

        logger.info("Executing node: %s (type=%s, agent=%s)", node_id, node_type, agent)

        action_result = "success"
        chosen_macro = None

        # TODO[APEG-PH-3]: Integrate scoring system in Phase 6

        if node_id == "intake":
            logger.info("  Action: %s", action)
            self.state["output"] = "Intake complete"

        elif node_id == "prep":
            logger.info("  Action: %s", action)
            self.state["output"] = "Prep complete"

        elif node_id == "build":
            logger.info("  Action: %s", action)
            # INTEGRATED: Bandit selector (APEG-PH-2 RESOLVED)
            from apeg_core.decision import choose_macro

            available_macros = self.config.get("macros", ["macro_role_prompt", "macro_chain_of_thought", "macro_rewrite"])
            chosen_macro = choose_macro(
                macros=available_macros,
                history=self.state["history"],
                config=self.config,
            )
            logger.info("  ✓ Bandit selected macro: %s", chosen_macro)

            # INTEGRATED: Agent calling (APEG-PH-4 RESOLVED in Phase 4)
            agent_response = self._call_agent(agent, action, self.state)
            self.state["output"] = agent_response
            self.state["loop_iterations"] += 1

        elif node_id == "review":
            logger.info("  Action: %s", action)
            # INTEGRATED: Evaluator scoring (APEG-PH-3 RESOLVED)
            from apeg_core.scoring import Evaluator

            # Initialize evaluator with config
            evaluator = Evaluator(config=self.config)

            # Get the output to evaluate
            output_text = str(self.state.get("output", ""))

            # Build evaluation context
            eval_context = {
                "history": self.state.get("history", []),
                "loop_iterations": self.state.get("loop_iterations", 0),
            }

            # Check if LLM scoring is enabled (for hybrid scoring)
            use_hybrid = self.config.get("scoring", {}).get("use_hybrid", False)

            # Evaluate the output
            if use_hybrid:
                eval_result = evaluator.hybrid_score(output_text, eval_context)
            else:
                eval_result = evaluator.evaluate(output_text, eval_context)

            # Update state with evaluation results
            score = eval_result.score
            self.state["last_score"] = score
            self.state["evaluation_result"] = eval_result.to_dict()

            # Log evaluation results
            logger.info("  ✓ Evaluation score: %.3f (passed=%s)", score, eval_result.passed)
            logger.debug("  Metrics: %s", eval_result.metrics)
            logger.debug("  Feedback: %s", eval_result.feedback)

            # INTEGRATED: Bandit reward integration (when enabled)
            enable_bandit_rewards = self.config.get("selector", {}).get("enable_score_based_bandit", False)
            if enable_bandit_rewards and self.state.get("history"):
                # Find the last macro selection and record the reward
                last_entry = self.state["history"][-1] if self.state["history"] else None
                if last_entry and "macro" in last_entry:
                    from apeg_core.decision import record_bandit_reward
                    record_bandit_reward(
                        macro=last_entry["macro"],
                        reward=score,
                        config=self.config
                    )
                    logger.debug("  ✓ Recorded bandit reward: %s -> %.3f", last_entry["macro"], score)

            # Determine outcome based on threshold
            pass_threshold = evaluator.threshold

            if eval_result.passed:
                action_result = "score_passed"
                self.state["loop_iterations"] = 0
            else:
                action_result = "validation_failed"

        elif node_id == "loop_detector":
            logger.info("  Action: %s", action)
            # INTEGRATED: Loop guard (APEG-PH-2 RESOLVED)
            from apeg_core.decision import detect_loop

            loop_config = self.config.get("loop_guard", {})
            is_looping = detect_loop(
                history=self.state["history"],
                N=loop_config.get("N", 3),
                epsilon=loop_config.get("epsilon", 0.02),
            )
            action_result = "loop_detected" if is_looping else "loop_not_detected"
            if is_looping:
                logger.warning("  ⚠️  Loop detected by guard!")

        elif node_id == "export":
            logger.info("  Action: %s", action)
            logger.info("  Output: %s", self.state.get("output"))
            action_result = "__end__"

        elif node_type == "mcp_tool":
            # INTEGRATED: MCP tool node (Phase 8, Task 8)
            logger.info("  Executing MCP tool node: %s", node_id)
            mcp_config = node.get("mcp_config", {})

            try:
                from apeg_core.connectors.mcp_client import MCPClient

                # Initialize MCP client with server configuration
                client_config = {
                    "server_url": self.config.get("mcp", {}).get("server_url", "http://localhost:3000"),
                    "timeout": self.config.get("mcp", {}).get("timeout", 30),
                    "retry_count": self.config.get("mcp", {}).get("retry_count", 2)
                }
                mcp_client = MCPClient(client_config)

                # Extract parameters from context using input_mapping
                input_mapping = mcp_config.get("input_mapping", {})
                params = {}
                for param_name, context_path in input_mapping.items():
                    # Simple path resolution (e.g., "context.user_input")
                    value = self._resolve_context_path(context_path)
                    params[param_name] = value

                # Call MCP tool
                server = mcp_config.get("server", "default")
                tool_name = mcp_config.get("tool_name", "")

                result = mcp_client.call_tool(
                    server=server,
                    tool=tool_name,
                    params=params
                )

                # Check if call was successful
                if result["success"]:
                    # Map results back to context using output_mapping
                    output_mapping = mcp_config.get("output_mapping", {})
                    for state_key, result_path in output_mapping.items():
                        # Simple path resolution (e.g., "result.output")
                        value = self._resolve_result_path(result, result_path)
                        self.state[state_key] = value

                    logger.info("  ✓ MCP tool call successful: %s", tool_name)
                    action_result = "success"
                else:
                    # Store error in state
                    self.state["_mcp_error"] = result["error"]
                    logger.error("  ✗ MCP tool call failed: %s", result["error"])
                    action_result = "mcp_failed"

            except Exception as e:
                logger.error("  ✗ Unexpected error in MCP node: %s", e)
                self.state["_mcp_error"] = str(e)
                action_result = "error"

        else:
            logger.info("  Generic node execution: %s", action)

        return {
            "action_result": action_result,
            "chosen_macro": chosen_macro,
        }

    def execute_graph(self) -> None:
        """
        Main execution loop for the workflow graph.

        Executes nodes sequentially following edges and conditions
        until reaching an end node or error condition.
        """
        logger.info("Starting workflow execution...")

        max_iterations = 100  # Safety limit
        iteration = 0

        while (
            self.state["current_node"] is not None
            and self.state["current_node"] != "__end__"
            and iteration < max_iterations
        ):
            iteration += 1
            current_node_id = self.state["current_node"]

            # Get node details
            node = self.get_node_details(current_node_id)
            if not node:
                logger.error("Node '%s' not found in workflow graph. Halting.", current_node_id)
                break

            # Check circuit breaker
            if self.circuit_open.get(node["id"]):
                logger.warning("Circuit breaker open for %s; escalating to human.", node["id"])
                break

            # Execute node with retry logic
            try:
                result = self._execute_node(node)
                self.fail_counts[node["id"]] = 0

            except Exception as exc:
                logger.exception("Node %s failed: %s", node["id"], exc)
                self.fail_counts[node["id"]] = self.fail_counts.get(node["id"], 0) + 1

                # Check circuit breaker threshold
                circuit_threshold = self.config.get("retry", {}).get("circuit_threshold", 5)
                if self.fail_counts[node["id"]] >= circuit_threshold:
                    self.circuit_open[node["id"]] = True
                    logger.error("Circuit breaker triggered for %s", node["id"])

                result = {"action_result": "failure", "chosen_macro": None}

            # Extract result
            action_result = result["action_result"]
            chosen_macro = result.get("chosen_macro")

            # Record history
            history_entry = {
                "node": node["id"],
                "result": action_result,
                "score": self.state["last_score"],
                "timestamp": datetime.now().isoformat(),
            }
            if chosen_macro:
                history_entry["macro"] = chosen_macro

            self.state["history"].append(history_entry)

            # Determine next node
            next_node_id = self.get_next_node(node["id"], action_result)

            if not next_node_id:
                logger.warning(
                    "No further path from node '%s' with condition '%s'. Halting.",
                    node["id"],
                    action_result,
                )
                break

            logger.info("Transitioning: %s -> %s (condition: %s)", node["id"], next_node_id, action_result)
            self.state["current_node"] = next_node_id

        if iteration >= max_iterations:
            logger.error("Maximum iterations (%d) reached. Possible infinite loop.", max_iterations)

        logger.info("Workflow execution complete. Total nodes executed: %d", len(self.state["history"]))

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the execution history."""
        return self.state["history"]

    def get_state(self) -> Dict[str, Any]:
        """Get the current execution state."""
        return self.state.copy()
