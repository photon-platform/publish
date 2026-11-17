"""Tests for publish v0.4.8 Scriptorium upgrades: breadcrumbs, masthead, Prev/Next, social banners, bubbling, and folio-ingest."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from docutils import nodes
from PIL import Image

from photon_platform.publish.book import resolve_book_context, resolve_page_breadcrumbs
from photon_platform.publish.directives.collection import _resolve_representative_figure
from photon_platform.publish.folio_ingest import ingest_repo_pdfs
from photon_platform.publish.social_meta import (
    BANNER_HEIGHT,
    BANNER_WIDTH,
    build_social_and_title_context,
    generate_repo_social_banners,
)


def _make_env(
    tmp_path: Path,
    found_docs: set[str],
    metadata: dict[str, dict],
    titles: dict[str, str],
    *,
    org: str = "geometor",
    repo: str = "euclid",
    site_title: str = "Euclid of Alexandria",
) -> SimpleNamespace:
    docsrc = tmp_path / "docsrc"
    docsrc.mkdir(parents=True, exist_ok=True)
    cfg = SimpleNamespace(
        master_doc="index",
        org=org,
        org_name="GEOMETOR",
        repo=repo,
        repo_name=repo,
        site_title=site_title,
        project=f"GEOMETOR • {repo}",
        html_title=f"GEOMETOR • {repo}",
        html_baseurl=f"https://{org}.github.io/{repo}",
    )
    title_nodes = {k: nodes.title(text=v) for k, v in titles.items()}
    return SimpleNamespace(
        srcdir=str(docsrc),
        config=cfg,
        found_docs=found_docs,
        metadata=metadata,
        titles=title_nodes,
        collect_relations=dict,
    )


def test_breadcrumbs_across_all_hierarchies_and_companion_tracks(tmp_path: Path) -> None:
    """Verify Home suppression, Book Home anchor, leaf unit crumb, companion track link-back, and non-book sections."""
    found_docs = {
        "index",
        "heath/index",
        "heath/volume_I/index",
        "heath/volume_I/book_i/index",
        "heath/volume_I/book_i/propositions/index",
        "heath/volume_I/book_i/propositions/01/index",
        "heath/volume_I/book_i/propositions/01/commentary",
        "de_noetica/index",
        "de_noetica/caput-1/caput-1",
        "de_noetica/caput-1/caput-1-en",
        "de_noetica/caput-1/caput-1-summary",
        "about/index",
        "about/biography",
    }
    metadata = {
        "index": {"site_title": "Euclid of Alexandria"},
        "heath/index": {
            "layout": "book",
            "book_title": "The Thirteen Books of Euclid’s Elements",
            "breadcrumb_title": "Elements",
        },
        "heath/volume_I/index": {"type": "volume"},
        "heath/volume_I/book_i/index": {"type": "book"},
        "heath/volume_I/book_i/propositions/index": {"type": "section"},
        "heath/volume_I/book_i/propositions/01/index": {
            "canonical_id": "I.1",
            "folio": "0255",
            "page": "241",
        },
        "heath/volume_I/book_i/propositions/01/commentary": {
            "canonical_id": "I.1.commentary",
        },
        "de_noetica/index": {
            "layout": "book",
            "book_title": "De Noetica Geometriae",
        },
        "de_noetica/caput-1/caput-1": {},
        "de_noetica/caput-1/caput-1-en": {},
        "de_noetica/caput-1/caput-1-summary": {},
        "about/index": {},
        "about/biography": {},
    }
    titles = {
        "index": "Euclid of Alexandria",
        "heath/index": "Elements",
        "heath/volume_I/index": "Volume I: Introduction and Books I, II",
        "heath/volume_I/book_i/index": "Book I — Triangles and Parallels",
        "heath/volume_I/book_i/propositions/index": "Book I. Propositions.",
        "heath/volume_I/book_i/propositions/01/index": "PROPOSITION 1.",
        "heath/volume_I/book_i/propositions/01/commentary": "Commentary on Proposition I.1",
        "de_noetica/index": "De Noetica Geometriae",
        "de_noetica/caput-1/caput-1": "CAPUT I: DE ORIGINE COGNITIONIS",
        "de_noetica/caput-1/caput-1-en": "CHAPTER I: ON THE ORIGIN OF GEOMETRIC KNOWLEDGE",
        "de_noetica/caput-1/caput-1-summary": "Chapter I — Summary",
        "about/index": "About",
        "about/biography": "Life & Works of Euclid",
    }
    env = _make_env(tmp_path, found_docs, metadata, titles)
    app = SimpleNamespace(env=env, builder=SimpleNamespace(name="html"))

    # 1. Home Page -> empty breadcrumbs
    ctx_home = resolve_book_context(env, "index")
    ctx_home.update(resolve_page_breadcrumbs(app, env, "index", ctx_home))
    assert ctx_home["page_breadcrumbs"] == []

    # 2. Book Title Page -> single non-clickable current section root
    ctx_book = resolve_book_context(env, "heath/index")
    ctx_book.update(resolve_page_breadcrumbs(app, env, "heath/index", ctx_book))
    assert [(c["title"], c["is_current"], c.get("link_when_current", False)) for c in ctx_book["page_breadcrumbs"]] == [
        ("The Thirteen Books of Euclid’s Elements", True, False)
    ]

    # 3. Leaf Primary Track -> Elements / Volume I / Book I / Propositions / I.1 + separate Folio pill
    p_name = "heath/volume_I/book_i/propositions/01/index"
    ctx_prop = resolve_book_context(env, p_name)
    ctx_prop.update(resolve_page_breadcrumbs(app, env, p_name, ctx_prop))
    assert [c["title"] for c in ctx_prop["page_breadcrumbs"]] == [
        "Elements",
        "Volume I",
        "Book I",
        "Propositions",
        "I.1",
    ]
    assert ctx_prop["page_breadcrumbs"][-1]["is_current"] is True
    assert ctx_prop["page_breadcrumbs"][-1]["link_when_current"] is False
    assert [b["label"] for b in ctx_prop["provenance_badges"]] == ["Folio 0255 | p. 241"]

    # 4. Leaf Companion Track -> I.1 links back to primary 01/index (no '.commentary' leak!)
    c_name = "heath/volume_I/book_i/propositions/01/commentary"
    ctx_comm = resolve_book_context(env, c_name)
    ctx_comm.update(resolve_page_breadcrumbs(app, env, c_name, ctx_comm))
    assert [c["title"] for c in ctx_comm["page_breadcrumbs"]] == [
        "Elements",
        "Volume I",
        "Book I",
        "Propositions",
        "I.1",
    ]
    assert ctx_comm["page_breadcrumbs"][-1]["link_when_current"] is True
    assert ctx_comm["page_breadcrumbs"][-1]["docname"] == p_name

    # 5. Multi-track chapter without canonical_id -> shows 'Caput I' / 'Chapter I' instead of empty!
    h_name = "de_noetica/caput-1/caput-1-summary"
    ctx_hoe = resolve_book_context(env, h_name)
    ctx_hoe.update(resolve_page_breadcrumbs(app, env, h_name, ctx_hoe))
    assert [c["title"] for c in ctx_hoe["page_breadcrumbs"]] == [
        "De Noetica Geometriae",
        "CAPUT I",
    ]
    assert ctx_hoe["page_breadcrumbs"][-1]["link_when_current"] is True

    # 6. Non-book top-level & nested pages -> zero double-root duplication
    ctx_about = resolve_book_context(env, "about/index")
    ctx_about.update(resolve_page_breadcrumbs(app, env, "about/index", ctx_about))
    assert [(c["title"], c["is_current"]) for c in ctx_about["page_breadcrumbs"]] == [
        ("About", True)
    ]

    ctx_bio = resolve_book_context(env, "about/biography")
    ctx_bio.update(resolve_page_breadcrumbs(app, env, "about/biography", ctx_bio))
    assert [(c["title"], c["is_current"]) for c in ctx_bio["page_breadcrumbs"]] == [
        ("About", False),
        ("Life & Works of Euclid", True),
    ]


def test_social_meta_titles_and_banner_generation(tmp_path: Path) -> None:
    """Verify A-to-Z <title> formatting and 1200x630 _static/social/ PNG generation."""
    repo_dir = tmp_path / "geometor" / "pacioli"
    docsrc = repo_dir / "docsrc"
    (docsrc / "_static").mkdir(parents=True)
    (docsrc / "de_divina_proportione").mkdir(parents=True)

    # Create a sample logo.png
    Image.new("RGBA", (128, 128), (232, 184, 90, 255)).save(docsrc / "_static" / "logo.png")
    (docsrc / "conf.py").write_text('site_title = "Fra Luca Pacioli"\n', encoding="utf-8")
    (docsrc / "index.rst").write_text(
        ".. container:: author-overline\n\n   the works of\n\n================\nFra Luca Pacioli\n================\n\n"
        "The mission of this project is to capture a semantic digital library of the works of Fra Luca Pacioli.\n",
        encoding="utf-8",
    )
    (docsrc / "de_divina_proportione" / "index.rst").write_text(
        ":layout: book\n:book_title: De Divina Proportione\n:author: Fra Luca Pacioli\n\n"
        "=====================\nDe Divina Proportione\n=====================\n",
        encoding="utf-8",
    )

    banner_res = generate_repo_social_banners(repo_dir)
    assert banner_res["ok"] is True
    site_banner = docsrc / "_static" / "social" / "banner.png"
    book_banner = docsrc / "_static" / "social" / "de_divina_proportione.png"
    assert site_banner.is_file()
    assert book_banner.is_file()
    with Image.open(site_banner) as im:
        assert im.size == (BANNER_WIDTH, BANNER_HEIGHT)

    env = _make_env(
        repo_dir,
        {"index", "de_divina_proportione/index"},
        {"index": {"site_title": "Fra Luca Pacioli"}, "de_divina_proportione/index": {"layout": "book"}},
        {"index": "Fra Luca Pacioli", "de_divina_proportione/index": "De Divina Proportione"},
        repo="pacioli",
        site_title="Fra Luca Pacioli",
    )
    app = SimpleNamespace(env=env, builder=SimpleNamespace(get_target_uri=lambda d: f"{d}.html"))

    home_social = build_social_and_title_context(app, "index", {"title": "GEOMETOR • pacioli"}, None)
    assert home_social["page_browser_title"] == "Fra Luca Pacioli • GEOMETOR"
    assert home_social["social_image_url"] == "https://geometor.github.io/pacioli/_static/social/banner.png"
    assert home_social["social_image_width"] == 1280
    assert home_social["social_image_height"] == 640

    book_social = build_social_and_title_context(
        app,
        "de_divina_proportione/index",
        {
            "is_book_page": True,
            "book_root": "de_divina_proportione/index",
            "book_title": "De Divina Proportione",
            "title": "De Divina Proportione",
        },
        None,
    )
    assert book_social["page_browser_title"] == "De Divina Proportione — Fra Luca Pacioli • GEOMETOR"
    assert (
        book_social["social_image_url"]
        == "https://geometor.github.io/pacioli/_static/social/de_divina_proportione.png"
    )


def test_recursive_graphic_bubbling_and_templates(tmp_path: Path) -> None:
    """Verify container index cards bubble child SVGs and templates use concise Prev/Next footers."""
    docsrc = tmp_path / "docsrc"
    prop_dir = docsrc / "book_i" / "prop_01"
    prop_dir.mkdir(parents=True)
    out_dir = tmp_path / "docs"
    out_dir.mkdir(parents=True)

    svg_file = prop_dir / "fig1.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>',
        encoding="utf-8",
    )

    dt_container = nodes.document("", nodes.title(text="Book I"))
    dt_leaf = nodes.document("", nodes.title(text="Prop 1"))
    img_node = nodes.image(uri="book_i/prop_01/fig1.svg", alt="Equilateral")
    fig_node = nodes.figure("", img_node)
    dt_leaf += fig_node

    doctrees = {"book_i/index": dt_container, "book_i/prop_01/index": dt_leaf}
    env = SimpleNamespace(
        srcdir=str(docsrc),
        config=SimpleNamespace(master_doc="index"),
        found_docs={"book_i/index", "book_i/prop_01/index"},
        metadata={"book_i/index": {}, "book_i/prop_01/index": {"order": 1}},
        get_doctree=lambda d: doctrees[d],
    )
    builder = SimpleNamespace(outdir=str(out_dir), imagedir="_images")

    bubbled = _resolve_representative_figure(env, builder, "book_i/index")
    assert bubbled is not None
    assert bubbled["svg_disk_path"] == str(svg_file)
    assert bubbled["uri"] == "_images/fig1.svg"
    assert "docsrc" not in bubbled["uri"]
    assert (out_dir / "_images" / "fig1.svg").is_file()

    # Verify footer templates use concise Prev / Next labels and header stacks org-repo inside <a>
    tpl_root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "photon_platform"
        / "publish"
        / "themes"
        / "foundation"
    )
    for tpl_rel in ("book_layout.html", "article/index.html"):
        txt = (tpl_root / tpl_rel).read_text(encoding="utf-8")
        assert "{{ prev.title|striptags }}</span>" not in txt
        assert "{{ next.title|striptags }}</span>" not in txt
        assert "book-portal-link" not in txt

    hdr_txt = (tpl_root / "layout" / "header" / "index.html").read_text(encoding="utf-8")
    assert '<span class="sep"' in hdr_txt
    assert hdr_txt.index('class="org-repo"') < hdr_txt.index("</a>")


def test_folio_ingest_renders_pngs_and_folio_map(tmp_path: Path) -> None:
    """Verify ingest_repo_pdfs renders <NNNN>.png scans and populates folio_map.json."""
    repo_dir = tmp_path / "sample_codex"
    pdf_dir = repo_dir / "resources" / "tractatus" / "pdfs"
    pdf_dir.mkdir(parents=True)

    # Generate a tiny 2-page PDF via Pillow
    p1 = Image.new("RGB", (400, 550), (255, 255, 255))
    p2 = Image.new("RGB", (400, 550), (250, 250, 250))
    pdf_file = pdf_dir / "tractatus.pdf"
    p1.save(pdf_file, "PDF", resolution=100.0, save_all=True, append_images=[p2])

    res = ingest_repo_pdfs(repo_dir, edition="tractatus", dpi=100)
    assert res["ok"] is True
    ed = res["editions"][0]
    assert ed["total_pages"] == 2
    assert ed["folio_png_count"] == 2
    assert (repo_dir / "resources" / "tractatus" / "folios" / "0001.png").is_file()
    assert (repo_dir / "resources" / "tractatus" / "folios" / "0002.png").is_file()

    fmap = json.loads((repo_dir / "resources" / "tractatus" / "folio_map.json").read_text(encoding="utf-8"))
    assert fmap["0001"] == "resources/tractatus/folios/0001.png"
    assert fmap["tractatus:0002"] == "resources/tractatus/folios/0002.png"
