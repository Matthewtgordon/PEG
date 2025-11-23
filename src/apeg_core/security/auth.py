"""
JWT Authentication and RBAC for APEG API.

Provides:
- JWT token creation and verification
- Role-based access control (RBAC)
- FastAPI security dependencies
- Token refresh mechanisms
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload model."""
    sub: str  # Subject (user ID)
    roles: List[str]  # User roles
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: Optional[str] = None  # JWT ID for revocation


class JWTAuthenticator:
    """
    Simple JWT authenticator using HMAC-SHA256.

    Note: For production, consider using python-jose or PyJWT with
    proper key management. This implementation provides basic JWT
    functionality without external dependencies.

    Attributes:
        secret_key: Secret key for signing tokens
        algorithm: Signing algorithm (HS256)
        access_token_expire_minutes: Token lifetime
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        access_token_expire_minutes: int = 60,
    ):
        """
        Initialize JWT authenticator.

        Args:
            secret_key: Secret key for signing (default: from env)
            access_token_expire_minutes: Token lifetime in minutes
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET", "apeg-dev-secret-change-in-prod")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = access_token_expire_minutes

        # Warn if using default secret
        if self.secret_key == "apeg-dev-secret-change-in-prod":
            logger.warning(
                "Using default JWT secret! Set JWT_SECRET environment variable in production."
            )

    def create_access_token(
        self,
        user_id: str,
        roles: List[str],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User identifier
            roles: List of user roles
            expires_delta: Custom expiration (default: access_token_expire_minutes)

        Returns:
            JWT token string
        """
        now = int(time.time())

        if expires_delta:
            expire = now + int(expires_delta.total_seconds())
        else:
            expire = now + (self.access_token_expire_minutes * 60)

        payload = {
            "sub": user_id,
            "roles": roles,
            "exp": expire,
            "iat": now,
            "jti": hashlib.sha256(f"{user_id}:{now}".encode()).hexdigest()[:16],
        }

        return self._encode(payload)

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            payload = self._decode(token)

            if not payload:
                return None

            # Check expiration
            if payload.get("exp", 0) < int(time.time()):
                logger.debug("Token expired")
                return None

            return TokenPayload(**payload)

        except Exception as e:
            logger.debug("Token verification failed: %s", e)
            return None

    def _encode(self, payload: Dict[str, Any]) -> str:
        """
        Encode payload to JWT token.

        Args:
            payload: Token payload

        Returns:
            JWT token string
        """
        # Header
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_b64 = urlsafe_b64encode(
            json.dumps(header, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

        # Payload
        payload_b64 = urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

        # Signature
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = urlsafe_b64encode(signature).rstrip(b"=").decode()

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _decode(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Payload dict if signature valid, None otherwise
        """
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()

        # Pad and decode signature
        signature_b64_padded = signature_b64 + "=" * (4 - len(signature_b64) % 4)
        try:
            actual_sig = urlsafe_b64decode(signature_b64_padded)
        except Exception:
            return None

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        try:
            payload = json.loads(urlsafe_b64decode(payload_b64_padded))
            return payload
        except Exception:
            return None


class RBACManager:
    """
    Role-Based Access Control manager.

    Defines roles and their permissions for APEG operations.

    Attributes:
        role_permissions: Mapping of roles to permitted operations
    """

    # Default role permissions
    DEFAULT_PERMISSIONS = {
        "admin": {
            "run_workflow", "view_logs", "manage_keys", "manage_users",
            "view_metrics", "configure_system", "export_data",
        },
        "operator": {
            "run_workflow", "view_logs", "view_metrics", "export_data",
        },
        "user": {
            "run_workflow", "view_logs",
        },
        "readonly": {
            "view_logs", "view_metrics",
        },
    }

    def __init__(
        self,
        permissions: Optional[Dict[str, Set[str]]] = None,
    ):
        """
        Initialize RBAC manager.

        Args:
            permissions: Custom role-permission mapping
        """
        self.role_permissions = permissions or self.DEFAULT_PERMISSIONS.copy()

    def has_permission(
        self,
        roles: List[str],
        permission: str,
    ) -> bool:
        """
        Check if any of the roles has the required permission.

        Args:
            roles: User's roles
            permission: Required permission

        Returns:
            True if permission granted
        """
        for role in roles:
            perms = self.role_permissions.get(role, set())
            if permission in perms:
                return True
        return False

    def get_permissions(self, roles: List[str]) -> Set[str]:
        """
        Get all permissions for a set of roles.

        Args:
            roles: User's roles

        Returns:
            Set of all permissions
        """
        permissions: Set[str] = set()
        for role in roles:
            permissions.update(self.role_permissions.get(role, set()))
        return permissions

    def add_role(self, role: str, permissions: Set[str]) -> None:
        """
        Add or update a role.

        Args:
            role: Role name
            permissions: Set of permissions
        """
        self.role_permissions[role] = permissions

    def remove_role(self, role: str) -> None:
        """
        Remove a role.

        Args:
            role: Role name to remove
        """
        self.role_permissions.pop(role, None)


# Global instances
_jwt_auth: Optional[JWTAuthenticator] = None
_rbac_manager: Optional[RBACManager] = None


def get_jwt_authenticator() -> JWTAuthenticator:
    """Get global JWT authenticator instance."""
    global _jwt_auth
    if _jwt_auth is None:
        _jwt_auth = JWTAuthenticator()
    return _jwt_auth


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager instance."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def create_access_token(
    user_id: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Convenience function to create access token.

    Args:
        user_id: User identifier
        roles: User roles
        expires_delta: Custom expiration

    Returns:
        JWT token string
    """
    return get_jwt_authenticator().create_access_token(user_id, roles, expires_delta)


def verify_token(token: str) -> Optional[TokenPayload]:
    """
    Convenience function to verify token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid
    """
    return get_jwt_authenticator().verify_token(token)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenPayload]:
    """
    FastAPI dependency to get current authenticated user.

    Args:
        credentials: HTTP Authorization header

    Returns:
        TokenPayload for authenticated user, None for anonymous
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    return payload


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """
    FastAPI dependency that requires authentication.

    Args:
        credentials: HTTP Authorization header

    Returns:
        TokenPayload for authenticated user

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def require_role(required_permission: str) -> Callable:
    """
    Factory for FastAPI dependency that requires a specific permission.

    Args:
        required_permission: Permission required to access endpoint

    Returns:
        FastAPI dependency function

    Example:
        @app.post("/admin/config", dependencies=[Depends(require_role("configure_system"))])
        async def update_config(...):
            ...
    """
    async def role_checker(
        user: TokenPayload = Depends(require_auth),
    ) -> TokenPayload:
        rbac = get_rbac_manager()

        if not rbac.has_permission(user.roles, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required",
            )

        return user

    return role_checker


__all__ = [
    "JWTAuthenticator",
    "RBACManager",
    "TokenPayload",
    "create_access_token",
    "verify_token",
    "get_current_user",
    "require_auth",
    "require_role",
    "get_jwt_authenticator",
    "get_rbac_manager",
]
