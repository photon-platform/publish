"""Social media metadata (OpenGraph / Twitter Cards), A-Z <title> formatting, and 1200x630 sharing banners."""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from docutils import nodes

BANNER_WIDTH = 1200
BANNER_HEIGHT = 630

_MINOR_TITLE_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "da",
    "de",
    "del",
    "della",
    "der",
    "des",
    "di",
    "du",
    "et",
    "for",
    "from",
    "in",
    "la",
    "le",
    "les",
    "of",
    "on",
    "or",
    "sur",
    "the",
    "to",
    "und",
    "van",
    "von",
    "with",
    "zu",
    "zur",
}

_ROMAN_NUMERAL_RE = re.compile(
    r"^(?:M{0,3})(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$"
)


def _smart_title_case_if_all_caps(text: str) -> str:
    """Normalize ALL-CAPS titles (like 'ENCYCLOPEDIA OF TRIANGLE CENTERS') to clean Title Case."""
    cleaned = (text or "").strip()
    alpha_chars = [c for c in cleaned if c.isalpha()]
    if len(alpha_chars) < 4 or not all(c.isupper() for c in alpha_chars):
        return cleaned

    words = cleaned.split()
    out: list[str] = []
    for idx, word in enumerate(words):
        core = word.strip(".,:;()[]'\"“”‘’—–-")
        if core and len(core) <= 6 and _ROMAN_NUMERAL_RE.match(core):
            out.append(word)
            continue
        low = word.lower()
        if idx > 0 and idx < len(words) - 1 and low in _MINOR_TITLE_WORDS:
            out.append(low)
        else:
            out.append(low.capitalize())
    return " ".join(out)


def _strip_brand_prefix(raw: str, org_name: str = "", repo_name: str = "") -> str:
    """Strip redundant 'GEOMETOR • ' or 'PHOTON • ' prefixes from a title string."""
    val = (raw or "").strip()
    if not val:
        return ""
    val = re.sub(r"^(?:GEOMETOR|PHOTON)\s*[•·\-—:|]\s*", "", val, flags=re.IGNORECASE).strip()
    if org_name:
        pat = rf"^{re.escape(org_name)}\s*[•·\-—:|]\s*"
        val = re.sub(pat, "", val, flags=re.IGNORECASE).strip()
    return val


def resolve_org_brand(env: Any, context: dict[str, Any] | None = None) -> str:
    """Return canonical uppercase organization brand ('GEOMETOR' or 'PHOTON')."""
    cfg = getattr(env, "config", None)
    ctx = context or {}
    org_raw = str(
        ctx.get("org_name")
        or getattr(cfg, "org_name", "")
        or getattr(cfg, "org", "")
        or "GEOMETOR"
    ).strip()
    low = org_raw.lower()
    if "geometor" in low:
        return "GEOMETOR"
    if "photon" in low:
        return "PHOTON"
    return org_raw.upper() if len(org_raw) <= 12 else org_raw


def resolve_site_base_url(env: Any, project_root: Path | None = None) -> str:
    """Resolve canonical HTTPS base URL from CNAME or Sphinx html_baseurl."""
    cfg = getattr(env, "config", None)
    if project_root is None:
        srcdir = getattr(env, "srcdir", None)
        if srcdir:
            project_root = Path(srcdir).resolve().parent

    if project_root is not None:
        for cname_cand in (project_root / "docsrc" / "CNAME", project_root / "CNAME"):
            if cname_cand.is_file():
                domain = cname_cand.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
                if domain and domain[0].strip():
                    host = domain[0].strip().removeprefix("https://").removeprefix("http://").rstrip("/")
                    return f"https://{host}"

    for attr in ("html_baseurl", "html_base_url", "blog_baseurl"):
        val = str(getattr(cfg, attr, "") or "").strip().rstrip("/")
        if val.startswith(("http://", "https://")):
            return val

    org = str(getattr(cfg, "org", "") or "geometor").strip()
    repo = str(getattr(cfg, "repo", "") or (project_root.name if project_root else "")).strip()
    if org and repo:
        return f"https://{org}.github.io/{repo}"
    return "https://geometor.com"


