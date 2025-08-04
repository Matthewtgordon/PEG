import json
from pathlib import Path


def test_workflow_graph_structure():
    path = Path("WorkflowGraph.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data.get("nodes"), list)
    assert isinstance(data.get("edges"), list)
