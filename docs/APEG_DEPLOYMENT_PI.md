# APEG Deployment Guide – Raspberry Pi / Linux Server

**Version:** 1.0
**Last Updated:** 2025-11-20
**Target Platform:** Raspberry Pi OS (Bullseye/Bookworm) / Ubuntu 22.04+
**Python Version:** 3.11 or 3.12
**Estimated Setup Time:** 30-60 minutes

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Server Start Command](#server-start-command)
4. [Systemd Service Setup](#systemd-service-setup)
5. [Nginx Reverse Proxy](#nginx-reverse-proxy)
6. [Performance Tuning](#performance-tuning)
7. [Security Configuration](#security-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- **Minimum:** Raspberry Pi 4B (4GB RAM)
- **Recommended:** Raspberry Pi 5 (8GB RAM)
- **Storage:** 32GB+ microSD card (Class 10) or USB 3.0 SSD
- **Cooling:** Heatsink + fan (active cooling recommended for 24/7 operation)
- **Power:** Official Raspberry Pi power supply (5V 3A for Pi 4, 5V 5A for Pi 5)

### Software Requirements
- **OS:** Raspberry Pi OS (64-bit) or Ubuntu Server 22.04+
- **Python:** 3.11 or 3.12
- **Git:** For repository cloning
- **Internet:** For API access (OpenAI, Shopify, Etsy)

### Optional Components
- Domain name (for HTTPS with Let's Encrypt)
- Static IP address or DDNS
- External USB storage for logs/backups

---

## Installation

### 1. System Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    nginx \
    certbot \
    python3-certbot-nginx

# Verify Python version
python3.11 --version
# Expected: Python 3.11.x
```

### 2. Create Application Directory
```bash
# Create application directory
sudo mkdir -p /opt/apeg
sudo chown $USER:$USER /opt/apeg
cd /opt/apeg
```

### 3. Clone Repository
```bash
# Clone APEG repository
git clone https://github.com/Matthewtgordon/PEG.git .

# Or copy from local machine
# rsync -av /path/to/local/PEG/ /opt/apeg/
```

### 4. Create Virtual Environment
```bash
# Create virtual environment with Python 3.11
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 5. Install Dependencies
```bash
# Install APEG package and dependencies
pip install -r requirements.txt
pip install -e .

# Verify installation
python -c "from apeg_core import APEGOrchestrator; print('✓ APEG installed successfully')"
```

### 6. Create Environment Configuration
```bash
# Copy environment template
cp .env.sample .env

# Edit with your API keys
nano .env
```

**Required Environment Variables:**
```bash
# APEG Configuration
APEG_TEST_MODE=false          # Set to true for testing without real APIs
APEG_DEBUG=false              # Set to true for verbose logging
APEG_HOST=0.0.0.0            # Bind to all interfaces
APEG_PORT=8000               # Default port
APEG_CONFIG_DIR=/opt/apeg    # Configuration directory

# API Keys (required for production)
OPENAI_API_KEY=sk-...        # OpenAI API key
SHOPIFY_API_KEY=...          # Shopify API credentials
SHOPIFY_STORE_URL=...
SHOPIFY_ACCESS_TOKEN=...
ETSY_API_KEY=...             # Etsy API credentials
```

### 7. Validate Installation
```bash
# Run validation script
python validate_repo.py

# Run tests in test mode
APEG_TEST_MODE=true pytest tests/ -v

# Test server startup (Ctrl+C to stop)
python -m apeg_core.server
```

---

## Server Start Command

### Canonical Start Method
```bash
# From project root with virtual environment activated
cd /opt/apeg
source .venv/bin/activate
python -m apeg_core.server
```

### Alternative Methods
```bash
# Method 1: Using CLI (if available)
python -m apeg_core serve

# Method 2: Direct uvicorn
python -m uvicorn apeg_core.server:app --host 0.0.0.0 --port 8000

# Method 3: Background process
nohup python -m apeg_core.server > logs/server.log 2>&1 &
```

### Verify Server Running
```bash
# Health check
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","version":"1.0.0","test_mode":"false"}

# Interactive API documentation
# Open browser: http://[raspberry-pi-ip]:8000/docs
```

---

## Systemd Service Setup

### 1. Create Service File
```bash
sudo nano /etc/systemd/system/apeg.service
```

**Service Configuration:**
```ini
[Unit]
Description=APEG (Agentic Prompt Engineering Graph) API Server
After=network.target
Documentation=https://github.com/Matthewtgordon/PEG
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/apeg
Environment="PATH=/opt/apeg/.venv/bin"
EnvironmentFile=/opt/apeg/.env

# Start command
ExecStart=/opt/apeg/.venv/bin/python -m apeg_core.server

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=60

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=apeg

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/apeg

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service
```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service (autostart on boot)
sudo systemctl enable apeg.service

# Start service
sudo systemctl start apeg.service

# Check status
sudo systemctl status apeg.service

# Expected output:
# ● apeg.service - APEG API Server
#    Loaded: loaded (/etc/systemd/system/apeg.service; enabled)
#    Active: active (running) since...
```

### 3. Service Management Commands
```bash
# Start service
sudo systemctl start apeg

# Stop service
sudo systemctl stop apeg

# Restart service
sudo systemctl restart apeg

# Reload service (graceful)
sudo systemctl reload apeg

# View real-time logs
sudo journalctl -u apeg -f

# View last 100 log lines
sudo journalctl -u apeg -n 100

# View logs from today
sudo journalctl -u apeg --since today

# Disable autostart
sudo systemctl disable apeg
```

---

## Nginx Reverse Proxy

### 1. Install Nginx (if not already installed)
```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/apeg
```

**Configuration File:**
```nginx
# /etc/nginx/sites-available/apeg

# HTTP Server (redirect to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name apeg.yourdomain.com;  # Replace with your domain

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name apeg.yourdomain.com;  # Replace with your domain

    # SSL Certificates (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/apeg.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/apeg.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # SSL Settings (Mozilla Intermediate Configuration)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CORS Headers (adjust origins for your frontend)
    add_header Access-Control-Allow-Origin "https://yourdomain.com" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Logging
    access_log /var/log/nginx/apeg_access.log;
    error_log /var/log/nginx/apeg_error.log;

    # Proxy to APEG API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts (adjust for long-running workflows)
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint (bypass auth if using)
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }

    # Static files (if any)
    location /static {
        alias /opt/apeg/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

# Rate Limiting Configuration (optional)
limit_req_zone $binary_remote_addr zone=apeg_limit:10m rate=10r/s;
limit_req_status 429;
```

### 3. Enable Site
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/apeg /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Expected output:
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload nginx
sudo systemctl reload nginx
```

### 4. SSL Certificate Setup (Let's Encrypt)
```bash
# Obtain certificate (interactive)
sudo certbot --nginx -d apeg.yourdomain.com

# Follow prompts:
# 1. Enter email address
# 2. Agree to terms
# 3. Choose redirect option (recommended: redirect HTTP to HTTPS)

# Verify auto-renewal is set up
sudo certbot renew --dry-run

# Certificate will auto-renew via cron/timer
```

### 5. Firewall Configuration
```bash
# Install UFW (if not installed)
sudo apt install ufw -y

# Allow SSH (IMPORTANT: do this first!)
sudo ufw allow OpenSSH

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status

# Expected output:
# Status: active
# To                         Action      From
# --                         ------      ----
# OpenSSH                    ALLOW       Anywhere
# Nginx Full                 ALLOW       Anywhere
```

---

## Performance Tuning

### Hardware Optimization

#### CPU and Memory
```bash
# Check current resources
htop

# Raspberry Pi-specific: Check temperature
vcgencmd measure_temp

# Check throttling status
vcgencmd get_throttled
# 0x0 = OK, 0x50000 = Throttled (needs cooling)
```

#### Swap Configuration
```bash
# Increase swap for memory-intensive operations
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Verify
free -h
```

### Uvicorn Worker Configuration

**For Raspberry Pi 4 (4GB):**
```bash
# In .env file
APEG_WORKERS=1              # Single worker for Pi 4
APEG_TIMEOUT=300            # 5-minute timeout
```

**For Raspberry Pi 5 (8GB):**
```bash
# In .env file
APEG_WORKERS=2              # Up to 2 workers for Pi 5
APEG_TIMEOUT=300
```

### Disable Unnecessary Services
```bash
# Free up RAM by disabling unused services
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

sudo systemctl disable cups
sudo systemctl stop cups

sudo systemctl disable avahi-daemon
sudo systemctl stop avahi-daemon
```

### Log Rotation
```bash
# Create log rotation config
sudo nano /etc/logrotate.d/apeg
```

**Configuration:**
```
/opt/apeg/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 pi pi
}
```

---

## Security Configuration

### ⚠️ CRITICAL WARNING
**DO NOT expose APEG API directly to the public internet without authentication.**

The default configuration has NO authentication. Anyone who can reach your server can execute workflows.

### Option 1: IP Allowlist (Nginx)

**Edit nginx configuration:**
```nginx
# Add inside server block (before location /)
# Allow specific IPs
allow 192.168.1.0/24;   # Local network
allow 203.0.113.5;      # Your office IP
deny all;               # Deny everyone else
```

### Option 2: API Key Authentication

**Modify `src/apeg_core/server.py`:**
```python
from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("APEG_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if not key or key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key

# Add to protected endpoints:
@app.post("/run", dependencies=[Depends(verify_api_key)])
async def run_workflow(request: WorkflowRequest):
    # ... existing code
```

**Usage:**
```bash
# Set in .env
APEG_API_KEY=your-secret-key-here

# Call API with key
curl -H "X-API-Key: your-secret-key-here" \
  https://apeg.yourdomain.com/run \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"goal": "test workflow"}'
```

### Option 3: Basic Authentication (Nginx)

**Create password file:**
```bash
sudo apt install apache2-utils -y
sudo htpasswd -c /etc/nginx/.htpasswd apeguser
```

**Add to nginx configuration:**
```nginx
location / {
    auth_basic "APEG API";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_pass http://127.0.0.1:8000;
    # ... rest of proxy config
}
```

### Secrets Management

**NEVER commit .env file:**
```bash
# Verify .env is gitignored
git check-ignore .env
# Should output: .env

# If not, add to .gitignore
echo ".env" >> .gitignore
```

**Use systemd environment file:**
```bash
# Create production env file
sudo nano /opt/apeg/.env.production

# Set permissions (owner read-only)
sudo chmod 600 /opt/apeg/.env.production
sudo chown pi:pi /opt/apeg/.env.production

# Reference in systemd service
# EnvironmentFile=/opt/apeg/.env.production
```

---

## Troubleshooting

### Service Won't Start

**Symptoms:**
- `systemctl status apeg` shows "failed" or "inactive"
- Service exits immediately

**Diagnosis:**
```bash
# Check logs
sudo journalctl -u apeg -n 50 --no-pager

# Common issues:
# 1. Python interpreter not found
which /opt/apeg/.venv/bin/python

# 2. Working directory doesn't exist
ls -la /opt/apeg

# 3. Permission issues
ls -la /opt/apeg/.env
sudo chown pi:pi /opt/apeg/.env

# 4. Missing dependencies
cd /opt/apeg && source .venv/bin/activate && pip list

# 5. Port already in use
sudo netstat -tlnp | grep 8000
```

**Resolution:**
```bash
# Fix permissions
cd /opt/apeg
sudo chown -R pi:pi .

# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Test manually
python -m apeg_core.server
# Press Ctrl+C, check for errors

# Restart service
sudo systemctl restart apeg
```

### Health Check Fails

**Symptoms:**
- `curl http://localhost:8000/health` times out or returns error
- 502 Bad Gateway from nginx

**Diagnosis:**
```bash
# Check if process is running
ps aux | grep apeg

# Check port binding
sudo netstat -tlnp | grep 8000

# Test direct connection
curl -v http://127.0.0.1:8000/health
```

**Resolution:**
```bash
# If process not running, check service status
sudo systemctl status apeg

# If port conflict, identify process
sudo lsof -i :8000
# Kill conflicting process or change APEG_PORT

# If firewall blocking
sudo ufw allow 8000/tcp
```

### High Memory Usage

**Symptoms:**
- System becomes unresponsive
- OOM (Out of Memory) errors in logs

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check APEG process
ps aux | grep apeg
```

**Resolution:**
```bash
# Reduce workers in .env
nano /opt/apeg/.env
# Set: APEG_WORKERS=1

# Increase swap (if using SD card, consider USB storage)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Increase CONF_SWAPSIZE
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Restart service
sudo systemctl restart apeg
```

### SSL Certificate Issues

**Symptoms:**
- Browser shows "Certificate not trusted" or "Connection not secure"
- Certbot renewal fails

**Diagnosis:**
```bash
# Check certificate status
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run
```

**Resolution:**
```bash
# Renew certificates
sudo certbot renew

# If renewal fails, check:
# 1. Port 80 open for verification
sudo ufw status | grep 80

# 2. Nginx serving .well-known
curl http://yourdomain.com/.well-known/acme-challenge/test

# 3. DNS records correct
nslookup yourdomain.com

# Force renewal
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### API Errors

**Symptoms:**
- Workflows fail with API errors
- "Rate limit exceeded" messages

**Diagnosis:**
```bash
# Check API keys set
cd /opt/apeg
grep OPENAI_API_KEY .env | wc -l
# Should be > 0

# Check test mode
grep APEG_TEST_MODE .env
# If true, switch to false for production

# Check logs for specific errors
sudo journalctl -u apeg -n 100 | grep -i "error\|fail"
```

**Resolution:**
```bash
# Verify API keys valid
# OpenAI: https://platform.openai.com/api-keys
# Shopify: https://partners.shopify.com/
# Etsy: https://www.etsy.com/developers/

# Update .env
nano /opt/apeg/.env

# Restart service
sudo systemctl restart apeg

# Test with simple workflow
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"goal": "test connection"}'
```

---

## Maintenance Checklist

### Daily
- [ ] Check service status: `sudo systemctl status apeg`
- [ ] Review logs for errors: `sudo journalctl -u apeg --since today`
- [ ] Monitor disk space: `df -h`
- [ ] Check temperature: `vcgencmd measure_temp`

### Weekly
- [ ] Review workflow execution logs
- [ ] Check SSL certificate expiry: `sudo certbot certificates`
- [ ] Backup configuration files
- [ ] Update system packages: `sudo apt update && sudo apt upgrade`

### Monthly
- [ ] Review and rotate logs
- [ ] Check for APEG updates: `git pull`
- [ ] Test disaster recovery procedure
- [ ] Review API usage and costs

---

## Additional Resources

- **GitHub Repository:** https://github.com/Matthewtgordon/PEG
- **APEG Documentation:** `docs/APEG_STATUS.md`
- **API Documentation:** https://your-domain.com/docs (when running)
- **Raspberry Pi Documentation:** https://www.raspberrypi.com/documentation/
- **Nginx Documentation:** https://nginx.org/en/docs/
- **Let's Encrypt:** https://letsencrypt.org/docs/

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `sudo journalctl -u apeg -n 100`
3. Validate configuration: `python validate_repo.py`
4. Open GitHub issue with logs and error messages

---

**Document Version:** 1.0
**Last Updated:** 2025-11-20
**Maintained By:** APEG Development Team
