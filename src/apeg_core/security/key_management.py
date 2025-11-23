"""
Secure API Key Management for APEG.

Provides:
- Encrypted key storage
- Key rotation support
- Secure key retrieval
- Memory-safe key handling
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Secure API key manager with encryption.

    Uses Fernet-compatible encryption for storing sensitive keys.
    Falls back to basic obfuscation if cryptography package not available.

    Attributes:
        keys_file: Path to encrypted keys file
        encryption_key: Key used for encryption
    """

    def __init__(
        self,
        keys_file: str | Path = ".keys.enc",
        encryption_key: Optional[str] = None,
        test_mode: bool = False,
    ):
        """
        Initialize key manager.

        Args:
            keys_file: Path to encrypted keys storage file
            encryption_key: Encryption key (default: from ENCRYPT_KEY env)
            test_mode: Use in-memory storage only
        """
        self.keys_file = Path(keys_file)
        self.test_mode = test_mode
        self._lock = Lock()
        self._in_memory_keys: Dict[str, Dict[str, Any]] = {}

        # Get or generate encryption key
        self.encryption_key = encryption_key or os.getenv("ENCRYPT_KEY")
        if not self.encryption_key:
            logger.warning(
                "ENCRYPT_KEY not set. Generating ephemeral key. "
                "Set ENCRYPT_KEY environment variable for persistent encryption."
            )
            self.encryption_key = secrets.token_urlsafe(32)

        # Try to import cryptography for proper encryption
        # We use a helper function to safely test if cryptography works
        self._fernet = None
        self._fernet = self._try_init_fernet()

    def _try_init_fernet(self):
        """
        Safely try to initialize Fernet encryption.

        Returns Fernet instance if available, None otherwise.
        This method handles all possible failure modes including
        broken cryptography installations.
        """
        try:
            # First check if cryptography module can be imported at all
            import importlib.util

            # Check for cffi backend which cryptography depends on
            # If cffi is broken, cryptography will panic (Rust-level crash)
            try:
                import _cffi_backend
            except ImportError:
                logger.warning(
                    "cffi backend not available. Using basic obfuscation. "
                    "Install cffi for cryptography support: pip install cffi"
                )
                return None

            spec = importlib.util.find_spec("cryptography")
            if spec is None:
                logger.warning(
                    "cryptography package not installed. Using basic obfuscation. "
                    "Install cryptography for production: pip install cryptography"
                )
                return None

            # Now safe to import Fernet
            from cryptography.fernet import Fernet

            # Derive a valid Fernet key from our key
            key_bytes = hashlib.sha256(self.encryption_key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            fernet = Fernet(fernet_key)
            logger.info("KeyManager initialized with Fernet encryption")
            return fernet

        except BaseException as e:
            # Catch ALL exceptions including SystemExit, KeyboardInterrupt, etc.
            # This handles cases where cryptography is installed but broken
            logger.warning(
                "cryptography package not available (%s). Using basic obfuscation. "
                "Install cryptography for production: pip install cryptography",
                type(e).__name__
            )
            return None

    def store_key(
        self,
        service: str,
        key_name: str,
        key_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store an API key securely.

        Args:
            service: Service name (e.g., "shopify", "etsy", "openai")
            key_name: Key identifier (e.g., "access_token", "api_key")
            key_value: The actual key value
            metadata: Optional metadata (e.g., expiration, shop_id)
        """
        with self._lock:
            keys = self._load_keys()

            if service not in keys:
                keys[service] = {}

            keys[service][key_name] = {
                "value": self._encrypt(key_value),
                "stored_at": datetime.utcnow().isoformat() + "Z",
                "metadata": metadata or {},
            }

            self._save_keys(keys)
            logger.info("Stored key %s for service %s", key_name, service)

    def retrieve_key(
        self,
        service: str,
        key_name: str,
    ) -> Optional[str]:
        """
        Retrieve a stored API key.

        Args:
            service: Service name
            key_name: Key identifier

        Returns:
            Decrypted key value, or None if not found
        """
        keys = self._load_keys()

        service_keys = keys.get(service, {})
        key_data = service_keys.get(key_name)

        if not key_data:
            logger.debug("Key %s not found for service %s", key_name, service)
            return None

        encrypted_value = key_data.get("value")
        if not encrypted_value:
            return None

        return self._decrypt(encrypted_value)

    def delete_key(
        self,
        service: str,
        key_name: str,
    ) -> bool:
        """
        Delete a stored key.

        Args:
            service: Service name
            key_name: Key identifier

        Returns:
            True if key was deleted
        """
        with self._lock:
            keys = self._load_keys()

            if service in keys and key_name in keys[service]:
                del keys[service][key_name]
                if not keys[service]:
                    del keys[service]
                self._save_keys(keys)
                logger.info("Deleted key %s for service %s", key_name, service)
                return True

            return False

    def list_keys(
        self,
        service: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        List stored keys (without values).

        Args:
            service: Filter by service (optional)

        Returns:
            Dictionary of services and their key metadata
        """
        keys = self._load_keys()

        result = {}
        for svc, svc_keys in keys.items():
            if service and svc != service:
                continue

            result[svc] = {}
            for key_name, key_data in svc_keys.items():
                result[svc][key_name] = {
                    "stored_at": key_data.get("stored_at"),
                    "metadata": key_data.get("metadata", {}),
                    # Don't include the actual value
                }

        return result

    def rotate_key(
        self,
        service: str,
        key_name: str,
        new_value: str,
    ) -> None:
        """
        Rotate a key (store new value, preserve metadata).

        Args:
            service: Service name
            key_name: Key identifier
            new_value: New key value
        """
        keys = self._load_keys()

        # Get existing metadata
        metadata = {}
        if service in keys and key_name in keys[service]:
            old_data = keys[service][key_name]
            metadata = old_data.get("metadata", {})
            metadata["previous_rotation"] = old_data.get("stored_at")

        # Store with rotation history
        self.store_key(service, key_name, new_value, metadata)
        logger.info("Rotated key %s for service %s", key_name, service)

    def _encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.

        Args:
            plaintext: Value to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if self._fernet:
            # Use Fernet encryption
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        else:
            # Fallback to basic obfuscation (XOR with key)
            key_bytes = hashlib.sha256(self.encryption_key.encode()).digest()
            plain_bytes = plaintext.encode()

            obfuscated = bytes(
                p ^ key_bytes[i % len(key_bytes)]
                for i, p in enumerate(plain_bytes)
            )

            return base64.b64encode(obfuscated).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Encrypted value (base64 encoded)

        Returns:
            Decrypted string
        """
        if self._fernet:
            try:
                decrypted = self._fernet.decrypt(ciphertext.encode())
                return decrypted.decode()
            except Exception as e:
                logger.error("Decryption failed: %s", e)
                return ""
        else:
            # Fallback to basic de-obfuscation
            key_bytes = hashlib.sha256(self.encryption_key.encode()).digest()

            try:
                obfuscated = base64.b64decode(ciphertext)
                plain_bytes = bytes(
                    o ^ key_bytes[i % len(key_bytes)]
                    for i, o in enumerate(obfuscated)
                )
                return plain_bytes.decode()
            except Exception as e:
                logger.error("De-obfuscation failed: %s", e)
                return ""

    def _load_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load keys from storage."""
        if self.test_mode:
            return self._in_memory_keys.copy()

        if not self.keys_file.exists():
            return {}

        try:
            with open(self.keys_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load keys: %s", e)
            return {}

    def _save_keys(self, keys: Dict[str, Dict[str, Any]]) -> None:
        """Save keys to storage."""
        if self.test_mode:
            self._in_memory_keys = keys.copy()
            return

        try:
            # Set restrictive permissions
            self.keys_file.touch(mode=0o600, exist_ok=True)

            with open(self.keys_file, "w", encoding="utf-8") as f:
                json.dump(keys, f, indent=2)

            # Ensure file permissions are restrictive
            os.chmod(self.keys_file, 0o600)

        except IOError as e:
            logger.error("Failed to save keys: %s", e)
            raise


# Global key manager instance
_global_key_manager: Optional[KeyManager] = None


def get_key_manager(
    keys_file: str | Path = ".keys.enc",
    test_mode: bool = False,
) -> KeyManager:
    """
    Get or create global key manager instance.

    Args:
        keys_file: Path to keys storage file
        test_mode: Use in-memory storage

    Returns:
        Global KeyManager instance
    """
    global _global_key_manager

    if _global_key_manager is None:
        _global_key_manager = KeyManager(keys_file, test_mode=test_mode)

    return _global_key_manager


def encrypt_api_key(key: str) -> str:
    """
    Convenience function to encrypt an API key.

    Args:
        key: API key to encrypt

    Returns:
        Encrypted key string
    """
    return get_key_manager()._encrypt(key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Convenience function to decrypt an API key.

    Args:
        encrypted_key: Encrypted key string

    Returns:
        Decrypted API key
    """
    return get_key_manager()._decrypt(encrypted_key)


__all__ = [
    "KeyManager",
    "get_key_manager",
    "encrypt_api_key",
    "decrypt_api_key",
]
