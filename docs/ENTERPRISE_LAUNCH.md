# PEG Enterprise Launch Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-23
**Status:** READY FOR LAUNCH

---

## Overview

This document describes the enterprise-ready features added to PEG for immediate deployment with Shopify and Etsy API integration. All features are **plug-and-play** - just add API keys and you're ready to go.

---

## Quick Start (5 Minutes)

### 1. Start the Server

```bash
# Set encryption key for secure API key storage
export PEG_ENCRYPT_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Start the server
uvicorn src.apeg_core.web.api:app --reload --port 8000
```

### 2. Open Dashboard

Navigate to: **http://localhost:8000/dashboard**

### 3. Configure API Keys

1. Expand "Configure API Keys" section
2. Enter your Shopify credentials:
   - Store Domain: `yourstore.myshopify.com`
   - Access Token: `shpat_xxxxx`
3. Enter your Etsy credentials:
   - API Key: `your-etsy-api-key`
   - Shop ID: `12345678`
4. Click "Save & Encrypt Keys"

### 4. Run Goals

Enter goals in the dashboard and click Execute:
- "list shopify products"
- "list etsy listings"
- "sync etsy order to shopify"

---

## New Components

### 1. Unified E-commerce Connector

**File:** `src/apeg_core/connectors/ecomm.py`

Provides a single interface for managing both Shopify and Etsy:

```python
from apeg_core.connectors.ecomm import EcommConnector, EC

# Save API keys (encrypted storage)
EcommConnector.save_keys(
    shopify_token="shpat_xxx",
    shopify_domain="mystore.myshopify.com",
    etsy_key="etsy-api-key",
    etsy_shop_id="12345678"
)

# Access Shopify agent
shopify = EcommConnector.shopify()
products = shopify.list_products()

# Access Etsy agent
etsy = EcommConnector.etsy()
listings = etsy.list_listings()

# Check configuration status
status = EcommConnector.get_keys_status()
print(status)
```

### 2. Error Handling Utilities

**File:** `src/apeg_core/utils/errors.py`

Enterprise-grade error handling with the `@safe` decorator:

```python
from apeg_core.utils.errors import safe, PEGError, APIError

class MyAgent:
    @safe
    def api_call(self):
        # Any exception is wrapped in APIError
        return external_api.get("/endpoint")
```

**Error Classes:**
- `PEGError` - Base exception for all PEG errors
- `APIError` - Exception for external API errors
- `ConfigurationError` - Configuration problems
- `AuthenticationError` - Auth/authz errors
- `RateLimitError` - Rate limiting errors

### 3. Interactive Web Dashboard

**File:** `src/apeg_core/web/static/index.html`

Features:
- Real-time system status display
- API key configuration UI with encryption
- Goal execution with live output
- Quick action buttons for common operations
- Health monitoring

### 4. Enhanced Web API

**File:** `src/apeg_core/web/api.py`

New endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (redirects to /dashboard) |
| `/dashboard` | GET | Interactive control panel |
| `/api/health` | GET | Extended health check with key status |
| `/ready` | GET | Quick readiness probe |
| `/api/keys/status` | GET | Check API key configuration |
| `/setup/keys` | POST | Configure API keys with encryption |
| `/api/run` | POST | Execute workflow goal |

---

## API Reference

### POST /setup/keys

Configure API keys with secure encryption.

**Request:**
```json
{
  "shopify_token": "shpat_xxxxx",
  "shopify_domain": "mystore.myshopify.com",
  "etsy_key": "your-api-key",
  "etsy_access_token": "oauth-token",
  "etsy_shop_id": "12345678"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Keys saved and encrypted successfully",
  "saved": ["shopify_access_token", "shopify_store_domain", "etsy_api_key"],
  "skipped": ["etsy_access_token"]
}
```

### GET /api/keys/status

Check which API keys are configured.

**Response:**
```json
{
  "shopify": {
    "configured": true,
    "has_token": true,
    "has_domain": true
  },
  "etsy": {
    "configured": true,
    "has_api_key": true,
    "has_access_token": false,
    "has_shop_id": true
  }
}
```

