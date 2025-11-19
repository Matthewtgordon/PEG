"""
Memory management for APEG runtime.

Components:
- MemoryStore: JSON-backed persistence for runtime data
- get_memory_store: Get global memory store instance
"""

from apeg_core.memory.memory_store import MemoryStore, get_memory_store

__all__ = ["MemoryStore", "get_memory_store"]
