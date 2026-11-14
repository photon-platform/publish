"""Tests for primary-source folio links resolution, map indexing, and repository auditing."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from photon_platform.publish.book import resolve_book_context
from photon_platform.publish.folio_links import (
    audit_repo_folio_links,
    load_folio_scan_index,
    resolve_folio_url,
)


class _MockConfig:
    """Minimal Sphinx config mock for folio resolution tests."""

    def __init__(self, org: str = "geometor", repo: str = "elements", folio_base_url: str = "") -> None:
        self.master_doc = "index"
        self.org = org
        self.repo = repo
        self.folio_base_url = folio_base_url
        self.html_context: dict[str, str] = {
            "github_user": org,
            "github_repo": repo,
            "github_version": "main",
        }


class _MockEnv:
    """Minimal Sphinx BuildEnvironment mock."""

    def __init__(self, srcdir: Path, config: _MockConfig | None = None) -> None:
        self.srcdir = str(srcdir)
        self.config = config or _MockConfig()
        self.metadata: dict[str, dict[str, Any]] = {}
        self.titles: dict[str, Any] = {}
        self.found_docs: set[str] = set()


def test_scan_resolution_and_volume_edition_disambiguation(tmp_path: Path) -> None:
    """(a) Test .png and .jpg 4-digit scan resolution and volume/edition disambiguation."""
    repo = tmp_path / "repo"
    res_dir = repo / "resources"
    docsrc = repo / "docsrc"

    # Volume 1 has 0001.png and 0002.jpg
    v1 = res_dir / "volume_01"
    v1.mkdir(parents=True)
    (v1 / "0001.png").write_bytes(b"v1_0001_png")
    (v1 / "0002.jpg").write_bytes(b"v1_0002_jpg")

    # Volume 2 has 0001.png and a duplicate 0001.jpg (png should take precedence)
    v2 = res_dir / "volume_02"
    v2.mkdir(parents=True)
    (v2 / "0001.png").write_bytes(b"v2_0001_png")
    (v2 / "0001.jpg").write_bytes(b"v2_0001_jpg")

    # Edition directory: resources/byrne_1847/0003.png
    ed = res_dir / "byrne_1847"
    ed.mkdir(parents=True)
    (ed / "0003.png").write_bytes(b"byrne_0003")

    docsrc.mkdir(parents=True)
    env = _MockEnv(docsrc)

    # Volume 1 disambiguation
    url_v1_0001 = resolve_folio_url(env, "volume_01/prop_01", "0001", project_root=repo)
    assert url_v1_0001 is not None
    assert url_v1_0001 == "https://raw.githubusercontent.com/geometor/elements/main/resources/volume_01/0001.png"

    # .jpg scan resolution
    url_v1_0002 = resolve_folio_url(env, "volume_01/prop_02", "0002", project_root=repo)
    assert url_v1_0002 is not None
    assert url_v1_0002 == "https://raw.githubusercontent.com/geometor/elements/main/resources/volume_01/0002.jpg"

    # Volume 2 disambiguation (.png prioritized over .jpg)
    url_v2_0001 = resolve_folio_url(env, "volume_02/prop_01", "0001", project_root=repo)
    assert url_v2_0001 is not None
    assert url_v2_0001 == "https://raw.githubusercontent.com/geometor/elements/main/resources/volume_02/0001.png"

    # Edition-scoped disambiguation
    url_ed = resolve_folio_url(env, "byrne_1847/prop_01", "0003", project_root=repo)
    assert url_ed is not None
    assert url_ed == "https://raw.githubusercontent.com/geometor/elements/main/resources/byrne_1847/0003.png"

    # With explicit folio_base_url configured
    env.config.folio_base_url = "https://cdn.geometor.com/facsimiles"
    url_cdn = resolve_folio_url(env, "volume_01/prop_01", "0001", project_root=repo)
    assert url_cdn == "https://cdn.geometor.com/facsimiles/resources/volume_01/0001.png"


def test_gitignore_exclusion_when_git_present(tmp_path: Path) -> None:
    """(b) Test .gitignore exclusion when .git is present."""
    repo = tmp_path / "git_repo"
    repo.mkdir()
    res_dir = repo / "resources"
    res_dir.mkdir()

    # Initialize a real git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

    # Create tracked and ignored scans
    (res_dir / "0001.png").write_bytes(b"tracked")
    (res_dir / "0002.png").write_bytes(b"ignored")
    (repo / ".gitignore").write_text("resources/0002.png\n", encoding="utf-8")

    # Commit tracked file and .gitignore
    subprocess.run(["git", "add", ".gitignore", "resources/0001.png"], cwd=repo, check=True, capture_output=True)

    scan_index = load_folio_scan_index(None, project_root=repo)
    assert ("", "0001") in scan_index
    assert ("", "0002") not in scan_index


def test_track_aware_folio_map_and_bekker_fallbacks(tmp_path: Path) -> None:
    """(c) Test track-aware folio_map.json (el vs en #L<line> and Bekker span fallbacks)."""
    repo = tmp_path / "repo"
    res_dir = repo / "resources"
    docsrc = repo / "docsrc"
    res_dir.mkdir(parents=True)
    docsrc.mkdir(parents=True)

    # Write track-aware folio_map.json
    fmap_data = {
        "folios": {
            "Bekker 71a": {
                "el": "https://facsimile.org/greek/71a.png",
                "en": "https://facsimile.org/english/71a.png",
            },
            "Bekker 4b": {
                "el": {"source": "texts/greek_source.txt", "line": 42},
                "en": {"source": "texts/english_source.txt", "line": 108},
            },
            "Bekker 25b": "https://facsimile.org/manuscript/25b.jpg",
        }
    }
    (res_dir / "folio_map.json").write_text(json.dumps(fmap_data), encoding="utf-8")

    env = _MockEnv(docsrc)

    # 1. Bekker span "71a1–79a16" on Greek track
    url_el = resolve_folio_url(env, "analytics/book_01.el", "71a1–79a16", project_root=repo)
    assert url_el == "https://facsimile.org/greek/71a.png"

    # 2. Bekker span "71a1–79a16" on English track
    url_en = resolve_folio_url(env, "analytics/book_01.en", "71a1–79a16", project_root=repo)
    assert url_en == "https://facsimile.org/english/71a.png"

    # 3. Complex span with line locus: "4b20–6a35, 25b–26a" on Greek track
    url_el_line = resolve_folio_url(env, "physics/book_01.el", "4b20–6a35, 25b–26a", project_root=repo)
    assert url_el_line is not None
    assert url_el_line == "https://github.com/geometor/elements/blob/main/texts/greek_source.txt#L42"

    # 4. Same span on English track
    url_en_line = resolve_folio_url(env, "physics/book_01.en", "4b20–6a35, 25b–26a", project_root=repo)
    assert url_en_line is not None
    assert url_en_line == "https://github.com/geometor/elements/blob/main/texts/english_source.txt#L108"

    # 5. Fallback string URL
    url_simple = resolve_folio_url(env, "physics/book_02.la", "25b10-30", project_root=repo)
    assert url_simple == "https://facsimile.org/manuscript/25b.jpg"


def test_resolve_book_context_populating_folio_url(tmp_path: Path) -> None:
    """(d) Test resolve_book_context populating folio_url in returned dictionary."""
    repo = tmp_path / "repo"
    res_dir = repo / "resources"
    docsrc = repo / "docsrc"
    res_dir.mkdir(parents=True)
    docsrc.mkdir(parents=True)

    # Scan in resources
    (res_dir / "0042.png").write_bytes(b"scan_42")

    env = _MockEnv(docsrc)
    env.metadata["index"] = {
        "layout": "book",
        "book_title": "The Elements",
    }
    env.metadata["propositions/prop_01"] = {
        "layout": "book",
        "title": "Proposition 1",
        "folio": "0042",
    }

    ctx = resolve_book_context(env, "propositions/prop_01")
    assert ctx.get("is_book_page") is not False
    assert ctx.get("folio") == "0042"
    assert "folio_url" in ctx
    assert ctx["folio_url"] == "https://raw.githubusercontent.com/geometor/elements/main/resources/0042.png"


def test_audit_repo_folio_links(tmp_path: Path) -> None:
    """(e) Test audit_repo_folio_links deterministic accounting."""
    repo = tmp_path / "audit_repo"
    repo.mkdir()
    docsrc = repo / "docsrc"
    res_dir = repo / "resources"
    docsrc.mkdir()
    res_dir.mkdir()

    # Create scans
    (res_dir / "0001.png").write_bytes(b"scan1")
    (res_dir / "0002.png").write_bytes(b"scan2")

    # Create folio map
    fmap = {"folios": {"Folio 0003": "https://example.com/facsimile/3"}}
    (res_dir / "folio_map.json").write_text(json.dumps(fmap), encoding="utf-8")

    # Create RST documents with frontmatter badge and directive
    doc1 = docsrc / "doc1.rst"
    doc1.write_text(
        ":folio: 0001\n:title: Page 1\n\nHeading\n=======\n\nBody text.\n",
        encoding="utf-8",
    )

    doc2 = docsrc / "doc2.rst"
    doc2.write_text(
        "Heading\n=======\n\n.. folio:: 0002\n\n.. folio:: Folio 0003\n\n.. folio:: missing_9999\n",
        encoding="utf-8",
    )

    t0 = time.perf_counter()
    report = audit_repo_folio_links(repo)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.2

    # Verify env cache population
    assert report.env is not None
    cached_scan = getattr(report.env, "_photon_folio_scan_cache", None)
    assert cached_scan is not None
    assert cached_scan[0] == str(repo.resolve())
    assert ("", "0001") in cached_scan[1]
    assert ("", "0002") in cached_scan[1]

    cached_map = getattr(report.env, "_photon_folio_map_cache", None)
    assert cached_map is not None
    assert cached_map[0] == str(repo.resolve())
    assert "Folio 0003" in cached_map[1]

    assert report.repo == repo.name
    assert report.tracked_scans == 2
    assert report.ignored_scans == 0
    assert report.folio_map_entries == 1

    # Badges
    assert report.badges_total == 1
    assert report.badges_resolved == 1

    # Directives: 0002 (resolved), Folio 0003 (resolved), missing_9999 (unresolved)
    assert report.directives_total == 3
    assert report.directives_resolved == 2
    assert len(report.unresolved_directives) == 1
    assert "missing_9999" in report.unresolved_directives[0]

    # Sample links collected
    assert len(report.sample_links) >= 2
