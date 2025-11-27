"""Generic HTTP client with retry logic and test mode support.

This module provides a reusable HTTP client for making API requests with:
- Exponential backoff retry logic
- Test mode for development/testing without real API calls
- Support for common HTTP methods (GET, POST, PUT, DELETE)
- Configurable timeout and base URL
- Optional rate limiting for API compliance

Usage:
    # Test mode (returns mock data)
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)
    result = client.get("/endpoint")
    # Returns: {"test_mode": True, "method": "GET", "url": "https://api.example.com/endpoint"}

    # Real mode
    client = HTTPClient(base_url="https://api.example.com", test_mode=False)
    result = client.get("/endpoint", params={"key": "value"})
    # Makes actual HTTP request with retry logic

    # With rate limiting (for APIs like Shopify)
    client = HTTPClient(base_url="https://api.example.com", rate_limit_per_second=2.0)
    # Requests will be throttled to ~2 per second
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm.

    Limits the rate of API calls to prevent hitting rate limits.
    Thread-safe implementation.

    Attributes:
        rate: Maximum requests per second
        tokens: Current available tokens
        last_check: Timestamp of last token check
    """

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests per second (e.g., 2.0 for Shopify)
        """
        self.rate = rate
        self.tokens = rate  # Start with full bucket
        self.last_check = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """
        Acquire a token, blocking if rate limit is exceeded.

        This method blocks until a token is available, ensuring
        that requests don't exceed the configured rate.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.last_check = now

            # Add tokens based on elapsed time
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)

            # If no tokens available, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                logger.debug("Rate limit: waiting %.3fs", wait_time)
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class HTTPClient:
    """Generic HTTP client with retry logic, rate limiting, and test mode support.

    Attributes:
        base_url: Base URL for all requests (can be overridden per request)
        test_mode: If True, returns mock data instead of making real requests
        timeout: Request timeout in seconds
        rate_limiter: Optional rate limiter for API compliance
    """

    def __init__(
        self,
        base_url: str = "",
        test_mode: bool = False,
        timeout: int = 30,
        rate_limit_per_second: Optional[float] = None
    ):
        """Initialize HTTP client.

        Args:
            base_url: Base URL for API requests (optional)
            test_mode: If True, return mock responses instead of real API calls
            timeout: Request timeout in seconds
            rate_limit_per_second: Optional rate limit (e.g., 2.0 for Shopify)
        """
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.test_mode = test_mode
        self.timeout = timeout
        self.rate_limiter = RateLimiter(rate_limit_per_second) if rate_limit_per_second else None
        logger.info(
            "HTTPClient initialized (base_url=%s, test_mode=%s, timeout=%ds, rate_limit=%s)",
            self.base_url or "(none)",
            self.test_mode,
            self.timeout,
            f"{rate_limit_per_second}/s" if rate_limit_per_second else "none"
        )

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute GET request.

        Args:
            url: Endpoint URL (absolute or relative to base_url)
            params: Query parameters
            headers: Request headers

        Returns:
            Response data as dictionary
        """
        full_url = self._build_url(url)

        if self.test_mode:
            logger.info("HTTPClient.get(%s) [TEST MODE]", full_url)
            return {
                "test_mode": True,
                "method": "GET",
                "url": full_url,
                "params": params,
                "headers": headers
            }

        response = self._retry_request("GET", full_url, params=params, headers=headers)
        return response.json() if response.content else {}

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute POST request.

        Args:
            url: Endpoint URL (absolute or relative to base_url)
            json: JSON payload
            headers: Request headers

        Returns:
            Response data as dictionary
        """
        full_url = self._build_url(url)

        if self.test_mode:
            logger.info("HTTPClient.post(%s) [TEST MODE]", full_url)
            return {
                "test_mode": True,
                "method": "POST",
                "url": full_url,
                "json": json,
                "headers": headers
            }

        response = self._retry_request("POST", full_url, json=json, headers=headers)
        return response.json() if response.content else {}

    def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute PUT request.

        Args:
            url: Endpoint URL (absolute or relative to base_url)
            json: JSON payload
            headers: Request headers

        Returns:
            Response data as dictionary
        """
        full_url = self._build_url(url)

        if self.test_mode:
            logger.info("HTTPClient.put(%s) [TEST MODE]", full_url)
            return {
                "test_mode": True,
                "method": "PUT",
                "url": full_url,
                "json": json,
                "headers": headers
            }

        response = self._retry_request("PUT", full_url, json=json, headers=headers)
        return response.json() if response.content else {}

    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute DELETE request.

        Args:
            url: Endpoint URL (absolute or relative to base_url)
            headers: Request headers

        Returns:
            Response data as dictionary
        """
        full_url = self._build_url(url)

        if self.test_mode:
            logger.info("HTTPClient.delete(%s) [TEST MODE]", full_url)
            return {
                "test_mode": True,
                "method": "DELETE",
                "url": full_url,
                "headers": headers
            }

        response = self._retry_request("DELETE", full_url, headers=headers)
        return response.json() if response.content else {}

    def _build_url(self, url: str) -> str:
        """Build full URL from base_url and relative URL.

        Args:
            url: Absolute or relative URL

        Returns:
            Full URL
        """
        if url.startswith(("http://", "https://")):
            return url

        if self.base_url:
            return f"{self.base_url}/{url.lstrip('/')}"

        return url

    def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """Execute HTTP request with exponential backoff retry logic and rate limiting.

        Retries up to 3 times with delays of 1s, 2s, 4s between attempts.
        If rate limiting is enabled, waits for rate limit token before each request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            **kwargs: Additional arguments for requests (params, json, headers)

        Returns:
            Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        max_retries = 3
        delays = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s

        kwargs['timeout'] = self.timeout

        for attempt in range(max_retries):
            try:
                # Apply rate limiting if configured
                if self.rate_limiter:
                    self.rate_limiter.acquire()

                logger.debug(
                    "HTTP %s %s (attempt %d/%d)",
                    method,
                    url,
                    attempt + 1,
                    max_retries
                )

                response = requests.request(method, url, **kwargs)
                response.raise_for_status()

                logger.info("HTTP %s %s -> %d", method, url, response.status_code)
                return response

            except requests.RequestException as exc:
                logger.warning(
                    "HTTP %s %s failed (attempt %d/%d): %s",
                    method,
                    url,
                    attempt + 1,
                    max_retries,
                    exc
                )

                if attempt < max_retries - 1:
                    delay = delays[attempt]
                    logger.info("Retrying in %.1fs...", delay)
                    time.sleep(delay)
                else:
                    logger.error("All retries exhausted for %s %s", method, url)
                    raise

        # Should never reach here, but satisfy type checker
        raise requests.RequestException(f"Failed to complete {method} {url}")
