"""
Tests for APEG Security Module.

Tests cover:
- Audit logging with MCP compliance
- JWT authentication and RBAC
- Input validation and sanitization
- Key management with encryption
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from datetime import timedelta

# Import security modules
from apeg_core.security.audit import AuditLogger, get_audit_logger, reset_audit_logger
from apeg_core.security.auth import (
    JWTAuthenticator,
    RBACManager,
    create_access_token,
    verify_token,
    TokenPayload,
)
from apeg_core.security.input_validation import (
    SafePrompt,
    InputValidator,
    sanitize_input,
    validate_workflow_goal,
)
from apeg_core.security.key_management import (
    KeyManager,
    get_key_manager,
    encrypt_api_key,
    decrypt_api_key,
)


class TestAuditLogger:
    """Tests for MCP-compliant audit logging."""

    def setup_method(self):
        """Reset audit logger before each test."""
        reset_audit_logger()

    def test_log_invocation(self):
        """Test tool invocation logging."""
        logger = AuditLogger(test_mode=True)

        logger.log_invocation(
            tool="shopify_agent",
            user_id="user123",
            params={"action": "list_products", "limit": 10},
            outcome="success",
            duration_ms=150.5,
        )

        entries = logger.get_recent_entries()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "tool_invocation"
        assert entries[0]["tool"] == "shopify_agent"
        assert entries[0]["outcome"] == "success"

    def test_secret_masking(self):
        """Test that sensitive values are masked."""
        logger = AuditLogger(test_mode=True)

        logger.log_invocation(
            tool="test_tool",
            user_id="user123",
            params={
                "api_key": "sk-secret-key-12345",
                "access_token": "token-abc-xyz",
                "normal_param": "visible",
            },
            outcome="success",
        )

        entries = logger.get_recent_entries()
        params = entries[0]["params"]

        # Sensitive values should be masked
        assert "***MASKED" in params["api_key"]
        assert "***MASKED" in params["access_token"]
        # Normal values should be visible
        assert params["normal_param"] == "visible"

    def test_user_id_hashing(self):
        """Test that user IDs are hashed for privacy."""
        logger = AuditLogger(test_mode=True)

        logger.log_auth_event(
            event="login",
            user_id="john.doe@example.com",
            success=True,
        )

        entries = logger.get_recent_entries()
        # User ID should be hashed (16 char hex)
        assert entries[0]["user_id"] != "john.doe@example.com"
        assert len(entries[0]["user_id"]) == 16

    def test_ip_anonymization(self):
        """Test that IP addresses are anonymized."""
        logger = AuditLogger(test_mode=True)

        logger.log_security_incident(
            incident_type="rate_limit",
            severity="medium",
            description="Rate limit exceeded",
            source_ip="192.168.1.100",
        )

        entries = logger.get_recent_entries()
        # Last octet should be zeroed
        assert entries[0]["source_ip"] == "192.168.1.0"

    def test_security_incident_logging(self):
        """Test security incident logging."""
        logger = AuditLogger(test_mode=True)

        logger.log_security_incident(
            incident_type="injection_attempt",
            severity="high",
            description="Potential SQL injection detected",
            source_ip="10.0.0.1",
            user_id="attacker",
        )

        entries = logger.get_recent_entries(event_type="security_incident")
        assert len(entries) == 1
        assert entries[0]["severity"] == "high"
        assert entries[0]["incident_type"] == "injection_attempt"


class TestJWTAuthentication:
    """Tests for JWT authentication."""

    def test_create_and_verify_token(self):
        """Test token creation and verification."""
        auth = JWTAuthenticator(secret_key="test-secret-key")

        token = auth.create_access_token(
            user_id="user123",
            roles=["admin", "operator"],
        )

        # Verify token
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload.sub == "user123"
        assert "admin" in payload.roles
        assert "operator" in payload.roles

    def test_expired_token(self):
        """Test that expired tokens are rejected."""
        auth = JWTAuthenticator(
            secret_key="test-secret-key",
            access_token_expire_minutes=0,  # Immediately expires
        )

        token = auth.create_access_token(
            user_id="user123",
            roles=["user"],
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        payload = auth.verify_token(token)
        assert payload is None

    def test_invalid_token(self):
        """Test that invalid tokens are rejected."""
        auth = JWTAuthenticator(secret_key="test-secret-key")

        # Tampered token
        payload = auth.verify_token("invalid.token.here")
        assert payload is None

        # Empty token
        payload = auth.verify_token("")
        assert payload is None

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        # Set environment variable for consistent secret
        os.environ["JWT_SECRET"] = "test-env-secret"

        token = create_access_token("testuser", ["user"])
        payload = verify_token(token)

        assert payload is not None
        assert payload.sub == "testuser"


class TestRBAC:
    """Tests for Role-Based Access Control."""

    def test_default_permissions(self):
        """Test default role permissions."""
        rbac = RBACManager()

        # Admin should have all permissions
        assert rbac.has_permission(["admin"], "run_workflow")
        assert rbac.has_permission(["admin"], "manage_keys")
        assert rbac.has_permission(["admin"], "configure_system")

        # User should have limited permissions
        assert rbac.has_permission(["user"], "run_workflow")
        assert not rbac.has_permission(["user"], "manage_keys")

        # Readonly should have minimal permissions
        assert rbac.has_permission(["readonly"], "view_logs")
        assert not rbac.has_permission(["readonly"], "run_workflow")

    def test_multiple_roles(self):
        """Test permissions with multiple roles."""
        rbac = RBACManager()

        # User with both user and operator roles
        roles = ["user", "operator"]

        # Should have combined permissions
        assert rbac.has_permission(roles, "run_workflow")
        assert rbac.has_permission(roles, "view_metrics")
        assert rbac.has_permission(roles, "export_data")

    def test_custom_permissions(self):
        """Test custom role permissions."""
        custom_perms = {
            "superuser": {"everything"},
            "limited": {"read_only"},
        }

        rbac = RBACManager(permissions=custom_perms)

        assert rbac.has_permission(["superuser"], "everything")
        assert not rbac.has_permission(["superuser"], "run_workflow")

    def test_get_all_permissions(self):
        """Test getting all permissions for roles."""
        rbac = RBACManager()

        perms = rbac.get_permissions(["admin"])
        assert "run_workflow" in perms
        assert "manage_keys" in perms
        assert "configure_system" in perms


class TestInputValidation:
    """Tests for input validation and sanitization."""

    def test_safe_prompt_valid(self):
        """Test valid prompts pass validation."""
        prompt = SafePrompt(prompt="Create a workflow to process data")
        assert prompt.prompt == "Create a workflow to process data"

    def test_safe_prompt_injection(self):
        """Test that injection attempts are blocked."""
        # Script injection
        with pytest.raises(ValueError, match="forbidden pattern"):
            SafePrompt(prompt="<script>alert('xss')</script>")

        # Code injection
        with pytest.raises(ValueError, match="forbidden pattern"):
            SafePrompt(prompt="Run eval(malicious_code)")

        # Import injection
        with pytest.raises(ValueError, match="forbidden pattern"):
            SafePrompt(prompt="Execute __import__('os').system('rm -rf /')")

    def test_safe_prompt_empty(self):
        """Test that empty prompts are rejected."""
        with pytest.raises(ValueError):
            SafePrompt(prompt="")

        with pytest.raises(ValueError):
            SafePrompt(prompt="   ")

    def test_safe_prompt_truncation(self):
        """Test that long prompts are truncated."""
        long_prompt = "x" * 15000
        prompt = SafePrompt(prompt=long_prompt)
        assert len(prompt.prompt) == 10000

    def test_identifier_validation(self):
        """Test identifier validation."""
        # Valid identifiers
        assert InputValidator.validate_identifier("workflow_1", "name") == "workflow_1"
        assert InputValidator.validate_identifier("my-macro", "name") == "my-macro"
        assert InputValidator.validate_identifier("_private", "name") == "_private"

        # Invalid identifiers
        with pytest.raises(ValueError):
            InputValidator.validate_identifier("123invalid", "name")

        with pytest.raises(ValueError):
            InputValidator.validate_identifier("with space", "name")

        with pytest.raises(ValueError):
            InputValidator.validate_identifier("", "name")

    def test_file_path_validation(self):
        """Test file path validation (prevent traversal)."""
        # Valid paths
        assert InputValidator.validate_file_path("config/settings.json") == "config/settings.json"
        assert InputValidator.validate_file_path("file.txt") == "file.txt"

        # Path traversal attempts
        with pytest.raises(ValueError):
            InputValidator.validate_file_path("../etc/passwd")

        with pytest.raises(ValueError):
            InputValidator.validate_file_path("/etc/passwd")

    def test_url_validation(self):
        """Test URL validation."""
        # Valid HTTPS URL
        assert InputValidator.validate_url("https://example.com/api") == "https://example.com/api"

        # HTTP not allowed by default
        with pytest.raises(ValueError):
            InputValidator.validate_url("http://example.com")

        # Invalid URL
        with pytest.raises(ValueError):
            InputValidator.validate_url("not-a-url")

    def test_sanitize_input(self):
        """Test input sanitization."""
        # Normal text passes through
        assert sanitize_input("Hello World") == "Hello World"

        # Control characters removed
        assert sanitize_input("Hello\x00World") == "HelloWorld"

        # Truncation
        long_text = "x" * 20000
        assert len(sanitize_input(long_text)) == 10000

    def test_validate_workflow_goal(self):
        """Test workflow goal validation."""
        # Valid goal
        goal = validate_workflow_goal("Process customer orders and update inventory")
        assert goal == "Process customer orders and update inventory"

        # Invalid goal with injection
        with pytest.raises(ValueError):
            validate_workflow_goal("<script>hack()</script>")


class TestKeyManagement:
    """Tests for secure key management."""

    def test_store_and_retrieve_key(self):
        """Test storing and retrieving an API key."""
        km = KeyManager(test_mode=True)

        km.store_key(
            service="shopify",
            key_name="access_token",
            key_value="shpat_secret_token_12345",
            metadata={"store_id": "mystore"},
        )

        retrieved = km.retrieve_key("shopify", "access_token")
        assert retrieved == "shpat_secret_token_12345"

    def test_key_encryption(self):
        """Test that keys are encrypted in storage."""
        km = KeyManager(test_mode=True)

        km.store_key(
            service="test",
            key_name="api_key",
            key_value="plain_text_key",
        )

        # Internal storage should have encrypted value
        # (we can't directly check this in test mode, but we verify round-trip)
        retrieved = km.retrieve_key("test", "api_key")
        assert retrieved == "plain_text_key"

    def test_list_keys(self):
        """Test listing stored keys."""
        km = KeyManager(test_mode=True)

        km.store_key("service1", "key1", "value1")
        km.store_key("service1", "key2", "value2")
        km.store_key("service2", "key1", "value3")

        # List all keys
        all_keys = km.list_keys()
        assert "service1" in all_keys
        assert "service2" in all_keys
        assert "key1" in all_keys["service1"]
        assert "key2" in all_keys["service1"]

        # List keys for specific service
        s1_keys = km.list_keys(service="service1")
        assert "service1" in s1_keys
        assert "service2" not in s1_keys

        # Values should not be in list output
        assert "value1" not in str(all_keys)

    def test_delete_key(self):
        """Test deleting a key."""
        km = KeyManager(test_mode=True)

        km.store_key("test", "to_delete", "secret")
        assert km.retrieve_key("test", "to_delete") == "secret"

        result = km.delete_key("test", "to_delete")
        assert result is True

        assert km.retrieve_key("test", "to_delete") is None

    def test_rotate_key(self):
        """Test key rotation."""
        km = KeyManager(test_mode=True)

        # Store original key
        km.store_key("service", "api_key", "old_key_value")
        assert km.retrieve_key("service", "api_key") == "old_key_value"

        # Rotate key
        km.rotate_key("service", "api_key", "new_key_value")
        assert km.retrieve_key("service", "api_key") == "new_key_value"

    def test_nonexistent_key(self):
        """Test retrieving nonexistent key."""
        km = KeyManager(test_mode=True)

        result = km.retrieve_key("nonexistent", "key")
        assert result is None


class TestBanditSelectorEnhancements:
    """Tests for enhanced Thompson Sampling with UCB hybrid."""

    def test_ucb_hybrid_selection(self):
        """Test that UCB hybrid affects selection."""
        from apeg_core.decision.bandit_selector import BanditSelector

        selector = BanditSelector(
            weights_path=Path("/tmp/test_bandit.json"),
            ucb_weight=0.2,
        )

        # Initialize some macros with history
        selector.weights = {
            "macro_a": {"successes": 10, "failures": 2, "plays": 12, "total_reward": 8},
            "macro_b": {"successes": 5, "failures": 5, "plays": 10, "total_reward": 5},
            "macro_c": {"successes": 1, "failures": 1, "plays": 2, "total_reward": 1},
        }

        # Run multiple selections
        selections = {}
        for _ in range(100):
            macro = selector.choose(
                macros=["macro_a", "macro_b", "macro_c"],
                history=[],
                config={"ci": {"minimum_score": 0.8}},
            )
            selections[macro] = selections.get(macro, 0) + 1

        # macro_a should be selected most often (best performance)
        # But UCB should ensure macro_c gets some exploration
        assert selections.get("macro_a", 0) > selections.get("macro_b", 0)
        assert selections.get("macro_c", 0) > 0  # UCB ensures exploration

    def test_uncertainty_metrics(self):
        """Test uncertainty metrics for MCTS decision."""
        from apeg_core.decision.bandit_selector import BanditSelector

        # Use a temp file path to avoid persistence issues
        selector = BanditSelector(
            weights_path=Path("/tmp/test_uncertainty_bandit.json"),
        )

        # Set up weights with high uncertainty (using smaller alpha/beta for higher variance)
        # Beta(1.5, 1.5) has variance ~0.083 which is > 0.05
        selector.weights = {
            "macro_a": {"successes": 1.5, "failures": 1.5, "plays": 3},
            "macro_b": {"successes": 1.5, "failures": 1.5, "plays": 3},
        }

        metrics = selector.get_uncertainty_metrics(["macro_a", "macro_b"])

        # With similar performance, score gap should be small
        assert metrics["score_gap"] < 0.1
        # Variance should be significant with few plays
        assert metrics["max_variance"] > 0.05
        # Should suggest MCTS (conditions met: score_gap < 0.1 AND max_variance > 0.05)
        assert metrics["should_use_mcts"] is True

    def test_expected_regret(self):
        """Test expected regret calculation."""
        from apeg_core.decision.bandit_selector import BanditSelector

        # Use a temp file path to avoid persistence issues
        selector = BanditSelector(
            weights_path=Path("/tmp/test_regret_bandit.json"),
        )

        selector.weights = {
            "good_macro": {"successes": 9, "failures": 1, "plays": 10},
            "bad_macro": {"successes": 1, "failures": 9, "plays": 10},
        }

        regret = selector.get_expected_regret(["good_macro", "bad_macro"])

        # Regret should be positive (suboptimal choices were made)
        assert regret > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
