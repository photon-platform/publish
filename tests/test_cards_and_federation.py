"""Tests for unified Page Cards, `cards.json` federation, `.. card::`, `.. summary::`,
mixed local/remote `.. collection::`, `:card_ref:` inheritance, and cross-repo apparatus roles."""

from __future__ import annotations

import json
from pathlib import Path

import photon_platform.publish as publish_pkg
from sphinx.application import Sphinx


def _themes_dir() -> str:
    return str(Path(publish_pkg.__file__).resolve().parent / "themes")


def _build_sphinx(srcdir: Path, outdir: Path, doctreedir: Path) -> Sphinx:
    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
        warningiserror=False,
    )
    app.build()
    return app


def test_hybrid_card_description_and_cards_json_manifest(tmp_path: Path) -> None:
    """Verify description priority (:description: > .. summary:: > .. enunciation:: > fallback)
    and automatic `docs/cards.json` export with dual medallion + hero slots."""
    srcdir = tmp_path / "aristotle" / "docsrc"
    outdir = tmp_path / "aristotle" / "docs"
    doctreedir = tmp_path / "aristotle" / ".doctrees"
    (srcdir / "_static").mkdir(parents=True)
    (srcdir / "analytica_posteriora").mkdir(parents=True)

    # Small site medallion SVG
    (srcdir / "_static" / "medallion.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8"/></svg>',
        encoding="utf-8",
    )
    # Larger hero diagram SVG
    (srcdir / "analytica_posteriora" / "hero.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80"/></svg>',
        encoding="utf-8",
    )

    (srcdir / "conf.py").write_text(
        f"""
org = "geometor"
org_name = "GEOMETOR"
repo = "aristotle"
repo_name = "aristotle"
project = "Aristotle"
html_baseurl = "https://geometor.github.io/aristotle"
extensions = [
    "photon_platform.publish.cards",
    "photon_platform.publish.directives.card",
    "photon_platform.publish.directives.collection",
    "photon_platform.publish.directives.elements",
    "photon_platform.publish.roles.geometry",
    "photon_platform.publish.bibliography",
]
html_theme = "foundation"
html_theme_path = [{_themes_dir()!r}]
html_static_path = ["_static"]
""",
        encoding="utf-8",
    )

    (srcdir / "index.rst").write_text(
        """\
:description: Canonical works of Aristotle in the GEOMETOR archive.

Aristotle
=========

.. toctree::

   analytica_posteriora/index
   summary_page
   fallback_page
""",
        encoding="utf-8",
    )

    (srcdir / "analytica_posteriora" / "index.rst").write_text(
        """\
:type: book
:author: Aristotle
:year: -350
:year_label: ca. 350 BCE
:edition_year: 1949
:editors: W. D. Ross
:publisher: Clarendon Press
:place: Oxford
:native_title: Ἀναλυτικὰ Ὕστερα
:languages: Greek, English

.. _cite-aristotle-anal-post:

Analytica Posteriora
====================

.. summary::

   Foundational treatise on demonstrative science, first principles, and intellectual vision.

.. image:: hero.svg
   :alt: Demonstration Graph

Body text that should not override the explicit summary block.
""",
        encoding="utf-8",
    )

    (srcdir / "summary_page.rst").write_text(
        """\
Hidden Summary Page
===================

.. summary::
   :hidden:

   Intentional editorial card blurb stored cleanly without showing in body prose.

Opening body paragraph that differs from the card copy.
""",
        encoding="utf-8",
    )

    (srcdir / "fallback_page.rst").write_text(
        """\
Uncurated Page
==============

This opening body paragraph acts as a fallback description and should be flagged for linting.
""",
        encoding="utf-8",
    )

    app = _build_sphinx(srcdir, outdir, doctreedir)

    cards = app.env.publish_cards
    assert cards["index"].description_source == "meta"
    assert cards["analytica_posteriora/index"].description_source == "summary"
    assert "demonstrative science" in cards["analytica_posteriora/index"].description
    assert cards["analytica_posteriora/index"].emblem == "_static/medallion.svg"
    assert cards["analytica_posteriora/index"].emblem_svg
    assert cards["analytica_posteriora/index"].image
    assert cards["analytica_posteriora/index"].image_svg

    assert cards["summary_page"].description_source == "meta"
    assert "Intentional editorial card blurb" in cards["summary_page"].description
    # Hidden summary should not render inline on summary_page.html
    summary_html = (outdir / "summary_page.html").read_text(encoding="utf-8")
    assert "Intentional editorial card blurb" not in summary_html.split("</head>", 1)[-1]

    assert cards["fallback_page"].description_source == "fallback"
    assert "fallback_page" in app.env.publish_cards_stats["uncurated_docs"]

    # Verify cards.json emitted right beside objects.inv
    manifest_file = outdir / "cards.json"
    assert manifest_file.is_file()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["schema"] == "photon.card.v1"
    assert manifest["site"]["repo"] == "aristotle"
    assert manifest["labels"]["cite-aristotle-anal-post"] == "analytica_posteriora/index"
    ap = manifest["cards"]["analytica_posteriora/index"]
    assert ap["type"] == "book"
    assert ap["url"] == "https://geometor.github.io/aristotle/analytica_posteriora/"
    assert ap["emblem"] == "https://geometor.github.io/aristotle/_static/medallion.svg"
    assert ap["bib"]["editors"] == "W. D. Ross"


