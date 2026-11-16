"""Deterministic archival PDF ingestion: 300-DPI folio PNG scans, text streams, embedded graphics, and folio_map.json."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .folio_links import optimize_repo_folio_scans


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

    found: list[tuple[str, Path]] = []
    for pdf in sorted(res_dir.rglob("*.pdf")):
        if not pdf.is_file():
            continue
        rel = pdf.relative_to(res_dir)
        parts = rel.parts
        if len(parts) >= 2 and parts[0] not in ("pdfs", "sources"):
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

    proc = subprocess.run(
        [pdftotext, "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
        check=False,
    )
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
        list_proc = subprocess.run(
            [pdfimages, "-list", str(pdf_path)],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
            check=False,
        )
        # Parse `pdfimages -list` rows: page num type width height ...
        page_img_counts: dict[int, int] = {}
        page_dims: list[tuple[int, int, int]] = []
        for ln in (list_proc.stdout or "").splitlines()[2:]:
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

        if has_subpage_or_multi:
            with tempfile.TemporaryDirectory() as tmpd:
                prefix = Path(tmpd) / "img"
                subprocess.run(
                    [pdfimages, "-png", "-p", str(pdf_path), str(prefix)],
                    capture_output=True,
                    timeout=300,
                    check=False,
                )
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

    # 1. Render missing `<NNNN>.png` folio scans via pdftoppm
    rendered_new = 0
    need_render = force or any(not (folios_dir / f"{p:04d}.png").is_file() for p in range(start_p, end_p + 1))
    if need_render:
        with tempfile.TemporaryDirectory() as tmpd:
            prefix = Path(tmpd) / "page"
            subprocess.run(
                [
                    pdftoppm,
                    "-png",
                    "-r",
                    str(dpi),
                    "-f",
                    str(start_p),
                    "-l",
                    str(end_p),
                    str(pdf_path),
                    str(prefix),
                ],
                capture_output=True,
                timeout=900,
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

    # Losslessly optimize scans (skip grayscale conversion when preserve_color=True)
    opt_stats: dict[str, Any] = {}
    if not preserve_color:
        opt_stats = optimize_repo_folio_scans(repo_root, force_grayscale=False)

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
