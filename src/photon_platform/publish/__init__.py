"""
``photon_platform.publish``

- templates and styles for the PHOTON theme
- custom directives for processing collections
"""
import os

__author__ = "PHOTON platform"
__maintainer__ = "PHOTON platform"
__email__ = "github@phiarchitect.com"
__version__ = "0.2.14"
__licence__ = "MIT"

def get_path() -> str:
    """Return the absolute path to the theme's directory."""
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "themes")
