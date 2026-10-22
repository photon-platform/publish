"""Folio discovery, metadata parsing, and statistics aggregation.

Operates exclusively on `resources/` directories containing `volume_*` folders.
"""

from __future__ import annotations

import html as html_lib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import markdown as _markdown
except ImportError:
    _markdown = None

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

try:
    from pygments import highlight as _pygments_highlight
    from pygments.formatters import HtmlFormatter as _HtmlFormatter
    from pygments.lexers import PythonLexer as _PythonLexer, XmlLexer as _XmlLexer
    from pygments.styles import get_style_by_name as _get_style_by_name

    try:
        _get_style_by_name("gruvbox-dark")
        PYGMENTS_STYLE = "gruvbox-dark"
    except Exception:
        PYGMENTS_STYLE = "monokai"

    _HTML_FORMATTER = _HtmlFormatter(style=PYGMENTS_STYLE, nowrap=False)
    PYGMENTS_CSS = _HTML_FORMATTER.get_style_defs(".highlight")
except ImportError:
    _pygments_highlight = None
    _HtmlFormatter = None
    _PythonLexer = None
    _XmlLexer = None
    PYGMENTS_STYLE = "gruvbox-dark"
    PYGMENTS_CSS = ""

from .rst_utils import parse_rst_frontmatter, render_rst_to_html


ROMAN_ORDER = {
    "volume_I": 1,
    "volume_II": 2,
    "volume_III": 3,
    "volume_IV": 4,
    "volume_V": 5,
    "volume_VI": 6,
    "volume_VII": 7,
    "volume_VIII": 8,
    "volume_IX": 9,
    "volume_X": 10,
}


def highlight_code_html(code: str, lang: str = "python") -> str:
    """Render code to syntax-highlighted HTML using Pygments (`gruvbox-dark`)."""
    if not code:
        return ""
    if _pygments_highlight is not None and _HtmlFormatter is not None:
        lexer = _PythonLexer() if lang == "python" else _XmlLexer()
        return _pygments_highlight(code, lexer, _HTML_FORMATTER)
    escaped = html_lib.escape(code)
    return f'<div class="highlight"><pre><code>{escaped}</code></pre></div>'


def parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown content."""
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            if _yaml is not None:
                try:
                    fm = _yaml.safe_load(parts[1]) or {}
                    return fm, parts[2].strip()
                except Exception:
                    pass
            # Simple fallback key: value parser if PyYAML is unavailable
            fm: Dict[str, Any] = {}
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip("'\"")
            return fm, parts[2].strip()
    return {}, md_text.strip()


def protect_math_for_markdown(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace LaTeX math spans with placeholders so Markdown doesn't mangle underscores or asterisks."""
    placeholders: Dict[str, str] = {}
    counter = 0

    def replace_match(match: re.Match) -> str:
        nonlocal counter
        key = f"@@MATH_PLACEHOLDER_{counter}@@"
        placeholders[key] = match.group(0)
        counter += 1
        return key

    text = re.sub(r"\$\$[\s\S]*?\$\$", replace_match, text)
    text = re.sub(r"\$[^\$\n]+?\$", replace_match, text)
    return text, placeholders


def restore_math_placeholders(html_str: str, placeholders: Dict[str, str]) -> str:
    """Restore LaTeX math spans into rendered HTML."""
    for key, val in placeholders.items():
        html_str = html_str.replace(key, val)
    return html_str


def fix_relative_media_urls(html_str: str, volume: str, rel_dir: str) -> str:
    """Rewrite relative image src attributes in rendered HTML to point to /media/."""
    prefix = f"/media/{volume}/{rel_dir}/" if rel_dir else f"/media/{volume}/"

    def repl(match: re.Match) -> str:
        src = match.group(1)
        if src.startswith(("http://", "https://", "/", "data:")):
            return match.group(0)
        clean_src = src.lstrip("./")
        return f'src="{prefix}{clean_src}"'

    return re.sub(r'src="([^"]+)"', repl, html_str)


