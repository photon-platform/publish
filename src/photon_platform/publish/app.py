
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