### GET /api/health

Extended health check with system status.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "keys_configured": true,
  "agents_count": 5
}
```

### POST /api/run

Execute a workflow goal.

**Request:**
```json
{
  "goal": "list all shopify products under $50",
  "max_steps": 10
}
```

**Response:**
```json
{
  "success": true,
  "final_output": "Found 15 products...",
  "score": 0.85,
  "history": [...]
}
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PEG_ENCRYPT_KEY` | Fernet encryption key for API key storage | Recommended |
| `SHOPIFY_STORE_DOMAIN` | Shopify store domain (fallback) | Optional |
| `SHOPIFY_ACCESS_TOKEN` | Shopify API token (fallback) | Optional |
| `ETSY_API_KEY` | Etsy API key (fallback) | Optional |
| `ETSY_ACCESS_TOKEN` | Etsy OAuth token (fallback) | Optional |
| `ETSY_SHOP_ID` | Etsy shop ID (fallback) | Optional |

**Note:** API keys configured via `/setup/keys` take precedence over environment variables.

---

## Security Features

### Encrypted Key Storage

- API keys are encrypted using Fernet (AES-128-CBC with HMAC)
- Keys stored in `.keys.enc` with 0600 permissions
- Encryption key from `PEG_ENCRYPT_KEY` environment variable
- Falls back to basic obfuscation if cryptography package unavailable

### Global Error Handling

- All API errors caught and logged
- Sensitive data never exposed in error responses
- Structured error responses with type information
- Stack traces limited to 500 characters

---

## Dashboard Features

### System Status
- Real-time health checks every 30 seconds
- Visual indicators for Shopify/Etsy configuration
- Agent count display

### API Key Configuration
- Secure input fields for credentials
- One-click save and encrypt
- Visual confirmation of saved keys

### Goal Execution
- Text input for natural language goals
- Quick action buttons for common operations
- Live streaming output
- Error highlighting

### Quick Actions
- List Shopify Products
- List Etsy Listings
- Inventory Status
- Recent Orders
- Sync Etsy to Shopify

---

## File Structure

```
src/apeg_core/
├── connectors/
│   ├── __init__.py         # Updated exports
│   └── ecomm.py            # NEW: Unified e-commerce connector
├── utils/
│   ├── __init__.py         # NEW: Utils package
│   └── errors.py           # NEW: Error handling utilities
└── web/
    ├── api.py              # Updated with new endpoints
    └── static/
        └── index.html      # NEW: Interactive dashboard
```

---

## Troubleshooting

### "No API keys found" Warning

1. Navigate to `/dashboard`
2. Configure API keys in the form
3. Click "Save & Encrypt Keys"

### "Keys not persisting"

Ensure `PEG_ENCRYPT_KEY` is set before starting the server:
```bash
export PEG_ENCRYPT_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### "Shopify/Etsy in test mode"

The agent runs in test mode when credentials are missing. Check:
1. API keys are saved via `/setup/keys`
2. Or environment variables are set

### Dashboard not loading

Verify static files exist:
```bash
ls src/apeg_core/web/static/index.html
```

---

## Production Deployment

### Recommended Setup

```bash
# 1. Set persistent encryption key
export PEG_ENCRYPT_KEY="your-generated-key-here"

# 2. Run with multiple workers
uvicorn src.apeg_core.web.api:app --host 0.0.0.0 --port 8000 --workers 4

# 3. Configure API keys via dashboard or API
curl -X POST http://localhost:8000/setup/keys \
  -H "Content-Type: application/json" \
  -d '{"shopify_token":"shpat_xxx","shopify_domain":"store.myshopify.com"}'
```

### Health Checks

```bash
# Quick readiness
curl http://localhost:8000/ready

# Full health
curl http://localhost:8000/api/health
```

---

## Next Steps

1. Configure your API keys via the dashboard
2. Test with "list shopify products" goal
3. Set up production environment variables
4. Configure SSL/TLS for production
5. Set up monitoring and alerting

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-23
**Author:** PEG Development Team
