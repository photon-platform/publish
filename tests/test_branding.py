"""Tests for global Sphinx branding defaults and Folio Review brand assets."""

from __future__ import annotations

from pathlib import Path

from photon_platform.publish import global_conf
from photon_platform.publish.folio_review.app import create_app


def test_global_conf_declares_logo_and_favicon() -> None:
    """Ensure global_conf configures both html_logo and html_favicon."""
    assert global_conf.html_logo == "_static/logo.png"
    assert global_conf.html_favicon == "_static/favicon.ico"


def test_folio_review_serves_default_and_repo_brand_assets(tmp_path: Path) -> None:
    """Verify Folio Review serves fallback and repo-specific logo.png & favicon.ico."""
    edition_dir = tmp_path / "sample-repo" / "resources" / "edition"
    (edition_dir / "vol1").mkdir(parents=True)

    # 1. Fallback to publish's built-in static/favicon.ico and static/logo.png
    app = create_app(root_dir=edition_dir, project_title="Sample", edition_label="1900")
    client = app.test_client()

    fav_resp = client.get("/favicon.ico")
    assert fav_resp.status_code == 200
    assert len(fav_resp.data) > 100

    logo_resp = client.get("/brand/logo.png")
    assert logo_resp.status_code == 200
    assert logo_resp.data.startswith(b"\x89PNG")

    dash_resp = client.get("/")
    assert dash_resp.status_code == 200
    html = dash_resp.get_data(as_text=True)
    assert 'rel="icon"' in html
    assert '/favicon.ico' in html
    assert '/brand/logo.png' in html

    # 2. Enclosing repo's docsrc/_static/ overrides fallback assets
    repo_static = tmp_path / "sample-repo" / "docsrc" / "_static"
    repo_static.mkdir(parents=True)
    custom_ico = b"\x00\x00\x01\x00custom-ico-payload"
    custom_png = b"\x89PNG\r\n\x1a\ncustom-png-payload"
    (repo_static / "favicon.ico").write_bytes(custom_ico)
    (repo_static / "logo.png").write_bytes(custom_png)

    assert client.get("/favicon.ico").data == custom_ico
    assert client.get("/brand/logo.png").data == custom_png
