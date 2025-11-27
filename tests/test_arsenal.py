"""
Tests for ArsenalManager - Persistent storage for generated agents.

Tests include:
- CRUD operations
- Persistence
- Query and statistics
- Import/export
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from apeg_core.arsenal import ArsenalManager, get_arsenal


class TestArsenalManager:
    """Tests for ArsenalManager."""

    @pytest.fixture
    def temp_arsenal_file(self):
        """Create a temporary arsenal file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name
        yield path
        os.unlink(path)

    @pytest.fixture
    def arsenal(self, temp_arsenal_file):
        """Create an ArsenalManager with temp file."""
        return ArsenalManager(file=temp_arsenal_file)

    def test_initialization_empty(self, arsenal):
        """Test initialization with empty file."""
        assert arsenal.arsenal == {}
        assert arsenal.list_agents() == []

    def test_initialization_nonexistent_file(self):
        """Test initialization with non-existent file."""
        arsenal = ArsenalManager(file="nonexistent_arsenal_xyz.json", auto_load=True)
        assert arsenal.arsenal == {}

    def test_add_agent(self, arsenal):
        """Test adding an agent to the arsenal."""
        spec = {
            "code": "def agent_execute(): pass",
            "capabilities": ["action1", "action2"]
        }

        result = arsenal.add("test_agent", spec)

        assert result is True
        assert arsenal.exists("test_agent")
        assert "test_agent" in arsenal.list_agents()

    def test_add_agent_with_metadata(self, arsenal):
        """Test that metadata is automatically added."""
        arsenal.add("meta_agent", {"code": "pass"})

        agent = arsenal.get("meta_agent")

        assert "added_at" in agent
        assert "version" in agent
        assert agent["tested"] is False

    def test_add_duplicate_agent_fails(self, arsenal):
        """Test that duplicate add fails without replace flag."""
        arsenal.add("dup_agent", {"code": "v1"})
        result = arsenal.add("dup_agent", {"code": "v2"})

        assert result is False
        assert arsenal.get("dup_agent")["code"] == "v1"

    def test_add_duplicate_with_replace(self, arsenal):
        """Test that duplicate add succeeds with replace flag."""
        arsenal.add("dup_agent", {"code": "v1"})
        result = arsenal.add("dup_agent", {"code": "v2"}, replace=True)

        assert result is True
        assert arsenal.get("dup_agent")["code"] == "v2"

    def test_get_agent(self, arsenal):
        """Test getting an agent."""
        arsenal.add("get_test", {"code": "test"})

        agent = arsenal.get("get_test")

        assert agent is not None
        assert agent["code"] == "test"

    def test_get_nonexistent_agent(self, arsenal):
        """Test getting a nonexistent agent."""
        agent = arsenal.get("nonexistent")
        assert agent is None

    def test_remove_agent(self, arsenal):
        """Test removing an agent."""
        arsenal.add("remove_test", {"code": "test"})
        assert arsenal.exists("remove_test")

        result = arsenal.remove("remove_test")

        assert result is True
        assert not arsenal.exists("remove_test")

    def test_remove_nonexistent_agent(self, arsenal):
        """Test removing a nonexistent agent."""
        result = arsenal.remove("nonexistent")
        assert result is False

    def test_list_agents(self, arsenal):
        """Test listing all agents."""
        arsenal.add("agent_a", {"code": "a"})
        arsenal.add("agent_b", {"code": "b"})
        arsenal.add("agent_c", {"code": "c"})

        agents = arsenal.list_agents()

        assert len(agents) == 3
        assert "agent_a" in agents
        assert "agent_b" in agents
        assert "agent_c" in agents

    def test_get_all(self, arsenal):
        """Test getting all agents."""
        arsenal.add("agent_1", {"code": "1"})
        arsenal.add("agent_2", {"code": "2"})

        all_agents = arsenal.get_all()

        assert len(all_agents) == 2
        assert "agent_1" in all_agents
        assert "agent_2" in all_agents

    def test_persistence(self, temp_arsenal_file):
        """Test that data persists between instances."""
        # Create first instance and add data
        arsenal1 = ArsenalManager(file=temp_arsenal_file)
        arsenal1.add("persist_test", {"code": "persistent"})

        # Create second instance and verify data
        arsenal2 = ArsenalManager(file=temp_arsenal_file)

        assert arsenal2.exists("persist_test")
        assert arsenal2.get("persist_test")["code"] == "persistent"

    def test_mark_tested(self, arsenal):
        """Test marking an agent as tested."""
        arsenal.add("test_mark", {"code": "test"})

        result = arsenal.mark_tested("test_mark", [True, True, False])

        assert result is True
        agent = arsenal.get("test_mark")
        assert agent["tested"] is True
        assert "tested_at" in agent
        assert agent["test_results"]["passed"] == 2
        assert agent["test_results"]["total"] == 3

    def test_mark_deployed(self, arsenal):
        """Test marking an agent as deployed."""
        arsenal.add("deploy_test", {"code": "test"})

        arsenal.mark_deployed("deploy_test")
        arsenal.mark_deployed("deploy_test")
        arsenal.mark_deployed("deploy_test")

        agent = arsenal.get("deploy_test")
        assert agent["deployments"] == 3
        assert "last_deployed" in agent


