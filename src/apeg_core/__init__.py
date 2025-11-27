"""
APEG - Autonomous Prompt Engineering Graph

A modular Python runtime for intelligent workflow orchestration using:
- Multi-armed bandit (MAB) selection with Thompson Sampling
- Loop detection and fallback routing
- OpenAI Agents/Graph integration
- Domain-specific agents (Shopify, Etsy)
- Scoring, logging, and adoption gates
- Dynamic subagent generation (MetaAgent)
- Plugin-based extensibility
- Persistent arsenal for generated agents
"""

__version__ = "1.1.0"
__author__ = "PEG System"

from apeg_core.orchestrator import APEGOrchestrator
from apeg_core.arsenal import ArsenalManager, get_arsenal

__all__ = [
    "APEGOrchestrator",
    "ArsenalManager",
    "get_arsenal",
    "__version__"
]
