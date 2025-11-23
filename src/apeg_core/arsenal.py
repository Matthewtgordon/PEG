"""
Arsenal Manager - Persistent storage for generated subagents and tools.

This module provides a persistent arsenal for storing and retrieving
dynamically generated subagents, their specifications, and associated
metadata. Enables agents to be reloaded across sessions without
regeneration.

Key Features:
- JSON-backed persistent storage
- Agent specification and code storage
- Testing status tracking
- Version management for agents
- Query and search capabilities
- Import/export functionality

Usage:
    arsenal = ArsenalManager()
    arsenal.add("my_agent", {"code": impl, "spec": spec, "tested": True})
    agent_data = arsenal.get("my_agent")
    all_agents = arsenal.list_agents()
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArsenalManager:
    """
    Persistent storage manager for generated agents and tools.

    The ArsenalManager maintains a JSON file containing all generated
    agent specifications, implementations, and metadata. This enables
    persistence across sessions and provides a registry of available
    dynamically-generated capabilities.

    Attributes:
        file: Path to arsenal JSON file
        arsenal: In-memory cache of arsenal contents
    """

    def __init__(
        self,
        file: str | Path = "arsenal.json",
        auto_load: bool = True
    ) -> None:
        """
        Initialize the ArsenalManager.

        Args:
            file: Path to arsenal storage file
            auto_load: Whether to load existing arsenal on init
        """
        self.file = Path(file)
        self.arsenal: Dict[str, Dict[str, Any]] = {}

        if auto_load:
            self.arsenal = self.load()

        logger.info(
            "ArsenalManager initialized with %d agents from %s",
            len(self.arsenal),
            self.file
        )

    def load(self) -> Dict[str, Dict[str, Any]]:
        """
        Load arsenal from persistence file.

        Returns:
            Dictionary of agent name to agent data
        """
        if not self.file.exists():
            logger.debug("Arsenal file does not exist: %s", self.file)
            return {}

        try:
            with self.file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both raw dict and versioned format
            if "version" in data and "agents" in data:
                return data["agents"]
            return data

        except json.JSONDecodeError as e:
            logger.error("Failed to parse arsenal file %s: %s", self.file, e)
            return {}
        except IOError as e:
            logger.error("Failed to read arsenal file %s: %s", self.file, e)
            return {}

    def save(self) -> bool:
        """
        Save arsenal to persistence file.

        Returns:
            True if save successful
        """
        try:
            # Create versioned structure
            data = {
                "version": "1.0.0",
                "metadata": {
                    "updated_at": datetime.now().isoformat(),
                    "agent_count": len(self.arsenal)
                },
                "agents": self.arsenal
            }

            # Atomic write: write to temp file then rename
            temp_file = self.file.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.file)
            logger.debug("Saved arsenal with %d agents to %s", len(self.arsenal), self.file)
            return True

        except IOError as e:
            logger.error("Failed to save arsenal to %s: %s", self.file, e)
            return False

    def add(
        self,
        name: str,
        spec: Dict[str, Any],
        replace: bool = False
    ) -> bool:
        """
        Add an agent to the arsenal.

        Args:
            name: Unique agent identifier
            spec: Agent specification including code, capabilities, etc.
            replace: Whether to replace existing agent with same name

        Returns:
            True if agent was added successfully
        """
        if name in self.arsenal and not replace:
            logger.warning("Agent '%s' already exists in arsenal", name)
            return False

        # Ensure required metadata
        spec.setdefault("added_at", datetime.now().isoformat())
        spec.setdefault("tested", False)
        spec.setdefault("version", "1.0.0")
        spec.setdefault("deployments", 0)

        if name in self.arsenal:
            # Update existing entry
            spec["updated_at"] = datetime.now().isoformat()
            spec["version"] = self._bump_version(self.arsenal[name].get("version", "1.0.0"))
            logger.info("Updated agent '%s' in arsenal (version %s)", name, spec["version"])
        else:
            logger.info("Added new agent '%s' to arsenal", name)

        self.arsenal[name] = spec
        self.save()
        return True

    def _bump_version(self, version: str) -> str:
        """Bump patch version number."""
        try:
            parts = version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except (ValueError, IndexError):
            return "1.0.1"

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get an agent from the arsenal.

        Args:
            name: Agent identifier

        Returns:
            Agent specification dictionary or None if not found
        """
        return self.arsenal.get(name)

    def remove(self, name: str) -> bool:
        """
        Remove an agent from the arsenal.

        Args:
            name: Agent identifier

        Returns:
            True if agent was removed
        """
        if name not in self.arsenal:
            return False

        del self.arsenal[name]
        self.save()
        logger.info("Removed agent '%s' from arsenal", name)
        return True

    def exists(self, name: str) -> bool:
        """Check if an agent exists in the arsenal."""
        return name in self.arsenal

    def list_agents(self) -> List[str]:
        """List all agent names in the arsenal."""
        return list(self.arsenal.keys())

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all agents in the arsenal."""
        return self.arsenal.copy()

    def mark_tested(self, name: str, test_results: List[bool] | None = None) -> bool:
        """
        Mark an agent as tested.

        Args:
            name: Agent identifier
            test_results: Optional list of test pass/fail results

        Returns:
            True if agent was updated
        """
        if name not in self.arsenal:
            return False

        self.arsenal[name]["tested"] = True
        self.arsenal[name]["tested_at"] = datetime.now().isoformat()

        if test_results:
            self.arsenal[name]["test_results"] = {
                "passed": sum(test_results),
                "total": len(test_results),
                "all_passed": all(test_results)
            }

        self.save()
        return True

    def mark_deployed(self, name: str) -> bool:
        """
        Increment deployment count for an agent.

        Args:
            name: Agent identifier

        Returns:
            True if agent was updated
        """
        if name not in self.arsenal:
            return False

        self.arsenal[name]["deployments"] = self.arsenal[name].get("deployments", 0) + 1
        self.arsenal[name]["last_deployed"] = datetime.now().isoformat()
        self.save()
        return True

    def query(
        self,
        tested_only: bool = False,
        has_capability: str | None = None,
        min_deployments: int = 0
    ) -> List[str]:
        """
        Query agents by criteria.

        Args:
            tested_only: Only return tested agents
            has_capability: Filter by capability
            min_deployments: Minimum deployment count

        Returns:
            List of matching agent names
        """
        results = []

        for name, spec in self.arsenal.items():
            # Check tested filter
            if tested_only and not spec.get("tested"):
                continue

            # Check deployments filter
            if spec.get("deployments", 0) < min_deployments:
                continue

            # Check capability filter
            if has_capability:
                capabilities = spec.get("capabilities", [])
                if has_capability not in capabilities:
                    continue

            results.append(name)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get arsenal statistics.

        Returns:
            Dictionary with counts and metrics
        """
        total = len(self.arsenal)
        tested = sum(1 for s in self.arsenal.values() if s.get("tested"))
        deployed = sum(1 for s in self.arsenal.values() if s.get("deployments", 0) > 0)
        total_deployments = sum(s.get("deployments", 0) for s in self.arsenal.values())

        return {
            "total_agents": total,
            "tested_agents": tested,
            "deployed_agents": deployed,
            "total_deployments": total_deployments,
            "untested_agents": total - tested
        }

    def export_to_file(self, export_path: str | Path) -> bool:
        """
        Export arsenal to a file.

        Args:
            export_path: Path to export file

        Returns:
            True if export successful
        """
        try:
            export_path = Path(export_path)
            data = {
                "version": "1.0.0",
                "exported_at": datetime.now().isoformat(),
                "agents": self.arsenal
            }
            with export_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Exported arsenal to %s", export_path)
            return True
        except IOError as e:
            logger.error("Failed to export arsenal: %s", e)
            return False

    def import_from_file(self, import_path: str | Path, merge: bool = True) -> int:
        """
        Import agents from a file.

        Args:
            import_path: Path to import file
            merge: If True, merge with existing; if False, replace

        Returns:
            Number of agents imported
        """
        try:
            import_path = Path(import_path)
            with import_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            agents = data.get("agents", data)

            if not merge:
                self.arsenal = {}

            count = 0
            for name, spec in agents.items():
                if self.add(name, spec, replace=True):
                    count += 1

            logger.info("Imported %d agents from %s", count, import_path)
            return count

        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to import arsenal: %s", e)
            return 0

    def clear(self) -> None:
        """Clear all agents from arsenal."""
        self.arsenal = {}
        self.save()
        logger.warning("Arsenal cleared")


# Global singleton instance
_default_arsenal: Optional[ArsenalManager] = None


def get_arsenal(file: str | Path = "arsenal.json") -> ArsenalManager:
    """
    Get or create the default arsenal manager.

    Args:
        file: Path to arsenal file

    Returns:
        ArsenalManager instance
    """
    global _default_arsenal
    if _default_arsenal is None:
        _default_arsenal = ArsenalManager(file=file)
    return _default_arsenal
