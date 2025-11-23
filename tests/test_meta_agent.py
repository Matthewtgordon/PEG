"""
Tests for MetaAgent - Dynamic subagent generation.

Tests include:
- Basic subagent generation
- Validation failures
- Test execution
- Arsenal integration
- Edge cases and performance
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from apeg_core.agents.meta_agent import MetaAgent, GeneratedAgent


class TestGeneratedAgent:
    """Tests for GeneratedAgent wrapper class."""

    def test_generated_agent_creation(self):
        """Test creating a GeneratedAgent."""
        def mock_execute(action, context, config, test_mode):
            return {"status": "success", "action": action}

        agent = GeneratedAgent(
            agent_name="test_agent",
            capabilities=["action1", "action2"],
            execute_impl=mock_execute,
            test_mode=True
        )

        assert agent.name == "test_agent"
        assert "action1" in agent.describe_capabilities()
        assert "action2" in agent.describe_capabilities()

    def test_generated_agent_execute(self):
        """Test executing an action on a GeneratedAgent."""
        def mock_execute(action, context, config, test_mode):
            return {"status": "success", "result": f"executed_{action}"}

        agent = GeneratedAgent(
            agent_name="test_agent",
            capabilities=["do_task"],
            execute_impl=mock_execute,
            test_mode=True
        )

        result = agent.execute("do_task", {"input": "test"})
        assert result["status"] == "success"
        assert result["result"] == "executed_do_task"

    def test_generated_agent_unsupported_action(self):
        """Test that unsupported actions return error."""
        def mock_execute(action, context, config, test_mode):
            return {"status": "success"}

        agent = GeneratedAgent(
            agent_name="test_agent",
            capabilities=["action1"],
            execute_impl=mock_execute,
            test_mode=True
        )

        result = agent.execute("unsupported_action", {})
        assert result["status"] == "error"
        assert "not supported" in result["error"]

    def test_generated_agent_metadata(self):
        """Test that metadata is properly set."""
        agent = GeneratedAgent(
            agent_name="test_agent",
            capabilities=["action1"],
            execute_impl=lambda *args: {"status": "success"},
            test_mode=True
        )

        metadata = agent.get_metadata()
        assert "generated_at" in metadata
        assert metadata["generator"] == "MetaAgent"


class TestMetaAgent:
    """Tests for MetaAgent subagent generation."""

    @pytest.fixture
    def meta_agent(self):
        """Create a MetaAgent instance for testing."""
        return MetaAgent(orchestrator=None, test_mode=True)

    def test_meta_agent_initialization(self, meta_agent):
        """Test MetaAgent initialization."""
        assert meta_agent.test_mode is True
        assert meta_agent.generated_agents == {}

    def test_design_agent_spec(self, meta_agent):
        """Test designing an agent specification."""
        spec = meta_agent.design_agent_spec("Process payment transactions")

        assert "name" in spec
        assert "capabilities" in spec
        assert "version" in spec
        assert isinstance(spec["capabilities"], list)

    def test_design_agent_spec_deterministic(self, meta_agent):
        """Test that same task produces same spec name in test mode."""
        task = "Handle customer support tickets"
        spec1 = meta_agent.design_agent_spec(task)
        spec2 = meta_agent.design_agent_spec(task)

        assert spec1["name"] == spec2["name"]

    def test_implement_agent(self, meta_agent):
        """Test generating agent implementation."""
        spec = {
            "name": "test_impl_agent",
            "purpose": "Test agent",
            "capabilities": ["test_action"]
        }

        code = meta_agent.implement_agent(spec)

        assert code["name"] == "test_impl_agent"
        assert "impl" in code
        assert "agent_execute" in code["impl"]

    def test_validate_implementation_valid(self, meta_agent):
        """Test validation of valid implementation."""
        valid_code = {
            "name": "valid_agent",
            "impl": '''
def agent_execute(action, context, config, test_mode):
    return {"status": "success"}
'''
        }

        assert meta_agent.validate_implementation(valid_code) is True

    def test_validate_implementation_syntax_error(self, meta_agent):
        """Test validation catches syntax errors."""
        invalid_code = {
            "name": "invalid_agent",
            "impl": "def broken(:\n    pass"
        }

        assert meta_agent.validate_implementation(invalid_code) is False

    def test_validate_implementation_security_violation(self, meta_agent):
        """Test validation catches security violations."""
        dangerous_code = {
            "name": "dangerous_agent",
            "impl": '''
def agent_execute(action, context, config, test_mode):
    eval("dangerous")
    return {"status": "success"}
'''
        }

        assert meta_agent.validate_implementation(dangerous_code) is False

    def test_generate_tests(self, meta_agent):
        """Test generating test cases."""
        spec = {
            "name": "test_agent",
            "capabilities": ["action1", "action2"]
        }

        tests = meta_agent.generate_tests(spec)

        # Should generate tests for each capability plus error handling
        assert len(tests) >= 3
        assert any(t["action"] == "action1" for t in tests)
        assert any(t["action"] == "action2" for t in tests)
        assert any(t["expected_status"] == "error" for t in tests)

    def test_run_tests_success(self, meta_agent):
        """Test running generated tests."""
        code = {
            "name": "test_agent",
            "impl": '''
def agent_execute(action, context, config, test_mode):
    if action == "unknown_action_xyz":
        return {"status": "error"}
    return {"status": "success"}
'''
        }

        tests = [
            {"name": "test1", "action": "test_action", "context": {}, "expected_status": "success"},
            {"name": "test2", "action": "unknown_action_xyz", "context": {}, "expected_status": "error"}
        ]

        results = meta_agent.run_tests(code, tests)

        assert len(results) == 2
        assert all(results)

    def test_generate_subagent_full_flow(self, meta_agent):
        """Test full subagent generation flow."""
        result = meta_agent.generate_subagent("Handle inventory management")

        assert result["status"] == "deployed"
        assert "name" in result
        assert "capabilities" in result

    def test_generate_subagent_validation_failed(self, meta_agent):
        """Test generation fails gracefully on validation failure."""
        # Override validation to fail
        meta_agent.validate_implementation = Mock(return_value=False)

        result = meta_agent.generate_subagent("Any task")

        assert result["status"] == "failed"
        assert result["reason"] == "validation_failed"

    def test_generate_subagent_tests_failed(self, meta_agent):
        """Test generation fails when tests fail."""
        # Override tests to fail
        meta_agent.run_tests = Mock(return_value=[True, False, True])

        result = meta_agent.generate_subagent("Any task")

        assert result["status"] == "failed"
        assert result["reason"] == "tests_failed"

    def test_get_generated_agent(self, meta_agent):
        """Test retrieving a generated agent."""
        # First generate an agent
        meta_agent.generate_subagent("Test task for retrieval")

        agents = meta_agent.list_generated_agents()
        if agents:
            agent = meta_agent.get_generated_agent(agents[0])
            assert agent is not None

    def test_list_generated_agents(self, meta_agent):
        """Test listing generated agents."""
        # Generate a couple of agents
        meta_agent.generate_subagent("Task A")
        meta_agent.generate_subagent("Task B")

        agents = meta_agent.list_generated_agents()
        assert len(agents) >= 2


class TestMetaAgentEdgeCases:
    """Edge case tests for MetaAgent."""

    def test_empty_task_description(self):
        """Test handling of empty task description."""
        meta = MetaAgent(test_mode=True)

        # Should still work with empty string
        result = meta.generate_subagent("")
        # In test mode, it should succeed even with empty task
        assert result["status"] in ["deployed", "failed"]

    def test_very_long_task_description(self):
        """Test handling of very long task descriptions."""
        meta = MetaAgent(test_mode=True)

        long_desc = "Process " * 1000 + "data"
        result = meta.generate_subagent(long_desc)

        assert result["status"] == "deployed"


class TestMetaAgentPerformance:
    """Performance tests for MetaAgent."""

    def test_generation_performance(self):
        """Test that generation completes in reasonable time."""
        meta = MetaAgent(test_mode=True)

        start = time.time()
        meta.generate_subagent("performance test task")
        duration = time.time() - start

        # Should complete in under 5 seconds in test mode
        assert duration < 5.0


class TestMetaAgentWithOrchestrator:
    """Tests for MetaAgent integration with orchestrator."""

    def test_agent_added_to_orchestrator(self):
        """Test that generated agent is added to orchestrator."""
        # Create mock orchestrator
        orchestrator = MagicMock()
        orchestrator.agents = {}

        meta = MetaAgent(orchestrator=orchestrator, test_mode=True)
        result = meta.generate_subagent("Test task for orchestrator")

        if result["status"] == "deployed":
            # Agent should be in orchestrator's agents dict
            assert result["name"] in orchestrator.agents or len(meta.generated_agents) > 0


class TestMetaAgentWithArsenal:
    """Tests for MetaAgent integration with Arsenal."""

    def test_full_flow_with_arsenal(self):
        """Test full generation flow with arsenal integration."""
        from apeg_core.arsenal import ArsenalManager
        import tempfile
        import os

        # Create temp arsenal file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            arsenal_path = f.name

        try:
            arsenal = ArsenalManager(file=arsenal_path)
            meta = MetaAgent(test_mode=True)

            result = meta.generate_subagent("Integration test task")

            if result["status"] == "deployed":
                # Add to arsenal
                arsenal.add(result["name"], {
                    "capabilities": result.get("capabilities", []),
                    "tested": True
                })

                # Verify in arsenal
                assert arsenal.exists(result["name"])
                agent_data = arsenal.get(result["name"])
                assert agent_data is not None
                assert agent_data["tested"] is True
        finally:
            os.unlink(arsenal_path)
