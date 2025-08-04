from src.sandbox_executor import SandboxExecutor


def test_sandbox_runs_command():
    executor = SandboxExecutor(max_cpu_time=1, max_memory=32 * 1024 * 1024)
    result = executor.run("echo hello")
    assert result.returncode == 0
    assert "hello" in result.stdout
