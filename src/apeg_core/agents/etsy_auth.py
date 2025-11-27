"""
Etsy OAuth 2.0 PKCE Authentication Module.

Implements OAuth 2.0 with PKCE (Proof Key for Code Exchange) for Etsy API v3.

Key Features:
- PKCE code verifier and challenge generation
- Authorization URL builder
- Token exchange and refresh
- Secure token storage interface

Usage:
    auth = EtsyAuth(
        api_key="your-api-key",
        redirect_uri="http://localhost:3000/callback"
    )

    # Generate auth URL
    auth_url, state = auth.get_authorization_url(scopes=["listings_r", "listings_w"])

    # After user authorizes, exchange code for tokens
    tokens = auth.exchange_code_for_tokens(code, auth.code_verifier)

    # Refresh tokens when needed
    new_tokens = auth.refresh_access_token(tokens["refresh_token"])
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

# Etsy OAuth 2.0 endpoints
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"


@dataclass
class EtsyTokens:
    """Container for Etsy OAuth tokens."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"

    def to_dict(self) -> Dict[str, str | int]:
        """Convert to dictionary."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
        }


class EtsyAuthError(Exception):
    """Exception raised for Etsy authentication errors."""
    pass


class EtsyAuth:
    """
    Etsy OAuth 2.0 PKCE Authentication Handler.

    Implements the full OAuth 2.0 flow with PKCE for secure
    authentication with the Etsy API v3.

    Attributes:
        api_key: Etsy API key (client ID)
        redirect_uri: OAuth callback URL
        code_verifier: PKCE code verifier (generated per auth flow)
        code_challenge: PKCE code challenge (derived from verifier)
        state: CSRF protection state token
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        redirect_uri: str = "http://localhost:3000/callback",
    ):
        """
        Initialize Etsy auth handler.

        Args:
            api_key: Etsy API key (or read from ETSY_API_KEY env var)
            redirect_uri: OAuth callback URL
        """
        self.api_key = api_key or os.environ.get("ETSY_API_KEY")
        self.redirect_uri = redirect_uri

        # PKCE values (generated fresh for each auth flow)
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        self.state: Optional[str] = None

        if not self.api_key:
            logger.warning("Etsy API key not configured")

    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        """
        Generate a cryptographically random code verifier.

        The code verifier is a high-entropy random string used in PKCE.
        Per RFC 7636, it should be 43-128 characters from unreserved URI chars.

        Args:
            length: Length of verifier (default 64, max 128)

        Returns:
            URL-safe base64 encoded random string
        """
        # Generate random bytes and encode as URL-safe base64
        random_bytes = secrets.token_bytes(length)
        verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
        # Remove padding and limit length
        return verifier.rstrip("=")[:128]

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """
        Generate SHA256 code challenge from verifier.

        The code challenge is the SHA256 hash of the verifier,
        base64url encoded (S256 method per RFC 7636).

        Args:
            verifier: The code verifier string

        Returns:
            Base64url encoded SHA256 hash
        """
        # SHA256 hash the verifier
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        # Base64url encode (no padding)
        challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return challenge

    @staticmethod
    def generate_state() -> str:
        """
        Generate a random state parameter for CSRF protection.

        Returns:
            Random hex string (32 characters)
        """
        return secrets.token_hex(16)

    def get_authorization_url(
        self,
        scopes: Optional[List[str]] = None,
    ) -> tuple[str, str]:
        """
        Build the Etsy OAuth authorization URL.

        Generates fresh PKCE values and constructs the authorization URL
        that users should be redirected to.

        Args:
            scopes: List of OAuth scopes to request. Common scopes:
                - listings_r: Read listings
                - listings_w: Write listings
                - transactions_r: Read orders/receipts
                - transactions_w: Write orders
                - profile_r: Read shop profile
                - email_r: Read user email

        Returns:
            Tuple of (authorization_url, state)

        Example:
            url, state = auth.get_authorization_url(["listings_r", "transactions_r"])
            # Redirect user to url
            # Store state for verification on callback
        """
        # Generate fresh PKCE values
        self.code_verifier = self.generate_code_verifier()
        self.code_challenge = self.generate_code_challenge(self.code_verifier)
        self.state = self.generate_state()

        # Default scopes if none provided
        if not scopes:
            scopes = ["listings_r", "transactions_r", "profile_r"]

        # Build query parameters
        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{ETSY_AUTH_URL}?{urlencode(params)}"

        logger.info("Generated Etsy authorization URL")
        logger.debug("State: %s", self.state)

        return auth_url, self.state

    def exchange_code_for_tokens(
        self,
        authorization_code: str,
        code_verifier: Optional[str] = None,
    ) -> EtsyTokens:
        """
        Exchange authorization code for access and refresh tokens.

        After the user authorizes and is redirected back with a code,
        use this method to get actual tokens.

        Args:
            authorization_code: The code from the OAuth callback
            code_verifier: PKCE code verifier (uses self.code_verifier if not provided)

        Returns:
            EtsyTokens dataclass with access_token, refresh_token, expires_in

        Raises:
            EtsyAuthError: If token exchange fails
        """
        verifier = code_verifier or self.code_verifier
        if not verifier:
            raise EtsyAuthError("No code verifier available. Call get_authorization_url first.")

        # Build token request
        data = {
            "grant_type": "authorization_code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "code": authorization_code,
            "code_verifier": verifier,
        }

        logger.info("Exchanging authorization code for tokens")

        try:
            response = requests.post(
                ETSY_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()

            tokens = EtsyTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer"),
            )

            logger.info("Successfully obtained Etsy tokens (expires_in=%d)", tokens.expires_in)
            return tokens

        except requests.RequestException as e:
            logger.error("Token exchange failed: %s", e)
            raise EtsyAuthError(f"Failed to exchange code for tokens: {e}")

    def refresh_access_token(self, refresh_token: str) -> EtsyTokens:
        """
        Refresh an expired access token.

        Etsy access tokens expire after about 1 hour. Use the refresh token
        (valid for 90 days) to get a new access token.

        Args:
            refresh_token: The refresh token from a previous token response

        Returns:
            EtsyTokens with new access_token and possibly new refresh_token

        Raises:
            EtsyAuthError: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.api_key,
            "refresh_token": refresh_token,
        }

        logger.info("Refreshing Etsy access token")

        try:
            response = requests.post(
                ETSY_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()

            tokens = EtsyTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data.get("expires_in", 3600),
                token_type=token_data.get("token_type", "Bearer"),
            )

            logger.info("Successfully refreshed Etsy tokens")
            return tokens

        except requests.RequestException as e:
            logger.error("Token refresh failed: %s", e)
            raise EtsyAuthError(f"Failed to refresh token: {e}")

    def validate_state(self, received_state: str) -> bool:
        """
        Validate the state parameter from OAuth callback.

        Compares the received state with the stored state to prevent CSRF.

        Args:
            received_state: State parameter from callback URL

        Returns:
            True if state matches, False otherwise
        """
        if not self.state:
            logger.warning("No stored state to validate against")
            return False

        is_valid = secrets.compare_digest(self.state, received_state)
        if not is_valid:
            logger.warning("State mismatch: CSRF protection triggered")

        return is_valid
