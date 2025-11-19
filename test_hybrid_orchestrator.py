#!/usr/bin/env python3
"""
Test script for APEG Hybrid Orchestrator build.

Verifies all 7 milestones against acceptance checklist.
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all new modules can be imported."""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)

    try:
        # Web API
        from apeg_core.web import api, server
        print("✓ Web API modules imported")

        # LLM Roles
        from apeg_core.agents import llm_roles
        print("✓ LLM roles module imported")

        # Domain Agents
        from apeg_core.agents import BaseAgent, ShopifyAgent, EtsyAgent
        print("✓ Domain agents imported")

        # Evaluator
        from apeg_core.scoring import Evaluator, EvaluationResult
        print("✓ Evaluator imported")

        # Memory Store
        from apeg_core.memory import MemoryStore, get_memory_store
        print("✓ Memory store imported")

        print("\n✅ All imports successful!\n")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}\n")
        return False


def test_domain_agents():
    """Test domain agent stubs."""
    print("=" * 60)
    print("TEST 2: Domain Agent Stubs")
    print("=" * 60)

    try:
        from apeg_core.agents import ShopifyAgent, EtsyAgent

        # Test Shopify Agent
        shopify = ShopifyAgent()
        capabilities = shopify.describe_capabilities()
        print(f"Shopify capabilities: {len(capabilities)} methods")
        assert "list_products" in capabilities
        assert "update_inventory" in capabilities

        products = shopify.list_products()
        print(f"  list_products() returned {len(products)} stub products")

        # Test Etsy Agent
        etsy = EtsyAgent()
        capabilities = etsy.describe_capabilities()
        print(f"Etsy capabilities: {len(capabilities)} methods")
        assert "list_listings" in capabilities
        assert "suggest_listing_seo" in capabilities

        listings = etsy.list_listings()
        print(f"  list_listings() returned {len(listings)} stub listings")

        print("\n✅ Domain agents working!\n")
        return True

    except Exception as e:
        print(f"\n❌ Domain agents test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_evaluator():
    """Test evaluator with rule-based scoring."""
    print("=" * 60)
    print("TEST 3: Evaluator (Rule-based Scoring)")
    print("=" * 60)

    try:
        from apeg_core.scoring import Evaluator

        evaluator = Evaluator()

        # Test empty output
        result1 = evaluator.evaluate("")
        print(f"Empty output: score={result1.score:.2f}, passed={result1.passed}")
        assert result1.score == 0.0

        # Test short output
        result2 = evaluator.evaluate("Short text")
        print(f"Short output: score={result2.score:.2f}, passed={result2.passed}")

        # Test good output
        good_text = """
        This is a well-formed output with multiple sentences.
        It has proper structure and reasonable length.
        The content is organized into paragraphs.

        It should score reasonably well on the evaluator.
        """
        result3 = evaluator.evaluate(good_text)
        print(f"Good output: score={result3.score:.2f}, passed={result3.passed}")
        assert result3.score > 0.5

        print(f"  Metrics: {result3.metrics}")
        print(f"  Feedback: {result3.feedback}")

        print("\n✅ Evaluator working!\n")
        return True

    except Exception as e:
        print(f"\n❌ Evaluator test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_memory_store():
    """Test memory store."""
    print("=" * 60)
    print("TEST 4: Memory Store")
    print("=" * 60)

    try:
        from apeg_core.memory import MemoryStore
        import tempfile

        # Use temp file for testing
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        store = MemoryStore(temp_path)

        # Test append run
        store.append_run({
            "goal": "Test goal",
            "success": True,
            "score": 0.85,
        })
        print("✓ Appended run to memory")

        # Test get runs
        runs = store.get_runs()
        print(f"  Retrieved {len(runs)} runs")
        assert len(runs) == 1
        assert runs[0]["goal"] == "Test goal"

        # Test runtime stats
        store.update_runtime_stat("test_stat", 42)
        stat = store.get_runtime_stat("test_stat")
        print(f"✓ Runtime stat: test_stat={stat}")
        assert stat == 42

        # Test store
        store.set_store("test_key", "test_value")
        value = store.get_store("test_key")
        print(f"✓ Store: test_key={value}")
        assert value == "test_value"

        # Test stats summary
        summary = store.get_stats_summary()
        print(f"✓ Stats summary: {summary}")

        # Cleanup
        import os
        os.unlink(temp_path)

        print("\n✅ Memory store working!\n")
        return True

    except Exception as e:
        print(f"\n❌ Memory store test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_web_api():
    """Test Web API endpoints (without server)."""
    print("=" * 60)
    print("TEST 5: Web API Structure")
    print("=" * 60)

    try:
        from apeg_core.web.api import app, RunRequest, RunResponse, HealthResponse

        print(f"✓ FastAPI app created: {app.title}")
        print(f"  Routes:")

        for route in app.routes:
            if hasattr(route, 'path'):
                print(f"    {route.path}")

        # Test request/response models
        req = RunRequest(goal="Test goal")
        print(f"✓ RunRequest model: goal='{req.goal}'")

        resp = RunResponse(success=True, final_output="Test output")
        print(f"✓ RunResponse model: success={resp.success}")

        print("\n✅ Web API structure valid!\n")
        return True

    except Exception as e:
        print(f"\n❌ Web API test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_web_ui():
    """Test Web UI files exist."""
    print("=" * 60)
    print("TEST 6: Web UI Files")
    print("=" * 60)

    try:
        webui_dir = Path("webui/static")

        files = [
            "index.html",
            "style.css",
            "app.js",
        ]

        for filename in files:
            filepath = webui_dir / filename
            if filepath.exists():
                print(f"✓ {filename} exists ({filepath.stat().st_size} bytes)")
            else:
                print(f"❌ {filename} NOT FOUND")
                return False

        print("\n✅ Web UI files present!\n")
        return True

    except Exception as e:
        print(f"\n❌ Web UI test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_llm_roles():
    """Test LLM role stubs."""
    print("=" * 60)
    print("TEST 7: LLM Role Adapters (Stubs)")
    print("=" * 60)

    try:
        from apeg_core.agents.llm_roles import (
            run_engineer_role,
            run_validator_role,
            run_scorer_role,
            LLMRoleError,
        )

        print("✓ LLM role functions imported")

        # Test that they raise NotImplementedError (as expected in Phase 1)
        try:
            run_engineer_role("test prompt")
            print("❌ Should have raised NotImplementedError")
            return False
        except NotImplementedError as e:
            print(f"✓ ENGINEER role raises NotImplementedError (as expected)")
            assert "TODO[APEG-PH-4]" in str(e)

        try:
            run_validator_role("test", "output")
            print("❌ Should have raised NotImplementedError")
            return False
        except NotImplementedError as e:
            print(f"✓ VALIDATOR role raises NotImplementedError (as expected)")

        try:
            run_scorer_role("test", "output")
            print("❌ Should have raised NotImplementedError")
            return False
        except NotImplementedError as e:
            print(f"✓ SCORER role raises NotImplementedError (as expected)")

        print("\n✅ LLM roles have proper stubs with TODO markers!\n")
        return True

    except Exception as e:
        print(f"\n❌ LLM roles test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("*" * 60)
    print("* APEG HYBRID ORCHESTRATOR - BUILD ACCEPTANCE TESTS")
    print("*" * 60)
    print("\n")

    tests = [
        ("Module Imports", test_imports),
        ("Domain Agent Stubs", test_domain_agents),
        ("Evaluator", test_evaluator),
        ("Memory Store", test_memory_store),
        ("Web API Structure", test_web_api),
        ("Web UI Files", test_web_ui),
        ("LLM Role Stubs", test_llm_roles),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"FATAL ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)

    print(f"\nTotal: {passed_count}/{total} tests passed")

    if passed_count == total:
        print("\n🎉 ALL TESTS PASSED! Build acceptance complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed_count} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
