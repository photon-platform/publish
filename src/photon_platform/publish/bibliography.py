"""Scholarly Bibliography formatting (Chicago, MLA, APA, BibTeX) and automated
bidirectional passage backlinks (`.. citation-formats::` and `.. backlinks::`).

Works directly from unified `Card` objects (local or inherited via `:card_ref:`)
and Sphinx's `:cite:`, `:person:`, and `:term:` inline role occurrences, grouping
parallel companion tracks (e.g., `LA · EN`, `EL · EN`) automatically.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docutils import nodes

from .cards import Card, get_card_registry, resolve_document_card
from .directives.card import PendingBacklinks, PendingCitationFormats


def _slugify(val: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (val or "").lower()).strip("-")


def _bib_key(card: Card) -> str:
    explicit = str(card.bib.get("citation_key") or "").strip()
    if explicit:
        return explicit
    author_part = _slugify(card.author.split(",")[0].split()[-1]) if card.author else ""
    year_part = str(card.edition_year or card.year or "").strip().lstrip("-")
    title_words = [w for w in re.findall(r"[a-zA-Z0-9]+", card.title.lower()) if w not in ("the", "a", "an", "of", "de", "in")]
    title_part = title_words[0] if title_words else _slugify(card.docname)
    parts = [p for p in (author_part, year_part, title_part) if p]
    return "_".join(parts) or _slugify(card.id)


def _bib_entry_type(card: Card) -> str:
    wt = str(card.bib.get("work_type") or "").strip().lower()
    if wt in ("article", "journal", "paper"):
        return "article"
    if wt in ("incollection", "chapter", "inbook"):
        return "incollection"
    if wt in ("inproceedings", "conference"):
        return "inproceedings"
    if wt in ("phdthesis", "thesis", "dissertation"):
        return "phdthesis"
    if wt in ("misc", "manuscript", "web", "online"):
        return "misc"
    return "book"


def _effective_pub_year(card: Card) -> str:
    if card.edition_year not in (None, ""):
        return str(card.edition_year).strip()
    if card.year_display:
        return card.year_display
    if card.year_label:
        return card.year_label
    if card.year not in (None, ""):
        try:
            y = int(card.year)
            return f"{abs(y)} BCE" if y < 0 else str(y)
        except (TypeError, ValueError):
            return str(card.year)
    return "n.d."


def _orig_year_display(card: Card) -> str:
    if card.bib.get("orig_year"):
        return str(card.bib["orig_year"]).strip()
    if card.edition_year not in (None, "") and (card.year_display or card.year_label or card.year not in (None, "")):
        return card.year_display or card.year_label or (
            f"{abs(int(card.year))} BCE" if isinstance(card.year, int) and card.year < 0 else str(card.year)
        )
    return ""


def format_chicago(card: Card) -> str:
    """Format a Chicago Notes & Bibliography entry from `card`."""
    parts: list[str] = []
    if card.author:
        parts.append(f"{card.author.rstrip('.')}.")
    title_str = card.title.rstrip(".")
    if card.native_title and card.native_title.lower() != card.title.lower():
        title_str = f"{title_str} ({card.native_title})"
    parts.append(f"*{title_str}*.")

    editors = str(card.bib.get("editors") or card.bib.get("editor") or "").strip()
    translators = str(card.bib.get("translators") or card.bib.get("translator") or "").strip()
    if editors:
        parts.append(f"Edited by {editors.rstrip('.')}.")
    if translators:
        parts.append(f"Translated by {translators.rstrip('.')}.")

    place = str(card.bib.get("place") or "").strip()
    publisher = str(card.bib.get("publisher") or "").strip()
    pub_year = _effective_pub_year(card)
    pub_bits: list[str] = []
    if place and publisher:
        pub_bits.append(f"{place}: {publisher}")
    elif publisher:
        pub_bits.append(publisher)
    elif place:
        pub_bits.append(place)
    if pub_year:
        pub_bits.append(pub_year)
    if pub_bits:
        parts.append(", ".join(pub_bits) + ".")

    locus = str(card.bib.get("locus") or card.bib.get("pages") or "").strip()
    if locus:
        parts.append(f"{locus.rstrip('.')}.")

    doi = str(card.bib.get("doi") or "").strip()
    url = str(card.site_url or card.url or "").strip()
    if doi:
        parts.append(f"https://doi.org/{doi}.")
    elif url:
        parts.append(f"{url}.")

    return " ".join(parts)


def format_mla(card: Card) -> str:
    """Format an MLA 9th-edition citation entry from `card`."""
    parts: list[str] = []
    if card.author:
        parts.append(f"{card.author.rstrip('.')}.")
    parts.append(f"*{card.title.rstrip('.')}*.")

    editors = str(card.bib.get("editors") or card.bib.get("editor") or "").strip()
    translators = str(card.bib.get("translators") or card.bib.get("translator") or "").strip()
    if editors:
        parts.append(f"Edited by {editors.rstrip(',')},")
    if translators:
        parts.append(f"Translated by {translators.rstrip(',')},")

    publisher = str(card.bib.get("publisher") or "").strip()
    pub_year = _effective_pub_year(card)
    tail = [b for b in (publisher, pub_year) if b]
    if tail:
        parts.append(", ".join(tail) + ".")

    url = str(card.site_url or card.url or "").strip()
    if url:
        parts.append(f"{url}.")
    return " ".join(parts)


def format_apa(card: Card) -> str:
    """Format an APA 7th-edition citation entry from `card`."""
    parts: list[str] = []
    pub_year = _effective_pub_year(card)
    if card.author:
        parts.append(f"{card.author.rstrip('.')} ({pub_year}).")
    else:
        parts.append(f"({pub_year}).")

    editors = str(card.bib.get("editors") or card.bib.get("editor") or "").strip()
    translators = str(card.bib.get("translators") or card.bib.get("translator") or "").strip()
    qualifiers: list[str] = []
    if editors:
        qualifiers.append(f"{editors}, Ed.")
    if translators:
        qualifiers.append(f"{translators}, Trans.")
    qual_str = f" ({'; '.join(qualifiers)})" if qualifiers else ""
    parts.append(f"*{card.title.rstrip('.')}*{qual_str}.")

    publisher = str(card.bib.get("publisher") or "").strip()
    if publisher:
        parts.append(f"{publisher.rstrip('.')}.")

    orig = _orig_year_display(card)
    if orig and orig != pub_year:
        parts.append(f"(Original work composed {orig}).")

    doi = str(card.bib.get("doi") or "").strip()
    url = str(card.site_url or card.url or "").strip()
    if doi:
        parts.append(f"https://doi.org/{doi}")
    elif url:
        parts.append(url)
    return " ".join(parts)


def format_bibtex(card: Card) -> str:
    """Format a standards-compliant BibTeX entry from `card`."""
    entry_type = _bib_entry_type(card)
    key = _bib_key(card)
    fields: list[tuple[str, str]] = []

    if card.author:
        fields.append(("author", card.author))
    title_val = card.title
    if card.native_title and card.native_title.lower() != card.title.lower():
        title_val = f"{card.title} ({card.native_title})"
    fields.append(("title", title_val))

    editors = str(card.bib.get("editors") or card.bib.get("editor") or "").strip()
    if editors:
        fields.append(("editor", editors))
    translators = str(card.bib.get("translators") or card.bib.get("translator") or "").strip()
    if translators:
        fields.append(("translator", translators))

    if card.edition_year not in (None, ""):
        fields.append(("year", str(card.edition_year)))
        if card.year not in (None, ""):
            fields.append(("origdate", str(card.year)))
    elif card.year not in (None, ""):
        fields.append(("year", str(card.year)))
    elif card.year_label:
        fields.append(("year", card.year_label))

    for bib_k, out_k in (
        ("journal", "journal"),
        ("booktitle", "booktitle"),
        ("series", "series"),
        ("volume", "volume"),
        ("issue", "number"),
        ("pages", "pages"),
        ("publisher", "publisher"),
        ("place", "address"),
        ("isbn", "isbn"),
        ("doi", "doi"),
    ):
        val = str(card.bib.get(bib_k) or "").strip()
        if val:
            fields.append((out_k, val))

    url = str(card.site_url or card.url or "").strip()
    if url:
        fields.append(("url", url))

    lines = [f"@{entry_type}{{{key},"]
    for idx, (fk, fv) in enumerate(fields):
        comma = "," if idx < len(fields) - 1 else ""
        lines.append(f"  {fk:<10} = {{{fv}}}{comma}")
    lines.append("}")
    return "\n".join(lines)


def format_all_citations(card: Card) -> dict[str, str]:
    return {
        "chicago": format_chicago(card),
        "mla": format_mla(card),
        "apa": format_apa(card),
        "bibtex": format_bibtex(card),
    }


def _md_italics_to_html(text: str) -> str:
    esc = html.escape(text)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)


def render_citation_formats_html(card: Card, *, title: str = "Cite This Work", extra_class: str = "") -> str:
    """Render interactive Chicago / MLA / APA / BibTeX tabs for a detail record."""
    formats = format_all_citations(card)
    box_id = f"cit-{_slugify(card.id or card.title)}"
    order = (("chicago", "Chicago"), ("mla", "MLA"), ("apa", "APA"), ("bibtex", "BibTeX"))

    buttons = []
    panels = []
    for idx, (key, label) in enumerate(order):
        active = " is-active" if idx == 0 else ""
        buttons.append(
            f'<button type="button" class="citation-tab{active}" data-cit-tab="{key}" '
            f'onclick="(function(b){{var box=b.closest(\'.citation-formats-box\');'
            f'box.querySelectorAll(\'.citation-tab\').forEach(function(x){{x.classList.remove(\'is-active\')}});'
            f'box.querySelectorAll(\'.citation-format-panel\').forEach(function(p){{p.classList.remove(\'is-active\')}});'
            f'b.classList.add(\'is-active\');'
            f'box.querySelector(\'[data-cit-panel=&quot;{key}&quot;]\').classList.add(\'is-active\');'
            f'}})(this)">{label}</button>'
        )
        if key == "bibtex":
            body = f"<pre>{html.escape(formats[key])}</pre>"
        else:
            body = f"<p>{_md_italics_to_html(formats[key])}</p>"
        panels.append(f'<div class="citation-format-panel{active}" data-cit-panel="{key}">{body}</div>')

    cls = f"citation-formats-box {html.escape(extra_class)}".strip()
    return (
        f'<section class="{cls}" id="{html.escape(box_id)}">'
        f'<h3 class="citation-formats-heading">{html.escape(title)}</h3>'
        f'<div class="citation-format-tabs">{"".join(buttons)}</div>'
        f'{"".join(panels)}'
        f"</section>"
    )


# ---------------------------------------------------------------------------
# Automated Bidirectional Passage Backlinks (Hoenen-Style Track Grouping)
# ---------------------------------------------------------------------------

TRACK_SUFFIX_RE = re.compile(r"-(en|la|el|grc|de|fr|it|da|summary|notes|commentary)$", re.IGNORECASE)


@dataclass
class RoleOccurrence:
    role_type: str  # 'person' | 'cite' | 'term'
    target: str
    slug: str
    docname: str
    doc_title: str
    section_title: str
    base_group: str  # e.g. 'caput-1/caput-1' so 'caput-1/caput-1' & 'caput-1/caput-1-en' pair cleanly
    track_label: str  # 'LA', 'EN', 'EL', or ''
    occ_id: str
    index_in_doc: int


def _infer_track_and_group(docname: str, meta: dict[str, Any]) -> tuple[str, str]:
    """Return `(base_group, track_label)` so parallel tracks pair cleanly."""
    stem = docname
    m = TRACK_SUFFIX_RE.search(stem)
    if m:
        suffix = m.group(1).lower()
        base_group = stem[: m.start()]
        label = suffix.upper() if len(suffix) <= 3 else suffix.title()
        return base_group, label

    lang = str(meta.get("language") or meta.get("track") or "").strip()
    if lang:
        return stem, lang.upper() if len(lang) <= 3 else lang.title()
    return stem, ""


def _nearest_section_title(node: nodes.Node, fallback: str) -> str:
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, nodes.section):
            for child in cur.children:
                if isinstance(child, nodes.title):
                    return child.astext().strip()
        cur = getattr(cur, "parent", None)
    return fallback


def collect_apparatus_occurrences(app: Any, env: Any) -> None:
    """Scan all doctrees on `env-updated` to build the automated bidirectional backlink index."""
    from .roles.geometry import cite_ref_node, person_ref_node, term_ref_node

    index: dict[tuple[str, str], list[RoleOccurrence]] = defaultdict(list)

    for docname in sorted(getattr(env, "found_docs", set()) or ()):
        try:
            doctree = env.get_doctree(docname)
        except (OSError, KeyError, AttributeError, ValueError):
            continue
        title_node = (getattr(env, "titles", {}) or {}).get(docname)
        doc_title = title_node.astext().strip() if title_node is not None else docname.split("/")[-1]
        doc_meta = (getattr(env, "metadata", {}) or {}).get(docname, {}) or {}
        base_group, track_label = _infer_track_and_group(docname, doc_meta)

        per_doc_counts: dict[tuple[str, str], int] = {}
        node_types = (
            ("cite", cite_ref_node),
            ("person", person_ref_node),
            ("term", term_ref_node),
        )
        for role_type, cls in node_types:
            for n in doctree.findall(cls):
                target = str(n.get("ref_target") or "").strip()
                if not target:
                    continue
                slug = _slugify(target)
                pair = (role_type, target)
                per_doc_counts[pair] = per_doc_counts.get(pair, 0) + 1
                idx_in_doc = per_doc_counts[pair]
                occ_id = f"occ-{role_type}-{slug}-{idx_in_doc}"
                sec_title = _nearest_section_title(n, doc_title)
                occ = RoleOccurrence(
                    role_type=role_type,
                    target=target,
                    slug=slug,
                    docname=docname,
                    doc_title=doc_title,
                    section_title=sec_title,
                    base_group=base_group,
                    track_label=track_label,
                    occ_id=occ_id,
                    index_in_doc=idx_in_doc,
                )
                index[(role_type, slug)].append(occ)

    env.publish_apparatus_backlinks = dict(index)


def _infer_backlink_kind_and_slug(docname: str, meta: dict[str, Any], card: Card | None) -> tuple[str, str]:
    """Infer `(role_type, slug)` from a detail record's path, `:type:`, or Sphinx labels."""
    entity_type = str(meta.get("type") or (card.type if card else "")).strip().lower()
    stem = docname.rsplit("/", 1)[-1]
    if stem == "index" and "/" in docname:
        stem = docname.rsplit("/", 2)[-2]

    if entity_type == "person" or "/people/" in f"/{docname}":
        return "person", _slugify(stem)
    if entity_type in ("reference", "source", "source_record", "book", "book_record") or "/bibliography/" in f"/{docname}":
        return "cite", _slugify(stem)
    if entity_type == "term" or "/glossary/" in f"/{docname}":
        return "term", _slugify(stem)

    if card:
        for lbl in card.labels:
            for pref in ("person-", "cite-", "term-"):
                if lbl.startswith(pref):
                    return pref[:-1], lbl[len(pref) :]
    return "cite", _slugify(stem)


