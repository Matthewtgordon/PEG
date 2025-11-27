# PEG Documentation Index

**Last Updated:** 2025-11-27

This directory contains all technical documentation for the PEG (Promptable Engineer GPT) project.

---

## 📖 Getting Started

### Essential Reading (Start Here)

1. **[../README.md](../README.md)** - Project overview, quick start, installation
2. **[../CLAUDE.md](../CLAUDE.md)** - Comprehensive project guide for AI assistants
3. **[APEG_STATUS.md](APEG_STATUS.md)** - Current implementation status (Phases 0-8)

---

## 📚 Core Documentation

### Status & Planning

- **[APEG_STATUS.md](APEG_STATUS.md)** - Runtime status report
  - Phase 0-8 completion status
  - Test results (132 passing)
  - Current capabilities
  - Known limitations

- **[APEG_PLACEHOLDERS.md](APEG_PLACEHOLDERS.md)** - Placeholder tracking
  - Active placeholders (test mode stubs)
  - Resolved placeholders
  - Resolution plans

### Requirements & Specifications

- **[APEG_REQUIREMENTS_SUMMARY.md](APEG_REQUIREMENTS_SUMMARY.md)** (612 lines)
  - Complete requirements specification
  - 10 core components detailed
  - Acceptance criteria
  - Runtime environment requirements

- **[APEG_PHASE_9_REQUIREMENTS.md](APEG_PHASE_9_REQUIREMENTS.md)** ⚠️ PLANNING ONLY
  - Self-improvement & operations layer (future work)
  - Feedback ingestion and analysis
  - Prompt tuning suggestions
  - E-commerce maintenance workflows
  - **Status**: Planning document, not yet implemented

- **[OPENAI_AGENTS_INTEGRATION.md](OPENAI_AGENTS_INTEGRATION.md)** (NEW - 2025-11-23)
  - OpenAI Agents SDK integration guide
  - Architecture overview and diagrams
  - Multi-agent workflow patterns
  - Session management
  - Guardrails and safety
  - Migration guide

- **[APEG_HYBRID_ORCHESTRATOR_BUILD.md](APEG_HYBRID_ORCHESTRATOR_BUILD.md)**
  - Hybrid orchestrator build specification
  - 7 milestones with acceptance tests
  - Web UI and API documentation

### Deployment & Operations

- **[DEPLOYMENT.md](DEPLOYMENT.md)** (785 lines)
  - Production deployment guide
  - Raspberry Pi optimizations
  - Systemd service setup
  - Nginx reverse proxy configuration
  - SSL/TLS setup with Let's Encrypt
  - Monitoring and logging
  - Backup and recovery
  - Troubleshooting guide

- **[SECURITY_HARDENING.md](SECURITY_HARDENING.md)**
  - Security best practices
  - Firewall configuration
  - API key management
  - Rate limiting
  - Compliance guidelines

- **[APEG_RUNTIME_STATUS.md](APEG_RUNTIME_STATUS.md)** (334 lines)
  - Runtime capabilities
  - Component status
  - Usage examples
  - Production checklist

---

## 📁 Subdirectories

### archive/ - Historical Documents

**Purpose:** Outdated or superseded documentation preserved for reference

- **[archive/APEG_TODO_2025-11-18.md](archive/APEG_TODO_2025-11-18.md)** (OUTDATED)
  - Original TODO list from Nov 18
  - Superseded by APEG_STATUS.md
  - All phases shown as pending (now complete)

- **[archive/dev-log-phases-0-3.md](archive/dev-log-phases-0-3.md)**
  - Development log for Phases 0-3
  - Historical record of initial implementation
  - Session date: 2025-11-18

- **[archive/PHASES_0-3_VERIFICATION.md](archive/PHASES_0-3_VERIFICATION.md)**
  - Early phase verification document
  - Historical milestone record

- **[archive/APEG_PHASE_8_REQUIREMENTS.md](archive/APEG_PHASE_8_REQUIREMENTS.md)** (ARCHIVED 2025-11-27)
  - Phase 8 planning document (600+ lines)
  - OpenAI, Shopify, Etsy API integration specs
  - Implementation largely complete, see APEG_STATUS.md for current state

