# APEG Security Hardening Checklist

**Version:** 1.0.0
**Last Updated:** 2025-11-20
**Purpose:** Production security checklist for APEG deployments

---

## Overview

This checklist ensures APEG deployments follow security best practices for protecting API keys, data, and system resources.

---

## Pre-Deployment Security

### Environment Variables

- [ ] **Never commit `.env` file to version control**
  ```bash
  # Verify .env is gitignored
  git check-ignore .env
  # Expected output: .env
  ```

- [ ] **Use strong, unique API keys for production**
  - OpenAI API key: Separate from development
  - Shopify/Etsy tokens: Production credentials only
  - GitHub PAT: Minimal required scopes

- [ ] **Set proper file permissions for `.env`**
  ```bash
  chmod 600 /opt/apeg/.env
  chown apeg:apeg /opt/apeg/.env
  ```

- [ ] **Validate all required environment variables**
  ```bash
  python -m apeg_core validate
  ```

### Configuration Files

- [ ] **Protect JSON configuration files**
  ```bash
  chmod 640 /opt/apeg/*.json
  chown apeg:apeg /opt/apeg/*.json
  ```

- [ ] **Review Knowledge.json for sensitive data**
  - No hardcoded credentials
  - No personal information
  - No internal URLs/IPs

- [ ] **Enable configuration versioning**
  - Use git for configuration tracking
  - Regular backups of configuration state

---

## System Security

### User and Group Permissions

- [ ] **Run APEG as dedicated non-root user**
  ```bash
  # Create apeg user
  sudo useradd -r -m -s /bin/bash apeg

  # Verify user has no sudo access
  sudo -l -U apeg
  ```

- [ ] **Set proper directory ownership**
  ```bash
  sudo chown -R apeg:apeg /opt/apeg
  chmod 750 /opt/apeg
  ```

- [ ] **Restrict log file access**
  ```bash
  mkdir -p /opt/apeg/logs
  chmod 750 /opt/apeg/logs
  chown apeg:apeg /opt/apeg/logs
  ```

### Firewall Configuration

- [ ] **Install and configure UFW (Uncomplicated Firewall)**
  ```bash
  sudo apt install -y ufw
  ```

- [ ] **Allow only necessary ports**
  ```bash
  # SSH (if needed)
  sudo ufw allow 22/tcp

  # HTTPS only (via Nginx)
  sudo ufw allow 443/tcp

  # HTTP (for Let's Encrypt only)
  sudo ufw allow 80/tcp

  # Deny direct access to APEG port
  sudo ufw deny 8000/tcp
  ```

- [ ] **Enable firewall**
  ```bash
  sudo ufw enable
  sudo ufw status verbose
  ```

- [ ] **Configure rate limiting** (optional)
  ```bash
  sudo ufw limit 22/tcp
  sudo ufw limit 443/tcp
  ```

### SSH Hardening

- [ ] **Disable root login**
  ```bash
  sudo nano /etc/ssh/sshd_config
  # Set: PermitRootLogin no
  sudo systemctl restart sshd
  ```

- [ ] **Use SSH keys instead of passwords**
  ```bash
  # Set: PasswordAuthentication no
  # Set: PubkeyAuthentication yes
  ```

- [ ] **Change default SSH port** (optional)
  ```bash
  # Set: Port 2222
  # Update firewall: sudo ufw allow 2222/tcp
  ```

---

## Application Security

### API Key Management

- [ ] **Use environment-specific keys**
  - Development: Limited permissions, low rate limits
  - Staging: Medium permissions, moderate rate limits
  - Production: Full permissions, high rate limits

- [ ] **Implement key rotation schedule**
  - OpenAI: Every 90 days
  - Shopify/Etsy: Every 180 days
  - GitHub PAT: Every 365 days

- [ ] **Set up billing alerts**
  - OpenAI: Set monthly budget cap
  - Monitor API usage daily

- [ ] **Use API key scoping** (where available)
  - Shopify: Minimal required scopes (read_products, write_products, etc.)
  - GitHub: Minimal required scopes (repo, read:org)
  - Etsy: OAuth with refresh tokens

- [ ] **Monitor API key usage**
  ```bash
  # Check OpenAI usage
  # Dashboard: https://platform.openai.com/usage

  # Check Shopify API usage
  # Check X-Shopify-Shop-Api-Call-Limit header
  ```

### Input Validation

- [ ] **Validate all user inputs**
  - Prompt length limits
  - JSON schema validation
  - File upload restrictions

- [ ] **Sanitize outputs**
  - Remove sensitive data from logs
  - Mask API keys in error messages

