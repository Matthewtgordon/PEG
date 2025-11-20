# APEG Phase 9: Self-Improvement & Operations Layer - Requirements

**Document Version:** 1.0.0
**Created:** 2025-11-20
**Status:** PLANNING
**Prerequisites:** Phases 0-8 Complete

---

## Executive Summary

Phase 9 introduces **self-improvement and operational automation** capabilities to APEG. This phase enables the system to learn from its execution history, suggest improvements to prompts and configurations, and support batch operational tasks for e-commerce integrations.

### Key Principles

1. **Safety First**: All self-improvement proposals are documentation-only. No automatic code deployment.
2. **Human-in-the-Loop**: All suggested changes require human review and CI/CD approval.
3. **Data-Driven**: Improvements are based on measurable patterns in Logbook and MemoryStore data.
4. **Operational Excellence**: Automate repetitive e-commerce tasks while maintaining quality and safety.

---

## Phase 9 Objectives

### Primary Goals

1. **Learn from History**
   - Analyze Logbook.json and MemoryStore data to identify patterns
   - Detect failure modes, inefficient workflows, and improvement opportunities
   - Track performance trends over time

2. **Suggest Improvements**
   - Generate proposals for prompt refinements
   - Recommend workflow optimizations
   - Suggest scoring threshold adjustments based on empirical data

3. **Batch Operations**
   - Automate routine e-commerce tasks (inventory sync, SEO refresh, etc.)
   - Support nightly jobs and scheduled maintenance
   - Enable bulk operations with safety checks

4. **Operations Support**
   - Provide tools for monitoring, debugging, and incident response
   - Create runbooks for common operational scenarios
   - Enable self-healing for known failure patterns

---

## Constraints and Safety Requirements

### Hard Constraints

1. **No Automatic Code Deployment**
   - Self-improvement generates **change specifications only**
   - All code changes must go through:
     - Version control (Git)
     - CI/CD pipeline validation
     - Human code review
     - Test suite execution

2. **Read-Only Access to Production**
   - Self-improvement processes can READ from:
     - Logbook.json
     - MemoryStore files
     - Workflow execution history
   - CANNOT modify production configs without explicit approval

3. **Gated Batch Operations**
   - All batch operations require:
     - Dry-run mode first
     - Explicit confirmation
     - Rollback capability
     - Audit logging

### Soft Constraints

1. **Preserve Backward Compatibility**
   - Configuration changes must not break existing workflows
   - Migration paths must be provided

2. **Respect API Rate Limits**
   - Batch operations must throttle requests
   - Honor Shopify/Etsy/OpenAI rate limits

3. **Maintain Data Privacy**
   - Do not log sensitive customer data
   - Respect GDPR and data protection requirements

---

## Planned Capabilities

### 9.1 Feedback Ingestion Job

**Purpose:** Aggregate and analyze execution logs to identify patterns and issues.

**Inputs:**
- `Logbook.json` - Workflow events and errors
- `MemoryStore` - Historical run data
- `bandit_weights.json` - Macro selection performance

**Outputs:**
- `feedback_report.json` - Aggregated insights
- `failure_patterns.json` - Categorized failure modes
- `performance_trends.json` - Time-series metrics

**Example Output:**

```json
{
  "timestamp": "2025-11-20T10:00:00Z",
  "analysis_period": {
    "start": "2025-11-13T00:00:00Z",
    "end": "2025-11-20T00:00:00Z"
  },
  "summary": {
    "total_runs": 450,
    "successful_runs": 387,
    "failed_runs": 63,
    "success_rate": 0.86
  },
  "failure_patterns": [
    {
      "pattern": "OpenAI API timeout",
      "count": 28,
      "frequency": 0.44,
      "suggested_fix": "Increase timeout from 30s to 60s in SessionConfig.json"
    },
    {
      "pattern": "Shopify rate limit exceeded",
      "count": 15,
      "frequency": 0.24,
      "suggested_fix": "Add exponential backoff with jitter"
    }
  ],
  "macro_performance": {
    "macro_chain_of_thought": {
      "usage_count": 200,
      "success_rate": 0.92,
      "avg_score": 0.88
    },
    "macro_role_prompt": {
      "usage_count": 150,
      "success_rate": 0.85,
      "avg_score": 0.82
    }
  },
  "recommendations": [
    "Increase usage of 'macro_chain_of_thought' (highest performance)",
    "Investigate 'macro_rewrite' underperformance (0.75 success rate)",
    "Add retry logic for OpenAI API calls"
  ]
}
```

**CLI Command:**
```bash
python -m apeg_core analyze-feedback --period 7d --output feedback_report.json
```

---

### 9.2 Prompt Tuning Suggestion Generator

**Purpose:** Generate proposals to improve prompts, workflows, and scoring models based on empirical data.

**Inputs:**
- `feedback_report.json` - Analysis from 9.1
- `PromptScoreModel.json` - Current scoring configuration
- `WorkflowGraph.json` - Current workflow definition
- `SessionConfig.json` - Current session configuration

**Outputs:**
- `improvement_proposals.md` - Human-readable change proposals
- `config_diffs/` - Git-style diffs for proposed changes

