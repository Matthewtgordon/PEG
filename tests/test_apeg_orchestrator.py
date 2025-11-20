"""
Tests for the APEG Orchestrator.

These tests cover the core orchestrator functionality including:
- Initialization with config and workflow graph
- Node lookup and navigation
- Context path resolution
- Entry point detection
"""

import json
import pytest
from pathlib import Path
from apeg_core.orchestrator import APEGOrchestrator


@pytest.fixture
def minimal_config():
    """Minimal valid SessionConfig for testing."""
    return {
        "session_type": "PEG",
        "mode": "Full",
        "macros": ["macro1", "macro2"],
        "ci": {"minimum_score": 0.8},
        "loop_guard": {"enabled": True, "N": 3, "epsilon": 0.02},
        "retry": {"max_attempts": 3, "circuit_threshold": 5}
    }


@pytest.fixture
def minimal_workflow_graph():
    """Minimal valid WorkflowGraph for testing."""
    return {
        "version": "2.1.0",
        "entry_point": "start",
        "nodes": [
            {"id": "start", "type": "start", "agent": "PEG", "action": "Begin workflow"},
            {"id": "process", "type": "process", "agent": "ENGINEER", "action": "Process data"},
            {"id": "end", "type": "end", "agent": "PEG", "action": "Complete"}
        ],
        "edges": [
            {"from": "start", "to": "process"},
            {"from": "process", "to": "end", "condition": "success"}
        ],
        "agent_roles": {
            "PEG": {"description": "Orchestrator"},
            "ENGINEER": {"description": "Engineer agent"}
        }
    }


@pytest.fixture
def orchestrator_with_dicts(minimal_config, minimal_workflow_graph):
    """Orchestrator initialized with dictionaries."""
    return APEGOrchestrator(
        config_path=minimal_config,
        workflow_graph_path=minimal_workflow_graph
    )


class TestOrchestratorInitialization:
    """Tests for orchestrator initialization."""

    def test_init_with_dicts(self, minimal_config, minimal_workflow_graph):
        """Test initialization with config and workflow graph as dictionaries."""
        orch = APEGOrchestrator(
            config_path=minimal_config,
            workflow_graph_path=minimal_workflow_graph
        )

        assert orch.config == minimal_config
        assert orch.workflow_graph == minimal_workflow_graph
        assert orch.config_path is None
        assert orch.workflow_graph_path is None
        assert orch.state["current_node"] == "start"
        assert orch.state["history"] == []
        assert orch.state["last_score"] == 0.0

    def test_init_with_files(self, tmp_path, minimal_config, minimal_workflow_graph):
        """Test initialization with config and workflow graph as files."""
        config_file = tmp_path / "config.json"
        workflow_file = tmp_path / "workflow.json"

        config_file.write_text(json.dumps(minimal_config))
        workflow_file.write_text(json.dumps(minimal_workflow_graph))

        orch = APEGOrchestrator(
            config_path=config_file,
            workflow_graph_path=workflow_file
        )

        assert orch.config == minimal_config
        assert orch.workflow_graph == minimal_workflow_graph
        assert orch.config_path == config_file
        assert orch.workflow_graph_path == workflow_file

    def test_init_missing_file_raises_error(self, tmp_path, minimal_workflow_graph):
        """Test that initialization with missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            APEGOrchestrator(
                config_path=tmp_path / "nonexistent.json",
                workflow_graph_path=minimal_workflow_graph
            )

    def test_init_invalid_json_raises_error(self, tmp_path, minimal_workflow_graph):
        """Test that initialization with invalid JSON raises JSONDecodeError."""
        bad_config = tmp_path / "bad_config.json"
        bad_config.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            APEGOrchestrator(
                config_path=bad_config,
                workflow_graph_path=minimal_workflow_graph
            )


class TestEntryPointDetection:
    """Tests for entry point detection."""

    def test_entry_point_explicit(self, minimal_config):
        """Test entry point detection with explicit entry_point field."""
        workflow = {
            "entry_point": "custom_start",
            "nodes": [{"id": "custom_start", "type": "process"}],
            "edges": []
        }
        orch = APEGOrchestrator(minimal_config, workflow)
        assert orch.state["current_node"] == "custom_start"

    def test_entry_point_from_start_type(self, minimal_config):
        """Test entry point detection from node with type='start'."""
        workflow = {
            "nodes": [
                {"id": "first", "type": "process"},
                {"id": "start_node", "type": "start"}
            ],
            "edges": []
        }
        orch = APEGOrchestrator(minimal_config, workflow)
        assert orch.state["current_node"] == "start_node"

    def test_entry_point_defaults_to_intake(self, minimal_config):
        """Test entry point defaults to 'intake' if not specified."""
        workflow = {
            "nodes": [{"id": "some_node", "type": "process"}],
            "edges": []
        }
        orch = APEGOrchestrator(minimal_config, workflow)
        assert orch.state["current_node"] == "intake"


class TestNodeLookup:
    """Tests for node lookup functionality."""

    def test_get_node_details_found(self, orchestrator_with_dicts):
        """Test getting details for an existing node."""
        node = orchestrator_with_dicts.get_node_details("start")
        assert node is not None
        assert node["id"] == "start"
        assert node["type"] == "start"
        assert node["agent"] == "PEG"

    def test_get_node_details_not_found(self, orchestrator_with_dicts):
        """Test getting details for non-existent node returns None."""
        node = orchestrator_with_dicts.get_node_details("nonexistent")
        assert node is None

    def test_get_node_details_multiple_nodes(self, orchestrator_with_dicts):
        """Test getting details for multiple nodes."""
        start_node = orchestrator_with_dicts.get_node_details("start")
        process_node = orchestrator_with_dicts.get_node_details("process")
        end_node = orchestrator_with_dicts.get_node_details("end")

        assert start_node["id"] == "start"
        assert process_node["id"] == "process"
        assert end_node["id"] == "end"


class TestNodeNavigation:
    """Tests for node navigation and edge traversal."""

    def test_get_next_node_unconditional(self, orchestrator_with_dicts):
        """Test getting next node with unconditional edge."""
        next_node = orchestrator_with_dicts.get_next_node("start", "any_condition")
        assert next_node == "process"

    def test_get_next_node_with_condition(self, orchestrator_with_dicts):
        """Test getting next node with conditional edge."""
        next_node = orchestrator_with_dicts.get_next_node("process", "success")
        assert next_node == "end"

    def test_get_next_node_wrong_condition(self, orchestrator_with_dicts):
        """Test that wrong condition doesn't match."""
        next_node = orchestrator_with_dicts.get_next_node("process", "wrong_condition")
        # Should fall back to unconditional edge if any, or None
        assert next_node is None  # No unconditional edge from process

    def test_get_next_node_no_edges(self, minimal_config):
        """Test getting next node when no outgoing edges exist."""
        workflow = {
            "nodes": [{"id": "isolated", "type": "process"}],
            "edges": []
        }
        orch = APEGOrchestrator(minimal_config, workflow)
        next_node = orch.get_next_node("isolated", "any_condition")
        assert next_node is None