def render_backlinks_html(
    builder: Any,
    fromdocname: str,
    occurrences: list[RoleOccurrence],
    *,
    title: str = "Occurrences in This Work",
    extra_class: str = "",
) -> str:
    """Render Hoenen-style passage backlinks grouped by `(base_group, index_in_doc)` with paired tracks."""
    if not occurrences:
        return ""

    # Group by (base_group, index_in_doc) so parallel tracks (e.g. caput-1 & caput-1-en) pair together
    grouped: dict[tuple[str, int], list[RoleOccurrence]] = defaultdict(list)
    order_keys: list[tuple[str, int]] = []
    for occ in occurrences:
        gk = (occ.base_group, occ.index_in_doc)
        if gk not in grouped:
            order_keys.append(gk)
        grouped[gk].append(occ)

    rows: list[str] = []
    for gk in order_keys:
        occs = grouped[gk]
        primary = occs[0]
        label = primary.doc_title
        if primary.section_title and primary.section_title.lower() != primary.doc_title.lower():
            label = f"{primary.doc_title} — {primary.section_title}"

        if len(occs) == 1:
            href = builder.get_relative_uri(fromdocname, primary.docname) + f"#{primary.occ_id}"
            rows.append(
                f'<li><a href="{html.escape(href, quote=True)}">{html.escape(label)}</a></li>'
            )
        else:
            track_links = []
            for o in occs:
                href = builder.get_relative_uri(fromdocname, o.docname) + f"#{o.occ_id}"
                t_lbl = o.track_label or o.docname.rsplit("/", 1)[-1].upper()
                track_links.append(
                    f'<a href="{html.escape(href, quote=True)}">{html.escape(t_lbl)}</a>'
                )
            rows.append(
                f'<li><strong>{html.escape(label)}</strong> '
                f'<span class="backlink-tracks">({" · ".join(track_links)})</span></li>'
            )

    cls = f"backlinks-box {html.escape(extra_class)}".strip()
    count = len(order_keys)
    return (
        f'<section class="{cls}">'
        f'<h3 class="backlinks-heading">{html.escape(title)} ({count})</h3>'
        f'<ul class="backlinks-chapter-list">{"".join(rows)}</ul>'
        f"</section>"
    )


