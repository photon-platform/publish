"""Semantic roles for geometric elements (:g:), justifications (:just:), and diplomatic line numbers (:line:)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docutils import nodes, utils
from docutils.parsers.rst import roles
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator

from photon_platform.publish.directives.elements import (
    _get_current_book,
    _resolve_justification_href,
    _resolve_justification_tooltip,
    format_justification_html,
    parse_justification_arg,
    record_dependency,
)


def escape_data_ref_attr(value: str) -> str:
    """Escape a Geometor data-ref attribute value, ensuring < and > are encoded as &lt; and &gt;."""
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def parse_geom_role_text(raw_content: str) -> Tuple[str, str]:
    """Parse :g: role content ``display <target>`` or bare ``target`` into ``(display, target)``.

    Handles targets that themselves contain angle brackets, such as:
    - ``AB <0255.g1:/ A B />`` -> ``("AB", "0255.g1:/ A B /")``
    - ``ABC <0255.g1:< A B C >>`` -> ``("ABC", "0255.g1:< A B C >")``
    - ``A <0309.g1:< K A G )>`` -> ``("A", "0309.g1:< K A G )")``
    - ``0255.g1:/ A B /`` -> ``("AB", "0255.g1:/ A B /")``
    """
    text = (raw_content or "").strip()
    if not text:
        return "", ""

    # Match non-greedy display text followed by whitespace and <target>
    match = re.match(r"^(.+?)\s+<(.+)>$", text)
    if match:
        display = match.group(1).strip()
        if len(display) >= 2 and display.startswith("$") and display.endswith("$"):
            display = display[1:-1].strip()
        target = match.group(2).strip()
        return display, target

    # Bare target without explicit display text
    target = text
    expr = target.split(":", 1)[-1].strip() if ":" in target else target
    letters = "".join(re.findall(r"[A-Za-z0-9]+", expr))
    display = letters if letters else target
    return display, target


class geom_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for geometric entity references (:g:)."""


class just_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for marginal/step justifications (:just:)."""


class line_num_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for diplomatic line numbers (:line:)."""


def format_geom_tooltip(target: str) -> str:
    """Strip <folio>.<gid>: prefixes from a :g: target string to return the underlying element ID(s)."""
    parts = []
    for raw_part in (target or "").split(";"):
        part = raw_part.strip()
        if not part:
            continue
        expr = part.split(":", 1)[-1].strip() if ":" in part else part
        if expr:
            parts.append(expr)
    return "; ".join(parts)


def format_geom_display_html(display: str) -> str:
    """Format :g: display text as HTML, stripping any outer $...$ and converting _sub / ^sup."""
    text = (display or "").strip()
    if len(text) >= 2 and text.startswith("$") and text.endswith("$"):
        text = text[1:-1].strip()
    esc = html.escape(text, quote=False)
    esc = re.sub(r"_([A-Za-z0-9]+)", r"<sub>\1</sub>", esc)
    esc = re.sub(r"\^([A-Za-z0-9]+)", r"<sup>\1</sup>", esc)
    return esc


def visit_geom_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for geom_ref_node."""
    target = str(node.get("ref_target", ""))
    display = str(node.get("display", node.astext()))
    esc_target = escape_data_ref_attr(target)
    esc_display = format_geom_display_html(display)
    tooltip = format_geom_tooltip(target)
    title_attr = f' title="{html.escape(tooltip, quote=True)}"' if tooltip else ""
    self.body.append(
        f'<span class="geom-ref" data-ref="{esc_target}"{title_attr}>{esc_display}</span>'
    )
    raise nodes.SkipNode


def depart_geom_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for geom_ref_node."""
    pass


def visit_just_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for just_ref_node."""
    display = str(node.get("display", node.astext()))
    target = node.get("ref_target")
    self.body.append(format_justification_html(display, target, translator=self))
    raise nodes.SkipNode


def depart_just_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for just_ref_node."""
    pass


def visit_line_num_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for line_num_node."""
    line_num = html.escape(str(node.get("line_num", node.astext())), quote=True)
    self.body.append(f'<sup class="line-num" data-line="{line_num}">{line_num}</sup>')
    raise nodes.SkipNode


def depart_line_num_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for line_num_node."""
    pass


