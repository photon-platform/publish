"""Book Codex hierarchy, track, collection, and apparatus compliance linter."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

_INFRA_DIRS = {
    ".git",
    ".doctrees",
    "_static",
    "_templates",
    "modules",
    "log",
    "about",
    "people",
    "usage",
    "demos",
    "sources",
    "todos",
    "refs",
    "__pycache__",
}

_APPARATUS_FILES = ("bibliography.rst", "glossary.rst", "persons.rst", "people/index.rst")

_LEGACY_STEM_TRACK_RE = re.compile(
    r"^(.+)[-_](en|el|grc|la|de|fr|it|da|summary|notes|commentary)$"
)
_TRANSLATION_NOTES_RE = re.compile(r"^translation-notes-(.+)$")


def _peek_meta(text: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in text.splitlines()[:35]:
        s = line.strip()
        if not s:
            continue
        if s.startswith(":") and ":" in s[1:]:
            k, v = s[1:].split(":", 1)
            meta[k.strip()] = v.strip()
        elif not s.startswith(".."):
            break
    return meta


@dataclass
class BookAuditReport:
    repo: str
    book_roots: List[str] = field(default_factory=list)
    non_english_first_tracks: List[Dict[str, str]] = field(default_factory=list)
    legacy_track_filenames: List[str] = field(default_factory=list)
    nested_book_titles: List[str] = field(default_factory=list)
    duplicate_collection_toctree: List[str] = field(default_factory=list)
    duplicated_apparatus: List[str] = field(default_factory=list)
    redundant_track_lists_in_body: List[str] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return (
            len(self.non_english_first_tracks)
            + len(self.legacy_track_filenames)
            + len(self.nested_book_titles)
            + len(self.duplicate_collection_toctree)
            + len(self.duplicated_apparatus)
            + len(self.redundant_track_lists_in_body)
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["issue_count"] = self.issue_count
        return payload


def audit_repo_books(repo_root: Path) -> BookAuditReport:
    """Audit a repository's docsrc/ against the canonical GEOMETOR Book Codex standard."""
    repo_root = Path(repo_root).resolve()
    report = BookAuditReport(repo=repo_root.name)
    docsrc = repo_root / "docsrc"
    if not docsrc.is_dir():
        return report

    # 1. Check apparatus duplication between docsrc root and book subdirectories
    root_app = {f for f in _APPARATUS_FILES if (docsrc / f).is_file()}
    for sub in sorted(docsrc.iterdir()):
        if not sub.is_dir() or sub.name.startswith(".") or sub.name in _INFRA_DIRS:
            continue
        for f in _APPARATUS_FILES:
            if (sub / f).is_file() and f in root_app:
                report.duplicated_apparatus.append(f"{sub.name}/{f} (also at docsrc/{f})")

    # 2. Discover :book_title: roots and detect nested overrides
    all_book_title_docs: List[str] = []
    rst_files = sorted(
        p
        for p in docsrc.rglob("*.rst")
        if not any(part.startswith(".") or part in _INFRA_DIRS for part in p.relative_to(docsrc).parts)
    )

    for p in rst_files:
        rel = p.relative_to(docsrc).as_posix()
        rel_no_ext = rel[:-4]
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        meta = _peek_meta(text)
        stem = p.stem

        if "book_title" in meta and meta.get("type") != "book_title" and not stem.startswith("title-"):
            all_book_title_docs.append(rel_no_ext)

        # Non-English-first explicit :tracks:
        raw_tracks = meta.get("tracks", "")
        if raw_tracks and "|" in raw_tracks:
            labels = [seg.split(":", 1)[0].strip() for seg in raw_tracks.split("|") if ":" in seg]
            if "English" in labels and labels[0] != "English":
                report.non_english_first_tracks.append({"doc": rel_no_ext, "tracks": raw_tracks})

        # Legacy stem-based track filenames (e.g., prop_01-en, cap_01_it, translation-notes-caput-1)
        if _TRANSLATION_NOTES_RE.match(stem) or (
            _LEGACY_STEM_TRACK_RE.match(stem) and not stem.startswith("title-")
        ):
            report.legacy_track_filenames.append(rel_no_ext)

        # Redundant .. collection:: + .. toctree:: listing same local subdirs
        if ".. collection::" in text and ".. toctree::" in text:
            # Check if the toctree lists direct child index docs that collection already auto-discovers
            # (ignoring apparatus subdirs like people/index)
            toc_matches = [
                m
                for m in re.findall(r"^\s+([\w.-]+/index)\s*$", text, re.MULTILINE)
                if m not in {"people/index", "sources/index", "about/index", "log/index", "modules/index"}
            ]
            if toc_matches and ":docs:" not in text:
                report.duplicate_collection_toctree.append(rel_no_ext)

        # Manual "Parallel Reading Tracks" heading duplicating header track switcher
        if re.search(r"^Parallel Reading Tracks\s*$", text, re.M):
            report.redundant_track_lists_in_body.append(rel_no_ext)

    # Determine top-level vs nested :book_title: declarations
    all_book_title_docs.sort(key=lambda d: (d.count("/"), d))
    top_prefixes: List[str] = []
    for doc in all_book_title_docs:
        doc_dir = doc[:-6] if doc.endswith("/index") else doc
        is_nested = any(
            doc_dir.startswith(pref + "/") for pref in top_prefixes if pref
        )
        if is_nested:
            report.nested_book_titles.append(doc)
        else:
            report.book_roots.append(doc)
            top_prefixes.append(doc_dir)

    return report
