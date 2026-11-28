"""Local HTML+CSS Social Media Card Capture (`1280×640` PNG) via headless Chrome.

Renders the exact same Foundation theme `<article class="card card--social">` markup
and compiled CSS as the live website, then snaps a crisp `1280×640` PNG using the
locally installed Chrome/Chromium binary (`--headless=new --screenshot`).

This runs ONLY when invoked locally via `publish social-banner` (never during
`publish build` or GitHub Actions).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .cards import Card, _read_inline_svg

SOCIAL_WIDTH = 1280
SOCIAL_HEIGHT = 640


def find_chrome_binary() -> str | None:
    """Locate a local Chromium/Chrome binary for headless HTML+CSS capture."""
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found

    # Check Playwright's cached Chromium if installed locally
    pw_cache = Path.home() / ".cache" / "ms-playwright"
    if pw_cache.is_dir():
        for cand in sorted(pw_cache.glob("chromium-*/chrome-linux/chrome"), reverse=True):
            if cand.is_file():
                return str(cand)
    return None


def _load_compiled_theme_css() -> str:
    """Load the compiled Foundation theme CSS (compiling SCSS on-the-fly if needed)."""
    theme_dir = Path(__file__).resolve().parent / "themes" / "foundation"
    css_path = theme_dir / "static" / "css" / "styles.css"
    scss_path = theme_dir / "static" / "scss" / "styles.scss"

    needs_compile = not css_path.is_file()
    if not needs_compile and scss_path.is_file():
        cards_scss = theme_dir / "static" / "scss" / "elements" / "_cards.scss"
        latest_scss = max(
            scss_path.stat().st_mtime,
            cards_scss.stat().st_mtime if cards_scss.is_file() else 0.0,
        )
        if latest_scss > css_path.stat().st_mtime:
            needs_compile = True

    if needs_compile:
        with contextlib.suppress(ImportError, OSError, ValueError):
            import sass

            compiled = sass.compile(filename=str(scss_path), output_style="compressed")
            css_path.parent.mkdir(parents=True, exist_ok=True)
            css_path.write_text(compiled, encoding="utf-8")
            return compiled

    if css_path.is_file():
        return css_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def render_social_card_html(
    card: Card,
    *,
    asset_root: Path | None = None,
    theme_css: str | None = None,
) -> str:
    """Render standalone `social_card.html` for `card` using the Foundation theme CSS."""
    theme_dir = Path(__file__).resolve().parent / "themes" / "foundation"
    env = Environment(loader=FileSystemLoader(str(theme_dir)))
    template = env.get_template("social_card.html")

    css = theme_css if theme_css is not None else _load_compiled_theme_css()
    # Rewrite relative font URLs to absolute file:// paths so headless Chrome loads bundled fonts
    static_dir = (theme_dir / "static").resolve()
    css = css.replace("url(../fonts/", f"url({static_dir.as_uri()}/fonts/")
    css = css.replace('url("../fonts/', f'url("{static_dir.as_uri()}/fonts/')

    article = card.to_template_dict()

    # Inline SVG hero / medallion directly if given local file paths
    if asset_root is not None:
        for key_uri, key_svg in (("image", "excerpt_svg_content"), ("emblem", "emblem_svg")):
            val = str(article.get(key_uri) or "").strip()
            if val and not article.get(key_svg):
                cand = Path(val) if Path(val).is_absolute() else (asset_root / val.lstrip("/"))
                if cand.is_file() and cand.suffix.lower() == ".svg":
                    article[key_svg] = _read_inline_svg(cand, as_thumbnail=False)

    def pathto(otheruri: str, resource: bool = False, baseuri: str | None = None) -> str:
        if not otheruri:
            return ""
        if otheruri.startswith(("http://", "https://", "data:", "file://")):
            return otheruri
        if asset_root is not None:
            cand = Path(otheruri) if Path(otheruri).is_absolute() else (asset_root / otheruri.lstrip("/"))
            if cand.is_file():
                return cand.resolve().as_uri()
        return otheruri

    return template.render(article=article, theme_css=css, pathto=pathto)


def _card_signature(html_text: str) -> str:
    return hashlib.sha256(html_text.encode("utf-8")).hexdigest()[:16]


def capture_social_card_png(
    card: Card,
    output_path: Path,
    *,
    asset_root: Path | None = None,
    force: bool = False,
    width: int = SOCIAL_WIDTH,
    height: int = SOCIAL_HEIGHT,
    chrome_bin: str | None = None,
) -> bool:
    """Render `card` with Foundation HTML+CSS and capture a `1280×640` PNG via headless Chrome.

    Returns `True` if a new PNG was written, `False` if skipped (unchanged cache hit).
    """
    html_text = render_social_card_html(card, asset_root=asset_root)
    sig = _card_signature(html_text)
    sig_file = output_path.with_suffix(output_path.suffix + ".sha")

    if output_path.is_file() and not force:
        if sig_file.is_file() and sig_file.read_text(encoding="utf-8").strip() == sig:
            return False
        if not force and not sig_file.is_file():
            # Existing committed banner without hash: preserve unless --force
            return False

    browser = chrome_bin or find_chrome_binary()
    if not browser:
        raise RuntimeError(
            "No local Chrome/Chromium binary found for HTML social card capture. "
            "Install google-chrome or chromium locally."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="photon_social_") as tmpdir:
        tmp = Path(tmpdir)
        html_file = tmp / "social_card.html"
        profile_dir = tmp / "chrome-profile"
        crash_dir = tmp / "chrome-crashes"
        profile_dir.mkdir(parents=True, exist_ok=True)
        crash_dir.mkdir(parents=True, exist_ok=True)
        html_file.write_text(html_text, encoding="utf-8")

        env = dict(os.environ)
        env["HOME"] = str(tmp)
        env["XDG_CONFIG_HOME"] = str(tmp / "xdg-config")
        env["XDG_CACHE_HOME"] = str(tmp / "xdg-cache")

        # Pad capture window height to absorb Chrome's headless chrome-frame delta,
        # then crop cleanly to exact `(width, height)` for OS-independent full-bleed output.
        capture_h = height + 160
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-crash-reporter",
            "--force-dark-mode",
            "--hide-scrollbars",
            f"--user-data-dir={profile_dir}",
            f"--crash-dumps-dir={crash_dir}",
            f"--window-size={width},{capture_h}",
            f"--screenshot={output_path.resolve()}",
            html_file.resolve().as_uri(),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30, env=env)
        if proc.returncode != 0 or not output_path.is_file():
            raise RuntimeError(
                f"Headless Chrome capture failed (rc={proc.returncode}): {proc.stderr.strip()}"
            )

    from PIL import Image

    with Image.open(output_path) as im:
        cropped = im.crop((0, 0, width, height)).convert("RGB")
        cropped.save(output_path, format="PNG", optimize=True)

    sig_file.write_text(sig + "\n", encoding="utf-8")
    return True


def build_social_card_from_params(
    *,
    org_brand: str,
    repo_slug: str,
    title: str,
    overline: str = "",
    subtitle: str = "",
    emblem_path: Path | None = None,
    hero_path: Path | None = None,
    site_domain: str = "",
) -> Card:
    """Build a `Card` payload for `generate_social_banner` / `publish social-banner`."""
    kicker = f"{org_brand.upper()} • {repo_slug}"
    hero_str = str(hero_path.resolve()) if hero_path and hero_path.is_file() else ""
    emblem_str = str(emblem_path.resolve()) if emblem_path and emblem_path.is_file() else ""

    # If only one graphic was discovered, place it in the larger hero slot
    if not hero_str and emblem_str:
        hero_str = emblem_str

    return Card(
        id=f"{repo_slug}:social",
        docname="index",
        title=title,
        type="social",
        kicker=kicker,
        subtitle=overline,
        description=subtitle,
        description_html=f"<p>{subtitle}</p>" if subtitle else "",
        emblem=emblem_str,
        image=hero_str,
        site_url=site_domain or f"{org_brand.lower()}.github.io/{repo_slug}",
    )


def load_cards_manifest_for_repo(repo_root: Path) -> dict[str, Any] | None:
    """Load `docs/cards.json` from `repo_root` if already built."""
    manifest = repo_root / "docs" / "cards.json"
    if manifest.is_file():
        try:
            return json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None
