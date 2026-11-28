"""Unified Page Card model, `cards.json` manifest emitter, and Intersphinx-backed CardRegistry.

Every Sphinx document built by `photon-platform/publish` resolves to one canonical
`Card` record with:

- Hybrid curated description (`:description:` > `.. summary::` > `.. enunciation::` > fallback)
- Dual visual slots: small project/org `emblem` medallion + larger `image` hero/diagram
- Structured facets (author, dates, era, languages, tags, bibliographic metadata)
- Record inheritance via `:card_ref:` (pulling canonical identity from another page or site)
- Automatic export to `docs/cards.json` alongside `docs/objects.inv`
- Lazy cross-project resolution piggybacking on `intersphinx_mapping` (local sibling first,
  cached HTTPS fallback, graceful degradation to `objects.inv`).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from docutils import nodes

SCHEMA_VERSION = "photon.card.v1"

# Frontmatter fields extracted into structured bibliographic metadata
BIB_FIELD_KEYS = (
    "work_type",
    "editors",
    "editor",
    "translators",
    "translator",
    "publisher",
    "place",
    "series",
    "volume",
    "issue",
    "pages",
    "isbn",
    "doi",
    "issn",
    "orig_year",
    "edition",
    "citation_key",
    "journal",
    "booktitle",
    "locus",
)


def _split_list(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        return [v.strip() for v in val.split(",") if v.strip()]
    if isinstance(val, (list, tuple, set)):
        return [str(v).strip() for v in val if str(v).strip()]
    return []


def _clean_plain_text(text: str, max_len: int = 240) -> str:
    """Normalize whitespace and strip inline RST markup leaks for crisp card copy."""
    txt = re.sub(r"\s+", " ", (text or "").strip())
    if not txt:
        return ""
    if len(txt) <= max_len:
        return txt
    cut = txt[: max_len - 1].rsplit(" ", 1)[0].rstrip(" ,;:-—–")
    return f"{cut}…"


def _absolute_asset_url(base_url: str, rel_or_abs: str) -> str:
    val = (rel_or_abs or "").strip()
    if not val:
        return ""
    if val.startswith(("http://", "https://", "data:")):
        return val
    if not base_url:
        return val
    return urljoin(base_url.rstrip("/") + "/", val.lstrip("/"))


def _read_inline_svg(svg_path: Path, *, as_thumbnail: bool = True) -> str:
    if not svg_path.is_file() or svg_path.suffix.lower() != ".svg":
        return ""
    try:
        from .images.directive import prepare_inline_svg

        return prepare_inline_svg(str(svg_path), as_thumbnail=as_thumbnail) or ""
    except (ImportError, OSError, ValueError):
        try:
            return svg_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""


@dataclass
class Card:
    """Canonical representation of any page or entity record across publish."""

    id: str
    docname: str
    title: str
    type: str = "article"
    inventory: str = ""
    is_remote: bool = False
    url: str = ""
    subtitle: str = ""
    kicker: str = ""
    description: str = ""
    description_html: str = ""
    description_source: str = "empty"

    # Dual visual slots: small project medallion (emblem) + larger hero visual (image)
    emblem: str = ""
    emblem_svg: str = ""
    image: str = ""
    image_alt: str = ""
    image_width: str = ""
    image_svg: str = ""
    social_image: str = ""

    # Facets & links
    author: str = ""
    author_doc: str = ""
    author_ref: str = ""
    year: Any = None
    year_sort: int | None = None
    year_label: str = ""
    year_display: str = ""
    death_year: Any = None
    death_year_sort: int | None = None
    death_label: str = ""
    lifespan: str = ""
    edition_year: Any = None
    era: str = ""
    series: str = ""
    native_title: str = ""
    languages: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    date: str = ""
    published_at: str = ""
    site_url: str = ""
    github_url: str = ""
    companion_tracks: list[dict[str, Any]] = field(default_factory=list)

    # Scholarly apparatus & federation metadata
    bib: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    card_ref: str = ""
    local_note_html: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_manifest_dict(self, base_url: str = "") -> dict[str, Any]:
        """Serialize for `docs/cards.json` (compact, portable, absolute URLs)."""
        page_url = self.url
        if not page_url and base_url:
            if self.docname == "index":
                page_url = base_url.rstrip("/") + "/"
            elif self.docname.endswith("/index"):
                page_url = f"{base_url.rstrip('/')}/{self.docname[:-5]}"
            else:
                page_url = f"{base_url.rstrip('/')}/{self.docname}.html"

        data: dict[str, Any] = {
            "id": self.id,
            "docname": self.docname,
            "type": self.type,
            "title": self.title,
            "url": page_url,
        }
        if self.subtitle:
            data["subtitle"] = self.subtitle
        if self.kicker:
            data["kicker"] = self.kicker
        if self.description:
            data["description"] = self.description
        if self.description_source:
            data["description_source"] = self.description_source
        if self.emblem:
            data["emblem"] = _absolute_asset_url(base_url, self.emblem)
        if self.image:
            data["image"] = _absolute_asset_url(base_url, self.image)
        if self.image_alt:
            data["image_alt"] = self.image_alt
        if self.social_image:
            data["social_image"] = _absolute_asset_url(base_url, self.social_image)

        facets: dict[str, Any] = {}
        for key in (
            "author",
            "author_doc",
            "author_ref",
            "year",
            "year_sort",
            "year_label",
            "year_display",
            "death_year",
            "death_year_sort",
            "death_label",
            "lifespan",
            "edition_year",
            "era",
            "series",
            "native_title",
            "date",
            "published_at",
            "site_url",
            "github_url",
        ):
            val = getattr(self, key)
            if val not in (None, "", []):
                facets[key] = val
        if self.languages:
            facets["languages"] = list(self.languages)
        if self.tags:
            facets["tags"] = list(self.tags)
        if self.categories:
            facets["categories"] = list(self.categories)
        if facets:
            data["facets"] = facets
        if self.bib:
            data["bib"] = dict(self.bib)
        if self.labels:
            data["labels"] = list(self.labels)
        return data

    @classmethod
    def from_manifest_dict(
        cls,
        raw: dict[str, Any],
        *,
        inventory: str = "",
        site_info: dict[str, Any] | None = None,
    ) -> Card:
        """Hydrate a remote `Card` from a `cards.json` entry."""
        site_info = site_info or {}
        facets = raw.get("facets") or {}
        docname = str(raw.get("docname") or "")
        card_id = str(raw.get("id") or (f"{inventory}:{docname}" if inventory else docname))
        kicker = str(raw.get("kicker") or "")
        if not kicker and site_info:
            org_name = site_info.get("org_name") or site_info.get("org") or ""
            repo_name = site_info.get("repo_name") or site_info.get("repo") or inventory
            if org_name and repo_name:
                kicker = f"{org_name} • {repo_name}"
            else:
                kicker = str(org_name or repo_name)

        emblem = str(raw.get("emblem") or site_info.get("emblem") or "")
        desc = str(raw.get("description") or "")
        return cls(
            id=card_id,
            docname=docname,
            title=str(raw.get("title") or docname),
            type=str(raw.get("type") or "article"),
            inventory=inventory,
            is_remote=bool(inventory),
            url=str(raw.get("url") or facets.get("site_url") or ""),
            subtitle=str(raw.get("subtitle") or facets.get("native_title") or facets.get("lifespan") or ""),
            kicker=kicker,
            description=desc,
            description_html=f"<p>{desc}</p>" if desc else "",
            description_source="remote",
            emblem=emblem,
            image=str(raw.get("image") or ""),
            image_alt=str(raw.get("image_alt") or raw.get("title") or ""),
            social_image=str(raw.get("social_image") or ""),
            author=str(facets.get("author") or ""),
            author_doc=str(facets.get("author_doc") or ""),
            author_ref=str(facets.get("author_ref") or ""),
            year=facets.get("year"),
            year_sort=facets.get("year_sort"),
            year_label=str(facets.get("year_label") or ""),
            year_display=str(facets.get("year_display") or ""),
            death_year=facets.get("death_year"),
            death_year_sort=facets.get("death_year_sort"),
            death_label=str(facets.get("death_label") or ""),
            lifespan=str(facets.get("lifespan") or ""),
            edition_year=facets.get("edition_year"),
            era=str(facets.get("era") or ""),
            series=str(facets.get("series") or ""),
            native_title=str(facets.get("native_title") or ""),
            languages=_split_list(facets.get("languages")),
            tags=_split_list(facets.get("tags")),
            categories=_split_list(facets.get("categories")),
            date=str(facets.get("date") or ""),
            published_at=str(facets.get("published_at") or ""),
            site_url=str(facets.get("site_url") or raw.get("url") or ""),
            github_url=str(facets.get("github_url") or site_info.get("github_url") or ""),
            bib=dict(raw.get("bib") or {}),
            labels=list(raw.get("labels") or []),
        )

    def to_template_dict(self) -> dict[str, Any]:
        """Produce a Jinja-friendly dictionary compatible with both `components/card.html`
        and legacy `collection/index.html` / `collection/directory.html` templates."""
        d: dict[str, Any] = dict(self.meta)
        d.update(
            {
                "id": self.id,
                "docname": self.docname,
                "inventory": self.inventory,
                "is_remote": self.is_remote,
                "url": self.url,
                "type": self.type,
                "title": self.title,
                "subtitle": self.subtitle,
                "kicker": self.kicker,
                "description": self.description,
                "description_source": self.description_source,
                "excerpt": self.description,
                "excerpt_text": self.description_html or (f"<p>{self.description}</p>" if self.description else ""),
                "emblem": self.emblem,
                "emblem_svg": self.emblem_svg,
                "image": self.image,
                "excerpt_figure_filename": self.image or None,
                "excerpt_figure_alt": self.image_alt or self.title,
                "excerpt_figure_width": self.image_width or "",
                "excerpt_svg_content": self.image_svg or "",
                "social_image": self.social_image,
                "author": self.author,
                "author_doc": self.author_doc,
                "author_ref": self.author_ref,
                "year": self.year,
                "year_sort": self.year_sort,
                "year_label": self.year_label,
                "year_display": self.year_display,
                "death_year": self.death_year,
                "death_year_sort": self.death_year_sort,
                "death_label": self.death_label,
                "lifespan": self.lifespan,
                "edition_year": self.edition_year,
                "era": self.era,
                "series": self.series,
                "native_title": self.native_title,
                "languages": self.languages,
                "tags": self.tags,
                "categories": self.categories,
                "category": self.categories,
                "date": self.date,
                "published_at": self.published_at,
                "site_url": self.site_url,
                "github_url": self.github_url,
                "companion_tracks": self.companion_tracks,
                "bib": self.bib,
                "labels": self.labels,
                "card_ref": self.card_ref,
                "local_note_html": self.local_note_html,
            }
        )
        return d

    def tooltip_text(self) -> str:
        """Concise hover tooltip summary for inline `:person:`, `:cite:`, `:term:` links."""
        parts = [self.title]
        if self.lifespan:
            parts[0] = f"{self.title} ({self.lifespan})"
        elif self.year_display:
            parts[0] = f"{self.title} ({self.year_display})"
        if self.author and self.author.lower() not in self.title.lower():
            parts.insert(0, self.author)
        head = " — ".join(parts)
        if self.description:
            short = _clean_plain_text(self.description, max_len=140)
            return f"{head}: {short}"
        return head


def _find_summary_node(doctree: nodes.document | None) -> nodes.Element | None:
    """Return the first explicit `.. summary::` block in `doctree`, if present."""
    if doctree is None or not hasattr(doctree, "findall"):
        return None
    for el in doctree.findall(nodes.Element):
        classes = el.get("classes", []) if hasattr(el, "get") else []
        if "card-summary" in classes:
            return el
    return None


def _find_enunciation_node(doctree: nodes.document | None) -> nodes.Element | None:
    if doctree is None or not hasattr(doctree, "findall"):
        return None
    for el in doctree.findall(nodes.Element):
        classes = el.get("classes", []) if hasattr(el, "get") else []
        if "enunciation" in classes:
            return el
    return None


def _find_fallback_paragraph(doctree: nodes.document | None) -> nodes.Element | None:
    """Return the first clean body paragraph/blockquote outside admonitions/figures/headers."""
    if doctree is None or not hasattr(doctree, "findall"):
        return None
    skip_ancestors = {
        "admonition",
        "figure",
        "signature",
        "collapse",
        "author-overline",
        "title-page",
        "folio-milestone",
        "caption",
        "card-embed",
    }
    for node in doctree.findall(nodes.Element):
        if not isinstance(node, (nodes.paragraph, nodes.block_quote)):
            continue
        anc = node.parent
        skip = False
        while anc is not None:
            if isinstance(anc, (nodes.Admonition, nodes.figure, nodes.caption)):
                skip = True
                break
            anc_classes = set(anc.get("classes", [])) if hasattr(anc, "get") else set()
            if anc_classes & skip_ancestors:
                skip = True
                break
            anc = getattr(anc, "parent", None)
        if skip:
            continue
        txt = node.astext().strip()
        if len(txt) >= 16 and txt.lower() != "the works of":
            return node
    return None


def resolve_site_emblem(env: Any, meta: dict[str, Any] | None = None) -> tuple[str, str]:
    """Resolve the small project/org medallion `(rel_uri, inline_svg)`."""
    meta = meta or {}
    srcdir = Path(getattr(env, "srcdir", ".")).resolve()
    cfg = getattr(env, "config", None)
    repo = str(getattr(cfg, "repo", "") or "").strip() if cfg else ""

    candidates: list[str] = []
    explicit = str(meta.get("emblem") or meta.get("medallion") or "").strip()
    if explicit:
        candidates.append(explicit.lstrip("/"))
    cfg_emblem = str(getattr(cfg, "card_emblem", "") or "").strip() if cfg else ""
    if cfg_emblem:
        candidates.append(cfg_emblem.lstrip("/"))
    if repo:
        candidates.append(f"_static/medallions/{repo}.svg")
    candidates.extend(
        [
            "_static/medallion.svg",
            "_static/logo.svg",
            "_static/logo.png",
        ]
    )

    for rel in candidates:
        disk = srcdir / rel
        if disk.is_file():
            svg = _read_inline_svg(disk, as_thumbnail=True) if disk.suffix.lower() == ".svg" else ""
            return rel, svg
    return "", ""


def _resolve_card_kicker(env: Any, meta: dict[str, Any]) -> str:
    explicit = str(meta.get("kicker") or "").strip()
    if explicit:
        return explicit
    cfg = getattr(env, "config", None)
    org_name = str(getattr(cfg, "org_name", "") or "").strip() if cfg else ""
    repo_name = str(getattr(cfg, "repo_name", "") or getattr(cfg, "repo", "") or "").strip() if cfg else ""
    if org_name and repo_name and org_name.lower() != repo_name.lower():
        return f"{org_name} • {repo_name}"
    return org_name or repo_name


def _collect_doc_labels(env: Any, docname: str) -> list[str]:
    """Collect Sphinx std domain labels targeting `docname`."""
    labels: list[str] = []
    with contextlib.suppress(AttributeError, KeyError, TypeError):
        std = env.domains.get("std") if hasattr(env, "domains") else None
        if std is not None:
            for lbl, entry in getattr(std, "labels", {}).items():
                if entry and entry[0] == docname and lbl not in labels:
                    labels.append(lbl)
            for lbl, entry in getattr(std, "anonlabels", {}).items():
                if entry and entry[0] == docname and lbl not in labels:
                    labels.append(lbl)
    return labels


def resolve_document_card(
    env: Any,
    builder: Any,
    docname: str,
    doctree: nodes.document | None = None,
    *,
    registry: CardRegistry | None = None,
) -> Card:
    """Resolve a single canonical `Card` for local document `docname`."""
    from .directives.collection import (
        _normalize_log_meta,
        _resolve_representative_figure,
        format_year_display,
        parse_year_sort_value,
        render_node_html,
    )

    raw_meta = dict((getattr(env, "metadata", {}) or {}).get(docname, {}) or {})
    meta = _normalize_log_meta(docname, raw_meta)

    if doctree is None and hasattr(env, "get_doctree"):
        with contextlib.suppress(Exception):
            doctree = env.get_doctree(docname)

    title_node = (getattr(env, "titles", {}) or {}).get(docname)
    doc_title = title_node.astext().strip() if title_node is not None else docname.split("/")[-1].replace("_", " ").title()
    card_title = str(meta.get("card_title") or meta.get("title") or doc_title).strip() or doc_title

    # Hybrid description precedence:
    # 1. Explicit frontmatter (:card_description: / :description: / :summary: / non-auto :excerpt:)
    # 2. Explicit body directive (.. summary::)
    # 3. Proposition enunciation (.. enunciation::)
    # 4. Clean fallback paragraph (flagged as description_source='fallback')
    description = ""
    description_html = ""
    description_source = "empty"

    explicit_desc = ""
    for k in ("card_description", "description", "summary"):
        v = str(meta.get(k) or "").strip()
        if v:
            explicit_desc = v
            break
    if not explicit_desc and meta.get("excerpt") and not meta.get("_enunciation_excerpt"):
        explicit_desc = str(meta.get("excerpt") or "").strip()

    if explicit_desc:
        description = _clean_plain_text(explicit_desc)
        description_html = f"<p>{description}</p>"
        description_source = "meta"
    else:
        summary_node = _find_summary_node(doctree)
        if summary_node is not None:
            description = _clean_plain_text(summary_node.astext())
            description_html = render_node_html(builder, summary_node) if builder else f"<p>{description}</p>"
            description_source = "summary"
        else:
            enunc_node = _find_enunciation_node(doctree)
            if enunc_node is not None:
                description = _clean_plain_text(enunc_node.astext())
                description_html = render_node_html(builder, enunc_node) if builder else f"<p>{description}</p>"
                description_source = "enunciation"
            else:
                fb_node = _find_fallback_paragraph(doctree)
                if fb_node is not None:
                    description = _clean_plain_text(fb_node.astext())
                    description_html = render_node_html(builder, fb_node) if builder else f"<p>{description}</p>"
                    description_source = "fallback"
                elif meta.get("excerpt"):
                    description = _clean_plain_text(str(meta.get("excerpt")))
                    description_html = f"<p>{description}</p>"
                    description_source = "meta"

    # Media: small medallion (emblem) + larger hero visual (image)
    emblem_uri, emblem_svg = resolve_site_emblem(env, meta)
    image_uri = ""
    image_alt = card_title
    image_width = ""
    image_svg = ""

    # Support :image: and :card_image: alongside existing :featured_image:
    media_meta = dict(meta)
    for img_key in ("card_image", "image"):
        if media_meta.get(img_key) and not media_meta.get("featured_image"):
            media_meta["featured_image"] = media_meta[img_key]
            break

    fig_info = _resolve_representative_figure(env, builder, docname, media_meta, doctree)
    if fig_info:
        image_uri = str(fig_info.get("uri") or "")
        image_alt = str(fig_info.get("alt") or card_title)
        image_width = str(fig_info.get("width") or "")
        if fig_info.get("svg_disk_path"):
            image_svg = _read_inline_svg(Path(fig_info["svg_disk_path"]), as_thumbnail=True)

    # Companion tracks
    companion_tracks: list[dict[str, Any]] = []
    with contextlib.suppress(Exception):
        from .book import detect_companion_tracks

        tracks = detect_companion_tracks(env, docname)
        if len(tracks) > 1:
            companion_tracks = tracks

    # Chronology & facets
    raw_year_sort = meta.get("year_sort") if meta.get("year_sort") not in (None, "") else meta.get("year")
    parsed_year = parse_year_sort_value(raw_year_sort)
    year_disp = format_year_display(meta.get("year"), meta.get("year_label"))
    parsed_death = parse_year_sort_value(meta.get("death_year"))

    # Structured bibliography fields
    bib: dict[str, Any] = {}
    for bk in BIB_FIELD_KEYS:
        if meta.get(bk) not in (None, ""):
            bib[bk] = meta[bk]

    # Normalize entity type
    cfg = getattr(env, "config", None)
    master_doc = getattr(cfg, "master_doc", "index") if cfg else "index"
    entity_type = str(meta.get("type") or "").strip()
    if not entity_type:
        if docname == master_doc:
            entity_type = "project"
        elif meta.get("layout") == "book" and docname.endswith("/index"):
            entity_type = "book"
        else:
            entity_type = "article"

    subtitle = str(
        meta.get("card_subtitle")
        or meta.get("subtitle")
        or meta.get("native_title")
        or meta.get("book_subtitle")
        or meta.get("lifespan")
        or ""
    ).strip()

    categories = _split_list(meta.get("categories") or meta.get("category"))
    card_ref = str(meta.get("card_ref") or "").strip()

    card = Card(
        id=docname,
        docname=docname,
        title=card_title,
        type=entity_type,
        subtitle=subtitle,
        kicker=_resolve_card_kicker(env, meta),
        description=description,
        description_html=description_html,
        description_source=description_source,
        emblem=emblem_uri,
        emblem_svg=emblem_svg,
        image=image_uri,
        image_alt=image_alt,
        image_width=image_width,
        image_svg=image_svg,
        social_image=str(meta.get("social_image") or "").strip(),
        author=str(meta.get("author") or "").strip(),
        author_doc=str(meta.get("author_doc") or "").strip(),
        author_ref=str(meta.get("author_ref") or "").strip(),
        year=meta.get("year"),
        year_sort=parsed_year,
        year_label=str(meta.get("year_label") or "").strip(),
        year_display=year_disp,
        death_year=meta.get("death_year"),
        death_year_sort=parsed_death,
        death_label=str(meta.get("death_label") or "").strip(),
        lifespan=str(meta.get("lifespan") or "").strip(),
        edition_year=meta.get("edition_year"),
        era=str(meta.get("era") or "").strip(),
        series=str(meta.get("series") or "").strip(),
        native_title=str(meta.get("native_title") or "").strip(),
        languages=_split_list(meta.get("languages")),
        tags=_split_list(meta.get("tags")),
        categories=categories,
        date=str(meta.get("date") or "").strip(),
        published_at=str(meta.get("published_at") or "").strip(),
        site_url=str(meta.get("site_url") or "").strip(),
        github_url=str(meta.get("github_url") or "").strip(),
        companion_tracks=companion_tracks,
        bib=bib,
        labels=_collect_doc_labels(env, docname),
        card_ref=card_ref,
        meta=meta,
    )

    # Inherit unset fields from canonical remote/local Card when `:card_ref:` is set
    if card_ref and registry is not None:
        ref_card = registry.resolve(card_ref)
        if ref_card is not None:
            _merge_inherited_card(card, ref_card)

    return card


def _merge_inherited_card(local: Card, canonical: Card) -> None:
    """Fill missing identity/media/bibliographic fields on `local` from `canonical`."""
    if not local.subtitle:
        local.subtitle = canonical.subtitle
    if local.description_source in ("empty", "fallback") and canonical.description:
        local.description = canonical.description
        local.description_html = canonical.description_html or f"<p>{canonical.description}</p>"
        local.description_source = "remote"
    if not local.image and canonical.image:
        local.image = canonical.image
        local.image_alt = canonical.image_alt or local.title
    if not local.emblem and canonical.emblem:
        local.emblem = canonical.emblem
    for attr in (
        "author",
        "author_doc",
        "author_ref",
        "year",
        "year_sort",
        "year_label",
        "year_display",
        "death_year",
        "death_year_sort",
        "death_label",
        "lifespan",
        "edition_year",
        "era",
        "series",
        "native_title",
        "site_url",
        "github_url",
    ):
        if getattr(local, attr) in (None, ""):
            setattr(local, attr, getattr(canonical, attr))
    if not local.languages and canonical.languages:
        local.languages = list(canonical.languages)
    if canonical.bib:
        merged_bib = dict(canonical.bib)
        merged_bib.update(local.bib)
        local.bib = merged_bib
    if not local.site_url and canonical.url:
        local.site_url = canonical.url


class CardRegistry:
    """Lazy, Intersphinx-backed Card resolver across local docs and sister sites."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.env = app.env
        self.builder = getattr(app, "builder", None)
        self._manifests: dict[str, dict[str, Any] | None] = {}
        self._cards_by_inv: dict[str, dict[str, Card]] = {}

    def _inventory_sources(self) -> dict[str, tuple[str, list[Path]]]:
        """Collect `(base_url, local_card_json_candidates)` from `intersphinx_mapping` and `card_sites`."""
        sources: dict[str, tuple[str, list[Path]]] = {}
        cfg = getattr(self.env, "config", None)
        srcdir = Path(getattr(self.env, "srcdir", ".")).resolve()
        project_root = srcdir.parent

        mapping = getattr(cfg, "intersphinx_mapping", None) or {}
        for inv_name, spec in mapping.items():
            if not isinstance(spec, (tuple, list)) or len(spec) < 1:
                continue
            base_url = str(spec[0] or "").rstrip("/")
            inv_locs = spec[1] if len(spec) > 1 else None
            local_candidates: list[Path] = []
            if isinstance(inv_locs, str):
                inv_locs = (inv_locs,)
            if isinstance(inv_locs, (tuple, list)):
                for loc in inv_locs:
                    if isinstance(loc, str) and loc and not loc.startswith(("http://", "https://")):
                        p = Path(loc)
                        if not p.is_absolute():
                            p = (srcdir / p).resolve()
                        local_candidates.append(p.parent / "cards.json")
            # Sibling convention fallback (`../<inv_name>/docs/cards.json`)
            local_candidates.append((project_root.parent / inv_name / "docs" / "cards.json").resolve())
            sources[inv_name] = (base_url, local_candidates)

        # Optional lightweight `card_sites` dict for org portals (lazy-only, not in intersphinx_mapping)
        extra_sites = getattr(cfg, "card_sites", None) or {}
        for inv_name, site_spec in extra_sites.items():
            if inv_name in sources:
                continue
            if isinstance(site_spec, str):
                base_url = site_spec.rstrip("/")
                local_candidates = [(project_root.parent / inv_name / "docs" / "cards.json").resolve()]
            elif isinstance(site_spec, (tuple, list)) and site_spec:
                base_url = str(site_spec[0]).rstrip("/")
                local_candidates = []
                if len(site_spec) > 1 and site_spec[1]:
                    p = Path(str(site_spec[1]))
                    if not p.is_absolute():
                        p = (srcdir / p).resolve()
                    local_candidates.append(p if p.name == "cards.json" else p / "cards.json")
                local_candidates.append((project_root.parent / inv_name / "docs" / "cards.json").resolve())
            else:
                continue
            sources[inv_name] = (base_url, local_candidates)

        return sources

    def _cache_dir(self) -> Path:
        outdir = Path(getattr(self.app, "outdir", ".")).resolve()
        return outdir.parent / ".cards_cache"

    def load_manifest(self, inventory: str) -> dict[str, Any] | None:
        """Lazily load `cards.json` for `inventory` (local sibling first, HTTPS cached fallback)."""
        if inventory in self._manifests:
            return self._manifests[inventory]

        sources = self._inventory_sources()
        spec = sources.get(inventory)

        # Also support same-org sibling convention on disk even if not explicitly mapped
        srcdir = Path(getattr(self.env, "srcdir", ".")).resolve()
        project_root = srcdir.parent
        local_candidates: list[Path] = []
        base_url = ""
        if spec:
            base_url, local_candidates = spec
        else:
            local_candidates.append((project_root.parent / inventory / "docs" / "cards.json").resolve())

        for cand in local_candidates:
            if cand.is_file():
                try:
                    data = json.loads(cand.read_text(encoding="utf-8"))
                    self._manifests[inventory] = data
                    return data
                except (OSError, json.JSONDecodeError):
                    pass

        # Remote HTTPS fetch with disk cache
        if base_url.startswith(("http://", "https://")):
            cache_file = self._cache_dir() / f"{re.sub(r'[^a-zA-Z0-9_.-]+', '_', inventory)}.json"
            if cache_file.is_file() and (time.time() - cache_file.stat().st_mtime) < 86400:
                try:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    self._manifests[inventory] = data
                    return data
                except (OSError, json.JSONDecodeError):
                    pass

            timeout = getattr(getattr(self.env, "config", None), "intersphinx_timeout", 3) or 3
            cards_url = f"{base_url.rstrip('/')}/cards.json"
            try:
                req = urllib.request.Request(cards_url, headers={"User-Agent": "photon-publish/cards"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
                data = json.loads(raw)
                with contextlib.suppress(OSError):
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(raw, encoding="utf-8")
                self._manifests[inventory] = data
                return data
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
                pass

        self._manifests[inventory] = None
        return None

    def _hydrate_inventory(self, inventory: str) -> dict[str, Card]:
        if inventory in self._cards_by_inv:
            return self._cards_by_inv[inventory]
        manifest = self.load_manifest(inventory)
        hydrated: dict[str, Card] = {}
        if isinstance(manifest, dict):
            site_info = manifest.get("site") or {}
            for docname, raw_card in (manifest.get("cards") or {}).items():
                if isinstance(raw_card, dict):
                    raw_copy = dict(raw_card)
                    raw_copy.setdefault("docname", docname)
                    hydrated[docname] = Card.from_manifest_dict(
                        raw_copy, inventory=inventory, site_info=site_info
                    )
        self._cards_by_inv[inventory] = hydrated
        return hydrated

    def _fallback_from_objects_inv(self, inventory: str, target: str) -> Card | None:
        """Graceful degradation to standard Sphinx `objects.inv` when a remote site has no `cards.json`."""
        named = getattr(self.env, "intersphinx_named_inventory", None) or {}
        inv_data = named.get(inventory)
        if not isinstance(inv_data, dict):
            return None
        for domain_type in ("std:doc", "std:label"):
            bucket = inv_data.get(domain_type) or {}
            if target in bucket:
                _proj, _ver, uri, disp = bucket[target]
                title = disp if disp and disp != "-" else target
                return Card(
                    id=f"{inventory}:{target}",
                    docname=target,
                    title=str(title),
                    type="reference",
                    inventory=inventory,
                    is_remote=True,
                    url=str(uri),
                    kicker=inventory,
                    description_source="remote",
                )
        return None

    def resolve(self, address: str, *, fromdocname: str = "") -> Card | None:
        """Resolve a local or cross-project (`inventory:target`) card address."""
        addr = (address or "").strip()
        if not addr:
            return None

        # Cross-project Intersphinx address: `inventory:target`
        if ":" in addr and not addr.startswith(("http://", "https://")):
            inventory, target = addr.split(":", 1)
            inventory = inventory.strip()
            target = target.strip().lstrip("/")
            if not inventory or not target:
                return None

            manifest = self.load_manifest(inventory)
            cards_map = self._hydrate_inventory(inventory)
            if cards_map:
                if target in cards_map:
                    return cards_map[target]
                if f"{target}/index" in cards_map:
                    return cards_map[f"{target}/index"]
                labels_map = (manifest or {}).get("labels") or {}
                if target in labels_map and labels_map[target] in cards_map:
                    return cards_map[labels_map[target]]
                # Match case-insensitive label or suffix
                low = target.lower()
                for lbl, docn in labels_map.items():
                    if lbl.lower() == low and docn in cards_map:
                        return cards_map[docn]

            return self._fallback_from_objects_inv(inventory, target)

        # Local address (`#label`, `/path`, or relative path)
        local_cards: dict[str, Card] = getattr(self.env, "publish_cards", {}) or {}
        if addr.startswith("#"):
            lbl = addr[1:].strip()
            std = self.env.domains.get("std") if hasattr(self.env, "domains") else None
            if std is not None:
                entry = getattr(std, "labels", {}).get(lbl) or getattr(std, "anonlabels", {}).get(lbl)
                if entry and entry[0] in local_cards:
                    return local_cards[entry[0]]
            for card in local_cards.values():
                if lbl in card.labels:
                    return card
            return None

        if addr.startswith("/"):
            cand = addr.lstrip("/")
        elif fromdocname and "/" in fromdocname:
            base_dir = fromdocname.rsplit("/", 1)[0]
            cand = os.path.normpath(f"{base_dir}/{addr}").replace(os.sep, "/")
        else:
            cand = addr

        for key in (cand, f"{cand}/index", addr.lstrip("/")):
            if key in local_cards:
                return local_cards[key]
            found_docs = getattr(self.env, "found_docs", set()) or set()
            if key in found_docs:
                resolved = resolve_document_card(self.env, self.builder, key, registry=self)
                local_cards[key] = resolved
                return resolved

        return None

    def query(self, pattern: str) -> list[Card]:
        """Query multiple remote cards using `inv:*`, `inv:prefix/*`, or `inv:type=book`."""
        pat = (pattern or "").strip()
        if ":" not in pat:
            c = self.resolve(pat)
            return [c] if c else []

        inventory, expr = pat.split(":", 1)
        inventory = inventory.strip()
        expr = expr.strip()

        # Wildcard across all known inventories (`*:type=book`)
        if inventory == "*":
            results: list[Card] = []
            for inv_name in self._inventory_sources():
                results.extend(self.query(f"{inv_name}:{expr}"))
            return results

        cards_map = self._hydrate_inventory(inventory)
        if not cards_map:
            return []

        if expr == "*":
            return list(cards_map.values())
        if expr.startswith("type="):
            want_type = expr.split("=", 1)[1].strip()
            return [c for c in cards_map.values() if c.type == want_type]
        if expr.endswith("/*"):
            prefix = expr[:-1].lstrip("/")
            return [c for d, c in cards_map.items() if d.startswith(prefix)]

        one = self.resolve(pat)
        return [one] if one else []

    def resolve_by_role(self, role_type: str, key: str) -> Card | None:
        """Resolve an apparatus role (`person`, `cite`, `term`) across configured inventories."""
        slug = re.sub(r"[^a-z0-9]+", "-", (key or "").lower()).strip("-")
        if not slug:
            return None
        prefix_map = {"person": "person", "cite": "cite", "term": "term"}
        dir_map = {"person": "people", "cite": "bibliography", "term": "glossary"}
        lbl = f"{prefix_map.get(role_type, role_type)}-{slug}"
        sub_dir = dir_map.get(role_type, role_type)

        # Direct explicit inventory prefix inside role target (e.g. `euclid:heath/index`)
        if ":" in key:
            direct = self.resolve(key)
            if direct is not None:
                return direct

        # Search configured inventories (author repo matching slug first, then `catalog`, then others)
        inv_names = list(self._inventory_sources().keys())
        prioritized: list[str] = []
        for pref in (slug, "catalog", "geometor", "photon"):
            if pref in inv_names and pref not in prioritized:
                prioritized.append(pref)
        for inv in inv_names:
            if inv not in prioritized and inv not in ("python", "sympy"):
                prioritized.append(inv)

        for inv in prioritized:
            # 1. Exact label match (`person-euclid`, `cite-...`, `term-...`)
            c = self.resolve(f"{inv}:{lbl}")
            if c is not None:
                return c
            # 2. Conventional directory path (`people/<slug>`, `bibliography/<slug>`, `glossary/<slug>`)
            c = self.resolve(f"{inv}:{sub_dir}/{slug}")
            if c is not None:
                return c
            # 3. Author repo root (`euclid:index` when looking up `:person:` `euclid`)
            if role_type == "person" and inv == slug:
                c = self.resolve(f"{inv}:index")
                if c is not None:
                    return c
        return None


def get_card_registry(app: Any) -> CardRegistry:
    """Get or create the per-build `CardRegistry` instance (stored on `app`, never pickled in `env`)."""
    reg = getattr(app, "_photon_card_registry", None)
    if reg is None or getattr(reg, "app", None) is not app:
        reg = CardRegistry(app)
        app._photon_card_registry = reg
    builder = getattr(app, "builder", None)
    if builder is not None:
        builder._photon_card_registry = reg
    return reg


_NAME_FIELD_RE = re.compile(
    r"^(:(?:author|authors|editor|editors|translator|translators|publisher|place|series):[ \t]+)(.+)$"
)
_INITIAL_RE = re.compile(r"(^|[ \t])([A-Za-z])\.([ \t])")


def _escape_frontmatter_initials(app: Any, docname: str, source: list[str]) -> None:
    """Prevent Docutils from parsing leading name initials (e.g. `:editors: W. D. Ross`)
    as RST enumerated lists in top-of-file frontmatter."""
    if not source:
        return
    lines = source[0].splitlines(keepends=True)
    changed = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            break
        if not stripped.startswith(":"):
            break
        m = _NAME_FIELD_RE.match(line.rstrip("\r\n"))
        if m:
            prefix, val = m.group(1), m.group(2)
            # Run twice to handle consecutive single-letter initials like `W. D. Ross`
            escaped = _INITIAL_RE.sub(r"\1\2\\.\3", val)
            escaped = _INITIAL_RE.sub(r"\1\2\\.\3", escaped)
            if escaped != val:
                eol = line[len(line.rstrip("\r\n")) :]
                lines[idx] = f"{prefix}{escaped}{eol}"
                changed = True
    if changed:
        source[0] = "".join(lines)


def _attach_registry_to_builder(app: Any) -> None:
    get_card_registry(app)


def build_all_cards(app: Any, env: Any) -> None:
    """Resolve `Card` objects for every document in `env.found_docs` on `env-updated`."""
    registry = get_card_registry(app)
    cards: dict[str, Card] = {}
    uncurated: list[str] = []

    for docname in sorted(getattr(env, "found_docs", set()) or ()):
        card = resolve_document_card(env, getattr(app, "builder", None), docname, registry=registry)
        cards[docname] = card
        if card.description_source in ("fallback", "empty"):
            uncurated.append(docname)

    env.publish_cards = cards
    env.publish_cards_stats = {
        "total": len(cards),
        "curated": len(cards) - len(uncurated),
        "fallback": len(uncurated),
        "uncurated_docs": uncurated,
    }


def emit_cards_manifest(app: Any, exception: Exception | None) -> None:
    """Write `docs/cards.json` right beside `docs/objects.inv` after HTML builds."""
    if exception is not None:
        return
    builder = getattr(app, "builder", None)
    if builder is None or getattr(builder, "format", "") != "html":
        return

    env = app.env
    cards: dict[str, Card] = getattr(env, "publish_cards", None) or {}
    if not cards:
        build_all_cards(app, env)
        cards = getattr(env, "publish_cards", {})

    from .social_meta import (
        resolve_org_brand,
        resolve_site_base_url,
        resolve_site_human_title,
    )

    cfg = getattr(env, "config", None)
    html_ctx = getattr(cfg, "html_context", None) or {} if cfg else {}
    srcdir = Path(getattr(env, "srcdir", ".")).resolve()
    project_root = srcdir.parent
    base_url = resolve_site_base_url(env, project_root=project_root)
    site_title = resolve_site_human_title(env, html_ctx)
    org_brand = resolve_org_brand(env, html_ctx)
    org = str((getattr(cfg, "org", "") if cfg else "") or html_ctx.get("github_user") or "").strip()
    if not org and project_root.parent.name in ("geometor", "photon-platform", "phiarchitect", "harmonic-resonance"):
        org = project_root.parent.name
    repo = str((getattr(cfg, "repo", "") if cfg else "") or html_ctx.get("github_repo") or project_root.name).strip()
    repo_name = str((getattr(cfg, "repo_name", "") if cfg else "") or html_ctx.get("repo_name") or repo).strip()
    emblem_rel, _ = resolve_site_emblem(env)

    labels_index: dict[str, str] = {}
    manifest_cards: dict[str, dict[str, Any]] = {}
    for docname, card in sorted(cards.items()):
        manifest_cards[docname] = card.to_manifest_dict(base_url=base_url)
        for lbl in card.labels:
            labels_index.setdefault(lbl, docname)

    payload = {
        "schema": SCHEMA_VERSION,
        "site": {
            "org": org,
            "org_name": org_brand,
            "repo": repo,
            "repo_name": repo_name,
            "title": site_title,
            "base_url": base_url,
            "github_url": f"https://github.com/{org}/{repo}" if org and repo else "",
            "emblem": _absolute_asset_url(base_url, emblem_rel) if emblem_rel else "",
        },
        "cards": manifest_cards,
        "labels": labels_index,
    }

    outdir = Path(app.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_file = outdir / "cards.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def setup(app: Any) -> dict[str, Any]:
    """Register unified Card resolution and `cards.json` export with Sphinx."""
    app.add_config_value("card_emblem", "", "html")
    app.add_config_value("card_sites", {}, "env")
    app.connect("builder-inited", _attach_registry_to_builder)
    app.connect("source-read", _escape_frontmatter_initials)
    app.connect("env-updated", build_all_cards)
    app.connect("build-finished", emit_cards_manifest)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
