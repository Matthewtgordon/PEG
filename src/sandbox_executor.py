You're running into this error on **Windows**:

```
ModuleNotFoundError: No module named 'resource'
```

This happens because the [`resource`](https://docs.python.org/3/library/resource.html) module **does not exist on Windows**—it is only available on Unix-like systems (Linux, macOS).

---

## How to Fix

You need to **import and use `resource` only if it is available**.  
Here’s the cross-platform way to do it:

### Update your `src/sandbox_executor.py` like this:

```python
"""
Sandboxed execution environment using subprocess with resource limits
and isolated temporary directories.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from typing import Any

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False


class SandboxExecutor:
    """Executes commands in a restricted sandbox."""

    def __init__(self, max_cpu_time: int = 5, max_memory: int = 64 * 1024 * 1024):
        self.max_cpu_time = max_cpu_time
        self.max_memory = max_memory
        self.logger = logging.getLogger(__name__)

    def _limit_resources(self) -> None:
        import sys
        if HAS_RESOURCE:
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))
            if sys.platform != "darwin":
                resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, self.max_memory))

    def run(self, command: str, timeout: int = 10) -> subprocess.CompletedProcess:
        """Run a shell command inside the sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=tmpdir,
                    preexec_fn=self._limit_resources if HAS_RESOURCE else None,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                return result
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Sandbox execution failed: %s", exc)
                raise
```

**Summary of changes:**
- Only import and use `resource` if available (`HAS_RESOURCE`).
- On Windows, `_limit_resources` will do nothing and `preexec_fn` will be `None`.  
- On Linux/macOS, nothing changes.

---

This will make your code and tests pass on all platforms—including Windows (no more `ModuleNotFoundError`).

Let me know if you need this as a downloadable file or pull request!
