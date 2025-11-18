"""
APEG Orchestrator - Core workflow execution engine.

This module implements the APEGOrchestrator class which:
- Loads configuration from SessionConfig.json and WorkflowGraph.json
- Executes workflow graphs as defined in specs
- Integrates decision engine, scoring, and logging
- Manages agent roles and node transitions
"""

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
        config_path: Path | str,
        workflow_graph_path: Path | str,
    ):
        """
        Initialize the orchestrator with configuration files.

        Args:
            config_path: Path to SessionConfig.json
            workflow_graph_path: Path to WorkflowGraph.json
        """
        logger.info("Initializing APEGOrchestrator...")

        self.config_path = Path(config_path)
        self.workflow_graph_path = Path(workflow_graph_path)

        # Load configurations
        self.config = self._load_json(self.config_path)
        self.workflow_graph = self._load_json(self.workflow_graph_path)

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
        # TODO[APEG-PH-4]: Integrate agent calls in Phase 5

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
            self.state["output"] = f"Built with {chosen_macro}"
            self.state["loop_iterations"] += 1

        elif node_id == "review":
            logger.info("  Action: %s", action)
            # Placeholder: Will integrate scoring in Phase 6
            score = 0.85  # Simulated score
            self.state["last_score"] = score
            pass_threshold = self.config.get("ci", {}).get("minimum_score", 0.8)

            if score >= pass_threshold:
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
