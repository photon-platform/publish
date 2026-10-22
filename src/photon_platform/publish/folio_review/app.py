"""Flask web application for Folio Review & Vetting.

Run via CLI:
    publish folio
    publish folio --port 5050
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

try:
    from flask import Flask, abort, jsonify, render_template, request, send_from_directory
except ImportError:
    Flask = None  # type: ignore[assignment,misc]
    abort = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    render_template = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_from_directory = None  # type: ignore[assignment]

from .reviews import ReviewManager
from .scanner import FolioScanner, discover_edition_root, infer_project_and_edition


def _extract_graphics_for_json(json_path: Path) -> None:
    """Extract graphic crops defined in `<folio>.json` from `<folio>.png`."""
    try:
        from geometor.euclid.graphic_tool import extract_graphics

        extract_graphics(json_path)
        return
    except ImportError:
        pass

    from PIL import Image

    data = json.loads(json_path.read_text(encoding="utf-8"))
    folio = data.get("folio", json_path.stem)
    scan_path = json_path.parent / f"{folio}.png"
    if not scan_path.exists():
        raise FileNotFoundError(f"Scan image not found: {scan_path}")

    with Image.open(scan_path) as img:
        for g in data.get("graphics", []):
            bbox = g.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x, y, w, h = [int(v) for v in bbox]
            gid = g.get("id", "g1")
            out_file = g.get("file", f"{folio}.{gid}.png")
            out_path = json_path.parent / out_file
            cropped = img.crop((x, y, x + w, y + h))
            cropped.save(out_path)


def create_app(
    root_dir: Optional[Path] = None,
    project_title: Optional[str] = None,
    edition_label: Optional[str] = None,
) -> Flask:
    """Create and configure the Flask review application."""
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    edition_root = discover_edition_root(root_dir)
    resolved_project, resolved_edition = infer_project_and_edition(
        edition_root,
        project_title=project_title,
        edition_label=edition_label,
    )

    scanner = FolioScanner(root_dir=edition_root)
    reviews = ReviewManager(storage_path=scanner.root_dir / "folio_reviews.json")

    app.config["SCANNER"] = scanner
    app.config["REVIEWS"] = reviews
    app.config["PROJECT_TITLE"] = resolved_project
    app.config["EDITION_LABEL"] = resolved_edition
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.context_processor
    def inject_branding() -> Dict[str, str]:
        return {
            "project_title": app.config["PROJECT_TITLE"],
            "edition_label": app.config["EDITION_LABEL"],
        }

    # -------------------------------------------------------------------------
    # HTML Routes
    # -------------------------------------------------------------------------

    @app.route("/")
    def dashboard() -> str:
        """Render the main Folio Review Dashboard."""
        stats = scanner.get_summary_stats()
        rev_stats = reviews.get_review_stats()
        return render_template(
            "dashboard.html",
            stats=stats,
            rev_stats=rev_stats,
            volumes=scanner.volumes,
        )

    @app.route("/folio/<volume>/<folio>")
    def folio_view(volume: str, folio: str) -> str:
        """Render the side-by-side Folio Workbench."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            abort(404, description=f"Folio {folio} in {volume} not found.")

        review_record = reviews.get_review(volume, folio)
        prev_folio, next_folio = scanner.get_neighbors(volume, folio)

        return render_template(
            "folio.html",
            folio=detail,
            review=review_record,
            prev_folio=prev_folio,
            next_folio=next_folio,
        )

    @app.route("/media/<path:rel_path>")
    def serve_media(rel_path: str):
        """Serve folio scan PNGs, cropped graphic PNGs, and SVGs from resources/<edition>."""
        prefix = f"{scanner.root_dir.name}/"
        if rel_path.startswith(prefix) and not (scanner.root_dir / rel_path).exists():
            rel_path = rel_path[len(prefix) :]
        return send_from_directory(str(scanner.root_dir), rel_path)

    # -------------------------------------------------------------------------
    # JSON API Routes
    # -------------------------------------------------------------------------

    @app.route("/api/folios")
    def api_folios():
        """Return filtered list of folios with their review statuses."""
        vol_filter = request.args.get("volume", "").strip()
        sec_filter = request.args.get("section", "").strip()
        status_filter = request.args.get("status", "").strip()
        review_filter = request.args.get("review_status", "").strip()
        search_q = request.args.get("q", "").strip().lower()

        all_folios = scanner.scan()
        all_reviews = reviews.get_all_reviews()

        results = []
        for f in all_folios:
            key = f["key"]
            rev = all_reviews.get(key, {"status": "unreviewed", "notes": ""})
            rev_status = rev.get("status", "unreviewed")

            if vol_filter and f["volume"] != vol_filter:
                continue
            if sec_filter and not (
                f["section_path"] == sec_filter
                or f["section_path"].startswith(sec_filter + "/")
                or f.get("book", "") == sec_filter
            ):
                continue
            if status_filter == "transcribed" and not f["has_md"]:
                continue
            if status_filter == "missing_transcription" and f["has_md"]:
                continue
            if status_filter == "has_notes" and not f["has_notes"]:
                continue
            if status_filter == "missing_notes" and f["has_notes"]:
                continue
            if status_filter == "has_graphics" and not f["has_graphics"]:
                continue
            if status_filter == "has_svg" and not f.get("has_svg"):
                continue
            if status_filter == "missing_svg" and (not f["has_graphics"] or f.get("has_svg")):
                continue
            if status_filter == "missing_crops" and f["missing_crops_count"] == 0:
                continue
            if review_filter and review_filter != "all" and rev_status != review_filter:
                continue

            if search_q:
                sec_spaced = f["section_path"].replace("_", " ")
                haystack = (
                    f"{f['folio']} {f['title']} {f['section_path']} {sec_spaced} "
                    f"{f.get('book', '')} {f['page']} {rev.get('notes', '')}"
                ).lower()
                search_q_spaced = search_q.replace("_", " ")
                if search_q not in haystack and search_q_spaced not in haystack:
                    continue

            item = dict(f)
            item["review_status"] = rev_status
            item["review_notes"] = rev.get("notes", "")
            results.append(item)

        return jsonify({"count": len(results), "folios": results})

    @app.route("/api/folio/<volume>/<folio>/review", methods=["GET", "POST"])
    def api_folio_review(volume: str, folio: str):
        """Get or update vetting status and checklist for a folio."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        if request.method == "GET":
            return jsonify(reviews.get_review(volume, folio))

        data: Dict[str, Any] = request.get_json(force=True) or {}
        status = data.get("status", "unreviewed")
        checklist = data.get("checklist")
        notes = data.get("notes", "")
        reviewer = data.get("reviewer", "phi")

        record = reviews.set_review(
            volume=volume,
            folio=folio,
            status=status,
            checklist=checklist,
            notes=notes,
            reviewer=reviewer,
        )
        return jsonify({"success": True, "review": record})

    @app.route("/api/folio/<volume>/<folio>/save_text", methods=["POST"])
    def api_save_text(volume: str, folio: str):
        """Save edited RST/Markdown transcription or notes directly to disk."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        data: Dict[str, Any] = request.get_json(force=True) or {}
        target = data.get("target")  # "md" or "notes"
        content = data.get("content", "")

        full_dir = Path(detail["full_dir_path"])
        if target == "md":
            rst_file = full_dir / f"{folio}.rst"
            md_file = full_dir / f"{folio}.md"
            file_path = rst_file if (rst_file.exists() or not md_file.exists()) else md_file
        elif target == "notes":
            notes_rst = full_dir / f"{folio}.notes.rst"
            notes_md = full_dir / f"{folio}.notes.md"
            file_path = notes_rst if (notes_rst.exists() or not notes_md.exists()) else notes_md
        else:
            return jsonify({"success": False, "error": "Invalid target (must be 'md' or 'notes')"}), 400

        file_path.write_text(content, encoding="utf-8")
        scanner.scan(force=True)
        updated = scanner.get_folio_detail(volume, folio)

        return jsonify(
            {
                "success": True,
                "md_html": updated["md_html"] if updated else "",
                "notes_html": updated["notes_html"] if updated else "",
            }
        )

    @app.route("/api/folio/<volume>/<folio>/extract_graphics", methods=["POST"])
    def api_extract_graphics(volume: str, folio: str):
        """Trigger graphic extraction from <folio>.json."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        full_dir = Path(detail["full_dir_path"])
        json_path = full_dir / f"{folio}.json"
        if not json_path.exists():
            return jsonify({"success": False, "error": f"{folio}.json does not exist"}), 404

        try:
            _extract_graphics_for_json(json_path)
            scanner.scan(force=True)
            updated = scanner.get_folio_detail(volume, folio)
            return jsonify({"success": True, "graphics": updated["graphics"] if updated else []})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/folio/<volume>/<folio>/update_graphic_bbox", methods=["POST"])
    def api_update_graphic_bbox(volume: str, folio: str):
        """Update bounding box coordinates for a graphic in <folio>.json and re-extract."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        data: Dict[str, Any] = request.get_json(force=True) or {}
        graphic_id = data.get("id")
        bbox = data.get("bbox")  # [x, y, w, h]
        re_extract = data.get("extract", True)

        if not graphic_id or not isinstance(bbox, list) or len(bbox) != 4:
            return jsonify({"success": False, "error": "Invalid graphic id or bbox"}), 400

        full_dir = Path(detail["full_dir_path"])
        json_path = full_dir / f"{folio}.json"
        if not json_path.exists():
            return jsonify({"success": False, "error": f"{folio}.json does not exist"}), 404

        try:
            json_data = json.loads(json_path.read_text(encoding="utf-8"))
            found = False
            for g in json_data.get("graphics", []):
                if g.get("id") == graphic_id:
                    g["bbox"] = [int(v) for v in bbox]
                    found = True
                    break

            if not found:
                return jsonify({"success": False, "error": f"Graphic {graphic_id} not found"}), 404

            json_path.write_text(json.dumps(json_data, indent=2) + "\n", encoding="utf-8")

            if re_extract:
                _extract_graphics_for_json(json_path)

            scanner.scan(force=True)
            updated = scanner.get_folio_detail(volume, folio)
            return jsonify({"success": True, "graphics": updated["graphics"] if updated else []})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/folio/<volume>/<folio>/set_graphic_format", methods=["POST"])
    def api_set_graphic_format(volume: str, folio: str):
        """Switch graphic reference in <folio>.rst (or <folio>.md) between .png and .svg."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        data: Dict[str, Any] = request.get_json(force=True) or {}
        graphic_id = data.get("id", "g1")
        target_format = data.get("format", "svg")  # "svg" or "png"
        if target_format not in ("svg", "png"):
            return jsonify({"success": False, "error": "Invalid format (must be 'svg' or 'png')"}), 400

        full_dir = Path(detail["full_dir_path"])
        rst_path = full_dir / f"{folio}.rst"
        md_path = full_dir / f"{folio}.md"

        active_path = rst_path if rst_path.exists() else (md_path if md_path.exists() else None)
        if not active_path:
            return jsonify({"success": False, "error": f"No {folio}.rst or {folio}.md found"}), 404

        png_name = f"{folio}.{graphic_id}.png"
        svg_name = f"{folio}.{graphic_id}.svg"

        if target_format == "svg" and not (full_dir / svg_name).exists():
            return jsonify({"success": False, "error": f"{svg_name} does not exist yet"}), 400

        text_content = active_path.read_text(encoding="utf-8")
        if target_format == "svg":
            new_content = re.sub(
                rf"(\.\.\s+(?:picture|image|figure)::\s+[^\n]*?){re.escape(png_name)}",
                rf"\g<1>{svg_name}",
                text_content,
            )
            new_content = re.sub(
                rf"(\]\([^\)]*?){re.escape(png_name)}(\))",
                rf"\g<1>{svg_name}\g<2>",
                new_content,
            )
        else:
            new_content = re.sub(
                rf"(\.\.\s+(?:picture|image|figure)::\s+[^\n]*?){re.escape(svg_name)}",
                rf"\g<1>{png_name}",
                text_content,
            )
            new_content = re.sub(
                rf"(\]\([^\)]*?){re.escape(svg_name)}(\))",
                rf"\g<1>{png_name}\g<2>",
                new_content,
            )

        active_path.write_text(new_content, encoding="utf-8")
        scanner.scan(force=True)
        updated = scanner.get_folio_detail(volume, folio)
        return jsonify(
            {
                "success": True,
                "md_content": updated["md_content"] if updated else "",
                "md_html": updated["md_html"] if updated else "",
                "graphics": updated["graphics"] if updated else [],
            }
        )

    @app.route("/api/folio/<volume>/<folio>/graphic/<graphic_id>/save_svg", methods=["POST"])
    def api_save_graphic_svg(volume: str, folio: str, graphic_id: str):
        """Save or update vector SVG file (<folio>.<id>.svg) on disk."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        data: Dict[str, Any] = request.get_json(force=True) or {}
        svg_code = data.get("svg", "").strip()
        if not svg_code or "<svg" not in svg_code:
            return jsonify({"success": False, "error": "Invalid SVG content"}), 400

        full_dir = Path(detail["full_dir_path"])
        svg_path = full_dir / f"{folio}.{graphic_id}.svg"
        svg_path.write_text(svg_code + "\n", encoding="utf-8")

        scanner.scan(force=True)
        updated = scanner.get_folio_detail(volume, folio)
        return jsonify(
            {
                "success": True,
                "graphics": updated["graphics"] if updated else [],
            }
        )

    @app.route("/api/folio/<volume>/<folio>/graphic/<graphic_id>/save_py", methods=["POST"])
    def api_save_graphic_py(volume: str, folio: str, graphic_id: str):
        """Save or update Python construction script (<folio>.<id>.py) on disk."""
        if folio.isdigit():
            folio = f"{int(folio):04d}"

        detail = scanner.get_folio_detail(volume, folio)
        if not detail:
            return jsonify({"success": False, "error": "Folio not found"}), 404

        data: Dict[str, Any] = request.get_json(force=True) or {}
        py_code = data.get("py", "").rstrip()
        if not py_code:
            return jsonify({"success": False, "error": "Empty Python script content"}), 400

        full_dir = Path(detail["full_dir_path"])
        py_path = full_dir / f"{folio}.{graphic_id}.py"
        py_path.write_text(py_code + "\n", encoding="utf-8")

        scanner.scan(force=True)
        updated = scanner.get_folio_detail(volume, folio)
        return jsonify(
            {
                "success": True,
                "graphics": updated["graphics"] if updated else [],
            }
        )

    @app.route("/api/apparatus")
    def api_apparatus():
        """Return the edition's citation and glossary registries."""
        return jsonify(scanner.get_apparatus())

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        """Force rescan of all volumes on disk."""
        scanner.scan(force=True)
        scanner.get_apparatus(force=True)
        return jsonify({"success": True, "stats": scanner.get_summary_stats()})

    return app


def main() -> None:
    """CLI entry point for launching the Folio Review web application."""
    parser = argparse.ArgumentParser(description="Launch the PHOTON Publish Folio Review web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5050, help="Port to listen on (default: 5050)")
    parser.add_argument("--root", default=None, help="Optional path to resources/<edition> or repository root")
    parser.add_argument("--title", default=None, help="Optional project title override")
    parser.add_argument("--edition", default=None, help="Optional edition label override")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()

    root_path = Path(args.root).resolve() if args.root else None
    app = create_app(root_dir=root_path, project_title=args.title, edition_label=args.edition)
    print(
        f"Starting {app.config['PROJECT_TITLE']} ({app.config['EDITION_LABEL']}) "
        f"Folio Review at http://{args.host}:{args.port}"
    )
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
