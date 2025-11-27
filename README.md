# PEG - Promptable Engineer GPT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-132%20passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Advanced AI agent orchestration system for prompt engineering, validation, and quality control.**

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Matthewtgordon/PEG.git
cd PEG

# Install dependencies
pip install -e ".[dev]"

# Validate environment
python -m apeg_core validate

# Run tests
APEG_TEST_MODE=true pytest tests/ -v

# Start web server (test mode)
APEG_TEST_MODE=true python -m apeg_core.server
```

Access web UI at: http://localhost:8000
API documentation at: http://localhost:8000/docs

---

## 📋 What is PEG?

PEG (Promptable Engineer GPT) is an **APEG (Autonomous Prompt Engineering Graph)** runtime that orchestrates complex AI workflows through:

- **Graph-Based Workflow Execution** - Directed graph workflow engine with conditional routing
- **Multi-Agent Collaboration** - 7 specialized agent roles (ENGINEER, VALIDATOR, SCORER, CHALLENGER, LOGGER, TESTER, PEG)
- **Intelligent Decision Making** - Thompson Sampling bandit selector with loop detection
- **Quality Assurance** - Automated scoring and adoption gates
- **Domain Integrations** - Shopify and Etsy e-commerce agents
- **Memory Persistence** - JSON-backed state management
- **Production Ready** - Web API, CLI, systemd service support

---

## 🏗️ Architecture

### Core Components

```
src/apeg_core/
├── orchestrator.py         # Workflow graph execution engine
├── decision/               # Decision engine (bandit, loop guard, MCTS)
├── agents/                 # LLM roles & domain agents (Shopify, Etsy)
├── connectors/             # External APIs (OpenAI, HTTP tools)
├── scoring/                # Quality evaluation system
├── memory/                 # Persistent storage
├── logging/                # Structured logging
├── workflow/               # Graph validation utilities
└── web/                    # FastAPI server & UI
```

### Workflow Execution Model

```
intake → prep → build → review → [export | loop_detector | external_call]
                  ↑          ↓
                  └─ reroute ←─ loop_detector
                  ↑          ↓
                  └─ fallback ←─ loop_detector
```

Workflows are defined declaratively in `WorkflowGraph.json` with:
- **Nodes:** Workflow stages with agent assignments
- **Edges:** Transitions with conditional routing
- **Agent Roles:** Specialized AI roles for each stage

---

## 🎯 Features

### Intelligent Macro Selection
- **Thompson Sampling** - Multi-armed bandit algorithm for adaptive macro selection
- **Loop Detection** - Prevents infinite cycles with configurable thresholds
- **Exploration Bonus** - Balances exploitation vs exploration

### Multi-Agent System
- **ENGINEER:** Designs prompt chains and injects constraints
- **VALIDATOR:** Validates structure, schema conformance, output format
- **CHALLENGER:** Stress-tests logic, triggers fallback on flaws
- **LOGGER:** Audits file changes and mutations
- **SCORER:** Evaluates outputs using PromptScoreModel
- **TESTER:** Injects regression and edge tests

### Domain Agents
- **Shopify Agent:** Product management, inventory, orders, customer messaging
- **Etsy Agent:** Listing management, orders, shop analytics, SEO suggestions

### Quality Control
- **Weighted Scoring:** Multiple metrics with configurable thresholds
- **Adoption Gate:** Blocks low-quality outputs before export
- **Hybrid Scoring:** Rule-based + optional LLM-based evaluation

---

## 📦 Installation

### Requirements
- Python 3.11 or higher (3.11-3.12 supported)
- Ubuntu 22.04 LTS or macOS (Raspberry Pi supported)
- 4GB+ RAM (8GB recommended for production)

### Standard Installation

```bash
# Clone repository
git clone https://github.com/Matthewtgordon/PEG.git
cd PEG

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Configuration

Create `.env` file (copy from `.env.sample`):

```bash
# Core Settings
APEG_TEST_MODE=false
APEG_USE_LLM_SCORING=true

# OpenAI API (Required)
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
OPENAI_DEFAULT_MODEL=gpt-4

# Optional: E-commerce Integrations
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat-YOUR-TOKEN
ETSY_API_KEY=your-etsy-key
ETSY_SHOP_ID=12345678
```

Validate your setup:

```bash
python -m apeg_core validate
```

---

## 🛠️ Usage

### CLI Mode

```bash
# Run workflow with default config
python -m apeg_core

# Specify custom workflow
python -m apeg_core --workflow custom_workflow.json

# Enable debug mode
python -m apeg_core --debug

# Show version
python -m apeg_core --version
```

### Web Server Mode

```bash
# Start server (test mode for development)
APEG_TEST_MODE=true python -m apeg_core.server

# Production mode
APEG_TEST_MODE=false python -m apeg_core.server
```

**API Endpoints:**
- `GET /` - API information and service status
- `GET /health` - Health check endpoint
- `POST /run` - Execute workflow with goal
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /mcp/serverInfo` - MCP-compliant server information
- `GET /mcp/tools` - List available MCP tools
- `WS /ws` - WebSocket for real-time updates

### Python API

```python
from apeg_core import APEGOrchestrator

# Initialize orchestrator with configuration paths
orchestrator = APEGOrchestrator(
    config_path="SessionConfig.json",
    workflow_graph_path="WorkflowGraph.json"
)

# Set the goal in the orchestrator state
orchestrator.state.setdefault("context", {})
orchestrator.state["context"]["goal"] = "Generate product description for gemstone anklet"

# Execute workflow
orchestrator.execute_graph()

# Access results from orchestrator state
state = orchestrator.get_state()
history = orchestrator.get_history()