def resolve_site_human_title(env: Any, context: dict[str, Any] | None = None) -> str:
    """Resolve the human-first site name (e.g. 'Fra Luca Pacioli', 'Encyclopedia of Triangle Centers')."""
    ctx = context or {}
    cfg = getattr(env, "config", None)
    master_doc = getattr(cfg, "master_doc", "index") if cfg else "index"
    org_brand = resolve_org_brand(env, ctx)
    repo_name = str(ctx.get("repo_name") or getattr(cfg, "repo_name", "") or getattr(cfg, "repo", "")).strip()

    # 1. Explicit :site_title: in master_doc metadata or conf.py `site_title`
    master_meta = (getattr(env, "metadata", {}) or {}).get(master_doc, {}) or {}
    explicit_site = str(
        master_meta.get("site_title")
        or getattr(cfg, "site_title", "")
        or ctx.get("site_title")
        or ""
    ).strip()
    if explicit_site:
        cleaned_exp = _strip_brand_prefix(explicit_site, org_brand, repo_name)
        if cleaned_exp and cleaned_exp.lower() != repo_name.lower():
            return _smart_title_case_if_all_caps(cleaned_exp)

    # 2. Master doc H1 title if it is already a real human title (not 'GEOMETOR • slug' or raw slug)
    titles = getattr(env, "titles", {}) or {}
    if master_doc in titles and titles[master_doc] is not None:
        h1_raw = titles[master_doc].astext().strip()
        h1_clean = _strip_brand_prefix(h1_raw, org_brand, repo_name)
        h1_clean = re.sub(r"^the\s+works\s+of\s+", "", h1_clean, flags=re.IGNORECASE).strip()
        if h1_clean and h1_clean.lower() != repo_name.lower():
            return _smart_title_case_if_all_caps(h1_clean)

    # 3. conf.py project / html_title if customized beyond 'GEOMETOR • repo'
    for cand_raw in (
        str(getattr(cfg, "project", "") or ""),
        str(getattr(cfg, "html_title", "") or ""),
        str(ctx.get("docstitle") or ""),
    ):
        cand_clean = _strip_brand_prefix(cand_raw, org_brand, repo_name)
        if cand_clean and cand_clean.lower() != repo_name.lower():
            return _smart_title_case_if_all_caps(cand_clean)

    # 4. Clean Title-Cased fallback from repo slug
    if repo_name:
        return repo_name.replace("-", " ").replace("_", " ").title()
    return org_brand


def _clean_text_snippet(raw: str, max_len: int = 195) -> str:
    """Normalize whitespace and truncate on a clean word boundary."""
    txt = re.sub(r"\s+", " ", (raw or "")).strip()
    txt = txt.replace("¶", "").strip()
    if len(txt) <= max_len:
        return txt
    cut = txt[: max_len - 1].rsplit(" ", 1)[0].rstrip(".,;:—–-")
    return f"{cut}…"


