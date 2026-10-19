"""Semantic directives for classical mathematical and philosophical texts (Elements, Pacioli, Hoenen)."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator


def parse_justification_arg(raw_arg: str) -> Tuple[str, Optional[str]]:
    """Parse a justification string into (display_text, target_id).

    Supports forms:
    - ``[Def. 15] <I.def.15>`` -> ``("[Def. 15]", "I.def.15")``
    - ``[Def. 15]`` -> ``("[Def. 15]", None)``
    - ``I.def.15`` -> ``("[I.def.15]", "I.def.15")``
    """
    text = (raw_arg or "").strip()
    if not text:
        return "", None

    match = re.match(r"^(.*?)\s*<([^>]+)>$", text)
    if match:
        display = match.group(1).strip()
        target = match.group(2).strip()
        if not display:
            display = f"[{target}]"
        return display, target

    if text.startswith("[") and text.endswith("]"):
        return text, None

    # Bare canonical ID such as I.def.15 or I.post.3
    if re.match(r"^[A-Za-z0-9_.-]+$", text) and "." in text:
        return f"[{text}]", text

    return text, None


def format_justification_html(display: str, target: Optional[str] = None) -> str:
    """Render a <span class="justification"> HTML fragment."""
    esc_display = html.escape(display)
    if target:
        esc_target = html.escape(target, quote=True)
        return f'<span class="justification" data-ref-target="{esc_target}">{esc_display}</span>'
    return f'<span class="justification">{esc_display}</span>'


def record_dependency(env: Any, target: Optional[str]) -> None:
    """Record a logical dependency target in the Sphinx build environment."""
    if not env or not target:
        return
    docname = getattr(env, "docname", None)
    if not docname or not hasattr(env, "metadata"):
        return
    doc_meta = env.metadata.setdefault(docname, {})
    deps = doc_meta.setdefault("dependencies", [])
    if isinstance(deps, str):
        deps = [d.strip() for d in deps.split(",") if d.strip()]
        doc_meta["dependencies"] = deps
    if target not in deps:
        deps.append(target)


class enunciation_node(nodes.General, nodes.Element):
    """AST node for an enunciation (protasis) block."""


class assertion_node(nodes.General, nodes.Element):
    """AST node for a centered proof step / assertion with optional justification."""


class subclause_node(nodes.General, nodes.Element):
    """AST node for an indented proof sub-clause with optional justification."""


class qed_node(nodes.General, nodes.Element):
    """AST node for a conclusion sign-off (Q.E.D. / Q.E.F.)."""


class porism_node(nodes.General, nodes.Element):
    """AST node for a corollary / porism block."""


class lemma_node(nodes.General, nodes.Element):
    """AST node for a lemma block."""


class scholium_node(nodes.General, nodes.Element):
    """AST node for a scholium block."""


class folio_node(nodes.General, nodes.Element):
    """AST node for a diplomatic folio transition milestone."""


def _visit_single_or_multi_block(
    translator: Any,
    node: nodes.Element,
    base_class: str,
    prefix_html: str = "",
) -> None:
    """Render a semantic block as <div class="...">, unwrapping single paragraphs for clean typography."""
    classes = [base_class] + list(node.get("classes", []))
    cls_str = " ".join(dict.fromkeys(c for c in classes if c))
    ids = node.get("ids", [])
    id_attr = f' id="{html.escape(ids[0], quote=True)}"' if ids else ""

    translator.body.append(f'<div class="{html.escape(cls_str, quote=True)}"{id_attr}>')
    if prefix_html:
        translator.body.append(prefix_html)

    if len(node.children) == 1 and isinstance(node.children[0], nodes.paragraph):
        for child in node.children[0].children:
            child.walkabout(translator)
        translator.body.append("</div>\n")
        raise nodes.SkipNode

    if node.children:
        translator.body.append("\n")


def visit_enunciation_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for enunciation_node."""
    _visit_single_or_multi_block(self, node, "enunciation")


