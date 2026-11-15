"""Zero-dependency MCP stdio server for ``photon-platform/publish`` (``publish mcp``).

Supports both ``Content-Length`` framed and newline-delimited JSON-RPC 2.0 over stdio
on Python 3.13, keeping Sphinx and extensions warm in-process while returning compact,
noise-free JSON summaries for incremental HTML builds, batch builds, EPUB 3 builds,
and primary-source folio link audits.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, BinaryIO

from . import __version__, publish
from .folio_links import audit_repo_folio_links, optimize_repo_folio_scans

_MODULE_MTIMES: dict[str, float] = {}


def _reload_modified_publish_modules() -> None:
    """Reload editable photon_platform.publish submodules modified on disk since import."""
    prefix = "photon_platform.publish."
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name.startswith(prefix) or mod_name.endswith(".mcp_server"):
            continue
        mod_file = getattr(mod, "__file__", None)
        if not mod_file or not mod_file.endswith(".py"):
            continue
        try:
            mtime = Path(mod_file).stat().st_mtime
        except OSError:
            continue
        prev = _MODULE_MTIMES.get(mod_name)
        _MODULE_MTIMES[mod_name] = mtime
        if prev is not None and mtime > prev:
            with contextlib.suppress(Exception):
                importlib.reload(mod)


def publish_build(
    repo: str,
    clean: bool = False,
    jobs: int | None = None,
) -> dict[str, Any]:
    """Build Sphinx HTML documentation for ``repo`` (incremental by default)."""
    _reload_modified_publish_modules()
    return publish.build(repo=repo, clean=clean, jobs=jobs, quiet=True)


def publish_build_batch(
    repos: list[str],
    clean: bool = False,
    jobs: int | None = None,
) -> dict[str, Any]:
    """Build Sphinx HTML documentation across multiple repositories in a warm process."""
    _reload_modified_publish_modules()
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0
    for r in repos:
        res = publish.build(repo=r, clean=clean, jobs=jobs, quiet=True)
        results.append(res)
        if res.get("ok"):
            succeeded += 1
        else:
            failed += 1
    return {
        "ok": failed == 0,
        "total": len(repos),
        "succeeded": succeeded,
        "failed": failed,
        "total_elapsed_s": round(time.perf_counter() - t0, 2),
        "results": results,
    }


def publish_clean(repo: str) -> dict[str, Any]:
    """Remove ``docs/`` and generated ``docsrc/modules/api/`` for ``repo``."""
    return publish.clean(repo=repo, quiet=True)


def publish_epub(
    repo: str,
    book: str | None = None,
    output: str | None = None,
) -> dict[str, Any]:
    """Build EPUB 3 edition(s) for ``repo``."""
    t0 = time.perf_counter()
    built = publish.build_epub(book=book, output=output, repo=repo, quiet=True)
    return {
        "ok": len(built) > 0,
        "repo": repo,
        "built_epubs": built,
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }


def publish_folio_links(
    repo: str,
    optimize_scans: bool = False,
    grayscale: bool = False,
) -> dict[str, Any]:
    """Audit ``.. folio::`` directives and ``:folio:`` badges for ``repo``."""
    repo_root = Path(repo).expanduser().resolve()
    opt_stats = None
    if optimize_scans:
        opt_stats = optimize_repo_folio_scans(repo_root, force_grayscale=grayscale)
    report = audit_repo_folio_links(repo_root)
    payload = asdict(report)
    if opt_stats is not None:
        payload["scan_optimization"] = opt_stats
    payload["unresolved_total"] = (
        (report.directives_total - report.directives_resolved)
        + (report.badges_total - report.badges_resolved)
    )
    payload["ok"] = payload["unresolved_total"] == 0
    return payload


TOOL_REGISTRY: dict[str, tuple[Callable[..., dict[str, Any]], dict[str, Any]]] = {
    "publish_build": (
        publish_build,
        {
            "description": (
                "Build Sphinx HTML documentation for a repository path into docs/. "
                "Incremental by default (reusing docs/.doctrees and cached autoapi when Python "
                "sources are unchanged) with multi-core parallel workers. Set clean=true only "
                "when forcing a full rebuild from scratch."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Absolute path to the target repository root.",
                    },
                    "clean": {
                        "type": "boolean",
                        "description": "Wipe docs/.doctrees and regenerate autoapi before building.",
                        "default": False,
                    },
                    "jobs": {
                        "type": "integer",
                        "description": "Optional number of parallel Sphinx workers (default: min(cpu_count, 8)).",
                        "minimum": 1,
                    },
                },
                "required": ["repo"],
            },
        },
    ),
    "publish_build_batch": (
        publish_build_batch,
        {
            "description": (
                "Build Sphinx HTML documentation across a list of repository root paths in a "
                "single warm Python process, returning compact per-repo timing and warning summaries."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute repository root paths to build.",
                    },
                    "clean": {
                        "type": "boolean",
                        "description": "Wipe docs/.doctrees and regenerate autoapi before building each repo.",
                        "default": False,
                    },
                    "jobs": {
                        "type": "integer",
                        "description": "Optional number of parallel Sphinx workers.",
                        "minimum": 1,
                    },
                },
                "required": ["repos"],
            },
        },
    ),
    "publish_clean": (
        publish_clean,
        {
            "description": "Remove docs/ and generated docsrc/modules/api/ for a repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Absolute path to the target repository root.",
                    },
                },
                "required": ["repo"],
            },
        },
    ),
    "publish_epub": (
        publish_epub,
        {
            "description": "Build EPUB 3 edition(s) for :layout: book codices in a repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Absolute path to the target repository root.",
                    },
                    "book": {
                        "type": "string",
                        "description": "Optional book subdirectory slug in docsrc/ (auto-detected if omitted).",
                    },
                    "output": {
                        "type": "string",
                        "description": "Optional output path for a single generated .epub file.",
                    },
                },
                "required": ["repo"],
            },
        },
    ),
    "publish_folio_links": (
        publish_folio_links,
        {
            "description": (
                "Audit primary-source .. folio:: directives and :folio: badges in a repository "
                "(and optionally crush 4-digit .png folio scans)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Absolute path to the target repository root.",
                    },
                    "optimize_scans": {
                        "type": "boolean",
                        "description": "Losslessly crush 4-digit .png folio scans in resources/.",
                        "default": False,
                    },
                    "grayscale": {
                        "type": "boolean",
                        "description": "Convert 4-digit .png folio scans to 8-bit grayscale when optimizing.",
                        "default": False,
                    },
                },
                "required": ["repo"],
            },
        },
    ),
}


def read_rpc_message(stream: BinaryIO) -> tuple[dict[str, Any] | None, str]:
    """Read one JSON-RPC message supporting both Content-Length framing and line-delimited JSON."""
    while True:
        first_line = stream.readline()
        if not first_line:
            return None, "line"
        stripped = first_line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(b"content-length:"):
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                hdr = stream.readline()
                if not hdr or hdr in (b"\r\n", b"\n"):
                    break
            body = stream.read(length)
            return json.loads(body.decode("utf-8")), "framed"
        return json.loads(stripped.decode("utf-8")), "line"


def write_rpc_message(stream: BinaryIO, payload: dict[str, Any], mode: str = "line") -> None:
    """Write a JSON-RPC response matching the client's framing mode."""
    raw = json.dumps(payload).encode("utf-8")
    if mode == "framed":
        header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
        stream.write(header + raw)
    else:
        stream.write(raw + b"\n")
    stream.flush()


