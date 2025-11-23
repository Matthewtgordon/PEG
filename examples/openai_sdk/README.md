# OpenAI Agents SDK Integration Examples

Demonstrations of APEG integration with OpenAI Agents SDK.

## Examples

1. **basic_adapter.py** - Wrap APEG agent as SDK agent
2. **multi_agent_handoff.py** - Handoffs between Shopify and Etsy agents
3. **mixed_workflow.py** - Combine APEG orchestrator with SDK agents

## Requirements

```bash
# Install SDK (if not already installed)
pip install openai-agents --break-system-packages

# Set environment variable (optional for real LLM calls)
export OPENAI_API_KEY="your-key-here"
```

## Running Examples

All examples run in test mode by default (no real API calls):

```bash
cd /path/to/PEG
python3 examples/openai_sdk/basic_adapter.py
python3 examples/openai_sdk/multi_agent_handoff.py
python3 examples/openai_sdk/mixed_workflow.py
```

## Test Mode

By default, examples use test mode:
- No real API calls to OpenAI or Shopify/Etsy
- Deterministic stub responses for testing
- Set `test_mode=False` and provide credentials for real operation