def extract_page_description(
    env: Any,
    pagename: str,
    doctree: nodes.document | None,
    context: dict[str, Any],
) -> str:
    """Extract a clean 160-200 character social description for `pagename`."""
    meta = (getattr(env, "metadata", {}) or {}).get(pagename, {}) or {}
    for key in ("description", "excerpt", "summary"):
        val = str(meta.get(key) or "").strip()
        if val:
            return _clean_text_snippet(val)

    if doctree is not None and hasattr(doctree, "findall"):
        # 1. Proposition enunciation takes priority on proposition pages
        for container in doctree.findall(nodes.Element):
            classes = container.get("classes", []) if hasattr(container, "get") else []
            if "enunciation" in classes:
                txt = container.astext().strip()
                if txt:
                    return _clean_text_snippet(txt)

        # 2. First substantive body paragraph (skipping 'the works of' overline & title-page table)
        rubric_txt = ""
        for p in doctree.findall(nodes.rubric):
            cand = p.astext().strip()
            if cand and cand.lower() != "the works of":
                rubric_txt = cand
                break

        for p in doctree.findall(nodes.paragraph):
            parent_classes: set[str] = set()
            anc = p.parent
            while anc is not None:
                if hasattr(anc, "get"):
                    parent_classes.update(anc.get("classes", []))
                anc = getattr(anc, "parent", None)
            if parent_classes & {"author-overline", "title-page", "folio-milestone", "caption"}:
                continue
            txt = p.astext().strip()
            if len(txt) >= 25 and txt.lower() != "the works of":
                return _clean_text_snippet(txt)

        if rubric_txt:
            return _clean_text_snippet(rubric_txt)

    site_human = resolve_site_human_title(env, context)
    org_brand = resolve_org_brand(env, context)
    book_title = str(context.get("book_title") or "").strip()
    if book_title:
        return _clean_text_snippet(f"{book_title} — Digital Scriptorium edition in {site_human} ({org_brand}).")
    return _clean_text_snippet(f"Semantic digital library and exact geometric reconstructions for {site_human} ({org_brand}).")


def build_social_and_title_context(
    app: Any,
    pagename: str,
    context: dict[str, Any],
    doctree: nodes.document | None,
) -> dict[str, Any]:
    """Compute bookmark-friendly `page_browser_title` and OpenGraph/Twitter `<head>` context."""
    env = app.env
    cfg = getattr(env, "config", None)
    master_doc = getattr(cfg, "master_doc", "index") if cfg else "index"
    srcdir = Path(getattr(env, "srcdir", ".")).resolve()
    project_root = srcdir.parent

    org_brand = resolve_org_brand(env, context)
    site_human = resolve_site_human_title(env, context)
    base_url = resolve_site_base_url(env, project_root=project_root)

    raw_page_title = html.unescape(re.sub(r"<[^>]+>", "", str(context.get("title") or ""))).strip()
    clean_page_title = _smart_title_case_if_all_caps(
        _strip_brand_prefix(raw_page_title, org_brand, str(context.get("repo_name") or ""))
    )

    is_book = bool(context.get("is_book_page"))
    book_root = str(context.get("book_root") or "")
    book_title = _smart_title_case_if_all_caps(str(context.get("book_title") or "").strip())
    canonical_id = str(context.get("canonical_id") or "").strip()
    clean_cid = re.sub(
        r"[._-](?:commentary|notes|summary|folio)$", "", canonical_id, flags=re.IGNORECASE
    ).strip()

    # 1. Browser <title> & og:title (A-to-Z bookmark-friendly: never prefixed with 'GEOMETOR • ')
    if pagename == master_doc:
        browser_title = f"{site_human} • {org_brand}"
        og_title = browser_title
        og_type = "website"
    elif is_book and pagename == book_root and book_root != master_doc:
        disp_book = book_title or clean_page_title or site_human
        if site_human.lower() in disp_book.lower():
            browser_title = f"{disp_book} • {org_brand}"
        else:
            browser_title = f"{disp_book} — {site_human} • {org_brand}"
        og_title = browser_title
        og_type = "book"
    elif is_book:
        short_book = book_title.split(":", 1)[0].split("—", 1)[0].strip() if book_title else site_human
        leaf_head = clean_page_title or clean_cid or site_human
        if clean_cid and clean_cid.lower() not in leaf_head.lower():
            leaf_head = f"{clean_cid}: {leaf_head}"
        browser_title = f"{leaf_head} — {short_book} • {org_brand}"
        og_title = browser_title
        og_type = "article"
    else:
        sec_title = clean_page_title or pagename.split("/")[-1].replace("-", " ").title()
        if sec_title.lower() == site_human.lower():
            browser_title = f"{site_human} • {org_brand}"
        else:
            browser_title = f"{sec_title} — {site_human} • {org_brand}"
        og_title = browser_title
        og_type = "article"

    # 2. Canonical Page URL
    if pagename == master_doc:
        canonical_url = f"{base_url}/"
    elif pagename.endswith("/index"):
        canonical_url = f"{base_url}/{pagename[:-5]}"
    else:
        target_uri = f"{pagename}.html"
        if hasattr(app, "builder") and hasattr(app.builder, "get_target_uri"):
            import contextlib

            with contextlib.suppress(AttributeError, KeyError, ValueError):
                target_uri = app.builder.get_target_uri(pagename)
        canonical_url = f"{base_url}/{target_uri.lstrip('/')}"

    # 3. 3-Tier Dedicated Sharing Banner Resolution (_static/social/*.png -> _static/logo.png)
    page_meta = (getattr(env, "metadata", {}) or {}).get(pagename, {}) or {}
    root_meta = (getattr(env, "metadata", {}) or {}).get(book_root, {}) if book_root else {}
    explicit_social = str(
        page_meta.get("social_image") or (root_meta or {}).get("social_image") or ""
    ).strip()

    chosen_rel = ""
    img_w, img_h = BANNER_WIDTH, BANNER_HEIGHT
    candidates: list[str] = []
    if explicit_social:
        candidates.append(explicit_social.lstrip("/"))
    if is_book and book_root and book_root != master_doc:
        book_slug = book_root.split("/", 1)[0]
        candidates.append(f"_static/social/{book_slug}.png")
    candidates.append("_static/social/banner.png")

    for rel_cand in candidates:
        disk_cand = srcdir / rel_cand
        if disk_cand.is_file():
            chosen_rel = rel_cand
            break

    if not chosen_rel:
        chosen_rel = "_static/logo.png"
        img_w, img_h = 512, 512

    social_image_url = f"{base_url}/{chosen_rel.lstrip('/')}"
    description = extract_page_description(env, pagename, doctree, context)

    return {
        "site_human_title": site_human,
        "org_brand": org_brand,
        "page_browser_title": browser_title,
        "canonical_url": canonical_url,
        "social_title": og_title,
        "social_description": description,
        "social_type": og_type,
        "social_site_name": org_brand,
        "social_image_url": social_image_url,
        "social_image_width": img_w,
        "social_image_height": img_h,
        "social_image_alt": f"{site_human} — {org_brand}",
    }