def handle_rpc_request(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Process one JSON-RPC 2.0 request dictionary and return a response dictionary."""
    msg_id = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params") or {}

    if method.startswith("notifications/") or msg_id is None:
        return None

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "photon-publish", "version": __version__},
            },
        }

    if method == "tools/list":
        tools_list = [
            {
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["inputSchema"],
            }
            for name, (_, meta) in TOOL_REGISTRY.items()
        ]
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}

    if method == "tools/call":
        tname = params.get("name")
        targs = params.get("arguments") or {}
        if tname not in TOOL_REGISTRY:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tname}"},
            }
        fn, _ = TOOL_REGISTRY[tname]
        try:
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                out = fn(**targs)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(out, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio_jsonrpc() -> None:
    """Run the MCP JSON-RPC 2.0 server loop over standard input/output."""
    in_stream = sys.stdin.buffer
    out_stream = sys.stdout.buffer
    while True:
        try:
            msg, framing_mode = read_rpc_message(in_stream)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            sys.stderr.write(f"publish-mcp parse error: {exc}\n")
            continue
        if msg is None:
            break
        resp = handle_rpc_request(msg)
        if resp is not None:
            write_rpc_message(out_stream, resp, mode=framing_mode)


def call_mcp_stdio(
    tool_name: str,
    arguments: dict[str, Any],
    server_cmd: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute a full MCP stdio JSON-RPC handshake + ``tools/call`` for tests and CLI."""
    cmd = server_cmd or [sys.executable, "-m", "photon_platform.publish.mcp_server"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        write_rpc_message(
            proc.stdin,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "publish-mcp-client", "version": __version__},
                },
            },
            mode="framed",
        )
        init_resp, _ = read_rpc_message(proc.stdout)
        if not init_resp or "error" in init_resp:
            raise RuntimeError(f"MCP initialize failed: {init_resp}")

        write_rpc_message(
            proc.stdin,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            mode="framed",
        )
        write_rpc_message(
            proc.stdin,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            mode="framed",
        )
        call_resp, _ = read_rpc_message(proc.stdout)
        if not call_resp or "error" in call_resp:
            raise RuntimeError(f"MCP tools/call failed: {call_resp}")

        result = call_resp["result"]
        text_payload = result["content"][0]["text"]
        parsed = json.loads(text_payload)
        if result.get("isError"):
            raise RuntimeError(parsed.get("error", text_payload))
        return parsed
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


def main() -> None:
    """Entry point for ``publish-mcp`` / ``publish mcp`` stdio server."""
    run_stdio_jsonrpc()


if __name__ == "__main__":
    main()
