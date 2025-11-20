# APEG Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-20
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Standard Deployment](#standard-deployment)
4. [Raspberry Pi Deployment](#raspberry-pi-deployment)
5. [Security Hardening](#security-hardening)
6. [Service Management](#service-management)
7. [Monitoring and Logs](#monitoring-and-logs)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)

---

## Overview

This guide covers production deployment of the APEG (Autonomous Prompt Engineering Graph) system on Linux servers, including specialized guidance for Raspberry Pi deployments.

### Deployment Options

- **Standalone Mode**: Run APEG workflows via CLI
- **Web Server Mode**: FastAPI web server with UI (port 8000)
- **Systemd Service**: Background daemon with automatic restart
- **Nginx Reverse Proxy**: Production-ready HTTPS setup

### System Requirements

**Minimum (Raspberry Pi 4)**:
- CPU: 4-core ARM Cortex-A72 (or equivalent x86_64)
- RAM: 4 GB (8 GB recommended)
- Storage: 16 GB available (32 GB+ recommended)
- OS: Ubuntu 22.04 LTS or Debian 11+

**Recommended (Standard Server)**:
- CPU: 4+ cores (x86_64)
- RAM: 8 GB+
- Storage: 50 GB+ SSD
- OS: Ubuntu 22.04 LTS

---

## Prerequisites

### 1. Python Environment

```bash
# Install Python 3.8-3.12 (recommended: 3.11)
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# Verify installation
python3.11 --version
```

### 2. System Dependencies

```bash
# Install required system packages
sudo apt install -y \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    nginx \
    supervisor

# For Raspberry Pi, also install:
sudo apt install -y libraspberrypi-bin
```

### 3. Create Deployment User

```bash
# Create dedicated user for APEG
sudo useradd -r -m -s /bin/bash apeg

# Add to necessary groups
sudo usermod -aG www-data apeg
```

---

## Standard Deployment

### Step 1: Clone Repository

```bash
# Switch to apeg user
sudo su - apeg

# Clone repository
cd /opt
sudo git clone https://github.com/Matthewtgordon/PEG.git apeg
sudo chown -R apeg:apeg /opt/apeg

# Enter directory
cd /opt/apeg
```

### Step 2: Set Up Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install APEG with dependencies
pip install -e ".[dev]"
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.sample .env

# Edit environment file
nano .env
```

**Required Environment Variables**:

```bash
# OpenAI API (Required)
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
OPENAI_DEFAULT_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2048

# Core Settings
APEG_TEST_MODE=false
APEG_USE_LLM_SCORING=true
APEG_RULE_WEIGHT=0.6

# Optional: E-commerce Integrations
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat-YOUR-TOKEN
ETSY_API_KEY=your-etsy-key
ETSY_SHOP_ID=12345678
ETSY_ACCESS_TOKEN=your-etsy-token

# Optional: GitHub Integration
GITHUB_PAT=ghp-YOUR-PERSONAL-ACCESS-TOKEN
```

### Step 4: Validate Installation

```bash
# Validate environment
python -m apeg_core validate

# Run test suite
APEG_TEST_MODE=true pytest tests/ -v

# Expected: 140+ tests passing
```

### Step 5: Test Web Server

```bash
# Start web server (development mode)
python -m apeg_core serve --reload

# In another terminal, test API
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"..."}
```

---

## Raspberry Pi Deployment

### Performance Optimizations

#### 1. Swap Configuration

```bash
# Increase swap for better performance
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile

# Set CONF_SWAPSIZE=2048 (2 GB)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### 2. Memory Optimization

```bash
# Reduce GPU memory (headless setup)
sudo nano /boot/config.txt

# Add or modify:
gpu_mem=16

# Reboot for changes to take effect
sudo reboot
```

#### 3. CPU Governor

```bash
# Set CPU to performance mode
sudo apt install -y cpufrequtils

echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

#### 4. Python Optimizations

```bash
# Use PyPy for better performance (optional)
sudo apt install -y pypy3 pypy3-dev

# Or compile Python with optimizations
export PYTHON_CONFIGURE_OPTS="--enable-optimizations"
```

#### 5. Disable Unnecessary Services

```bash
# Disable Bluetooth (if not needed)
sudo systemctl disable bluetooth.service

# Disable WiFi power management
sudo iwconfig wlan0 power off

# Add to /etc/rc.local for persistence:
/sbin/iwconfig wlan0 power off
```

---

## Security Hardening

### 1. File Permissions

```bash
# Set proper ownership
sudo chown -R apeg:apeg /opt/apeg

# Protect .env file
chmod 600 /opt/apeg/.env

# Protect configuration files
chmod 640 /opt/apeg/*.json

# Protect logs
chmod 750 /opt/apeg/logs
```

### 2. Firewall Configuration

```bash
# Install UFW (Uncomplicated Firewall)
sudo apt install -y ufw

# Allow SSH (if needed)
sudo ufw allow 22/tcp

# Allow Nginx (HTTPS only)
sudo ufw allow 'Nginx Full'

# Deny direct access to APEG port
sudo ufw deny 8000/tcp

# Enable firewall
sudo ufw enable
```

### 3. API Key Security

**Best Practices**:

1. **Never commit .env to version control**
   ```bash
   # Verify .env is gitignored
   git check-ignore .env
   ```

2. **Use environment-specific keys**
   - Development: Limited permissions
   - Production: Full permissions with IP restrictions

3. **Rotate keys regularly**
   ```bash
   # Rotate OpenAI API key every 90 days
   # Rotate Shopify/Etsy tokens every 180 days
   ```

4. **Monitor API usage**
   ```bash
   # Check OpenAI usage dashboard
   # Set up billing alerts
   ```

### 4. Nginx Security Headers

```nginx
# /etc/nginx/sites-available/apeg

server {
    listen 443 ssl http2;
    server_name apeg.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/apeg.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/apeg.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=apeg_limit:10m rate=10r/s;
    limit_req zone=apeg_limit burst=20 nodelay;

    # Proxy to APEG
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Access and Error Logs
    access_log /var/log/nginx/apeg_access.log;
    error_log /var/log/nginx/apeg_error.log;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name apeg.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 5. SSL Certificate Setup

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d apeg.yourdomain.com

# Auto-renewal (cron job)
sudo crontab -e

# Add:
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### 6. API Security & Access Control

**Important**: The APEG HTTP API does not have built-in authentication by default. Exposing the raw API to the public internet without additional security measures is **NOT SUPPORTED**.

#### Recommended Authentication Options

**Option 1: IP Allowlist (Simplest)**

```nginx
# In /etc/nginx/sites-available/apeg
location / {
    # Allow specific IPs only
    allow 192.168.1.0/24;    # Local network
    allow 203.0.113.10;      # Specific trusted IP
    deny all;

    proxy_pass http://127.0.0.1:8000;
    # ... other proxy settings
}
```

**Option 2: Shared Secret Header**

```nginx
# In /etc/nginx/sites-available/apeg
location / {
    # Require secret header
    if ($http_x_apeg_secret != "your-secret-token-here") {
        return 403;
    }

    proxy_pass http://127.0.0.1:8000;
    # ... other proxy settings
}
```

Client usage:
```bash
curl -H "X-APEG-Secret: your-secret-token-here" https://apeg.yourdomain.com/health
```

**Option 3: HTTP Basic Auth (nginx)**

```bash
# Create password file
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd apeg_user

# Update nginx config
sudo nano /etc/nginx/sites-available/apeg
```

```nginx
location / {
    auth_basic "APEG Restricted Area";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_pass http://127.0.0.1:8000;
    # ... other proxy settings
}
```

**Option 4: OAuth2/JWT Proxy (Advanced)**

For production environments requiring fine-grained access control:

```bash
# Use OAuth2 Proxy or similar
# https://github.com/oauth2-proxy/oauth2-proxy

# Example with Google OAuth:
docker run -d \
  --name oauth2-proxy \
  -p 4180:4180 \
  quay.io/oauth2-proxy/oauth2-proxy:latest \
  --upstream=http://localhost:8000/ \
  --provider=google \
  --client-id=YOUR_CLIENT_ID \
  --client-secret=YOUR_CLIENT_SECRET \
  --cookie-secret=RANDOM_SECRET_HERE \
  --email-domain=yourdomain.com
```

#### Access Control Best Practices

1. **Never expose APEG port 8000 directly to the internet**
   ```bash
   # Always bind to localhost only
   python -m apeg_core serve --host 127.0.0.1 --port 8000

   # Block external access with firewall
   sudo ufw deny 8000/tcp
   ```

2. **Use HTTPS for all external access**
   - HTTP connections should redirect to HTTPS
   - Configure strong TLS ciphers (see Nginx config above)

3. **Implement rate limiting**
   - Prevent abuse and DoS attacks
   - nginx example: `limit_req_zone` (see section 4 above)

4. **Monitor access logs**
   ```bash
   # Watch for suspicious activity
   sudo tail -f /var/log/nginx/apeg_access.log

   # Alert on failed auth attempts
   grep "403" /var/log/nginx/apeg_access.log | tail
   ```

5. **Restrict API endpoints if possible**
   ```nginx
   # Allow only specific endpoints
   location = /health {
       # Public health check
       proxy_pass http://127.0.0.1:8000;
   }

   location / {
       # Protected admin endpoints
       auth_basic "Admin Area";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://127.0.0.1:8000;
   }
   ```

6. **Use VPN for sensitive deployments**
   - For internal tools, require VPN connection
   - Tools: WireGuard, OpenVPN, Tailscale

#### Security Audit Checklist

- [ ] APEG API not directly exposed to internet (port 8000 blocked)
- [ ] All external access goes through nginx reverse proxy
- [ ] HTTPS configured with valid SSL certificate
- [ ] Authentication enabled (IP allowlist, shared secret, or OAuth)
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Access logs monitored regularly
- [ ] .env file permissions set to 600
- [ ] API keys rotated on schedule

**For more security hardening, see:** `docs/SECURITY_HARDENING.md`

---

## Service Management

### Systemd Service Setup

#### 1. Create Service File

```bash
# Create systemd service file
sudo nano /etc/systemd/system/apeg.service
```

**Service Configuration**:

```ini
[Unit]
Description=APEG - Autonomous Prompt Engineering Graph
After=network.target

[Service]
Type=simple
User=apeg
Group=apeg
WorkingDirectory=/opt/apeg
Environment="PATH=/opt/apeg/venv/bin"
EnvironmentFile=/opt/apeg/.env
ExecStart=/opt/apeg/venv/bin/python -m apeg_core serve --host 0.0.0.0 --port 8000

# Restart configuration
Restart=always
RestartSec=10s

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/apeg

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=apeg

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable apeg

# Start service
sudo systemctl start apeg

# Check status
sudo systemctl status apeg
```

#### 3. Service Management Commands

```bash
# Start service
sudo systemctl start apeg

# Stop service
sudo systemctl stop apeg

# Restart service
sudo systemctl restart apeg

# Reload configuration
sudo systemctl reload apeg

# View logs
sudo journalctl -u apeg -f

# View last 100 lines
sudo journalctl -u apeg -n 100
```

---

## Monitoring and Logs

### 1. Log Files

**APEG Logs**:
```bash
# Application logs
/opt/apeg/Logbook.json
/opt/apeg/Journal.json

# Systemd journal
sudo journalctl -u apeg

# Nginx logs
/var/log/nginx/apeg_access.log
/var/log/nginx/apeg_error.log
```

### 2. Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/apeg
```

**Configuration**:

```
/opt/apeg/*.json {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
```

### 3. Health Monitoring

```bash
# Create health check script
sudo nano /usr/local/bin/apeg-healthcheck.sh
```

**Health Check Script**:

```bash
#!/bin/bash
# APEG Health Check Script

APEG_URL="http://localhost:8000/health"
ALERT_EMAIL="admin@yourdomain.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $APEG_URL)

if [ "$response" != "200" ]; then
    echo "APEG health check failed: HTTP $response" | \
        mail -s "APEG Alert: Service Unhealthy" $ALERT_EMAIL

    # Auto-restart service
    sudo systemctl restart apeg
fi
```

**Add to Crontab**:

```bash
# Check every 5 minutes
*/5 * * * * /usr/local/bin/apeg-healthcheck.sh
```

### 4. Performance Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor APEG process
ps aux | grep apeg_core

# Monitor memory usage
free -h

# Monitor disk usage
df -h

# Monitor I/O
sudo iotop -p $(pgrep -f apeg_core)
```

---

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

**Check logs**:
```bash
sudo journalctl -u apeg -n 50
```

**Common causes**:
- Missing environment variables
- Port 8000 already in use
- Permission issues
- Missing dependencies

**Solutions**:
```bash
# Check port usage
sudo lsof -i :8000

# Fix permissions
sudo chown -R apeg:apeg /opt/apeg

# Validate environment
sudo -u apeg bash -c "cd /opt/apeg && source venv/bin/activate && python -m apeg_core validate"
```

#### 2. API Calls Failing

**Check environment**:
```bash
# Verify API keys
sudo -u apeg bash -c "cd /opt/apeg && source .env && echo \$OPENAI_API_KEY | head -c 20"
```

**Test connectivity**:
```bash
# Test OpenAI API
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 3. High Memory Usage

**Raspberry Pi specific**:
```bash
# Check swap usage
free -h

# Restart service to clear memory
sudo systemctl restart apeg

# Reduce worker count (if using uvicorn workers)
# Edit /etc/systemd/system/apeg.service
# ExecStart=/opt/apeg/venv/bin/python -m apeg_core serve --workers 1
```

#### 4. Slow Performance

**Check CPU throttling** (Raspberry Pi):
```bash
# Check current frequency
vcgencmd measure_clock arm

# Check temperature
vcgencmd measure_temp

# If overheating, add cooling
```

**Optimize Python**:
```bash
# Use PyPy instead of CPython
sudo apt install pypy3
```

---

## Backup and Recovery

### 1. Backup Strategy

**What to Backup**:
- Configuration files: `*.json`
- Environment file: `.env` (encrypted)
- Knowledge base: `Knowledge.json`
- Logs: `Logbook.json`, `Journal.json`

**Backup Script**:

```bash
#!/bin/bash
# /usr/local/bin/apeg-backup.sh

BACKUP_DIR="/var/backups/apeg"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/apeg_backup_$DATE.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create encrypted backup
tar -czf - -C /opt/apeg \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    . | gpg --symmetric --cipher-algo AES256 > $BACKUP_FILE.gpg

# Keep only last 30 backups
find $BACKUP_DIR -name "apeg_backup_*.tar.gz.gpg" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gpg"
```

**Add to Crontab**:
```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/apeg-backup.sh
```

### 2. Restore Procedure

```bash
# Stop service
sudo systemctl stop apeg

# Decrypt and extract backup
cd /opt/apeg
gpg --decrypt /var/backups/apeg/apeg_backup_YYYYMMDD_HHMMSS.tar.gz.gpg | tar -xzf -

# Fix permissions
sudo chown -R apeg:apeg /opt/apeg

# Validate
sudo -u apeg bash -c "cd /opt/apeg && source venv/bin/activate && python -m apeg_core validate"

# Start service
sudo systemctl start apeg
```

### 3. Disaster Recovery

**GitHub Recovery** (if enabled):
```bash
# APEG supports GitHub-based recovery
# Ensure GITHUB_PAT is set in .env

# Trigger recovery
python -m apeg_core --config-recovery github
```

---

## Production Checklist

### Pre-Deployment

- [ ] Python 3.11 installed
- [ ] All system dependencies installed
- [ ] APEG installed in virtual environment
- [ ] `.env` file configured with all required keys
- [ ] Environment validation passes: `python -m apeg_core validate`
- [ ] Test suite passes: `pytest tests/ -v`

### Security

- [ ] `.env` file permissions set to 600
- [ ] Firewall configured (UFW)
- [ ] SSL certificate installed (Certbot)
- [ ] Nginx security headers configured
- [ ] Rate limiting enabled
- [ ] API keys rotated to production keys
- [ ] Backup encryption configured

### Service Setup

- [ ] Systemd service file created
- [ ] Service enabled: `systemctl enable apeg`
- [ ] Service started and healthy: `systemctl status apeg`
- [ ] Nginx reverse proxy configured
- [ ] Nginx enabled and reloaded

### Monitoring

- [ ] Log rotation configured
- [ ] Health check cron job added
- [ ] Backup cron job added
- [ ] Performance monitoring tools installed
- [ ] Alert email configured

### Post-Deployment

- [ ] Test web UI accessible
- [ ] Test API health endpoint
- [ ] Test workflow execution
- [ ] Verify logs are being written
- [ ] Verify backups are created
- [ ] Monitor for 24 hours

---

## Additional Resources

### Documentation

- [Phase 8 Requirements](./APEG_PHASE_8_REQUIREMENTS.md)
- [APEG Status](./APEG_STATUS.md)
- [Project Conventions](../CLAUDE.md)

### Support

- **Issues**: https://github.com/Matthewtgordon/PEG/issues
- **Project Board**: https://github.com/Matthewtgordon/PEG/projects

### External References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-20
**Maintainer:** APEG Development Team
