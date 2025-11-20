"""
APEG LLM Role Adapters - OpenAI Agents SDK integration for role-based calls.

This module provides high-level wrappers for executing different agent roles:
- ENGINEER: Designs and constructs prompts/workflows
- VALIDATOR: Validates outputs against requirements
- SCORER: Evaluates quality and assigns scores
- CHALLENGER: Stress-tests logic and identifies flaws
- LOGGER: Audits and logs operations
- TESTER: Creates and runs tests

Phase 1: Stub implementations with NotImplementedError
Phase 2: Real OpenAI Agents SDK or API integration

Integration points:
- APEGOrchestrator._execute_node() should detect role assignments
- Build prompts from state, Knowledge.json, and WorkflowGraph
- Call appropriate run_*_role() function
- Record output for evaluation
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMRoleError(Exception):
    """Exception raised when LLM role execution fails."""

    pass


def _get_openai_client() -> Any:
    """
    Get OpenAI client for API calls.

    Returns:
        OpenAI client instance or None if in test mode

    Raises:
        LLMRoleError: If OPENAI_API_KEY is not set and not in test mode
    """
    # Check test mode first
    test_mode = os.environ.get("APEG_TEST_MODE", "false").lower() == "true"
    if test_mode:
        logger.info("Test mode enabled - LLM roles will use mock responses")
        return None  # Will trigger test mode in role functions

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMRoleError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it to use LLM roles, or enable APEG_TEST_MODE=true."
        )

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return client
    except ImportError:
        raise LLMRoleError(
            "openai package not installed. Install with: pip install openai"
        )


def run_engineer_role(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """
    Execute the ENGINEER role using OpenAI API.

    The ENGINEER role is responsible for:
    - Designing macro chains and workflows
    - Constructing prompts with proper structure
    - Injecting constraints and requirements
    - Building solutions from specifications

    Args:
        prompt: The task or instruction for the engineer
        context: Optional context dictionary with state, history, etc.
        **kwargs: Additional parameters for API call (model, temperature, max_tokens)

    Returns:
        Generated output from ENGINEER role

    Raises:
        LLMRoleError: If API call fails
    """
    logger.info("ENGINEER role called with prompt: %s", prompt[:100])

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        logger.info("ENGINEER role using test mode - returning mock response")
        return "ENGINEER test mode: This is a stubbed response for prompt engineering."

    # Build system prompt
    system_prompt = """You are an expert prompt engineer. Your role is to:
- Design macro chains and workflows
- Construct prompts with proper structure
- Inject constraints and requirements
- Build solutions from specifications

Be concise, structured, and follow best practices."""

    # Add context if provided
    if context:
        system_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=float(kwargs.get("temperature", os.environ.get("OPENAI_TEMPERATURE", "0.7"))),
            max_tokens=int(kwargs.get("max_tokens", os.environ.get("OPENAI_MAX_TOKENS", "2048"))),
        )
        result = response.choices[0].message.content
        logger.info("ENGINEER role completed successfully")
        return result
    except Exception as e:
        logger.error("ENGINEER role failed: %s", e)
        raise LLMRoleError(f"ENGINEER role execution failed: {e}")


def run_validator_role(
    prompt: str,
    output_to_validate: str,
    validation_criteria: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """
    Execute the VALIDATOR role.

    The VALIDATOR role is responsible for:
    - Checking outputs against requirements
    - Validating structure and schema conformance
    - Verifying format and completeness
    - Returning review narrative or structured JSON

    Args:
        prompt: Validation instructions
        output_to_validate: The output to validate
        validation_criteria: Optional criteria dictionary
        **kwargs: Additional parameters (model, temperature, max_tokens)

    Returns:
        Validation result (JSON string with valid, score, issues, recommendations)

    Raises:
        LLMRoleError: If API call fails
    """
    logger.info("VALIDATOR role called for output validation")
    logger.debug("Output length: %d chars", len(output_to_validate))

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        logger.info("VALIDATOR role using test mode - returning mock response")
        return json.dumps({
            "valid": True,
            "score": 0.85,
            "issues": [],
            "recommendations": ["Test mode validation"]
        })

    # Build system prompt
    system_prompt = """You are a validation expert. Review outputs against requirements.