- **[archive/PHASE_9_VERIFICATION_REPORT.md](archive/PHASE_9_VERIFICATION_REPORT.md)** (ARCHIVED 2025-11-27)
  - Verification of Phase 9 planning documentation
  - Not an implementation verification
  - Confirms planning docs meet requirements

### ADRS/ - Architecture Decision Records

**Purpose:** Document significant architectural decisions

- **[ADRS/ADR-001-OpenAI-Agents.md](ADRS/ADR-001-OpenAI-Agents.md)** (IMPLEMENTED)
  - Use OpenAI Agents SDK as Primary LLM Runtime
  - Dual-backend with SDK primary, API fallback
  - Test mode for CI/CD
  - Implementation completed 2025-11-23

- **[ADRS/ADR-002-MCTS-Disabled-By-Default.md](ADRS/ADR-002-MCTS-Disabled-By-Default.md)**
  - MCTS Planner disabled by default
  - Bandit + scoring as primary decision engine
  - Feature flag for optional enablement

### milestones/ - Implementation Milestones

**Purpose:** Detailed implementation summaries for completed phases

- **[milestones/BUILD_COMPLETION_SUMMARY.md](milestones/BUILD_COMPLETION_SUMMARY.md)**
  - Hybrid orchestrator build completion (2025-11-19)
  - All 7 milestones delivered
  - 7/7 acceptance tests passed
  - File breakdown and statistics

- **[milestones/IMPLEMENTATION_SUMMARY.md](milestones/IMPLEMENTATION_SUMMARY.md)**
  - Phases 4-5 implementation (2025-11-20)
  - OpenAI client wrapper
  - Workflow executor utilities
  - Agent framework and registry
  - 27 new tests added

- **[milestones/APEG_AUDIT_2025-11-18.md](milestones/APEG_AUDIT_2025-11-18.md)** (39KB)
  - Comprehensive audit report
  - Phases 0-3 complete, 4-7 pending (at time of audit)
  - pytest-cov configuration issue identified
  - 44 tests passing at audit time
  - 14 prioritized repair tasks defined

---

## 🗂️ Documentation by Purpose

### For New Contributors

1. Start: [../README.md](../README.md)
2. Understand project: [../CLAUDE.md](../CLAUDE.md)
3. Check status: [APEG_STATUS.md](APEG_STATUS.md)
4. Set up environment: [DEPLOYMENT.md](DEPLOYMENT.md)

### For Developers

1. Requirements: [APEG_REQUIREMENTS_SUMMARY.md](APEG_REQUIREMENTS_SUMMARY.md)
2. Current status: [APEG_STATUS.md](APEG_STATUS.md)
3. Placeholders: [APEG_PLACEHOLDERS.md](APEG_PLACEHOLDERS.md)
4. Phase 8 tasks: [APEG_PHASE_8_REQUIREMENTS.md](APEG_PHASE_8_REQUIREMENTS.md)
5. Project guide: [../CLAUDE.md](../CLAUDE.md)

### For DevOps/SRE

