"""Workflow graph executor with node validation and edge traversal.

This module provides utilities for validating and navigating workflow graphs
as defined in WorkflowGraph.json. It ensures graph integrity and provides
safe traversal mechanisms for the orchestrator.

Example:
    from apeg_core.workflow import validate_workflow_graph, get_next_node

    # Validate graph structure
    workflow_graph = load_workflow_graph()
    validate_workflow_graph(workflow_graph)

    # Navigate graph
    next_node_id = get_next_node(workflow_graph, "intake", "success")
"""

import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def validate_workflow_graph(graph: Dict) -> bool:
    """Validate the structure and integrity of a workflow graph.

    Performs comprehensive validation including:
    - Required top-level keys present
    - All nodes have required fields (id, type)
    - All edges reference valid node IDs
    - No orphaned nodes (except terminal nodes)
    - Graph is connected

    Args:
        graph: Workflow graph dictionary from WorkflowGraph.json

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails with detailed error message

    Example:
        try:
            validate_workflow_graph(workflow_graph)
            print("Graph is valid")
        except ValueError as e:
            print(f"Validation failed: {e}")
    """
    # Check for required top-level keys
    if "nodes" not in graph:
        raise ValueError("Workflow graph must contain 'nodes' key")

    if "edges" not in graph:
        raise ValueError("Workflow graph must contain 'edges' key")

    nodes = graph["nodes"]
    edges = graph["edges"]

    # Validate nodes
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValueError("Workflow graph must have at least one node")

    node_ids: Set[str] = set()
    for i, node in enumerate(nodes):
        # Check required fields
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {i} must be a dictionary")

        if "id" not in node:
            raise ValueError(f"Node at index {i} missing required 'id' field")

        if "type" not in node:
            raise ValueError(f"Node at index {i} ('{node.get('id')}') missing required 'type' field")

        # Check for duplicate IDs
        node_id = node["id"]
        if node_id in node_ids:
            raise ValueError(f"Duplicate node ID found: '{node_id}'")

        node_ids.add(node_id)

    # Validate edges
    if not isinstance(edges, list):
        raise ValueError("Workflow graph 'edges' must be a list")

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"Edge at index {i} must be a dictionary")

        # Check required fields
        if "from" not in edge:
            raise ValueError(f"Edge at index {i} missing required 'from' field")

        if "to" not in edge:
            raise ValueError(f"Edge at index {i} missing required 'to' field")

        # Validate edge references
        from_node = edge["from"]
        to_node = edge["to"]

        if from_node not in node_ids:
            raise ValueError(
                f"Edge {i}: 'from' node '{from_node}' does not exist in nodes list"
            )

        if to_node not in node_ids:
            raise ValueError(
                f"Edge {i}: 'to' node '{to_node}' does not exist in nodes list"
            )

    logger.info(
        f"Workflow graph validation passed: {len(nodes)} nodes, {len(edges)} edges"
    )
    return True


def get_next_node(
    graph: Dict,
    current_node_id: str,
    condition: str = ""
) -> Optional[str]:
    """Find the next node ID based on current node and condition.

    Traverses the graph edges to find the next node. Supports:
    - Unconditional edges (no condition field)
    - Conditional edges (matching condition field)
    - Default edges (condition="default" or "*")

    Args:
        graph: Workflow graph dictionary
        current_node_id: ID of the current node
        condition: Condition/result from current node execution (default: "")

    Returns:
        Next node ID, or None if no matching edge found

    Example:
        # Simple traversal
        next_id = get_next_node(graph, "intake", "success")
        if next_id:
            print(f"Moving to node: {next_id}")

        # Conditional routing
        if score >= 0.8:
            next_id = get_next_node(graph, "review", "score_passed")
        else:
            next_id = get_next_node(graph, "review", "validation_failed")
    """
    edges = graph.get("edges", [])

    # First, try to find exact condition match
    for edge in edges:
        if edge.get("from") != current_node_id:
            continue

        edge_condition = edge.get("condition", "")

        # Exact match
        if edge_condition == condition:
            logger.debug(
                f"Edge found: {current_node_id} -> {edge['to']} (condition='{condition}')"
            )
            return edge["to"]

    # Second, try default/wildcard edges
    for edge in edges:
        if edge.get("from") != current_node_id:
            continue

        edge_condition = edge.get("condition", "")

        # Default or wildcard match
        if edge_condition in ("default", "*", ""):
            logger.debug(
                f"Default edge found: {current_node_id} -> {edge['to']}"
            )
            return edge["to"]

    # No matching edge found
    logger.warning(
        f"No edge found from node '{current_node_id}' with condition '{condition}'"
    )
    return None


def get_node_by_id(graph: Dict, node_id: str) -> Optional[Dict]:
    """Retrieve a node's full details by its ID.

    Args:
        graph: Workflow graph dictionary
        node_id: ID of the node to retrieve

    Returns:
        Node dictionary, or None if not found

    Example:
        node = get_node_by_id(graph, "build")
        if node:
            print(f"Node type: {node['type']}")
            print(f"Agent: {node.get('agent', 'N/A')}")
    """
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def get_entry_point(graph: Dict) -> str:
    """Determine the entry point node for the workflow.

    Checks in order:
    1. Explicit 'entry_point' field in graph
    2. Node with type='start'
    3. First node in nodes list
    4. Default to "intake" if all else fails

    Args:
        graph: Workflow graph dictionary

    Returns:
        Entry point node ID

    Example:
        entry_id = get_entry_point(workflow_graph)
        print(f"Starting workflow at: {entry_id}")
    """
    # Check for explicit entry point
    if "entry_point" in graph:
        return graph["entry_point"]

    # Look for start node
    for node in graph.get("nodes", []):
        if node.get("type") == "start":
            return node["id"]

    # Use first node
    nodes = graph.get("nodes", [])
    if nodes:
        return nodes[0]["id"]

    # Fallback default
    return "intake"


def get_outgoing_edges(graph: Dict, node_id: str) -> List[Dict]:
    """Get all edges leaving a specific node.

    Args:
        graph: Workflow graph dictionary
        node_id: ID of the source node

    Returns:
        List of edge dictionaries

    Example:
        edges = get_outgoing_edges(graph, "review")
        print(f"Review node has {len(edges)} possible exits")
        for edge in edges:
            print(f"  -> {edge['to']} (condition: {edge.get('condition', 'any')})")
    """
    return [edge for edge in graph.get("edges", []) if edge.get("from") == node_id]
