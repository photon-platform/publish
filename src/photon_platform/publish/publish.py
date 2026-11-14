"""Core publishing functions.
"""
from __future__ import annotations

import http.server
import io
import os
import shutil
import socketserver
import subprocess
import sys
import time
from typing import Any

import click
import sass
from sphinx.application import Sphinx


class _ChDir:
    """Context manager to temporarily switch working directory."""

    def __init__(self, new_path: str) -> None:
        self.new_path = os.path.abspath(os.path.expanduser(new_path))
        self.saved_path = os.getcwd()

    def __enter__(self) -> str:
        os.chdir(self.new_path)
        return self.new_path

    def __exit__(self, etype: object, evalue: object, traceback: object) -> None:
        os.chdir(self.saved_path)


def find_git_root(start_dir: str | None = None) -> str | None:
    """Find the git repository root from start_dir (or current working directory)."""
    target = os.path.abspath(os.path.expanduser(start_dir)) if start_dir else None
    if target and os.path.isdir(os.path.join(target, ".git")):
        return target
    try:
        cmd = ["git"]
        if target:
            cmd.extend(["-C", target])
        cmd.extend(["rev-parse", "--show-toplevel"])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return target if (target and os.path.isdir(os.path.join(target, "docsrc"))) else None


def _latest_mtime_in_tree(directory: str, suffix: str) -> float:
    latest = 0.0
    if not os.path.isdir(directory):
        return latest
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for fname in files:
            if fname.endswith(suffix):
                try:
                    mt = os.path.getmtime(os.path.join(root, fname))
                    latest = max(latest, mt)
                except OSError:
                    pass
    return latest


def _earliest_mtime_in_tree(directory: str, suffix: str) -> tuple[int, float]:
    count = 0
    earliest = float("inf")
    if not os.path.isdir(directory):
        return 0, 0.0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.endswith(suffix):
                count += 1
                try:
                    mt = os.path.getmtime(os.path.join(root, fname))
                    earliest = min(earliest, mt)
                except OSError:
                    pass
    return count, (earliest if count > 0 else 0.0)


def _should_regenerate_autoapi(project_root: str, api_dir: str, clean: bool) -> bool:
    """Return True only when clean=True, api_dir is missing/empty, or Python sources are newer."""
    if clean or not os.path.isdir(api_dir):
        return True
    rst_count, min_api_mtime = _earliest_mtime_in_tree(api_dir, ".rst")
    if rst_count == 0:
        return True
    src_root = os.path.join(project_root, "src")
    if not os.path.isdir(src_root):
        return False
    max_py_mtime = _latest_mtime_in_tree(src_root, ".py")
    return max_py_mtime > min_api_mtime


def build_sass(force: bool = False, quiet: bool = False) -> None:
    """Compile SASS files for themes only when .scss sources are newer than compiled .css."""
    base_dir = os.path.dirname(__file__)
    themes_dir = os.path.join(base_dir, "themes")
    if not os.path.isdir(themes_dir):
        return

    for theme_name in sorted(os.listdir(themes_dir)):
        theme_path = os.path.join(themes_dir, theme_name)
        if not os.path.isdir(theme_path):
            continue
        scss_dir = os.path.join(theme_path, "static", "scss")
        css_dir = os.path.join(theme_path, "static", "css")
        if not os.path.isdir(scss_dir):
            continue

        latest_scss = _latest_mtime_in_tree(scss_dir, ".scss")
        for filename in sorted(os.listdir(scss_dir)):
            if filename.endswith(".scss") and not filename.startswith("_"):
                scss_file = os.path.join(scss_dir, filename)
                css_file = os.path.join(css_dir, filename.replace(".scss", ".css"))
                if not force and os.path.isfile(css_file):
                    try:
                        if os.path.getmtime(css_file) >= latest_scss:
                            continue
                    except OSError:
                        pass
                if not quiet:
                    click.echo(f"Compiling {filename} for theme: {theme_name}")
                try:
                    os.makedirs(css_dir, exist_ok=True)
                    compiled = sass.compile(filename=scss_file, output_style="expanded")
                    with open(css_file, "w", encoding="utf-8") as f:
                        f.write(compiled)
                except OSError as exc:
                    if not quiet:
                        click.echo(f"  Skipping read-only CSS write for {filename}: {exc}", err=True)
                except sass.CompileError as exc:
                    if not quiet:
                        click.echo(f"  Error compiling {filename}: {exc}", err=True)


