"""
Input Validation and Sanitization for APEG.

Provides:
- Prompt injection detection
- Input sanitization
- Safe prompt models
- XSS/injection prevention
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class SafePrompt(BaseModel):
    """
    Validated and sanitized prompt model.

    Provides protection against:
    - Prompt injection attacks
    - Script injection
    - Excessive length (DoS)
    - Control character injection
    """

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Sanitized prompt text",
    )

    @field_validator("prompt", mode="before")
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        """
        Sanitize and validate prompt input.

        Args:
            v: Raw prompt string

        Returns:
            Sanitized prompt

        Raises:
            ValueError: If prompt contains dangerous patterns
        """
        if not isinstance(v, str):
            v = str(v)

        # Strip leading/trailing whitespace
        v = v.strip()

        if not v:
            raise ValueError("Prompt cannot be empty")

        # Check for script/code injection patterns
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"on\w+\s*=",  # Event handlers like onclick=
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"subprocess\.",
            r"os\.system",
            r"\{\{.*\}\}",  # Template injection
            r"\$\{.*\}",    # Template literal injection
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                logger.warning("Dangerous pattern detected in prompt: %s", pattern)
                raise ValueError(f"Invalid prompt: contains forbidden pattern")

        # Remove control characters (except newlines and tabs)
        v = "".join(
            char for char in v
            if char in "\n\t" or (ord(char) >= 32 and ord(char) != 127)
        )

        # Truncate to max length
        if len(v) > 10000:
            v = v[:10000]
            logger.info("Prompt truncated to 10000 characters")

        return v


class InputValidator:
    """
    Comprehensive input validation utility.

    Provides validation methods for various input types
    used throughout APEG.
    """

    # Allowed characters in identifiers
    IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]{0,63}$")

    # Allowed characters in file paths (relative, no traversal)
    SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_./\-]+$")

    # Email pattern (simplified)
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @classmethod
    def validate_identifier(cls, value: str, field_name: str = "identifier") -> str:
        """
        Validate an identifier (workflow name, macro name, etc.).

        Args:
            value: Identifier to validate
            field_name: Name for error messages

        Returns:
            Validated identifier

        Raises:
            ValueError: If identifier is invalid
        """
        if not value:
            raise ValueError(f"{field_name} cannot be empty")

        if not cls.IDENTIFIER_PATTERN.match(value):
            raise ValueError(
                f"{field_name} must start with a letter or underscore, "
                f"contain only alphanumeric characters, underscores, and hyphens, "
                f"and be 1-64 characters long"
            )

        return value

    @classmethod
    def validate_file_path(cls, path: str, field_name: str = "path") -> str:
        """
        Validate a file path (prevent path traversal).

        Args:
            path: File path to validate
            field_name: Name for error messages

        Returns:
            Validated path

        Raises:
            ValueError: If path contains traversal or invalid characters
        """
        if not path:
            raise ValueError(f"{field_name} cannot be empty")

        # Check for path traversal attempts
        if ".." in path or path.startswith("/"):
            raise ValueError(f"{field_name} cannot contain path traversal sequences")

        if not cls.SAFE_PATH_PATTERN.match(path):
            raise ValueError(f"{field_name} contains invalid characters")

        return path

    @classmethod
    def validate_url(cls, url: str, allowed_schemes: List[str] = None) -> str:
        """
        Validate a URL.

        Args:
            url: URL to validate
            allowed_schemes: Allowed URL schemes (default: https)

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is invalid
        """
        allowed_schemes = allowed_schemes or ["https"]

        if not url:
            raise ValueError("URL cannot be empty")

        # Basic URL validation
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("Invalid URL format")

        if not parsed.scheme or not parsed.netloc:
            raise ValueError("URL must have scheme and host")

        if parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(f"URL scheme must be one of: {allowed_schemes}")

        return url

    @classmethod
    def validate_email(cls, email: str) -> str:
        """
        Validate an email address.

        Args:
            email: Email to validate

        Returns:
            Validated email

        Raises:
            ValueError: If email is invalid
        """
        if not email:
            raise ValueError("Email cannot be empty")

        email = email.strip().lower()

        if not cls.EMAIL_PATTERN.match(email):
            raise ValueError("Invalid email format")

        return email

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        Sanitize HTML entities in text.

        Args:
            text: Text to sanitize

        Returns:
            HTML-escaped text
        """
        return html.escape(text)

    @classmethod
    def sanitize_for_json(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a dictionary for safe JSON serialization.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        def sanitize_value(v: Any) -> Any:
            if isinstance(v, str):
                # Remove null bytes and control characters
                return "".join(c for c in v if ord(c) >= 32 or c in "\n\t")
            elif isinstance(v, dict):
                return {k: sanitize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [sanitize_value(item) for item in v]
            return v

        return sanitize_value(data)


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Convenience function to sanitize text input.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove other control characters except whitespace
    text = "".join(
        char for char in text
        if char in "\n\t\r " or (ord(char) >= 32 and ord(char) != 127)
    )

    # Truncate
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def validate_workflow_goal(goal: str) -> str:
    """
    Validate a workflow goal string.

    Args:
        goal: Workflow goal to validate

    Returns:
        Validated goal

    Raises:
        ValueError: If goal is invalid
    """
    safe_prompt = SafePrompt(prompt=goal)
    return safe_prompt.prompt


__all__ = [
    "SafePrompt",
    "InputValidator",
    "sanitize_input",
    "validate_workflow_goal",
]