Return JSON with this exact structure:
{
    "valid": true/false,
    "score": 0.0-1.0,
    "issues": ["list", "of", "issues"],
    "recommendations": ["list", "of", "recommendations"]
}"""

    # Add validation criteria if provided
    if validation_criteria:
        system_prompt += f"\n\nValidation Criteria:\n{json.dumps(validation_criteria, indent=2)}"

    # Build user message
    user_message = f"{prompt}\n\nOutput to validate:\n{output_to_validate}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=float(kwargs.get("temperature", "0.3")),  # Lower temp for validation
            max_tokens=int(kwargs.get("max_tokens", "1024")),
        )
        result = response.choices[0].message.content
        logger.info("VALIDATOR role completed successfully")
        return result
    except Exception as e:
        logger.error("VALIDATOR role failed: %s", e)
        raise LLMRoleError(f"VALIDATOR role execution failed: {e}")


def run_scorer_role(
    prompt: str,
    output_to_score: str,
    scoring_model: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """
    Execute the SCORER role for LLM-based quality scoring.

    The SCORER role is responsible for:
    - Evaluating output quality
    - Assigning numeric scores
    - Providing detailed feedback
    - Using PromptScoreModel metrics

    Args:
        prompt: Scoring instructions
        output_to_score: The output to score
        scoring_model: Optional PromptScoreModel.json dict
        **kwargs: Additional parameters (model, temperature, max_tokens)

    Returns:
        Scoring result (JSON string with overall_score, metrics, feedback)

    Raises:
        LLMRoleError: If API call fails
    """
    logger.info("SCORER role called for quality scoring")
    logger.debug("Output length: %d chars", len(output_to_score))

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        logger.info("SCORER role using test mode - returning mock response")
        return json.dumps({
            "overall_score": 0.85,
            "metrics": {
                "semantic_relevance": 0.9,
                "syntactic_correctness": 0.8,
                "completeness": 0.85
            },
            "feedback": "Test mode scoring - output appears valid"
        })

    # Build system prompt
    system_prompt = """You are a quality scorer. Evaluate outputs using the provided metrics.

Return JSON with this exact structure:
{
    "overall_score": 0.0-1.0,
    "metrics": {
        "metric_name": 0.0-1.0,
        ...
    },
    "feedback": "Detailed feedback explaining the scores"
}"""

    # Add scoring model metrics if provided
    if scoring_model and "metrics" in scoring_model:
        metrics_desc = "\n\nScoring Metrics:\n"
        for metric in scoring_model["metrics"]:
            metrics_desc += f"- {metric['name']}: {metric.get('description', '')}\n"
        system_prompt += metrics_desc

    # Build user message
    user_message = f"{prompt}\n\nOutput to score:\n{output_to_score}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=float(kwargs.get("temperature", "0.3")),  # Lower temp for scoring
            max_tokens=int(kwargs.get("max_tokens", "1024")),
        )
        result = response.choices[0].message.content
        logger.info("SCORER role completed successfully")
        return result
    except Exception as e:
        logger.error("SCORER role failed: %s", e)
        raise LLMRoleError(f"SCORER role execution failed: {e}")


def run_challenger_role(
    prompt: str,
    output_to_challenge: str,
    **kwargs: Any
) -> str:
    """
    Execute the CHALLENGER role for adversarial testing.

    The CHALLENGER role is responsible for:
    - Stress-testing logic and outputs
    - Identifying flaws and edge cases
    - Triggering fallback on critical issues
    - Providing adversarial feedback

    Args:
        prompt: Challenge instructions
        output_to_challenge: The output to challenge
        **kwargs: Additional parameters (model, temperature, max_tokens)

    Returns:
        Challenge result (JSON string with critical_issues, warnings, stress_test_results)

    Raises:
        LLMRoleError: If API call fails
    """
    logger.info("CHALLENGER role called for adversarial testing")

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        logger.info("CHALLENGER role using test mode - returning mock response")
        return json.dumps({
            "critical_issues": [],
            "warnings": ["Test mode - no real adversarial testing performed"],
            "stress_test_results": {"test_coverage": "limited"}
        })

    # Build system prompt
    system_prompt = """You are an adversarial tester. Stress-test logic and identify flaws.

Return JSON with this exact structure:
{
    "critical_issues": ["list", "of", "critical", "issues"],
    "warnings": ["list", "of", "warnings"],
    "stress_test_results": {
        "test_type": "result",
        ...
    }
}