1. Deployment: [DEPLOYMENT.md](DEPLOYMENT.md)
2. Security: [SECURITY_HARDENING.md](SECURITY_HARDENING.md)
3. Runtime status: [APEG_RUNTIME_STATUS.md](APEG_RUNTIME_STATUS.md)
4. Monitoring: [DEPLOYMENT.md#monitoring-and-logs](DEPLOYMENT.md#monitoring-and-logs)

### For Understanding History

1. Milestones: [milestones/](milestones/)
2. Audit report: [milestones/APEG_AUDIT_2025-11-18.md](milestones/APEG_AUDIT_2025-11-18.md)
3. Dev logs: [archive/dev-log-phases-0-3.md](archive/dev-log-phases-0-3.md)
4. Original TODO: [archive/APEG_TODO_2025-11-18.md](archive/APEG_TODO_2025-11-18.md)

---

## 📋 Configuration Files Reference

All configuration files are in the root directory:

- **WorkflowGraph.json** - Workflow definition (nodes, edges, agents)
- **SessionConfig.json** - Runtime configuration
- **Knowledge.json** - Versioned knowledge base
- **Rules.json** - Enforcement rules
- **PromptScoreModel.json** - Quality scoring metrics
- **TagEnum.json** - System-wide tags
- **Tasks.json** - Task tracking
- **Tests.json** - Test definitions
- **Logbook.json** - Audit trail
- **Journal.json** - Additional logging

See [../CLAUDE.md](../CLAUDE.md) for detailed descriptions of each config file.

---

## 🔍 Finding Information

### By Topic

- **Installation:** [../README.md](../README.md), [DEPLOYMENT.md](DEPLOYMENT.md)
- **Configuration:** [../CLAUDE.md](../CLAUDE.md#configuration-files)
- **Testing:** [../README.md](../README.md#testing), [APEG_STATUS.md](APEG_STATUS.md)
- **API Integration:** [APEG_PHASE_8_REQUIREMENTS.md](APEG_PHASE_8_REQUIREMENTS.md)
- **Architecture:** [../README.md](../README.md#architecture), [APEG_REQUIREMENTS_SUMMARY.md](APEG_REQUIREMENTS_SUMMARY.md)
- **Security:** [SECURITY_HARDENING.md](SECURITY_HARDENING.md)
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Troubleshooting:** [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md#troubleshooting)

### By Status

- **Current Work:** [APEG_STATUS.md](APEG_STATUS.md)
- **Completed Phases:** [milestones/](milestones/)
- **Future Work:** [APEG_PHASE_8_REQUIREMENTS.md](APEG_PHASE_8_REQUIREMENTS.md)
- **Historical:** [archive/](archive/)

---

## 📝 Document Status Legend

- **✅ CURRENT** - Up-to-date, actively maintained
- **🔄 IN PROGRESS** - Being updated, work in progress
- **📋 PLANNED** - Future documentation planned
- **📦 ARCHIVED** - Historical, superseded, or outdated
- **🔒 FINAL** - Milestone document, final state

### Document Status Summary

| Document | Status | Last Updated |
|----------|--------|--------------|
| APEG_STATUS.md | ✅ CURRENT | 2025-11-20 |
| APEG_PHASE_8_REQUIREMENTS.md | ✅ CURRENT | 2025-11-20 |
| APEG_PHASE_9_REQUIREMENTS.md | ✅ CURRENT | 2025-11-20 |
| OPENAI_AGENTS_INTEGRATION.md | ✅ CURRENT | 2025-11-23 |
| DEPLOYMENT.md | ✅ CURRENT | 2025-11-20 |
| SECURITY_HARDENING.md | ✅ CURRENT | 2025-11-20 |
| APEG_REQUIREMENTS_SUMMARY.md | ✅ CURRENT | 2025-11-18 |
| APEG_PLACEHOLDERS.md | ✅ CURRENT | 2025-11-20 |
| APEG_RUNTIME_STATUS.md | ✅ CURRENT | 2025-11-20 |
| APEG_HYBRID_ORCHESTRATOR_BUILD.md | 🔒 FINAL | 2025-11-19 |
| ADRS/ADR-001-OpenAI-Agents.md | ✅ IMPLEMENTED | 2025-11-23 |
| ADRS/ADR-002-MCTS-Disabled-By-Default.md | ✅ CURRENT | 2025-11-20 |
| milestones/* | 🔒 FINAL | Various |
| archive/* | 📦 ARCHIVED | Various |

---

## 🤝 Contributing to Documentation

### When to Update

- After completing any phase or milestone
- When adding new features or components
- When fixing bugs that affect documented behavior
- When deployment procedures change
- When configuration options change

### Documentation Standards

1. **Always update "Last Updated" date**
2. **Bump document version for major changes**
3. **Use clear, concise language**
4. **Include code examples where appropriate**
5. **Link to related documents**
6. **Update this index when adding new docs**

### File Naming Conventions

- **Status/Reports:** `APEG_STATUS.md`, `APEG_RUNTIME_STATUS.md`
- **Specifications:** `APEG_*_REQUIREMENTS.md`
- **Guides:** `DEPLOYMENT.md`, `SECURITY_HARDENING.md`
- **Historical:** `*_YYYY-MM-DD.md` (in archive/)
- **Milestones:** Descriptive names (in milestones/)

---

## 📞 Support

- **Issues:** https://github.com/Matthewtgordon/PEG/issues
- **Project Board:** https://github.com/Matthewtgordon/PEG/projects
- **Main Docs:** [../README.md](../README.md), [../CLAUDE.md](../CLAUDE.md)

---

**Documentation Index Version:** 1.1.0
**Last Updated:** 2025-11-23
**Maintainer:** PEG Development Team
