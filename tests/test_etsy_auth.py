"""Tests for Etsy OAuth 2.0 PKCE authentication module."""

import pytest
from unittest.mock import patch, MagicMock

from apeg_core.agents.etsy_auth import (
    EtsyAuth,
    EtsyTokens,
    EtsyAuthError,
)


class TestEtsyAuthPKCE:
    """Tests for PKCE code generation."""

    def test_generate_code_verifier_length(self):
        """Test code verifier has correct length."""
        verifier = EtsyAuth.generate_code_verifier()
        assert 43 <= len(verifier) <= 128

    def test_generate_code_verifier_uniqueness(self):
        """Test code verifiers are unique."""
        verifiers = {EtsyAuth.generate_code_verifier() for _ in range(100)}
        assert len(verifiers) == 100

    def test_generate_code_verifier_url_safe(self):
        """Test code verifier contains only URL-safe characters."""
        verifier = EtsyAuth.generate_code_verifier()
        # URL-safe base64 characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in verifier)

    def test_generate_code_challenge(self):
        """Test code challenge is derived from verifier."""
        verifier = "test_verifier_string_for_testing"
        challenge = EtsyAuth.generate_code_challenge(verifier)
        # Should be base64url encoded
        assert len(challenge) > 0
        # Same verifier should produce same challenge
        assert challenge == EtsyAuth.generate_code_challenge(verifier)

    def test_generate_code_challenge_different_verifiers(self):
        """Test different verifiers produce different challenges."""
        verifier1 = EtsyAuth.generate_code_verifier()
        verifier2 = EtsyAuth.generate_code_verifier()
        challenge1 = EtsyAuth.generate_code_challenge(verifier1)
        challenge2 = EtsyAuth.generate_code_challenge(verifier2)
        assert challenge1 != challenge2

    def test_generate_state(self):
        """Test state generation."""
        state = EtsyAuth.generate_state()
        assert len(state) == 32  # 16 bytes as hex
        # Should be valid hex
        int(state, 16)


class TestEtsyAuthInit:
    """Tests for EtsyAuth initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        auth = EtsyAuth(api_key="test-api-key")
        assert auth.api_key == "test-api-key"

    def test_init_with_redirect_uri(self):
        """Test initialization with custom redirect URI."""
        auth = EtsyAuth(
            api_key="test-key",
            redirect_uri="https://example.com/callback"
        )
        assert auth.redirect_uri == "https://example.com/callback"

    @patch.dict("os.environ", {"ETSY_API_KEY": "env-api-key"})
    def test_init_from_env(self):
        """Test initialization from environment variable."""
        auth = EtsyAuth()
        assert auth.api_key == "env-api-key"


class TestEtsyAuthAuthorizationURL:
    """Tests for authorization URL generation."""

    def test_get_authorization_url_structure(self):
        """Test authorization URL has correct structure."""
        auth = EtsyAuth(api_key="test-key")
        url, state = auth.get_authorization_url()

        assert "https://www.etsy.com/oauth/connect" in url
        assert "response_type=code" in url
        assert "client_id=test-key" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert f"state={state}" in url

    def test_get_authorization_url_generates_pkce(self):
        """Test authorization URL generates PKCE values."""
        auth = EtsyAuth(api_key="test-key")
        auth.get_authorization_url()

        assert auth.code_verifier is not None
        assert auth.code_challenge is not None
        assert auth.state is not None

    def test_get_authorization_url_with_scopes(self):
        """Test authorization URL includes requested scopes."""
        auth = EtsyAuth(api_key="test-key")
        url, _ = auth.get_authorization_url(scopes=["listings_r", "transactions_r"])

        assert "scope=" in url
        assert "listings_r" in url
        assert "transactions_r" in url


class TestEtsyAuthTokenExchange:
    """Tests for token exchange."""

    @patch("apeg_core.agents.etsy_auth.requests.post")
    def test_exchange_code_for_tokens_success(self, mock_post):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        auth = EtsyAuth(api_key="test-key")
        auth.get_authorization_url()  # Generate PKCE values

        tokens = auth.exchange_code_for_tokens("auth-code")

        assert tokens.access_token == "new-access-token"
        assert tokens.refresh_token == "new-refresh-token"
        assert tokens.expires_in == 3600

    def test_exchange_code_without_verifier_raises(self):
        """Test exchange without verifier raises error."""
        auth = EtsyAuth(api_key="test-key")
        # Don't call get_authorization_url, so no verifier

        with pytest.raises(EtsyAuthError, match="No code verifier"):
            auth.exchange_code_for_tokens("auth-code")

    @patch("apeg_core.agents.etsy_auth.requests.post")
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "refreshed-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        auth = EtsyAuth(api_key="test-key")
        tokens = auth.refresh_access_token("old-refresh-token")

        assert tokens.access_token == "refreshed-access-token"


class TestEtsyAuthStateValidation:
    """Tests for state validation."""

    def test_validate_state_correct(self):
        """Test state validation with correct state."""
        auth = EtsyAuth(api_key="test-key")
        _, state = auth.get_authorization_url()

        assert auth.validate_state(state) is True

    def test_validate_state_incorrect(self):
        """Test state validation with incorrect state."""
        auth = EtsyAuth(api_key="test-key")
        auth.get_authorization_url()

        assert auth.validate_state("wrong-state") is False

    def test_validate_state_no_stored_state(self):
        """Test state validation without stored state."""
        auth = EtsyAuth(api_key="test-key")
        # Don't call get_authorization_url

        assert auth.validate_state("any-state") is False


class TestEtsyTokens:
    """Tests for EtsyTokens dataclass."""

    def test_tokens_to_dict(self):
        """Test converting tokens to dictionary."""
        tokens = EtsyTokens(
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
        )
        data = tokens.to_dict()

        assert data["access_token"] == "access"
        assert data["refresh_token"] == "refresh"
        assert data["expires_in"] == 3600
        assert data["token_type"] == "Bearer"
