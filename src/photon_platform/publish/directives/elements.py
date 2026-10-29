"""Semantic directives for classical mathematical and philosophical texts (Elements, Pacioli, Hoenen)."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator


VALID_BOOKS = {
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
}


def _get_current_book(env: Any) -> Optional[str]:
    """Infer current Euclid book Roman numeral from Sphinx BuildEnvironment."""
    if not env:
        return None
    docname = getattr(env, "docname", "") or ""
    if hasattr(env, "metadata") and docname in env.metadata:
        bk = env.metadata[docname].get("book")
        if bk:
            return str(bk).strip().upper()
    m = re.search(r"(?:^|/)book_([ivxlcdm]+)(?:/|$)", docname, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def infer_justification_target(
    display: str, current_book: Optional[str] = None
) -> Optional[str]:
    """Infer canonical target ID(s) from justification display text when <target> is omitted."""
    s = (display or "").strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    if not s or re.match(
        r"^(?:Q\.\s*\$?E\$?\.|[*]?id[*]?\.|above|from above|Part\s+\d|First part|Prop\.\s*D|Simson|Pappus|\(\d+\))",
        s,
        re.IGNORECASE,
    ):
        return None

    m_deff = re.search(
        r"\b([IVXLCDM]+)\.\s*Deff?\.\s*(III|II)(?:\.\s*(\d+))?",
        s,
        re.IGNORECASE,
    )
    if m_deff and m_deff.group(1).upper() in VALID_BOOKS:
        bk = m_deff.group(1).upper()
        sub = m_deff.group(2).lower()
        num = m_deff.group(3)
        return f"{bk}.def.{sub}.{num}" if num else f"{bk}.def.{sub}"

    bk_default = (current_book or "I").upper()
    m_post = re.match(r"^Post\.\s*(\d+)\.?$", s, re.IGNORECASE)
    if m_post:
        return f"I.post.{m_post.group(1)}"
    m_cn = re.match(r"^C\.\s*N\.\s*(\d+)\.?$", s, re.IGNORECASE)
    if m_cn:
        return f"I.cn.{m_cn.group(1)}"
    m_def_bare = re.match(r"^Def\.\s*(\d+)\.?$", s, re.IGNORECASE)
    if m_def_bare:
        return f"{bk_default}.def.{m_def_bare.group(1)}"

    results: List[str] = []
    pat = re.compile(
        r"\b([IVXLCDM]+)\.\s*(?:(Def\.?)\s*(\d+)|(\d+)(?:\s*(?:,|and|or)\s*(\d+))?)",
        re.IGNORECASE,
    )
    for m in pat.finditer(s):
        bk = m.group(1).upper()
        if bk not in VALID_BOOKS:
            continue
        if m.group(2):
            results.append(f"{bk}.def.{m.group(3)}")
        else:
            results.append(f"{bk}.{m.group(4)}")
            if m.group(5):
                results.append(f"{bk}.{m.group(5)}")
    if results:
        return ", ".join(dict.fromkeys(results))
    return None


def parse_justification_arg(
    raw_arg: str, current_book: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """Parse a justification string into (display_text, target_id).

    Supports forms:
    - ``[Def. 15] <I.def.15>`` -> ``("[Def. 15]", "I.def.15")``
    - ``[Def. 15]`` -> ``("[Def. 15]", "I.def.15")``
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
        return text, infer_justification_target(text, current_book=current_book)

    # Bare canonical ID such as I.def.15 or I.post.3
    if re.match(r"^[A-Za-z0-9_.-]+$", text) and "." in text:
        return f"[{text}]", text

    return text, infer_justification_target(text, current_book=current_book)


def _resolve_justification_href(translator: Any, target: str) -> Optional[str]:
    """Resolve a canonical justification target (or comma-separated list) to a relative Sphinx href."""
    if translator is None or not target:
        return None
    builder = getattr(translator, "builder", None)
    if builder is None or not hasattr(builder, "env") or not hasattr(builder, "get_relative_uri"):
        return None
    env = builder.env
    if env is None or not hasattr(env, "get_domain"):
        return None

    try:
        std_domain = env.get_domain("std")
    except Exception:
        return None

    anonlabels = getattr(std_domain, "anonlabels", {})
    labels = getattr(std_domain, "labels", {})
    current_docname = getattr(builder, "current_docname", "") or ""

    candidates = [t.strip() for t in target.split(",") if t.strip()]
    for cand in candidates:
        key = cand.lower()
        search_keys = [key]
        if key.startswith("viii.def."):
            search_keys.append("vii." + key[5:])
        prefix = key
        while "." in prefix:
            prefix = prefix.rsplit(".", 1)[0]
            search_keys.append(prefix)
            if prefix.startswith("viii.def"):
                search_keys.append("vii." + prefix[5:])

        for sk in search_keys:
            target_docname: Optional[str] = None
            label_id: Optional[str] = None
            if sk in anonlabels:
                target_docname, label_id = anonlabels[sk]
            elif sk in labels:
                target_docname, label_id, _ = labels[sk]
            if target_docname and label_id:
                try:
                    rel_uri = builder.get_relative_uri(current_docname, target_docname)
                    return f"{rel_uri}#{label_id}" if rel_uri else f"#{label_id}"
                except Exception:
                    continue
    return None


