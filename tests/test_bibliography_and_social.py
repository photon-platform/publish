"""Tests for standard citation formatting (Chicago/MLA/APA/BibTeX), parallel-track
Hoenen-style automated backlinks, and local HTML+CSS social media card capture."""

from __future__ import annotations

from pathlib import Path

import photon_platform.publish as publish_pkg
from photon_platform.publish.bibliography import (
    format_apa,
    format_bibtex,
    format_chicago,
    format_mla,
)
from photon_platform.publish.cards import Card
from photon_platform.publish.social_capture import (
    build_social_card_from_params,
    capture_social_card_png,
    find_chrome_binary,
    render_social_card_html,
)
from PIL import Image
from sphinx.application import Sphinx


def _themes_dir() -> str:
    return str(Path(publish_pkg.__file__).resolve().parent / "themes")


def test_standard_citation_formatters_for_classical_edition() -> None:
    card = Card(
        id="aristotle:analytica_posteriora/index",
        docname="analytica_posteriora/index",
        type="book",
        title="Posterior Analytics",
        native_title="Analytica Posteriora",
        author="Aristotle",
        year=-350,
        year_label="ca. 350 BCE",
        year_display="ca. 350 BCE",
        edition_year=1949,
        site_url="https://geometor.github.io/aristotle/analytica_posteriora/",
        bib={
            "editors": "W. D. Ross",
            "publisher": "Clarendon Press",
            "place": "Oxford",
            "locus": "Bekker 71a–100b",
        },
    )

    chicago = format_chicago(card)
    mla = format_mla(card)
    apa = format_apa(card)
    bibtex = format_bibtex(card)

    assert "Aristotle." in chicago
    assert "*Posterior Analytics (Analytica Posteriora)*." in chicago
    assert "Edited by W. D. Ross." in chicago
    assert "Oxford: Clarendon Press, 1949." in chicago

    assert "Aristotle. *Posterior Analytics*." in mla
    assert "Clarendon Press, 1949." in mla

    assert "Aristotle (1949)." in apa
    assert "(W. D. Ross, Ed.)" in apa
    assert "(Original work composed ca. 350 BCE)." in apa

    assert bibtex.startswith("@book{aristotle_1949_posterior,")
    assert "origdate" in bibtex and "{-350}" in bibtex
    assert "publisher" in bibtex and "{Clarendon Press}" in bibtex


def test_parallel_track_hoenen_style_backlinks_and_bib_export(tmp_path: Path) -> None:
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    doctreedir = tmp_path / "doctrees"
    (srcdir / "caput-1").mkdir(parents=True)
    (srcdir / "people").mkdir(parents=True)
    (srcdir / "bibliography").mkdir(parents=True)

    (srcdir / "conf.py").write_text(
        f"""
project = "Hoenen Test"
extensions = [
    "photon_platform.publish.cards",
    "photon_platform.publish.directives.card",
    "photon_platform.publish.directives.collection",
    "photon_platform.publish.roles.geometry",
    "photon_platform.publish.bibliography",
]
html_theme = "foundation"
html_theme_path = [{_themes_dir()!r}]
""",
        encoding="utf-8",
    )

    (srcdir / "index.rst").write_text(
        """\
De Noetica Geometriae
=====================

.. toctree::

   caput-1/caput-1
   caput-1/caput-1-en
   people/aquinas
   bibliography/euclid-elements
""",
        encoding="utf-8",
    )

    (srcdir / "caput-1" / "caput-1.rst").write_text(
        """\
:language: la

Caput I
=======

Doctrina :person:`S. Thomae <aquinas>` et :cite:`Euclidis Elementa <euclid-elements>`.
""",
        encoding="utf-8",
    )
    (srcdir / "caput-1" / "caput-1-en.rst").write_text(
        """\
:language: en

Caput I (English)
=================

The doctrine of :person:`St. Thomas Aquinas <aquinas>` and :cite:`Euclid's Elements <euclid-elements>`.
""",
        encoding="utf-8",
    )

    (srcdir / "people" / "aquinas.rst").write_text(
        """\
:type: person
:death_year: 1274
:lifespan: 1225 – 1274
:description: Scholastic philosopher of intelligible matter and formal abstraction.

St. Thomas Aquinas
==================

.. backlinks::
""",
        encoding="utf-8",
    )

    (srcdir / "bibliography" / "euclid-elements.rst").write_text(
        """\
:type: reference
:author: Euclid of Alexandria
:year: -300
:year_label: ca. 300 BCE
:edition_year: 1926
:translators: Sir Thomas L. Heath
:publisher: Cambridge University Press
:place: Cambridge

The Thirteen Books of Euclid's Elements
=======================================

.. citation-formats::

.. backlinks::
""",
        encoding="utf-8",
    )

    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
    )
    app.build()

    aquinas_html = (outdir / "people" / "aquinas.html").read_text(encoding="utf-8")
    assert "Occurrences in This Work (1)" in aquinas_html
    assert "LA" in aquinas_html and "EN" in aquinas_html
    assert "caput-1/caput-1.html#occ-person-aquinas-1" in aquinas_html
    assert "caput-1/caput-1-en.html#occ-person-aquinas-1" in aquinas_html

    euclid_html = (outdir / "bibliography" / "euclid-elements.html").read_text(encoding="utf-8")
    assert "Translated by Sir Thomas L. Heath." in euclid_html
    assert "Cambridge University Press" in euclid_html
    assert "Occurrences in This Work (1)" in euclid_html

    bib_export = outdir / "bibliography.bib"
    assert bib_export.is_file()
    bib_text = bib_export.read_text(encoding="utf-8")
    assert "@book{" in bib_text and "Cambridge University Press" in bib_text


def test_html_css_social_card_capture_and_caching(tmp_path: Path) -> None:
    emblem = tmp_path / "medallion.svg"
    emblem.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        '<circle cx="20" cy="20" r="18" fill="#12141a" stroke="#d4af37" stroke-width="2"/>'
        "</svg>",
        encoding="utf-8",
    )
    hero = tmp_path / "hero.svg"
    hero.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        '<polygon points="100,20 180,170 20,170" fill="none" stroke="#e8b85a" stroke-width="3"/>'
        "</svg>",
        encoding="utf-8",
    )

    card = build_social_card_from_params(
        org_brand="GEOMETOR",
        repo_slug="euclid",
        title="The Thirteen Books of Euclid's Elements",
        overline="Sir Thomas L. Heath (1926)",
        subtitle="Complete thirteen books of plane geometry, proportion, and solid geometry.",
        emblem_path=emblem,
        hero_path=hero,
        site_domain="geometor.github.io/euclid/heath/",
    )

    html_doc = render_social_card_html(card, asset_root=tmp_path)
    assert "card--social" in html_doc
    assert "The Thirteen Books of Euclid" in html_doc
    assert "polygon" in html_doc

    chrome_bin = find_chrome_binary()
    assert chrome_bin is not None, "Expected local Chrome/Chromium binary"

    out_png = tmp_path / "banner.png"
    written = capture_social_card_png(card, out_png, asset_root=tmp_path, force=True, chrome_bin=chrome_bin)
    assert written is True
    assert out_png.is_file()
    with Image.open(out_png) as img:
        assert img.size == (1280, 640)

    # Unchanged card should skip re-capture when force=False
    written_again = capture_social_card_png(card, out_png, asset_root=tmp_path, force=False, chrome_bin=chrome_bin)
    assert written_again is False
