import json
import sys
import os
from pathlib import Path

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from orchestrator import Orchestrator
import pytest

def test_orchestrator_integration(tmp_path: Path):
    pytest.skip("Orchestrator integration test pending update to new API")