**Example Proposal:**

```markdown
# APEG Improvement Proposal #042
**Generated:** 2025-11-20
**Based on:** 7 days of execution data (450 runs)

## Proposal: Increase OpenAI API Timeout

**Issue:**
- 28 runs (6.2%) failed due to OpenAI API timeouts
- Timeouts cluster around long-form content generation tasks

**Current Configuration:**
```json
{
  "openai": {
    "timeout": 30
  }
}
```

**Proposed Change:**
```json
{
  "openai": {
    "timeout": 60,
    "timeout_retry": {
      "enabled": true,
      "max_retries": 2,
      "backoff_factor": 2.0
    }
  }
}
```

**Expected Impact:**
- Reduce timeout failures by ~80% (based on retry simulations)
- Minimal performance impact (only affects long-running requests)

**Risk Assessment:** LOW
- No breaking changes
- Backward compatible
- Can be reverted easily

**Next Steps:**
1. Review this proposal
2. Apply changes to `SessionConfig.json`
3. Run `python validate_repo.py`
4. Commit and push to feature branch
5. Monitor for 48 hours
6. Merge to main if successful

---

## Proposal: Adjust Scoring Threshold for Product Descriptions

**Issue:**
- Product description tasks have 15% false-negative rate (good outputs scored below threshold)
- Current threshold: 0.80
- Analysis shows median score for good descriptions: 0.77

**Proposed Change to PromptScoreModel.json:**
```json
{
  "thresholds": {
    "default": 0.80,
    "product_description": 0.75
  }
}
```

**Expected Impact:**
- Reduce false negatives by ~12%
- Allow slightly lower scores for domain-specific tasks

**Risk Assessment:** MEDIUM
- Requires workflow logic to select threshold by task type
- Potential for more false positives

**Recommendation:** Implement context-aware thresholds in Phase 9.
```

**CLI Command:**
```bash
python -m apeg_core suggest-improvements --from-report feedback_report.json --output improvement_proposals.md
```

---

### 9.3 Maintenance Workflows for E-commerce

**Purpose:** Automate routine Shopify/Etsy operational tasks with safety checks.

#### 9.3.1 Inventory Synchronization

**Task:** Keep Shopify and Etsy inventory in sync nightly.

**Workflow:**
1. Fetch inventory from both platforms
2. Detect discrepancies
3. Generate sync plan
4. Execute sync with confirmation
5. Log results to Logbook

**CLI Command:**
```bash
# Dry run (no changes)
python -m apeg_core sync-inventory --dry-run --report sync_plan.json

# Review sync_plan.json, then execute
python -m apeg_core sync-inventory --execute --plan sync_plan.json
```

**Safety Features:**
- Dry-run mode required first
- Confirms before making changes
- Caps bulk updates (max 100 items per run)
- Rollback support via API

#### 9.3.2 SEO Refresh for Etsy Listings

**Task:** Use ENGINEER LLM role to suggest SEO improvements for stale listings.

**Workflow:**
1. Identify listings with low views (< 10 views in 30 days)
2. Call `suggest_listing_seo()` for each
3. Generate improvement proposals
4. Human reviews and approves
5. Apply approved changes via Etsy API

**CLI Command:**
```bash
# Analyze listings
python -m apeg_core etsy-seo-analyze --threshold 10 --days 30 --output seo_suggestions.json

# Apply approved suggestions
python -m apeg_core etsy-seo-apply --input seo_approved.json
```

#### 9.3.3 Order Status Monitoring

**Task:** Alert on stuck orders (unfulfilled > 48 hours).

**Workflow:**
1. Query orders from Shopify and Etsy
2. Identify orders not fulfilled within SLA
3. Generate alert report
4. Send notifications (email, Slack, etc.)

**CLI Command:**
```bash
python -m apeg_core monitor-orders --sla 48h --alert-email ops@example.com
```

---

## Logbook & Memory Schemas

### Logbook Entry Schema

Standardized schema for all events logged to `Logbook.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp with timezone"
    },
    "event_type": {
      "type": "string",
      "enum": [
        "workflow_start",
        "workflow_end",
        "node_execution",
        "scoring",
        "error",
        "warning",
        "info"
      ]
    },
    "workflow_id": {
      "type": "string",
      "description": "Unique identifier for workflow execution run"
    },
    "node_id": {
      "type": "string",
      "description": "Node ID from WorkflowGraph (if applicable)"
    },
    "agent": {
      "type": "string",
      "description": "Agent role (PEG, ENGINEER, etc.)"
    },
    "action": {
      "type": "string",
      "description": "Action performed"
    },
    "score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Quality score (if applicable)"
    },
    "success": {
      "type": "boolean",
      "description": "Whether the action succeeded"
    },
    "error_message": {
      "type": "string",
      "description": "Error details (if applicable)"
    },
    "metadata": {
      "type": "object",
      "description": "Additional context-specific data"
    }
  },
  "required": ["timestamp", "event_type", "workflow_id"]
}
```

**Example Logbook Entry:**

