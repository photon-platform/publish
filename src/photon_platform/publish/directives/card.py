"""Directives for Page Cards, Summaries, Standard Citations, and Automated Backlinks.

Provides:

- ``.. summary::`` — Visible editorial lead block that also populates the page's ``Card.description``
- ``.. card:: <address>`` — Embeds any local or cross-project (Intersphinx + ``cards.json``) Card
  with optional local contextual body note
- ``.. citation-formats::`` — Renders auto-generated Chicago/MLA/APA/BibTeX tabs for a record
- ``.. backlinks::`` — Renders automated Hoenen-style passage backlinks for a person or citation
"""

from __future__ import annotations

import copy
import html
import os
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri

from ..cards import Card, get_card_registry


class PendingCard(nodes.General, nodes.Element):
    """Deferred placeholder resolved on `doctree-resolved` once all cards are built."""


class PendingCitationFormats(nodes.General, nodes.Element):
    """Deferred placeholder for standard citation format tabs (Chicago/MLA/APA/BibTeX)."""


class PendingBacklinks(nodes.General, nodes.Element):
    """Deferred placeholder for automated bidirectional apparatus backlinks."""


class SummaryDirective(SphinxDirective):
    """Editorial summary block that renders cleanly on the page AND feeds `Card.description`.

    Use `:hidden:` if you want multi-line editorial card copy without repeating it in body prose.
    """

    has_content = True
    option_spec: ClassVar[dict[str, Any]] = {
        "class": directives.class_option,
        "hidden": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        container = nodes.container()
        classes = ["card-summary"]
        extra = self.options.get("class")
        if extra:
            classes.extend(extra)
        container["classes"] = classes
        self.state.nested_parse(self.content, self.content_offset, container)

        env = getattr(self, "env", None)
        if env is not None and hasattr(env, "metadata") and hasattr(env, "docname"):
            meta = env.metadata.setdefault(env.docname, {})
            meta["_has_summary_block"] = True
            if "hidden" in self.options:
                plain = " ".join(container.astext().split())
                if plain:
                    meta["card_description"] = plain
                return []

        return [container]


class CardDirective(SphinxDirective):
    """Embed a formatted Card for any local page or cross-project Intersphinx address.

    Example::

        .. card:: aristotle:analytica_posteriora/index
           :variant: banner

           Cited 5 times in Hoenen's Caput I, III, and VII.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True
    option_spec: ClassVar[dict[str, Any]] = {
        "variant": lambda arg: directives.choice(
            arg, ("vertical", "banner", "compact", "inline")
        ),
        "title": directives.unchanged,
        "description": directives.unchanged,
        "note-label": directives.unchanged,
        "class": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        node = PendingCard()
        node["address"] = self.arguments[0].strip()
        node["options"] = dict(self.options)
        if self.content:
            note_box = nodes.container()
            self.state.nested_parse(self.content, self.content_offset, note_box)
            node += note_box
        return [node]


class CitationFormatsDirective(SphinxDirective):
    """Render auto-generated Chicago, MLA, APA, and BibTeX citations for the current record
    (or an optional referenced Card address)."""

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = False
    option_spec: ClassVar[dict[str, Any]] = {
        "title": directives.unchanged,
        "class": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        node = PendingCitationFormats()
        node["address"] = self.arguments[0].strip() if self.arguments else ""
        node["options"] = dict(self.options)
        return [node]


class BacklinksDirective(SphinxDirective):
    """Render automated passage backlinks (grouped by chapter & paired tracks) for a person/work."""

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = False
    option_spec: ClassVar[dict[str, Any]] = {
        "kind": lambda arg: directives.choice(arg, ("auto", "person", "cite", "term")),
        "key": directives.unchanged,
        "title": directives.unchanged,
        "class": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        node = PendingBacklinks()
        node["key"] = self.options.get("key") or (self.arguments[0].strip() if self.arguments else "")
        node["kind"] = self.options.get("kind", "auto")
        node["options"] = dict(self.options)
        return [node]


def _get_foundation_template(builder: Any, template_name: str) -> Any:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound

    try:
        return builder.templates.environment.get_template(template_name)
    except (AttributeError, TemplateNotFound, OSError):
        foundation_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "themes", "foundation")
        )
        return Environment(loader=FileSystemLoader(foundation_dir)).get_template(template_name)


def render_card_html(
    builder: Any,
    fromdocname: str,
    card: Card,
    *,
    variant: str = "banner",
    extra_class: str = "",
    note_label: str = "In This Work",
    is_directory: bool = False,
) -> str:
    """Render a `Card` using the unified `components/card.html` Jinja template."""

    def pathto(otheruri: str, resource: bool = False, baseuri: str | None = None) -> str:
        if not otheruri:
            return ""
        if otheruri.startswith(("http://", "https://", "data:", "#")):
            return otheruri
        if resource:
            return relative_uri(builder.get_target_uri(fromdocname), otheruri)
        return builder.get_relative_uri(fromdocname, otheruri)

    template = _get_foundation_template(builder, "components/card.html")
    return template.render(
        article=card.to_template_dict(),
        card=card.to_template_dict(),
        variant=variant,
        extra_class=extra_class,
        note_label=note_label,
        is_directory=is_directory,
        pathto=pathto,
    )


def process_cards(app: Any, doctree: nodes.document, fromdocname: str) -> None:
    """Resolve `PendingCard` nodes on `doctree-resolved`."""
    from .collection import render_node_html

    builder = app.builder
    registry = get_card_registry(app)

    for node in list(doctree.findall(PendingCard)):
        address = str(node.get("address") or "").strip()
        options = node.get("options") or {}
        variant = options.get("variant", "banner")
        extra_class = options.get("class", "")
        note_label = options.get("note-label", "In This Work")

        resolved = registry.resolve(address, fromdocname=fromdocname)
        if resolved is None:
            esc = html.escape(address)
            fallback = (
                f'<div class="card-embed card-missing {html.escape(extra_class)}">'
                f'<p><strong>Unresolved Card:</strong> <code>{esc}</code></p>'
                f"</div>"
            )
            node.replace_self(nodes.raw("", fallback, format="html"))
            continue

        card_copy = copy.deepcopy(resolved)
        if options.get("title"):
            card_copy.title = options["title"]
        if options.get("description"):
            card_copy.description = options["description"]
            card_copy.description_html = f"<p>{html.escape(options['description'])}</p>"

        if len(node.children) > 0:
            parts = [render_node_html(builder, child) for child in node.children]
            card_copy.local_note_html = "".join(parts).strip()

        variant_layout = {
            "vertical": "layout-cards",
            "banner": "layout-banners",
            "compact": "layout-list",
            "inline": "layout-banners card-embed-inline",
        }.get(variant, "layout-banners")

        card_markup = render_card_html(
            builder,
            fromdocname,
            card_copy,
            variant=variant,
            extra_class=extra_class,
            note_label=note_label,
        )
        wrapped = (
            f'<div class="card-embed collection {variant_layout} {html.escape(extra_class)}">'
            f"{card_markup}"
            f"</div>"
        )
        node.replace_self(nodes.raw("", wrapped, format="html"))


def setup(app: Any) -> dict[str, Any]:
    app.add_node(PendingCard)
    app.add_node(PendingCitationFormats)
    app.add_node(PendingBacklinks)
    app.add_directive("summary", SummaryDirective)
    app.add_directive("card", CardDirective)
    app.add_directive("citation-formats", CitationFormatsDirective)
    app.add_directive("backlinks", BacklinksDirective)
    app.connect("doctree-resolved", process_cards)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
