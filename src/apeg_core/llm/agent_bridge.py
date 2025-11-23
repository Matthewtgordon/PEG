"""
APEG Agents Bridge - Integration layer for LLM role execution.

This module provides the AgentsBridge class which serves as the central
integration point for executing LLM roles. It supports:
- OpenAI Agents SDK integration (when available and configured)
- Fallback to OpenAI API via OpenAIClient
- Test mode for deterministic responses in CI/testing

The bridge abstracts away the specific LLM provider, allowing the
orchestrator and scoring components to work with a consistent interface.

Usage:
    from apeg_core.llm import AgentsBridge, LLMRole

    bridge = AgentsBridge(config)
    result = bridge.run_role(LLMRole.ENGINEER, "Design a workflow", context)
    score_result = bridge.run_scorer("Evaluate output", output_text, metadata)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from apeg_core.llm.roles import LLMRole, RoleConfig, get_role_config

logger = logging.getLogger(__name__)


class AgentsBridgeError(Exception):
    """Exception raised when AgentsBridge operations fail."""
    pass


class AgentsBridge:
    """
    Bridge class for executing LLM roles through various backends.

    The AgentsBridge provides a unified interface for calling LLM roles,
    supporting multiple backends:
    1. OpenAI Agents SDK (if configured and available)
    2. OpenAI API via OpenAIClient (fallback)
    3. Test mode with deterministic responses

    Attributes:
        config: Configuration dictionary
        test_mode: Whether to use test mode (no real API calls)
        use_agents_sdk: Whether to use OpenAI Agents SDK
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AgentsBridge.

        Args:
            config: Optional configuration dictionary with keys:
                - use_openai_agents: Whether to use Agents SDK (bool)
                - agents_project_id: OpenAI Agents project ID
                - test_mode: Force test mode (bool)
                - default_model: Default model to use
        """
        self.config = config or {}
        self.test_mode = self._determine_test_mode()
        self.use_agents_sdk = self._determine_agents_sdk()
        self._openai_client = None
        self._agents_client = None

        logger.info(
            "AgentsBridge initialized (test_mode=%s, use_agents_sdk=%s)",
            self.test_mode,
            self.use_agents_sdk
        )

    def _determine_test_mode(self) -> bool:
        """Determine if test mode should be enabled."""
        # Environment variable takes precedence
        env_test_mode = os.environ.get("APEG_TEST_MODE", "").lower()
        if env_test_mode in ("true", "1", "yes"):
            return True
        if env_test_mode in ("false", "0", "no"):
            return False

        # Check config
        return self.config.get("test_mode", False)

    def _determine_agents_sdk(self) -> bool:
        """Determine if OpenAI Agents SDK should be used."""
        if self.test_mode:
            return False

        # Check environment
        env_setting = os.environ.get("APEG_USE_AGENTS_SDK", "").lower()
        if env_setting in ("true", "1", "yes"):
            return True
        if env_setting in ("false", "0", "no"):
            return False

        # Check config
        return self.config.get("use_openai_agents", False)

    def _get_openai_client(self):
        """Get or create OpenAI client for API calls."""
        if self._openai_client is None:
            from apeg_core.connectors import OpenAIClient
            self._openai_client = OpenAIClient()
        return self._openai_client

    def run_role(
        self,
        role: LLMRole | str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute an LLM role with the given prompt and context.

        Args:
            role: Role to execute (LLMRole enum or string)
            prompt: User prompt/instruction
            context: Optional context dictionary
            **kwargs: Additional parameters (model, temperature, max_tokens)

        Returns:
            Dictionary with:
                - content: Generated response text
                - role: Role that was executed
                - model: Model used
                - success: Whether execution succeeded
                - test_mode: Whether test mode was used
                - metadata: Additional execution metadata

        Raises:
            AgentsBridgeError: If role execution fails
        """
        # Normalize role
        if isinstance(role, str):
            try:
                role = LLMRole(role.upper())
            except ValueError:
                raise AgentsBridgeError(f"Unknown role: {role}")

        role_config = get_role_config(role)
        logger.info("Executing role %s with prompt: %s", role, prompt[:100])

        # Test mode - return deterministic response
        if self.test_mode:
            return self._test_mode_response(role, role_config, prompt, context)

        # Try Agents SDK first if enabled
        if self.use_agents_sdk:
            try:
                return self._run_via_agents_sdk(role, role_config, prompt, context, **kwargs)
            except Exception as e:
                logger.warning("Agents SDK failed, falling back to OpenAI API: %s", e)

        # Fallback to OpenAI API
        return self._run_via_openai_api(role, role_config, prompt, context, **kwargs)

    def run_scorer(
        self,
        prompt: str,
        output_to_score: str,
        metadata: Optional[Dict[str, Any]] = None,
        scoring_model: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute the SCORER role for quality evaluation.

        This is a convenience method specifically for scoring operations,
        which are commonly used in the adoption gate and feedback pipeline.

        Args:
            prompt: Scoring instructions
            output_to_score: Text to evaluate
            metadata: Optional metadata about the output
            scoring_model: Optional PromptScoreModel.json dict
            **kwargs: Additional parameters

        Returns:
            Dictionary with:
                - overall_score: Float score (0.0-1.0)
                - metrics: Dictionary of individual metric scores
                - feedback: Human-readable feedback
                - success: Whether scoring succeeded
                - test_mode: Whether test mode was used
        """
        context = {
            "output_to_score": output_to_score,
            "metadata": metadata or {},
        }

        if scoring_model:
            context["scoring_model"] = scoring_model

        result = self.run_role(LLMRole.SCORER, prompt, context, **kwargs)

        # Parse JSON response if needed
        if result.get("success") and isinstance(result.get("content"), str):
            try:
                parsed = json.loads(result["content"])
                result["overall_score"] = parsed.get("overall_score", 0.0)
                result["metrics"] = parsed.get("metrics", {})
                result["feedback"] = parsed.get("feedback", "")
            except json.JSONDecodeError:
                logger.warning("Could not parse SCORER response as JSON")
                result["overall_score"] = 0.5
                result["metrics"] = {}
                result["feedback"] = result.get("content", "")

        return result

    def run_validator(
        self,
        prompt: str,
        output_to_validate: str,
        validation_criteria: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute the VALIDATOR role for output validation.

        Args:
            prompt: Validation instructions
            output_to_validate: Text to validate
            validation_criteria: Optional validation criteria
            **kwargs: Additional parameters

        Returns:
            Dictionary with validation results
        """
        context = {
            "output_to_validate": output_to_validate,
            "validation_criteria": validation_criteria or {},
        }

        result = self.run_role(LLMRole.VALIDATOR, prompt, context, **kwargs)

        # Parse JSON response if needed
        if result.get("success") and isinstance(result.get("content"), str):
            try:
                parsed = json.loads(result["content"])
                result["valid"] = parsed.get("valid", False)
                result["score"] = parsed.get("score", 0.0)
                result["issues"] = parsed.get("issues", [])
                result["recommendations"] = parsed.get("recommendations", [])
            except json.JSONDecodeError:
                logger.warning("Could not parse VALIDATOR response as JSON")
                result["valid"] = False
                result["score"] = 0.0

        return result

    def _test_mode_response(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate deterministic test mode response."""
        logger.info("Test mode: generating stub response for %s", role)

        # Role-specific test responses
        if role == LLMRole.SCORER:
            content = json.dumps({
                "overall_score": 0.85,
                "metrics": {
                    "completeness": 0.9,
                    "format_valid": 0.8,
                    "quality": 0.85
                },
                "feedback": "Test mode scoring - output appears valid"
            })
        elif role == LLMRole.VALIDATOR:
            content = json.dumps({
                "valid": True,
                "score": 0.85,
                "issues": [],
                "recommendations": ["Test mode validation"]
            })
        elif role == LLMRole.CHALLENGER:
            content = json.dumps({
                "critical_issues": [],
                "warnings": ["Test mode - no real adversarial testing"],
                "edge_cases": ["Test edge case"],
                "stress_test_results": {"coverage": "limited"}
            })
        elif role == LLMRole.TESTER:
            content = json.dumps({
                "test_cases": [{"name": "test_basic", "type": "unit", "status": "generated"}],
                "coverage": "limited",
                "recommendations": ["Add integration tests"]
            })
        else:
            content = f"Test mode response for {role.value}: Processed prompt successfully"

        return {
            "content": content,
            "role": role.value,
            "model": "test-mode",
            "success": True,
            "test_mode": True,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "prompt_preview": prompt[:100],
            }
        }

    def _run_via_agents_sdk(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute role via OpenAI Agents SDK.

        Uses the OpenAI Agents SDK to run an agent with role-specific instructions.
        Falls back to OpenAI API if the SDK is not available or fails.

        Args:
            role: LLM role to execute
            role_config: Role configuration with system prompt and parameters
            prompt: User prompt/instruction
            context: Optional context dictionary
            **kwargs: Additional parameters

        Returns:
            Dictionary with execution results

        RESOLVED[APEG-LLM-001]: OpenAI Agents SDK integration implemented
        - Initializes Agents client with project ID from config
        - Creates agent with role-specific instructions
        - Executes agent with prompt and context
        - Parses and returns results
        - Falls back gracefully if SDK not available
        """
        logger.info("Attempting Agents SDK execution for %s", role)

        # Try to import the OpenAI Agents SDK
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("OpenAI SDK not installed, falling back to API")
            raise ImportError("OpenAI SDK not available")

        # Get configuration for Agents SDK
        project_id = self.config.get("agents_project_id") or os.environ.get("OPENAI_PROJECT_ID")
        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            logger.warning("OPENAI_API_KEY not set, cannot use Agents SDK")
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Build the agent instructions from role config
        instructions = role_config.system_prompt
        if context:
            instructions += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        # Get model and parameters
        model = kwargs.get("model", role_config.model)
        temperature = kwargs.get("temperature", role_config.temperature)
        max_tokens = kwargs.get("max_tokens", role_config.max_tokens)

        try:
            # Initialize the OpenAI client
            client_kwargs = {"api_key": api_key}
            if project_id:
                client_kwargs["project"] = project_id

            client = OpenAI(**client_kwargs)

            # Use the Assistants API as the Agents SDK interface
            # Create a temporary assistant for this role execution
            assistant = client.beta.assistants.create(
                name=f"APEG-{role.value}",
                instructions=instructions,
                model=model,
                tools=[],  # No tools for simple role execution
            )

            # Create a thread and run the assistant
            thread = client.beta.threads.create()

            # Add the user message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )

            # Run the assistant
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )

            # Get the response
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                # Get the assistant's response (first message that's from assistant)
                response_content = ""
                for msg in messages.data:
                    if msg.role == "assistant":
                        for content_block in msg.content:
                            if hasattr(content_block, "text"):
                                response_content = content_block.text.value
                                break
                        break

                # Clean up - delete the assistant
                try:
                    client.beta.assistants.delete(assistant.id)
                except Exception as cleanup_err:
                    logger.debug("Failed to cleanup assistant: %s", cleanup_err)

                return {
                    "content": response_content,
                    "role": role.value,
                    "model": model,
                    "success": True,
                    "test_mode": False,
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "backend": "agents_sdk",
                        "assistant_id": assistant.id,
                        "thread_id": thread.id,
                        "run_id": run.id,
                        "tokens_used": {
                            "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                            "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                        } if run.usage else {},
                    }
                }
            else:
                logger.error("Agents SDK run failed with status: %s", run.status)
                raise RuntimeError(f"Agent run failed with status: {run.status}")

        except Exception as e:
            logger.error("Agents SDK execution failed: %s", e)
            # Clean up on error if assistant was created
            raise

    def _run_via_openai_api(
        self,
        role: LLMRole,
        role_config: RoleConfig,
        prompt: str,
        context: Optional[Dict[str, Any]],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute role via OpenAI API using OpenAIClient."""
        logger.info("Executing %s via OpenAI API", role)

        client = self._get_openai_client()

        # Build system prompt with context
        system_prompt = role_config.system_prompt
        if context:
            system_prompt += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        # Get model and parameters
        model = kwargs.get("model", role_config.model)
        temperature = kwargs.get("temperature", role_config.temperature)
        max_tokens = kwargs.get("max_tokens", role_config.max_tokens)

        try:
            response = client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return {
                "content": response.get("content", ""),
                "role": role.value,
                "model": model,
                "success": True,
                "test_mode": False,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "tokens_used": response.get("usage", {}),
                }
            }

        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise AgentsBridgeError(f"Failed to execute role {role}: {e}")

    def get_available_roles(self) -> list[str]:
        """Get list of available role names."""
        from apeg_core.llm.roles import list_roles
        return list_roles()

    def is_test_mode(self) -> bool:
        """Check if bridge is in test mode."""
        return self.test_mode

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "test_mode": self.test_mode,
            "use_agents_sdk": self.use_agents_sdk,
            "config": self.config,
        }


# Convenience singleton
_global_bridge: Optional[AgentsBridge] = None


def get_global_bridge(config: Optional[Dict[str, Any]] = None) -> AgentsBridge:
    """
    Get or create global AgentsBridge instance.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        Global AgentsBridge instance
    """
    global _global_bridge

    if _global_bridge is None:
        _global_bridge = AgentsBridge(config)

    return _global_bridge


def reset_global_bridge() -> None:
    """Reset global bridge instance (for testing)."""
    global _global_bridge
    _global_bridge = None


__all__ = [
    "AgentsBridge",
    "AgentsBridgeError",
    "get_global_bridge",
    "reset_global_bridge",
]