- [ ] **Implement rate limiting**
  - Per-user request limits
  - Global throughput limits

### LLM Security

- [ ] **Use APEG_TEST_MODE for testing**
  ```bash
  # Never use real API calls in tests
  APEG_TEST_MODE=true pytest tests/
  ```

- [ ] **Implement prompt injection protection**
  - Validate prompt structure
  - Sanitize user-provided prompts
  - Use system prompts to set boundaries

- [ ] **Monitor LLM outputs for sensitive data**
  - No API keys in responses
  - No credentials in generated content
  - Review SCORER outputs for leaks

- [ ] **Set appropriate model parameters**
  ```bash
  OPENAI_TEMPERATURE=0.7  # Not too creative
  OPENAI_MAX_TOKENS=2048  # Reasonable limit
  ```

---

## Network Security

### Nginx Configuration

- [ ] **Install and configure Nginx**
  ```bash
  sudo apt install -y nginx
  ```

- [ ] **Use HTTPS only**
  ```bash
  # Install Certbot
  sudo apt install -y certbot python3-certbot-nginx

  # Obtain certificate
  sudo certbot --nginx -d apeg.yourdomain.com
  ```

- [ ] **Configure security headers**
  ```nginx
  # /etc/nginx/sites-available/apeg
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Referrer-Policy "no-referrer-when-downgrade" always;
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
  ```

- [ ] **Implement rate limiting**
  ```nginx
  limit_req_zone $binary_remote_addr zone=apeg_limit:10m rate=10r/s;
  limit_req zone=apeg_limit burst=20 nodelay;
  ```

- [ ] **Disable unnecessary HTTP methods**
  ```nginx
  if ($request_method !~ ^(GET|POST|PUT|DELETE|HEAD)$ ) {
      return 405;
  }
  ```

- [ ] **Hide Nginx version**
  ```nginx
  # /etc/nginx/nginx.conf
  server_tokens off;
  ```

### SSL/TLS Configuration

- [ ] **Use strong ciphers**
  ```nginx
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
  ssl_prefer_server_ciphers on;
  ```

- [ ] **Enable OCSP stapling**
  ```nginx
  ssl_stapling on;
  ssl_stapling_verify on;
  ssl_trusted_certificate /etc/letsencrypt/live/apeg.yourdomain.com/chain.pem;
  ```

- [ ] **Set up automatic certificate renewal**
  ```bash
  # Add to crontab
  0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
  ```

- [ ] **Test SSL configuration**
  ```bash
  # Use SSL Labs test
  # https://www.ssllabs.com/ssltest/
  ```

---

## Data Security

### Backup Encryption

- [ ] **Encrypt backups**
  ```bash
  # Use GPG for encryption
  tar -czf - /opt/apeg | gpg --symmetric --cipher-algo AES256 > backup.tar.gz.gpg
  ```

- [ ] **Use strong encryption passphrase**
  - Minimum 20 characters
  - Mix of letters, numbers, symbols
  - Store securely (password manager)

- [ ] **Store backups securely**
  - Off-site storage (S3, Backblaze, etc.)
  - Encrypted at rest and in transit
  - Regular testing of restore procedure

### Database Security (if applicable)

- [ ] **Use encrypted connections**
  - PostgreSQL: require SSL
  - MySQL: require TLS

- [ ] **Implement least privilege**
  - Separate read/write users
  - Application-specific credentials
  - No root/admin access from application

- [ ] **Regular backups**
  - Daily automated backups
  - Off-site storage
  - Encrypted backups

### Log Security

- [ ] **Sanitize logs**
  ```python
  # Never log full API keys
  logger.info(f"Using API key: {api_key[:10]}...")

  # Never log passwords or tokens
  # Never log full request bodies (may contain sensitive data)
  ```

- [ ] **Protect log files**
  ```bash
  chmod 640 /var/log/apeg/*.log
  chown apeg:adm /var/log/apeg/*.log
  ```

- [ ] **Implement log rotation**
  ```bash
  # /etc/logrotate.d/apeg
  /var/log/apeg/*.log {
      daily
      rotate 30
      compress
      delaycompress
      notifempty
      missingok
      create 640 apeg adm
  }
  ```

- [ ] **Monitor logs for security events**
  - Failed authentication attempts
  - Unusual API usage patterns
  - Error spikes

---

## Monitoring and Alerting

### Health Monitoring

- [ ] **Set up health checks**
  ```bash
  # Cron job every 5 minutes
  */5 * * * * /usr/local/bin/apeg-healthcheck.sh
  ```