def format_justification_html(
    display: str, target: Optional[str] = None, translator: Any = None
) -> str:
    """Render an <a class="justification"> or <span class="justification"> HTML fragment."""
    esc_display = html.escape(display)
    if not target and translator is not None:
        env = getattr(getattr(translator, "builder", None), "env", None)
        target = infer_justification_target(display, current_book=_get_current_book(env))

    if target:
        esc_target = html.escape(target, quote=True)
        href = _resolve_justification_href(translator, target)
        if href:
            esc_href = html.escape(href, quote=True)
            return f'<a class="justification" href="{esc_href}" data-ref-target="{esc_target}">{esc_display}</a>'
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
    for single in (t.strip() for t in target.split(",") if t.strip()):
        if single not in deps:
            deps.append(single)


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
    extra_attrs: Optional[Dict[str, str]] = None,
) -> None:
    """Render a semantic block as <div class="...">, unwrapping single paragraphs for clean typography."""
    classes = [base_class] + list(node.get("classes", []))
    cls_str = " ".join(dict.fromkeys(c for c in classes if c))
    ids = node.get("ids", [])
    id_attr = f' id="{html.escape(ids[0], quote=True)}"' if ids else ""
    extra_str = ""
    if extra_attrs:
        for k, v in extra_attrs.items():
            if v:
                extra_str += f' {k}="{html.escape(str(v), quote=True)}"'

    translator.body.append(f'<div class="{html.escape(cls_str, quote=True)}"{id_attr}{extra_str}>')
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
    prefix = format_justification_html(just_display, just_target, translator=self) if just_display else ""
    extra = {"data-assert-equal": node["assert_equal"]} if node.get("assert_equal") else None
    _visit_single_or_multi_block(self, node, "assertion", prefix_html=prefix, extra_attrs=extra)


def depart_assertion_node(self: Any, node: nodes.Element) -> None:
    """HTML departure visitor for assertion_node."""
    self.body.append("</div>\n")


def visit_subclause_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for subclause_node."""
    just_display = node.get("justification_display", "")
    just_target = node.get("justification_target")
    prefix = format_justification_html(just_display, just_target, translator=self) if just_display else ""
    extra = {"data-assert-equal": node["assert_equal"]} if node.get("assert_equal") else None
    _visit_single_or_multi_block(self, node, "sub-clause", prefix_html=prefix, extra_attrs=extra)


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
        "equal": directives.unchanged,
        "assert": directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Parse assertion body, optional justification argument, and record dependency."""
        node = self.node_class()
        node["classes"] = list(self.options.get("class", []))
        self.add_name(node)

        assert_equal = (self.options.get("equal") or self.options.get("assert") or "").strip()
        if assert_equal:
            node["assert_equal"] = assert_equal

        if self.arguments:
            env = getattr(self, "env", None)
            display, target = parse_justification_arg(
                self.arguments[0], current_book=_get_current_book(env)
            )
            node["justification_display"] = display
            node["justification_target"] = target
            if env and target:
                record_dependency(env, target)

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


_MATH_PROTECT_PATTERN = re.compile(
    r"(``[^`]+``|:[A-Za-z0-9_.-]+:`[^`]+`|`[^`\n]+`_?|\$\$[\s\S]+?\$\$|\$(?!\s)[^$\n]+?(?<!\s)\$|\$[A-Za-z0-9]+\$)"
)
_PLACEHOLDER_TOKEN_RE = re.compile(r"PHOTONMATHPLACEHOLDER\d+END")