def _load_font(candidates: list[str], size: int) -> Any:
    """Load the first available TrueType/OpenType font at `size`."""
    from PIL import ImageFont

    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_lines(draw: Any, text: str, font: Any, max_width: int, max_lines: int = 3) -> list[str]:
    """Greedy word-wrap `text` within `max_width` pixels."""
    words = (text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
    used_words = sum(len(ln.split()) for ln in lines)
    rem = " ".join(words[used_words:])
    if rem:
        while draw.textbbox((0, 0), rem, font=font)[2] > max_width and " " in rem:
            rem = rem.rsplit(" ", 1)[0] + "…"
        lines.append(rem)
    return lines[:max_lines]


def _find_best_emblem_image(docsrc_dir: Path, subtree_slug: str | None = None) -> Path | None:
    """Find a representative diagram/plate in `docsrc/<subtree_slug>` (or fallback to `_static/logo.png`)."""
    search_roots: list[Path] = []
    if subtree_slug and (docsrc_dir / subtree_slug).is_dir():
        search_roots.append(docsrc_dir / subtree_slug)
    search_roots.append(docsrc_dir)

    for root in search_roots:
        # Prefer curated .svg geometric diagrams first, then .png plates (excluding social/ and favicon)
        for pattern in ("*.svg", "*.png"):
            for p in sorted(root.rglob(pattern)):
                rel_parts = p.relative_to(docsrc_dir).parts
                if "_static" in rel_parts and "social" in rel_parts:
                    continue
                if p.name.startswith(".") or "logo" in p.name.lower() or "favicon" in p.name.lower():
                    continue
                if p.stat().st_size > 350:
                    return p

    logo = docsrc_dir / "_static" / "logo.png"
    return logo if logo.is_file() else None


def _rasterize_emblem(asset_path: Path, box_size: int = 390) -> Any | None:
    """Load or rasterize `asset_path` (`.svg` or `.png`) into a `box_size` RGBA Pillow Image."""
    import tempfile

    from PIL import Image

    if asset_path.suffix.lower() == ".svg":
        inkscape = shutil.which("inkscape")
        if not inkscape:
            return None
        svg_txt = asset_path.read_text(encoding="utf-8", errors="ignore")
        # Force dark-mode foreground variables to warm ivory/gold for the dark sharing card
        dark_override = (
            "<style>"
            ":root, svg { --geom-fg: #ebe4d8 !important; --book-text: #ebe4d8 !important; "
            "--geom-point-stroke: #18181b !important; }"
            "</style>"
        )
        if "</svg>" in svg_txt:
            svg_txt = svg_txt.replace("</svg>", f"{dark_override}</svg>", 1)
        with tempfile.TemporaryDirectory() as tmpd:
            tmp_svg = Path(tmpd) / "emblem.svg"
            tmp_png = Path(tmpd) / "emblem.png"
            tmp_svg.write_text(svg_txt, encoding="utf-8")
            proc = subprocess.run(
                [
                    inkscape,
                    str(tmp_svg),
                    "--export-type=png",
                    f"--export-filename={tmp_png}",
                    f"--export-width={box_size * 2}",
                ],
                capture_output=True,
                timeout=15,
                check=False,
            )
            if proc.returncode == 0 and tmp_png.is_file():
                im = Image.open(tmp_png).convert("RGBA")
                im.thumbnail((box_size, box_size), Image.Resampling.LANCZOS)
                return im
        return None

    try:
        im = Image.open(asset_path).convert("RGBA")
        im.thumbnail((box_size, box_size), Image.Resampling.LANCZOS)
        return im
    except OSError:
        return None


def generate_social_banner(
    output_path: Path,
    *,
    org_brand: str,
    repo_slug: str,
    title: str,
    overline: str = "",
    subtitle: str = "",
    emblem_path: Path | None = None,
    site_domain: str = "",
    force: bool = False,
) -> bool:
    """Render a dedicated 1200x630 obsidian-vellum & gold social sharing PNG banner."""
    if output_path.is_file() and not force:
        return False

    from PIL import Image, ImageDraw

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (BANNER_WIDTH, BANNER_HEIGHT), (24, 24, 27, 255))
    draw = ImageDraw.Draw(canvas)

    # Subtle layered architectural frame (golden-section proportions: 742px text | 458px emblem)
    draw.rectangle([22, 22, BANNER_WIDTH - 23, BANNER_HEIGHT - 23], outline=(62, 57, 50, 255), width=1)
    draw.rectangle([30, 30, BANNER_WIDTH - 31, BANNER_HEIGHT - 31], outline=(212, 175, 55, 95), width=1)
    split_x = 738
    draw.line([(split_x, 54), (split_x, BANNER_HEIGHT - 54)], fill=(62, 57, 50, 190), width=1)

    # Corner gold ticks
    for cx, cy, dx, dy in (
        (30, 30, 18, 18),
        (BANNER_WIDTH - 31, 30, -18, 18),
        (30, BANNER_HEIGHT - 31, 18, -18),
        (BANNER_WIDTH - 31, BANNER_HEIGHT - 31, -18, -18),
    ):
        draw.line([(cx, cy), (cx + dx, cy)], fill=(232, 184, 90, 220), width=2)
        draw.line([(cx, cy), (cx, cy + dy)], fill=(232, 184, 90, 220), width=2)

    serif_bold_paths = [
        "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]
    serif_italic_paths = [
        "/usr/share/fonts/truetype/noto/NotoSerif-Italic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ]
    serif_reg_paths = [
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    sans_paths = [
        "/usr/share/fonts/opentype/fira/FiraSansCondensed-Medium.otf",
        "/usr/share/fonts/opentype/fira/FiraSans-Medium.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    ]

    font_kicker = _load_font(sans_paths, 21)
    font_overline = _load_font(serif_italic_paths, 26)
    font_sub = _load_font(serif_reg_paths, 24)
    font_url = _load_font(sans_paths, 18)

    left_x = 68
    max_text_w = split_x - left_x - 44

    # 1. Brand Kicker: GEOMETOR • <repo>
    kicker = f"{org_brand.upper()}  •  {repo_slug}"
    draw.text((left_x, 66), kicker, font=font_kicker, fill=(232, 184, 90, 245))

    # 2. Adaptive Title Size (52 -> 44 -> 38)
    clean_title = _smart_title_case_if_all_caps(title.strip())
    font_title = _load_font(serif_bold_paths, 52 if len(clean_title) <= 34 else (44 if len(clean_title) <= 65 else 38))
    title_lines = _wrap_lines(draw, clean_title, font_title, max_text_w, max_lines=3)

    cur_y = 178
    if overline.strip():
        draw.text((left_x, cur_y), overline.strip(), font=font_overline, fill=(176, 168, 156, 235))
        cur_y += 42

    for line in title_lines:
        draw.text((left_x, cur_y), line, font=font_title, fill=(244, 239, 230, 255))
        bbox = draw.textbbox((0, 0), line, font=font_title)
        cur_y += (bbox[3] - bbox[1]) + 14

    if subtitle.strip():
        cur_y += 14
        sub_lines = _wrap_lines(draw, subtitle.strip(), font_sub, max_text_w, max_lines=3)
        for sline in sub_lines:
            draw.text((left_x, cur_y), sline, font=font_sub, fill=(184, 176, 164, 235))
            cur_y += 33

    # Footer URL
    footer_label = site_domain or f"{org_brand.lower()}.github.io/{repo_slug}"
    draw.text((left_x, BANNER_HEIGHT - 74), footer_label, font=font_url, fill=(132, 125, 115, 220))

    # Right Emblem Panel (centered at (969, 315))
    if emblem_path and emblem_path.is_file():
        emblem = _rasterize_emblem(emblem_path, box_size=376)
        if emblem is not None:
            ex = split_x + (BANNER_WIDTH - 30 - split_x - emblem.width) // 2
            ey = (BANNER_HEIGHT - emblem.height) // 2
            canvas.alpha_composite(emblem, dest=(max(split_x + 16, ex), max(46, ey)))

    out_rgb = canvas.convert("RGB")
    out_rgb.save(output_path, format="PNG", optimize=True)
    return True


def generate_repo_social_banners(repo_root: str | Path, force: bool = False) -> dict[str, Any]:
    """Generate `docsrc/_static/social/banner.png` and per-book `<book_slug>.png` for a repository."""
    from .directives.collection import peek_metadata

    root = Path(repo_root).expanduser().resolve()
    docsrc = root / "docsrc"
    if not docsrc.is_dir():
        return {"ok": False, "repo": str(root), "error": "docsrc/ not found"}

    repo_slug = root.name
    org_slug = root.parent.name if root.parent.name in ("geometor", "photon-platform") else "geometor"
    org_brand = "PHOTON" if "photon" in org_slug else "GEOMETOR"

    # Extract site_title / H1 and lead paragraph from docsrc/index.rst (+ intro.rst)
    idx_rst = docsrc / "index.rst"
    idx_meta = peek_metadata(str(idx_rst)) if idx_rst.is_file() else {}
    idx_text = idx_rst.read_text(encoding="utf-8", errors="ignore") if idx_rst.is_file() else ""
    intro_rst = docsrc / "intro.rst"
    if intro_rst.is_file():
        idx_text = idx_text + "\n" + intro_rst.read_text(encoding="utf-8", errors="ignore")

    # Parse conf.py for explicit site_title if present
    conf_site_title = ""
    conf_py = docsrc / "conf.py"
    if conf_py.is_file():
        conf_txt = conf_py.read_text(encoding="utf-8", errors="ignore")
        m_st = re.search(r'^site_title\s*=\s*["\']([^"\']+)["\']', conf_txt, re.MULTILINE)
        if m_st:
            conf_site_title = m_st.group(1).strip()

    h1_title = ""
    lines = idx_text.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^[=\-~^]{3,}\s*$", ln.strip()) and i > 0 and lines[i - 1].strip():
            cand = lines[i - 1].strip()
            if not cand.startswith((":", "..")):
                h1_title = cand
                break

    site_title = (
        idx_meta.get("site_title")
        or conf_site_title
        or _strip_brand_prefix(h1_title, org_brand, repo_slug)
        or repo_slug.replace("-", " ").title()
    )
    if site_title.lower() == repo_slug.lower():
        site_title = repo_slug.replace("-", " ").title()

    has_works_overline = "the works of" in idx_text.lower()
    overline = "the works of" if has_works_overline else ""

    # Find first clean descriptive sentence
    subtitle = idx_meta.get("description", "")
    if not subtitle:
        for para in re.split(r"\n\s*\n", idx_text):
            p = para.strip()
            if (
                not p
                or p.startswith(("..", ":", "="))
                or "\n===" in p
                or "\n---" in p
                or p.lower() == "the works of"
            ):
                continue
            clean_p = re.sub(r":[a-zA-Z0-9_+-]+:`([^`<]+)(?:\s*<[^>]+>)?`", r"\1", p)
            clean_p = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_p)
            clean_p = re.sub(r"\*([^*]+)\*", r"\1", clean_p)
            clean_p = re.sub(r"``([^`]+)``", r"\1", clean_p)
            clean_p = _clean_text_snippet(clean_p, max_len=150)
            if len(clean_p) >= 24:
                subtitle = clean_p
                break

    cname_domain = ""
    for cname in (docsrc / "CNAME", root / "CNAME"):
        if cname.is_file():
            raw_c = cname.read_text(encoding="utf-8", errors="ignore").strip()
            if raw_c:
                cname_domain = raw_c.splitlines()[0].strip()
                break

    social_dir = docsrc / "_static" / "social"
    created: list[str] = []
    skipped: list[str] = []

    root_emblem = _find_best_emblem_image(docsrc)
    main_banner = social_dir / "banner.png"
    if generate_social_banner(
        main_banner,
        org_brand=org_brand,
        repo_slug=repo_slug,
        title=site_title,
        overline=overline,
        subtitle=subtitle,
        emblem_path=root_emblem,
        site_domain=cname_domain,
        force=force,
    ):
        created.append(str(main_banner.relative_to(root)))
    else:
        skipped.append(str(main_banner.relative_to(root)))

    # Also generate per-book banners for any top-level `docsrc/<book_slug>/index.rst` with `:layout: book`
    for sub in sorted(docsrc.iterdir()):
        if not sub.is_dir() or sub.name.startswith(("_", ".")) or sub.name in {
            "about",
            "usage",
            "log",
            "modules",
            "demos",
            "todos",
        }:
            continue
        sub_idx = sub / "index.rst"
        if not sub_idx.is_file():
            continue
        bmeta = peek_metadata(str(sub_idx))
        if bmeta.get("layout") != "book" and "book_title" not in bmeta and bmeta.get("type") != "book":
            continue
        btitle = bmeta.get("book_title") or bmeta.get("nav_title") or sub.name.replace("_", " ").title()
        bauthor = bmeta.get("author") or site_title
        bsub = bmeta.get("description") or bmeta.get("book_subtitle") or ""
        bemblem = _find_best_emblem_image(docsrc, subtree_slug=sub.name)
        book_banner = social_dir / f"{sub.name}.png"
        if generate_social_banner(
            book_banner,
            org_brand=org_brand,
            repo_slug=repo_slug,
            title=btitle,
            overline=bauthor if bauthor.lower() != btitle.lower() else "",
            subtitle=bsub,
            emblem_path=bemblem,
            site_domain=cname_domain,
            force=force,
        ):
            created.append(str(book_banner.relative_to(root)))
        else:
            skipped.append(str(book_banner.relative_to(root)))

    return {
        "ok": True,
        "repo": root.name,
        "created": created,
        "skipped": skipped,
    }
