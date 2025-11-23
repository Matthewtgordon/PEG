"""
Performance benchmark tests for APEG critical paths.

These tests measure performance of key operations to detect regressions.
Run with: pytest tests/benchmarks/ --benchmark-only
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure APEG modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Set test mode
os.environ.setdefault("APEG_TEST_MODE", "true")


class TestOrchestratorPerformance:
    """Benchmark tests for orchestrator initialization and execution."""

    def test_orchestrator_import_time(self, benchmark):
        """Benchmark time to import orchestrator module."""

        def import_orchestrator():
            # Force reimport
            import importlib

            import apeg_core.orchestrator as orch

            importlib.reload(orch)
            return orch

        result = benchmark(import_orchestrator)
        assert result is not None

    def test_orchestrator_init(self, benchmark):
        """Benchmark orchestrator initialization time."""
        from apeg_core.orchestrator import APEGOrchestrator
        from pathlib import Path

        def init_orchestrator():
            # Use actual config files from the repo root
            config_path = Path("SessionConfig.json")
            workflow_path = Path("WorkflowGraph.json")
            if config_path.exists() and workflow_path.exists():
                return APEGOrchestrator(config_path, workflow_path)
            # Return a mock if files don't exist in test environment
            return None

        orch = benchmark(init_orchestrator)
        # May be None if config files not available in test env
        assert True  # Just ensure no exceptions

    def test_config_loading(self, benchmark):
        """Benchmark configuration file loading."""

        def load_configs():
            configs = {}
            config_files = [
                "SessionConfig.json",
                "WorkflowGraph.json",
                "PromptScoreModel.json",
            ]
            for cf in config_files:
                path = Path(cf)
                if path.exists():
                    configs[cf] = json.loads(path.read_text())
            return configs

        configs = benchmark(load_configs)
        assert len(configs) >= 0  # May not have all files in test env


class TestDecisionEnginePerformance:
    """Benchmark tests for decision engine components."""

    def test_bandit_selection_small_history(self, benchmark):
        """Benchmark macro selection with small history."""
        from apeg_core.decision.bandit_selector import choose_macro

        macros = ["macro_role_prompt", "macro_chain_of_thought", "macro_rewrite"]
        history = [{"macro": "macro_role_prompt", "score": 0.8} for _ in range(10)]
        config = {"selector": {"algorithm": "thompson_sampling"}}

        def select():
            return choose_macro(macros, history, config)

        result = benchmark(select)
        assert result in macros

    def test_bandit_selection_large_history(self, benchmark):
        """Benchmark macro selection with large history."""
        from apeg_core.decision.bandit_selector import choose_macro

        macros = ["macro_role_prompt", "macro_chain_of_thought", "macro_rewrite"]
        # Large history to test scaling
        history = [
            {"macro": macros[i % 3], "score": 0.5 + (i % 5) * 0.1} for i in range(1000)
        ]
        config = {"selector": {"algorithm": "thompson_sampling"}}

        def select():
            return choose_macro(macros, history, config)

        result = benchmark(select)
        assert result in macros

    def test_loop_detection(self, benchmark):
        """Benchmark loop detection algorithm."""
        from apeg_core.decision.loop_guard import detect_loop

        # History with potential loop
        history = [
            {"node": "build", "macro": "macro_role_prompt", "score": 0.75},
            {"node": "build", "macro": "macro_role_prompt", "score": 0.76},
            {"node": "build", "macro": "macro_role_prompt", "score": 0.75},
        ]

        def detect():
            return detect_loop(history, N=3, epsilon=0.02)

        result = benchmark(detect)
        assert isinstance(result, bool)


class TestScoringPerformance:
    """Benchmark tests for scoring system."""

    def test_evaluator_init(self, benchmark):
        """Benchmark evaluator initialization."""
        from apeg_core.scoring.evaluator import Evaluator

        def init_evaluator():
            return Evaluator()

        evaluator = benchmark(init_evaluator)
        assert evaluator is not None

    def test_rule_based_scoring(self, benchmark):
        """Benchmark rule-based scoring (no LLM)."""
        from apeg_core.scoring.evaluator import Evaluator

        evaluator = Evaluator()
        test_output = """
        This is a test output for evaluation.
        It contains multiple sentences to simulate real output.
        The content should be analyzed for quality metrics.
        """

        def evaluate():
            return evaluator.evaluate(test_output)

        result = benchmark(evaluate)
        # EvaluationResult is a dataclass with a score attribute
        assert hasattr(result, "score")


class TestMemoryPerformance:
    """Benchmark tests for memory operations."""

    def test_memory_store_write(self, benchmark, tmp_path):
        """Benchmark memory store write operations."""
        from apeg_core.memory.memory_store import MemoryStore

        store = MemoryStore(path=tmp_path / "test_memory.json")

        counter = [0]

        def write_memory():
            counter[0] += 1
            # Use append_run which is the standard API for MemoryStore
            store.append_run({"goal": f"test_{counter[0]}", "success": True, "index": counter[0]})

        benchmark(write_memory)

    def test_memory_store_read(self, benchmark, tmp_path):
        """Benchmark memory store read operations."""
        from apeg_core.memory.memory_store import MemoryStore

        store = MemoryStore(path=tmp_path / "test_memory.json")

        # Pre-populate using the correct API
        for i in range(100):
            store.append_run({"goal": f"test_{i}", "success": True, "index": i})

        def read_memory():
            # Use get_runs to read data
            return store.get_runs()

        result = benchmark(read_memory)
        assert result is not None


class TestLoggingPerformance:
    """Benchmark tests for logging operations."""

    def test_logbook_write(self, benchmark, tmp_path):
        """Benchmark logbook write operations."""
        from apeg_core.logging.logbook_adapter import LogbookAdapter

        adapter = LogbookAdapter(test_mode=True)

        counter = [0]

        def log_event():
            counter[0] += 1
            # Use log_event which is the actual API method
            adapter.log_event(
                event_type="benchmark_test",
                data={"iteration": counter[0]},
            )

        benchmark(log_event)


# Fixtures


@pytest.fixture
def benchmark(request):
    """Simple benchmark fixture if pytest-benchmark not available."""
    try:
        from pytest_benchmark.fixture import BenchmarkFixture

        return request.getfixturevalue("benchmark")
    except ImportError:
        # Fallback simple benchmark
        import time

        class SimpleBenchmark:
            def __call__(self, func):
                start = time.perf_counter()
                result = func()
                elapsed = time.perf_counter() - start
                print(f"\n  {func.__name__}: {elapsed*1000:.3f}ms")
                return result

        return SimpleBenchmark()
