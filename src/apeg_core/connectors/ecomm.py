"""
Unified E-commerce Connector for Shopify and Etsy.

Provides a single interface for managing API keys and accessing
both Shopify and Etsy clients with encrypted key storage.

Features:
- Encrypted API key storage using Fernet encryption
- Auto-loading of credentials from environment or encrypted file
- Unified access to both e-commerce platforms
- Key setup and rotation support

Usage:
    from apeg_core.connectors.ecomm import EcommConnector

    # Save keys (one-time setup)
    EcommConnector.save_keys(shopify_token="shpat_xxx", etsy_key="xxx")

    # Access Shopify
    shopify = EcommConnector.shopify()
    products = shopify.list_products()

    # Access Etsy
    etsy = EcommConnector.etsy()
    listings = etsy.list_listings()
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class EcommConnector:
    """
    Unified connector for Shopify and Etsy e-commerce platforms.

    Manages API key storage and provides factory methods for
    accessing platform-specific agents.

    Environment Variables:
        PEG_ENCRYPT_KEY: Encryption key for secure storage
        SHOPIFY_STORE_DOMAIN: Shopify store domain
        SHOPIFY_ACCESS_TOKEN: Shopify API access token
        ETSY_API_KEY: Etsy API key
        ETSY_ACCESS_TOKEN: Etsy OAuth access token
        ETSY_SHOP_ID: Etsy shop ID
    """

    _shopify_agent = None
    _etsy_agent = None
    _key_manager = None

    @classmethod
    def _get_key_manager(cls):
        """Get or create key manager instance."""
        if cls._key_manager is None:
            from apeg_core.security.key_management import get_key_manager
            cls._key_manager = get_key_manager()
        return cls._key_manager

    @classmethod
    def save_keys(
        cls,
        shopify_token: Optional[str] = None,
        shopify_domain: Optional[str] = None,
        etsy_key: Optional[str] = None,
        etsy_access_token: Optional[str] = None,
        etsy_shop_id: Optional[str] = None,
    ) -> dict:
        """
        Save API keys securely with encryption.

        Args:
            shopify_token: Shopify Admin API access token
            shopify_domain: Shopify store domain (e.g., "mystore.myshopify.com")
            etsy_key: Etsy API key (client ID)
            etsy_access_token: Etsy OAuth access token
            etsy_shop_id: Etsy shop ID

        Returns:
            Dictionary with status of each key saved
        """
        km = cls._get_key_manager()
        result = {"saved": [], "skipped": []}

        # Save Shopify credentials
        if shopify_token:
            km.store_key("shopify", "access_token", shopify_token)
            result["saved"].append("shopify_access_token")
            logger.info("Saved Shopify access token")
        else:
            result["skipped"].append("shopify_access_token")

        if shopify_domain:
            km.store_key("shopify", "store_domain", shopify_domain)
            result["saved"].append("shopify_store_domain")
            logger.info("Saved Shopify store domain")
        else:
            result["skipped"].append("shopify_store_domain")

        # Save Etsy credentials
        if etsy_key:
            km.store_key("etsy", "api_key", etsy_key)
            result["saved"].append("etsy_api_key")
            logger.info("Saved Etsy API key")
        else:
            result["skipped"].append("etsy_api_key")

        if etsy_access_token:
            km.store_key("etsy", "access_token", etsy_access_token)
            result["saved"].append("etsy_access_token")
            logger.info("Saved Etsy access token")
        else:
            result["skipped"].append("etsy_access_token")

        if etsy_shop_id:
            km.store_key("etsy", "shop_id", etsy_shop_id)
            result["saved"].append("etsy_shop_id")
            logger.info("Saved Etsy shop ID")
        else:
            result["skipped"].append("etsy_shop_id")

        # Reset cached agents to pick up new credentials
        cls._shopify_agent = None
        cls._etsy_agent = None

        return result

    @classmethod
    def get_keys_status(cls) -> dict:
        """
        Check which API keys are configured.

        Returns:
            Dictionary with configuration status for each service
        """
        km = cls._get_key_manager()

        # Check Shopify
        shopify_token = km.retrieve_key("shopify", "access_token")
        shopify_domain = km.retrieve_key("shopify", "store_domain") or os.getenv("SHOPIFY_STORE_DOMAIN")

        # Check Etsy
        etsy_key = km.retrieve_key("etsy", "api_key") or os.getenv("ETSY_API_KEY")
        etsy_token = km.retrieve_key("etsy", "access_token") or os.getenv("ETSY_ACCESS_TOKEN")
        etsy_shop = km.retrieve_key("etsy", "shop_id") or os.getenv("ETSY_SHOP_ID")

        return {
            "shopify": {
                "configured": bool(shopify_token and shopify_domain),
                "has_token": bool(shopify_token),
                "has_domain": bool(shopify_domain),
            },
            "etsy": {
                "configured": bool(etsy_key),
                "has_api_key": bool(etsy_key),
                "has_access_token": bool(etsy_token),
                "has_shop_id": bool(etsy_shop),
            },
        }

    @classmethod
    def shopify(cls, force_new: bool = False):
        """
        Get Shopify agent instance.

        Args:
            force_new: Force creation of new agent instance

        Returns:
            ShopifyAgent configured with stored credentials
        """
        if cls._shopify_agent is not None and not force_new:
            return cls._shopify_agent

        from apeg_core.agents.shopify_agent import ShopifyAgent

        # Try to get credentials from key manager first, then environment
        km = cls._get_key_manager()

        access_token = km.retrieve_key("shopify", "access_token") or os.getenv("SHOPIFY_ACCESS_TOKEN")
        store_domain = km.retrieve_key("shopify", "store_domain") or os.getenv("SHOPIFY_STORE_DOMAIN")
        api_version = os.getenv("SHOPIFY_API_VERSION", "2024-01")

        # Determine test mode based on credentials availability
        test_mode = not (access_token and store_domain)

        if test_mode:
            logger.warning(
                "ShopifyAgent: No credentials found. Running in test mode. "
                "Use EcommConnector.save_keys() to configure."
            )

        config = {
            "access_token": access_token,
            "store_domain": store_domain,
            "api_version": api_version,
            "test_mode": test_mode,
        }

        cls._shopify_agent = ShopifyAgent(config=config, test_mode=test_mode)
        return cls._shopify_agent

    @classmethod
    def etsy(cls, force_new: bool = False):
        """
        Get Etsy agent instance.

        Args:
            force_new: Force creation of new agent instance

        Returns:
            EtsyAgent configured with stored credentials
        """
        if cls._etsy_agent is not None and not force_new:
            return cls._etsy_agent

        from apeg_core.agents.etsy_agent import EtsyAgent

        # Try to get credentials from key manager first, then environment
        km = cls._get_key_manager()

        api_key = km.retrieve_key("etsy", "api_key") or os.getenv("ETSY_API_KEY")
        access_token = km.retrieve_key("etsy", "access_token") or os.getenv("ETSY_ACCESS_TOKEN")
        refresh_token = os.getenv("ETSY_REFRESH_TOKEN")
        shop_id = km.retrieve_key("etsy", "shop_id") or os.getenv("ETSY_SHOP_ID")

        # Determine test mode based on credentials availability
        test_mode = not api_key

        if test_mode:
            logger.warning(
                "EtsyAgent: No API key found. Running in test mode. "
                "Use EcommConnector.save_keys() to configure."
            )

        config = {
            "etsy_api_key": api_key,
            "etsy_access_token": access_token,
            "etsy_refresh_token": refresh_token,
            "etsy_shop_id": shop_id,
            "test_mode": test_mode,
        }

        cls._etsy_agent = EtsyAgent(config=config, test_mode=test_mode)
        return cls._etsy_agent

    @classmethod
    def reset(cls) -> None:
        """Reset cached agent instances."""
        cls._shopify_agent = None
        cls._etsy_agent = None
        cls._key_manager = None
        logger.info("EcommConnector cache reset")


# Convenience aliases
EC = EcommConnector

__all__ = ["EcommConnector", "EC"]
