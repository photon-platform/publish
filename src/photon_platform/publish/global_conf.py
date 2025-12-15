"""A global, reusable configuration file for Sphinx documentation."""
import os
import sys
from datetime import datetime
import tomllib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'directives')))

html_context = {}


def setup_globals(org: str, org_name: str, repo: str, repo_name: str) -> None:
    """Set up global variables for the Sphinx configuration.

    Args:
        org: The GitHub organization or username.
        org_name: The display name of the organization.
        repo: The GitHub repository name.
        repo_name: The display name of the repository.

    """
    globals().update(
        {
            "org": org,
            "org_name": org_name,
            "repo": repo,
            "repo_name": repo_name,
            "blog_title": f"{org_name} • {repo_name}",
            "html_title": f"{org_name} • {repo_name}",
            "project": f"{org_name} • {repo_name}",
            "version": "",  # The short X.Y version.
            "release": "",  # The full version, including alpha/beta/rc tags.
            "copyright": f"{year}, {org_name}",
            "author": org_name,
            "blog_baseurl": f"https://{org}.github.io/{repo}",
            "html_base_url": f"https://{org}.github.io/{repo}",
            "html_baseurl": f"https://{org}.github.io/{repo}",
            "blog_authors": {"phi": ("phi ARCHITECT", None)},
        }
    )
    # Add exclusion for the main package index to avoid duplicates with modules/index.rst
    # We assume the structure modules/api/<namespace>/<repo>/index.rst
    # We use the 'include' variable parsed from pyproject.toml
    if 'include' in globals() and include and include != '*':
        # Construct path: modules/api/<include>/<repo>/index.rst
        # e.g. modules/api/photon_platform/publish/index.rst
        exclusion = f"modules/api/{include}/{repo}/index.rst"
        if 'exclude_patterns' in globals():
             # Check if it's already there to avoid duplicates if called multiple times
             if exclusion not in exclude_patterns:
                 exclude_patterns.append(exclusion)
    html_context.update(
        {
            "display_github": True,
            "github_user": org,
            "github_repo": repo,
            "github_version": "main",
            "conf_py_path": "/docsrc/",
            "org_name": org_name,
            "repo_name": repo_name,
        }
    )


year = datetime.now().year


# -- Sphinx Options -----------------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    #  "sphinx.ext.autodoc",
    #  "sphinx.ext.autosummary",
    # "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
    "sphinx.ext.mathjax",
    "sphinx.ext.todo",
    # "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinxcontrib.youtube",
    #  "sphinxcontrib.bibtex",
    "myst_parser",
    "sphinx_revealjs",
    "sphinx_revealjs.ext.footnotes",
    #  "sphinx_revealjs.ext.screenshot",
    #  "sphinxcontrib.budoux",
    #  "sphinxcontrib.gtagjs",
    #  "sphinxcontrib.oembed",
    "sphinxext.opengraph",
    "sphinx_carousel.carousel",
    "sphinxcontrib.jquery",
    "photon_platform.publish.directives.collection",
    "photon_platform.publish.images",
    "autoapi.extension",
]

# autosummary_generate = True

# AutoAPI options
# AutoAPI options

# Dynamic AutoAPI Configuration
# We walk up from the current working directory to find pyproject.toml
# This allows global_conf.py to adapt to the project it's being used in.
current_dir = os.getcwd()
project_root = None
pyproject_path = None
include = None # Initialize include

while current_dir != os.path.dirname(current_dir):
    potential_path = os.path.join(current_dir, 'pyproject.toml')
    if os.path.exists(potential_path):
        project_root = current_dir
        pyproject_path = potential_path
        break
    current_dir = os.path.dirname(current_dir)

# Default fallback
autoapi_dirs = [os.path.abspath('../src')]

if project_root and pyproject_path:
    try:
        with open(pyproject_path, 'rb') as f:
            pyproject_data = tomllib.load(f)
        
        # Extract package configuration
        find_config = pyproject_data.get('tool', {}).get('setuptools', {}).get('packages', {}).get('find', {})
        where = find_config.get('where', ['.'])[0]
        include = find_config.get('include', ['*'])[0]
        
        src_path = os.path.join(project_root, where)
        
        # Add src to sys.path so that modules can be imported
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            
        # Determine autoapi_dirs
        # If include is a specific package (not wildcard), point to it for namespace support
        # This mimics the 'geometor' configuration: ../src/geometor
        if include and '*' not in include:
            autoapi_dirs = [os.path.join(src_path, include)]
        else:
            autoapi_dirs = [src_path]
            
    except Exception as e:
        print(f"Warning: Error parsing pyproject.toml for AutoAPI config: {e}")

autoapi_options = [
    'members',
    'undoc-members',
    'show-inheritance',
    'show-module-summary',
    'special-members',
    'imported-members',
    # 'inherited-members',
]
autoapi_root = 'modules/api'
autoapi_python_use_implicit_namespaces = True
autoapi_keep_files = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [".archive", ".docs", "tests", "*.egg-info"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "gruvbox-dark"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.


html_theme = "foundation"


# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [os.path.abspath(os.path.join(os.path.dirname(__file__), 'themes'))]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Output file base name for HTML help builder.
htmlhelp_basename = "help_doc"


html_theme_options = {
    "display_version": False,
    "navigation_depth": -1,
    "prev_next_buttons_location": "both",
    "collapse_navigation": False,
    "includehidden": True,
    "titles_only": False,
    "sticky_navigation": True,
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.13", None),
    "sympy": ("https://docs.sympy.org/latest", None),
}

html_logo = "_static/logo.png"

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    #  'special-members': '__init__',
    "undoc-members": True,
    #  'exclude-members': '__weakref__'
    "show-inheritance": True,
}

html_permalinks = True
