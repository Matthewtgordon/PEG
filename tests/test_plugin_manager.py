from src.plugin_manager import PluginManager


class DummyPlugin:
    def __init__(self):
        self.initialized = False
        self.ran = False

    def setup(self) -> None:
        self.initialized = True

    def run(self, x: int) -> int:
        self.ran = True
        return x * 2

    def teardown(self) -> None:
        self.initialized = False


def test_plugin_lifecycle():
    manager = PluginManager([])
    manager.register_plugin("dummy", DummyPlugin)
    assert "dummy" in manager.plugins
    assert manager.run("dummy", 2) == 4
    manager.unload("dummy")
    assert "dummy" not in manager.plugins
