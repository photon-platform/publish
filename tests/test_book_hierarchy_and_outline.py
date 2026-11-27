"""Tests for English-first auto-tracks, auxiliary skipping, auto companion toctree, book outline, and audit-book."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from docutils import nodes

from photon_platform.publish.book import (
    _is_auxiliary_track_doc,
    build_book_outline_tree,
    detect_companion_tracks,
    discover_book_roots,
    inject_companion_tracks_toctree,
    resolve_book_context,
)
from photon_platform.publish.book_audit import audit_repo_books


def test_folder_per_unit_bare_tracks_auto_detect_english_first() -> None:
    """Folder-per-unit `index` + bare `la`/`de`/`el`/`fr`/`it` + `summary`/`notes` auto-detects English first."""
    env = SimpleNamespace(
        found_docs={
            "grundlagen/chapter_01/sec_01/index",
            "grundlagen/chapter_01/sec_01/de",
            "grundlagen/chapter_01/sec_01/summary",
            "grundlagen/chapter_01/sec_01/notes",
        },
        metadata={
            "grundlagen/chapter_01/sec_01/index": {"layout": "book", "order": "1"},
        },
    )
    tracks = detect_companion_tracks(env, "grundlagen/chapter_01/sec_01/de")
    assert [(t["key"], t["label"], t["active"]) for t in tracks] == [
        ("en", "English", False),
        ("de", "German", True),
        ("summary", "Summary", False),
        ("notes", "Notes", False),
    ]


def test_legacy_hoenen_bare_stem_puts_english_before_latin() -> None:
    """Legacy `<stem>` (Latin) + `<stem>-en` (English) auto-detects English first, Latin second."""
    env = SimpleNamespace(
        found_docs={
            "de_noetica_geometriae/caput-1/caput-1",
            "de_noetica_geometriae/caput-1/caput-1-en",
            "de_noetica_geometriae/caput-1/caput-1-summary",
            "de_noetica_geometriae/caput-1/translation-notes-caput-1",
        },
        metadata={},
    )
    tracks = detect_companion_tracks(env, "de_noetica_geometriae/caput-1/caput-1-en")
    assert [(t["key"], t["label"], t["active"]) for t in tracks] == [
        ("en", "English", True),
        ("la", "Latin", False),
        ("summary", "Summary", False),
        ("notes", "Notes", False),
    ]
    assert _is_auxiliary_track_doc(env, "de_noetica_geometriae/caput-1/caput-1") is True
    assert _is_auxiliary_track_doc(env, "de_noetica_geometriae/caput-1/caput-1-en") is False


def test_book_title_page_auto_detects_title_lang_without_explicit_tracks() -> None:
    """Book root `index` + `title-la` auto-detects English | Latin without manual `:tracks:`."""
    env = SimpleNamespace(
        found_docs={"treatise/index", "treatise/title-la"},
        metadata={"treatise/index": {"layout": "book", "book_title": "Treatise", "type": "book"}},
    )
    tracks = detect_companion_tracks(env, "treatise/index")
    assert [(t["key"], t["label"], t["active"]) for t in tracks] == [
        ("en", "English", True),
        ("la", "Latin", False),
    ]


def test_greek_french_danish_and_title_pages_marked_auxiliary() -> None:
    """Greek (`el`/`grc`), French (`fr`), Danish (`da`), and `title-*` are skipped by Prev/Next."""
    env = SimpleNamespace(found_docs=set(), metadata={})
    for doc in (
        "book/ch1/el",
        "book/ch1/grc",
        "book/ch1/fr",
        "book/ch1/da",
        "book/ch1/ch1-el",
        "book/ch1/ch1-fr",
        "book/title-el",
        "book/title-la",
    ):
        assert _is_auxiliary_track_doc(env, doc) is True, doc


def test_outermost_book_title_not_overwritten_by_nested_subbook() -> None:
    """A sub-book accidentally declaring `:book_title:` does not clobber the parent book title."""
    env = SimpleNamespace(
        found_docs={
            "synagoge/index",
            "synagoge/book_07/index",
            "synagoge/book_07/prop_01/index",
        },
        metadata={
            "synagoge/index": {"layout": "book", "book_title": "Mathematical Collection"},
            "synagoge/book_07/index": {"layout": "book", "book_title": "Book VII"},
            "synagoge/book_07/prop_01/index": {},
        },
        titles={},
    )
    ctx = resolve_book_context(env, "synagoge/book_07/prop_01/index")
    assert ctx["book_root"] == "synagoge/index"
    assert ctx["book_title"] == "Mathematical Collection"
    assert discover_book_roots(env) == ["synagoge/index"]


def test_inject_companion_tracks_toctree(tmp_path: Path) -> None:
    """`inject_companion_tracks_toctree` appends missing bare companion tracks to book `index.rst`."""
    unit = tmp_path / "book" / "sec_01"
    unit.mkdir(parents=True)
    (tmp_path / "book" / "index.rst").write_text(":layout: book\n:book_title: Demo\n", encoding="utf-8")
    (unit / "index.rst").write_text("Section 1\n=========\n\nBody.\n", encoding="utf-8")
    (unit / "de.rst").write_text("Deutsch\n=======\n", encoding="utf-8")
    (unit / "summary.rst").write_text("Summary\n=======\n", encoding="utf-8")
    (unit / "notes.rst").write_text("Notes\n=====\n", encoding="utf-8")

    app = SimpleNamespace(env=SimpleNamespace(srcdir=str(tmp_path)))
    src = ["Section 1\n=========\n\nBody.\n"]
    inject_companion_tracks_toctree(app, "book/sec_01/index", src)
    assert ".. toctree::" in src[0]
    assert "   de\n" in src[0]
    assert "   summary\n" in src[0]
    assert "   notes\n" in src[0]


def test_build_book_outline_tree_skips_auxiliary_and_apparatus() -> None:
    """`build_book_outline_tree` produces a clean English nested tree with inline companion tracks."""
    found = {
        "book/index",
        "book/title-la",
        "book/bibliography",
        "book/ch_01/index",
        "book/ch_01/summary",
        "book/ch_01/sec_01/index",
        "book/ch_01/sec_01/la",
        "book/ch_01/sec_01/summary",
        "book/ch_01/sec_01/notes",
    }
    env = SimpleNamespace(
        found_docs=found,
        toctree_includes={
            "book/index": ["book/ch_01/index", "book/bibliography", "book/title-la"],
            "book/ch_01/index": ["book/ch_01/sec_01/index", "book/ch_01/summary"],
            "book/ch_01/sec_01/index": [
                "book/ch_01/sec_01/la",
                "book/ch_01/sec_01/summary",
                "book/ch_01/sec_01/notes",
            ],
        },
        metadata={
            "book/index": {"layout": "book", "book_title": "Demo Book", "type": "book"},
            "book/ch_01/index": {"type": "chapter", "title": "Chapter I"},
            "book/ch_01/sec_01/index": {"title": "Section 1", "canonical_id": "§ 1"},
        },
        titles={
            "book/index": nodes.title(text="Demo Book"),
            "book/ch_01/index": nodes.title(text="Chapter I"),
            "book/ch_01/sec_01/index": nodes.title(text="Section 1"),
        },
    )
    tree = build_book_outline_tree(env, "book/index")
    assert len(tree) == 1
    assert tree[0]["docname"] == "book/ch_01/index"
    assert len(tree[0]["children"]) == 1
    leaf = tree[0]["children"][0]
    assert leaf["docname"] == "book/ch_01/sec_01/index"
    assert [t["label"] for t in leaf["tracks"]] == ["English", "Latin", "Summary", "Notes"]


def test_audit_repo_books_flags_violations(tmp_path: Path) -> None:
    """`audit_repo_books` flags non-English-first tracks, legacy filenames, nested book_title, and dup apparatus."""
    docsrc = tmp_path / "docsrc"
    (docsrc / "bibliography.rst").parent.mkdir(parents=True)
    (docsrc / "bibliography.rst").write_text("Bib\n===\n", encoding="utf-8")
    book = docsrc / "treatise"
    (book / "sub").mkdir(parents=True)
    (book / "index.rst").write_text(":layout: book\n:book_title: Treatise\n", encoding="utf-8")
    (book / "bibliography.rst").write_text("Bib\n===\n", encoding="utf-8")
    (book / "sub" / "index.rst").write_text(
        ":layout: book\n:book_title: Sub\n\n.. collection::\n\n.. toctree::\n   :hidden:\n\n   u1/index\n",
        encoding="utf-8",
    )
    (book / "sub" / "prop_01-en.rst").write_text(
        ":tracks: Latin: prop_01-la | English: prop_01-en\n\nProp 1\n======\n\nParallel Reading Tracks\n-----------------------\n",
        encoding="utf-8",
    )

    rep = audit_repo_books(tmp_path)
    assert rep.book_roots == ["treatise/index"]
    assert len(rep.non_english_first_tracks) == 1
    assert "treatise/sub/prop_01-en" in rep.legacy_track_filenames
    assert "treatise/sub/index" in rep.nested_book_titles
    assert "treatise/sub/index" in rep.duplicate_collection_toctree
    assert any("bibliography.rst" in d for d in rep.duplicated_apparatus)
    assert "treatise/sub/prop_01-en" in rep.redundant_track_lists_in_body