Be thorough and critical. Look for edge cases, logical flaws, and potential failures."""

    # Build user message
    user_message = f"{prompt}\n\nOutput to challenge:\n{output_to_challenge}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=float(kwargs.get("temperature", "0.8")),  # Higher temp for creativity
            max_tokens=int(kwargs.get("max_tokens", "1024")),
        )
        result = response.choices[0].message.content
        logger.info("CHALLENGER role completed successfully")
        return result
    except Exception as e:
        logger.error("CHALLENGER role failed: %s", e)
        raise LLMRoleError(f"CHALLENGER role execution failed: {e}")


def run_logger_role(
    event: str,
    details: Dict[str, Any],
    **kwargs: Any
) -> str:
    """
    Execute the LOGGER role for audit logging.

    The LOGGER role is responsible for:
    - Auditing file changes and mutations
    - Recording scoring logs
    - Tracking operations and events
    - Maintaining compliance records

    Args:
        event: Event type or name
        details: Event details dictionary
        **kwargs: Additional parameters

    Returns:
        Log entry (JSON string with timestamp, event, summary, details)

    Raises:
        LLMRoleError: If API call fails

    Note: Uses structured logging with optional LLM summarization
    """
    logger.info("LOGGER role called for event: %s", event)

    client = _get_openai_client()

    # Test mode or direct logging (no LLM needed for simple logs)
    if client is None or kwargs.get("use_llm", False) is False:
        logger.info("LOGGER role using structured logging only")
        import datetime
        return json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "event": event,
            "summary": f"Event '{event}' logged",
            "details": details
        })

    # Use LLM for complex log summarization
    system_prompt = """You are an audit logger. Summarize events for compliance tracking.

Return JSON with this exact structure:
{
    "timestamp": "ISO-8601 timestamp",
    "event": "event_name",
    "summary": "Brief human-readable summary",
    "details": {...}
}"""

    user_message = f"Event: {event}\n\nDetails:\n{json.dumps(details, indent=2)}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=float(kwargs.get("temperature", "0.3")),
            max_tokens=int(kwargs.get("max_tokens", "512")),
        )
        result = response.choices[0].message.content
        logger.info("LOGGER role completed successfully")
        return result
    except Exception as e:
        logger.error("LOGGER role failed: %s", e)
        raise LLMRoleError(f"LOGGER role execution failed: {e}")


def run_tester_role(
    prompt: str,
    code_or_output: str,
    test_requirements: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """
    Execute the TESTER role for test generation and execution.

    The TESTER role is responsible for:
    - Generating regression tests
    - Creating edge case tests
    - Running test suites
    - Reporting test results

    Args:
        prompt: Testing instructions
        code_or_output: Code or output to test
        test_requirements: Optional test specifications
        **kwargs: Additional parameters (model, temperature, max_tokens)

    Returns:
        Test results or generated tests (JSON string)

    Raises:
        LLMRoleError: If API call fails
    """
    logger.info("TESTER role called for test generation/execution")

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        logger.info("TESTER role using test mode - returning mock response")
        return json.dumps({
            "test_cases": [
                {"name": "test_basic", "type": "unit", "status": "generated"}
            ],
            "coverage": "limited",
            "recommendations": ["Add integration tests in production mode"]
        })

    # Build system prompt
    system_prompt = """You are a test engineer. Generate comprehensive test cases.

Return JSON with this exact structure:
{
    "test_cases": [
        {
            "name": "test_name",
            "type": "unit|integration|edge",
            "description": "what it tests",
            "code": "test code (optional)"
        }
    ],
    "coverage": "assessment of test coverage",
    "recommendations": ["list", "of", "recommendations"]
}

Focus on edge cases, error conditions, and regression scenarios."""

    # Add test requirements if provided
    if test_requirements:
        system_prompt += f"\n\nTest Requirements:\n{json.dumps(test_requirements, indent=2)}"

    # Build user message
    user_message = f"{prompt}\n\nCode/Output to test:\n{code_or_output}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=float(kwargs.get("temperature", "0.7")),
            max_tokens=int(kwargs.get("max_tokens", "2048")),
        )
        result = response.choices[0].message.content
        logger.info("TESTER role completed successfully")
        return result
    except Exception as e:
        logger.error("TESTER role failed: %s", e)
        raise LLMRoleError(f"TESTER role execution failed: {e}")


# Export all role functions
__all__ = [
    "LLMRoleError",
    "run_engineer_role",
    "run_validator_role",
    "run_scorer_role",
    "run_challenger_role",
    "run_logger_role",
    "run_tester_role",
]
