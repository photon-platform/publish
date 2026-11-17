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
    (r"^(.+)[._-]pseudocode$", "pseudocode", "Pseudocode"),
    (r"^(.+)[._-]video$", "video", "Video"),
    (r"^(.+)[._-]code$", "code", "Code"),
    (r"^(.+)[._-]heath$", "heath", "Heath"),
    (r"^(.+)[._-]en$", "en", "English"),
    (r"^(.+)[._-]el$", "el", "Greek"),
    (r"^(.+)[._-]grc$", "el", "Greek"),
    (r"^(.+)[._-]la$", "la", "Latin"),
    (r"^(.+)[._-]de$", "de", "German"),
    (r"^(.+)[._-]fr$", "fr", "French"),
    (r"^(.+)[._-]it$", "it", "Italian"),
    (r"^(.+)[._-]da$", "da", "Danish"),
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
    if basename in {
        "index",
        "proposition",
        "pseudocode",
        "video",
        "code",
        "heath",
        "commentary",
        "summary",
        "notes",
        "folio",
        "en",
        "el",
        "grc",
        "la",
        "de",
        "fr",
        "it",
        "da",
    }:
        return os.path.basename(doc_dir) if doc_dir else basename
    return basename


def detect_companion_tracks(env: Any, pagename: str) -> List[Dict[str, Any]]:
    """Detect companion tracks for ``pagename`` in ``env.found_docs``.

    Supports:

    - Elements 2.0 tracks: ``index`` (Pseudocode), ``video`` (Video), ``code`` (Code), ``heath`` (Heath)
    - Euclid tracks: ``index`` / ``proposition``, ``commentary``, ``notes``, ``folio``
      or ``<pagename>.commentary``, ``<pagename>.notes``
    - Multilingual tracks: ``<stem>_en`` / ``-en``, ``-el`` (Greek), ``-la`` (Latin),
      ``-de`` (German), ``-fr`` (French), ``-it`` (Italian), ``-da`` (Danish),
      ``-summary``, ``-notes``
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

    # Explicit frontmatter tracks declaration: e.g. `:tracks: English: index | Latin: la | Summary: summary | Notes: notes`
    page_meta = _get_doc_metadata(env, pagename)
    raw_tracks = page_meta.get("tracks")
    if not raw_tracks and basename != "index" and doc_dir:
        parent_idx_meta = _get_doc_metadata(env, f"{doc_dir}/index")
        if parent_idx_meta.get("type") not in ("book", "book_title") and "book_title" not in parent_idx_meta:
            raw_tracks = parent_idx_meta.get("tracks")
    if raw_tracks and isinstance(raw_tracks, str):
        parsed_tracks: List[Dict[str, Any]] = []
        for segment in raw_tracks.split("|"):
            if ":" in segment:
                lbl, doc_target = segment.split(":", 1)
                clean_lbl = lbl.strip()
                clean_target = doc_target.strip()
                target_doc = _qual(clean_target) if not clean_target.startswith("/") else clean_target.lstrip("/")
                if target_doc in found_docs:
                    parsed_tracks.append(
                        {
                            "key": clean_target,
                            "label": clean_lbl,
                            "docname": target_doc,
                            "active": target_doc == pagename,
                        }
                    )
        if len(parsed_tracks) > 1:
            return parsed_tracks

    # Determine if bare `<stem>` is the Latin/original primary track (e.g. Hoenen `caput-1/caput-1`)
    has_hyphen_or_under_en = _qual(f"{stem}-en") in found_docs or _qual(f"{stem}_en") in found_docs
    has_elements_siblings = (
        any(_qual(name) in found_docs for name in ("heath", f"{stem}.heath"))
        or os.path.basename(doc_dir).startswith("G.")
    )
    has_proposition_siblings = any(
        _qual(name) in found_docs
        for name in ("commentary", f"{stem}.commentary", f"{stem}_commentary", f"{stem}-commentary")
    )

    if has_elements_siblings:
        index_label = "Pseudocode"
    elif has_proposition_siblings:
        index_label = "Proposition"
    else:
        index_label = "Overview"

    is_unit_dir = not doc_dir or stem == os.path.basename(doc_dir)

    def _cands(stemmed: List[str], bare: List[str]) -> List[str]:
        return stemmed + (bare if is_unit_dir else [])

    candidate_specs: List[Tuple[str, str, List[str]]] = [
        (
            "proposition",
            index_label,
            _cands(
                [_qual(f"{stem}.proposition")],
                [_qual("index"), _qual("pseudocode"), _qual("proposition")],
            ),
        ),
        (
            "video",
            "Video",
            _cands(
                [_qual(f"{stem}.video"), _qual(f"{stem}_video"), _qual(f"{stem}-video")],
                [_qual("video")],
            ),
        ),
        (
            "code",
            "Code",
            _cands(
                [_qual(f"{stem}.code"), _qual(f"{stem}_code"), _qual(f"{stem}-code")],
                [_qual("code")],
            ),
        ),
        (
            "heath",
            "Heath",
            _cands(
                [_qual(f"{stem}.heath"), _qual(f"{stem}_heath"), _qual(f"{stem}-heath")],
                [_qual("heath")],
            ),
        ),
        (
            "la",
            "Latin",
            [_qual(stem)] if has_hyphen_or_under_en and stem != "index" else [],
        ),
        (
            "en",
            "English",
            _cands(
                [_qual(f"{stem}.en"), _qual(f"{stem}_en"), _qual(f"{stem}-en")],
                [_qual("en")],
            ),
        ),
        (
            "el",
            "Greek",
            _cands(
                [
                    _qual(f"{stem}.el"),
                    _qual(f"{stem}_el"),
                    _qual(f"{stem}-el"),
                    _qual(f"{stem}.grc"),
                    _qual(f"{stem}_grc"),
                    _qual(f"{stem}-grc"),
                ],
                [_qual("el"), _qual("grc")],
            ),
        ),
        (
            "la",
            "Latin",
            _cands(
                [_qual(f"{stem}.la"), _qual(f"{stem}_la"), _qual(f"{stem}-la")],
                [_qual("la")],
            ),
        ),
        (
            "de",
            "German",
            _cands(
                [_qual(f"{stem}.de"), _qual(f"{stem}_de"), _qual(f"{stem}-de")],
                [_qual("de")],
            ),
        ),
        (
            "fr",
            "French",
            _cands(
                [_qual(f"{stem}.fr"), _qual(f"{stem}_fr"), _qual(f"{stem}-fr")],
                [_qual("fr")],
            ),
        ),
        (
            "it",
            "Italian",
            _cands(
                [_qual(f"{stem}.it"), _qual(f"{stem}_it"), _qual(f"{stem}-it")],
                [_qual("it")],
            ),
        ),
        (
            "da",
            "Danish",
            _cands(
                [_qual(f"{stem}.da"), _qual(f"{stem}_da"), _qual(f"{stem}-da")],
                [_qual("da")],
            ),
        ),
        (
            "commentary",
            "Commentary",
            _cands(
                [
                    _qual(f"{stem}.commentary"),
                    _qual(f"{stem}_commentary"),
                    _qual(f"{stem}-commentary"),
                ],
                [_qual("commentary")],
            ),
        ),
        (
            "summary",
            "Summary",
            _cands(
                [_qual(f"{stem}.summary"), _qual(f"{stem}_summary"), _qual(f"{stem}-summary")],
                [_qual("summary")],
            ),
        ),
        (
            "notes",
            "Notes",
            _cands(
                [
                    _qual(f"{stem}.notes"),
                    _qual(f"{stem}_notes"),
                    _qual(f"{stem}-notes"),
                    _qual(f"translation-notes-{stem}"),
                ],
                [_qual("notes")],
            ),
        ),
        (
            "folio",
            "Folio",
            _cands(
                [_qual(f"{stem}.folio"), _qual(f"{stem}_folio"), _qual(f"{stem}-folio")],
                [_qual("folio")],
            ),
        ),
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


_CONTAINER_PREFIX_WORDS = (
    "volume ",
    "vol. ",
    "book ",
    "liber ",
    "part ",
    "pars ",
    "tractatus ",
    "caput ",
    "chapter ",
    "ch. ",
    "prologue ",
    "section ",
    "sec. ",
    "teil ",
    "abschnitt ",
)

_CONTAINER_TYPES = {
    "volume",
    "book",
    "liber",
    "part",
    "pars",
    "tractatus",
    "caput",
    "chapter",
    "prologue",
    "section",
}


def _shorten_container_crumb_label(raw_title: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """Shorten container headings ('Volume I: Intro...', 'Book I — Triangles') for breadcrumbs."""
    if meta:
        explicit = str(meta.get("breadcrumb_title") or meta.get("nav_title") or "").strip()
        if explicit:
            return explicit.rstrip(".")
    label = (raw_title or "").strip().rstrip(".")
    low = label.lower()
    mtype = str((meta or {}).get("type") or "").strip().lower()
    if mtype in _CONTAINER_TYPES or low.startswith(_CONTAINER_PREFIX_WORDS):
        label = re.split(r"\s*[:\u2014\u2013]\s*", label, maxsplit=1)[0].strip()
    return label


def _shorten_book_home_label(book_title: str) -> str:
    """Produce a concise Book Home label for inner-page breadcrumbs."""
    cleaned = (book_title or "").strip().rstrip(".")
    if not cleaned:
        return ""
    if "euclid" in cleaned.lower() and "elements" in cleaned.lower():
        return "Elements"
    short = re.split(r"\s*[:\u2014\u2013]\s*", cleaned, maxsplit=1)[0].strip()
    return short


def _shorten_leaf_crumb_label(raw_title: str) -> str:
    """Produce a clean, concise terminal breadcrumb label for a leaf unit or section page."""
    cleaned = re.sub(r"<[^>]+>", "", (raw_title or "")).strip().rstrip(".")
    if not cleaned:
        return ""
    short = re.split(r"\s*[:\u2014\u2013]\s*", cleaned, maxsplit=1)[0].strip()
    if len(short) > 48:
        short = short[:45].rsplit(" ", 1)[0] + "…"
    return short


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

    # Promote leading folio_node (before first body paragraph) to masthead & mark in_masthead=True
    if doctree is not None and nodes is not None and hasattr(doctree, "findall"):
        first_para = next(iter(doctree.findall(nodes.paragraph)), None)
        for el in doctree.findall(nodes.Element):
            if el.__class__.__name__ == "folio_node":
                # Check if this folio_node precedes the first prose paragraph (or matches masthead folio)
                el_fid = str(el.get("folio_id") or "").strip()
                el_pg = str(el.get("page") or "").strip()
                is_leading = False
                if first_para is None:
                    is_leading = True
                else:
                    # Walk document order to check if el comes before first_para
                    for walk_el in doctree.findall(nodes.Element):
                        if walk_el is el:
                            is_leading = True
                            break
                        if walk_el is first_para:
                            is_leading = False
                            break
                if is_leading and not folio and el_fid:
                    folio = el_fid
                    if not page_num and el_pg:
                        page_num = el_pg
                    el["in_masthead"] = True
                elif folio and el_fid == folio:
                    el["in_masthead"] = True
                break

    canonical_id = str(
        page_meta.get("canonical_id") or unit_index_meta.get("canonical_id") or ""
    ).strip()
    original_id = str(
        page_meta.get("original_id") or unit_index_meta.get("original_id") or ""
    ).strip()
    book_num = str(page_meta.get("book") or unit_index_meta.get("book") or "").strip()
    volume = str(page_meta.get("volume") or unit_index_meta.get("volume") or "").strip()

    tracks = detect_companion_tracks(env, pagename)

    # Build hierarchical breadcrumbs between book_root and the current unit
    found_docs: Set[str] = set(getattr(env, "found_docs", set()))
    unit_doc = pagename
    if (
        doc_dir
        and os.path.basename(pagename) != "index"
        and _extract_unit_stem(os.path.basename(pagename), doc_dir) == os.path.basename(doc_dir)
    ):
        cand_unit_idx = f"{doc_dir}/index"
        if (
            _is_auxiliary_track_doc(env, pagename)
            or any(tr.get("docname") == cand_unit_idx for tr in tracks)
        ) and (not found_docs or cand_unit_idx in found_docs):
            unit_doc = cand_unit_idx

    crumb_docnames: List[str] = []
    seen_crumb_dirs: Set[str] = set()
    after_root = False
    for anc in ancestor_docnames:
        if anc == book_root:
            after_root = True
            continue
        if not after_root:
            continue
        if anc == unit_doc or anc == pagename:
            break
        exists = (
            (anc in found_docs)
            if found_docs
            else (bool(_get_doc_metadata(env, anc)) or anc in getattr(env, "titles", {}))
        )
        if not exists:
            continue
        anc_dir = os.path.dirname(anc) if os.path.basename(anc) == "index" else anc
        if anc_dir in seen_crumb_dirs:
            continue
        seen_crumb_dirs.add(anc_dir)
        crumb_docnames.append(anc)

    book_breadcrumbs: List[Dict[str, str]] = []
    prev_crumb_label = ""
    for anc in crumb_docnames:
        anc_meta = _get_doc_metadata(env, anc)
        raw_label = _shorten_container_crumb_label(
            _get_doc_title(env, anc, anc_meta), anc_meta
        )
        if prev_crumb_label and raw_label.lower().startswith(prev_crumb_label.lower()):
            trimmed = re.sub(
                r"^[.:\-\u2013\u2014\s]+", "", raw_label[len(prev_crumb_label) :]
            ).strip()
            if trimmed:
                raw_label = trimmed
        prev_crumb_label = raw_label
        book_breadcrumbs.append({"docname": anc, "title": raw_label})

    if doctree is not None and nodes is not None and hasattr(doctree, "traverse"):
        for node in list(doctree.traverse(nodes.container)):
            if "track-nav" in node.get("classes", []) and node.parent is not None:
                node.parent.remove(node)

    from .folio_links import resolve_folio_url

    folio_url = resolve_folio_url(env, pagename, folio) if folio else None
    book_short_title = (
        str(root_doc_meta.get("breadcrumb_title") or root_doc_meta.get("nav_title") or "").strip()
        or _shorten_book_home_label(str(book_title or ""))
    )

    return {
        "is_book_page": True,
        "book_root": book_root,
        "book_title": book_title,
        "book_short_title": book_short_title,
        "book_subtitle": book_subtitle,
        "book_theme": book_theme,
        "folio": folio,
        "folio_url": folio_url or "",
        "page": page_num,
        "canonical_id": canonical_id,
        "original_id": original_id,
        "book": book_num,
        "volume": volume,
        "book_tracks": tracks,
        "book_breadcrumbs": book_breadcrumbs,
    }


def _render_mathml_fallback(latex_str: str, inline: bool = True) -> str:
    """Convert LaTeX math string to MathML for EPUB 3, with clean HTML fallback."""
    cleaned = (latex_str or "").strip()
    if not cleaned:
        return ""
    try:
        from docutils.utils.math.latex2mathml import tex2mathml

        # Normalize \text{...} with endash/spaces if needed
        return tex2mathml(cleaned, inline=inline)
    except Exception:
        import html as _html

        # Clean fallback if tex2mathml encounters an unsupported macro
        fallback = (
            cleaned.replace(r"\times", "×")
            .replace(r"\dots", "…")
            .replace(r"\pi", "π")
            .replace(r"\alpha", "α")
            .replace(r"\beta", "β")
            .replace(r"\gamma", "γ")
            .replace(r"\propto", "∝")
            .replace(r"\leftrightarrow", "↔")
            .replace(r"\to", "→")
            .replace(r"\neq", "≠")
            .replace(r"^\circ", "°")
            .replace(r"\quad", " ")
        )
        fallback = re.sub(r"\\text\{([^}]*)\}", r"\1", fallback)
        tag = "span" if inline else "div"
        return f'<{tag} class="math-fallback"><em>{_html.escape(fallback)}</em></{tag}>'


def filter_epub_book_sources(app: Any, docname: str, source: List[str]) -> None:
    """Clean up non-book editorial references in source RST when building an EPUB."""
    if getattr(getattr(app, "builder", None), "name", "") != "epub" or not source:
        return

    text = source[0]

    # Strip excluded project/editorial pages from the book index toctree and body,
    # and unhide toctrees so Epub3Builder populates nav.xhtml and toc.ncx.
    if docname == "index" or docname.endswith("/index"):
        text = re.sub(
            r"^\* :ref:`[^`]*<(?:agent-chronicle|scan-inventory)>`\s*$\n?",
            "",
            text,
            flags=re.M,
        )
        text = re.sub(r"^[ \t]+(?:agent-chronicle|scan-inventory)\s*$\n?", "", text, flags=re.M)
        text = re.sub(r"^[ \t]+:hidden:\s*$\n?", "", text, flags=re.M)
        text = text.replace(
            "Apparatus & Editorial Documentation\n-----------------------------------",
            "Critical Apparatus\n------------------",
        )
        text = text.replace(":caption: Apparatus & Editorial", ":caption: Critical Apparatus")

    # Strip benchmark 3.1 draft notes from translation notes
    if "translation-notes-" in docname:
        text = re.sub(
            r"\.\. note::\n+\s+For reference and comparative benchmarking[^\n]*\n+",
            "",
            text,
        )

    # Fix empty bold marker and trailing transitions in apparatus files
    text = text.replace("* **** (", "* **op.** (")
    text = re.sub(r"\n+----+\s*$", "\n", text)

    source[0] = text


def resolve_book_doctree(app: Any, doctree: Any, fromdocname: str) -> None:
    """Consolidate footnote targets and apply EPUB 3 doctree transformations."""
    if nodes is None or doctree is None:
        return

    # 1. Consolidate standalone target nodes immediately preceding footnote nodes
    # so Docutils groups all chapter footnotes into a single <aside class="footnote-list">
    for fn_node in list(doctree.traverse(nodes.footnote)):
        parent = fn_node.parent
        if parent is None:
            continue
        idx = parent.index(fn_node)
        if idx > 0:
            prev = parent[idx - 1]
            if isinstance(prev, nodes.target) and not prev.children and prev.get("ids"):
                for tid in prev["ids"]:
                    if tid not in fn_node["ids"]:
                        fn_node["ids"].append(tid)
                parent.remove(prev)

    # Promote leading folio_node (preceding first body paragraph) to masthead & mark in_masthead=True
    env = getattr(app, "env", None)
    if env is not None and hasattr(doctree, "findall"):
        doc_meta = env.metadata.setdefault(fromdocname, {}) if hasattr(env, "metadata") else {}
        fm_folio = str(doc_meta.get("folio") or "").strip()
        first_para = next(iter(doctree.findall(nodes.paragraph)), None)
        for el in doctree.findall(nodes.Element):
            if el.__class__.__name__ == "folio_node":
                el_fid = str(el.get("folio_id") or "").strip()
                el_pg = str(el.get("page") or "").strip()
                is_leading = first_para is None
                if not is_leading:
                    for walk_el in doctree.findall(nodes.Element):
                        if walk_el is el:
                            is_leading = True
                            break
                        if walk_el is first_para:
                            break
                if is_leading and not fm_folio and el_fid:
                    doc_meta["folio"] = el_fid
                    if el_pg and not doc_meta.get("page"):
                        doc_meta["page"] = el_pg
                    el["in_masthead"] = True
                elif fm_folio and el_fid == fm_folio:
                    el["in_masthead"] = True
                break

    if getattr(getattr(app, "builder", None), "name", "") != "epub":
        return

    # 2. Rewrite relative .html concordance back-links to .xhtml and mark internal=True
    for ref_node in list(doctree.traverse(nodes.reference)):
        refuri = ref_node.get("refuri", "")
        if refuri and not refuri.startswith(("http://", "https://", "mailto:", "ftp://", "data:")):
            if ".html" in refuri:
                ref_node["refuri"] = re.sub(r"\.html(?=#|$)", ".xhtml", refuri)
            ref_node["internal"] = True

    # 3. Convert inline and display math nodes to native EPUB 3 MathML
    if hasattr(nodes, "math"):
        for math_node in list(doctree.traverse(nodes.math)):
            if math_node.parent is not None:
                mml = _render_mathml_fallback(math_node.astext(), inline=True)
                raw_node = nodes.raw("", mml, format="html")
                math_node.parent.replace(math_node, raw_node)

    if hasattr(nodes, "math_block"):
        for mb_node in list(doctree.traverse(nodes.math_block)):
            if mb_node.parent is not None:
                mml = _render_mathml_fallback(mb_node.astext(), inline=False)
                raw_node = nodes.raw("", f'<div class="math-block">{mml}</div>\n', format="html")
                mb_node.parent.replace(mb_node, raw_node)


def resolve_epub_missing_reference(app: Any, env: Any, node: Any, contnode: Any) -> Optional[Any]:
    """Gracefully degrade excluded website references (e.g. about-*) to plain text in EPUB builds."""
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        return contnode
    return None


def _build_epub_tracks_bar_html(
    app: Any,
    pagename: str,
    book_ctx: Dict[str, Any],
) -> str:
    """Build an in-page Track & Apparatus navigation bar for EPUB 3 pages."""
    import html as _html

    builder = getattr(app, "builder", None)
    if builder is None or not hasattr(builder, "get_relative_uri"):
        return ""

    env = getattr(app, "env", None)
    found_docs: Set[str] = set(getattr(env, "found_docs", set())) if env else set()
    book_root = book_ctx.get("book_root") or getattr(app.config, "master_doc", "index")

    if pagename == book_root:
        return ""

    tracks = book_ctx.get("book_tracks", [])
    parts_html: List[str] = []

    if tracks:
        track_items: List[str] = []
        for tr in tracks:
            label = _html.escape(str(tr["label"]))
            if tr.get("active"):
                track_items.append(
                    f'<strong class="book-track-item is-active" aria-current="page">{label}</strong>'
                )
            else:
                rel_uri = _html.escape(builder.get_relative_uri(pagename, tr["docname"]), quote=True)
                track_items.append(f'<a class="book-track-item" href="{rel_uri}">{label}</a>')
        parts_html.append(' <span class="book-track-sep">&middot;</span> '.join(track_items))

    # Add Contents & Apparatus quick links (English default, metadata-overridable e.g. for Hoenen)
    book_prefix = os.path.dirname(book_root)
    def _qual_book(name: str) -> str:
        return f"{book_prefix}/{name}" if book_prefix else name

    root_meta = getattr(env, "metadata", {}).get(book_root, {}) if env else {}
    page_meta = getattr(env, "metadata", {}).get(pagename, {}) if env else {}
    toc_label = _html.escape(str(page_meta.get("toc_label") or root_meta.get("toc_label") or "Contents"))
    persons_label = _html.escape(str(page_meta.get("persons_label") or root_meta.get("persons_label") or "People"))
    bib_label = _html.escape(str(page_meta.get("bibliography_label") or root_meta.get("bibliography_label") or "Bibliography"))
    glossary_label = _html.escape(str(page_meta.get("glossary_label") or root_meta.get("glossary_label") or "Glossary"))

    util_links: List[str] = []
    if book_root in found_docs and pagename != book_root:
        toc_uri = _html.escape(builder.get_relative_uri(pagename, book_root), quote=True)
        util_links.append(f'<a class="book-track-item book-util-link" href="{toc_uri}">{toc_label}</a>')

    for app_doc, app_label in (
        ("bibliography", bib_label),
        (("people/index", "persons"), persons_label),
        ("glossary", glossary_label),
    ):
        cands = app_doc if isinstance(app_doc, tuple) else (app_doc,)
        cand = None
        for doc_opt in cands:
            q_opt = _qual_book(doc_opt)
            if q_opt in found_docs:
                cand = q_opt
                break
            if doc_opt in found_docs:
                cand = doc_opt
                break
        if cand:
            if pagename == cand:
                util_links.append(
                    f'<strong class="book-track-item is-active" aria-current="page">{app_label}</strong>'
                )
            else:
                app_uri = _html.escape(builder.get_relative_uri(pagename, cand), quote=True)
                util_links.append(f'<a class="book-track-item book-util-link" href="{app_uri}">{app_label}</a>')

    if util_links:
        parts_html.append(' <span class="book-track-sep">&middot;</span> '.join(util_links))

    if not parts_html:
        return ""

    inner = ' <span class="book-track-divider">|</span> '.join(parts_html)
    return f'<nav class="book-tracks-nav epub-tracks-nav" aria-label="Edition Tracks">{inner}</nav>\n'


def _enhance_epub_body_html(
    app: Any,
    pagename: str,
    body_html: str,
    book_ctx: Dict[str, Any],
) -> str:
    """Enhance rendered HTML body for EPUB 3 / Thorium Reader."""
    if not body_html:
        return body_html

    # 1. Add epub:type="noteref" and epub:type="footnote" for Thorium Reader pop-up footnotes
    body_html = re.sub(
        r'(<a\b[^>]*\bclass="[^"]*(?<![-\w])footnote-reference(?![-\w])[^"]*"[^>]*)(?<!epub:type="noteref")>',
        r'\1 epub:type="noteref">',
        body_html,
    )
    body_html = re.sub(
        r'(<aside\b[^>]*\bclass="[^"]*(?<![-\w])footnote(?![-\w])[^"]*"[^>]*)(?<!epub:type="footnote")>',
        r'\1 epub:type="footnote">',
        body_html,
    )

    # 2. Inject section-level [LA] <-> [EN] counterpart links on matching headings
    builder = getattr(app, "builder", None)
    tracks = book_ctx.get("book_tracks", [])
    track_map = {tr["key"]: tr["docname"] for tr in tracks}
    active_keys = [tr["key"] for tr in tracks if tr.get("active")]
    active_key = active_keys[0] if active_keys else None

    if (
        builder is not None
        and hasattr(builder, "get_relative_uri")
        and active_key in ("en", "la")
        and "en" in track_map
        and "la" in track_map
    ):
        counterpart_key = "la" if active_key == "en" else "en"
        counterpart_label = "Latin" if active_key == "en" else "English"
        counterpart_title = "Read this section in Latin" if active_key == "en" else "Read this section in English"
        counterpart_uri = builder.get_relative_uri(pagename, track_map[counterpart_key])

        std_domain = app.env.domains.get("std") if hasattr(app.env, "domains") else None
        known_labels = set()
        if std_domain is not None:
            known_labels.update(getattr(std_domain, "anonlabels", {}).keys())
            known_labels.update(getattr(std_domain, "labels", {}).keys())

        sec_pattern = re.compile(
            r'(<span id="((?:caput-\d+|appendix)-'
            + active_key
            + r'-s[^"]+)"></span>\s*<h([2-6])[^>]*>)(.*?)(</h\3>)',
            flags=re.S,
        )

        def _add_sec_counterpart(m: re.Match) -> str:
            prefix_html, sec_id, _hlevel, heading_inner, close_tag = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4),
                m.group(5),
            )
            target_sec_id = re.sub(
                rf"^((?:caput-\d+|appendix))-{active_key}-(s.+)$",
                rf"\1-{counterpart_key}-\2",
                sec_id,
            )
            if known_labels and target_sec_id not in known_labels:
                return m.group(0)
            href = f"{counterpart_uri}#{target_sec_id}"
            badge = (
                f' <a class="section-track-link" href="{href}" '
                f'title="{counterpart_title}">[{counterpart_label}]</a>'
            )
            return f"{prefix_html}{heading_inner}{badge}{close_tag}"

        body_html = sec_pattern.sub(_add_sec_counterpart, body_html)

    # 3. Inject in-page Track & Apparatus navigation bar after chapter rubric or h1
    tracks_bar = _build_epub_tracks_bar_html(app, pagename, book_ctx)
    if tracks_bar:
        if '<p class="rubric">' in body_html:
            body_html = re.sub(
                r'(<p class="rubric">.*?</p>\s*)',
                r"\1" + tracks_bar.replace("\\", "\\\\"),
                body_html,
                count=1,
                flags=re.S,
            )
        elif "</h1>" in body_html:
            body_html = body_html.replace("</h1>", "</h1>\n" + tracks_bar, 1)
        else:
            body_html = tracks_bar + body_html

    return body_html


_AUX_TRACK_BASENAMES: Set[str] = {
    "video",
    "code",
    "heath",
    "commentary",
    "summary",
    "notes",
    "folio",
    "it",
    "de",
    "la",
}

_AUX_TRACK_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"^.+[._-](?:video|code|heath|commentary|summary|notes|folio|it|de|la)$"),
    re.compile(r"^translation-notes-.+$"),
]


def _is_auxiliary_track_doc(env: Any, docname: str) -> bool:
    """Return True if `docname` is an auxiliary companion track (e.g., commentary, notes, summary, folio,
    or secondary language track) that should be skipped by sequential Prev/Next book navigation.
    """
    basename = os.path.basename(docname)
    if basename in _AUX_TRACK_BASENAMES:
        return True
    for pat in _AUX_TRACK_PATTERNS:
        if pat.match(basename):
            return True
    meta = _get_doc_metadata(env, docname)
    if str(meta.get("type", "")).strip().lower() in _AUX_TRACK_BASENAMES:
        return True
    return False


def _update_book_prev_next(app: Any, pagename: str, context: Dict[str, Any]) -> None:
    """Adjust `prev` and `next` links in `context` so sequential navigation steps through
    primary book elements and preserves the active companion track when available.
    """
    builder = getattr(app, "builder", None)
    env = getattr(app, "env", None)
    if builder is None or env is None:
        return
    relations: Optional[Dict[str, List[Optional[str]]]] = getattr(builder, "relations", None)
    if not relations or not isinstance(relations, dict):
        return

    cur_tracks = detect_companion_tracks(env, pagename)
    active_track_key: Optional[str] = None
    for tr in cur_tracks:
        if tr.get("active") or tr.get("docname") == pagename:
            active_track_key = tr.get("key")
            break

    start_doc = pagename
    if _is_auxiliary_track_doc(env, pagename):
        resolved_primary: Optional[str] = None
        for tr in cur_tracks:
            cand_doc = tr.get("docname")
            if cand_doc and cand_doc in relations and not _is_auxiliary_track_doc(env, cand_doc):
                resolved_primary = cand_doc
                break
        if resolved_primary:
            start_doc = resolved_primary
        else:
            doc_dir = os.path.dirname(pagename)
            cand_index = f"{doc_dir}/index" if doc_dir else "index"
            if cand_index in relations and not _is_auxiliary_track_doc(env, cand_index):
                start_doc = cand_index

    if start_doc not in relations:
        return

    def _find_non_aux(initial_doc: Optional[str], direction_idx: int) -> Optional[str]:
        cur = initial_doc
        visited: Set[str] = {start_doc}
        while cur and cur not in visited:
            visited.add(cur)
            if not _is_auxiliary_track_doc(env, cur):
                return cur
            rel = relations.get(cur)
            cur = rel[direction_idx] if rel and len(rel) > direction_idx else None
        return None

    cur_basename = os.path.basename(pagename)
    found_docs: Set[str] = set(getattr(env, "found_docs", set()))

    def _make_link(target_doc: Optional[str]) -> Optional[Dict[str, str]]:
        if not target_doc:
            return None
        link_doc = target_doc
        if active_track_key:
            target_tracks = detect_companion_tracks(env, target_doc)
            for tr in target_tracks:
                if tr.get("key") == active_track_key and tr.get("docname") in found_docs:
                    link_doc = tr["docname"]
                    break
        if (
            link_doc == target_doc
            and cur_basename in ("video", "code", "heath")
            and os.path.basename(target_doc) == "index"
        ):
            target_dir = os.path.dirname(target_doc)
            cand_track = f"{target_dir}/{cur_basename}" if target_dir else cur_basename
            if cand_track in found_docs:
                link_doc = cand_track
        try:
            link = builder.get_relative_uri(pagename, link_doc)
        except Exception:
            return None
        titles = getattr(env, "titles", {})
        title_str = ""
        if target_doc in titles and titles[target_doc] is not None and hasattr(builder, "render_partial"):
            try:
                title_str = builder.render_partial(titles[target_doc]).get("title", "")
            except Exception:
                title_str = ""
        if not title_str:
            title_str = _get_doc_title(env, target_doc, _get_doc_metadata(env, target_doc))
        return {"link": link, "title": title_str}

    start_rel = relations[start_doc]
    prev_doc = _find_non_aux(start_rel[1] if len(start_rel) > 1 else None, 1)
    next_doc = _find_non_aux(start_rel[2] if len(start_rel) > 2 else None, 2)

    context["prev"] = _make_link(prev_doc)
    context["next"] = _make_link(next_doc)


def resolve_page_breadcrumbs(
    app: Any,
    env: Any,
    pagename: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Build unified section/book-anchored `page_breadcrumbs` and separate `provenance_badges` across all page types."""
    master_doc = getattr(getattr(env, "config", None), "master_doc", "index")
    if pagename == master_doc:
        return {
            "page_breadcrumbs": [],
            "provenance_badges": [],
            "section_root_doc": master_doc,
            "section_root_title": "",
        }

    found_docs: Set[str] = set(getattr(env, "found_docs", set()))
    is_book = bool(context.get("is_book_page"))
    crumbs: List[Dict[str, Any]] = []
    badges: List[Dict[str, Any]] = []
    section_root_doc = master_doc
    section_root_title = ""

    # Gather relation-based ancestor chain from Sphinx `collect_relations` (excluding master_doc)
    rel_ancestors: List[str] = []
    if hasattr(env, "collect_relations"):
        try:
            relations = env.collect_relations()
            cur_p = relations.get(pagename, [None])[0] if pagename in relations else None
            seen_rel: Set[str] = set()
            while cur_p and cur_p != master_doc and cur_p not in seen_rel:
                seen_rel.add(cur_p)
                rel_ancestors.append(cur_p)
                cur_p = relations.get(cur_p, [None])[0] if cur_p in relations else None
            rel_ancestors.reverse()
        except Exception:
            rel_ancestors = []

    if is_book:
        book_root = str(context.get("book_root") or master_doc)
        section_root_doc = book_root
        book_full_title = str(context.get("book_title") or "").strip()
        book_short = str(context.get("book_short_title") or _shorten_book_home_label(book_full_title)).strip()
        section_root_title = book_short or book_full_title

        if pagename == book_root:
            # Book Title Page itself: single plain section-root crumb (no self-link)
            crumbs.append(
                {
                    "docname": book_root,
                    "title": book_full_title or book_short,
                    "is_current": True,
                    "link_when_current": False,
                }
            )
        else:
            # 1. Book Home anchor link
            crumbs.append(
                {
                    "docname": book_root,
                    "title": book_short or book_full_title,
                    "is_current": False,
                }
            )

            # 2. Intermediate container crumbs (merging book_breadcrumbs + relation ancestors after book_root)
            existing_crumbs = list(context.get("book_breadcrumbs") or [])
            seen_dirs: Set[str] = {
                os.path.dirname(book_root) if os.path.basename(book_root) == "index" else book_root
            }
            doc_dir = os.path.dirname(pagename)
            tracks = list(context.get("book_tracks") or [])

            # Determine primary reading doc for current unit
            primary_track_doc = pagename
            if tracks:
                preferred = next(
                    (
                        t["docname"]
                        for t in tracks
                        if t.get("key") in ("proposition", "en", "la", "el", "de", "it", "fr")
                    ),
                    tracks[0]["docname"],
                )
                primary_track_doc = preferred

            unit_dir_key = (
                doc_dir
                if (
                    doc_dir
                    and (
                        os.path.basename(pagename) == "index"
                        or bool(tracks)
                        or _extract_unit_stem(os.path.basename(pagename), doc_dir) == os.path.basename(doc_dir)
                    )
                )
                else pagename
            )

            # Add relation ancestors that sit below book_root and above current unit
            merged_anc_docs: List[str] = [c["docname"] for c in existing_crumbs if c.get("docname")]
            for ranc in rel_ancestors:
                if ranc == book_root or ranc == pagename or ranc == primary_track_doc:
                    continue
                if book_root != master_doc:
                    bprefix = book_root[:-5] if book_root.endswith("/index") else f"{book_root}/"
                    if not ranc.startswith(bprefix):
                        continue
                rdir = os.path.dirname(ranc) if os.path.basename(ranc) == "index" else ranc
                if rdir == unit_dir_key:
                    continue
                if ranc not in merged_anc_docs:
                    # Insert in path-length order
                    merged_anc_docs.append(ranc)

            merged_anc_docs.sort(key=lambda d: (d.count("/"), len(d)))

            prev_label = (book_short or book_full_title).lower()
            for anc_doc in merged_anc_docs:
                anc_dir = os.path.dirname(anc_doc) if os.path.basename(anc_doc) == "index" else anc_doc
                if anc_dir in seen_dirs or anc_dir == unit_dir_key:
                    continue
                seen_dirs.add(anc_dir)
                anc_meta = _get_doc_metadata(env, anc_doc)
                lbl = _shorten_container_crumb_label(_get_doc_title(env, anc_doc, anc_meta), anc_meta)
                if prev_label and lbl.lower().startswith(prev_label):
                    trimmed = re.sub(r"^[.:\-\u2013\u2014\s]+", "", lbl[len(prev_label) :]).strip()
                    if trimmed:
                        lbl = trimmed
                prev_label = lbl.lower()
                crumbs.append({"docname": anc_doc, "title": lbl, "is_current": False})

            # 3. Terminal current unit crumb (always present; links back to primary_track_doc when on an auxiliary track)
            page_meta = _get_doc_metadata(env, pagename)
            prim_meta = _get_doc_metadata(env, primary_track_doc)
            raw_cid = str(context.get("canonical_id") or "").strip()
            clean_cid = re.sub(
                r"[._-](?:commentary|notes|summary|folio)$", "", raw_cid, flags=re.IGNORECASE
            ).strip()

            unit_label = (
                str(page_meta.get("breadcrumb_title") or prim_meta.get("breadcrumb_title") or "").strip()
                or clean_cid
                or _shorten_container_crumb_label(
                    _get_doc_title(env, primary_track_doc, prim_meta), prim_meta
                )
            )
            unit_label = _shorten_leaf_crumb_label(unit_label)
            is_companion_view = bool(tracks) and pagename != primary_track_doc
            if unit_label:
                crumbs.append(
                    {
                        "docname": primary_track_doc if is_companion_view else pagename,
                        "title": unit_label,
                        "is_current": True,
                        "link_when_current": is_companion_view,
                    }
                )
    else:
        # Non-book pages (About, People, Usage, Modules, Log, Demos, etc.)
        parts = pagename.split("/")
        anc_candidates: List[str] = []
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            for cand in (f"{prefix}/index", prefix):
                if cand != pagename and (not found_docs or cand in found_docs) and cand not in anc_candidates:
                    anc_candidates.append(cand)
        for ranc in rel_ancestors:
            if ranc != pagename and ranc not in anc_candidates:
                anc_candidates.append(ranc)
        anc_candidates.sort(key=lambda d: (d.count("/"), len(d)))

        seen_nonbook_dirs: Set[str] = set()
        for anc_doc in anc_candidates:
            anc_dir = os.path.dirname(anc_doc) if os.path.basename(anc_doc) == "index" else anc_doc
            if anc_dir in seen_nonbook_dirs:
                continue
            seen_nonbook_dirs.add(anc_dir)
            anc_meta = _get_doc_metadata(env, anc_doc)
            lbl = _shorten_container_crumb_label(_get_doc_title(env, anc_doc, anc_meta), anc_meta)
            crumbs.append({"docname": anc_doc, "title": lbl, "is_current": False})

        cur_meta = _get_doc_metadata(env, pagename)
        cur_raw = (
            str(cur_meta.get("breadcrumb_title") or cur_meta.get("nav_title") or "").strip()
            or _get_doc_title(env, pagename, cur_meta)
        )
        cur_lbl = _shorten_leaf_crumb_label(cur_raw)
        if cur_lbl:
            crumbs.append(
                {
                    "docname": pagename,
                    "title": cur_lbl,
                    "is_current": True,
                    "link_when_current": False,
                }
            )

        if crumbs:
            section_root_doc = str(crumbs[0].get("docname") or pagename)
            section_root_title = str(crumbs[0].get("title") or "")

    # Separate provenance badges (never mixed into breadcrumb `/` trail)
    canonical_id = str(context.get("canonical_id") or "").strip()
    clean_cid = re.sub(
        r"[._-](?:commentary|notes|summary|folio)$", "", canonical_id, flags=re.IGNORECASE
    ).strip()
    original_id = str(context.get("original_id") or "").strip()
    terminal_title = crumbs[-1]["title"] if crumbs else ""
    if original_id and original_id not in {canonical_id, clean_cid, terminal_title}:
        badges.append({"label": original_id, "cls": "folio-badge", "url": ""})

    folio = str(context.get("folio") or "").strip()
    page_num = str(context.get("page") or "").strip()
    folio_url = str(context.get("folio_url") or "").strip()
    if folio:
        flabel = f"Folio {folio}" + (f" | p. {page_num}" if page_num else "")
        ftitle = f"View Folio {folio}" + (f" (p. {page_num})" if page_num else "")
        badges.append({"label": flabel, "cls": "folio-badge", "url": folio_url, "title": ftitle})

    if not is_book:
        meta = context.get("meta") or _get_doc_metadata(env, pagename)
        meta_date = str((meta or {}).get("date") or "").strip()
        if meta_date and pagename.startswith("log/") and pagename != "log/index":
            badges.append({"label": meta_date, "cls": "canonical-badge", "url": ""})

    return {
        "page_breadcrumbs": crumbs,
        "provenance_badges": badges,
        "section_root_doc": section_root_doc,
        "section_root_title": section_root_title,
    }


