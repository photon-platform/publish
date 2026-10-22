"""Book subtree inheritance and multi-track context injection for the 'Website in a Website' Codex layout."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from docutils import nodes
except ImportError:  # pragma: no cover
    nodes = None  # type: ignore

try:
    from photon_platform.publish.directives.collection import peek_metadata
except ImportError:  # pragma: no cover
    def peek_metadata(filepath: str) -> Dict[str, str]:
        """Peek at the beginning of an RST file to extract top field-list metadata."""
        meta: Dict[str, str] = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                head = f.read(2048)
                for line in head.split("\n")[:25]:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(":") and ":" in line[1:]:
                        parts = line[1:].split(":", 1)
                        if len(parts) == 2:
                            meta[parts[0].strip()] = parts[1].strip()
                    elif not line.startswith("..") and len(line) > 0:
                        break
        except Exception:
            pass
        return meta



def _get_doc_metadata(env: Any, docname: str) -> Dict[str, Any]:
    """Retrieve metadata for a docname from env.metadata with peek_metadata fallback."""
    meta: Dict[str, Any] = {}
    if hasattr(env, "metadata") and docname in env.metadata:
        meta.update(env.metadata[docname])

    srcdir = getattr(env, "srcdir", None)
    if srcdir:
        rst_path = os.path.join(str(srcdir), f"{docname}.rst")
        if os.path.exists(rst_path):
            early = peek_metadata(rst_path)
            for k, v in early.items():
                meta.setdefault(k, v)
    return meta


def _get_doc_title(env: Any, docname: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """Retrieve a clean title string for a docname."""
    if meta:
        if meta.get("book_title"):
            return str(meta["book_title"]).strip()
        if meta.get("title"):
            return str(meta["title"]).strip()
    titles = getattr(env, "titles", {})
    if docname in titles and titles[docname] is not None:
        return titles[docname].astext().strip()
    return docname


_TRACK_SUFFIX_PATTERNS: List[Tuple[str, str, str]] = [
    (r"^translation-notes-(.+)$", "notes", "Notes"),
    (r"^(.+)[._-]proposition$", "proposition", "Proposition"),
    (r"^(.+)[._-]en$", "en", "English"),
    (r"^(.+)[._-]it$", "it", "Italiano (1509)"),
    (r"^(.+)[._-]de$", "de", "Deutsch (1889)"),
    (r"^(.+)[._-]la$", "la", "Latin"),
    (r"^(.+)[._-]commentary$", "commentary", "Commentary"),
    (r"^(.+)[._-]summary$", "summary", "Summary"),
    (r"^(.+)[._-]notes$", "notes", "Notes"),
    (r"^(.+)[._-]folio$", "folio", "Folio"),
]


def _extract_unit_stem(basename: str, doc_dir: str) -> str:
    """Determine the shared unit stem for track sibling discovery."""
    for pattern, _key, _label in _TRACK_SUFFIX_PATTERNS:
        m = re.match(pattern, basename)
        if m:
            return m.group(1)
    if basename in {"index", "proposition", "commentary", "summary", "notes", "folio", "en", "it", "de", "la"}:
        return os.path.basename(doc_dir) if doc_dir else basename
    return basename


def detect_companion_tracks(env: Any, pagename: str) -> List[Dict[str, Any]]:
    """Detect companion tracks for `pagename` in `env.found_docs`.

    Supports:
    - Euclid / Elements tracks: ``index`` / ``proposition``, ``commentary``, ``notes``, ``folio``
      or ``<pagename>.commentary``, ``<pagename>.notes``
    - Pacioli tracks: ``<stem>_en``, ``<stem>_it``, ``<stem>_de``, ``<stem>_notes``, ``index``
    - Hoenen tracks: ``<stem>`` (Latin), ``<stem>-en``, ``<stem>-summary``, ``translation-notes-<stem>``
    """
    found_docs: Set[str] = set(getattr(env, "found_docs", set()))
    if not found_docs:
        return []

    doc_dir = os.path.dirname(pagename)
    basename = os.path.basename(pagename)
    stem = _extract_unit_stem(basename, doc_dir)

    def _qual(local_name: str) -> str:
        return f"{doc_dir}/{local_name}" if doc_dir else local_name

    # Determine if bare `<stem>` is the Latin/original primary track (e.g. Hoenen `caput-1/caput-1`)
    has_hyphen_or_under_en = _qual(f"{stem}-en") in found_docs or _qual(f"{stem}_en") in found_docs
    has_proposition_siblings = any(
        _qual(name) in found_docs
        for name in ("commentary", f"{stem}.commentary", f"{stem}_commentary", f"{stem}-commentary")
    )

    index_label = "Proposition" if has_proposition_siblings else "Overview"

    candidate_specs: List[Tuple[str, str, List[str]]] = [
        ("proposition", index_label, [_qual("index"), _qual("proposition"), _qual(f"{stem}.proposition")]),
        ("la", "Latin", ([_qual(stem)] if has_hyphen_or_under_en and stem != "index" else []) + [
            _qual(f"{stem}.la"),
            _qual(f"{stem}_la"),
            _qual(f"{stem}-la"),
            _qual("la"),
        ]),
        ("en", "English", [
            _qual(f"{stem}.en"),
            _qual(f"{stem}_en"),
            _qual(f"{stem}-en"),
            _qual("en"),
        ]),
        ("it", "Italiano", [
            _qual(f"{stem}.it"),
            _qual(f"{stem}_it"),
            _qual(f"{stem}-it"),
            _qual("it"),
        ]),
        ("de", "Deutsch", [
            _qual(f"{stem}.de"),
            _qual(f"{stem}_de"),
            _qual(f"{stem}-de"),
            _qual("de"),
        ]),
        ("commentary", "Commentary", [
            _qual(f"{stem}.commentary"),
            _qual(f"{stem}_commentary"),
            _qual(f"{stem}-commentary"),
            _qual("commentary"),
        ]),
        ("summary", "Summary", [
            _qual(f"{stem}.summary"),
            _qual(f"{stem}_summary"),
            _qual(f"{stem}-summary"),
            _qual("summary"),
        ]),
        ("notes", "Notes", [
            _qual(f"{stem}.notes"),
            _qual(f"{stem}_notes"),
            _qual(f"{stem}-notes"),
            _qual(f"translation-notes-{stem}"),
            _qual("notes"),
        ]),
        ("folio", "Folio", [
            _qual(f"{stem}.folio"),
            _qual(f"{stem}_folio"),
            _qual(f"{stem}-folio"),
            _qual("folio"),
        ]),
    ]

    tracks: List[Dict[str, Any]] = []
    seen_docs: Set[str] = set()

    for track_key, default_label, doc_candidates in candidate_specs:
        for cand in doc_candidates:
            if cand in found_docs and cand not in seen_docs:
                seen_docs.add(cand)
                tracks.append(
                    {
                        "key": track_key,
                        "label": default_label,
                        "docname": cand,
                        "active": cand == pagename,
                    }
                )
                break

    # If only 1 track (e.g., just `index` with no companion tracks), do not render a multi-track switcher
    if len(tracks) < 2:
        return []

    # If `index` is in tracks alongside language tracks (like Pacioli cap_04/index + _en/_it/_de/_notes),
    # keep it labeled "Overview" or "Proposition" appropriately.
    return tracks


def resolve_book_context(
    env: Any,
    pagename: str,
    doctree: Optional[nodes.document] = None,
) -> Dict[str, Any]:
    """Resolve book subtree inheritance and companion tracks for `pagename`."""
    master_doc = getattr(getattr(env, "config", None), "master_doc", "index")
    parts = pagename.split("/")

    # Build ordered list of ancestor index docnames from root to current directory
    ancestor_docnames: List[str] = [master_doc]
    for i in range(1, len(parts)):
        prefix = "/".join(parts[:i])
        for cand in (f"{prefix}/index", prefix):
            if cand not in ancestor_docnames:
                ancestor_docnames.append(cand)
    if pagename not in ancestor_docnames:
        ancestor_docnames.append(pagename)

    book_root: Optional[str] = None
    book_meta: Dict[str, Any] = {}
    is_book_page = False

    for anc in ancestor_docnames:
        meta = _get_doc_metadata(env, anc)
        if meta.get("layout") == "book" or "book_title" in meta:
            is_book_page = True
            if book_root is None:
                book_root = anc
            # Merge book-level configuration down the hierarchy
            for k in ("book_title", "book_subtitle", "book_theme", "author", "title", "subtitle"):
                if k in meta and meta[k]:
                    book_meta[k] = meta[k]

    if not is_book_page:
        return {"is_book_page": False}

    # If the page itself declared :layout: book without an ancestor book_root having book_title,
    # check master_doc or parent index for book title/author fallback
    if book_root == pagename and len(parts) > 1:
        parent_idx = f"{'/'.join(parts[:-1])}/index"
        parent_meta = _get_doc_metadata(env, parent_idx)
        root_meta = _get_doc_metadata(env, master_doc)
        if parent_meta.get("book_title") or parent_meta.get("layout") == "book":
            book_root = parent_idx
            for k, v in parent_meta.items():
                book_meta.setdefault(k, v)
        elif root_meta.get("title") or root_meta.get("book_title"):
            book_root = master_doc
            for k, v in root_meta.items():
                book_meta.setdefault(k, v)

    if not book_root:
        book_root = master_doc

    root_doc_meta = _get_doc_metadata(env, book_root)
    book_title = (
        book_meta.get("book_title")
        or root_doc_meta.get("book_title")
        or root_doc_meta.get("title")
        or _get_doc_title(env, book_root, root_doc_meta)
    )
    book_subtitle = (
        book_meta.get("book_subtitle")
        or root_doc_meta.get("book_subtitle")
        or root_doc_meta.get("author")
        or book_meta.get("author")
        or ""
    )
    book_theme = book_meta.get("book_theme") or root_doc_meta.get("book_theme") or "classical-serif"

    # Page-specific metadata (with fallback to unit index.rst in the same directory)
    page_meta = _get_doc_metadata(env, pagename)
    doc_dir = os.path.dirname(pagename)
    unit_index_meta: Dict[str, Any] = {}
    if doc_dir and os.path.basename(pagename) != "index":
        unit_index_meta = _get_doc_metadata(env, f"{doc_dir}/index")

    folio = str(page_meta.get("folio") or unit_index_meta.get("folio") or "").strip()
    page_num = str(page_meta.get("page") or unit_index_meta.get("page") or "").strip()
    canonical_id = str(
        page_meta.get("canonical_id") or unit_index_meta.get("canonical_id") or ""
    ).strip()
    book_num = str(page_meta.get("book") or unit_index_meta.get("book") or "").strip()
    volume = str(page_meta.get("volume") or unit_index_meta.get("volume") or "").strip()

    tracks = detect_companion_tracks(env, pagename)

    if doctree is not None and nodes is not None and hasattr(doctree, "traverse"):
        for node in list(doctree.traverse(nodes.container)):
            if "track-nav" in node.get("classes", []) and node.parent is not None:
                node.parent.remove(node)

    return {
        "is_book_page": True,
        "book_root": book_root,
        "book_title": book_title,
        "book_subtitle": book_subtitle,
        "book_theme": book_theme,
        "folio": folio,
        "page": page_num,
        "canonical_id": canonical_id,
        "book": book_num,
        "volume": volume,
        "book_tracks": tracks,
    }


def setup_book_page_context(
    app: Any,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: Optional[nodes.document],
) -> Optional[str]:
    """Sphinx `html-page-context` hook to inject Book Codex context and select `book_layout.html`."""
    book_ctx = resolve_book_context(app.env, pagename, doctree=doctree)
    context.update(book_ctx)
    if book_ctx.get("is_book_page") and templatename == "page.html":
        return "book_layout.html"
    return None


def setup(app: Any) -> Dict[str, Any]:
    """Register the book subtree inheritance hook with Sphinx."""
    app.connect("html-page-context", setup_book_page_context)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
