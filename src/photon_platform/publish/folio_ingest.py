"""Deterministic archival PDF ingestion: 300-DPI folio PNG scans, text streams, embedded graphics, and folio_map.json."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _get_pdf_page_count(pdf_path: Path) -> int:
    """Return total page count of `pdf_path` via `pdfinfo`."""
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return 0
    proc = subprocess.run(
        [pdfinfo, str(pdf_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        return 0
    m = re.search(r"^Pages:\s*(\d+)", proc.stdout, re.MULTILINE)
    return int(m.group(1)) if m else 0


def _discover_repo_pdfs(repo_root: Path, edition: str | None = None) -> list[tuple[str, Path]]:
    """Return `(edition_slug, pdf_path)` pairs discovered under `repo_root/resources/`."""
    res_dir = repo_root / "resources"
    if not res_dir.is_dir():
        return []

    raw_pdfs = [p for p in sorted(res_dir.rglob("*.pdf")) if p.is_file()]
    parent_counts: dict[str, int] = {}
    for pdf in raw_pdfs:
        parts = pdf.relative_to(res_dir).parts
        if len(parts) >= 2 and parts[0] not in ("pdfs", "sources"):
            parent_counts[parts[0]] = parent_counts.get(parts[0], 0) + 1

    found: list[tuple[str, Path]] = []
    for pdf in raw_pdfs:
        rel = pdf.relative_to(res_dir)
        parts = rel.parts
        if (
            len(parts) >= 2
            and parts[0] not in ("pdfs", "sources")
            and parent_counts.get(parts[0], 0) == 1
        ):
            ed_slug = parts[0]
        else:
            ed_slug = re.sub(r"[^a-z0-9_]+", "_", pdf.stem.lower()).strip("_")
        if edition and ed_slug.lower() != edition.lower():
            continue
        found.append((ed_slug, pdf))
    return found


def _extract_pdf_text_streams(pdf_path: Path, out_text_dir: Path) -> list[str]:
    """Extract non-empty embedded text streams page-by-page into `<NNNN>.txt` in a single `pdftotext` pass."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return []

    try:
        proc = subprocess.run(
            [pdftotext, "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []

    raw_pages = proc.stdout.split("\x0c")
    written: list[str] = []
    for idx, page_txt in enumerate(raw_pages, start=1):
        cleaned = page_txt.strip()
        if not cleaned:
            continue
        out_text_dir.mkdir(parents=True, exist_ok=True)
        folio_id = f"{idx:04d}"
        target = out_text_dir / f"{folio_id}.txt"
        target.write_text(page_txt.rstrip() + "\n", encoding="utf-8")
        written.append(folio_id)
    return written


def _extract_pdf_embedded_graphics(
    pdf_path: Path,
    out_gfx_dir: Path,
    extract_vector_svg: bool = False,
) -> list[str]:
    """Extract sub-page embedded raster figures via `pdfimages` (and optional vector SVGs via `pdftocairo`)."""
    extracted: list[str] = []
    pdfimages = shutil.which("pdfimages")

    if pdfimages:
        try:
            list_proc = subprocess.run(
                [pdfimages, "-list", str(pdf_path)],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=300,
                check=False,
            )
            list_stdout = list_proc.stdout or ""
        except subprocess.TimeoutExpired:
            list_stdout = ""
        # Parse `pdfimages -list` rows: page num type width height ...
        page_img_counts: dict[int, int] = {}
        page_dims: list[tuple[int, int, int]] = []
        for ln in list_stdout.splitlines()[2:]:
            cols = ln.split()
            if len(cols) >= 5 and cols[0].isdigit() and cols[1].isdigit():
                pg = int(cols[0])
                img_type = cols[2].lower()
                if img_type in ("smask", "stencil"):
                    continue
                w = int(cols[3]) if cols[3].isdigit() else 0
                h = int(cols[4]) if cols[4].isdigit() else 0
                if w < 32 or h < 32:
                    continue
                page_img_counts[pg] = page_img_counts.get(pg, 0) + 1
                page_dims.append((pg, w, h))

        # Determine if PDF is purely 1 full-page scan image per page vs containing embedded figures
        has_subpage_or_multi = any(cnt > 1 for cnt in page_img_counts.values())
        if not has_subpage_or_multi and page_dims:
            max_h = max(h for _, _, h in page_dims)
            if any(h < max_h * 0.80 for _, _, h in page_dims):
                has_subpage_or_multi = True

        # Skip MRC 3-layer full-page scan decompositions when every page has uniform 2-3 scan layers
        if has_subpage_or_multi and len(page_img_counts) > 20:
            avg_per_page = sum(page_img_counts.values()) / max(1, len(page_img_counts))
            if 1.8 <= avg_per_page <= 3.2 and page_dims:
                max_h = max(h for _, _, h in page_dims)
                full_cnt = sum(1 for _, _, h in page_dims if h >= max_h * 0.85)
                if full_cnt >= len(page_img_counts) * 0.8:
                    has_subpage_or_multi = False

        if has_subpage_or_multi:
            with tempfile.TemporaryDirectory() as tmpd:
                prefix = Path(tmpd) / "img"
                try:
                    subprocess.run(
                        [pdfimages, "-png", "-p", str(pdf_path), str(prefix)],
                        capture_output=True,
                        timeout=600,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    pass
                raw_imgs = sorted(Path(tmpd).glob("img-*.png"))
                if raw_imgs:
                    from PIL import Image

                    # Measure median full-page height if present so full-page scan backdrops are skipped
                    heights = []
                    for p in raw_imgs[:40]:
                        try:
                            with Image.open(p) as im:
                                heights.append(im.height)
                        except OSError:
                            heights.extend(())
                    max_obs_h = max(heights) if heights else 0

                    per_page_seq: dict[str, int] = {}
                    for p in raw_imgs:
                        m_pg = re.match(r"^img-(\d+)-\d+\.png$", p.name)
                        if not m_pg:
                            continue
                        pg_num = int(m_pg.group(1))
                        w, h = 0, 0
                        try:
                            with Image.open(p) as im:
                                w, h = im.size
                        except OSError:
                            w, h = 0, 0
                        if w < 40 or h < 40:
                            continue
                        # Skip full-page scan backdrops when page has >1 layer or uniform scan pages
                        if (
                            max_obs_h >= 1200
                            and h >= int(max_obs_h * 0.90)
                            and page_img_counts.get(pg_num, 1) == 1
                        ):
                            continue
                        folio_id = f"{pg_num:04d}"
                        seq = per_page_seq.get(folio_id, 0) + 1
                        per_page_seq[folio_id] = seq
                        out_gfx_dir.mkdir(parents=True, exist_ok=True)
                        dest = out_gfx_dir / f"{folio_id}-img{seq}.png"
                        shutil.copy2(p, dest)
                        extracted.append(dest.name)

    if extract_vector_svg:
        pdftocairo = shutil.which("pdftocairo")
        total_pages = _get_pdf_page_count(pdf_path)
        if pdftocairo and total_pages > 0:
            out_gfx_dir.mkdir(parents=True, exist_ok=True)
            for pg in range(1, total_pages + 1):
                svg_dest = out_gfx_dir / f"{pg:04d}.svg"
                if not svg_dest.is_file():
                    subprocess.run(
                        [
                            pdftocairo,
                            "-svg",
                            "-f",
                            str(pg),
                            "-l",
                            str(pg),
                            str(pdf_path),
                            str(svg_dest),
                        ],
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                if svg_dest.is_file():
                    extracted.append(svg_dest.name)

    return extracted


def ingest_single_pdf(
    repo_root: Path,
    pdf_path: Path,
    *,
    edition_slug: str,
    dpi: int = 300,
    preserve_color: bool = False,
    extract_text: bool = True,
    extract_graphics: bool = True,
    extract_vector_svg: bool = False,
    first_page: int | None = None,
    last_page: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Render 4-digit `<NNNN>.png` folio scans, harvest text/graphics, and update `folio_map.json`."""
    repo_root = repo_root.resolve()
    pdf_path = pdf_path.resolve()
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return {"ok": False, "pdf": str(pdf_path), "error": "pdftoppm not installed"}

    total_pages = _get_pdf_page_count(pdf_path)
    start_p = max(1, first_page or 1)
    end_p = min(total_pages, last_page) if (last_page and total_pages) else (last_page or total_pages)
    if end_p <= 0:
        return {"ok": False, "pdf": str(pdf_path), "error": "Could not determine PDF page count"}

    edition_dir = repo_root / "resources" / edition_slug
    folios_dir = edition_dir / "folios"
    folios_dir.mkdir(parents=True, exist_ok=True)

    # 1. Render missing `<NNNN>.png` folio scans via resumable 25-page pdftoppm chunks
    rendered_new = 0
    missing_pages = [
        p for p in range(start_p, end_p + 1) if force or not (folios_dir / f"{p:04d}.png").is_file()
    ]
    if missing_pages:
        chunk_size = 25
        c_start = missing_pages[0]
        max_missing = missing_pages[-1]
        while c_start <= max_missing:
            c_end = min(c_start + chunk_size - 1, end_p)
            if force or any(not (folios_dir / f"{p:04d}.png").is_file() for p in range(c_start, c_end + 1)):
                with tempfile.TemporaryDirectory() as tmpd:
                    prefix = Path(tmpd) / "page"
                    cmd = [pdftoppm, "-png"]
                    if not preserve_color:
                        cmd.append("-gray")
                    cmd.extend(
                        [
                            "-r",
                            str(dpi),
                            "-f",
                            str(c_start),
                            "-l",
                            str(c_end),
                            str(pdf_path),
                            str(prefix),
                        ]
                    )
                    subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=600,
                        check=True,
                    )
                    for gen_png in sorted(Path(tmpd).glob("page-*.png")):
                        m_num = re.search(r"page-0*(\d+)\.png$", gen_png.name)
                        if not m_num:
                            continue
                        pg_num = int(m_num.group(1))
                        dest_png = folios_dir / f"{pg_num:04d}.png"
                        if force or not dest_png.is_file():
                            shutil.move(str(gen_png), str(dest_png))
                            rendered_new += 1
            c_start = c_end + 1

    opt_stats: dict[str, Any] = {}

    # 2. Extract embedded text stream if present
    text_folios: list[str] = []
    if extract_text:
        text_folios = _extract_pdf_text_streams(pdf_path, edition_dir / "extracted_text")

    # 3. Extract embedded raster/vector graphics if present
    graphic_files: list[str] = []
    if extract_graphics:
        graphic_files = _extract_pdf_embedded_graphics(
            pdf_path,
            edition_dir / "extracted_graphics",
            extract_vector_svg=extract_vector_svg,
        )

    # 4. Update `folio_map.json` and `pdf_manifest.json`
    all_folio_pngs = sorted(folios_dir.glob("[0-9][0-9][0-9][0-9].png"))
    fmap_path = edition_dir / "folio_map.json"
    existing_fmap: dict[str, Any] = {}
    if fmap_path.is_file():
        try:
            loaded = json.loads(fmap_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing_fmap = loaded
        except (json.JSONDecodeError, OSError):
            existing_fmap = {}

    folios_table = (
        existing_fmap.setdefault("folios", {})
        if isinstance(existing_fmap.get("folios"), dict)
        else existing_fmap
    )
    for png in all_folio_pngs:
        fid = png.stem
        rel_posix = png.relative_to(repo_root).as_posix()
        folios_table.setdefault(fid, rel_posix)
        folios_table.setdefault(f"{edition_slug}:{fid}", rel_posix)

    fmap_path.write_text(json.dumps(existing_fmap, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "edition": edition_slug,
        "source_pdf": pdf_path.relative_to(repo_root).as_posix()
        if pdf_path.is_relative_to(repo_root)
        else str(pdf_path),
        "total_pages": total_pages,
        "dpi": dpi,
        "preserve_color": preserve_color,
        "folio_png_count": len(all_folio_pngs),
        "rendered_new_count": rendered_new,
        "extracted_text_pages": len(text_folios),
        "extracted_graphics_count": len(graphic_files),
        "extracted_graphics": graphic_files[:100],
    }
    (edition_dir / "pdf_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if opt_stats:
        manifest["scan_optimization"] = opt_stats
    manifest["ok"] = True
    return manifest


def ingest_repo_pdfs(
    repo_root: str | Path,
    *,
    pdf: str | Path | None = None,
    edition: str | None = None,
    dpi: int = 300,
    preserve_color: bool = False,
    extract_text: bool = True,
    extract_graphics: bool = True,
    extract_vector_svg: bool = False,
    first_page: int | None = None,
    last_page: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Ingest one or all archival PDFs under `repo_root/resources/`."""
    root = Path(repo_root).expanduser().resolve()
    targets: list[tuple[str, Path]] = []
    if pdf:
        p = Path(pdf).expanduser()
        if not p.is_absolute():
            p = (root / p).resolve()
        if not p.is_file():
            return {"ok": False, "repo": root.name, "error": f"PDF not found: {p}"}
        ed = edition or re.sub(r"[^a-z0-9_]+", "_", p.stem.lower()).strip("_")
        targets.append((ed, p))
    else:
        targets = _discover_repo_pdfs(root, edition=edition)

    if not targets:
        return {"ok": False, "repo": root.name, "error": "No PDFs found in resources/"}

    results = []
    for ed_slug, pdf_file in targets:
        res = ingest_single_pdf(
            root,
            pdf_file,
            edition_slug=ed_slug,
            dpi=dpi,
            preserve_color=preserve_color,
            extract_text=extract_text,
            extract_graphics=extract_graphics,
            extract_vector_svg=extract_vector_svg,
            first_page=first_page,
            last_page=last_page,
            force=force,
        )
        results.append(res)

    return {
        "ok": all(r.get("ok") for r in results),
        "repo": root.name,
        "pdf_count": len(results),
        "editions": results,
    }
