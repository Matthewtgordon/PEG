from src.connectors.openai_connector import OpenAIConnector
from src.connectors.github_connector import GitHubConnector
from src.connectors.filesystem_connector import FilesystemConnector


def test_openai_connector():
    conn = OpenAIConnector()
    conn.connect()
    resp = conn.query("test")
    assert "test" in resp
    conn.disconnect()


def test_github_connector():
    conn = GitHubConnector()
    conn.connect()
    resp = conn.query("repo")
    assert resp["repo"] == "repo"
    conn.disconnect()


def test_filesystem_connector(tmp_path):
    p = tmp_path / "file.txt"
    p.write_text("data", encoding="utf-8")
    conn = FilesystemConnector()
    conn.connect()
    data = conn.query(str(p))
    assert data == "data"
    conn.disconnect()