def g_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:g:` for interactive geometric references."""
    restored = utils.unescape(text, restore_backslashes=True)
    display, target = parse_geom_role_text(restored)
    node = geom_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target
    return [node], []


def just_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:just:` for proposition step justifications and dependency recording."""
    restored = utils.unescape(text, restore_backslashes=True)
    env = getattr(inliner.document.settings, "env", None)
    display, target = parse_justification_arg(
        restored, current_book=_get_current_book(env)
    )
    node = just_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    if env and target:
        record_dependency(env, target)

    return [node], []


def format_inline_emphasis_html(text: str) -> str:
    """Escape HTML and convert ``**bold**`` and ``*italic*`` spans into ``<strong>`` and ``<em>``."""
    parts = re.split(r"(\*\*[^*\n]+\*\*|\*[^*\n]+\*)", text)
    out: List[str] = []
    for part in parts:
        if len(part) >= 4 and part.startswith("**") and part.endswith("**"):
            out.append(f"<strong>{html.escape(part[2:-2], quote=False)}</strong>")
        elif len(part) >= 2 and part.startswith("*") and part.endswith("*"):
            out.append(f"<em>{html.escape(part[1:-1], quote=False)}</em>")
        else:
            out.append(html.escape(part, quote=False))
    return "".join(out)


def parse_display_target(raw_content: str) -> Tuple[str, str]:
    """Parse ``display <target>`` or bare ``display`` into ``(display, target)``."""
    text = (raw_content or "").strip()
    match = re.match(r"^(.+?)\s+<([^>]+)>$", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    slug = re.sub(r"[^a-z0-9:._-]+", "-", text.lower()).strip("-")
    return text, slug


class cite_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for bibliographic/locus citations (:cite:)."""


class term_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for foreign/glossary terms (:term:)."""


class person_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for historical/scholarly person references (:person:)."""


def _apparatus_slug(key: str) -> str:
    """Create a deterministic anchor slug for a citation, person, or glossary term key."""
    return re.sub(r"[^a-z0-9]+", "-", (key or "").lower()).strip("-")


def _load_book_apparatus(env: Any, book_slug: str) -> Dict[str, Dict[str, Any]]:
    """Load and cache citations.json, persons.json, and glossary.json for a book if available."""
    cache_attr = "_photon_apparatus_cache"
    cache = getattr(env, cache_attr, None)
    if cache is None:
        cache = {}
        setattr(env, cache_attr, cache)
    if book_slug in cache:
        return cache[book_slug]

    registries: Dict[str, Dict[str, Any]] = {"cite": {}, "person": {}, "term": {}}
    srcdir = Path(getattr(env, "srcdir", "."))
    candidates = [
        srcdir.parent / "resources" / book_slug,
        srcdir.parent.parent / "resources" / srcdir.name,
        srcdir / book_slug,
        srcdir.parent / "resources",
    ]
    file_map = {"cite": "citations.json", "person": "persons.json", "term": "glossary.json"}
    for kind, fname in file_map.items():
        for base in candidates:
            fpath = base / fname
            if fpath.is_file():
                try:
                    registries[kind] = json.loads(fpath.read_text(encoding="utf-8"))
                except Exception:
                    pass
                break

    cache[book_slug] = registries
    return registries


