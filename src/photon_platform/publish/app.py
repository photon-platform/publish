
"""Command-line interface for the publish tool.
"""
import click

from . import publish


@click.group()
def cli():
    """A tool to streamline and enhance the Sphinx documentation framework."""

@cli.command()
@click.option('--repo', default=None, help='Path to target repository root (default: current directory).')
@click.option('--clean', 'clean_build', is_flag=True, help='Wipe .doctrees and regenerate autoapi from scratch.')
@click.option('-j', '--jobs', default=None, type=int, help='Number of parallel Sphinx workers (default: auto up to 8).')
@click.option('--json', 'as_json', is_flag=True, help='Emit compact JSON build summary.')
def build(repo, clean_build, jobs, as_json):
    """Builds the documentation (incremental by default; pass --clean for full rebuild)."""
    import json
    res = publish.build(repo=repo, clean=clean_build, jobs=jobs, quiet=as_json)
    if as_json:
        click.echo(json.dumps(res, indent=2))


@cli.command()
@click.option('--repo', default=None, help='Path to target repository root (default: current directory).')
def clean(repo):
    """Removes the docs/ build directory and generated autoapi files."""
    publish.clean(repo=repo)


@cli.command()
@click.option('--port', default=8000, help='Port to serve the documentation on.')
def test(port):
    """Builds and serves the documentation locally."""
    publish.test(port=port)


@cli.command()
@click.option('--repo', default=None, help='Path to target repository root (default: current directory).')
@click.option('--host', default='127.0.0.1', show_default=True, help='Host interface to bind.')
@click.option('-p', '--port', default=8000, show_default=True, type=int, help='Starting port (advances to next open port if busy).')
@click.option('-b', '--build', 'build_first', is_flag=True, help='Run incremental build before serving (auto-enabled if docs/ is missing).')
@click.option('--no-browser', is_flag=True, help='Do not automatically launch Chrome.')
def serve(repo, host, port, build_first, no_browser):
    """Serves docs/ on the first open port >= 8000 and launches Chrome."""
    publish.serve(
        repo=repo,
        host=host,
        port=port,
        build_first=build_first,
        open_browser=not no_browser,
    )


@cli.command()
@click.option('--repo', default=None, help='Path to target repository root (default: current directory).')
@click.option('--book', default=None, help='Book subdirectory in docsrc/ (auto-detected if omitted).')
@click.option('--output', '-o', default=None, help='Optional output path for the generated .epub file.')
def epub(repo, book, output):
    """Builds an EPUB 3 edition for the book subtree in docsrc/."""
    publish.build_epub(book=book, output=output, repo=repo)


@cli.command()
def mcp():
    """Launches the Model Context Protocol (MCP) JSON-RPC stdio server for publish."""
    from .mcp_server import run_stdio_jsonrpc
    run_stdio_jsonrpc()



@cli.command()
@click.option('--host', default='127.0.0.1', help='Host interface to bind (default: 127.0.0.1).')
@click.option('--port', default=5050, type=int, help='Port to serve the Folio Review app on (default: 5050).')
@click.option('--root', default=None, help='Path to resources/<edition> or repository root (auto-detected if omitted).')
@click.option('--title', default=None, help='Optional project title override.')
@click.option('--edition', default=None, help='Optional edition label override.')
@click.option('--debug', is_flag=True, help='Enable Flask debug mode.')
def folio(host, port, root, title, edition, debug):
    """Launches the interactive Folio Review & Vetting web application for resources/."""
    from pathlib import Path

    from .folio_review.app import create_app

    root_path = Path(root).resolve() if root else None
    app = create_app(root_dir=root_path, project_title=title, edition_label=edition)
    click.echo(
        f"Starting {app.config['PROJECT_TITLE']} ({app.config['EDITION_LABEL']}) "
        f"Folio Review at http://{host}:{port}"
    )
    app.run(host=host, port=port, debug=debug, use_reloader=True)


