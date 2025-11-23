"""
Enterprise-grade error handling for APEG.

Provides:
- PEGError: Base exception for all APEG errors
- APIError: Exception for external API errors
- safe_api_call: Decorator for safe API calls with error wrapping
- safe: Alias for safe_api_call (concise usage)

Usage:
    from apeg_core.utils.errors import safe, PEGError

    class MyAgent:
        @safe
        def list_items(self):
            return api.get("/items")

        @safe
        async def async_operation(self):
            return await api.async_get("/items")
"""

from __future__ import annotations

import asyncio
import functools
import logging
import traceback
from typing import Any, Callable, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Type variable for preserving function signatures
F = TypeVar("F", bound=Callable[..., Any])


class PEGError(Exception):
    """
    Base exception for all PEG-related errors.

    Attributes:
        message: Human-readable error message
        original: Original exception that caused this error
        context: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        original: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.original = original
        self.context = context or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.original:
            parts.append(f"(caused by {type(self.original).__name__}: {self.original})")
        return " ".join(parts)

    def to_dict(self) -> dict:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.message,
            "type": type(self).__name__,
            "original_error": str(self.original) if self.original else None,
            "trace": traceback.format_exc()[:500] if self.original else None,
            "context": self.context,
        }


class APIError(PEGError):
    """
    Exception for external API errors.

    Attributes:
        status_code: HTTP status code (if applicable)
        service: Name of the service that failed
        endpoint: API endpoint that failed
    """

    def __init__(
        self,
        message: str,
        original: Optional[Exception] = None,
        status_code: Optional[int] = None,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        super().__init__(message, original)
        self.status_code = status_code
        self.service = service
        self.endpoint = endpoint
        self.context.update({
            "status_code": status_code,
            "service": service,
            "endpoint": endpoint,
        })


class ConfigurationError(PEGError):
    """Exception for configuration errors."""
    pass


class AuthenticationError(PEGError):
    """Exception for authentication/authorization errors."""
    pass


class RateLimitError(APIError):
    """Exception for rate limiting errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.context["retry_after"] = retry_after


def safe_api_call(func: F) -> F:
    """
    Decorator for safe API calls with automatic error wrapping.

    Catches all exceptions and wraps them in PEGError for consistent
    error handling. Works with both sync and async functions.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that catches and wraps exceptions

    Usage:
        @safe_api_call
        def my_api_function():
            return requests.get(url)

        @safe_api_call
        async def my_async_function():
            return await aiohttp.get(url)
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except PEGError:
                # Re-raise PEG errors as-is
                raise
            except Exception as e:
                func_name = getattr(func, "__name__", "unknown")
                logger.error(
                    "API call failed in %s: %s: %s",
                    func_name,
                    type(e).__name__,
                    str(e),
                )
                raise APIError(
                    f"API call failed: {type(e).__name__}: {e}",
                    original=e,
                ) from e

        return async_wrapper  # type: ignore
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PEGError:
                # Re-raise PEG errors as-is
                raise
            except Exception as e:
                func_name = getattr(func, "__name__", "unknown")
                logger.error(
                    "API call failed in %s: %s: %s",
                    func_name,
                    type(e).__name__,
                    str(e),
                )
                raise APIError(
                    f"API call failed: {type(e).__name__}: {e}",
                    original=e,
                ) from e

        return sync_wrapper  # type: ignore


# Alias for concise usage
safe = safe_api_call


def handle_api_error(
    error: Exception,
    service: str = "unknown",
    endpoint: str = "",
) -> APIError:
    """
    Convert any exception to an APIError with context.

    Args:
        error: Original exception
        service: Name of the service
        endpoint: API endpoint

    Returns:
        APIError with proper context
    """
    if isinstance(error, APIError):
        return error

    if isinstance(error, PEGError):
        return APIError(
            message=error.message,
            original=error.original,
            service=service,
            endpoint=endpoint,
        )

    return APIError(
        message=str(error),
        original=error,
        service=service,
        endpoint=endpoint,
    )


__all__ = [
    "PEGError",
    "APIError",
    "ConfigurationError",
    "AuthenticationError",
    "RateLimitError",
    "safe_api_call",
    "safe",
    "handle_api_error",
]