def setup_book_page_context(
    app: Any,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: Optional[nodes.document],
) -> Optional[str]:
    """Sphinx `html-page-context` hook to inject Book Codex, breadcrumbs, and social `<head>` context."""
    book_ctx = resolve_book_context(app.env, pagename, doctree=doctree)
    context.update(book_ctx)
    if book_ctx.get("is_book_page"):
        _update_book_prev_next(app, pagename, context)
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        context["script_files"] = []
        if "body" in context and isinstance(context["body"], str):
            context["body"] = _enhance_epub_body_html(app, pagename, context["body"], book_ctx)
        return None

    crumb_ctx = resolve_page_breadcrumbs(app, app.env, pagename, context)
    context.update(crumb_ctx)

    from .social_meta import build_social_and_title_context

    social_ctx = build_social_and_title_context(app, pagename, context, doctree)
    context.update(social_ctx)

    if book_ctx.get("is_book_page") and templatename == "page.html":
        return "book_layout.html"
    return None


def setup(app: Any) -> Dict[str, Any]:
    """Register the book subtree inheritance and EPUB 3 hooks with Sphinx."""
    app.connect("source-read", filter_epub_book_sources)
    app.connect("doctree-resolved", resolve_book_doctree)
    app.connect("missing-reference", resolve_epub_missing_reference)
    app.connect("html-page-context", setup_book_page_context)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
