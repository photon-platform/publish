"""Fast, standalone in-memory Docutils RST renderer and metadata parser for Scriptorium and folio_review."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

from docutils import nodes, utils
from docutils.core import publish_parts
from docutils.parsers.rst import roles

from photon_platform.publish.directives.elements import register_standalone_directives
from photon_platform.publish.images.directive import register_standalone_picture
from photon_platform.publish.roles.geometry import register_standalone_roles

_REGISTERED = False

_LIST_METADATA_KEYS = {"tags", "dependencies", "categories"}

_STRING_METADATA_KEYS = {
    "folio",
    "page",
    "volume",
    "book",
    "section",
    "title",
    "canonical_id",
    "type",
}


def _standalone_ref_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: Optional[Dict[str, Any]] = None,
    content: Optional[List[str]] = None,
) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
    """Fallback :ref: and :term: role for standalone Docutils preview."""
    restored = utils.unescape(text, restore_backslashes=True).strip()
    match = re.match(r"^(.+?)\s+<([^>]+)>$", restored)
    if match:
        display = match.group(1).strip()
        target = match.group(2).strip()
    else:
        display = restored
        target = restored
    href = f"#{html.escape(target, quote=True)}"
    raw_html = f'<a class="reference internal" href="{href}">{html.escape(display)}</a>'
    return [nodes.raw(rawtext, raw_html, format="html")], []


def ensure_standalone_extensions() -> None:
    """Ensure all publish directives and roles are registered with Docutils."""
    global _REGISTERED
    if _REGISTERED:
        return
    register_standalone_directives()
    register_standalone_roles()
    register_standalone_picture()
    for role_name in ("ref", "term"):
        roles.register_local_role(role_name, _standalone_ref_role)
    _REGISTERED = True


def _infer_first_heading(body_rst: str) -> Optional[str]:
    """Infer title from the first RST section heading if not specified in field list."""
    lines = body_rst.splitlines()
    adornment_re = re.compile(r"^([=!~^\"'`#*+\-_])\1{2,}\s*$")
    for idx in range(len(lines) - 1):
        title_cand = lines[idx].strip()
        next_line = lines[idx + 1].strip()
        if (
            title_cand
            and not title_cand.startswith("..")
            and not title_cand.startswith(":")
            and adornment_re.match(next_line)
            and len(next_line) >= len(title_cand)
        ):
            return title_cand
    return None


def parse_rst_metadata(rst_text: str) -> Tuple[Dict[str, Any], str]:
    """Extract the top `:key: value` field list from an RST document.

    Converts standard keys (`:folio:`, `:page:`, `:volume:`, `:book:`, `:section:`,
    `:title:`, `:canonical_id:`, `:type:`, `:tags:`, `:dependencies:`) and returns
    ``(metadata_dict, body_rst)``.
    """
    if not rst_text:
        return {}, ""

    lines = rst_text.splitlines()
    idx = 0
    n = len(lines)

    # Skip leading blank lines
    while idx < n and not lines[idx].strip():
        idx += 1

    metadata: Dict[str, Any] = {}
    field_re = re.compile(r"^:([A-Za-z0-9_.-]+):\s*(.*)$")

    last_key: Optional[str] = None
    in_field_list = False

    while idx < n:
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            # Blank line: check if the next non-blank line continues the top field list
            lookahead = idx + 1
            while lookahead < n and not lines[lookahead].strip():
                lookahead += 1
            if in_field_list and lookahead < n and field_re.match(lines[lookahead]):
                idx = lookahead
                continue
            break

        match = field_re.match(line)
        if match:
            in_field_list = True
            key = match.group(1).strip()
            val = match.group(2).strip()
            metadata[key] = val
            last_key = key
            idx += 1
        elif in_field_list and (line.startswith(" ") or line.startswith("\t")) and last_key:
            # Indented continuation line of the previous field
            metadata[last_key] = f"{metadata[last_key]} {stripped}".strip()
            idx += 1
        else:
            break

    if not in_field_list:
        body_rst = rst_text
    else:
        while idx < n and not lines[idx].strip():
            idx += 1
        body_rst = "\n".join(lines[idx:])
        if rst_text.endswith("\n") and body_rst:
            body_rst += "\n"

    # Normalize list-valued fields (:tags:, :dependencies:, :categories:)
    for list_key in _LIST_METADATA_KEYS:
        if list_key in metadata and isinstance(metadata[list_key], str):
            raw_val = metadata[list_key].strip()
            metadata[list_key] = [item.strip() for item in raw_val.split(",") if item.strip()] if raw_val else []

    # Normalize string-valued fields
    for str_key in _STRING_METADATA_KEYS:
        if str_key in metadata and metadata[str_key] is not None:
            metadata[str_key] = str(metadata[str_key]).strip()

    # Fallback title inference from first heading if :title: not explicitly provided
    if "title" not in metadata or not metadata["title"]:
        inferred = _infer_first_heading(body_rst)
        if inferred:
            metadata["title"] = inferred

    return metadata, body_rst


def _protect_math_segments(rst_body: str) -> Tuple[str, Dict[str, str]]:
    """Protect inline $...$ and display $$...$$ math outside of RST roles/backticks from Docutils escaping."""
    placeholders: Dict[str, str] = {}
    counter = 0

    def _store(math_str: str) -> str:
        nonlocal counter
        counter += 1
        token = f"PHOTONMATHPLACEHOLDER{counter:05d}END"
        placeholders[token] = math_str
        return token

    # Split by role/backtick spans so we do not alter content inside :g:`...` or ``...``
    pattern = re.compile(
        r"(``[^`]+``|:[A-Za-z0-9_.-]+:`[^`]+`|`[^`]+`|\$\$[\s\S]+?\$\$|\$(?!\s)[^$\n]+?(?<!\s)\$|\$[A-Za-z0-9]+\$)"
    )

    def _replacer(match: re.Match) -> str:
        seg = match.group(0)
        if seg.startswith("$"):
            return _store(seg)
        return seg

    protected = pattern.sub(_replacer, rst_body)
    return protected, placeholders


def render_rst_html(rst_text: str) -> str:
    """Render extended Scriptorium RST source to an HTML5 fragment string in memory."""
    if not rst_text or not rst_text.strip():
        return ""

    ensure_standalone_extensions()
    _, body_rst = parse_rst_metadata(rst_text)
    if not body_rst.strip():
        return ""

    protected_rst, math_placeholders = _protect_math_segments(body_rst)

    settings_overrides = {
        "doctitle_xform": False,
        "docinfo_xform": False,
        "initial_header_level": 1,
        "math_output": "MathJax",
        "report_level": 5,  # Suppress noisy Docutils warnings in live preview
        "halt_level": 5,
    }

    parts = publish_parts(
        source=protected_rst,
        writer_name="html5",
        settings_overrides=settings_overrides,
    )
    html_out = parts.get("fragment") or parts.get("html_body", "")

    for token, math_str in math_placeholders.items():
        html_out = html_out.replace(token, html.escape(math_str, quote=False))

    return html_out.strip()