def test_federated_cards_collection_inheritance_and_roles(tmp_path: Path) -> None:
    """Two remote sites (`aristotle` + `catalog`) publish `cards.json`; a third site (`hoenen`)
    embeds `.. card::`, mixes local + remote records in `.. collection::`, inherits metadata via
    `:card_ref:`, and resolves `:person:` / `:cite:` cross-project with zero sidecar JSONs."""
    # 1. Build Site A: aristotle
    a_src = tmp_path / "aristotle" / "docsrc"
    a_out = tmp_path / "aristotle" / "docs"
    a_src.mkdir(parents=True)
    (a_src / "conf.py").write_text(
        f"""
org = "geometor"
org_name = "GEOMETOR"
repo = "aristotle"
repo_name = "aristotle"
project = "Aristotle"
html_baseurl = "https://geometor.github.io/aristotle"
extensions = [
    "photon_platform.publish.cards",
    "photon_platform.publish.directives.card",
    "photon_platform.publish.directives.collection",
]
html_theme = "foundation"
html_theme_path = [{_themes_dir()!r}]
""",
        encoding="utf-8",
    )
    (a_src / "index.rst").write_text(
        """\
:type: book
:author: Aristotle
:year: -350
:year_label: ca. 350 BCE
:edition_year: 1949
:editors: W. D. Ross
:publisher: Clarendon Press
:place: Oxford
:description: Foundational treatise on demonstrative science and intellectual intuition.

.. _cite-aristotle-anal-post:

Analytica Posteriora
====================

Canonical edition.
""",
        encoding="utf-8",
    )
    _build_sphinx(a_src, a_out, tmp_path / "aristotle" / ".doctrees")

    # 2. Build Site B: catalog (fallback hub for figures without their own repo)
    c_src = tmp_path / "catalog" / "docsrc"
    c_out = tmp_path / "catalog" / "docs"
    (c_src / "people").mkdir(parents=True)
    (c_src / "conf.py").write_text(
        f"""
org = "geometor"
org_name = "GEOMETOR"
repo = "catalog"
repo_name = "catalog"
project = "GEOMETOR Catalog"
html_baseurl = "https://geometor.github.io/catalog"
extensions = [
    "photon_platform.publish.cards",
    "photon_platform.publish.directives.card",
    "photon_platform.publish.directives.collection",
]
html_theme = "foundation"
html_theme_path = [{_themes_dir()!r}]
""",
        encoding="utf-8",
    )
    (c_src / "index.rst").write_text(
        """\
Catalog
=======

.. toctree::

   people/eudoxus
""",
        encoding="utf-8",
    )
    (c_src / "people" / "eudoxus.rst").write_text(
        """\
:type: person
:death_year: -355
:lifespan: c. 408 – c. 355 BCE
:description: Greek astronomer and geometer who formulated the general theory of proportions.

.. _person-eudoxus:

Eudoxus of Cnidus
=================

Canonical catalog record.
""",
        encoding="utf-8",
    )
    _build_sphinx(c_src, c_out, tmp_path / "catalog" / ".doctrees")

    # 3. Build Consumer Site C: hoenen
    h_src = tmp_path / "hoenen" / "docsrc"
    h_out = tmp_path / "hoenen" / "docs"
    (h_src / "bibliography").mkdir(parents=True)
    (h_src / "people").mkdir(parents=True)
    (h_src / "conf.py").write_text(
        f"""
org = "geometor"
org_name = "GEOMETOR"
repo = "hoenen"
repo_name = "hoenen"
project = "Hoenen"
html_baseurl = "https://geometor.github.io/hoenen"
extensions = [
    "sphinx.ext.intersphinx",
    "photon_platform.publish.cards",
    "photon_platform.publish.directives.card",
    "photon_platform.publish.directives.collection",
    "photon_platform.publish.roles.geometry",
    "photon_platform.publish.bibliography",
]
intersphinx_mapping = {{
    "aristotle": ("https://geometor.github.io/aristotle", ({str(a_out / 'objects.inv')!r}, None)),
    "catalog": ("https://geometor.github.io/catalog", ({str(c_out / 'objects.inv')!r}, None)),
}}
html_theme = "foundation"
html_theme_path = [{_themes_dir()!r}]
""",
        encoding="utf-8",
    )

    (h_src / "index.rst").write_text(
        """\
De Noetica Geometriae
=====================

Hoenen cites :person:`Eudoxus <eudoxus>` and :cite:`Posterior Analytics <aristotle-anal-post>`.

.. card:: aristotle:index
   :variant: banner

   Cited 5 times in Hoenen's analysis of formal abstraction.

.. toctree::

   bibliography/index
   people/index
""",
        encoding="utf-8",
    )

    # Local bibliography dossier inheriting canonical metadata from aristotle:index via :card_ref:
    (h_src / "bibliography" / "aristotle-anal-post.rst").write_text(
        """\
:type: reference
:card_ref: aristotle:index

.. _cite-aristotle-anal-post:

Aristotle — Analytica Posteriora
================================

.. citation-formats::

.. backlinks::

*What Hoenen refers to*: Immediate intellectual intuition of first principles.
""",
        encoding="utf-8",
    )
    (h_src / "bibliography" / "index.rst").write_text(
        """\
Bibliography
============

.. reference-directory::
   :sort: year

   aristotle-anal-post
""",
        encoding="utf-8",
    )

    # Mixed collection: local person + remote catalog person via :from-roles:
    (h_src / "people" / "local_scholar.rst").write_text(
        """\
:type: person
:death_year: 1961
:lifespan: 1880 – 1961
:description: Jesuit philosopher of geometry at the Gregorian University.

Peter Hoenen, S.J.
==================

Local record.
""",
        encoding="utf-8",
    )
    (h_src / "people" / "index.rst").write_text(
        """\
People
======

.. people-directory::
   :from-roles: person
   :sort: death_year
""",
        encoding="utf-8",
    )

    app = _build_sphinx(h_src, h_out, tmp_path / "hoenen" / ".doctrees")

    # 1. Inline `.. card::` embed pulled remote description + local contextual note
    idx_html = (h_out / "index.html").read_text(encoding="utf-8")
    assert "Foundational treatise on demonstrative science" in idx_html
    assert "Cited 5 times in Hoenen" in idx_html
    assert "In This Work" in idx_html

    # 2. `:person:` resolved cross-project to `catalog` with rich Card tooltip (zero persons.json!)
    assert "https://geometor.github.io/catalog/people/eudoxus.html" in idx_html
    assert "general theory of proportions" in idx_html

    # 3. `:card_ref:` inherited Ross / Clarendon Press / Oxford / -350 onto local bibliography dossier
    bib_card = app.env.publish_cards["bibliography/aristotle-anal-post"]
    assert bib_card.author == "Aristotle"
    assert bib_card.year_sort == -350
    assert bib_card.bib.get("editors") == "W. D. Ross"
    bib_html = (h_out / "bibliography" / "aristotle-anal-post.html").read_text(encoding="utf-8")
    assert "Clarendon Press" in bib_html
    assert "@book{" in bib_html
    assert "Occurrences in This Work (1)" in bib_html
    assert "occ-cite-aristotle-anal-post-1" in bib_html

    # 4. `:from-roles: person` auto-merged local Peter Hoenen + remote Eudoxus sorted ancient -> modern
    import re

    people_html = (h_out / "people" / "index.html").read_text(encoding="utf-8")
    card_titles = re.findall(r'data-title="([^"]+)"', people_html)
    assert card_titles == ["Eudoxus of Cnidus", "Peter Hoenen, S.J."]