@cli.command("folio-links")
@click.option("--repo", default=".", help="Path to target repository root (default: current directory).")
@click.option("--optimize-scans", is_flag=True, help="Losslessly crush 4-digit .png folio scans in resources/.")
@click.option("--grayscale", is_flag=True, help="Convert all 4-digit .png folio scans to 8-bit grayscale when optimizing.")
@click.option("--json", "as_json", is_flag=True, help="Emit structured JSON report.")
def folio_links_cmd(repo, optimize_scans, grayscale, as_json):
    """Audits primary-source .. folio:: and :folio: links (and optionally optimizes scans)."""
    import json
    from dataclasses import asdict
    from pathlib import Path

    from .folio_links import audit_repo_folio_links, optimize_repo_folio_scans

    repo_root = Path(repo).resolve()
    opt_stats = None
    if optimize_scans:
        opt_stats = optimize_repo_folio_scans(repo_root, force_grayscale=grayscale)

    report = audit_repo_folio_links(repo_root)
    payload = asdict(report)
    payload.pop("env", None)
    if opt_stats is not None:
        payload["scan_optimization"] = opt_stats

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    if opt_stats is not None:
        click.echo(
            f"[optimize-scans] checked={opt_stats['files_checked']}, "
            f"rewritten={opt_stats['files_rewritten']}, "
            f"saved={opt_stats['saved_mb']:.2f} MB "
            f"({opt_stats['before_bytes'] / 1048576:.2f} -> {opt_stats['after_bytes'] / 1048576:.2f} MB)"
        )
    click.echo(
        f"[{report.repo}] scans: tracked={report.tracked_scans}, ignored={report.ignored_scans} | "
        f"folio_map={report.folio_map_entries} | "
        f"directives={report.directives_resolved}/{report.directives_total} | "
        f"badges={report.badges_resolved}/{report.badges_total}"
    )
    for u in report.unresolved_directives[:10]:
        click.echo(f"  ! unresolved directive -> {u}")
    for u in report.unresolved_badges[:10]:
        click.echo(f"  ! unresolved badge     -> {u}")
    for s in report.sample_links[:3]:
        click.echo(f"  ✓ sample -> {s}")


@cli.command("social-banner")
@click.option("--repo", default=".", help="Path to target repository root (default: current directory).")
@click.option("--force", is_flag=True, help="Overwrite existing 1200x630 banners in docsrc/_static/social/.")
@click.option("--json", "as_json", is_flag=True, help="Emit structured JSON summary.")
def social_banner_cmd(repo, force, as_json):
    """Generates dedicated 1200x630 sharing-only PNG banners in docsrc/_static/social/."""
    import json

    from .social_meta import generate_repo_social_banners

    res = generate_repo_social_banners(repo, force=force)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    if not res.get("ok"):
        click.echo(f"Error: {res.get('error')}", err=True)
        raise SystemExit(1)
    click.echo(
        f"[{res['repo']}] social-banner: created={len(res['created'])}, skipped={len(res['skipped'])}"
    )
    for c in res["created"]:
        click.echo(f"  + {c}")


@cli.command("folio-ingest")
@click.option("--repo", default=".", help="Path to target repository root (default: current directory).")
@click.option("--pdf", default=None, help="Optional specific PDF path (discovers all PDFs in resources/ if omitted).")
@click.option("--edition", default=None, help="Optional edition directory slug under resources/.")
@click.option("--dpi", default=300, show_default=True, type=int, help="Rendering DPI for <NNNN>.png folio scans.")
@click.option("--preserve-color", is_flag=True, help="Preserve full RGB on color editions (e.g. Byrne 1847).")
@click.option("--vector-svg", is_flag=True, help="Also extract per-page vector SVGs via pdftocairo.")
@click.option("--first-page", default=None, type=int, help="Optional starting page (1-indexed).")
@click.option("--last-page", default=None, type=int, help="Optional ending page (1-indexed).")
@click.option("--force", is_flag=True, help="Re-render existing folio PNGs.")
@click.option("--json", "as_json", is_flag=True, help="Emit structured JSON manifest summary.")
def folio_ingest_cmd(repo, pdf, edition, dpi, preserve_color, vector_svg, first_page, last_page, force, as_json):
    """Renders 300-DPI <NNNN>.png folios, extracts embedded text & graphics, and updates folio_map.json."""
    import json

    from .folio_ingest import ingest_repo_pdfs

    res = ingest_repo_pdfs(
        repo,
        pdf=pdf,
        edition=edition,
        dpi=dpi,
        preserve_color=preserve_color,
        extract_vector_svg=vector_svg,
        first_page=first_page,
        last_page=last_page,
        force=force,
    )
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    if not res.get("ok"):
        click.echo(f"Error: {res.get('error')}", err=True)
        raise SystemExit(1)
    for ed in res.get("editions", []):
        click.echo(
            f"[{res['repo']}:{ed.get('edition')}] pages={ed.get('total_pages')} | "
            f"folios={ed.get('folio_png_count')} (+{ed.get('rendered_new_count')} new) | "
            f"text_pages={ed.get('extracted_text_pages')} | "
            f"graphics={ed.get('extracted_graphics_count')}"
        )