```json
{
  "timestamp": "2025-11-20T14:35:22.123Z",
  "event_type": "node_execution",
  "workflow_id": "wf-20251120-143520-abc123",
  "node_id": "build",
  "agent": "ENGINEER",
  "action": "build_prompt_logic",
  "success": true,
  "metadata": {
    "chosen_macro": "macro_chain_of_thought",
    "execution_time_ms": 1250
  }
}
```

### Memory Record Schema

Standardized schema for entries in `MemoryStore` files:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "key": {
      "type": "string",
      "description": "Unique identifier for this memory record"
    },
    "value": {
      "type": "any",
      "description": "Stored value (can be any JSON type)"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Searchable tags for categorization"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "When this record was created"
    },
    "last_used_at": {
      "type": "string",
      "format": "date-time",
      "description": "When this record was last accessed"
    },
    "access_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of times accessed"
    },
    "ttl": {
      "type": "integer",
      "description": "Time-to-live in seconds (optional)"
    }
  },
  "required": ["key", "value", "created_at"]
}
```

**Example Memory Record:**

```json
{
  "key": "bandit_weights_macro_chain_of_thought",
  "value": {
    "successes": 184,
    "failures": 16,
    "last_reward": 0.92
  },
  "tags": ["bandit", "macro", "decision_engine"],
  "created_at": "2025-11-13T08:00:00Z",
  "last_used_at": "2025-11-20T14:35:20Z",
  "access_count": 450
}
```

---

## Implementation Plan

### Phase 9.1: Feedback Analysis (4 weeks)

**Week 1-2:**
- Implement feedback ingestion job
- Create `feedback_report.json` schema
- Add CLI command: `analyze-feedback`

**Week 3:**
- Add failure pattern detection
- Implement time-series metrics

**Week 4:**
- Testing and refinement
- Documentation

### Phase 9.2: Improvement Suggestions (4 weeks)

**Week 1-2:**
- Implement proposal generator
- Create proposal template format

**Week 3:**
- Add config diff generation
- Implement risk assessment logic

**Week 4:**
- Human-in-the-loop approval workflow
- Testing and documentation

### Phase 9.3: E-commerce Maintenance (6 weeks)

**Week 1-2:**
- Implement inventory sync workflow
- Add dry-run and confirmation flows

**Week 3-4:**
- Implement SEO refresh workflow
- Integrate ENGINEER LLM role

**Week 5:**
- Implement order monitoring
- Add alerting system

**Week 6:**
- End-to-end testing
- Production deployment guide

---

## Success Criteria

### Functional Requirements

- [ ] Feedback ingestion job runs successfully on 7-day windows
- [ ] Improvement proposals generate valid config diffs
- [ ] E-commerce batch operations support dry-run mode
- [ ] All operations log to Logbook with structured schema
- [ ] Memory records conform to defined schema

### Quality Requirements

- [ ] No automatic code deployment (verified by audit)
- [ ] All batch operations require explicit confirmation
- [ ] 100% of proposals include risk assessment
- [ ] Rollback capability exists for all batch operations
- [ ] CI/CD gates prevent unreviewed changes

### Documentation Requirements

- [ ] Operations runbook created (Phase 9.2)
- [ ] CLI command reference complete
- [ ] Schema documentation published
- [ ] Troubleshooting guide available

---

## Dependencies

### Required Phases

- **Phase 8:** OpenAI LLM roles, Shopify/Etsy agents
- **Phase 6:** Logbook adapter, MemoryStore

### External Dependencies

- Stable Shopify/Etsy API credentials
- OpenAI API access for ENGINEER role
- Sufficient API rate limits for batch operations

---

## Risk Assessment

### High Risk

1. **Data Privacy**
   - Mitigation: Implement PII filtering, respect GDPR
2. **Accidental Bulk Changes**
   - Mitigation: Mandatory dry-run, caps on bulk operations

### Medium Risk

1. **API Rate Limits**
   - Mitigation: Throttling, exponential backoff
2. **False Positive Improvements**
   - Mitigation: Human review required, A/B testing

### Low Risk

1. **Performance Impact**
   - Mitigation: Run batch jobs off-peak, optimize queries

---

## Future Enhancements (Phase 10+)

- **Reinforcement Learning**: Use bandit feedback to train better macro selectors
- **Automated A/B Testing**: Deploy config changes to subset of traffic
- **Predictive Analytics**: Forecast inventory needs, demand trends
- **Self-Healing**: Automatically apply known fixes for common failures
- **Dashboard**: Web UI for monitoring, approving proposals, reviewing logs

---

## References

- **APEG Status:** `docs/APEG_STATUS.md`
- **Operations Runbook:** `docs/APEG_OPERATIONS_RUNBOOK.md` (Phase 9.2)
- **Logbook Adapter:** `src/apeg_core/logging/logbook_adapter.py`
- **Memory Store:** `src/apeg_core/memory/memory_store.py`
- **Shopify Agent:** `src/apeg_core/agents/shopify_agent.py`
- **Etsy Agent:** `src/apeg_core/agents/etsy_agent.py`

---

**Document Status:** APPROVED FOR PLANNING
**Last Updated:** 2025-11-20
**Next Review:** After Phase 8 stabilization
