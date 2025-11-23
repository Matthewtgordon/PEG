"""
APEG Utilities - Common utilities and helper functions.

Components:
- errors: Error handling decorators and exception classes
"""

from .errors import (
    PEGError,
    APIError,
    safe_api_call,
    safe,
)

__all__ = [
    "PEGError",
    "APIError",
    "safe_api_call",
    "safe",
]
