#
# This script is the core "brain" of the PEG agent. It acts as a graph
# execution engine, bringing the process defined in WorkflowGraph.json to life.
# It orchestrates the agent's actions, from intake to final export, and
# integrates all the learning and safety modules.
#
import json
import logging
from pathlib import Path
import time
from datetime import datetime
from typing import Any, Dict

# Import the learning and safety modules
from bandit_selector import choose_macro
from loop_guard import detect_loop
# TODO: Refactor run_scoring.py to be importable, then uncomment the line below
# from run_scoring import calculate_final_score

class Orchestrator:
    """
    Executes the workflow defined in WorkflowGraph.json.
    """
    def __init__(self, config_path: Path, workflow_graph_path: Path):
        """Initializes the orchestrator with all necessary configuration files."""
        logging.basicConfig(level=logging.INFO)
        logging.info("Initializing Orchestrator...")
        with config_path.open(encoding='utf-8') as f:
            self.config = json.load(f)
        with workflow_graph_path.open(encoding='utf-8') as f:
            self.workflow_graph = json.load(f)
        
        # The state holds all the dynamic information for a single run
        self.state = {
            "current_node": self.workflow_graph.get("entry_point", "intake"),
            "history": [],
            "last_score": 0.0,
            "output": None,
            "loop_iterations": 0
        }
        self.fail_counts: Dict[str, int] = {}
        self.circuit_open: Dict[str, bool] = {}
        logging.info("Orchestrator initialized. Starting at node: '%s'", self.state['current_node'])

    def _get_simulated_score(self, output):
        """
        Placeholder for the real scoring function.
        Once run_scoring.py is refactored, this will be replaced.
        """
        print("NOTE: Using simulated scoring.")
        # In a real run, this would call: return calculate_final_score(output)
        import random
        return random.uniform(0.7, 1.0)

    def get_node_details(self, node_id: str):
        """Finds the full details for a node by its ID in the graph."""
        for node in self.workflow_graph.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def get_next_node(self, current_node_id: str, condition: str):
        """Finds the next node in the graph based on the current node and a condition."""
        for edge in self.workflow_graph.get("edges", []):
            if edge.get("from") == current_node_id and edge.get("condition") == condition:
                return edge.get("to")
        # Find an unconditional edge if no conditional one matches
        for edge in self.workflow_graph.get("edges", []):
            if edge.get("from") == current_node_id and "condition" not in edge:
                return edge.get("to")
        return None # No path forward

    def _execute_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        action_result = "success"
        chosen_macro_for_history = None

        if node['id'] == 'build':
            available_macros = self.config.get('macros', [])
            chosen_macro = choose_macro(
                available_macros,
                self.state['history'],
                self.config,
            )
            chosen_macro_for_history = chosen_macro
            logging.info("Chosen Macro: '%s'", chosen_macro)
            self.state['output'] = f"Output from {chosen_macro}"
            self.state['loop_iterations'] += 1

        elif node['id'] == 'review':
            score = self._get_simulated_score(self.state['output'])
            self.state['last_score'] = score
            logging.info("Scoring complete. Score: %.2f", score)

            pass_threshold = self.config.get('ci', {}).get('minimum_score', 0.8)
            if score >= pass_threshold:
                action_result = "score_passed"
                self.state['loop_iterations'] = 0
            else:
                action_result = "validation_failed"

        elif node['id'] == 'loop_detector':
            is_looping = detect_loop(
                self.state['history'],
                N=self.config.get('loop_guard', {}).get('N', 3),
                epsilon=self.config.get('loop_guard', {}).get('epsilon', 0.02),
            )
            action_result = "loop_detected" if is_looping else "loop_not_detected"
            logging.info("Loop detection result: %s", action_result)

        elif node['id'] == 'export':
            logging.info("✅ Workflow complete. Exporting results.")
            action_result = "__end__"

        return {
            'action_result': action_result,
            'chosen_macro': chosen_macro_for_history,
        }

    def execute_graph(self):
        """Runs the main loop executing the workflow graph."""
        while self.state["current_node"] is not None and self.state["current_node"] != "__end__":
            node = self.get_node_details(self.state["current_node"])
            if not node:
                logging.error("Node '%s' not found in workflow graph. Halting.", self.state['current_node'])
                break

            if self.circuit_open.get(node['id']):
                logging.warning("Circuit breaker open for %s; escalating to human.", node['id'])
                break

            retries = 0
            max_retries = self.config.get('retry', {}).get('max_attempts', 3)
            delay = 1.0
            result = None
            while retries < max_retries:
                try:
                    result = self._execute_node(node)
                    self.fail_counts[node['id']] = 0
                    break
                except Exception as exc:  # pragma: no cover - defensive
                    retries += 1
                    self.fail_counts[node['id']] = self.fail_counts.get(node['id'], 0) + 1
                    logging.error("Node %s failed: %s", node['id'], exc)
                    time.sleep(delay)
                    delay *= 2

            if result is None:
                if self.fail_counts.get(node['id'], 0) >= self.config.get('retry', {}).get('circuit_threshold', 5):
                    self.circuit_open[node['id']] = True
                result = {'action_result': 'failure', 'chosen_macro': None}
                logging.info("Escalating node %s to human operator.", node['id'])

            action_result = result['action_result']
            chosen_macro_for_history = result['chosen_macro']

            next_node_id = self.get_next_node(node['id'], action_result)

            history_entry = {
                'node': node['id'],
                'result': action_result,
                'score': self.state['last_score'],
                'timestamp': datetime.now().isoformat(),
            }
            if chosen_macro_for_history:
                history_entry['macro'] = chosen_macro_for_history
            self.state['history'].append(history_entry)

            self.state["current_node"] = next_node_id

            if not self.state["current_node"]:
                logging.warning(
                    "No further path from node '%s' with condition '%s'. Halting.",
                    node['id'],
                    action_result,
                )


def main():
    """A simple main function to demonstrate the orchestrator."""
    config_file = Path("SessionConfig.json")
    graph_file = Path("WorkflowGraph.json")

    if not config_file.exists() or not graph_file.exists():
        print(f"❌ Error: Make sure SessionConfig.json and WorkflowGraph.json are present.")
        return

    agent_orchestrator = Orchestrator(config_file, graph_file)
    agent_orchestrator.execute_graph()

if __name__ == "__main__":
    main()
