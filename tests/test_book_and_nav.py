"""Unit tests for companion track detection, EPUB track bar labels, and :nav_title: navigation."""

from __future__ import annotations

from types import SimpleNamespace

from docutils import nodes

from photon_platform.publish.book import (
    _build_epub_tracks_bar_html,
    detect_companion_tracks,
)
from photon_platform.publish.directives.collection import build_nav_links


def test_detect_greek_and_french_companion_tracks() -> None:
    """Greek (-el) and French (-fr) tracks resolve with English labels in companion switcher."""
    env = SimpleNamespace(
        found_docs={
            "loci_mathematici/unit-01/unit-01-en",
            "loci_mathematici/unit-01/unit-01-el",
            "loci_mathematici/unit-01/unit-01-summary",
            "loci_mathematici/unit-01/unit-01-notes",
            "science_and_hypothesis/part-1/part-1-en",
            "science_and_hypothesis/part-1/part-1-fr",
            "science_and_hypothesis/part-1/part-1-summary",
        }
    )

    gr_tracks = detect_companion_tracks(env, "loci_mathematici/unit-01/unit-01-el")
    assert [(t["key"], t["label"], t["active"]) for t in gr_tracks] == [
        ("en", "English", False),
        ("el", "Greek", True),
        ("summary", "Summary", False),
        ("notes", "Notes", False),
    ]

    fr_tracks = detect_companion_tracks(env, "science_and_hypothesis/part-1/part-1-fr")
    assert [(t["key"], t["label"], t["active"]) for t in fr_tracks] == [
        ("en", "English", False),
        ("fr", "French", True),
        ("summary", "Summary", False),
    ]


def test_epub_track_bar_english_defaults_and_hoenen_override() -> None:
    """EPUB track bar defaults to English ('Contents', 'People') and honors Hoenen overrides."""
    builder = SimpleNamespace(get_relative_uri=lambda _src, dst: f"../{dst}.xhtml")
    env = SimpleNamespace(
        found_docs={
            "grundlagen/index",
            "grundlagen/ch1-en",
            "grundlagen/persons",
            "grundlagen/bibliography",
        },
        metadata={"grundlagen/index": {}},
    )
    app = SimpleNamespace(builder=builder, env=env, config=SimpleNamespace(master_doc="index"))
    html_default = _build_epub_tracks_bar_html(
        app,
        "grundlagen/ch1-en",
        {"book_root": "grundlagen/index", "book_tracks": []},
    )
    assert ">Contents<" in html_default
    assert ">People<" in html_default
    assert "Conspectus" not in html_default

    env.metadata["grundlagen/index"] = {
        "toc_label": "Conspectus",
        "persons_label": "Index Nominum",
    }
    html_hoenen = _build_epub_tracks_bar_html(
        app,
        "grundlagen/ch1-en",
        {"book_root": "grundlagen/index", "book_tracks": []},
    )
    assert ">Conspectus<" in html_hoenen
    assert ">Index Nominum<" in html_hoenen


def test_nav_title_override_and_deterministic_sorting() -> None:
    """:nav_title: overrides full document H1 in header_nav_list while preserving sort order."""
    env = SimpleNamespace(
        found_docs={"book/index", "persons", "mission/index"},
        metadata={
            "book/index": {
                "navigation": "header",
                "order": "1",
                "nav_title": "Foundations of Geometry",
            },
            "persons": {"navigation": "header", "order": "5", "nav_title": "People"},
            "mission/index": {"navigation": "header", "order": "10"},
        },
        titles={
            "book/index": nodes.title(text="GRUNDLAGEN DER GEOMETRIE — FULL TREATISE TITLE"),
            "persons": nodes.title(text="Biographical Register of Geometers"),
            "mission/index": nodes.title(text="Mission"),
        },
    )
    app = SimpleNamespace(env=env)
    context: dict = {"meta": {}}
    build_nav_links(app, "index", "page.html", context, None)
    assert [(item["docname"], item["title"]) for item in context["header_nav_list"]] == [
        ("book/index", "Foundations of Geometry"),
        ("persons", "People"),
        ("mission/index", "Mission"),
    ]


