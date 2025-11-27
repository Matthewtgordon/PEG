# ADR-001: Use OpenAI Agents SDK as Primary LLM Runtime

## Status
Accepted

## Date
2025-11-22

## Context
APEG requires LLM capabilities for various agent roles (ENGINEER, VALIDATOR, SCORER, etc.)
to enable intelligent workflow orchestration, output evaluation, and prompt engineering.

We need to decide on the LLM integration strategy that:
- Supports multiple agent roles with different behaviors
- Allows for future expansion to other LLM providers
- Maintains testability with deterministic responses
- Provides graceful fallback when APIs are unavailable

## Decision
We will implement a dual-backend LLM integration:

1. **Primary**: OpenAI Agents SDK (when available and configured)
   - Provides structured agent execution
   - Supports persistent agents with state
   - Enables tool use and function calling

2. **Fallback**: OpenAI API via OpenAIClient
   - Uses direct chat completions API
   - Simpler integration, always available
   - Used when Agents SDK is not configured

3. **Test Mode**: Deterministic stub responses
   - Enabled via APEG_TEST_MODE=true
   - Returns predictable JSON responses for CI/testing
   - No external API calls

## Implementation
The integration is implemented via:
- `src/apeg_core/llm/` package
- `AgentsBridge` class as the unified interface
- `LLMRole` enum for role definitions
- `RoleConfig` dataclass for role-specific settings

### Configuration
```json
{
  "use_openai_agents": true,
  "agents_project_id": "proj_xxx",
  "test_mode": false
}
```

### Environment Variables
- `APEG_TEST_MODE`: Enable test mode
- `APEG_USE_AGENTS_SDK`: Enable Agents SDK
- `OPENAI_API_KEY`: API authentication

## Consequences

### Positive
- Clean abstraction decouples orchestrator from LLM specifics
- Multiple backends provide flexibility and resilience
- Test mode enables reliable CI without API costs
- Role-based system aligns with APEG's multi-agent architecture

### Negative
- Two code paths to maintain (SDK and API fallback)
- Additional complexity in configuration

### Neutral
- OpenAI dependency (industry standard)
- Future work needed for multi-provider support

## Implementation Status

**Status:** IMPLEMENTED (2025-11-23)

The OpenAI Agents SDK integration has been fully implemented:

1. **OpenAIAgentsAdapter** (`src/apeg_core/llm/openai_agents_adapter.py`)
   - Full adapter layer for OpenAI Agents SDK
   - Support for all 8 APEG LLM roles
   - Session management with SQLite
   - Test mode for CI/CD
   - Hybrid mode with API fallback

2. **AgentsBridge** (`src/apeg_core/llm/agent_bridge.py`)
   - Updated to use Assistants API as fallback
   - Full test mode support
   - Role-based execution

3. **Documentation** (`docs/OPENAI_AGENTS_INTEGRATION.md`)
   - Comprehensive integration guide
   - Architecture diagrams
   - Usage examples
   - Migration guide

4. **Tests** (`tests/test_openai_agents_adapter.py`)
   - Full test coverage for adapter
   - Test mode validation
   - SDK integration tests

## References
- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents SDK GitHub](https://github.com/openai/openai-agents-python)
- APEG Phase 8 requirements
- `src/apeg_core/llm/agent_bridge.py`
- `src/apeg_core/llm/openai_agents_adapter.py`
- `docs/OPENAI_AGENTS_INTEGRATION.md`
