"""Tests for inline SVG dimension injection, attribute normalization, and scoped style preservation."""

from pathlib import Path

from photon_platform.publish.images.directive import prepare_inline_svg


def test_widthless_viewbox_injects_pixel_dimensions_and_scopes_dark_media(tmp_path: Path) -> None:
    svg_file = tmp_path / "06-tran.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" class="euclid-graphic" viewBox="0 0 680 480">\n'
        "  <style>\n"
        "    .euclid-graphic .svg-bg { fill: none; }\n"
        "    .euclid-graphic .geom-segment.golden-major { stroke: #d4af37; stroke-width: 4.3; }\n"
        "    @media (prefers-color-scheme: dark) {\n"
        "      .euclid-graphic .geom-segment.golden-major { stroke: #f5c542; }\n"
        "    }\n"
        "  </style>\n"
        '  <rect class="svg-bg" x="0" y="0" width="680" height="480" fill="none" />\n'
        '  <path class="geom-segment golden-major" d="M 10 10 L 100 100" id="p1" data-ref="OF" />\n'
        "</svg>\n",
        encoding="utf-8",
    )

    out = prepare_inline_svg(svg_file, as_thumbnail=False)
    assert out is not None
    assert 'width="680"' in out
    assert 'height="480"' in out
    assert out.split(">", 1)[0].count("class=") == 1
    assert 'class="svg-bg"' not in out
    assert "data-svg-scope=" in out
    assert ".geom-segment.golden-major { stroke: #d4af37; stroke-width: 4.3 }" in out
    assert 'body:not(.light-mode):not([data-theme="light"]) svg[data-svg-scope=' in out


def test_model_space_viewbox_scales_and_deduplicates_thumbnail_classes(tmp_path: Path) -> None:
    svg_file = tmp_path / "w-01.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" id="root-w01" class="wildberger-diagram" viewBox="-1.0800 -8.0800 8.1600 8.1600">\n'
        "  <style>\n"
        "    svg.wildberger-diagram { background-color: #111318; border: 1px solid #2e3440; width: 100%; max-height: 560px; }\n"
        "    .Line, .Segment { stroke: #9aa5b4; stroke-width: 1.3px; fill: none; }\n"
        "    @media (prefers-color-scheme: light) {\n"
        "      svg.wildberger-diagram { background-color: #fbfbfd; }\n"
        "      svg.wildberger-diagram .Line { stroke: #4c566a; }\n"
        "    }\n"
        "  </style>\n"
        '  <line class="Line" id="l1" x1="0" y1="0" x2="5" y2="-5" />\n'
        "</svg>\n",
        encoding="utf-8",
    )

    thumb = prepare_inline_svg(svg_file, as_thumbnail=True)
    assert thumb is not None
    open_tag = thumb.split(">", 1)[0] + ">"
    assert open_tag.count("class=") == 1
    assert 'class="euclid-graphic euclid-thumbnail wildberger-diagram"' in open_tag
    assert 'id="root-w01"' not in open_tag
    assert 'id="l1"' not in thumb
    assert 'width="600"' in open_tag
    assert 'height="600"' in open_tag
    assert "background-color" not in thumb
    assert ".Line" in thumb
    assert "body.light-mode svg[data-svg-scope=" in thumb


def test_root_custom_vars_preserved_while_global_theme_vars_stripped(tmp_path: Path) -> None:
    svg_file = tmp_path / "fig_conics.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360" width="760" height="360" class="euclid-graphic">\n'
        "  <style>\n"
        "    :root { --geom-fg: #18181b; --geom-bg: #ffffff; --geom-hyper: #2563eb; }\n"
        "    @media (prefers-color-scheme: dark) {\n"
        "      :root { --geom-fg: #e4ded5; --geom-hyper: #60a5fa; }\n"
        "    }\n"
        "    .geom-hyper-line { stroke: var(--geom-hyper); fill: none; }\n"
        "  </style>\n"
        '  <path class="geom-hyper-line" d="M 0 0 L 100 50" />\n'
        "</svg>\n",
        encoding="utf-8",
    )

    out = prepare_inline_svg(svg_file)
    assert out is not None
    assert "--geom-fg:" not in out
    assert "--geom-bg:" not in out
    assert "--geom-hyper: #2563eb" in out
    assert "--geom-hyper: #60a5fa" in out
    assert ".geom-hyper-line" in out


def test_legacy_light_only_boilerplate_style_is_stripped(tmp_path: Path) -> None:
    svg_file = tmp_path / "hero.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 280" width="420" height="280" class="euclid-graphic">\n'
        "  <style>\n"
        "    .euclid-graphic { background-color: #ffffff; font-weight: 700; }\n"
        "    .geom-line { stroke: #18181b; stroke-width: 1.8; fill: none; }\n"
        "    [data-ref]:hover, .highlight { stroke: #c88a1e !important; }\n"
        "  </style>\n"
        '  <line class="geom-line" x1="0" y1="0" x2="100" y2="100" />\n'
        "</svg>\n",
        encoding="utf-8",
    )

    out = prepare_inline_svg(svg_file)
    assert out is not None
    assert "<style>" not in out
    assert "data-svg-scope=" not in out
    assert "#18181b" not in out


def test_custom_classes_without_media_are_preserved(tmp_path: Path) -> None:
    svg_file = tmp_path / "sieve.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" class="euclid-graphic" viewBox="0 0 820 474">\n'
        "  <style>\n"
        "    .euclid-graphic .blue-line { stroke: #6ba9d8; stroke-width: 2.0; fill: none; }\n"
        "    .euclid-graphic .card-accent { fill: #202026; stroke: #e2b553; }\n"
        "  </style>\n"
        '  <path class="blue-line" d="M 10 10 Q 50 30 90 10" />\n'
        "</svg>\n",
        encoding="utf-8",
    )

    out = prepare_inline_svg(svg_file)
    assert out is not None
    assert 'width="820"' in out
    assert 'height="474"' in out
    assert ".blue-line" in out
    assert ".card-accent" in out


def test_sass_compiles_geometor_svg_selectors() -> None:
    import sass

    scss_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "photon_platform"
        / "publish"
        / "themes"
        / "foundation"
        / "static"
        / "scss"
        / "styles.scss"
    )
    css = sass.compile(filename=str(scss_path), output_style="expanded")
    assert "figure.photon-svg svg:not([width])" in css
    assert ".geom-segment" in css
    assert ".geom-accent-line" in css
    assert ".geom-assert-line" in css
    assert ".geom-hyper-line" in css
    assert ".geom-rose-line" in css
    assert ".geom-polygon-rose" in css
    assert ".geom-point-rose" in css
    assert ".geom-label-hyper" in css
    assert ".geom-label-rose" in css