def test_book_title_page_tracks_no_bleed_and_page_labels() -> None:
    """Book Title Page :tracks: stay on index/title-la and page_meta overrides utility labels."""
    builder = SimpleNamespace(get_relative_uri=lambda _src, dst: f"../{dst}.xhtml")
    env = SimpleNamespace(
        found_docs={
            "treatise/index",
            "treatise/title-la",
            "treatise/bibliography",
            "treatise/persons",
        },
        metadata={
            "treatise/index": {
                "type": "book",
                "tracks": "English: index | Latin: title-la",
            },
            "treatise/title-la": {
                "type": "book_title",
                "tracks": "English: index | Latin: title-la",
                "toc_label": "Conspectus",
                "persons_label": "Index Nominum",
            },
            "treatise/bibliography": {},
        },
    )
    assert [(t["label"], t["active"]) for t in detect_companion_tracks(env, "treatise/index")] == [
        ("English", True),
        ("Latin", False),
    ]
    assert detect_companion_tracks(env, "treatise/bibliography") == []

    app = SimpleNamespace(builder=builder, env=env, config=SimpleNamespace(master_doc="index"))
    html_la = _build_epub_tracks_bar_html(
        app,
        "treatise/title-la",
        {"book_root": "treatise/index", "book_tracks": []},
    )
    assert ">Conspectus<" in html_la
    assert ">Index Nominum<" in html_la


def test_etc_multitrack_and_mathjax_unification() -> None:
    from pathlib import Path

    from photon_platform.publish.book import _update_book_prev_next

    found = {
        "centers/c-00001-00019/x-00001/index",
        "centers/c-00001-00019/x-00001/lines",
        "centers/c-00001-00019/x-00001/relations",
        "centers/c-00001-00019/x-00001/notes",
        "centers/c-00001-00019/x-00001/code",
        "centers/c-00001-00019/x-00002/index",
        "centers/c-00001-00019/x-00002/lines",
        "centers/c-00001-00019/x-00002/relations",
        "centers/c-00001-00019/x-00002/notes",
        "centers/c-00001-00019/x-00002/code",
    }
    env = SimpleNamespace(
        found_docs=found,
        metadata={
            "centers/c-00001-00019/x-00001/index": {
                "tracks": "Overview: index | Lines: lines | Relations: relations | Notes: notes | Code: code"
            },
            "centers/c-00001-00019/x-00002/index": {
                "tracks": "Overview: index | Lines: lines | Relations: relations | Notes: notes | Code: code"
            },
        },
        titles={doc: SimpleNamespace(astext=lambda d=doc: d) for doc in found},
    )
    tracks = detect_companion_tracks(env, "centers/c-00001-00019/x-00001/lines")
    assert [(t["key"], t["label"], t["active"]) for t in tracks] == [
        ("index", "Overview", False),
        ("lines", "Lines", True),
        ("relations", "Relations", False),
        ("notes", "Notes", False),
        ("code", "Code", False),
    ]

    # Verify track-preserving Prev/Next steps from X_1/lines -> X_2/lines
    relations = {
        "centers/c-00001-00019/x-00001/index": [None, None, "centers/c-00001-00019/x-00001/lines"],
        "centers/c-00001-00019/x-00001/lines": [
            "centers/c-00001-00019/x-00001/index",
            "centers/c-00001-00019/x-00001/index",
            "centers/c-00001-00019/x-00002/index",
        ],
        "centers/c-00001-00019/x-00002/index": [
            None,
            "centers/c-00001-00019/x-00001/lines",
            "centers/c-00001-00019/x-00002/lines",
        ],
    }
    builder = SimpleNamespace(
        relations=relations,
        get_relative_uri=lambda from_doc, to_doc: f"{to_doc}.html",
    )
    app = SimpleNamespace(builder=builder, env=env)
    ctx = {"prev": None, "next": None}
    _update_book_prev_next(app, "centers/c-00001-00019/x-00001/lines", ctx)
    assert ctx["next"]["link"].endswith("x-00002/lines.html")

    # Verify MathJax v4 standardization (no KaTeX in foundation layout or folio_review base)
    pkg_root = Path(__file__).resolve().parents[1] / "src" / "photon_platform" / "publish"
    layout_html = (pkg_root / "themes" / "foundation" / "layout.html").read_text(encoding="utf-8")
    assert "katex" not in layout_html.lower()
    folio_base = (pkg_root / "folio_review" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "katex" not in folio_base.lower()
    assert "mathjax@4/tex-mml-chtml.js" in folio_base
    card_html = (pkg_root / "themes" / "foundation" / "components" / "card.html").read_text(encoding="utf-8")
    assert 'loading="lazy"' in card_html


