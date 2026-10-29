"""Core publishing functions.
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

    # Clear Sphinx environment, doctrees, and autoapi generated files to ensure a clean build
    if os.path.exists(doctree_dir):
        shutil.rmtree(doctree_dir)
    os.makedirs(doctree_dir, exist_ok=True)

    api_dir = os.path.join(src_dir, "modules", "api")
    if os.path.exists(api_dir):
        shutil.rmtree(api_dir)

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

    api_dir = os.path.join(project_root, "docsrc", "modules", "api")
    if os.path.exists(api_dir):
        shutil.rmtree(api_dir)

    build_dir = os.path.join(project_root, "docs")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        click.echo(f"Removed build directory: {build_dir}")
    else:
        click.echo("Build directory not found.")

def test(port: int = 8000) -> None:
    """Build and serve the documentation locally."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return

    build()

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


def build_epub(book: str | None = None, output: str | None = None) -> list[str]:
    """Build an EPUB 3 edition for a book subtree in docsrc."""
    from .directives.collection import peek_metadata

    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository. Cannot determine project root.", err=True)
        return []

    docsrc_dir = os.path.join(project_root, "docsrc")
    if not os.path.isdir(docsrc_dir):
        click.echo(f"Error: 'docsrc' directory not found in project root: {project_root}", err=True)
        return []

    if book:
        cand_dir = os.path.join(docsrc_dir, book) if book != "." else docsrc_dir
        idx_rst = os.path.join(cand_dir, "index.rst")
        if not os.path.isfile(idx_rst):
            click.echo(f"Error: Book index not found at {idx_rst}", err=True)
            return []
        meta = peek_metadata(idx_rst)
        slug = book if book != "." else os.path.basename(project_root)
        books = [{"slug": slug, "srcdir": cand_dir, "index_rst": idx_rst, **meta}]
    else:
        books = discover_books(docsrc_dir)
        if not books:
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

        app = Sphinx(
            srcdir=book_srcdir,
            confdir=docsrc_dir,
            outdir=epub_work_dir,
            doctreedir=doctree_dir,
            buildername="epub",
            confoverrides=confoverrides,
            warningiserror=False,
        )
        app.build()

        generated_epub = os.path.join(epub_work_dir, f"{slug}.epub")
        if os.path.isfile(generated_epub):
            target_path = os.path.abspath(output) if output else os.path.join(docs_dir, f"{slug}.epub")
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(generated_epub, target_path)
            built_epubs.append(target_path)
            click.echo(f"EPUB 3 created: {target_path}")

    return built_epubs