class TestContextPathResolution:
    """Tests for context path resolution."""

    def test_resolve_simple_path(self, orchestrator_with_dicts):
        """Test resolving a simple context path."""
        orchestrator_with_dicts.state["output"] = "test_output"
        result = orchestrator_with_dicts._resolve_context_path("output")
        assert result == "test_output"

    def test_resolve_nested_path(self, orchestrator_with_dicts):
        """Test resolving a nested context path."""
        orchestrator_with_dicts.state["data"] = {"nested": {"value": 42}}
        result = orchestrator_with_dicts._resolve_context_path("data.nested.value")
        assert result == 42

    def test_resolve_path_not_found(self, orchestrator_with_dicts):
        """Test resolving a non-existent path returns empty string."""
        result = orchestrator_with_dicts._resolve_context_path("nonexistent.path")
        assert result == ""

    def test_resolve_partial_path(self, orchestrator_with_dicts):
        """Test resolving a partially valid path returns empty string."""
        orchestrator_with_dicts.state["data"] = {"key": "value"}
        result = orchestrator_with_dicts._resolve_context_path("data.nonexistent.path")
        assert result == ""


class TestResultPathResolution:
    """Tests for result path resolution."""

    def test_resolve_simple_result_path(self, orchestrator_with_dicts):
        """Test resolving a simple result path."""
        result = {"output": "test_result"}
        value = orchestrator_with_dicts._resolve_result_path(result, "output")
        assert value == "test_result"

    def test_resolve_nested_result_path(self, orchestrator_with_dicts):
        """Test resolving a nested result path."""
        result = {"data": {"nested": {"value": 123}}}
        value = orchestrator_with_dicts._resolve_result_path(result, "data.nested.value")
        assert value == 123

    def test_resolve_result_path_not_found(self, orchestrator_with_dicts):
        """Test resolving a non-existent result path returns None."""
        result = {"output": "test"}
        value = orchestrator_with_dicts._resolve_result_path(result, "nonexistent")
        assert value is None

    def test_resolve_result_path_partial(self, orchestrator_with_dicts):
        """Test resolving a partially valid result path returns None."""
        result = {"data": {"key": "value"}}
        value = orchestrator_with_dicts._resolve_result_path(result, "data.nonexistent.path")
        assert value is None


class TestStateManagement:
    """Tests for state management."""

    def test_get_state_returns_copy(self, orchestrator_with_dicts):
        """Test that get_state returns a copy of the state."""
        state1 = orchestrator_with_dicts.get_state()
        state2 = orchestrator_with_dicts.get_state()

        # Modify state1
        state1["output"] = "modified"

        # state2 should be unchanged
        assert state2.get("output") != "modified"
        # Original state should be unchanged
        assert orchestrator_with_dicts.state.get("output") != "modified"

    def test_get_history_empty(self, orchestrator_with_dicts):
        """Test getting empty history."""
        history = orchestrator_with_dicts.get_history()
        assert history == []

    def test_initial_state_values(self, orchestrator_with_dicts):
        """Test that initial state has expected values."""
        state = orchestrator_with_dicts.get_state()
        assert state["current_node"] == "start"
        assert state["history"] == []
        assert state["last_score"] == 0.0
        assert state["output"] is None
        assert state["loop_iterations"] == 0


class TestCircuitBreaker:
    """Tests for circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self, orchestrator_with_dicts):
        """Test that circuit breaker is initially closed for all nodes."""
        assert orchestrator_with_dicts.fail_counts == {}
        assert orchestrator_with_dicts.circuit_open == {}

    def test_fail_counts_tracking(self, orchestrator_with_dicts):
        """Test that fail counts can be tracked."""
        orchestrator_with_dicts.fail_counts["test_node"] = 3
        assert orchestrator_with_dicts.fail_counts["test_node"] == 3

    def test_circuit_open_tracking(self, orchestrator_with_dicts):
        """Test that circuit breaker state can be tracked."""
        orchestrator_with_dicts.circuit_open["test_node"] = True
        assert orchestrator_with_dicts.circuit_open["test_node"] is True
