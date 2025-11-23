"""
MCP-Compliant Audit Logger for APEG.

Provides comprehensive audit logging for:
- Tool invocations (MCP compliance)
- Authentication events
- API access logs
- Security incidents

Features:
- Secret masking in logs
- Thread-safe operations
- JSONL format for log analysis
- Rotation support
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    MCP-compliant audit logger with secret masking.

    Implements audit trail requirements for:
    - Tool invocation visualization
    - Confused deputy attack prevention
    - Token validation logging
    - GDPR compliance

    Attributes:
        log_file: Path to audit log file (JSONL format)
        _lock: Thread lock for atomic writes
        sensitive_keys: Keys to mask in logs
    """

    # Keys containing sensitive data to mask
    SENSITIVE_KEYS = {
        "api_key", "access_token", "refresh_token", "secret", "password",
        "token", "key", "authorization", "bearer", "credential", "auth",
        "openai_api_key", "shopify_access_token", "etsy_api_key", "github_pat",
    }

    def __init__(
        self,
        log_file: str | Path = "audit.jsonl",
        test_mode: bool = False,
        max_param_length: int = 500,
    ):
        """
        Initialize the audit logger.

        Args:
            log_file: Path to audit log file
            test_mode: If True, store logs in memory
            max_param_length: Max length for parameter values in logs
        """
        self.log_file = Path(log_file)
        self.test_mode = test_mode
        self.max_param_length = max_param_length
        self._lock = Lock()
        self._in_memory_logs: List[Dict[str, Any]] = []

        # Ensure log directory exists
        if not test_mode:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("AuditLogger initialized (path=%s, test_mode=%s)", log_file, test_mode)

    def log_invocation(
        self,
        tool: str,
        user_id: str,
        params: Dict[str, Any],
        outcome: str,
        duration_ms: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log a tool invocation (MCP compliance).

        Args:
            tool: Tool/agent name being invoked
            user_id: Anonymized user identifier
            params: Tool parameters (sensitive values masked)
            outcome: Result status (success, failure, error)
            duration_ms: Execution duration in milliseconds
            session_id: Session identifier for correlation
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "tool_invocation",
            "tool": tool,
            "user_id": self._hash_user_id(user_id),
            "params": self._mask_sensitive(params),
            "outcome": outcome,
            "duration_ms": duration_ms,
            "session_id": session_id,
        }
        self._write_entry(entry)

    def log_auth_event(
        self,
        event: str,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an authentication event.

        Args:
            event: Event type (login, logout, token_refresh, etc.)
            user_id: User identifier
            success: Whether authentication succeeded
            ip_address: Client IP address (anonymized)
            details: Additional event details
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "authentication",
            "event": event,
            "user_id": self._hash_user_id(user_id),
            "success": success,
            "ip_address": self._anonymize_ip(ip_address) if ip_address else None,
            "details": self._mask_sensitive(details or {}),
        }
        self._write_entry(entry)

    def log_api_access(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str],
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log an API access event.

        Args:
            endpoint: API endpoint accessed
            method: HTTP method
            user_id: Authenticated user (if any)
            status_code: HTTP response status
            duration_ms: Request duration
            request_id: Unique request identifier
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "api_access",
            "endpoint": endpoint,
            "method": method,
            "user_id": self._hash_user_id(user_id) if user_id else None,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
        }
        self._write_entry(entry)

    def log_security_incident(
        self,
        incident_type: str,
        severity: str,
        description: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a security incident.

        Args:
            incident_type: Type of incident (rate_limit, auth_failure, injection_attempt)
            severity: Severity level (low, medium, high, critical)
            description: Human-readable description
            source_ip: Source IP address
            user_id: Associated user (if known)
            details: Additional incident details
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "security_incident",
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
            "source_ip": self._anonymize_ip(source_ip) if source_ip else None,
            "user_id": self._hash_user_id(user_id) if user_id else None,
            "details": self._mask_sensitive(details or {}),
        }
        self._write_entry(entry)

        # Also log to Python logger for immediate visibility
        log_level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }.get(severity, logging.WARNING)

        logger.log(log_level, "Security incident: %s - %s", incident_type, description)

    def get_recent_entries(
        self,
        n: int = 100,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit log entries.

        Args:
            n: Number of entries to retrieve
            event_type: Filter by event type (optional)

        Returns:
            List of audit log entries
        """
        if self.test_mode:
            entries = self._in_memory_logs
        else:
            entries = self._read_entries()

        if event_type:
            entries = [e for e in entries if e.get("event_type") == event_type]

        return entries[-n:]

    def _mask_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive values in a dictionary.

        Args:
            data: Dictionary to mask

        Returns:
            Dictionary with sensitive values masked
        """
        if not data:
            return {}

        masked = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if key contains sensitive terms
            is_sensitive = any(
                sensitive in key_lower
                for sensitive in self.SENSITIVE_KEYS
            )

            if is_sensitive and value:
                # Mask the value but show length hint
                if isinstance(value, str):
                    masked[key] = f"***MASKED({len(value)} chars)***"
                else:
                    masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                masked[key] = self._mask_sensitive(value)
            elif isinstance(value, str) and len(value) > self.max_param_length:
                # Truncate long values
                masked[key] = value[:self.max_param_length] + "...[truncated]"
            else:
                masked[key] = value

        return masked

    def _hash_user_id(self, user_id: str) -> str:
        """
        Create anonymized hash of user ID for GDPR compliance.

        Args:
            user_id: Original user identifier

        Returns:
            Hashed user identifier
        """
        if not user_id:
            return "anonymous"

        # Use SHA256 with a salt from environment
        salt = os.getenv("AUDIT_SALT", "apeg-audit-salt")
        return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]

    def _anonymize_ip(self, ip_address: str) -> str:
        """
        Anonymize IP address for GDPR compliance.

        Args:
            ip_address: Original IP address

        Returns:
            Anonymized IP address (last octet zeroed)
        """
        if not ip_address:
            return "unknown"

        parts = ip_address.split(".")
        if len(parts) == 4:
            # IPv4: Zero out last octet
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        elif ":" in ip_address:
            # IPv6: Keep only first 3 groups
            parts = ip_address.split(":")
            return ":".join(parts[:3]) + "::anonymized"

        return ip_address

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """
        Write an entry to the audit log atomically.

        Args:
            entry: Log entry to write
        """
        if self.test_mode:
            self._in_memory_logs.append(entry)
            return

        with self._lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except IOError as e:
                logger.error("Failed to write audit log: %s", e)

    def _read_entries(self) -> List[Dict[str, Any]]:
        """
        Read all entries from the audit log.

        Returns:
            List of log entries
        """
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except IOError as e:
            logger.error("Failed to read audit log: %s", e)

        return entries


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(
    log_file: str | Path = "audit.jsonl",
    test_mode: bool = False,
) -> AuditLogger:
    """
    Get or create global audit logger instance.

    Args:
        log_file: Path to audit log file
        test_mode: Use in-memory logging

    Returns:
        Global AuditLogger instance
    """
    global _global_audit_logger

    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger(log_file, test_mode)

    return _global_audit_logger


def reset_audit_logger() -> None:
    """Reset global audit logger instance (for testing)."""
    global _global_audit_logger
    _global_audit_logger = None


__all__ = ["AuditLogger", "get_audit_logger", "reset_audit_logger"]