print(f"Output: {state.get('output')}")
print(f"Score: {state.get('last_score')}")
print(f"Nodes executed: {len(history)}")
```

---

## 🧪 Testing

```bash
# Run all tests (test mode)
APEG_TEST_MODE=true pytest tests/ -v

# Run with coverage
pytest --cov=src/apeg_core tests/

# Run specific test file
pytest tests/test_orchestrator.py -v

# Run integration tests
pytest tests/test_*_integration.py -v
```

**Test Coverage:** 132 tests passing (1 skipped)

---

## 📚 Documentation

### Essential Reading
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive project guide for AI assistants
- **[docs/APEG_STATUS.md](docs/APEG_STATUS.md)** - Current implementation status
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[docs/SECURITY_HARDENING.md](docs/SECURITY_HARDENING.md)** - Security checklist

### Phase Documentation
- **[docs/APEG_REQUIREMENTS_SUMMARY.md](docs/APEG_REQUIREMENTS_SUMMARY.md)** - Requirements specification
- **[docs/APEG_PHASE_8_REQUIREMENTS.md](docs/APEG_PHASE_8_REQUIREMENTS.md)** - Phase 8 (API integration) spec
- **[docs/APEG_PLACEHOLDERS.md](docs/APEG_PLACEHOLDERS.md)** - Placeholder tracking

### Configuration Files
- **WorkflowGraph.json** - Workflow definition (nodes, edges, agents)
- **SessionConfig.json** - Runtime configuration
- **Knowledge.json** - Knowledge base with versioning
- **PromptScoreModel.json** - Quality scoring metrics
- **TagEnum.json** - System-wide tag definitions

---

## 🏁 Project Status

**Current Phase:** Phase 8 - Production API Integration (In Progress)

**Completed:**
- ✅ Phase 0-7: Core APEG runtime (132 tests passing)
- ✅ Decision engine with Thompson Sampling
- ✅ Multi-agent orchestration system
- ✅ Web API and UI
- ✅ Memory and logging systems
- ✅ CI/CD pipeline

**In Progress:**
- 🔄 Phase 8: Production API integrations
  - ✅ OpenAI Agents SDK integration
  - ✅ Enhanced LLM scoring
  - 📋 Shopify API integration (awaiting credentials)
  - 📋 Etsy API integration (awaiting credentials)

**Test Mode:** Fully functional without API keys
**Production Mode:** Requires API credentials (see `.env.sample`)

---

## 🚢 Deployment

### Systemd Service (Recommended)

```bash
# Install as systemd service
sudo cp deploy/apeg.service /etc/systemd/system/
sudo systemctl enable apeg
sudo systemctl start apeg
```

### Nginx Reverse Proxy

```bash
# Configure Nginx with SSL
sudo cp deploy/nginx-apeg.conf /etc/nginx/sites-available/apeg
sudo ln -s /etc/nginx/sites-available/apeg /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

### Raspberry Pi

Special optimizations available for Raspberry Pi 4/5. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#raspberry-pi-deployment) for:
- Swap configuration
- Memory optimization
- CPU governor settings
- Performance tuning

---

## 🔐 Security

**Best Practices:**
- Never commit `.env` to version control
- Rotate API keys every 90 days
- Use environment-specific credentials
- Enable rate limiting in production
- Deploy behind HTTPS reverse proxy
- Review [docs/SECURITY_HARDENING.md](docs/SECURITY_HARDENING.md)

**Firewall Setup:**
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 8000/tcp  # Block direct APEG access
sudo ufw enable
```

---

## 🤝 Contributing

### Development Workflow

1. **Create feature branch** from `main`
2. **Make changes** following conventions in CLAUDE.md
3. **Write tests** (maintain 80%+ coverage)
4. **Run validation:** `python validate_repo.py`
5. **Run tests:** `pytest tests/ -v`
6. **Commit** using conventional commit format
7. **Push** and create pull request

### Commit Message Format

```
feat: add new loop detection algorithm
fix: correct version bumping in knowledge update
docs: update deployment guide
test: add tests for memory manager
chore: update dependencies
```

### Code Style
- Python: PEP 8 with type hints
- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

---

## 📊 Performance

**Benchmarks** (Raspberry Pi 4, 8GB RAM):
- Web server startup: <1 second
- API response time: ~100ms (test mode)
- Memory footprint: ~50MB
- Decision engine: <50ms per selection

**Optimization:**
- Lazy dependency loading
- Efficient JSON I/O
- No heavy frameworks
- Raspberry Pi optimizations available

---

## 🐛 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
# Reinstall in development mode
pip install -e .
```

**Tests failing:**
```bash
# Ensure test mode enabled
export APEG_TEST_MODE=true
pytest tests/ -v
```

**API calls failing:**
```bash
# Validate environment
python -m apeg_core validate

# Check API key
echo $OPENAI_API_KEY | head -c 20
```

**Service won't start:**
```bash
# Check logs
sudo journalctl -u apeg -n 50

# Verify permissions
sudo chown -R apeg:apeg /opt/apeg
```

See [docs/DEPLOYMENT.md#troubleshooting](docs/DEPLOYMENT.md#troubleshooting) for more solutions.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** - GPT models and API
- **FastAPI** - Web framework
- **Pytest** - Testing framework
- **Thompson Sampling** - Multi-armed bandit algorithm

---

## 📞 Support

- **Issues:** https://github.com/Matthewtgordon/PEG/issues
- **Documentation:** [docs/](docs/)
- **Status Updates:** [docs/APEG_STATUS.md](docs/APEG_STATUS.md)

---

**Built with ❤️ for autonomous AI orchestration**

**Version:** 1.0.0 (Phase 8 in progress)
**Last Updated:** 2025-11-20
