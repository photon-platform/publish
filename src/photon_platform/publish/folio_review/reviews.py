"""Persistent review and vetting status tracker for folios.

Stores vetting checklist, review status, and notes in `folio_reviews.json`
inside the edition's `resources/<edition>/` directory.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ReviewManager:
    """Manages reading and writing vetting / review records for folios."""

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            self.storage_path = Path.cwd() / "resources" / "folio_reviews.json"
        else:
            self.storage_path = Path(storage_path)

        self._reviews: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _make_key(self, volume: str, folio: str) -> str:
        if folio.isdigit():
            folio = f"{int(folio):04d}"
        return f"{volume}:{folio}"

    def _load(self) -> None:
        """Load review records from JSON storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._reviews = json.load(f)
            except Exception:
                self._reviews = {}
        else:
            self._reviews = {}

    def _save(self) -> None:
        """Save review records to JSON storage file."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._reviews, f, indent=2, sort_keys=True)

    def get_review(self, volume: str, folio: str) -> Dict[str, Any]:
        """Get review record for a specific folio, returning default if unreviewed."""
        self._load()
        key = self._make_key(volume, folio)
        default_record = {
            "status": "unreviewed",
            "checklist": {
                "transcription_verified": False,
                "math_verified": False,
                "notes_verified": False,
                "graphics_verified": False,
            },
            "notes": "",
            "updated_at": None,
            "reviewer": None,
        }
        return self._reviews.get(key, default_record)

    def set_review(
        self,
        volume: str,
        folio: str,
        status: str,
        checklist: Optional[Dict[str, bool]] = None,
        notes: str = "",
        reviewer: Optional[str] = "phi",
    ) -> Dict[str, Any]:
        """Save or update review record for a specific folio."""
        self._load()
        key = self._make_key(volume, folio)

        valid_statuses = {"unreviewed", "verified", "needs_fix", "flagged"}
        if status not in valid_statuses:
            status = "unreviewed"

        record = {
            "status": status,
            "checklist": checklist
            or {
                "transcription_verified": False,
                "math_verified": False,
                "notes_verified": False,
                "graphics_verified": False,
            },
            "notes": notes.strip(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "reviewer": reviewer or "reviewer",
        }

        self._reviews[key] = record
        self._save()
        return record

    def get_all_reviews(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored reviews."""
        self._load()
        return dict(self._reviews)

    def get_review_stats(self) -> Dict[str, int]:
        """Return count breakdown of review statuses."""
        self._load()
        stats = {
            "unreviewed": 0,
            "verified": 0,
            "needs_fix": 0,
            "flagged": 0,
            "total_reviewed": 0,
        }
        for rec in self._reviews.values():
            st = rec.get("status", "unreviewed")
            if st in stats:
                stats[st] += 1
            if st in {"verified", "needs_fix", "flagged"}:
                stats["total_reviewed"] += 1
        return stats
