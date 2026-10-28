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

    # Add Conspectus & Apparatus quick links
    book_prefix = os.path.dirname(book_root)
    def _qual_book(name: str) -> str:
        return f"{book_prefix}/{name}" if book_prefix else name

    util_links: List[str] = []
    if book_root in found_docs and pagename != book_root:
        toc_uri = _html.escape(builder.get_relative_uri(pagename, book_root), quote=True)
        util_links.append(f'<a class="book-track-item book-util-link" href="{toc_uri}">Conspectus</a>')

    for app_doc, app_label in (
        ("bibliography", "Bibliography"),
        ("persons", "Persons"),
        ("glossary", "Glossary"),
    ):
        cand = _qual_book(app_doc)
        if cand not in found_docs and app_doc in found_docs:
            cand = app_doc
        if cand in found_docs:
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
        counterpart_label = "LA" if active_key == "en" else "EN"
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
    "commentary",
    "summary",
    "notes",
    "folio",
}

_AUX_TRACK_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"^.+[._-](?:commentary|summary|notes|folio)$"),
    re.compile(r"^translation-notes-.+$"),
]


def _is_auxiliary_track_doc(env: Any, docname: str) -> bool:
    """Return True if `docname` is an auxiliary companion track (e.g., commentary, notes, summary, folio)
    that should be skipped by sequential Prev/Next book navigation.
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
    primary book elements and skips auxiliary companion tracks (such as commentary or notes).
    """
    builder = getattr(app, "builder", None)
    env = getattr(app, "env", None)
    if builder is None or env is None:
        return
    relations: Optional[Dict[str, List[Optional[str]]]] = getattr(builder, "relations", None)
    if not relations or not isinstance(relations, dict):
        return

    start_doc = pagename
    if _is_auxiliary_track_doc(env, pagename):
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

    def _make_link(target_doc: Optional[str]) -> Optional[Dict[str, str]]:
        if not target_doc:
            return None
        try:
            link = builder.get_relative_uri(pagename, target_doc)
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
    if book_ctx.get("is_book_page"):
        _update_book_prev_next(app, pagename, context)
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        context["script_files"] = []
        if "body" in context and isinstance(context["body"], str):
            context["body"] = _enhance_epub_body_html(app, pagename, context["body"], book_ctx)
        return None
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