def _resolve_apparatus_link(
    translator: Any, role_type: str, target: str
) -> Tuple[Optional[str], Optional[str], str]:
    """Return (href, occ_id, title_text) for :cite:, :person:, or :term: nodes."""
    slug = _apparatus_slug(target)
    default_labels = {"cite": "Citation", "person": "Person", "term": "Term"}
    title_text = f"{default_labels.get(role_type, 'Ref')}: {target}"

    builder = getattr(translator, "builder", None)
    if builder is None:
        return None, None, title_text

    current_docname = getattr(builder, "current_docname", "") or ""
    env = getattr(builder, "env", None)
    found_docs = getattr(env, "found_docs", set()) if env is not None else set()

    first_seg = current_docname.split("/")[0] if "/" in current_docname else ""
    doc_targets = {"cite": "bibliography", "person": "persons", "term": "glossary"}
    anchor_prefixes = {"cite": "cite", "person": "person", "term": "term"}
    base_doc = doc_targets.get(role_type, "bibliography")
    anchor_prefix = anchor_prefixes.get(role_type, role_type)

    target_doc = None
    if first_seg and f"{first_seg}/{base_doc}" in found_docs:
        target_doc = f"{first_seg}/{base_doc}"
    elif base_doc in found_docs:
        target_doc = base_doc
    elif first_seg:
        target_doc = f"{first_seg}/{base_doc}"

    href = None
    if target_doc and hasattr(builder, "get_relative_uri"):
        try:
            rel_uri = builder.get_relative_uri(current_docname, target_doc)
            href = f"{rel_uri}#{anchor_prefix}-{slug}"
        except Exception:
            href = None

    # Track per-page occurrence counter for back-link targets
    occ_doc = getattr(translator, "_apparatus_occ_doc", None)
    if occ_doc != current_docname:
        translator._apparatus_occ_doc = current_docname
        translator._apparatus_occ_counts = {}
    counts: Dict[Tuple[str, str], int] = getattr(translator, "_apparatus_occ_counts", {})
    key_pair = (role_type, target)
    counts[key_pair] = counts.get(key_pair, 0) + 1
    occ_id = f"occ-{role_type}-{slug}-{counts[key_pair]}"

    # Enrich tooltip title from book apparatus registries if available
    if env is not None:
        regs = _load_book_apparatus(env, first_seg or "default")
        entry = regs.get(role_type, {}).get(target)
        if isinstance(entry, dict):
            if role_type == "cite":
                author = entry.get("author", "")
                work = entry.get("work", "")
                locus = entry.get("locus", "")
                parts = [p for p in (author, work, f"({locus})" if locus else "") if p]
                if parts:
                    title_text = " — ".join(parts[:2]) + (f" {parts[2]}" if len(parts) > 2 else "")
            elif role_type == "person":
                name = entry.get("name", target)
                dates = entry.get("dates", "")
                role = entry.get("role", "")
                head = f"{name} ({dates})" if dates else name
                title_text = f"{head} — {role}" if role else head
            elif role_type == "term":
                hw = entry.get("headword", target)
                trans = entry.get("translation", "")
                defn = entry.get("definition", "")
                head = f"{hw} ({trans})" if trans and trans.lower() != hw.lower() else hw
                title_text = f"{head}: {defn}" if defn else head

    return href, occ_id, title_text


def visit_cite_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for cite_ref_node."""
    display = str(node.get("display", node.astext()))
    target = str(node.get("ref_target", ""))
    esc_target = html.escape(target, quote=True)
    inner_html = format_inline_emphasis_html(display)
    href, occ_id, title_text = _resolve_apparatus_link(self, "cite", target)
    esc_title = html.escape(title_text, quote=True)
    if href:
        id_attr = f' id="{html.escape(occ_id, quote=True)}"' if occ_id else ""
        self.body.append(
            f'<a class="citation-ref"{id_attr} href="{html.escape(href, quote=True)}" data-cite="{esc_target}" title="{esc_title}">{inner_html}</a>'
        )
    else:
        self.body.append(
            f'<span class="citation-ref" data-cite="{esc_target}" title="{esc_title}">{inner_html}</span>'
        )
    raise nodes.SkipNode


def depart_cite_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for cite_ref_node."""
    pass


def visit_term_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for term_ref_node."""
    display = str(node.get("display", node.astext()))
    target = str(node.get("ref_target", ""))
    esc_target = html.escape(target, quote=True)
    inner_html = format_inline_emphasis_html(display)
    href, occ_id, title_text = _resolve_apparatus_link(self, "term", target)
    esc_title = html.escape(title_text, quote=True)
    if href:
        id_attr = f' id="{html.escape(occ_id, quote=True)}"' if occ_id else ""
        self.body.append(
            f'<a class="term-ref glossary-term"{id_attr} href="{html.escape(href, quote=True)}" data-term="{esc_target}" title="{esc_title}">{inner_html}</a>'
        )
    else:
        self.body.append(
            f'<span class="glossary-term" data-term="{esc_target}" title="{esc_title}">{inner_html}</span>'
        )
    raise nodes.SkipNode


def depart_term_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for term_ref_node."""
    pass


