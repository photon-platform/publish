"""Tests for Sphinx math node restoration and RST-parsed picture captions."""

from __future__ import annotations

from pathlib import Path

from sphinx.application import Sphinx


def test_dollar_math_safety_net_and_parsed_picture_caption(tmp_path: Path) -> None:
    """Protected $...$ / $$...$$ convert to Sphinx math nodes and :caption: parses RST inline markup."""
    srcdir = tmp_path / "docsrc"
    outdir = tmp_path / "docs"
    doctreedir = tmp_path / "doctrees"
    srcdir.mkdir()
    (srcdir / "_static").mkdir()

    (srcdir / "fig.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" class="euclid-graphic">'
        '<line x1="0" y1="0" x2="100" y2="100" /></svg>',
        encoding="utf-8",
    )
    (srcdir / "conf.py").write_text(
        "extensions = [\n"
        "    'sphinx.ext.mathjax',\n"
        "    'photon_platform.publish.directives.elements',\n"
        "    'photon_platform.publish.images',\n"
        "]\n"
        "html_theme = 'basic'\n",
        encoding="utf-8",
    )
    (srcdir / "index.rst").write_text(
        ".. _tri-ref:\n\n"
        "Test Page\n"
        "=========\n\n"
        "Inline dollar math $A + B$ and native :math:`C`.\n\n"
        "$$\n"
        "a^2 + b^2 = c^2\n"
        "$$\n\n"
        "Currency $100,000 a simultaneous debit of $40,000 stays prose.\n\n"
        ".. picture:: fig.svg\n"
        "   :alt: Triangle\n"
        "   :caption: **Theorem 1.** Right triangle (:ref:`see top <tri-ref>`) with :math:`a^2 + b^2 = c^2`.\n",
        encoding="utf-8",
    )

    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
        warningiserror=False,
    )
    app.build()

    html = (outdir / "index.html").read_text(encoding="utf-8")
    assert r'<span class="math notranslate nohighlight">\(A + B\)</span>' in html
    assert r'<span class="math notranslate nohighlight">\(C\)</span>' in html
    assert r"\[a^2 + b^2 = c^2\]" in html
    assert "$100,000 a simultaneous debit of $40,000" in html
    assert "<figcaption><strong>Theorem 1.</strong> Right triangle (" in html
    assert 'href="#tri-ref"' in html
    assert r'<span class="math notranslate nohighlight">\(a^2 + b^2 = c^2\)</span>.</figcaption>' in html
    assert "mathjax" in html.lower()
