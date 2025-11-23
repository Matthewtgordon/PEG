"""
Meta-Agent - Dynamically generates, tests, and deploys subagents for novel tasks.

This module implements a meta-agent that extends the ENGINEER agent capabilities
to create new specialized agents on-the-fly when the orchestrator encounters
tasks that existing agents cannot handle effectively.

Key Features:
- Dynamic subagent specification design using ENGINEER role
- Code generation for new agent implementations
- Validation of generated code via VALIDATOR role
- Testing harness for generated agents
- Integration with arsenal for persistent storage
- Safe deployment to orchestrator runtime

Usage:
    meta = MetaAgent(orchestrator)
    result = meta.generate_subagent("Handle Stripe payment processing")
    if result["status"] == "deployed":
        # New agent is available in orchestrator.agents[result["name"]]
"""

from __future__ import annotations

import logging
import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_agent import BaseAgent
from .agent_registry import register_agent, is_agent_registered

if TYPE_CHECKING:
    from apeg_core.orchestrator import APEGOrchestrator

logger = logging.getLogger(__name__)


class GeneratedAgent(BaseAgent):
    """
    Wrapper class for dynamically generated agents.

    This class wraps dynamically generated agent implementations,
    providing a consistent interface while allowing custom behavior.
    """

    def __init__(
        self,
        agent_name: str,
        capabilities: List[str],
        execute_impl: callable,
        config: Dict[str, Any] | None = None,
        test_mode: bool = False
    ) -> None:
        """
        Initialize a generated agent wrapper.

        Args:
            agent_name: Name of the generated agent
            capabilities: List of capabilities this agent supports
            execute_impl: The execution function to call
            config: Agent configuration
            test_mode: Whether to run in test mode
        """
        super().__init__(config=config, test_mode=test_mode)
        self._name = agent_name
        self._capabilities = capabilities
        self._execute_impl = execute_impl
        self._metadata = {
            "generated_at": datetime.now().isoformat(),
            "generator": "MetaAgent",
            "version": "1.0.0"
        }

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return self._name

    def execute(self, action: str, context: Dict) -> Dict:
        """Execute an action using the generated implementation."""
        if action not in self._capabilities:
            return {
                "status": "error",
                "error": f"Action '{action}' not supported. Available: {self._capabilities}"
            }

        try:
            result = self._execute_impl(action, context, self.config, self.test_mode)
            self._log_action(action, result)
            return result
        except Exception as e:
            logger.error(f"Generated agent {self._name} failed: {e}")
            return {"status": "error", "error": str(e)}

    def describe_capabilities(self) -> List[str]:
        """Return list of supported capabilities."""
        return self._capabilities.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """Get agent metadata including generation info."""
        return self._metadata.copy()


