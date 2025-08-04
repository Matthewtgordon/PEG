from src.memory_manager import MemoryManager


def test_memory_namespacing_and_summarization():
    mm = MemoryManager(short_term_limit=3)
    for i in range(5):
        mm.add("task1", f"msg{i}")
    assert "task1" in mm.long_term
    assert len(mm.short_term["task1"]) <= 3
    assert len(mm.query_long_term("task1")) >= 1
