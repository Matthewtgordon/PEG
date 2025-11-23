"""
APEG Security Module - Enterprise security features.

This module provides:
- Audit logging for MCP compliance
- JWT authentication and RBAC
- Input validation and sanitization
- Encrypted key management
- Rate limiting utilities
"""

from apeg_core.security.audit import AuditLogger, get_audit_logger
from apeg_core.security.auth import (
    JWTAuthenticator,
    RBACManager,
    create_access_token,
    verify_token,
    require_role,
)
from apeg_core.security.input_validation import (
    InputValidator,
    SafePrompt,
    sanitize_input,
    validate_workflow_goal,
)
from apeg_core.security.key_management import (
    KeyManager,
    encrypt_api_key,
    decrypt_api_key,
)

__all__ = [
    # Audit
    "AuditLogger",
    "get_audit_logger",
    # Auth
    "JWTAuthenticator",
    "RBACManager",
    "create_access_token",
    "verify_token",
    "require_role",
    # Input validation
    "InputValidator",
    "SafePrompt",
    "sanitize_input",
    "validate_workflow_goal",
    # Key management
    "KeyManager",
    "encrypt_api_key",
    "decrypt_api_key",
]
