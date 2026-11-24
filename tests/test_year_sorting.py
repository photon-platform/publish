"""Tests for standardized chronological publication year parsing, display, and sorting."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sphinx.application import Sphinx

from photon_platform.publish.directives.collection import (
    chronological_sort_key,
    format_year_display,
    parse_year_sort_value,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (-300, -300),
        ("-300", -300),
        ("+60", 60),
        (1952, 1952),
        ("1952", 1952),
        ("ca. 300 BCE", -300),
        ("c. 300 BCE / 1896", -300),
        ("ca. 350 BCE / 1831, 1908–1952", -350),
        ("fl. c. 300 BC", -300),
        ("ca. 60 CE", 60),
        ("c. 470 AD", 470),
        ("ca. 1257–1259", 1257),
        ("1596 / 1621", 1596),
        ("1950–1952", 1950),
        ("", None),
        (None, None),
        (False, None),
        ("undated", None),
    ],
)
def test_parse_year_sort_value(raw: object, expected: int | None) -> None:
    assert parse_year_sort_value(raw) == expected


@pytest.mark.parametrize(
    ("year_raw", "year_label", "expected"),
    [
        (-300, "ca. 300 BCE", "ca. 300 BCE"),
        (-300, None, "300 BCE"),
        ("-200", "", "200 BCE"),
        (60, "ca. 60 CE", "ca. 60 CE"),
        (1509, None, "1509"),
        ("1950", "1950–1952", "1950–1952"),
        ("ca. 340 CE", None, "ca. 340 CE"),
        ("", None, ""),
        (None, None, ""),
    ],
)
def test_format_year_display(year_raw: object, year_label: str | None, expected: str) -> None:
    assert format_year_display(year_raw, year_label) == expected


def test_chronological_sort_key_order_and_undated_last() -> None:
    records = [
        ("Altshiller-Court", "1952"),
        ("Undated Manuscript", ""),
        ("Euclid Elements", "-300"),
        ("Euclid Data", "ca. 300 BCE"),
        ("Heron Metrica", "60"),
        ("Plato Meno", "-385"),
        ("Fibonacci Liber Abbaci", "1202"),
        ("Apollonius Conics", "-200"),
    ]
    asc = sorted(records, key=lambda r: chronological_sort_key(r[1], r[0], reverse=False))
    assert [r[0] for r in asc] == [
        "Plato Meno",
        "Euclid Data",
        "Euclid Elements",
        "Apollonius Conics",
        "Heron Metrica",
        "Fibonacci Liber Abbaci",
        "Altshiller-Court",
        "Undated Manuscript",
    ]
    desc = sorted(records, key=lambda r: chronological_sort_key(r[1], r[0], reverse=True))
    assert [r[0] for r in desc] == [
        "Altshiller-Court",
        "Fibonacci Liber Abbaci",
        "Heron Metrica",
        "Apollonius Conics",
        "Euclid Data",
        "Euclid Elements",
        "Plato Meno",
        "Undated Manuscript",
    ]


def test_reference_directory_sorts_bce_to_modern_in_sphinx(tmp_path: Path) -> None:
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    doctreedir = tmp_path / "doctrees"
    books_dir = srcdir / "books"
    books_dir.mkdir(parents=True)

    import photon_platform.publish as publish_pkg

    themes_dir = str(Path(publish_pkg.__file__).resolve().parent / "themes")
    (srcdir / "conf.py").write_text(
        f"""
project = "Test Books"
extensions = ["photon_platform.publish.directives.collection"]
html_theme = "foundation"
html_theme_path = [{themes_dir!r}]
""",
        encoding="utf-8",
    )
    (srcdir / "index.rst").write_text(
        """
Root
====

.. toctree::

   books/index
""",
        encoding="utf-8",
    )
    (books_dir / "index.rst").write_text(
        """
Books
=====

.. reference-directory::
   :sort: year
""",
        encoding="utf-8",
    )
    (books_dir / "euclid.rst").write_text(
        """\
:type: book_record
:author: Euclid of Alexandria
:year: -300
:year_label: ca. 300 BCE
:edition_year: 1926

Elements
========
""",
        encoding="utf-8",
    )
    (books_dir / "plato.rst").write_text(
        """\
:type: book_record
:author: Plato of Athens
:year: -385
:year_label: ca. 385 BCE

Meno
====
""",
        encoding="utf-8",
    )
    (books_dir / "heron.rst").write_text(
        """\
:type: book_record
:author: Heron of Alexandria
:year: 60
:year_label: ca. 60 CE

Metrica
=======
""",
        encoding="utf-8",
    )
    (books_dir / "court.rst").write_text(
        """\
:type: book_record
:author: Nathan Altshiller-Court
:year: 1952

College Geometry
================
""",
        encoding="utf-8",
    )
    (books_dir / "undated.rst").write_text(
        """\
:type: book_record
:author: Anonymous

Undated Fragment
================
""",
        encoding="utf-8",
    )

    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
        status=None,
        warning=None,
    )
    app.build()

    html = (outdir / "books" / "index.html").read_text(encoding="utf-8")
    titles = re.findall(r'data-title="([^"]+)"', html)
    years = re.findall(r'data-year="([^"]*)"', html)

    assert titles == ["Meno", "Elements", "Metrica", "College Geometry", "Undated Fragment"]
    assert years == ["-385", "-300", "60", "1952", ""]
    assert "<span>ca. 300 BCE</span>" in html
    assert "1926" in html