def render_markdown_with_math(md_body: str, volume: str = "", rel_dir: str = "") -> str:
    """Render Markdown to HTML while preserving KaTeX math expressions and fixing image paths."""
    protected_text, placeholders = protect_math_for_markdown(md_body)
    if _markdown is not None:
        html_out = _markdown.markdown(
            protected_text,
            extensions=["extra", "tables", "sane_lists", "nl2br"],
        )
    else:
        escaped = html_lib.escape(protected_text)
        html_out = f"<p>{escaped}</p>"
    html_out = restore_math_placeholders(html_out, placeholders)
    if volume:
        html_out = fix_relative_media_urls(html_out, volume, rel_dir)
    return html_out


def render_rst_with_media(rst_body: str, volume: str = "", rel_dir: str = "") -> str:
    """Render reStructuredText to HTML and rewrite relative media URLs."""
    html_out = render_rst_to_html(rst_body)
    if volume:
        html_out = fix_relative_media_urls(html_out, volume, rel_dir)
    return html_out


def _has_volume_dirs(directory: Path) -> bool:
    """Return True if `directory` contains at least one `volume_*` directory or symlink."""
    if not directory.is_dir():
        return False
    try:
        return any(
            (child.is_dir() or child.is_symlink()) and child.name.startswith("volume_")
            for child in directory.iterdir()
        )
    except OSError:
        return False


def _has_folio_pngs(directory: Path) -> bool:
    """Return True if `directory` or its subdirectories contain 4-digit `<NNNN>.png` folio scans."""
    if not directory.is_dir():
        return False
    try:
        return any(
            re.match(r"^\d{4}\.png$", p.name)
            for p in directory.rglob("[0-9][0-9][0-9][0-9].png")
        )
    except OSError:
        return False


def discover_edition_root(root_path: Optional[Path] = None) -> Path:
    """Locate the edition or book root directory inside `resources/`.

    Never inspects `docsrc/`. Supports both multi-volume editions (`volume_*`)
    and single-volume book directories (`resources/<book>/`) containing folio PNGs.
    """
    base = Path(root_path).resolve() if root_path is not None else Path.cwd().resolve()

    # Case 1: `base` itself has `volume_*` directories
    if _has_volume_dirs(base):
        return base

    # Case 2: `base / "resources"` exists
    resources_dir = base / "resources"
    if resources_dir.is_dir():
        if _has_volume_dirs(resources_dir):
            return resources_dir
        vol_candidates = sorted(
            [
                d
                for d in resources_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and _has_volume_dirs(d)
            ],
            key=lambda p: p.name,
        )
        if vol_candidates:
            return vol_candidates[0]
        book_candidates = sorted(
            [
                d
                for d in resources_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and _has_folio_pngs(d)
            ],
            key=lambda p: p.name,
        )
        if book_candidates:
            return book_candidates[0]

    # Case 3: `base` itself is a book directory (not repo root or `resources`) with folio PNGs
    if base.is_dir() and base.name != "resources" and not (base / "resources").is_dir():
        if _has_folio_pngs(base):
            return base

    # Case 4: `base` is `resources/` or parent of an edition/book directory
    if base.is_dir():
        vol_candidates = sorted(
            [
                d
                for d in base.iterdir()
                if d.is_dir()
                and d.name != "docsrc"
                and not d.name.startswith(".")
                and _has_volume_dirs(d)
            ],
            key=lambda p: p.name,
        )
        if vol_candidates:
            return vol_candidates[0]
        book_candidates = sorted(
            [
                d
                for d in base.iterdir()
                if d.is_dir()
                and d.name != "docsrc"
                and not d.name.startswith(".")
                and _has_folio_pngs(d)
            ],
            key=lambda p: p.name,
        )
        if book_candidates:
            return book_candidates[0]

    # Fallback: return `resources_dir` if it exists, otherwise `base`
    return resources_dir if resources_dir.is_dir() else base


