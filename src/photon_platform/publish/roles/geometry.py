"""Semantic roles for geometric elements (:g:), justifications (:just:), and diplomatic line numbers (:line:)."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

from docutils import nodes, utils
from docutils.parsers.rst import roles
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator

from photon_platform.publish.directives.elements import (
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
    - ``$AB$ <0255.g1:/ A B />`` -> ``("$AB$", "0255.g1:/ A B /")``
    - ``$ABC$ <0255.g1:< A B C >>`` -> ``("$ABC$", "0255.g1:< A B C >")``
    - ``$A$ <0309.g1:< K A G )>`` -> ``("$A$", "0309.g1:< K A G )")``
    - ``0255.g1:/ A B /`` -> ``("$AB$", "0255.g1:/ A B /")``
    """
    text = (raw_content or "").strip()
    if not text:
        return "", ""

    # Match non-greedy display text followed by whitespace and <target>
    match = re.match(r"^(.+?)\s+<(.+)>$", text)
    if match:
        display = match.group(1).strip()
        target = match.group(2).strip()
        return display, target

    # Bare target without explicit display text
    target = text
    expr = target.split(":", 1)[-1].strip() if ":" in target else target
    letters = "".join(re.findall(r"[A-Za-z0-9]+", expr))
    display = f"${letters}$" if letters else target
    return display, target


class geom_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for geometric entity references (:g:)."""


class just_ref_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for marginal/step justifications (:just:)."""


class line_num_node(nodes.Inline, nodes.TextElement):
    """Inline AST node for diplomatic line numbers (:line:)."""


def visit_geom_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for geom_ref_node."""
    target = str(node.get("ref_target", ""))
    display = str(node.get("display", node.astext()))
    esc_target = escape_data_ref_attr(target)
    self.body.append(f'<span class="geom-ref" data-ref="{esc_target}">{display}</span>')
    raise nodes.SkipNode


def depart_geom_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for geom_ref_node."""
    pass


def visit_just_ref_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for just_ref_node."""
    display = str(node.get("display", node.astext()))
    target = node.get("ref_target")
    self.body.append(format_justification_html(display, target))
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
    display, target = parse_justification_arg(restored)
    node = just_ref_node(rawtext, display)
    node["display"] = display
    node["ref_target"] = target

    env = getattr(inliner.document.settings, "env", None)
    if env and target:
        record_dependency(env, target)

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


_ROLE_NODE_VISITORS = [
    (geom_ref_node, visit_geom_ref_node, depart_geom_ref_node),
    (just_ref_node, visit_just_ref_node, depart_just_ref_node),
    (line_num_node, visit_line_num_node, depart_line_num_node),
]

_ROLES = {
    "g": g_role,
    "just": just_role,
    "line": line_role,
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
    """Register geometry roles and nodes with Sphinx."""
    register_standalone_roles()
    for node_cls, visit_fn, depart_fn in _ROLE_NODE_VISITORS:
        app.add_node(node_cls, html=(visit_fn, depart_fn), override=True)
    for role_name, role_fn in _ROLES.items():
        app.add_role(role_name, role_fn, override=True)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
