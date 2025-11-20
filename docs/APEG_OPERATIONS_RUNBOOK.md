# APEG Operations Runbook

**Version:** 1.0.0
**Last Updated:** 2025-11-20
**Status:** PLANNING

---

## Table of Contents

1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [Nightly Jobs](#nightly-jobs)
4. [Incident Response](#incident-response)
5. [Maintenance Tasks](#maintenance-tasks)
6. [Configuration Management](#configuration-management)
7. [Monitoring and Alerts](#monitoring-and-alerts)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This runbook documents standard operating procedures for running and maintaining APEG in production. It defines:
- Routine operational tasks
- Automated job schedules
- Incident response procedures
- Configuration rollout processes

### Audience

- DevOps engineers
- Site reliability engineers (SRE)
- On-call responders
- Platform administrators

### Prerequisites

- APEG deployed and configured (see `docs/DEPLOYMENT.md`)
- Access to production environment
- Familiarity with APEG architecture
- CLI access configured

---

## Daily Operations

### Morning Health Check

**Frequency:** Daily at 9:00 AM (local time)

**Steps:**

1. **Check Service Status**
   ```bash
   sudo systemctl status apeg.service
   ```

   Expected: `active (running)`

2. **Verify API Health**
   ```bash
   curl https://apeg.yourdomain.com/health
   ```

   Expected:
   ```json
   {"status": "healthy", "version": "1.0.0", "timestamp": "..."}
   ```

3. **Review Overnight Logs**
   ```bash
   sudo journalctl -u apeg.service --since "yesterday" --priority err
   ```

   Expected: No errors (or only known non-critical errors)

4. **Check Logbook for Issues**
   ```bash
   python -m apeg_core review-logs --since 24h --errors-only
   ```

   Expected: Review flagged errors and take action if needed

5. **Verify API Key Validity**
   ```bash
   python -m apeg_core validate
   ```

   Expected: All API keys valid, no expiration warnings

**Alert Conditions:**
- Service not running → Page on-call
- Health check fails → Investigate immediately
- >10 errors in 24h → Review and triage

---

### Review Nightly Job Results

**Frequency:** Daily at 10:00 AM (after nightly jobs complete)

**Steps:**

1. **Check Job Completion**
   ```bash
   # View cron job logs
   sudo grep "apeg" /var/log/syslog | tail -50
   ```

2. **Review Feedback Reports**
   ```bash
   ls -ltr /opt/apeg/reports/feedback_*.json | tail -5
   cat /opt/apeg/reports/feedback_$(date +%Y-%m-%d).json | jq .summary
   ```

3. **Review Improvement Proposals (if generated)**
   ```bash
   ls -ltr /opt/apeg/proposals/*.md | tail -3
   ```

4. **Check Batch Operation Results**
   ```bash
   cat /opt/apeg/reports/inventory_sync_$(date +%Y-%m-%d).json | jq .summary
   ```

**Action Items:**
- Review proposals → Schedule review meeting if high-value improvements found
- Failed batch jobs → Investigate and re-run if transient failure
- Inventory discrepancies → Alert e-commerce team

---

## Nightly Jobs

### Schedule Overview

| Time    | Job                    | Command                                                   |
|---------|------------------------|-----------------------------------------------------------|
| 01:00   | Feedback Analysis      | `python -m apeg_core analyze-feedback --period 7d`       |
| 02:00   | Improvement Suggestions| `python -m apeg_core suggest-improvements`               |
| 03:00   | Inventory Sync         | `python -m apeg_core sync-inventory --execute`           |
| 04:00   | SEO Refresh            | `python -m apeg_core etsy-seo-analyze --threshold 10`     |
| 05:00   | Order Monitoring       | `python -m apeg_core monitor-orders --sla 48h`           |
| 06:00   | Logbook Archival       | `python -m apeg_core archive-logs --older-than 90d`      |

### Crontab Configuration

```bash
# Edit crontab
sudo crontab -e -u apeg

# Add these entries
0 1 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core analyze-feedback --period 7d --output /opt/apeg/reports/feedback_$(date +\%Y-\%m-\%d).json 2>&1 | logger -t apeg-feedback

0 2 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core suggest-improvements --from-report /opt/apeg/reports/feedback_$(date +\%Y-\%m-\%d).json --output /opt/apeg/proposals/improvements_$(date +\%Y-\%m-\%d).md 2>&1 | logger -t apeg-proposals

0 3 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core sync-inventory --execute --report /opt/apeg/reports/inventory_sync_$(date +\%Y-\%m-\%d).json 2>&1 | logger -t apeg-inventory

0 4 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core etsy-seo-analyze --threshold 10 --days 30 --output /opt/apeg/reports/seo_suggestions_$(date +\%Y-\%m-\%d).json 2>&1 | logger -t apeg-seo

0 5 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core monitor-orders --sla 48h --alert-email ops@example.com 2>&1 | logger -t apeg-orders

0 6 * * * cd /opt/apeg && /opt/apeg/venv/bin/python -m apeg_core archive-logs --older-than 90d 2>&1 | logger -t apeg-archive
```

### Job Failure Alerts

Configure email alerts for failed cron jobs:

```bash
# Install cronic for better cron output handling
sudo apt install -y cronic

# Modify crontab to use cronic
0 1 * * * cronic /opt/apeg/scripts/feedback_analysis.sh

# In feedback_analysis.sh:
#!/bin/bash
cd /opt/apeg
/opt/apeg/venv/bin/python -m apeg_core analyze-feedback --period 7d || {
    echo "ERROR: Feedback analysis failed" | mail -s "APEG Job Failure" ops@example.com
    exit 1
}
```

---

## Incident Response

### Severity Levels

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| P0 | Service down, critical outage | 15 minutes | APEG API unreachable |
| P1 | Degraded service, customer impact | 1 hour | Shopify sync failing |
| P2 | Non-critical feature broken | 4 hours | SEO suggestions not generating |
| P3 | Minor issue, no customer impact | 1 business day | Low test coverage warning |

### Incident Checklist

#### P0: Service Down

1. **Immediate Actions (0-5 min)**
   ```bash
   # Check service status
   sudo systemctl status apeg.service

   # Check recent logs
   sudo journalctl -u apeg.service --since "5 minutes ago"

   # Check resource usage
   top
   df -h
   ```

2. **Restart Service (5-10 min)**
   ```bash
   # Restart APEG
   sudo systemctl restart apeg.service

   # Verify health
   curl https://apeg.yourdomain.com/health
   ```

3. **If Restart Fails (10-15 min)**
   ```bash
   # Check configuration
   python -m apeg_core validate

   # Check dependencies
   pip list | grep -E "openai|fastapi|uvicorn"

   # Check port binding
   sudo lsof -i :8000

   # Check nginx
   sudo systemctl status nginx
   sudo nginx -t
   ```

4. **Escalation**
   - If not resolved in 15 min → Page senior engineer
   - Create incident ticket
   - Start incident log

#### P1: Degraded Service

1. **Assess Impact (0-15 min)**
   ```bash
   # Check what's failing
   python -m apeg_core review-logs --since 1h --errors-only

   # Check API rate limits
   # (check Shopify/Etsy/OpenAI dashboards)
   ```

2. **Temporary Mitigation (15-30 min)**
   ```bash
   # Disable failing integration
   # Edit SessionConfig.json to set test_mode=true for affected service

   # Restart to apply
   sudo systemctl restart apeg.service
   ```

3. **Root Cause Investigation (30-60 min)**
   - Review Logbook for failure patterns
   - Check external service status pages
   - Review recent configuration changes

4. **Resolution**
   - Apply fix
   - Re-enable integration
   - Monitor for 1 hour

#### P2: Non-Critical Feature Broken

1. **Document Issue**
   - Create GitHub issue
   - Add to known issues list

2. **Assess Workaround**
   - Can feature be disabled temporarily?
   - Is there a manual workaround?

3. **Schedule Fix**
   - Prioritize in next sprint
   - Assign to appropriate team

---

## Maintenance Tasks

### Weekly Tasks

#### Review Improvement Proposals (Every Monday)

**Time:** 30 minutes

**Steps:**
1. Collect all proposals from past week
   ```bash
   ls /opt/apeg/proposals/improvements_*.md | tail -7
   ```

2. Review each proposal:
   - Read description and rationale
   - Assess risk level
   - Check expected impact

3. Approve or reject:
   - Approved → Create GitHub PR with changes
   - Rejected → Document reason, archive proposal
   - Needs Discussion → Add to team meeting agenda

4. Track approved changes:
   ```bash
   # Apply approved changes
   cd /opt/apeg
   git checkout -b improvement-042

   # Apply config changes from proposal
   # ...

   # Validate
   python validate_repo.py
   pytest tests/

   # Commit
   git add .
   git commit -m "Apply improvement proposal #042: Increase OpenAI timeout"
   git push origin improvement-042

   # Create PR for review
   ```

#### Clean Up Old Reports (Every Friday)

**Time:** 10 minutes

**Steps:**
```bash
# Archive reports older than 90 days
cd /opt/apeg/reports
find . -name "*.json" -mtime +90 -exec gzip {} \;
mv *.gz /opt/apeg/archives/reports/

# Verify disk space
df -h /opt/apeg
```

### Monthly Tasks

#### Rotate API Keys (1st of each month)

**Time:** 1 hour

**Steps:**
1. Generate new API keys:
   - OpenAI: https://platform.openai.com/api-keys
   - Shopify: Regenerate access token
   - Etsy: Refresh OAuth token

2. Test new keys in staging:
   ```bash
   # Update staging .env
   export OPENAI_API_KEY=sk-proj-NEW_KEY
   python -m apeg_core validate
   ```

3. Deploy to production:
   ```bash
   # Update production .env
   sudo nano /opt/apeg/.env

   # Restart service
   sudo systemctl restart apeg.service

   # Verify
   curl https://apeg.yourdomain.com/health
   ```

4. Revoke old keys:
   - Wait 24 hours after deployment
   - Verify no errors in logs
   - Revoke old keys in provider dashboards

#### Review Bandit Weights (15th of each month)

**Time:** 15 minutes

**Steps:**
```bash
# Review macro performance
cat /opt/apeg/bandit_weights.json | jq

# Check for underperforming macros
python -m apeg_core analyze-macros --output macro_report.json
```

**Action:**
- If a macro has <60% success rate → Investigate or deprecate
- If new macro needed → Create GitHub issue

---

## Configuration Management

### Configuration Rollout Process

1. **Local Development**
   ```bash
   # Make changes to SessionConfig.json, WorkflowGraph.json, etc.

   # Validate
   python validate_repo.py

   # Test locally
   APEG_TEST_MODE=true pytest tests/
   ```

2. **Create Pull Request**
   ```bash
   git checkout -b config-update-description
   git add SessionConfig.json
   git commit -m "config: Update OpenAI timeout to 60s"
   git push origin config-update-description
   ```

3. **CI/CD Validation**
   - GitHub Actions runs tests
   - Coverage check passes
   - Configuration validation passes

4. **Peer Review**
   - At least one approval required
   - Reviewer checks:
     - Is change documented?
     - Are tests updated?
     - Is rollback plan clear?

5. **Merge to Main**
   ```bash
   # After approval, merge PR
   git checkout main
   git pull origin main
   ```

6. **Deploy to Production**
   ```bash
   # SSH to production server
   ssh apeg-prod

   # Pull latest
   cd /opt/apeg
   sudo -u apeg git pull origin main

   # Backup current config
   cp SessionConfig.json SessionConfig.json.backup-$(date +%Y%m%d)

   # Restart service
   sudo systemctl restart apeg.service

   # Monitor logs for 5 minutes
   sudo journalctl -u apeg.service -f
   ```

7. **Verification**
   ```bash
   # Check health
   curl https://apeg.yourdomain.com/health

   # Run validation
   python -m apeg_core validate

   # Monitor for 1 hour
   ```

8. **Rollback (if needed)**
   ```bash
   # Restore backup
   cp SessionConfig.json.backup-$(date +%Y%m%d) SessionConfig.json

   # Restart
   sudo systemctl restart apeg.service
   ```

---

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Service Health**
   - Uptime (target: 99.9%)
   - Response time (target: <500ms for /health)

2. **Workflow Execution**
   - Success rate (target: >85%)
   - Average execution time
   - Loop detection frequency

3. **External API Usage**
   - OpenAI API calls per day
   - Shopify/Etsy rate limit headroom
   - API error rates

4. **Resource Usage**
   - CPU usage (alert if >80% for >5 min)
   - Memory usage (alert if >90%)
   - Disk usage (alert if >85%)

### Alert Configuration

Using **Prometheus + Grafana** (optional):

```yaml
# /etc/prometheus/rules/apeg.yml
groups:
  - name: apeg
    interval: 30s
    rules:
      - alert: APEGServiceDown
        expr: up{job="apeg"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "APEG service is down"

      - alert: APEGHighErrorRate
        expr: rate(apeg_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"

      - alert: APEGDiskSpacelow
        expr: disk_free_percent{mountpoint="/opt/apeg"} < 15
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on APEG server"
```

---

## Troubleshooting

### Common Issues

#### Issue: OpenAI API Timeout

**Symptoms:**
- Logbook shows "OpenAI API timeout" errors
- Workflow fails at "build" node

**Diagnosis:**
```bash
# Check recent errors
python -m apeg_core review-logs --since 1h --filter "timeout"

# Test OpenAI API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Resolution:**
1. Temporary: Increase timeout in SessionConfig.json
2. Long-term: Implement retry logic (Phase 9)

---

#### Issue: Shopify Rate Limit Exceeded

**Symptoms:**
- HTTP 429 errors in logs
- Inventory sync fails

**Diagnosis:**
```bash
# Check Shopify API usage
curl https://your-store.myshopify.com/admin/api/2024-01/shop.json \
  -H "X-Shopify-Access-Token: $SHOPIFY_ACCESS_TOKEN" \
  -v 2>&1 | grep "X-Shopify-Shop-Api-Call-Limit"
```

**Resolution:**
1. Immediate: Wait for rate limit window to reset (2 requests/second)
2. Add exponential backoff to HTTP client
3. Batch operations to reduce request count

---

#### Issue: Memory Leak

**Symptoms:**
- Memory usage grows over time
- OOM killer terminates process

**Diagnosis:**
```bash
# Monitor memory over time
watch -n 5 'ps aux | grep apeg'

# Check for resource leaks
python -m apeg_core debug --memory-profile
```

**Resolution:**
1. Restart service to reclaim memory
2. Enable memory profiling
3. Review code for unclosed resources (file handles, connections)

---

## Emergency Contacts

| Role | Name | Contact | Escalation |
|------|------|---------|------------|
| On-Call Engineer | Rotation | Slack: #apeg-oncall | PagerDuty |
| APEG Lead | [Name] | [Email/Phone] | After 30 min |
| Infrastructure Team | [Name] | [Email/Phone] | For host issues |
| Security Team | [Name] | [Email/Phone] | For credential issues |

---

## Appendix

### Useful Commands Reference

```bash
# Service management
sudo systemctl start apeg.service
sudo systemctl stop apeg.service
sudo systemctl restart apeg.service
sudo systemctl status apeg.service

# Log viewing
sudo journalctl -u apeg.service -f
sudo journalctl -u apeg.service --since "1 hour ago"
sudo journalctl -u apeg.service --priority err

# Configuration validation
python -m apeg_core validate
python validate_repo.py

# Testing
APEG_TEST_MODE=true pytest tests/
pytest tests/ --cov=src/apeg_core

# Deployment
git pull origin main
sudo systemctl restart apeg.service
```

---

**Document Status:** PLANNING
**Last Updated:** 2025-11-20
**Next Review:** After Phase 9 implementation
