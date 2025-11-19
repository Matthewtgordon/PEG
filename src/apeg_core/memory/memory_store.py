"""
APEG Memory Store - Lightweight JSON-backed persistence for runtime data.

This module provides simple JSON file storage for:
- Runtime statistics (bandit weights, performance metrics)
- Run history (past workflow executions with results)
- Store data (arbitrary key-value storage)
- Session metadata

Design principles:
- Single JSON file for simplicity (APEGMemory.json)
- Automatic save on modifications
- Safe for Raspberry Pi (small file size, minimal I/O)
- Thread-safe basic operations
- Graceful degradation on file errors

Structure:
{
    "version": "1.0.0",
    "metadata": {
        "created_at": "2025-11-19T...",
        "last_updated": "2025-11-19T...",
        "total_runs": 42
    },
    "runtime_stats": {
        "bandit_weights": {...},
        "performance": {...}
    },
    "runs": [
        {
            "timestamp": "2025-11-19T...",
            "goal": "...",
            "success": true,
            "score": 0.85,
            "duration_ms": 1234
        }
    ],
    "stores": {
        "custom_key": "custom_value"
    }
}
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    JSON-backed memory store for APEG runtime data.

    Provides simple persistence for:
    - Runtime stats (bandit weights, metrics)
    - Run history (workflow execution summaries)
    - Arbitrary key-value stores

    Thread safety: Basic operations are atomic via file writes,
    but concurrent access from multiple processes is not supported.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """
        Initialize memory store.

        Args:
            path: Path to memory JSON file (default: APEGMemory.json in repo root)
        """
        if path is None:
            # Default to repo root
            path = self._find_repo_root() / "APEGMemory.json"

        self.path = Path(path) if isinstance(path, str) else path
        self.data: Dict[str, Any] = self._initialize_data()
        self._load()

        logger.info("Memory store initialized at %s", self.path)

    def _find_repo_root(self) -> Path:
        """
        Find repository root by looking for SessionConfig.json.

        Returns:
            Repository root path
        """
        # Start from current file location and go up
        current = Path(__file__).parent
        for _ in range(5):  # Check up to 5 levels up
            if (current / "SessionConfig.json").exists():
                return current
            current = current.parent

        # Fall back to cwd
        if (Path.cwd() / "SessionConfig.json").exists():
            return Path.cwd()

        # Last resort: cwd
        logger.warning("Could not find repo root, using cwd")
        return Path.cwd()

    def _initialize_data(self) -> Dict[str, Any]:
        """
        Initialize empty data structure.

        Returns:
            Empty data dictionary with proper structure
        """
        return {
            "version": "1.0.0",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_runs": 0,
            },
            "runtime_stats": {},
            "runs": [],
            "stores": {},
        }

    def _load(self) -> None:
        """
        Load data from JSON file.

        If file doesn't exist or is invalid, keeps initialized data.
        """
        if not self.path.exists():
            logger.info("Memory file does not exist, will create on first save")
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)

                # Merge with initialized structure (in case of schema updates)
                self.data.update(loaded)

                # Ensure all required keys exist
                if "metadata" not in self.data:
                    self.data["metadata"] = self._initialize_data()["metadata"]
                if "runtime_stats" not in self.data:
                    self.data["runtime_stats"] = {}
                if "runs" not in self.data:
                    self.data["runs"] = []
                if "stores" not in self.data:
                    self.data["stores"] = {}

                logger.info("Loaded memory from %s", self.path)

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in memory file: %s", e)
            logger.warning("Using empty memory structure")

        except Exception as e:
            logger.error("Failed to load memory file: %s", e)
            logger.warning("Using empty memory structure")

    def save(self) -> None:
        """
        Save data to JSON file.

        Updates last_updated timestamp before saving.
        """
        try:
            # Update metadata
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()

            # Ensure parent directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically (write to temp file, then rename)
            temp_path = self.path.with_suffix(".tmp")

            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.path)

            logger.debug("Saved memory to %s", self.path)

        except Exception as e:
            logger.error("Failed to save memory: %s", e)

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata dictionary.

        Returns:
            Metadata dictionary
        """
        return self.data.get("metadata", {})

    def append_run(self, summary: Dict[str, Any]) -> None:
        """
        Append a run summary to history.

        Args:
            summary: Run summary dictionary with fields:
                - timestamp: ISO timestamp (optional, will be added)
                - goal: Task goal
                - success: Whether run succeeded
                - score: Quality score (optional)
                - duration_ms: Duration in milliseconds (optional)
                - ... other custom fields
        """
        # Ensure timestamp
        if "timestamp" not in summary:
            summary["timestamp"] = datetime.now().isoformat()

        # Append to runs
        self.data.setdefault("runs", []).append(summary)

        # Update metadata
        self.data["metadata"]["total_runs"] = len(self.data["runs"])

        # Save
        self.save()

        logger.info("Appended run to memory (total: %d)", len(self.data["runs"]))

    def get_runs(
        self,
        limit: Optional[int] = None,
        success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get run history.

        Args:
            limit: Maximum number of runs to return (most recent first)
            success_only: Only return successful runs

        Returns:
            List of run summary dictionaries
        """
        runs = self.data.get("runs", [])

        # Filter by success if requested
        if success_only:
            runs = [r for r in runs if r.get("success", False)]

        # Sort by timestamp (most recent first)
        runs = sorted(
            runs,
            key=lambda r: r.get("timestamp", ""),
            reverse=True
        )

        # Apply limit
        if limit is not None:
            runs = runs[:limit]

        return runs

    def update_runtime_stat(self, key: str, value: Any) -> None:
        """
        Update a runtime statistic.

        Args:
            key: Stat key (e.g., "bandit_weights", "circuit_breaker_trips")
            value: Stat value (any JSON-serializable type)
        """
        self.data.setdefault("runtime_stats", {})[key] = value
        self.save()

        logger.debug("Updated runtime stat: %s", key)

    def get_runtime_stat(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a runtime statistic.

        Args:
            key: Stat key
            default: Default value if key not found

        Returns:
            Stat value or default
        """
        return self.data.get("runtime_stats", {}).get(key, default)

    def set_store(self, key: str, value: Any) -> None:
        """
        Set a value in the general-purpose store.

        Args:
            key: Store key
            value: Store value (any JSON-serializable type)
        """
        self.data.setdefault("stores", {})[key] = value
        self.save()

        logger.debug("Set store value: %s", key)

    def get_store(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the general-purpose store.

        Args:
            key: Store key
            default: Default value if key not found

        Returns:
            Store value or default
        """
        return self.data.get("stores", {}).get(key, default)

    def delete_store(self, key: str) -> None:
        """
        Delete a key from the store.

        Args:
            key: Store key to delete
        """
        stores = self.data.get("stores", {})
        if key in stores:
            del stores[key]
            self.save()
            logger.debug("Deleted store key: %s", key)

    def clear_runs(self, keep_recent: int = 0) -> None:
        """
        Clear run history.

        Args:
            keep_recent: Number of recent runs to keep (0 = clear all)
        """
        if keep_recent > 0:
            runs = self.get_runs(limit=keep_recent)
            self.data["runs"] = runs
        else:
            self.data["runs"] = []

        self.data["metadata"]["total_runs"] = len(self.data["runs"])
        self.save()

        logger.info("Cleared run history (kept %d recent)", keep_recent)

    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about stored data.

        Returns:
            Summary dictionary with counts and stats
        """
        runs = self.data.get("runs", [])
        successful_runs = [r for r in runs if r.get("success", False)]

        return {
            "total_runs": len(runs),
            "successful_runs": len(successful_runs),
            "success_rate": (
                len(successful_runs) / len(runs) if runs else 0.0
            ),
            "average_score": (
                sum(r.get("score", 0) for r in successful_runs) / len(successful_runs)
                if successful_runs else 0.0
            ),
            "runtime_stats_count": len(self.data.get("runtime_stats", {})),
            "store_keys_count": len(self.data.get("stores", {})),
            "last_updated": self.data["metadata"].get("last_updated"),
        }

    def export_to_file(self, export_path: Path | str) -> None:
        """
        Export memory data to a different file.

        Useful for backups or analysis.

        Args:
            export_path: Path to export file
        """
        export_path = Path(export_path) if isinstance(export_path, str) else export_path

        try:
            with export_path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            logger.info("Exported memory to %s", export_path)

        except Exception as e:
            logger.error("Failed to export memory: %s", e)


# Global instance (lazy initialization)
_global_store: Optional[MemoryStore] = None


def get_memory_store(path: Optional[Path] = None) -> MemoryStore:
    """
    Get global memory store instance.

    Args:
        path: Optional custom path (only used on first call)

    Returns:
        Global MemoryStore instance
    """
    global _global_store

    if _global_store is None:
        _global_store = MemoryStore(path)

    return _global_store


__all__ = [
    "MemoryStore",
    "get_memory_store",
]
