"""Primary-source folio URL resolution, repository link auditing, and lossless scan optimization."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote

_SCAN_FILENAME_RE = re.compile(r"^(\d{4})\.(png|jpg|jpeg)$", re.IGNORECASE)
_FOLIO_NUM_RE = re.compile(r"\b(\d{4})\b")
_TRACK_SUFFIX_RE = re.compile(r"(?:^|[._/-])(el|grc|en|la|de|it|fr|heath)$", re.IGNORECASE)
_DIRECTIVE_FOLIO_RE = re.compile(r"^\s*\.\.\s+folio::\s*(.+?)\s*$", re.MULTILINE)
_DIRECTIVE_URL_OPT_RE = re.compile(r"^\s*:url:\s*(\S+)", re.MULTILINE)
_FRONTMATTER_FOLIO_RE = re.compile(r"^:folio:\s*(.+?)\s*$", re.MULTILINE)

_LANG_ALIASES: dict[str, tuple[str, ...]] = {
    "el": ("el", "grc"),
    "grc": ("grc", "el"),
    "en": ("en",),
    "la": ("la",),
    "de": ("de",),
    "it": ("it",),
    "fr": ("fr",),
    "heath": ("heath", "en"),
}


def _list_non_ignored_resource_files(project_root: Path) -> list[str]:
    """Return relative POSIX paths under `resources/` that are tracked or non-gitignored."""
    res_dir = project_root / "resources"
    if not res_dir.is_dir():
        return []

    if (project_root / ".git").exists():
        try:
            proc = subprocess.run(
                [
                    "git",
                    "-C",
                    str(project_root),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "resources",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            paths = [
                line.strip()
                for line in proc.stdout.splitlines()
                if line.strip() and (project_root / line.strip()).is_file()
            ]
            return sorted(paths)
        except (subprocess.SubprocessError, OSError):
            pass

    return sorted(
        p.relative_to(project_root).as_posix()
        for p in res_dir.rglob("*")
        if p.is_file()
    )


def _github_coords(env: Any, project_root: Path) -> tuple[str, str, str, str]:
    """Extract `(gh_user, gh_repo, gh_branch, folio_base_url)` from Sphinx `env`."""
    cfg = getattr(env, "config", None) if env is not None else None
    html_ctx = (getattr(cfg, "html_context", None) or {}) if cfg is not None else {}
    gh_user = str(html_ctx.get("github_user") or getattr(cfg, "org", "") or "geometor")
    gh_repo = str(html_ctx.get("github_repo") or getattr(cfg, "repo", "") or project_root.name)
    gh_branch = str(html_ctx.get("github_version") or "main")
    base_url = str(getattr(cfg, "folio_base_url", "") or "").rstrip("/")
    return gh_user, gh_repo, gh_branch, base_url


def load_folio_scan_index(env: Any, project_root: Path | None = None) -> dict[tuple[str, str], str]:
    """Index non-ignored 4-digit `.png`/`.jpg` scan files under `resources/` by `(scope_key, stem)`.

    Args:
        env: Sphinx BuildEnvironment (optional when invoked from CLI).
        project_root: Explicit repository root override.

    Returns:
        Mapping of `(scope_key, 4_digit_stem)` to repo-relative POSIX path.
    """
    if project_root is None:
        srcdir = getattr(env, "srcdir", ".") if env is not None else "."
        resolved_root = Path(srcdir).resolve().parent
    else:
        resolved_root = Path(project_root).resolve()

    cache_attr = "_photon_folio_scan_cache"
    if env is not None:
        cached = getattr(env, cache_attr, None)
        if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == str(resolved_root):
            return cached[1]
        if isinstance(cached, dict):
            return cached

    index: dict[tuple[str, str], str] = {}

    def _store(key: tuple[str, str], rel_posix: str) -> None:
        existing = index.get(key)
        # Prefer .png over .jpg/.jpeg only if both exist for the identical key
        if existing is None or (existing.lower().endswith((".jpg", ".jpeg")) and rel_posix.lower().endswith(".png")):
            index[key] = rel_posix

    for rel_posix in _list_non_ignored_resource_files(resolved_root):
        parts = Path(rel_posix).parts
        if not parts:
            continue
        m = _SCAN_FILENAME_RE.match(parts[-1])
        if not m:
            continue
        stem = m.group(1)
        # Scope keys: volume_* segment and top-level edition directory under resources/
        if len(parts) >= 3:
            edition_slug = parts[1].lower()
            _store((f"ed:{edition_slug}", stem), rel_posix)
        for part in parts:
            low = part.lower()
            if low.startswith("volume_"):
                _store((low, stem), rel_posix)
        _store(("", stem), rel_posix)

    if env is not None:
        setattr(env, cache_attr, (str(resolved_root), index))
    return index


def load_folio_map_index(env: Any, project_root: Path | None = None) -> dict[str, Any]:
    """Load and merge all non-ignored `resources/**/folio_map.json` manifests."""
    if project_root is None:
        srcdir = getattr(env, "srcdir", ".") if env is not None else "."
        resolved_root = Path(srcdir).resolve().parent
    else:
        resolved_root = Path(project_root).resolve()

    cache_attr = "_photon_folio_map_cache"
    if env is not None:
        cached = getattr(env, cache_attr, None)
        if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == str(resolved_root):
            return cached[1]
        if isinstance(cached, dict):
            return cached

    merged: dict[str, Any] = {}
    for rel_posix in _list_non_ignored_resource_files(resolved_root):
        if Path(rel_posix).name != "folio_map.json":
            continue
        full_path = resolved_root / rel_posix
        try:
            data = json.loads(full_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            entries = data.get("folios") if isinstance(data.get("folios"), dict) else data
            for k, v in entries.items():
                if not str(k).startswith("_"):
                    merged[str(k).strip()] = v

    if env is not None:
        setattr(env, cache_attr, (str(resolved_root), merged))
    return merged


def _detect_doc_track(env: Any, current_docname: str) -> str:
    """Detect language/edition track (`el`, `en`, `la`, `de`, `it`, `fr`, etc.) for `current_docname`."""
    if env is not None and hasattr(env, "metadata") and current_docname in env.metadata:
        lang_meta = str(env.metadata[current_docname].get("lang") or "").strip().lower()
        if lang_meta:
            return lang_meta

    base = os.path.basename(current_docname or "")
    m = _TRACK_SUFFIX_RE.search(base)
    if m:
        return m.group(1).lower()

    for part in reversed((current_docname or "").split("/")[:-1]):
        if part.lower() in _LANG_ALIASES:
            return part.lower()
    return ""


def _format_target_url(
    target: str,
    gh_user: str,
    gh_repo: str,
    gh_branch: str,
) -> str:
    """Format a `folio_map.json` target string as either an external URL or a GitHub blob URL."""
    cleaned = target.strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return cleaned

    if "#" in cleaned:
        path_part, frag = cleaned.split("#", 1)
        frag_str = f"#{frag}"
    else:
        path_part, frag_str = cleaned, ""

    quoted_path = "/".join(quote(seg) for seg in path_part.lstrip("/").split("/"))
    return f"https://github.com/{gh_user}/{gh_repo}/blob/{gh_branch}/{quoted_path}{frag_str}"


def _lookup_folio_map_entry(folio_map: dict[str, Any], raw_folio_id: str) -> Any:
    """Find a matching entry in `folio_map` for `raw_folio_id` (including normalized & span fallbacks)."""
    fid = raw_folio_id.strip()
    if not fid or not folio_map:
        return None
    if fid in folio_map:
        return folio_map[fid]

    norm = re.sub(r"\s+", " ", fid)
    if norm in folio_map:
        return folio_map[norm]

    # Span fallback (e.g., "71a1–79a16" or "4b20–6a35, 25b–26a" -> "71a" / "Bekker 4b")
    first_part = re.split(r"\s*[,;\u2013\u2014\-]\s*", norm, maxsplit=1)[0].strip()
    if first_part and first_part != norm:
        if first_part in folio_map:
            return folio_map[first_part]
        m_bekker = re.match(r"^(?:Bekker\s+)?(\d+[ab])\d*$", first_part, re.IGNORECASE)
        if m_bekker:
            col = m_bekker.group(1).lower()
            for cand in (f"Bekker {col}", col):
                if cand in folio_map:
                    return folio_map[cand]

    m_bekker_single = re.match(r"^(?:Bekker\s+)?(\d+[ab])\d*$", norm, re.IGNORECASE)
    if m_bekker_single:
        col = m_bekker_single.group(1).lower()
        for cand in (f"Bekker {col}", col):
            if cand in folio_map:
                return folio_map[cand]

    return None


def resolve_folio_url(
    env: Any,
    current_docname: str,
    folio_id: str,
    project_root: Path | None = None,
) -> str | None:
    """Resolve `folio_id` to a verified primary-source scan or text-locus URL.

    Resolution order:
    1. Non-gitignored 4-digit `.png` or `.jpg` scan in `resources/` -> GitHub raw URL (or `folio_base_url`).
    2. Track-aware `resources/**/folio_map.json` entry -> GitHub `blob/...#L<line>` or external facsimile URL.
    """
    raw_id = (folio_id or "").strip()
    if not raw_id:
        return None

    if project_root is None:
        srcdir = getattr(env, "srcdir", ".") if env is not None else "."
        project_root = Path(srcdir).resolve().parent

    gh_user, gh_repo, gh_branch, base_url = _github_coords(env, project_root)

    # 1. Check 4-digit scan image (.png / .jpg)
    m_num = _FOLIO_NUM_RE.search(raw_id)
    if m_num:
        folio_num = m_num.group(1)
        scan_index = load_folio_scan_index(env, project_root=project_root)
        if scan_index:
            doc_parts = [p.lower() for p in (current_docname or "").split("/") if p]
            vol_key = next((p for p in doc_parts if p.startswith("volume_")), "")
            if not vol_key and env is not None and hasattr(env, "metadata") and current_docname in env.metadata:
                vol_meta = str(env.metadata[current_docname].get("volume", "")).strip()
                if vol_meta:
                    vol_key = f"volume_{vol_meta.lower()}"

            ed_key = f"ed:{doc_parts[0]}" if doc_parts else ""
            rel_path = (
                (scan_index.get((vol_key, folio_num)) if vol_key else None)
                or (scan_index.get((ed_key, folio_num)) if ed_key else None)
                or scan_index.get(("", folio_num))
            )
            if rel_path:
                quoted_rel = "/".join(quote(seg) for seg in rel_path.split("/"))
                if base_url:
                    return f"{base_url}/{quoted_rel}"
                return f"https://raw.githubusercontent.com/{gh_user}/{gh_repo}/{gh_branch}/{quoted_rel}"

    # 2. Check track-aware folio_map.json
    folio_map = load_folio_map_index(env, project_root=project_root)
    entry = _lookup_folio_map_entry(folio_map, raw_id)
    if entry is None:
        return None

    if isinstance(entry, str):
        resolved = _format_target_url(entry, gh_user, gh_repo, gh_branch)
        return resolved or None

    if isinstance(entry, dict):
        if "url" in entry and isinstance(entry["url"], str):
            resolved = _format_target_url(entry["url"], gh_user, gh_repo, gh_branch)
            return resolved or None
        if "source" in entry and isinstance(entry["source"], str):
            src = entry["source"].strip()
            line = entry.get("line")
            target = f"{src}#L{line}" if line else src
            resolved = _format_target_url(target, gh_user, gh_repo, gh_branch)
            return resolved or None

        track = _detect_doc_track(env, current_docname)
        cand_keys: list[str] = []
        if track:
            cand_keys.extend(_LANG_ALIASES.get(track, (track,)))
        cand_keys.extend(["default", "en", "la", "el", "grc", "de", "it", "fr"])

        for ck in cand_keys:
            val = entry.get(ck)
            if isinstance(val, str) and val.strip():
                resolved = _format_target_url(val, gh_user, gh_repo, gh_branch)
                if resolved:
                    return resolved
            elif isinstance(val, dict) and isinstance(val.get("source"), str):
                line = val.get("line")
                target = f"{val['source'].strip()}#L{line}" if line else val["source"].strip()
                resolved = _format_target_url(target, gh_user, gh_repo, gh_branch)
                if resolved:
                    return resolved

        for val in entry.values():
            if isinstance(val, str) and val.strip():
                resolved = _format_target_url(val, gh_user, gh_repo, gh_branch)
                if resolved:
                    return resolved

    return None


@dataclass
class FolioAuditReport:
    """Structured audit summary of primary-source folio links in a repository."""

    repo: str
    tracked_scans: int
    ignored_scans: int
    folio_map_entries: int
    directives_total: int
    directives_resolved: int
    badges_total: int
    badges_resolved: int
    unresolved_directives: list[str] = field(default_factory=list)
    unresolved_badges: list[str] = field(default_factory=list)
    sample_links: list[str] = field(default_factory=list)
    env: Any = None


def audit_repo_folio_links(repo_root: Path, env: Any = None) -> FolioAuditReport:
    """Deterministically audit all `.. folio::` directives and `:folio:` badges in `repo_root`."""
    repo_root = repo_root.resolve()
    docsrc = repo_root / "docsrc"
    res_dir = repo_root / "resources"

    non_ignored = set(_list_non_ignored_resource_files(repo_root))
    all_disk_scans = (
        [
            p.relative_to(repo_root).as_posix()
            for p in res_dir.rglob("*")
            if p.is_file() and _SCAN_FILENAME_RE.match(p.name)
        ]
        if res_dir.is_dir()
        else []
    )
    tracked_scans = sum(1 for s in all_disk_scans if s in non_ignored)
    ignored_scans = len(all_disk_scans) - tracked_scans

    # Build lightweight mock env so caches reuse exact Sphinx logic
    class _StubConfig:
        def __init__(self, repo_name: str) -> None:
            self.org = "geometor"
            self.repo = repo_name
            self.folio_base_url = ""
            self.html_context = {
                "github_user": "geometor",
                "github_repo": repo_name,
                "github_version": "main",
            }

    class _StubEnv:
        def __init__(self, docsrc_path: Path, repo_name: str) -> None:
            self.srcdir = str(docsrc_path)
            self.config = _StubConfig(repo_name)
            self.metadata: dict[str, dict[str, Any]] = {}

    if env is None:
        env = _StubEnv(docsrc, repo_root.name)
    fmap = load_folio_map_index(env, project_root=repo_root)

    directives_total = 0
    directives_resolved = 0
    badges_total = 0
    badges_resolved = 0
    unresolved_dir_set: set[str] = set()
    unresolved_badge_set: set[str] = set()
    samples: list[str] = []

    if docsrc.is_dir():
        for rst_path in sorted(docsrc.rglob("*.rst")):
            docname = rst_path.relative_to(docsrc).with_suffix("").as_posix()
            text = rst_path.read_text(encoding="utf-8", errors="replace")

            # Frontmatter :folio: (only top field list before first blank-separated heading)
            head_chunk = text[:1500]
            for m_fm in _FRONTMATTER_FOLIO_RE.finditer(head_chunk):
                # Ensure it's at start of file field list (no preceding section underline)
                prefix = head_chunk[: m_fm.start()]
                if re.search(r"^[=\-~^\"`#*+]{3,}\s*$", prefix, re.MULTILINE):
                    continue
                fid = m_fm.group(1).strip()
                badges_total += 1
                url = resolve_folio_url(env, docname, fid, project_root=repo_root)
                if url:
                    badges_resolved += 1
                    if len(samples) < 5 and url not in samples:
                        samples.append(url)
                else:
                    unresolved_badge_set.add(f"{docname}: {fid}")

            # Body .. folio:: directives
            lines = text.splitlines()
            for i, line in enumerate(lines):
                m_dir = _DIRECTIVE_FOLIO_RE.match(line)
                if not m_dir:
                    continue
                fid = m_dir.group(1).strip()
                directives_total += 1
                explicit_url = None
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].startswith((" ", "\t"))):
                    m_opt = _DIRECTIVE_URL_OPT_RE.match(lines[j])
                    if m_opt:
                        explicit_url = m_opt.group(1).strip()
                        break
                    if lines[j].strip() and not lines[j].lstrip().startswith(":"):
                        break
                    j += 1
                url = explicit_url or resolve_folio_url(env, docname, fid, project_root=repo_root)
                if url:
                    directives_resolved += 1
                    if len(samples) < 5 and url not in samples:
                        samples.append(url)
                else:
                    unresolved_dir_set.add(f"{docname}: {fid}")

    return FolioAuditReport(
        repo=repo_root.name,
        tracked_scans=tracked_scans,
        ignored_scans=ignored_scans,
        folio_map_entries=len(fmap),
        directives_total=directives_total,
        directives_resolved=directives_resolved,
        badges_total=badges_total,
        badges_resolved=badges_resolved,
        unresolved_directives=sorted(unresolved_dir_set)[:25],
        unresolved_badges=sorted(unresolved_badge_set)[:25],
        sample_links=samples,
        env=env,
    )


def optimize_repo_folio_scans(repo_root: Path, force_grayscale: bool = False) -> dict[str, Any]:
    """Losslessly optimize 4-digit `.png` folio scans in `resources/` (converting near-grayscale RGB to `L`)."""
    from PIL import Image, ImageChops, ImageStat

    res_dir = repo_root.resolve() / "resources"
    if not res_dir.is_dir():
        return {"files_checked": 0, "files_rewritten": 0, "before_bytes": 0, "after_bytes": 0, "saved_mb": 0.0}

    checked = 0
    rewritten = 0
    before_total = 0
    after_total = 0

    for png_path in sorted(res_dir.rglob("[0-9][0-9][0-9][0-9].png")):
        if not png_path.is_file():
            continue
        checked += 1
        orig_bytes = png_path.stat().st_size
        before_total += orig_bytes

        with Image.open(png_path) as im:
            work = im
            if force_grayscale and im.mode != "L":
                work = im.convert("L")
            elif im.mode in ("RGB", "RGBA"):
                rgb = im.convert("RGB")
                r, g, b = rgb.split()
                diff_rg = ImageStat.Stat(ImageChops.difference(r, g)).mean[0]
                diff_rb = ImageStat.Stat(ImageChops.difference(r, b)).mean[0]
                # Convert colorless/near-grayscale RGB scans to 8-bit grayscale 'L'
                if max(diff_rg, diff_rb) < 4.0:
                    work = rgb.convert("L")

            buf = BytesIO()
            work.save(buf, format="PNG", optimize=True, compress_level=9)
            cand = buf.getvalue()

        if len(cand) < orig_bytes:
            png_path.write_bytes(cand)
            after_total += len(cand)
            rewritten += 1
        else:
            after_total += orig_bytes

    return {
        "files_checked": checked,
        "files_rewritten": rewritten,
        "before_bytes": before_total,
        "after_bytes": after_total,
        "saved_mb": round((before_total - after_total) / (1024 * 1024), 2),
    }
