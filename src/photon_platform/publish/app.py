
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