def depart_enunciation_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for enunciation_node."""
    self.body.append("</div>\n")


def visit_assertion_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for assertion_node."""
    just_display = node.get("justification_display", "")
    just_target = node.get("justification_target")
    prefix = format_justification_html(just_display, just_target) if just_display else ""
    _visit_single_or_multi_block(self, node, "assertion", prefix_html=prefix)


def depart_assertion_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for assertion_node."""
    self.body.append("</div>\n")


def visit_subclause_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for subclause_node."""
    just_display = node.get("justification_display", "")
    just_target = node.get("justification_target")
    prefix = format_justification_html(just_display, just_target) if just_display else ""
    _visit_single_or_multi_block(self, node, "sub-clause", prefix_html=prefix)


def depart_subclause_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for subclause_node."""
    self.body.append("</div>\n")


def visit_qed_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for qed_node."""
    _visit_single_or_multi_block(self, node, "qed")


def depart_qed_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for qed_node."""
    self.body.append("</div>\n")


def _visit_container_block(self: Any, node: nodes.Element, base_class: str) -> None:
    classes = [base_class] + list(node.get("classes", []))
    cls_str = " ".join(dict.fromkeys(c for c in classes if c))
    ids = node.get("ids", [])
    id_attr = f' id="{html.escape(ids[0], quote=True)}"' if ids else ""
    self.body.append(f'<div class="{html.escape(cls_str, quote=True)}"{id_attr}>\n')
    title = node.get("title")
    if title:
        self.body.append(f'<div class="{base_class}-title">{html.escape(title)}</div>\n')


def _depart_container_block(self: Any, node: nodes.Element) -> None:
    self.body.append("</div>\n")


def visit_porism_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for porism_node."""
    _visit_container_block(self, node, "porism")


def depart_porism_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for porism_node."""
    _depart_container_block(self, node)


def visit_lemma_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for lemma_node."""
    _visit_container_block(self, node, "lemma")


def depart_lemma_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for lemma_node."""
    _depart_container_block(self, node)


def visit_scholium_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for scholium_node."""
    _visit_container_block(self, node, "scholium")


def depart_scholium_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for scholium_node."""
    _depart_container_block(self, node)


def visit_folio_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for folio_node."""
    folio_id = html.escape(str(node.get("folio_id", "")), quote=True)
    page = html.escape(str(node.get("page", "")), quote=True)
    page_str = f" | p. {page}" if page else ""
    self.body.append(
        f'<div class="folio-milestone" id="folio-{folio_id}" '
        f'data-folio="{folio_id}" data-page="{page}">'
        f"[Folio {folio_id}{page_str}]</div>\n"
    )
    raise nodes.SkipNode


def depart_folio_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for folio_node."""
    pass


class DualModeDirective(Directive):
    """Base directive class compatible with both Sphinx and standalone Docutils."""

    @property
    def env(self) -> Any:
        """Return the Sphinx BuildEnvironment if running inside Sphinx, else None."""
        return getattr(self.state.document.settings, "env", None)


class EnunciationDirective(DualModeDirective):
    """Directive for proposition enunciations (protasis): ``.. enunciation::``."""

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Parse enunciation body and register excerpt in Sphinx metadata if available."""
        node = enunciation_node()
        node["classes"] = list(self.options.get("class", []))
        self.add_name(node)
        self.state.nested_parse(self.content, self.content_offset, node)

        if hasattr(self, "env") and self.env:
            doc_meta = self.env.metadata.setdefault(self.env.docname, {})
            if "excerpt" not in doc_meta:
                doc_meta["excerpt"] = node.astext().strip()

        return [node]