def infer_project_and_edition(
    edition_root: Path,
    project_title: Optional[str] = None,
    edition_label: Optional[str] = None,
) -> Tuple[str, str]:
    """Infer `(project_title, edition_label)` from the `resources/` path without reading `docsrc/`."""
    resolved = Path(edition_root).resolve()

    if not edition_label:
        if resolved.name == "resources":
            edition_label = "Resources"
        else:
            edition_label = resolved.name.replace("_", " ").title()

    if not project_title:
        # Determine repo directory: if parent is `resources`, repo is parent.parent
        if resolved.parent.name == "resources":
            repo_dir = resolved.parent.parent
        elif resolved.name == "resources":
            repo_dir = resolved.parent
        else:
            repo_dir = resolved.parent

        repo_name = repo_dir.name.replace("_", " ").title()
        org_name = repo_dir.parent.name.lower() if repo_dir.parent else ""
        if org_name == "geometor" or repo_dir.name.lower() in {"euclid", "hoenen", "pacioli", "elements", "model"}:
            project_title = f"GEOMETOR {repo_name}"
        else:
            project_title = repo_name

    return project_title, edition_label


class FolioScanner:
    """Scans `volume_*` or book directories under an edition root and indexes all folio assets."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = discover_edition_root(root_dir)
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._by_key: Dict[str, Dict[str, Any]] = {}

    def _get_volume_dir(self, vol_name: str) -> Path:
        """Resolve the filesystem directory for a volume or single-book identifier."""
        candidate = self.root_dir / vol_name
        if candidate.exists() and (candidate.is_dir() or candidate.is_symlink()):
            return candidate
        if vol_name == self.root_dir.name or not _has_volume_dirs(self.root_dir):
            return self.root_dir
        return candidate

    @property
    def volumes(self) -> List[Dict[str, str]]:
        """Discover `volume_*` directories dynamically, or treat the book directory itself as the unit."""
        if not self.root_dir.exists():
            return []
        found: List[Path] = []
        for child in self.root_dir.iterdir():
            if (child.is_dir() or child.is_symlink()) and child.name.startswith("volume_"):
                found.append(child)
        if found:
            found.sort(key=lambda p: (ROMAN_ORDER.get(p.name, 999), p.name))
            result = []
            for p in found:
                suffix = p.name.replace("volume_", "")
                result.append({"name": p.name, "label": f"Volume {suffix}"})
            return result

        if self.root_dir.name == "resources":
            books = sorted(
                [
                    child
                    for child in self.root_dir.iterdir()
                    if child.is_dir() and not child.name.startswith(".") and _has_folio_pngs(child)
                ],
                key=lambda p: p.name,
            )
            return [{"name": b.name, "label": b.name.replace("_", " ").title()} for b in books]

        if _has_folio_pngs(self.root_dir):
            return [
                {
                    "name": self.root_dir.name,
                    "label": self.root_dir.name.replace("_", " ").title(),
                }
            ]
        return []

    def scan(self, force: bool = False) -> List[Dict[str, Any]]:
        """Scan all volumes/books and return sorted list of folio metadata dicts."""
        if self._cache is not None and not force:
            return self._cache

        folios: List[Dict[str, Any]] = []
        by_key: Dict[str, Dict[str, Any]] = {}

        for vol_info in self.volumes:
            vol_name = vol_info["name"]
            vol_label = vol_info["label"]
            vol_dir = self._get_volume_dir(vol_name)
            if not vol_dir.exists():
                continue

            # Find all 4-digit PNG scan files in this volume (including symlinked volume dirs)
            png_files = sorted(vol_dir.rglob("[0-9][0-9][0-9][0-9].png"))
            for png_path in png_files:
                if not re.match(r"^\d{4}\.png$", png_path.name):
                    continue

                folio_num = png_path.stem
                parent_dir = png_path.parent
                rel_dir = "" if parent_dir == vol_dir else str(parent_dir.relative_to(vol_dir))
                media_dir = f"{vol_name}/{rel_dir}" if rel_dir else vol_name

                rst_path = parent_dir / f"{folio_num}.rst"
                md_path = parent_dir / f"{folio_num}.md"

                notes_rst_path = parent_dir / f"{folio_num}.notes.rst"
                notes_md_path = parent_dir / f"{folio_num}.notes.md"
                json_path = parent_dir / f"{folio_num}.json"

                has_rst = rst_path.exists()
                has_md_file = md_path.exists()
                has_md = has_rst or has_md_file
                transcription_format = "rst" if has_rst else ("md" if has_md_file else None)

                has_notes_rst = notes_rst_path.exists()
                has_notes_md = notes_md_path.exists()
                has_notes = has_notes_rst or has_notes_md
                notes_format = "rst" if has_notes_rst else ("md" if has_notes_md else None)

                has_json = json_path.exists()

                frontmatter: Dict[str, Any] = {}
                title = f"Folio {folio_num}"
                page = ""
                book_val = ""
                section_val = ""

                if has_rst:
                    try:
                        rst_text = rst_path.read_text(encoding="utf-8")
                        frontmatter, _ = parse_rst_frontmatter(rst_text)
                        title = str(frontmatter.get("title", title))
                        page = str(
                            frontmatter.get(
                                "page",
                                frontmatter.get(
                                    "original_folio",
                                    frontmatter.get("page_num", ""),
                                ),
                            )
                        )
                        book_val = str(frontmatter.get("book", ""))
                        section_val = str(frontmatter.get("section", ""))
                    except Exception:
                        pass
                elif has_md_file:
                    try:
                        md_text = md_path.read_text(encoding="utf-8")
                        frontmatter, _ = parse_frontmatter(md_text)
                        title = str(frontmatter.get("title", title))
                        page = str(
                            frontmatter.get(
                                "page",
                                frontmatter.get(
                                    "original_folio",
                                    frontmatter.get("page_num", ""),
                                ),
                            )
                        )
                        book_val = str(frontmatter.get("book", ""))
                        section_val = str(frontmatter.get("section", ""))
                    except Exception:
                        pass

                graphics: List[Dict[str, Any]] = []
                svg_count = 0
                py_count = 0
                json_meta: Dict[str, Any] = {}
                if has_json:
                    try:
                        json_meta = json.loads(json_path.read_text(encoding="utf-8"))
                        raw_graphics = json_meta.get("graphics", [])
                        for g in raw_graphics:
                            gid = g.get("id", "g1")
                            gfile = g.get("file", f"{folio_num}.{gid}.png")
                            gpath = parent_dir / gfile
                            svg_file = f"{folio_num}.{gid}.svg"
                            svg_path = parent_dir / svg_file
                            svg_exists = svg_path.exists()
                            if svg_exists:
                                svg_count += 1
                            py_file = f"{folio_num}.{gid}.py"
                            py_path = parent_dir / py_file
                            py_exists = py_path.exists()
                            if py_exists:
                                py_count += 1
                            graphics.append(
                                {
                                    "id": gid,
                                    "type": g.get("type", "diagram"),
                                    "file": gfile,
                                    "file_exists": gpath.exists(),
                                    "svg_file": svg_file,
                                    "svg_exists": svg_exists,
                                    "py_file": py_file,
                                    "py_exists": py_exists,
                                    "bbox": g.get("bbox", []),
                                    "caption": g.get("caption", ""),
                                    "white_point": g.get("white_point"),
                                }
                            )
                    except Exception:
                        pass

                if title == f"Folio {folio_num}" and json_meta.get("title"):
                    title = str(json_meta["title"])
                if not page:
                    page = str(
                        json_meta.get(
                            "original_folio",
                            json_meta.get("page_num", json_meta.get("page", "")),
                        )
                    )
                if not book_val:
                    book_val = str(json_meta.get("section", ""))

                # Determine logical section_path for grouping & display
                if rel_dir:
                    section_path = rel_dir
                else:
                    section_path = (
                        section_val
                        or str(json_meta.get("section_id", ""))
                        or str(json_meta.get("section", ""))
                        or book_val
                        or "general"
                    )

                parts = rel_dir.split("/") if rel_dir else [section_path]
                top_section = book_val or parts[0]
                sub_section = "/".join(parts[1:]) if len(parts) > 1 else ""

                scan_rel_path = f"{media_dir}/{png_path.name}"

                item = {
                    "key": f"{vol_name}:{folio_num}",
                    "volume": vol_name,
                    "volume_label": vol_label,
                    "folio": folio_num,
                    "folio_int": int(folio_num),
                    "rel_dir": rel_dir,
                    "media_dir": media_dir,
                    "section_path": section_path,
                    "book": top_section,
                    "subsection": sub_section,
                    "title": title,
                    "page": page,
                    "has_scan": True,
                    "has_md": has_md,
                    "has_rst": has_rst,
                    "transcription_format": transcription_format,
                    "has_notes": has_notes,
                    "notes_format": notes_format,
                    "has_json": has_json,
                    "graphics_count": len(graphics),
                    "has_graphics": len(graphics) > 0,
                    "missing_crops_count": sum(1 for g in graphics if not g["file_exists"]),
                    "svg_count": svg_count,
                    "has_svg": svg_count > 0,
                    "py_count": py_count,
                    "has_py": py_count > 0,
                    "graphics": graphics,
                    "scan_rel_path": scan_rel_path,
                    "frontmatter": frontmatter,
                }
                folios.append(item)
                by_key[item["key"]] = item

        folios.sort(key=lambda x: (ROMAN_ORDER.get(x["volume"], 99), x["folio_int"]))
        self._cache = folios
        self._by_key = by_key
        return folios

    def get_folio_detail(self, volume: str, folio: str) -> Optional[Dict[str, Any]]:
        """Get full details for a single folio, including rendered RST/Markdown and Notes."""
        self.scan()
        if folio.isdigit():
            folio = f"{int(folio):04d}"
        key = f"{volume}:{folio}"
        base_info = self._by_key.get(key)
        if not base_info and len(self.volumes) == 1:
            base_info = self._by_key.get(f"{self.volumes[0]['name']}:{folio}")
        if not base_info:
            self.scan(force=True)
            base_info = self._by_key.get(key)
            if not base_info and len(self.volumes) == 1:
                base_info = self._by_key.get(f"{self.volumes[0]['name']}:{folio}")
            if not base_info:
                return None

        res = dict(base_info)
        rel_dir = res["rel_dir"]
        vol_dir = self._get_volume_dir(res["volume"])
        full_parent = (vol_dir / rel_dir) if rel_dir else vol_dir

        rst_path = full_parent / f"{folio}.rst"
        md_path = full_parent / f"{folio}.md"
        notes_rst_path = full_parent / f"{folio}.notes.rst"
        notes_md_path = full_parent / f"{folio}.notes.md"
        json_path = full_parent / f"{folio}.json"

        res["has_rst"] = rst_path.exists()
        res["has_md"] = rst_path.exists() or md_path.exists()
        res["has_notes"] = notes_rst_path.exists() or notes_md_path.exists()
        res["has_json"] = json_path.exists()

        md_content = ""
        md_body = ""
        md_html = ""
        if rst_path.exists():
            try:
                md_content = rst_path.read_text(encoding="utf-8")
                fm, md_body = parse_rst_frontmatter(md_content)
                res["frontmatter"] = fm
                res["transcription_format"] = "rst"
                res["md_file_name"] = f"{folio}.rst"
                md_html = render_rst_with_media(md_body, res["volume"], rel_dir)
            except Exception as e:
                md_html = f"<p class='text-red-500'>Error reading RST: {e}</p>"
        elif md_path.exists():
            try:
                md_content = md_path.read_text(encoding="utf-8")
                fm, md_body = parse_frontmatter(md_content)
                res["frontmatter"] = fm
                res["transcription_format"] = "md"
                res["md_file_name"] = f"{folio}.md"
                md_html = render_markdown_with_math(md_body, res["volume"], rel_dir)
            except Exception as e:
                md_html = f"<p class='text-red-500'>Error reading markdown: {e}</p>"
        else:
            res["transcription_format"] = None
            res["md_file_name"] = f"{folio}.rst"

        notes_content = ""
        notes_html = ""
        if notes_rst_path.exists():
            try:
                notes_content = notes_rst_path.read_text(encoding="utf-8")
                res["notes_format"] = "rst"
                res["notes_file_name"] = f"{folio}.notes.rst"
                _, notes_body = parse_rst_frontmatter(notes_content)
                notes_html = render_rst_with_media(notes_body, res["volume"], rel_dir)
            except Exception as e:
                notes_html = f"<p class='text-red-500'>Error reading notes RST: {e}</p>"
        elif notes_md_path.exists():
            try:
                notes_content = notes_md_path.read_text(encoding="utf-8")
                res["notes_format"] = "md"
                res["notes_file_name"] = f"{folio}.notes.md"
                notes_html = render_markdown_with_math(notes_content, res["volume"], rel_dir)
            except Exception as e:
                notes_html = f"<p class='text-red-500'>Error reading notes: {e}</p>"
        else:
            res["notes_format"] = None
            res["notes_file_name"] = f"{folio}.notes.rst"

        json_content = ""
        json_data: Dict[str, Any] = {}
        if json_path.exists():
            try:
                json_content = json_path.read_text(encoding="utf-8")
                json_data = json.loads(json_content)
                raw_graphics = json_data.get("graphics", [])
                graphics = []
                svg_count = 0
                py_count = 0
                for g in raw_graphics:
                    gid = g.get("id", "g1")
                    gfile = g.get("file", f"{folio}.{gid}.png")
                    gpath = full_parent / gfile
                    svg_file = f"{folio}.{gid}.svg"
                    svg_path = full_parent / svg_file
                    svg_exists = svg_path.exists()
                    svg_content = ""
                    svg_highlighted_html = ""
                    if svg_exists:
                        svg_count += 1
                        try:
                            svg_content = svg_path.read_text(encoding="utf-8")
                            svg_highlighted_html = highlight_code_html(svg_content, lang="xml")
                        except Exception:
                            pass

                    py_file = f"{folio}.{gid}.py"
                    py_path = full_parent / py_file
                    py_exists = py_path.exists()
                    py_content = ""
                    py_highlighted_html = ""
                    if py_exists:
                        py_count += 1
                        try:
                            py_content = py_path.read_text(encoding="utf-8")
                            py_highlighted_html = highlight_code_html(py_content, lang="python")
                        except Exception:
                            pass

                    in_md_format = None
                    if md_content:
                        if re.search(rf"\.\.\s+(?:picture|image|figure)::\s+[^\n]*{re.escape(svg_file)}", md_content) or re.search(
                            rf"\]\([^\)]*{re.escape(svg_file)}\)", md_content
                        ):
                            in_md_format = "svg"
                        elif re.search(rf"\.\.\s+(?:picture|image|figure)::\s+[^\n]*{re.escape(gfile)}", md_content) or re.search(
                            rf"\]\([^\)]*{re.escape(gfile)}\)", md_content
                        ):
                            in_md_format = "png"

                    graphics.append(
                        {
                            "id": gid,
                            "type": g.get("type", "diagram"),
                            "file": gfile,
                            "file_exists": gpath.exists(),
                            "svg_file": svg_file,
                            "svg_exists": svg_exists,
                            "svg_content": svg_content,
                            "svg_highlighted_html": svg_highlighted_html,
                            "py_file": py_file,
                            "py_exists": py_exists,
                            "py_content": py_content,
                            "py_highlighted_html": py_highlighted_html,
                            "in_md_format": in_md_format,
                            "bbox": g.get("bbox", []),
                            "caption": g.get("caption", ""),
                            "white_point": g.get("white_point"),
                        }
                    )
                res["graphics"] = graphics
                res["graphics_count"] = len(graphics)
                res["svg_count"] = svg_count
                res["has_svg"] = svg_count > 0
                res["py_count"] = py_count
                res["has_py"] = py_count > 0
            except Exception:
                pass

        apparatus = self.get_apparatus()
        cites_reg = apparatus.get("citations", {})
        terms_reg = apparatus.get("glossary", {})
        persons_reg = apparatus.get("persons", {})

        folio_citations: Dict[str, Any] = {}
        folio_terms: Dict[str, Any] = {}
        folio_persons: Dict[str, Any] = {}
        combined_html = md_html + "\n" + notes_html
        combined_raw = md_content + "\n" + notes_content
        page_label = str(res["frontmatter"].get("page", folio))

        cite_keys = [html_lib.unescape(m.group(1)) for m in re.finditer(r'data-cite="([^"]+)"', combined_html)]
        for m in re.finditer(r":cite:`(?:[^`<]*<([^>]+)>|([^`]+))`", combined_raw):
            ck = (m.group(1) or m.group(2) or "").strip()
            if ck and ck not in cite_keys:
                cite_keys.append(ck)

        for ck in cite_keys:
            if ck in cites_reg:
                folio_citations[ck] = cites_reg[ck]
            else:
                parts = ck.split(":")
                wk = ":".join(parts[:2]) if len(parts) >= 2 else ck
                folio_citations[ck] = {
                    "key": ck,
                    "author": parts[0].replace("-", " ").title(),
                    "work": wk,
                    "locus": ":".join(parts[2:]) if len(parts) > 2 else "",
                    "occurrences": [{"volume": res["volume"], "folio": folio, "page": page_label}],
                    "work_occurrences": [{"volume": res["volume"], "folio": folio, "page": page_label}],
                }

        term_keys = [html_lib.unescape(m.group(1)) for m in re.finditer(r'data-term="([^"]+)"', combined_html)]
        for m in re.finditer(r":term:`(?:[^`<]*<([^>]+)>|([^`]+))`", combined_raw):
            tk = (m.group(1) or m.group(2) or "").strip()
            if tk and tk not in term_keys:
                term_keys.append(tk)

        for tk in term_keys:
            if tk in terms_reg:
                folio_terms[tk] = terms_reg[tk]
            else:
                folio_terms[tk] = {
                    "slug": tk,
                    "headword": tk.replace("-", " "),
                    "language": "Term",
                    "translation": tk.replace("-", " "),
                    "definition": "",
                    "occurrences": [{"volume": res["volume"], "folio": folio, "page": page_label}],
                }

        person_keys = [html_lib.unescape(m.group(1)) for m in re.finditer(r'data-person="([^"]+)"', combined_html)]
        for m in re.finditer(r":person:`(?:[^`<]*<([^>]+)>|([^`]+))`", combined_raw):
            pk = (m.group(1) or m.group(2) or "").strip()
            if pk and pk not in person_keys:
                person_keys.append(pk)

        for pk in person_keys:
            if pk in persons_reg:
                folio_persons[pk] = persons_reg[pk]
            else:
                folio_persons[pk] = {
                    "slug": pk,
                    "name": pk.replace("-", " ").title(),
                    "dates": "",
                    "role": "Historical Figure / Scholar",
                    "bio": "",
                    "works": [],
                    "occurrences": [{"volume": res["volume"], "folio": folio, "page": page_label}],
                }

        res["pygments_css"] = PYGMENTS_CSS
        res["md_content"] = md_content
        res["md_body"] = md_body
        res["md_html"] = md_html
        res["notes_content"] = notes_content
        res["notes_html"] = notes_html
        res["json_content"] = json_content
        res["json_data"] = json_data
        res["full_dir_path"] = str(full_parent)
        res["folio_citations"] = folio_citations
        res["folio_terms"] = folio_terms
        res["folio_persons"] = folio_persons

        return res

    get_folio = get_folio_detail

    def get_apparatus(self, force: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load or build the edition's citations, glossary, and persons registries."""
        if not force and getattr(self, "_apparatus_cache", None) is not None:
            return self._apparatus_cache  # type: ignore[return-value]

        citations: Dict[str, Any] = {}
        glossary: Dict[str, Any] = {}
        persons: Dict[str, Any] = {}

        cites_path = self.root_dir / "citations.json"
        if cites_path.exists():
            try:
                citations = json.loads(cites_path.read_text(encoding="utf-8"))
            except Exception:
                citations = {}

        glossary_path = self.root_dir / "glossary.json"
        if glossary_path.exists():
            try:
                glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
            except Exception:
                glossary = {}

        persons_path = self.root_dir / "persons.json"
        if persons_path.exists():
            try:
                persons = json.loads(persons_path.read_text(encoding="utf-8"))
            except Exception:
                persons = {}

        self._apparatus_cache = {"citations": citations, "glossary": glossary, "persons": persons}
        return self._apparatus_cache

    def get_neighbors(self, volume: str, folio: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Return (prev_folio, next_folio) in the ordered sequence."""
        folios = self.scan()
        if folio.isdigit():
            folio = f"{int(folio):04d}"
        key = f"{volume}:{folio}"
        fallback_key = f"{self.volumes[0]['name']}:{folio}" if len(self.volumes) == 1 else key
        for idx, item in enumerate(folios):
            if item["key"] in (key, fallback_key):
                prev_item = folios[idx - 1] if idx > 0 else None
                next_item = folios[idx + 1] if idx < len(folios) - 1 else None
                return prev_item, next_item
        return None, None

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics per volume and across the entire edition."""
        folios = self.scan()
        vol_stats: Dict[str, Dict[str, Any]] = {}

        for v in self.volumes:
            vname = v["name"]
            vol_stats[vname] = {
                "name": vname,
                "label": v["label"],
                "total_folios": 0,
                "first_folio": None,
                "transcribed_count": 0,
                "notes_count": 0,
                "graphics_count": 0,
                "folios_with_graphics": 0,
                "missing_crops_count": 0,
                "svg_count": 0,
                "sections": set(),
            }

        total_folios = 0
        total_transcribed = 0
        total_notes = 0
        total_graphics = 0
        total_folios_with_graphics = 0
        total_missing_crops = 0
        total_svgs = 0

        for f in folios:
            vname = f["volume"]
            if vname not in vol_stats:
                vol_stats[vname] = {
                    "name": vname,
                    "label": f["volume_label"],
                    "total_folios": 0,
                    "first_folio": None,
                    "transcribed_count": 0,
                    "notes_count": 0,
                    "graphics_count": 0,
                    "folios_with_graphics": 0,
                    "missing_crops_count": 0,
                    "svg_count": 0,
                    "sections": set(),
                }
            vs = vol_stats[vname]
            if vs["first_folio"] is None:
                vs["first_folio"] = f["folio"]
            vs["total_folios"] += 1
            total_folios += 1

            if f["has_md"]:
                vs["transcribed_count"] += 1
                total_transcribed += 1
            if f["has_notes"]:
                vs["notes_count"] += 1
                total_notes += 1
            if f["graphics_count"] > 0:
                vs["graphics_count"] += f["graphics_count"]
                vs["folios_with_graphics"] += 1
                total_graphics += f["graphics_count"]
                total_folios_with_graphics += 1
            if f["missing_crops_count"] > 0:
                vs["missing_crops_count"] += f["missing_crops_count"]
                total_missing_crops += f["missing_crops_count"]
            if f.get("svg_count", 0) > 0:
                vs["svg_count"] += f["svg_count"]
                total_svgs += f["svg_count"]

            vs["sections"].add(f["section_path"])

        for vname, vs in vol_stats.items():
            vs["sections"] = sorted(list(vs["sections"]))

        return {
            "total_folios": total_folios,
            "total_transcribed": total_transcribed,
            "total_notes": total_notes,
            "total_graphics": total_graphics,
            "total_folios_with_graphics": total_folios_with_graphics,
            "total_missing_crops": total_missing_crops,
            "total_svgs": total_svgs,
            "transcribed_pct": round((total_transcribed / total_folios * 100), 1) if total_folios else 0,
            "notes_pct": round((total_notes / total_folios * 100), 1) if total_folios else 0,
            "svg_pct": round((total_svgs / total_graphics * 100), 1) if total_graphics else 0,
            "volumes": vol_stats,
        }