- [ ] **Configure alerts**
  - Email alerts for service failures
  - Slack/PagerDuty for critical issues
  - SMS for high-severity incidents

- [ ] **Monitor resource usage**
  ```bash
  # CPU, memory, disk
  htop
  free -h
  df -h
  ```

### Security Monitoring

- [ ] **Enable audit logging**
  ```bash
  # Install auditd
  sudo apt install -y auditd

  # Monitor /opt/apeg directory
  sudo auditctl -w /opt/apeg -p wa -k apeg_changes
  ```

- [ ] **Monitor failed login attempts**
  ```bash
  # Install fail2ban
  sudo apt install -y fail2ban

  # Configure for SSH
  sudo systemctl enable fail2ban
  ```

- [ ] **Set up intrusion detection** (optional)
  ```bash
  # Install AIDE
  sudo apt install -y aide
  sudo aideinit
  ```

- [ ] **Review logs regularly**
  ```bash
  # Daily review of:
  # - /var/log/auth.log (authentication)
  # - /var/log/nginx/access.log (web access)
  # - /var/log/apeg/*.log (application logs)
  # - journalctl -u apeg (systemd logs)
  ```

---

## Incident Response

### Preparation

- [ ] **Document incident response plan**
  - Contact information
  - Escalation procedures
  - Recovery procedures

- [ ] **Test backup restoration**
  ```bash
  # Monthly restore test
  # Verify backups are complete and valid
  ```

- [ ] **Maintain runbook for common incidents**
  - Service failures
  - API key compromises
  - Data breaches
  - DDoS attacks

### Response Procedures

- [ ] **API Key Compromise Response**
  1. Immediately revoke compromised key
  2. Generate new key
  3. Update `.env` file
  4. Restart service
  5. Review logs for unauthorized usage
  6. Notify affected parties (if applicable)

- [ ] **Data Breach Response**
  1. Isolate affected systems
  2. Preserve evidence
  3. Identify scope of breach
  4. Notify stakeholders
  5. Implement remediation
  6. Post-incident review

- [ ] **Service Disruption Response**
  1. Check service status
  2. Review recent logs
  3. Attempt restart
  4. Escalate if necessary
  5. Communicate status to users

---

## Compliance and Auditing

### GDPR Compliance (if applicable)

- [ ] **Data minimization**
  - Collect only necessary data
  - Implement data retention policies

- [ ] **User consent**
  - Obtain consent for data processing
  - Provide opt-out mechanisms

- [ ] **Data portability**
  - Provide user data export
  - Support data deletion requests

- [ ] **Privacy by design**
  - Encrypt data at rest and in transit
  - Implement access controls

### Audit Trail

- [ ] **Log all configuration changes**
  ```json
  // Knowledge.json metadata
  "operation_log": [
    {
      "timestamp": "2025-11-20T12:00:00+00:00",
      "operation": "update_knowledge_item",
      "user": "admin",
      "item_id": "uuid"
    }
  ]
  ```

- [ ] **Track API usage**
  - OpenAI: Review usage dashboard
  - Shopify: Check API call limits
  - Etsy: Monitor rate limits

- [ ] **Regular security audits**
  - Monthly: Review access logs
  - Quarterly: Security scan
  - Annually: Full security audit

---

## Additional Resources

### Security Tools

- **Vulnerability Scanning**:
  - [OWASP ZAP](https://www.zaproxy.org/)
  - [Nikto](https://cirt.net/Nikto2)
  - [Lynis](https://cisofy.com/lynis/)

- **Dependency Scanning**:
  - [Safety](https://pyup.io/safety/) - Python dependency checker
  - [Snyk](https://snyk.io/) - Vulnerability scanning

- **Secret Scanning**:
  - [git-secrets](https://github.com/awslabs/git-secrets)
  - [truffleHog](https://github.com/trufflesecurity/truffleHog)

### Best Practices

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

## Security Checklist Summary

**Critical (Must Complete)**:
- [x] File permissions configured
- [x] Firewall enabled
- [x] SSL/TLS configured
- [x] API keys secured
- [x] Backups encrypted
- [x] Service running as non-root user

**Recommended (Should Complete)**:
- [x] Rate limiting enabled
- [x] Security headers configured
- [x] Monitoring and alerting set up
- [x] Log rotation configured
- [x] SSH hardened
- [x] Incident response plan documented

**Optional (Nice to Have)**:
- [ ] Intrusion detection configured
- [ ] Security auditing tools installed
- [ ] Compliance framework implemented
- [ ] Regular penetration testing

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-20
**Next Review:** 2026-02-20 (90 days)