class AssertionDirective(DualModeDirective):
    """Directive for proof steps / assertions: ``.. assertion:: [optional_justification]``."""

    node_class = assertion_node
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Parse assertion body, optional justification argument, and record dependency."""
        node = self.node_class()
        node["classes"] = list(self.options.get("class", []))
        self.add_name(node)

        if self.arguments:
            display, target = parse_justification_arg(self.arguments[0])
            node["justification_display"] = display
            node["justification_target"] = target
            if hasattr(self, "env") and self.env and target:
                record_dependency(self.env, target)

        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class SubclauseDirective(AssertionDirective):
    """Directive for indented proof sub-clauses: ``.. subclause:: [optional_justification]``."""

    node_class = subclause_node


class QedDirective(DualModeDirective):
    """Directive for proof conclusions: ``.. qed:: [optional_label]``."""

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Parse Q.E.D. / Q.E.F. conclusion block."""
        node = qed_node()
        node["classes"] = list(self.options.get("class", []))
        self.add_name(node)

        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        elif self.arguments:
            para = nodes.paragraph(text=self.arguments[0].strip())
            node += para

        return [node]


class _SemanticBlockDirective(DualModeDirective):
    """Shared base for porism, lemma, and scholium directives."""

    node_class = porism_node
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Parse semantic container block."""
        node = self.node_class()
        node["classes"] = list(self.options.get("class", []))
        if self.arguments:
            node["title"] = self.arguments[0].strip()
        self.add_name(node)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class PorismDirective(_SemanticBlockDirective):
    """Directive for corollaries / porisms: ``.. porism:: [optional_title]``."""

    node_class = porism_node


class LemmaDirective(_SemanticBlockDirective):
    """Directive for lemmas: ``.. lemma:: [optional_title]``."""

    node_class = lemma_node


class ScholiumDirective(_SemanticBlockDirective):
    """Directive for scholia: ``.. scholium:: [optional_title]``."""

    node_class = scholium_node


class FolioDirective(DualModeDirective):
    """Directive for folio transition milestones: ``.. folio:: <folio_id>``."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "page": directives.unchanged,
        "class": directives.class_option,
    }

    def run(self) -> List[nodes.Node]:
        """Create folio milestone node."""
        folio_id = self.arguments[0].strip()
        page = (self.options.get("page") or "").strip()
        node = folio_node()
        node["folio_id"] = folio_id
        node["page"] = page
        node["classes"] = list(self.options.get("class", []))
        return [node]


_NODE_VISITORS = [
    (enunciation_node, visit_enunciation_node, depart_enunciation_node),
    (assertion_node, visit_assertion_node, depart_assertion_node),
    (subclause_node, visit_subclause_node, depart_subclause_node),
    (qed_node, visit_qed_node, depart_qed_node),
    (porism_node, visit_porism_node, depart_porism_node),
    (lemma_node, visit_lemma_node, depart_lemma_node),
    (scholium_node, visit_scholium_node, depart_scholium_node),
    (folio_node, visit_folio_node, depart_folio_node),
]

_DIRECTIVES = {
    "enunciation": EnunciationDirective,
    "assertion": AssertionDirective,
    "subclause": SubclauseDirective,
    "sub-clause": SubclauseDirective,
    "qed": QedDirective,
    "porism": PorismDirective,
    "lemma": LemmaDirective,
    "scholium": ScholiumDirective,
    "folio": FolioDirective,
}


from docutils.parsers.rst import states as rst_states

FIXED_SECTION_LEVELS: Dict[str, int] = {
    "=": 1,
    "-": 2,
    "~": 3,
    "^": 4,
    '"': 5,
    "'": 6,
    "#": 1,
    "*": 2,
    "+": 3,
}

_FIXED_LEVELS_INSTALLED = False
_ORIG_CHECK_SUBSECTION = rst_states.RSTState.check_subsection
_ORIG_NEW_SUBSECTION = rst_states.RSTState.new_subsection
_ORIG_SECTION_TITLE_TAGS = BaseHTMLTranslator.section_title_tags


