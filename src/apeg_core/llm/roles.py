"""
APEG LLM Role Definitions - Constants and configurations for agent roles.

This module defines the available LLM roles used throughout APEG workflows.
Each role has specific responsibilities and can be configured with different
models, temperatures, and system prompts.

Roles:
- ENGINEER: Designs prompts, workflows, and macro chains
- VALIDATOR: Validates outputs against requirements and schemas
- SCORER: Evaluates quality and assigns numeric scores
- CHALLENGER: Stress-tests logic and identifies flaws
- LOGGER: Audits operations and maintains compliance records
- TESTER: Generates and runs test cases
- TRANSLATOR: Converts between formats and languages
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class LLMRole(str, Enum):
    """
    Enumeration of available LLM agent roles.

    Each role corresponds to a specific agent function in the APEG workflow.
    """
    ENGINEER = "ENGINEER"
    VALIDATOR = "VALIDATOR"
    SCORER = "SCORER"
    CHALLENGER = "CHALLENGER"
    LOGGER = "LOGGER"
    TESTER = "TESTER"
    TRANSLATOR = "TRANSLATOR"
    PEG = "PEG"  # Master orchestrator role

    def __str__(self) -> str:
        return self.value


@dataclass
class RoleConfig:
    """
    Configuration for an LLM role.

    Attributes:
        name: Role identifier
        description: Human-readable description of the role
        system_prompt: Default system prompt for the role
        model: Preferred model (e.g., "gpt-4", "gpt-4-turbo")
        temperature: Generation temperature (0.0-1.0)
        max_tokens: Maximum response tokens
        response_format: Expected response format ("text" or "json")
        metadata: Additional role-specific configuration
    """
    name: str
    description: str
    system_prompt: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048
    response_format: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": self.response_format,
            "metadata": self.metadata,
        }


# Default role configurations
ROLE_CONFIGS: Dict[LLMRole, RoleConfig] = {
    LLMRole.ENGINEER: RoleConfig(
        name="ENGINEER",
        description="Designs prompts, workflows, and macro chains",
        system_prompt="""You are an expert prompt engineer. Your role is to:
- Design macro chains and workflows for complex tasks
- Construct prompts with proper structure and constraints
- Inject requirements and guidelines effectively
- Build solutions from specifications

Be concise, structured, and follow best practices for prompt engineering.
Always explain your reasoning when designing complex workflows.""",
        model="gpt-4",
        temperature=0.7,
        max_tokens=2048,
        response_format="text",
    ),

    LLMRole.VALIDATOR: RoleConfig(
        name="VALIDATOR",
        description="Validates outputs against requirements and schemas",
        system_prompt="""You are a validation expert. Your role is to:
- Check outputs against requirements and specifications
- Validate structure, schema conformance, and format
- Verify completeness and accuracy
- Return structured validation results

Return JSON with this structure:
{
    "valid": true/false,
    "score": 0.0-1.0,
    "issues": ["list of issues found"],
    "recommendations": ["list of recommendations"]
}""",
        model="gpt-4",
        temperature=0.3,
        max_tokens=1024,
        response_format="json",
    ),

    LLMRole.SCORER: RoleConfig(
        name="SCORER",
        description="Evaluates quality and assigns numeric scores",
        system_prompt="""You are a quality scorer. Your role is to:
- Evaluate output quality using defined metrics
- Assign numeric scores (0.0-1.0) for each metric
- Provide detailed feedback explaining scores
- Consider context and requirements

Return JSON with this structure:
{
    "overall_score": 0.0-1.0,
    "metrics": {
        "metric_name": 0.0-1.0
    },
    "feedback": "Detailed feedback explaining scores"
}""",
        model="gpt-4",
        temperature=0.3,
        max_tokens=1024,
        response_format="json",
    ),

    LLMRole.CHALLENGER: RoleConfig(
        name="CHALLENGER",
        description="Stress-tests logic and identifies flaws",
        system_prompt="""You are an adversarial tester. Your role is to:
- Stress-test logic and identify potential flaws
- Find edge cases and failure scenarios
- Challenge assumptions and identify risks
- Provide constructive criticism

Return JSON with this structure:
{
    "critical_issues": ["list of critical issues"],
    "warnings": ["list of warnings"],
    "edge_cases": ["potential edge cases"],
    "stress_test_results": {"test_name": "result"}
}

Be thorough and critical. Look for logical flaws, edge cases, and potential failures.""",
        model="gpt-4",
        temperature=0.8,
        max_tokens=1024,
        response_format="json",
    ),

    LLMRole.LOGGER: RoleConfig(
        name="LOGGER",
        description="Audits operations and maintains compliance records",
        system_prompt="""You are an audit logger. Your role is to:
- Summarize events for compliance tracking
- Maintain accurate operation records
- Ensure audit trail completeness
- Generate human-readable summaries

Return JSON with this structure:
{
    "timestamp": "ISO-8601 timestamp",
    "event": "event_name",
    "summary": "Brief human-readable summary",
    "details": {...}
}""",
        model="gpt-4",
        temperature=0.3,
        max_tokens=512,
        response_format="json",
    ),

    LLMRole.TESTER: RoleConfig(
        name="TESTER",
        description="Generates and runs test cases",
        system_prompt="""You are a test engineer. Your role is to:
- Generate comprehensive test cases
- Cover edge cases and error conditions
- Create regression test scenarios
- Ensure adequate test coverage

Return JSON with this structure:
{
    "test_cases": [
        {
            "name": "test_name",
            "type": "unit|integration|edge",
            "description": "what it tests",
            "expected_result": "expected outcome"
        }
    ],
    "coverage": "assessment of test coverage",
    "recommendations": ["list of recommendations"]
}

Focus on edge cases, error conditions, and regression scenarios.""",
        model="gpt-4",
        temperature=0.7,
        max_tokens=2048,
        response_format="json",
    ),

    LLMRole.TRANSLATOR: RoleConfig(
        name="TRANSLATOR",
        description="Converts between formats and languages",
        system_prompt="""You are a translation expert. Your role is to:
- Convert content between different formats
- Translate technical documentation
- Maintain semantic accuracy
- Preserve structure and meaning

Provide accurate translations while maintaining the original intent and structure.""",
        model="gpt-4",
        temperature=0.5,
        max_tokens=4096,
        response_format="text",
    ),

    LLMRole.PEG: RoleConfig(
        name="PEG",
        description="Master orchestrator for workflow management",
        system_prompt="""You are the PEG orchestrator. Your role is to:
- Manage workflow execution and state
- Coordinate between agent roles
- Handle fallback strategies
- Ensure workflow completion

Make decisions about workflow routing and escalation based on context.""",
        model="gpt-4",
        temperature=0.5,
        max_tokens=1024,
        response_format="text",
    ),
}


def get_role_config(role: LLMRole | str) -> RoleConfig:
    """
    Get configuration for a specific role.

    Args:
        role: Role enum or string name

    Returns:
        RoleConfig for the specified role

    Raises:
        ValueError: If role is not found
    """
    if isinstance(role, str):
        try:
            role = LLMRole(role.upper())
        except ValueError:
            raise ValueError(f"Unknown role: {role}")

    if role not in ROLE_CONFIGS:
        raise ValueError(f"No configuration found for role: {role}")

    return ROLE_CONFIGS[role]


def list_roles() -> list[str]:
    """
    Get list of all available role names.

    Returns:
        List of role name strings
    """
    return [role.value for role in LLMRole]


__all__ = [
    "LLMRole",
    "RoleConfig",
    "ROLE_CONFIGS",
    "get_role_config",
    "list_roles",
]