def protect_rst_math_segments(
    rst_body: str, start_counter: int = 0
) -> Tuple[str, Dict[str, str], int]:
    """Protect inline $...$ and display $$...$$ math outside of RST roles/backticks from Docutils escaping."""
    placeholders: Dict[str, str] = {}
    counter = start_counter

    def _store(math_str: str) -> str:
        nonlocal counter
        counter += 1
        token = f"PHOTONMATHPLACEHOLDER{counter:06d}END"
        placeholders[token] = math_str
        return token

    def _replacer(match: re.Match) -> str:
        seg = match.group(0)
        if seg.startswith("$"):
            return _store(seg)
        return seg

    protected = _MATH_PROTECT_PATTERN.sub(_replacer, rst_body)
    if placeholders:
        lines = protected.splitlines()
        adorn_re = re.compile(r"^([=\-~^\"'#*+])\1{2,}$")
        for i in range(len(lines) - 1):
            if "PHOTONMATHPLACEHOLDER" in lines[i]:
                m_adorn = adorn_re.match(lines[i + 1].strip())
                if m_adorn:
                    target_len = len(lines[i].rstrip())
                    if len(lines[i + 1].strip()) < target_len:
                        char = m_adorn.group(1)
                        lines[i + 1] = char * target_len
                        if i > 0 and adorn_re.match(lines[i - 1].strip()):
                            lines[i - 1] = char * target_len
        protected = "\n".join(lines) + ("\n" if rst_body.endswith("\n") else "")

    return protected, placeholders, counter


def _restore_math_string(text: str, placeholders: Dict[str, str]) -> str:
    """Restore any PHOTONMATHPLACEHOLDER...END tokens in a string."""
    if not text or "PHOTONMATHPLACEHOLDER" not in text:
        return text
    return _PLACEHOLDER_TOKEN_RE.sub(lambda m: placeholders.get(m.group(0), m.group(0)), text)


def _on_sphinx_source_read(app: Any, docname: str, source: List[str]) -> None:
    """Sphinx source-read hook to protect $...$ and $$...$$ segments before Docutils parsing."""
    if not source or not source[0] or "$" not in source[0]:
        return
    env = getattr(app, "env", None)
    if env is None:
        return
    store: Dict[str, str] = getattr(env, "_photon_math_placeholders", None)
    if store is None:
        store = {}
        setattr(env, "_photon_math_placeholders", store)
    counter = getattr(env, "_photon_math_counter", 0)
    protected, new_placeholders, counter = protect_rst_math_segments(source[0], start_counter=counter)
    setattr(env, "_photon_math_counter", counter)
    if new_placeholders:
        store.update(new_placeholders)
        source[0] = protected


def _on_sphinx_doctree_read(app: Any, doctree: nodes.document) -> None:
    """Sphinx doctree-read hook to restore protected $...$ and $$...$$ segments into AST nodes."""
    env = getattr(app, "env", None)
    store: Optional[Dict[str, str]] = getattr(env, "_photon_math_placeholders", None) if env else None
    if not store:
        return

    for text_node in list(doctree.findall(nodes.Text)):
        raw_str = str(text_node)
        if "PHOTONMATHPLACEHOLDER" in raw_str:
            restored = _restore_math_string(raw_str, store)
            if restored != raw_str and text_node.parent is not None:
                text_node.parent.replace(text_node, nodes.Text(restored))

    lower_token_re = re.compile(r"photonmathplaceholder\d+end")
    for el in doctree.findall(nodes.Element):
        for attr_key, attr_val in list(el.attributes.items()):
            if isinstance(attr_val, str) and "PHOTONMATHPLACEHOLDER" in attr_val:
                el.attributes[attr_key] = _restore_math_string(attr_val, store)
            elif isinstance(attr_val, list) and attr_key in ("ids", "names"):
                new_list = []
                changed = False
                for item in attr_val:
                    if isinstance(item, str) and "photonmathplaceholder" in item.lower():
                        changed = True
                        def _slug_repl(m: re.Match) -> str:
                            orig = store.get(m.group(0).upper(), "")
                            return re.sub(r"[^a-z0-9]+", "-", orig.lower()).strip("-")
                        cleaned = lower_token_re.sub(_slug_repl, item.lower()).strip("-")
                        cleaned = re.sub(r"-{2,}", "-", cleaned)
                        new_list.append(cleaned or item)
                    else:
                        new_list.append(item)
                if changed:
                    el.attributes[attr_key] = new_list

    docname = getattr(env, "docname", None)
    if docname and hasattr(env, "metadata") and docname in env.metadata:
        meta = env.metadata[docname]
        for k, v in list(meta.items()):
            if isinstance(v, str) and "PHOTONMATHPLACEHOLDER" in v:
                meta[k] = _restore_math_string(v, store)


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
    app.connect("source-read", _on_sphinx_source_read)
    app.connect("doctree-read", _on_sphinx_doctree_read)
    for node_cls, visit_fn, depart_fn in _NODE_VISITORS:
        app.add_node(
            node_cls,
            html=(visit_fn, depart_fn),
            epub=(visit_fn, depart_fn),
            override=True,
        )
    for name, directive_cls in _DIRECTIVES.items():
        app.add_directive(name, directive_cls, override=True)

    app.add_js_file("js/geometor_interactive.js")
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