def _fixed_check_subsection(self: Any, source: str, style: Any, lineno: int) -> bool:
    """Resolve section hierarchy using fixed underline character levels instead of per-page order."""
    char = style[-1] if isinstance(style, tuple) else str(style)
    fixed_level = FIXED_SECTION_LEVELS.get(char)
    if fixed_level is None:
        self.memo._current_fixed_level = None
        self.memo._current_adornment_char = None
        return _ORIG_CHECK_SUBSECTION(self, source, style, lineno)

    self.memo._current_fixed_level = fixed_level
    self.memo._current_adornment_char = char

    while isinstance(self.parent, nodes.section) and self.parent.get("fixed_level", 0) >= fixed_level:
        self.parent = self.parent.parent

    self.memo.section_level = len(self.parent.section_hierarchy())
    if style not in self.memo.title_styles:
        self.memo.title_styles.append(style)
    return True


def _fixed_new_subsection(self: Any, title: str, lineno: int, messages: List[Any]) -> None:
    """Attach fixed_level and adornment_char metadata to newly created section nodes."""
    _ORIG_NEW_SUBSECTION(self, title, lineno, messages)
    fixed_level = getattr(self.memo, "_current_fixed_level", None)
    adornment_char = getattr(self.memo, "_current_adornment_char", None)
    if fixed_level is not None and isinstance(self.parent, nodes.section):
        self.parent["fixed_level"] = fixed_level
        self.parent["adornment_char"] = adornment_char
        cls_name = f"level-{fixed_level}"
        if cls_name not in self.parent["classes"]:
            self.parent["classes"].append(cls_name)


def _fixed_section_title_tags(self: Any, node: nodes.Element) -> Tuple[str, str]:
    """Emit <h1..h6> tag matching the section's fixed underline character level."""
    fixed_level = node.parent.get("fixed_level") if isinstance(node.parent, nodes.section) else None
    if fixed_level is not None:
        saved_sec = self.section_level
        saved_init = self.initial_header_level
        try:
            self.section_level = int(fixed_level)
            self.initial_header_level = 1
            return _ORIG_SECTION_TITLE_TAGS(self, node)
        finally:
            self.section_level = saved_sec
            self.initial_header_level = saved_init
    return _ORIG_SECTION_TITLE_TAGS(self, node)


def install_fixed_section_levels(custom_levels: Optional[Dict[str, int]] = None) -> None:
    """Install fixed underline-character to heading-level mapping into Docutils and Sphinx."""
    global _FIXED_LEVELS_INSTALLED
    if custom_levels:
        FIXED_SECTION_LEVELS.update(custom_levels)
    if _FIXED_LEVELS_INSTALLED:
        return
    rst_states.RSTState.check_subsection = _fixed_check_subsection  # type: ignore[method-assign]
    rst_states.RSTState.new_subsection = _fixed_new_subsection  # type: ignore[method-assign]
    BaseHTMLTranslator.section_title_tags = _fixed_section_title_tags  # type: ignore[method-assign]
    _FIXED_LEVELS_INSTALLED = True


def register_standalone_directives() -> None:
    """Register directives, fixed section levels, and HTML node visitors with standalone Docutils."""
    install_fixed_section_levels()
    for name, directive_cls in _DIRECTIVES.items():
        directives.register_directive(name, directive_cls)

    for node_cls, visit_fn, depart_fn in _NODE_VISITORS:
        for translator_cls in (BaseHTMLTranslator, HTML5Translator):
            setattr(translator_cls, f"visit_{node_cls.__name__}", visit_fn)
            setattr(translator_cls, f"depart_{node_cls.__name__}", depart_fn)


def setup(app: Any) -> Dict[str, Any]:
    """Register elements directives, fixed section levels, and nodes with Sphinx."""
    register_standalone_directives()
    app.add_config_value("rst_fixed_section_levels", dict(FIXED_SECTION_LEVELS), "env")
    app.connect(
        "config-inited",
        lambda _app, config: install_fixed_section_levels(getattr(config, "rst_fixed_section_levels", None)),
    )
    for node_cls, visit_fn, depart_fn in _NODE_VISITORS:
        app.add_node(node_cls, html=(visit_fn, depart_fn), override=True)
    for name, directive_cls in _DIRECTIVES.items():
        app.add_directive(name, directive_cls, override=True)

    app.add_js_file("js/geometor_interactive.js")
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
