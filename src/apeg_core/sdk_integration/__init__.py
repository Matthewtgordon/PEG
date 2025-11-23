"""
OpenAI Agents SDK integration for APEG.

This module provides adapters and wrappers to integrate the OpenAI
Agents SDK with APEG's existing orchestration system. It enables:

- Wrapping APEG agents as SDK agents
- Using SDK agents within APEG orchestrator
- Handoffs between APEG and SDK agents
- Tool bridging and schema conversion
- Session management integration

Architecture:
    APEG Orchestrator
        |-> Domain Agents (Shopify, Etsy) - Direct
        |-> SDK Agents - Via adapters

Usage:
    # Wrap APEG agent for SDK use
    from apeg_core.sdk_integration import APEGAgentAdapter
    sdk_agent = APEGAgentAdapter(shopify_agent).to_sdk_agent()

    # Use SDK agent in APEG
    from apeg_core.sdk_integration import SDKAgentWrapper
    apeg_agent = SDKAgentWrapper(sdk_agent)
"""

from .tool_bridge import ToolBridge, apeg_method_to_sdk_tool
from .adapters import APEGAgentAdapter, SDKAgentWrapper
from .handoff_coordinator import HandoffCoordinator

__all__ = [
    "APEGAgentAdapter",
    "SDKAgentWrapper",
    "ToolBridge",
    "apeg_method_to_sdk_tool",
    "HandoffCoordinator",
]
