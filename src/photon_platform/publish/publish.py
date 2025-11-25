"""
Core publishing functions.
"""
import os
import shutil
import http.server
import socketserver
import click
import sass
import subprocess
from sphinx.application import Sphinx

def find_git_root() -> str | None:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def build_sass() -> None:
    """Compile SASS files for all themes."""
    click.echo("Compiling SASS for all themes...")
    try:
        base_dir = os.path.dirname(__file__)
        themes_dir = os.path.join(base_dir, 'themes')

        for theme_name in os.listdir(themes_dir):
            theme_path = os.path.join(themes_dir, theme_name)
            if os.path.isdir(theme_path):
                scss_dir = os.path.join(theme_path, 'static', 'scss')
                css_dir = os.path.join(theme_path, 'static', 'css')

                if os.path.exists(scss_dir):
                    if not os.path.exists(css_dir):
                        os.makedirs(css_dir)
                    
                    for filename in os.listdir(scss_dir):
                        if filename.endswith('.scss') and not filename.startswith('_'):
                            scss_file = os.path.join(scss_dir, filename)
                            css_file = os.path.join(css_dir, filename.replace('.scss', '.css'))
                            
                            click.echo(f"  Compiling {filename} for theme: {theme_name}")
                            try:
                                with open(css_file, 'w') as f:
                                    f.write(sass.compile(filename=scss_file, output_style='expanded'))
                            except Exception as e:
                                click.echo(f"  Error compiling {filename}: {e}", err=True)
                else:
                    click.echo(f"  No SASS directory found for theme: {theme_name}, skipping.")
        click.echo("SASS compilation successful.")
    except Exception as e:
        click.echo(f"Error compiling SASS: {e}", err=True)
        raise

def build() -> None:
    """Build the Sphinx documentation."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return

    src_dir = os.path.join(project_root, "docsrc")
    if not os.path.isdir(src_dir):
        click.echo(f"Error: 'docsrc' directory not found in project root: {project_root}", err=True)
        return

    build_sass()
    
    click.echo(f"Starting Sphinx build for project at: {project_root}")
    conf_dir = src_dir
    build_dir = os.path.join(project_root, "docs")
    doctree_dir = os.path.join(build_dir, ".doctrees")

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(doctree_dir, exist_ok=True)

    # Clear Sphinx environment and doctrees to ensure a clean build
    if os.path.exists(doctree_dir):
        shutil.rmtree(doctree_dir)
    os.makedirs(doctree_dir, exist_ok=True)

    app = Sphinx(
        srcdir=src_dir,
        confdir=conf_dir,
        outdir=build_dir,
        doctreedir=doctree_dir,
        buildername="html",
        warningiserror=False,
    )
    app.build()
    click.echo("Sphinx build completed successfully.")

def clean() -> None:
    """Remove the build directory."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return

    build_dir = os.path.join(project_root, "docs")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        click.echo(f"Removed build directory: {build_dir}")
    else:
        click.echo("Build directory not found.")

def test() -> None:
    """Build and serve the documentation locally."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return

    build()

    port = 8000
    build_dir = os.path.join(project_root, "docs")

    if not os.path.isdir(build_dir):
        click.echo("Build failed. 'docs' directory not found. Aborting test server.", err=True)
        return

    class ChDir:
        def __init__(self, new_path):
            self.new_path = os.path.expanduser(new_path)
            self.saved_path = os.getcwd()
        def __enter__(self):
            os.chdir(self.new_path)
        def __exit__(self, etype, evalue, traceback):
            os.chdir(self.saved_path)

    with ChDir(build_dir):
        Handler = http.server.SimpleHTTPRequestHandler
        # Allow the port to be reused immediately
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
    
    clean()

