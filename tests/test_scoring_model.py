import json
from pathlib import Path


def test_prompt_score_model_threshold():
    path = Path("PromptScoreModel.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data.get("metrics"), list)
    assert data.get("ci", {}).get("minimum_score") is not None