def process_bibliography_nodes(app: Any, doctree: nodes.document, fromdocname: str) -> None:
    """Resolve `PendingCitationFormats` and `PendingBacklinks` nodes on `doctree-resolved`."""
    env = app.env
    builder = app.builder
    registry = get_card_registry(app)
    cached_cards = getattr(env, "publish_cards", None) or {}
    backlink_index: dict[tuple[str, str], list[RoleOccurrence]] = (
        getattr(env, "publish_apparatus_backlinks", None) or {}
    )

    for node in list(doctree.findall(PendingCitationFormats)):
        address = str(node.get("address") or "").strip()
        options = node.get("options") or {}
        if address:
            card = registry.resolve(address, fromdocname=fromdocname)
        else:
            card = cached_cards.get(fromdocname) or resolve_document_card(
                env, builder, fromdocname, doctree=doctree, registry=registry
            )
        if card is None:
            node.replace_self([])
            continue
        html_out = render_citation_formats_html(
            card,
            title=options.get("title") or "Cite This Work",
            extra_class=options.get("class") or "",
        )
        node.replace_self(nodes.raw("", html_out, format="html"))

    for node in list(doctree.findall(PendingBacklinks)):
        options = node.get("options") or {}
        raw_key = str(node.get("key") or "").strip()
        kind = str(node.get("kind") or "auto").strip().lower()
        doc_meta = (getattr(env, "metadata", {}) or {}).get(fromdocname, {}) or {}
        card = cached_cards.get(fromdocname)

        if kind == "auto" or not raw_key:
            inferred_kind, inferred_slug = _infer_backlink_kind_and_slug(fromdocname, doc_meta, card)
            if kind == "auto":
                kind = inferred_kind
            slug = _slugify(raw_key) if raw_key else inferred_slug
        else:
            slug = _slugify(raw_key)

        occs = backlink_index.get((kind, slug), [])
        # Exclude self-references from the record page itself
        occs = [o for o in occs if o.docname != fromdocname]
        if not occs:
            node.replace_self([])
            continue
        html_out = render_backlinks_html(
            builder,
            fromdocname,
            occs,
            title=options.get("title") or "Occurrences in This Work",
            extra_class=options.get("class") or "",
        )
        node.replace_self(nodes.raw("", html_out, format="html"))


def emit_bibliography_bib(app: Any, exception: Exception | None) -> None:
    """Export `docs/bibliography.bib` when the build contains bibliographic work records."""
    if exception is not None:
        return
    builder = getattr(app, "builder", None)
    if builder is None or getattr(builder, "format", "") != "html":
        return

    cards: dict[str, Card] = getattr(app.env, "publish_cards", None) or {}
    bib_cards = [
        c
        for c in cards.values()
        if c.type in ("reference", "book", "book_record", "source", "source_record")
    ]
    if not bib_cards:
        return

    entries = [format_bibtex(c) for c in sorted(bib_cards, key=lambda x: (x.year_sort or 9999, x.title))]
    out_file = Path(app.outdir) / "bibliography.bib"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def setup(app: Any) -> dict[str, Any]:
    app.connect("env-updated", collect_apparatus_occurrences)
    app.connect("doctree-resolved", process_bibliography_nodes)
    app.connect("build-finished", emit_bibliography_bib)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
