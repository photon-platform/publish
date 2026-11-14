"""Tests for ``publish serve``, automatic open-port discovery, and Chrome launcher."""

from __future__ import annotations

import socket
import threading
import time
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from photon_platform.publish import publish as pub_mod
from photon_platform.publish.app import cli


def test_find_open_port_skips_occupied_ports() -> None:
    """When port N and N+1 are actively listening, find_open_port(N) returns N+2."""
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.bind(("127.0.0.1", 0))
    s1.listen(1)
    base_port = s1.getsockname()[1]

    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            s2.bind(("127.0.0.1", base_port + 1))
            s2.listen(1)
            both_bound = True
        except OSError:
            both_bound = False

        chosen = pub_mod.find_open_port(start_port=base_port, host="127.0.0.1")
        assert chosen > base_port
        if both_bound:
            assert chosen >= base_port + 2
    finally:
        s1.close()
        s2.close()


def test_launch_chrome_prefers_google_chrome(monkeypatch) -> None:
    """launch_chrome spawns google-chrome detached with the target URL."""
    popen_calls: list[list[str]] = []

    def fake_which(cmd: str) -> str | None:
        return "/usr/bin/google-chrome" if cmd == "google-chrome" else None

    def fake_popen(args: list[str], **kwargs):
        popen_calls.append(list(args))
        return MagicMock()

    monkeypatch.delenv("PUBLISH_BROWSER", raising=False)
    monkeypatch.setattr(pub_mod.shutil, "which", fake_which)
    monkeypatch.setattr(pub_mod.subprocess, "Popen", fake_popen)

    launched = pub_mod.launch_chrome("http://localhost:8001")
    assert launched == "/usr/bin/google-chrome"
    assert popen_calls == [["/usr/bin/google-chrome", "http://localhost:8001"]]


def test_serve_cli_advances_port_launches_chrome_and_keeps_docs(tmp_path: Path, monkeypatch) -> None:
    """publish serve binds next open port after an occupied port, opens Chrome, serves HTML, and preserves docs/."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    index_file = docs_dir / "index.html"
    index_file.write_text("<html><body><h1>GEOMETOR Serve Test</h1></body></html>", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    # Occupy a port to verify serve advances past it
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied_port = blocker.getsockname()[1]

    launched_urls: list[str] = []

    def fake_launch_chrome(url: str) -> str:
        launched_urls.append(url)
        return "/usr/bin/google-chrome"

    orig_server_cls = pub_mod._DocsHTTPServer
    created_servers: list[pub_mod._DocsHTTPServer] = []

    class ControlledServer(orig_server_cls):
        def serve_forever(self, poll_interval: float = 0.05) -> None:
            created_servers.append(self)
            t = threading.Thread(target=super().serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            t.start()
            # Perform live HTTP request while server is up, then shut down cleanly
            url = f"http://127.0.0.1:{self.server_port}/index.html"
            for _ in range(20):
                try:
                    with urllib.request.urlopen(url, timeout=1.0) as resp:
                        body = resp.read().decode("utf-8")
                        assert "GEOMETOR Serve Test" in body
                        break
                except OSError:
                    time.sleep(0.02)
            super().shutdown()
            t.join(timeout=1.0)

    monkeypatch.setattr(pub_mod, "launch_chrome", fake_launch_chrome)
    monkeypatch.setattr(pub_mod, "_DocsHTTPServer", ControlledServer)

    try:
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--repo", str(tmp_path), "--port", str(occupied_port)])
        assert result.exit_code == 0, result.output
        assert len(created_servers) == 1
        actual_port = created_servers[0].server_port
        assert actual_port > occupied_port
        assert launched_urls == [f"http://localhost:{actual_port}"]
        assert f"Port {occupied_port} is busy; using open port {actual_port}." in result.output
        # Unlike `publish test`, `publish serve` MUST keep docs/ intact after stopping!
        assert index_file.is_file()
    finally:
        blocker.close()