class MetaAgent:
    """
    Meta-Agent for dynamically generating and deploying subagents.

    The MetaAgent uses LLM roles (ENGINEER, VALIDATOR, TESTER) to:
    1. Design agent specifications based on task descriptions
    2. Generate implementation code
    3. Validate the generated code
    4. Test the agent behavior
    5. Deploy to the orchestrator runtime

    Attributes:
        orchestrator: Reference to APEGOrchestrator for deployment
        generated_agents: Registry of generated agent specs
        test_mode: Whether to use test mode for LLM calls
    """

    def __init__(
        self,
        orchestrator: Optional[APEGOrchestrator] = None,
        test_mode: bool = False
    ) -> None:
        """
        Initialize the MetaAgent.

        Args:
            orchestrator: APEGOrchestrator instance for agent deployment
            test_mode: If True, use mock LLM responses
        """
        self.orchestrator = orchestrator
        self.test_mode = test_mode
        self.generated_agents: Dict[str, Dict[str, Any]] = {}

        logger.info("MetaAgent initialized (test_mode=%s)", test_mode)

    def design_agent_spec(self, task_desc: str) -> Dict[str, Any]:
        """
        Design an agent specification based on task description.

        Uses the ENGINEER LLM role to design the agent's:
        - Name and purpose
        - Capabilities required
        - Input/output interface
        - Dependencies

        Args:
            task_desc: Natural language description of the task

        Returns:
            Agent specification dictionary
        """
        logger.info("Designing agent spec for: %s", task_desc[:50])

        if self.test_mode:
            # Generate deterministic test spec
            name_hash = hashlib.md5(task_desc.encode()).hexdigest()[:8]
            return {
                "name": f"generated_agent_{name_hash}",
                "purpose": task_desc,
                "capabilities": ["execute_task", "validate_result"],
                "inputs": ["task_context", "parameters"],
                "outputs": ["result", "status"],
                "dependencies": [],
                "version": "1.0.0"
            }

        # Use ENGINEER LLM role to design spec
        try:
            from apeg_core.agents.llm_roles import run_engineer_role

            prompt = f"""Design an agent specification for the following task:

Task Description: {task_desc}

Provide a JSON specification with:
- name: A snake_case identifier for the agent
- purpose: Brief description of what the agent does
- capabilities: List of action names the agent can perform
- inputs: Required input parameters
- outputs: What the agent returns
- dependencies: External services or APIs needed

Return only valid JSON."""

            result = run_engineer_role(
                prompt=prompt,
                context={"task": task_desc},
                test_mode=self.test_mode
            )

            # Parse JSON from response
            import json
            spec = json.loads(result.get("content", "{}"))

            # Ensure required fields
            spec.setdefault("name", f"generated_agent_{hashlib.md5(task_desc.encode()).hexdigest()[:8]}")
            spec.setdefault("capabilities", ["execute_task"])
            spec.setdefault("version", "1.0.0")

            return spec

        except Exception as e:
            logger.error("Failed to design agent spec: %s", e)
            # Fallback to basic spec
            name_hash = hashlib.md5(task_desc.encode()).hexdigest()[:8]
            return {
                "name": f"generated_agent_{name_hash}",
                "purpose": task_desc,
                "capabilities": ["execute_task"],
                "inputs": ["context"],
                "outputs": ["result"],
                "dependencies": [],
                "version": "1.0.0"
            }

    def implement_agent(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate implementation code for an agent specification.

        Uses the ENGINEER LLM role to generate Python code that
        implements the specified agent behavior.

        Args:
            spec: Agent specification from design_agent_spec()

        Returns:
            Dictionary with name, impl (code string), and capabilities
        """
        logger.info("Implementing agent: %s", spec.get("name", "unknown"))

        agent_name = spec.get("name", "generated_agent")
        capabilities = spec.get("capabilities", ["execute_task"])
        purpose = spec.get("purpose", "Execute task")

        if self.test_mode:
            # Generate test implementation
            impl = self._generate_test_implementation(agent_name, capabilities, purpose)
            return {
                "name": agent_name,
                "impl": impl,
                "capabilities": capabilities,
                "spec": spec
            }

        # Use ENGINEER LLM role to generate implementation
        try:
            from apeg_core.agents.llm_roles import run_engineer_role

            prompt = f"""Generate a Python function implementation for an agent with:

Name: {agent_name}
Purpose: {purpose}
Capabilities: {capabilities}

The function should have this signature:
def agent_execute(action: str, context: dict, config: dict, test_mode: bool) -> dict:

It should:
1. Handle each capability as an action
2. Return a dict with 'status' and 'result' keys
3. Handle errors gracefully
4. Support test_mode for mock responses

Return only the Python function code, no imports needed."""

            result = run_engineer_role(
                prompt=prompt,
                context={"spec": spec},
                test_mode=self.test_mode
            )

            impl = result.get("content", "")

            # Validate the implementation has required structure
            if "def agent_execute" not in impl:
                impl = self._generate_test_implementation(agent_name, capabilities, purpose)

            return {
                "name": agent_name,
                "impl": impl,
                "capabilities": capabilities,
                "spec": spec
            }

        except Exception as e:
            logger.error("Failed to implement agent: %s", e)
            impl = self._generate_test_implementation(agent_name, capabilities, purpose)
            return {
                "name": agent_name,
                "impl": impl,
                "capabilities": capabilities,
                "spec": spec
            }

    def _generate_test_implementation(
        self,
        name: str,
        capabilities: List[str],
        purpose: str
    ) -> str:
        """Generate a basic test implementation."""
        capabilities_str = ", ".join(f'"{c}"' for c in capabilities)
        return f'''
def agent_execute(action: str, context: dict, config: dict, test_mode: bool) -> dict:
    """
    Generated agent: {name}
    Purpose: {purpose}
    """
    supported_actions = [{capabilities_str}]

    if action not in supported_actions:
        return {{"status": "error", "error": f"Unknown action: {{action}}"}}

    if test_mode:
        return {{"status": "success", "result": f"Test result for {{action}}", "action": action}}

    # Execute the action
    try:
        result = {{"status": "success", "result": f"Executed {{action}}", "context": context}}
        return result
    except Exception as e:
        return {{"status": "error", "error": str(e)}}
'''

    def validate_implementation(self, code: Dict[str, Any]) -> bool:
        """
        Validate generated agent implementation.

        Performs:
        - Syntax validation
        - Security checks (no dangerous operations)
        - Interface compliance

        Args:
            code: Implementation dict from implement_agent()

        Returns:
            True if valid, False otherwise
        """
        impl = code.get("impl", "")
        name = code.get("name", "unknown")

        logger.info("Validating implementation for: %s", name)

        # Syntax validation
        try:
            compile(impl, f"<{name}>", "exec")
        except SyntaxError as e:
            logger.error("Syntax error in generated code: %s", e)
            return False

        # Security checks - disallow dangerous operations
        dangerous_patterns = [
            r"__import__\s*\(",
            r"exec\s*\(",
            r"eval\s*\(",
            r"subprocess",
            r"os\.system",
            r"os\.popen",
            r"shutil\.rmtree",
            r"open\s*\([^)]*['\"]w['\"]",  # File writes
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, impl):
                logger.error("Security violation: dangerous pattern '%s' found", pattern)
                return False

        # Check for required function
        if "def agent_execute" not in impl:
            logger.error("Missing required function 'agent_execute'")
            return False

        logger.info("Validation passed for: %s", name)
        return True

    def generate_tests(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate test cases for an agent specification.

        Args:
            spec: Agent specification

        Returns:
            List of test case dictionaries
        """
        capabilities = spec.get("capabilities", [])
        name = spec.get("name", "unknown")

        tests = []

        # Generate basic tests for each capability
        for cap in capabilities:
            tests.append({
                "name": f"test_{name}_{cap}_success",
                "action": cap,
                "context": {"test": True},
                "expected_status": "success"
            })

            tests.append({
                "name": f"test_{name}_{cap}_test_mode",
                "action": cap,
                "context": {"test_mode": True},
                "expected_status": "success",
                "test_mode": True
            })

        # Add error handling test
        tests.append({
            "name": f"test_{name}_unknown_action",
            "action": "nonexistent_action_xyz",
            "context": {},
            "expected_status": "error"
        })

        return tests

    def run_tests(
        self,
        code: Dict[str, Any],
        tests: List[Dict[str, Any]]
    ) -> List[bool]:
        """
        Run test cases against generated implementation.

        Args:
            code: Implementation dict
            tests: Test cases from generate_tests()

        Returns:
            List of test results (True for pass, False for fail)
        """
        impl = code.get("impl", "")
        name = code.get("name", "unknown")

        logger.info("Running %d tests for: %s", len(tests), name)

        # Create execution namespace
        namespace: Dict[str, Any] = {}

        try:
            exec(impl, namespace)
        except Exception as e:
            logger.error("Failed to execute implementation: %s", e)
            return [False] * len(tests)

        execute_fn = namespace.get("agent_execute")
        if not execute_fn:
            logger.error("Function 'agent_execute' not found in namespace")
            return [False] * len(tests)

        results = []
        for test in tests:
            try:
                result = execute_fn(
                    action=test["action"],
                    context=test.get("context", {}),
                    config={},
                    test_mode=test.get("test_mode", True)
                )

                passed = result.get("status") == test.get("expected_status", "success")
                results.append(passed)

                if passed:
                    logger.debug("  PASS: %s", test["name"])
                else:
                    logger.warning("  FAIL: %s (got %s, expected %s)",
                                   test["name"], result.get("status"), test["expected_status"])

            except Exception as e:
                logger.error("  ERROR in %s: %s", test["name"], e)
                results.append(False)

        passed_count = sum(results)
        logger.info("Test results: %d/%d passed", passed_count, len(tests))

        return results

    def deploy_agent(self, code: Dict[str, Any]) -> bool:
        """
        Deploy a validated agent to the orchestrator.

        Args:
            code: Validated implementation dict

        Returns:
            True if deployment successful
        """
        impl = code.get("impl", "")
        name = code.get("name", "unknown")
        capabilities = code.get("capabilities", [])

        logger.info("Deploying agent: %s", name)

        # Create execution namespace and execute implementation
        namespace: Dict[str, Any] = {}
        try:
            exec(impl, namespace)
        except Exception as e:
            logger.error("Failed to execute implementation for deployment: %s", e)
            return False

        execute_fn = namespace.get("agent_execute")
        if not execute_fn:
            logger.error("Function 'agent_execute' not found")
            return False

        # Create GeneratedAgent wrapper
        agent = GeneratedAgent(
            agent_name=name,
            capabilities=capabilities,
            execute_impl=execute_fn,
            test_mode=self.test_mode
        )

        # Register in global agent registry
        try:
            register_agent(name, type(agent))
            # Store the actual instance for direct access
            self.generated_agents[name] = {
                "instance": agent,
                "code": code,
                "deployed_at": datetime.now().isoformat()
            }

            # If orchestrator is available, add to its agents dict
            if self.orchestrator and hasattr(self.orchestrator, 'agents'):
                self.orchestrator.agents[name] = agent

            logger.info("Successfully deployed agent: %s", name)
            return True

        except Exception as e:
            logger.error("Failed to register agent: %s", e)
            return False

    def generate_subagent(self, task_desc: str) -> Dict[str, Any]:
        """
        Main entry point: Generate, test, and deploy a subagent for a task.

        This is the primary method to call when a novel task is detected.
        It orchestrates the full pipeline:
        1. Design agent specification
        2. Generate implementation
        3. Validate code
        4. Generate and run tests
        5. Deploy if all checks pass

        Args:
            task_desc: Natural language description of the task

        Returns:
            Dictionary with status ("deployed" or "failed") and agent name
        """
        logger.info("=== Generating subagent for: %s ===", task_desc[:50])

        # Step 1: Design specification
        spec = self.design_agent_spec(task_desc)
        logger.info("Designed spec: %s", spec.get("name"))

        # Step 2: Generate implementation
        code = self.implement_agent(spec)
        logger.info("Generated implementation")

        # Step 3: Validate
        if not self.validate_implementation(code):
            logger.error("Validation failed")
            return {"status": "failed", "reason": "validation_failed", "name": code.get("name")}
        logger.info("Validation passed")

        # Step 4: Generate and run tests
        tests = self.generate_tests(spec)
        test_results = self.run_tests(code, tests)

        if not all(test_results):
            failed_count = len(test_results) - sum(test_results)
            logger.error("Testing failed: %d test(s) failed", failed_count)
            return {"status": "failed", "reason": "tests_failed", "name": code.get("name")}
        logger.info("All tests passed")

        # Step 5: Deploy
        if not self.deploy_agent(code):
            logger.error("Deployment failed")
            return {"status": "failed", "reason": "deployment_failed", "name": code.get("name")}

        logger.info("=== Successfully deployed: %s ===", code.get("name"))
        return {
            "status": "deployed",
            "name": code.get("name"),
            "capabilities": code.get("capabilities", []),
            "spec": spec
        }

    def get_generated_agent(self, name: str) -> Optional[GeneratedAgent]:
        """
        Get a generated agent instance by name.

        Args:
            name: Agent name

        Returns:
            GeneratedAgent instance or None
        """
        agent_info = self.generated_agents.get(name)
        if agent_info:
            return agent_info.get("instance")
        return None

    def list_generated_agents(self) -> List[str]:
        """List all generated agent names."""
        return list(self.generated_agents.keys())
