import json
from pathlib import Path


def test_knowledge_json_loads():
    path = Path("Knowledge.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert data  # ensure not empty
