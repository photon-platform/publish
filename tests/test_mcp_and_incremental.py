"""Tests for incremental navigation invalidation, mtime-gated autoapi, and publish MCP server."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from photon_platform.publish import __version__
from photon_platform.publish.directives.collection import (
    _scan_root_navigation_items,
    check_root_navigation_outdated,
    inject_root_navigation,
)
from photon_platform.publish.mcp_server import (
    handle_rpc_request,
    read_rpc_message,
    write_rpc_message,
)
from photon_platform.publish.publish import _should_regenerate_autoapi


def test_incremental_root_navigation_invalidation(tmp_path: Path) -> None:
    docsrc = tmp_path / "docsrc"
    docsrc.mkdir()
    (docsrc / "index.rst").write_text("Home\n====\n", encoding="utf-8")
    mission = docsrc / "mission.rst"
    mission.write_text(":navigation: header\n:order: 10\n\nMission\n=======\n", encoding="utf-8")

    env = SimpleNamespace(srcdir=str(docsrc), found_docs={"index", "mission"})
    app = SimpleNamespace(
        builder=SimpleNamespace(name="html"),
        config=SimpleNamespace(master_doc="index"),
        env=env,
    )

    src = ["Home\n====\n"]
    inject_root_navigation(app, "index", src)
    assert "mission" in src[0]

    # Unchanged nav -> master_doc is NOT outdated
    assert check_root_navigation_outdated(app, env, set(), set(), set()) == []

    # Remove mission.rst and add about.rst -> master_doc IS marked outdated
    mission.unlink()
    (docsrc / "about.rst").write_text(
        ":navigation: header\n:order: 10\n:nav_title: About\n\nAbout\n=====\n",
        encoding="utf-8",
    )
    assert check_root_navigation_outdated(app, env, {"about"}, set(), {"mission"}) == ["index"]
    hdr, _ = _scan_root_navigation_items(str(docsrc), "index")
    assert [d["docname"] for d in hdr] == ["about"]


def test_autoapi_mtime_gate(tmp_path: Path) -> None:
    src_pkg = tmp_path / "src" / "pkg"
    src_pkg.mkdir(parents=True)
    py_file = src_pkg / "mod.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    api_dir = tmp_path / "docsrc" / "modules" / "api"
    assert _should_regenerate_autoapi(str(tmp_path), str(api_dir), clean=False) is True

    api_dir.mkdir(parents=True)
    rst_file = api_dir / "index.rst"
    rst_file.write_text("API\n===\n", encoding="utf-8")

    # API rst newer than or equal to py_file -> skip regeneration
    import os

    os.utime(py_file, (1000.0, 1000.0))
    os.utime(rst_file, (2000.0, 2000.0))
    assert _should_regenerate_autoapi(str(tmp_path), str(api_dir), clean=False) is False
    assert _should_regenerate_autoapi(str(tmp_path), str(api_dir), clean=True) is True

    # Touch py_file newer -> regenerate
    os.utime(py_file, (3000.0, 3000.0))
    assert _should_regenerate_autoapi(str(tmp_path), str(api_dir), clean=False) is True


def test_mcp_rpc_protocol_and_tools_list() -> None:
    init = handle_rpc_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init is not None
    assert init["result"]["serverInfo"] == {"name": "photon-publish", "version": __version__}

    tlist = handle_rpc_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert tlist is not None
    names = {t["name"] for t in tlist["result"]["tools"]}
    assert {
        "publish_build",
        "publish_build_batch",
        "publish_clean",
        "publish_epub",
        "publish_folio_links",
    }.issubset(names)

    # Verify Content-Length framing round-trip
    buf = io.BytesIO()
    write_rpc_message(buf, init, mode="framed")
    buf.seek(0)
    decoded, mode = read_rpc_message(buf)
    assert mode == "framed"
    assert decoded == init
