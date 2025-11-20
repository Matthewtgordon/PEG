"""Tests for the memory store.

Tests cover:
- Memory store initialization
- Run history management
- Runtime statistics storage
- General-purpose key-value store
- Data persistence and loading
- Summary statistics calculation
"""

import json
import pytest
import tempfile
from pathlib import Path

from apeg_core.memory.memory_store import MemoryStore, get_memory_store


def test_memory_store_initialization():
    """Test memory store initialization with temporary file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        assert store.path == tmp_path
        assert "metadata" in store.data
        assert "runtime_stats" in store.data
        assert "runs" in store.data
        assert "stores" in store.data
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_append_run():
    """Test appending run summary to history."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        run_summary = {
            "goal": "test goal",
            "success": True,
            "score": 0.85,
            "duration_ms": 1234
        }

        store.append_run(run_summary)

        runs = store.get_runs()
        assert len(runs) == 1
        assert runs[0]["goal"] == "test goal"
        assert runs[0]["success"] is True
        assert "timestamp" in runs[0]
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_get_runs_with_limit():
    """Test retrieving runs with limit."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        # Add multiple runs
        for i in range(10):
            store.append_run({"goal": f"goal_{i}", "success": True})

        # Get recent 5
        runs = store.get_runs(limit=5)

        assert len(runs) == 5
        # Should be most recent first
        assert runs[0]["goal"] == "goal_9"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_get_runs_success_only():
    """Test filtering runs by success status."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        store.append_run({"goal": "test1", "success": True})
        store.append_run({"goal": "test2", "success": False})
        store.append_run({"goal": "test3", "success": True})

        successful_runs = store.get_runs(success_only=True)

        assert len(successful_runs) == 2
        assert all(r["success"] for r in successful_runs)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_runtime_stats():
    """Test storing and retrieving runtime statistics."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        # Set runtime stat
        store.update_runtime_stat("bandit_weights", {"macro1": 0.5, "macro2": 0.7})

        # Get runtime stat
        weights = store.get_runtime_stat("bandit_weights")

        assert weights == {"macro1": 0.5, "macro2": 0.7}

        # Get non-existent stat with default
        missing = store.get_runtime_stat("nonexistent", default="default_value")
        assert missing == "default_value"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_general_store():
    """Test general-purpose key-value store."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        # Set values
        store.set_store("custom_key", "custom_value")
        store.set_store("config", {"setting": "value"})

        # Get values
        assert store.get_store("custom_key") == "custom_value"
        assert store.get_store("config") == {"setting": "value"}

        # Delete key
        store.delete_store("custom_key")
        assert store.get_store("custom_key") is None
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_clear_runs():
    """Test clearing run history."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        # Add runs
        for i in range(5):
            store.append_run({"goal": f"goal_{i}", "success": True})

        # Clear all
        store.clear_runs(keep_recent=0)
        assert len(store.get_runs()) == 0

        # Add more runs
        for i in range(5):
            store.append_run({"goal": f"goal_{i}", "success": True})

        # Keep recent 2
        store.clear_runs(keep_recent=2)
        assert len(store.get_runs()) == 2
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_stats_summary():
    """Test getting summary statistics."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        store = MemoryStore(path=tmp_path)

        # Add runs with mixed success
        store.append_run({"goal": "test1", "success": True, "score": 0.8})
        store.append_run({"goal": "test2", "success": False, "score": 0.5})
        store.append_run({"goal": "test3", "success": True, "score": 0.9})

        # Add runtime stats and store values
        store.update_runtime_stat("stat1", "value1")
        store.set_store("key1", "value1")

        summary = store.get_stats_summary()

        assert summary["total_runs"] == 3
        assert summary["successful_runs"] == 2
        assert summary["success_rate"] == pytest.approx(2/3)
        assert summary["average_score"] == pytest.approx(0.85)  # (0.8 + 0.9) / 2
        assert summary["runtime_stats_count"] == 1
        assert summary["store_keys_count"] == 1
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_persistence():
    """Test that data persists across instances."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create first instance and add data
        store1 = MemoryStore(path=tmp_path)
        store1.append_run({"goal": "test", "success": True})
        store1.update_runtime_stat("test_stat", "test_value")

        # Create second instance and verify data persists
        store2 = MemoryStore(path=tmp_path)

        assert len(store2.get_runs()) == 1
        assert store2.get_runtime_stat("test_stat") == "test_value"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_memory_store_export():
    """Test exporting memory data to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "memory.json"
        export_path = Path(tmpdir) / "export.json"

        store = MemoryStore(path=store_path)
        store.append_run({"goal": "test", "success": True})

        store.export_to_file(export_path)

        assert export_path.exists()

        # Verify exported data
        with open(export_path) as f:
            data = json.load(f)

        assert len(data["runs"]) == 1


def test_get_memory_store_singleton():
    """Test global memory store singleton."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Note: Global store may have been initialized already
        # This test just verifies the function works
        store = get_memory_store(tmp_path)
        assert isinstance(store, MemoryStore)
    finally:
        tmp_path.unlink(missing_ok=True)
