
"""Command-line interface for the publish tool.
"""
import click
from . import publish

@click.group()
def cli():
    """A tool to streamline and enhance the Sphinx documentation framework."""
    pass

@cli.command()
def build():
    """Builds the documentation."""
    publish.build()

@cli.command()
@click.option('--port', default=8000, help='Port to serve the documentation on.')
def test(port):
    """Builds and serves the documentation locally."""
    publish.test(port=port)

@cli.command()
@click.option('--book', default=None, help='Book subdirectory in docsrc/ (auto-detected if omitted).')
@click.option('--output', '-o', default=None, help='Optional output path for the generated .epub file.')
def epub(book, output):
    """Builds an EPUB 3 edition for the book subtree in docsrc/."""
    publish.build_epub(book=book, output=output)


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