def visit_person_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for person_ref_node."""
    display = str(node.get("display", node.astext()))
    target = str(node.get("ref_target", ""))
    esc_target = html.escape(target, quote=True)
    inner_html = format_inline_emphasis_html(display)
    href, occ_id, title_text = _resolve_apparatus_link(self, "person", target)
    esc_title = html.escape(title_text, quote=True)
    if href:
        id_attr = f' id="{html.escape(occ_id, quote=True)}"' if occ_id else ""
        self.body.append(
            f'<a class="person-ref"{id_attr} href="{html.escape(href, quote=True)}" data-person="{esc_target}" title="{esc_title}">{inner_html}</a>'
        )
    else:
        self.body.append(
            f'<span class="person-ref" data-person="{esc_target}" title="{esc_title}">{inner_html}</span>'
        )
    raise nodes.SkipNode


def depart_person_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for person_ref_node."""
    pass


def cite_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:cite:` for bibliographic and locus citations."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    display, target = parse_display_target(restored)
    node = cite_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    env = getattr(inliner.document.settings, "env", None)
    if env is not None and hasattr(env, "metadata") and hasattr(env, "docname"):
        doc_meta = env.metadata.setdefault(env.docname, {})
        cites = doc_meta.setdefault("citations", [])
        if target and target not in cites:
            cites.append(target)

    return [node], []


def term_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:term:` for glossary and foreign philosophical/mathematical terms."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    display, target = parse_display_target(restored)
    node = term_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    env = getattr(inliner.document.settings, "env", None)
    if env is not None and hasattr(env, "metadata") and hasattr(env, "docname"):
        doc_meta = env.metadata.setdefault(env.docname, {})
        terms = doc_meta.setdefault("terms", [])
        if target and target not in terms:
            terms.append(target)

    return [node], []


def person_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:person:` for historical mathematicians, philosophers, and commentators."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    display, target = parse_display_target(restored)
    node = person_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    env = getattr(inliner.document.settings, "env", None)
    if env is not None and hasattr(env, "metadata") and hasattr(env, "docname"):
        doc_meta = env.metadata.setdefault(env.docname, {})
        persons = doc_meta.setdefault("persons", [])
        if target and target not in persons:
            persons.append(target)

    return [node], []


def line_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:line:` for diplomatic line numbers."""
    line_num = utils.unescape(text, restore_backslashes=True).strip()
    node = line_num_node(rawtext, line_num)
    node["line_num"] = line_num
    return [node], []


def parse_eq_role_text(raw_content: str) -> Tuple[str, str]:
    """Parse :eq: role content ``display <spec>`` into ``(display, spec)``.

    Handles specs that themselves contain angle brackets (such as ``< A B C >``), e.g.:
    - ``equal <0255.g1:[ A C ] = 0255.g1:[ A B ]>`` -> ``("equal", "0255.g1:[ A C ] = 0255.g1:[ A B ]")``
    - ``equal <0265.g1:< A B C > = 0265.g1:< A C B >>`` -> ``("equal", "0265.g1:< A B C > = 0265.g1:< A C B >")``
    """
    text = (raw_content or "").strip()
    if not text:
        return "", ""

    match = re.match(r"^([^<>]+?)\s+<(.+)>$", text)
    if match:
        display = match.group(1).strip()
        spec = match.group(2).strip()
        return display, spec

    return "", text


class eq_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for equality assertion references (:eq:)."""


def visit_eq_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for eq_ref_node."""
    raw_spec = str(node.get("eq_spec", ""))
    spec = escape_data_ref_attr(raw_spec)
    display = str(node.get("display", node.astext()))
    if display:
        inner_html = format_inline_emphasis_html(display)
        eq_tooltip = re.sub(r"\b(?:\d{4}\.)?g\d+:\s*", "", raw_spec).strip()
        title_attr = f' title="{html.escape(eq_tooltip, quote=True)}"' if eq_tooltip else ""
        self.body.append(
            f'<span class="geom-eq-ref" data-assert-equal="{spec}"{title_attr}>{inner_html}</span>'
        )
    else:
        self.body.append(
            f'<span class="geom-eq-marker" data-assert-equal="{spec}" hidden></span>'
        )
    raise nodes.SkipNode


def depart_eq_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for eq_ref_node."""
    pass