def build(
    repo: str | None = None,
    clean: bool = False,
    jobs: int | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """Build the Sphinx HTML documentation (incremental by default; full wipe when clean=True)."""
    t0 = time.perf_counter()
    project_root = find_git_root(repo)
    if not project_root:
        msg = f"Error: Not a git repository or valid project path: {repo or os.getcwd()}"
        if not quiet:
            click.echo(msg, err=True)
        return {"ok": False, "repo": repo or os.getcwd(), "error": msg}

    src_dir = os.path.join(project_root, "docsrc")
    if not os.path.isdir(src_dir):
        msg = f"Error: 'docsrc' directory not found in project root: {project_root}"
        if not quiet:
            click.echo(msg, err=True)
        return {"ok": False, "repo": project_root, "error": msg}

    build_sass(force=clean, quiet=quiet)

    mode = "clean" if clean else "incremental"
    parallel = jobs if (jobs is not None and jobs >= 1) else min(os.cpu_count() or 1, 8)
    if not quiet:
        click.echo(f"Starting Sphinx build ({mode}, jobs={parallel}) for: {project_root}")

    conf_dir = src_dir
    build_dir = os.path.join(project_root, "docs")
    doctree_dir = os.path.join(build_dir, ".doctrees")
    api_dir = os.path.join(src_dir, "modules", "api")

    if clean and os.path.exists(doctree_dir):
        shutil.rmtree(doctree_dir)

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(doctree_dir, exist_ok=True)

    regen_autoapi = _should_regenerate_autoapi(project_root, api_dir, clean=clean)
    confoverrides: dict[str, Any] = {}
    if regen_autoapi:
        if os.path.exists(api_dir):
            shutil.rmtree(api_dir)
    else:
        confoverrides["autoapi_generate_api_docs"] = False

    status_stream = io.StringIO() if quiet else sys.stdout
    warning_buf = io.StringIO()

    with _ChDir(project_root):
        sys.modules.pop("photon_platform.publish.global_conf", None)
        app = Sphinx(
            srcdir=src_dir,
            confdir=conf_dir,
            outdir=build_dir,
            doctreedir=doctree_dir,
            buildername="html",
            confoverrides=confoverrides,
            status=status_stream,
            warning=warning_buf,
            freshenv=clean,
            warningiserror=False,
            parallel=parallel,
        )
        app.build(force_all=clean)

    import re
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    raw_warnings = [ansi_re.sub("", ln).strip() for ln in warning_buf.getvalue().splitlines() if ln.strip()]
    if raw_warnings and not quiet:
        for w in raw_warnings:
            click.echo(w, err=True)

    elapsed = round(time.perf_counter() - t0, 2)
    if not quiet:
        click.echo(f"Sphinx build completed in {elapsed:.2f}s ({len(raw_warnings)} warnings).")

    return {
        "ok": True,
        "repo": project_root,
        "mode": mode,
        "jobs": parallel,
        "autoapi_regenerated": regen_autoapi,
        "elapsed_s": elapsed,
        "warnings_count": len(raw_warnings),
        "warnings": raw_warnings[:25],
    }


def clean(repo: str | None = None, quiet: bool = False) -> dict[str, Any]:
    """Remove the docs/ build directory and generated autoapi files."""
    project_root = find_git_root(repo)
    if not project_root:
        msg = "Error: Not a git repository. Cannot determine project root."
        if not quiet:
            click.echo(msg, err=True)
        return {"ok": False, "error": msg}

    api_dir = os.path.join(project_root, "docsrc", "modules", "api")
    if os.path.exists(api_dir):
        shutil.rmtree(api_dir)

    build_dir = os.path.join(project_root, "docs")
    removed = False
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        removed = True
        if not quiet:
            click.echo(f"Removed build directory: {build_dir}")
    elif not quiet:
        click.echo("Build directory not found.")
    return {"ok": True, "repo": project_root, "removed": removed}


def test(port: int = 8000) -> None:
    """Build and serve the documentation locally."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return

    build(repo=project_root)

    build_dir = os.path.join(project_root, "docs")

    if not os.path.isdir(build_dir):
        click.echo("Build failed. 'docs' directory not found. Aborting test server.", err=True)
        return

    with _ChDir(build_dir):
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", port), Handler)

        click.echo(f"Serving documentation on http://localhost:{port}")
        click.echo("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            click.echo("Stopping server...")
        finally:
            httpd.server_close()

    clean(repo=project_root)


def discover_books(docsrc_dir: str) -> list[dict[str, str]]:
    """Discover book subtrees (marked with :layout: book or :book_title:) inside docsrc."""
    from .directives.collection import peek_metadata

    books: list[dict[str, str]] = []
    if not os.path.isdir(docsrc_dir):
        return books

    for entry in sorted(os.listdir(docsrc_dir)):
        sub_path = os.path.join(docsrc_dir, entry)
        idx_rst = os.path.join(sub_path, "index.rst")
        if os.path.isdir(sub_path) and not entry.startswith((".", "_")) and os.path.isfile(idx_rst):
            meta = peek_metadata(idx_rst)
            if meta.get("layout") == "book" or "book_title" in meta:
                books.append({"slug": entry, "srcdir": sub_path, "index_rst": idx_rst, **meta})

    if not books:
        root_idx = os.path.join(docsrc_dir, "index.rst")
        if os.path.isfile(root_idx):
            meta = peek_metadata(root_idx)
            if meta.get("layout") == "book" or "book_title" in meta:
                slug = os.path.basename(os.path.dirname(docsrc_dir))
                books.append({"slug": slug, "srcdir": docsrc_dir, "index_rst": root_idx, **meta})

    return books


def build_epub(
    book: str | None = None,
    output: str | None = None,
    repo: str | None = None,
    quiet: bool = False,
) -> list[str]:
    """Build an EPUB 3 edition for a book subtree in docsrc."""
    from .directives.collection import peek_metadata

    project_root = find_git_root(repo)
    if not project_root:
        if not quiet:
            click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return []

    docsrc_dir = os.path.join(project_root, "docsrc")
    if not os.path.isdir(docsrc_dir):
        if not quiet:
            click.echo(f"Error: 'docsrc' directory not found in project root: {project_root}", err=True)
        return []

    if book:
        cand_dir = os.path.join(docsrc_dir, book) if book != "." else docsrc_dir
        idx_rst = os.path.join(cand_dir, "index.rst")
        if not os.path.isfile(idx_rst):
            if not quiet:
                click.echo(f"Error: Book index not found at {idx_rst}", err=True)
            return []
        meta = peek_metadata(idx_rst)
        slug = book if book != "." else os.path.basename(project_root)
        books = [{"slug": slug, "srcdir": cand_dir, "index_rst": idx_rst, **meta}]
    else:
        books = discover_books(docsrc_dir)
        if not books:
            if not quiet:
                click.echo("Error: No book subtree (:layout: book) found in docsrc/.", err=True)
            return []

    base_dir = os.path.dirname(__file__)
    epub_css_dir = os.path.join(base_dir, "themes", "foundation", "static", "css")
    docs_dir = os.path.join(project_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    built_epubs: list[str] = []

    for b in books:
        slug = b["slug"]
        book_srcdir = b["srcdir"]
        book_title = b.get("book_title") or b.get("title") or slug
        book_subtitle = b.get("book_subtitle") or b.get("subtitle") or ""
        full_title = f"{book_title}: {book_subtitle}" if book_subtitle else book_title
        author = b.get("author") or "GEOMETOR"
        publisher = b.get("publisher") or "GEOMETOR"
        year = b.get("year") or ""
        copyright_str = (
            f"{year}, {publisher} • Digital Edition GEOMETOR"
            if year
            else f"{publisher} • Digital Edition GEOMETOR"
        )

        if not quiet:
            click.echo(f"Building EPUB 3 for '{full_title}' ({slug})...")

        epub_work_dir = os.path.join(docs_dir, ".epub_build", slug)
        doctree_dir = os.path.join(docs_dir, ".epub_build", f"{slug}_doctrees")
        for d in (epub_work_dir, doctree_dir):
            if os.path.exists(d):
                shutil.rmtree(d)
        os.makedirs(doctree_dir, exist_ok=True)

        confoverrides = {
            "master_doc": "index",
            "project": full_title,
            "html_title": full_title,
            "author": author,
            "copyright": copyright_str,
            "epub_title": full_title,
            "epub_author": author,
            "epub_publisher": f"{publisher} • GEOMETOR",
            "epub_copyright": copyright_str,
            "epub_basename": slug,
            "epub_theme": "epub",
            "epub_show_urls": "no",
            "html_permalinks": False,
            "html_static_path": [epub_css_dir],
            "extensions": [
                "photon_platform.publish.directives.collection",
                "photon_platform.publish.directives.elements",
                "photon_platform.publish.roles.geometry",
                "photon_platform.publish.book",
                "photon_platform.publish.images",
                "sphinx.ext.graphviz",
                "sphinx.ext.todo",
            ],
            "graphviz_output_format": "svg",
            "epub_exclude_files": [
                "_static/opensearch.xml",
                "_static/doctools.js",
                "_static/language_data.js",
                "_static/searchtools.js",
                "_static/documentation_options.js",
                "_static/sphinx_highlight.js",
                ".nojekyll",
                ".buildinfo",
            ],
            "exclude_patterns": [
                ".archive",
                ".docs",
                "tests",
                "*.egg-info",
                "agent-chronicle.rst",
                "scan-inventory.rst",
                "**/*-3.1.rst",
                "*-3.1.rst",
            ],
        }

        status_stream = io.StringIO() if quiet else sys.stdout
        warning_stream = io.StringIO() if quiet else sys.stderr
        with _ChDir(project_root):
            sys.modules.pop("photon_platform.publish.global_conf", None)
            app = Sphinx(
                srcdir=book_srcdir,
                confdir=docsrc_dir,
                outdir=epub_work_dir,
                doctreedir=doctree_dir,
                buildername="epub",
                confoverrides=confoverrides,
                status=status_stream,
                warning=warning_stream,
                warningiserror=False,
            )
            app.build()

        generated_epub = os.path.join(epub_work_dir, f"{slug}.epub")
        if os.path.isfile(generated_epub):
            target_path = os.path.abspath(output) if output else os.path.join(docs_dir, f"{slug}.epub")
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(generated_epub, target_path)
            built_epubs.append(target_path)
            if not quiet:
                click.echo(f"EPUB 3 created: {target_path}")

    return built_epubs



