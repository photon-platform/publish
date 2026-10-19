"""Folio Review & Vetting Web Application for PHOTON Publish.

Provides an interactive local web interface (`publish folio`) to inspect folio scans,
read and edit side-by-side RST/Markdown transcriptions and notes, verify graphic
bounding boxes on full-page scans, and track folio-by-folio vetting status
exclusively within a repository's `resources/` directory.
"""

from .app import create_app, main
from .reviews import ReviewManager
from .scanner import FolioScanner, discover_edition_root, infer_project_and_edition

__all__ = [
    "create_app",
    "main",
    "FolioScanner",
    "ReviewManager",
    "discover_edition_root",
    "infer_project_and_edition",
]