class TestArsenalQuery:
    """Tests for Arsenal query functionality."""

    @pytest.fixture
    def populated_arsenal(self):
        """Create an arsenal with test data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        arsenal = ArsenalManager(file=path)

        # Add various agents
        arsenal.add("tested_agent", {"code": "test", "capabilities": ["cap1"]})
        arsenal.mark_tested("tested_agent")

        arsenal.add("untested_agent", {"code": "test"})

        arsenal.add("deployed_agent", {"code": "test", "capabilities": ["cap1", "cap2"]})
        arsenal.mark_tested("deployed_agent")
        arsenal.mark_deployed("deployed_agent")
        arsenal.mark_deployed("deployed_agent")

        yield arsenal
        os.unlink(path)

    def test_query_tested_only(self, populated_arsenal):
        """Test querying only tested agents."""
        results = populated_arsenal.query(tested_only=True)

        assert "tested_agent" in results
        assert "deployed_agent" in results
        assert "untested_agent" not in results

    def test_query_by_capability(self, populated_arsenal):
        """Test querying by capability."""
        results = populated_arsenal.query(has_capability="cap1")

        assert "tested_agent" in results
        assert "deployed_agent" in results

    def test_query_by_min_deployments(self, populated_arsenal):
        """Test querying by minimum deployments."""
        results = populated_arsenal.query(min_deployments=2)

        assert "deployed_agent" in results
        assert len(results) == 1

    def test_combined_query(self, populated_arsenal):
        """Test combining multiple query filters."""
        results = populated_arsenal.query(
            tested_only=True,
            has_capability="cap1",
            min_deployments=1
        )

        assert results == ["deployed_agent"]


class TestArsenalStats:
    """Tests for Arsenal statistics."""

    @pytest.fixture
    def arsenal_with_stats(self):
        """Create an arsenal with stats data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        arsenal = ArsenalManager(file=path)

        # Add agents with various states
        arsenal.add("agent_1", {"code": "1"})
        arsenal.mark_tested("agent_1")
        arsenal.mark_deployed("agent_1")

        arsenal.add("agent_2", {"code": "2"})
        arsenal.mark_tested("agent_2")

        arsenal.add("agent_3", {"code": "3"})

        yield arsenal
        os.unlink(path)

    def test_get_stats(self, arsenal_with_stats):
        """Test getting statistics."""
        stats = arsenal_with_stats.get_stats()

        assert stats["total_agents"] == 3
        assert stats["tested_agents"] == 2
        assert stats["deployed_agents"] == 1
        assert stats["untested_agents"] == 1


class TestArsenalImportExport:
    """Tests for Arsenal import/export."""

    @pytest.fixture
    def source_arsenal(self):
        """Create a source arsenal for export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        arsenal = ArsenalManager(file=path)
        arsenal.add("export_agent_1", {"code": "1"})
        arsenal.add("export_agent_2", {"code": "2"})

        yield arsenal
        os.unlink(path)

    def test_export_to_file(self, source_arsenal):
        """Test exporting arsenal to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name

        try:
            result = source_arsenal.export_to_file(export_path)

            assert result is True

            # Verify export file
            with open(export_path) as f:
                data = json.load(f)

            assert "agents" in data
            assert "export_agent_1" in data["agents"]
            assert "export_agent_2" in data["agents"]
        finally:
            os.unlink(export_path)

    def test_import_from_file(self, source_arsenal):
        """Test importing from exported file."""
        # Export first
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
            source_arsenal.export_to_file(export_path)

        # Create target arsenal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            target_path = f.name

        try:
            target = ArsenalManager(file=target_path)
            count = target.import_from_file(export_path)

            assert count == 2
            assert target.exists("export_agent_1")
            assert target.exists("export_agent_2")
        finally:
            os.unlink(export_path)
            os.unlink(target_path)

    def test_import_merge(self, source_arsenal):
        """Test import merges with existing data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
            source_arsenal.export_to_file(export_path)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            target_path = f.name

        try:
            target = ArsenalManager(file=target_path)
            target.add("existing_agent", {"code": "existing"})

            count = target.import_from_file(export_path, merge=True)

            assert target.exists("existing_agent")
            assert target.exists("export_agent_1")
            assert target.exists("export_agent_2")
        finally:
            os.unlink(export_path)
            os.unlink(target_path)


class TestArsenalClear:
    """Tests for Arsenal clear functionality."""

    def test_clear(self):
        """Test clearing the arsenal."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            arsenal = ArsenalManager(file=path)
            arsenal.add("agent_1", {"code": "1"})
            arsenal.add("agent_2", {"code": "2"})

            assert len(arsenal.list_agents()) == 2

            arsenal.clear()

            assert len(arsenal.list_agents()) == 0
        finally:
            os.unlink(path)