def eq_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:eq:` for interactive equality references wrapping 'equal' (or 'equilateral', etc.)."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    display, spec = parse_eq_role_text(restored)
    node = eq_ref_node(rawtext, display)
    node["display"] = display
    node["eq_spec"] = spec
    return [node], []


class fn_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for geometric construction/theorem function references (:fn:)."""


def visit_fn_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for fn_ref_node."""
    display = str(node.get("display", node.astext()))
    target = str(node.get("ref_target", ""))
    esc_display = html.escape(display)
    esc_target = html.escape(target, quote=True)
    tooltip = _resolve_justification_tooltip(self, target) or target
    esc_title = html.escape(tooltip, quote=True)
    href = _resolve_justification_href(self, target)
    if href and not href.startswith("#"):
        esc_href = html.escape(href, quote=True)
        self.body.append(
            f'<a class="geom-fn" href="{esc_href}" '
            f'data-ref-target="{esc_target}" title="{esc_title}">{esc_display}</a>'
        )
    else:
        self.body.append(
            f'<span class="geom-fn geom-fn-def" '
            f'data-ref-target="{esc_target}" title="{esc_title}">{esc_display}</span>'
        )
    raise nodes.SkipNode


def depart_fn_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for fn_ref_node."""
    pass


def fn_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Role `:fn:` for composable construction/rule function calls linking to G-nodes."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    display, target = parse_display_target(restored)
    node = fn_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    env = getattr(inliner.document.settings, "env", None)
    if env and target:
        docname = getattr(env, "docname", "") or ""
        doc_parts = set(docname.split("/"))
        if target not in doc_parts:
            record_dependency(env, target)

    return [node], []


_ROLE_NODE_VISITORS = [
    (geom_ref_node, visit_geom_ref_node, depart_geom_ref_node),
    (just_ref_node, visit_just_ref_node, depart_just_ref_node),
    (line_num_node, visit_line_num_node, depart_line_num_node),
    (cite_ref_node, visit_cite_ref_node, depart_cite_ref_node),
    (term_ref_node, visit_term_ref_node, depart_term_ref_node),
    (person_ref_node, visit_person_ref_node, depart_person_ref_node),
    (eq_ref_node, visit_eq_ref_node, depart_eq_ref_node),
    (fn_ref_node, visit_fn_ref_node, depart_fn_ref_node),
]

_ROLES = {
    "g": g_role,
    "just": just_role,
    "line": line_role,
    "cite": cite_role,
    "term": term_role,
    "person": person_role,
    "eq": eq_role,
    "fn": fn_role,
}


def register_standalone_roles() -> None:
    """Register roles and HTML node visitors with standalone Docutils."""
    for role_name, role_fn in _ROLES.items():
        roles.register_local_role(role_name, role_fn)
        roles.register_canonical_role(role_name, role_fn)

    for node_cls, visit_fn, depart_fn in _ROLE_NODE_VISITORS:
        for translator_cls in (BaseHTMLTranslator, HTML5Translator):
            setattr(translator_cls, f"visit_{node_cls.__name__}", visit_fn)
            setattr(translator_cls, f"depart_{node_cls.__name__}", depart_fn)


def setup(app: Any) -> Dict[str, Any]:
    """Register geometry and scholarly roles and nodes with Sphinx."""
    register_standalone_roles()
    for node_cls, visit_fn, depart_fn in _ROLE_NODE_VISITORS:
        app.add_node(
            node_cls,
            html=(visit_fn, depart_fn),
            epub=(visit_fn, depart_fn),
            override=True,
        )
    for role_name, role_fn in _ROLES.items():
        if role_name == "term":
            # Override both top-level :term: and Sphinx's std:term domain role
            app.add_role(role_name, role_fn, override=True)
            app.add_role_to_domain("std", role_name, role_fn, override=True)
        else:
            app.add_role(role_name, role_fn, override=True)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
