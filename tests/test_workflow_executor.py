"""Tests for workflow graph validation and navigation utilities."""

import pytest

from apeg_core.workflow import (
    validate_workflow_graph,
    get_next_node,
    get_node_by_id,
    get_entry_point,
    get_outgoing_edges
)


@pytest.fixture
def valid_graph():
    """Sample valid workflow graph for testing."""
    return {
        "nodes": [
            {"id": "start", "type": "start", "action": "Initialize"},
            {"id": "process", "type": "process", "action": "Process data"},
            {"id": "end", "type": "end", "action": "Finish"}
        ],
        "edges": [
            {"from": "start", "to": "process"},
            {"from": "process", "to": "end", "condition": "success"},
            {"from": "process", "to": "start", "condition": "retry"}
        ]
    }


def test_validate_workflow_graph_valid(valid_graph):
    """Valid graph passes validation."""
    result = validate_workflow_graph(valid_graph)
    assert result is True


def test_validate_workflow_graph_missing_nodes():
    """Graph without nodes raises ValueError."""
    graph = {"edges": []}

    with pytest.raises(ValueError, match="must contain 'nodes'"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_missing_edges():
    """Graph without edges raises ValueError."""
    graph = {"nodes": [{"id": "test", "type": "start"}]}

    with pytest.raises(ValueError, match="must contain 'edges'"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_empty_nodes():
    """Graph with empty nodes list raises ValueError."""
    graph = {"nodes": [], "edges": []}

    with pytest.raises(ValueError, match="at least one node"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_missing_node_id():
    """Node without ID raises ValueError."""
    graph = {
        "nodes": [{"type": "start"}],
        "edges": []
    }

    with pytest.raises(ValueError, match="missing required 'id' field"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_missing_node_type():
    """Node without type raises ValueError."""
    graph = {
        "nodes": [{"id": "test"}],
        "edges": []
    }

    with pytest.raises(ValueError, match="missing required 'type' field"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_duplicate_node_ids():
    """Duplicate node IDs raise ValueError."""
    graph = {
        "nodes": [
            {"id": "duplicate", "type": "start"},
            {"id": "duplicate", "type": "end"}
        ],
        "edges": []
    }

    with pytest.raises(ValueError, match="Duplicate node ID"):
        validate_workflow_graph(graph)


def test_validate_workflow_graph_invalid_edge():
    """Edge references nonexistent node."""
    graph = {
        "nodes": [
            {"id": "start", "type": "start"}
        ],
        "edges": [
            {"from": "start", "to": "nonexistent"}
        ]
    }

    with pytest.raises(ValueError, match="does not exist in nodes list"):
        validate_workflow_graph(graph)


def test_get_next_node_found(valid_graph):
    """Returns correct next node ID with matching condition."""
    next_id = get_next_node(valid_graph, "process", "success")
    assert next_id == "end"


def test_get_next_node_retry(valid_graph):
    """Returns correct next node for retry condition."""
    next_id = get_next_node(valid_graph, "process", "retry")
    assert next_id == "start"


def test_get_next_node_unconditional(valid_graph):
    """Returns node for unconditional edge."""
    next_id = get_next_node(valid_graph, "start", "anything")
    assert next_id == "process"


def test_get_next_node_not_found(valid_graph):
    """Returns None for invalid condition."""
    next_id = get_next_node(valid_graph, "process", "invalid_condition")
    assert next_id is None


def test_get_next_node_default_fallback():
    """Uses default edge when no exact match."""
    graph = {
        "nodes": [
            {"id": "a", "type": "start"},
            {"id": "b", "type": "process"}
        ],
        "edges": [
            {"from": "a", "to": "b", "condition": "default"}
        ]
    }

    next_id = get_next_node(graph, "a", "any_condition")
    assert next_id == "b"


def test_get_node_by_id_found(valid_graph):
    """Retrieve node details by ID."""
    node = get_node_by_id(valid_graph, "process")

    assert node is not None
    assert node["id"] == "process"
    assert node["type"] == "process"
    assert node["action"] == "Process data"


def test_get_node_by_id_not_found(valid_graph):
    """Returns None when node not found."""
    node = get_node_by_id(valid_graph, "nonexistent")
    assert node is None


def test_get_entry_point_explicit():
    """Uses explicit entry_point field."""
    graph = {
        "entry_point": "custom_start",
        "nodes": [
            {"id": "custom_start", "type": "start"},
            {"id": "other", "type": "process"}
        ],
        "edges": []
    }

    entry = get_entry_point(graph)
    assert entry == "custom_start"


def test_get_entry_point_start_type(valid_graph):
    """Finds node with type='start'."""
    entry = get_entry_point(valid_graph)
    assert entry == "start"


def test_get_entry_point_first_node():
    """Uses first node when no start type."""
    graph = {
        "nodes": [
            {"id": "first", "type": "process"},
            {"id": "second", "type": "process"}
        ],
        "edges": []
    }

    entry = get_entry_point(graph)
    assert entry == "first"


def test_get_entry_point_default():
    """Returns 'intake' as default."""
    graph = {"nodes": []}

    entry = get_entry_point(graph)
    assert entry == "intake"


def test_get_outgoing_edges(valid_graph):
    """Get all edges leaving a node."""
    edges = get_outgoing_edges(valid_graph, "process")

    assert len(edges) == 2
    assert any(e["to"] == "end" for e in edges)
    assert any(e["to"] == "start" for e in edges)


def test_get_outgoing_edges_single(valid_graph):
    """Node with single outgoing edge."""
    edges = get_outgoing_edges(valid_graph, "start")

    assert len(edges) == 1
    assert edges[0]["to"] == "process"


def test_get_outgoing_edges_none(valid_graph):
    """Terminal node has no outgoing edges."""
    edges = get_outgoing_edges(valid_graph, "end")

    assert len(edges) == 0
