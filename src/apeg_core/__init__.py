"""
APEG - Autonomous Prompt Engineering Graph

A modular Python runtime for intelligent workflow orchestration using:
- Multi-armed bandit (MAB) selection with Thompson Sampling
- Loop detection and fallback routing
- OpenAI Agents/Graph integration
- Domain-specific agents (Shopify, Etsy)
- Scoring, logging, and adoption gates
"""

__version__ = "1.0.0"
__author__ = "PEG System"

from apeg_core.orchestrator import APEGOrchestrator

__all__ = ["APEGOrchestrator", "__version__"]
