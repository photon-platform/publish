"""Directives for image processing."""

import hashlib
import os
import re
from pathlib import Path
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator

_GLOBAL_THEME_VARS = frozenset({
    '--geom-fg',
    '--geom-bg',
    '--geom-point-stroke',
    '--geom-poly-fill',
    '--geom-accent',
    '--geom-accent-bg',
    '--geom-accent-border',
    '--geom-assert',
    '--geom-assert-bg',
    '--geom-assert-border',
    '--geom-coincide',
    '--geom-coincide-bg',
    '--geom-coincide-border',
    '--geom-font-sans',
})

_ROOT_BOX_PROPS = frozenset({
    'background',
    'background-color',
    'border',
    'border-color',
    'border-width',
    'border-style',
    'border-radius',
    'width',
    'height',
    'max-width',
    'max-height',
    'min-width',
    'min-height',
    'margin',
    'margin-top',
    'margin-bottom',
    'margin-left',
    'margin-right',
    'padding',
    'display',
    'box-shadow',
    'overflow',
    'cursor',
})

_BG_RECT_TOKENS = frozenset({
    '.bg',
    '.svg-bg',
    '.facsimile-bg',
    'rect.bg',
    'rect.svg-bg',
    'rect.facsimile-bg',
})

_LEGACY_STANDARD_SELECTORS = frozenset({
    'svg',
    '.euclid-graphic',
    'svg.euclid-graphic',
    '.bg',
    '.svg-bg',
    '.facsimile-bg',
    '.geom-line',
    '.line',
    '.element',
    '.graphic-seg',
    '.geom-bold',
    '.geom-circle',
    '.geom-curve',
    '.geom-ellipse',
    '.geom-arc',
    '.geom-dashed',
    '.geom-line-dashed',
    '.geom-arc-dashed',
    '.geom-aux',
    '.geom-Auxiliary',
    '.geom-construction',
    '.geom-arc-dotted',
    '.geom-ray',
    '.geom-tick',
    '.grid-line',
    '.geom-polygon',
    '.poly',
    '.graphic-poly',
    '.geom-polygon-bordered',
    '.geom-polygon-stroked',
    '.geom-space',
    '.geom-polygon-gnomon',
    '.wedge',
    '.angle',
    '.graphic-wedge',
    '.geom-ang-arc',
    '.geom-tick-mark',
    '.geom-point',
    '.point',
    '.geom-dot',
    '.geom-label',
    '.label',
    '.lbl',
    '.geom-label-roman',
    '.geom-label-sm',
    '.geom-label-sub',
    '.geom-overlay',
})


def _split_top_level(text: str, sep: str) -> list[str]:
    """Split text on single-character separator outside parentheses and quotes."""
    parts: list[str] = []
    buf: list[str] = []
    paren = 0
    quote: str | None = None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
        elif ch == '(':
            paren += 1
            buf.append(ch)
        elif ch == ')':
            paren = max(0, paren - 1)
            buf.append(ch)
        elif ch == sep and paren == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf))
    return parts


def _iter_css_blocks(css_text: str) -> list[tuple[str, str]]:
    """Parse top-level CSS `{ ... }` blocks into `(prelude, body)` pairs."""
    blocks: list[tuple[str, str]] = []
    n = len(css_text)
    i = 0
    start = 0
    depth = 0
    body_start = 0
    prelude = ''
    quote: str | None = None

    while i < n:
        ch = css_text[i]
        if quote:
            if ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == '{':
            if depth == 0:
                prelude = css_text[start:i].strip()
                body_start = i + 1
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0:
                    body = css_text[body_start:i].strip()
                    if prelude:
                        blocks.append((prelude, body))
                    start = i + 1
        elif ch == ';' and depth == 0:
            # Skip standalone @charset / @import statements
            start = i + 1
        i += 1
    return blocks


def _is_legacy_standard_selector(sel: str, root_classes: set[str]) -> bool:
    """Return True if selector only targets standard `_geometor.scss` base/highlight classes."""
    s = sel.strip()
    if not s:
        return True
    if any(tok in s for tok in ('[data-ref]', '.highlight', '.geom-highlight-')):
        return True
    for rc in sorted(root_classes, key=len, reverse=True):
        for prefix in (f'svg.{rc}', f'.{rc}'):
            if s == prefix:
                return True
            if s.startswith(prefix + ' '):
                s = s[len(prefix):].strip()
                break
    s_base = re.sub(r':(?:hover|active|focus)\b', '', s).strip()
    return s_base in _LEGACY_STANDARD_SELECTORS


def _scope_single_selector(
    sel: str, scope_sel: str, root_classes: set[str]
) -> tuple[str | None, bool]:
    """Scope a single CSS selector to `scope_sel`; return `(scoped, is_root_selector)`."""
    s = ' '.join(sel.strip().split())
    if not s:
        return None, False
    if s == ':root':
        return scope_sel, True
    if s in _BG_RECT_TOKENS:
        return None, False

    root_prefixes = ['svg']
    for rc in sorted(root_classes, key=len, reverse=True):
        root_prefixes.append(f'svg.{rc}')
        root_prefixes.append(f'.{rc}')

    for rp in root_prefixes:
        if s == rp:
            return scope_sel, True
        if s.startswith(rp):
            rest = s[len(rp):]
            if rest.startswith((':', '.')) and ' ' not in rest and '>' not in rest:
                return f'{scope_sel}{rest}', True
            if rest.startswith((' ', '>', '+', '~')):
                inner = rest.strip()
                if inner in _BG_RECT_TOKENS:
                    return None, False
                return f'{scope_sel}{rest}', False

    return f'{scope_sel} {s}', False


def _filter_declarations(
    decls: str, *, is_root_selector: bool = False
) -> str:
    """Filter CSS declarations, stripping root container box overrides and global theme clobbers."""
    kept: list[str] = []
    for raw_decl in _split_top_level(decls, ';'):
        decl = raw_decl.strip()
        if not decl or ':' not in decl:
            continue
        prop, val = decl.split(':', 1)
        prop_l = prop.strip().lower()
        val_s = val.strip()
        if not prop_l or not val_s:
            continue
        if is_root_selector and (prop_l in _GLOBAL_THEME_VARS or prop_l in _ROOT_BOX_PROPS):
            continue
        kept.append(f'{prop.strip()}: {val_s}')
    return '; '.join(kept)


def _scope_rule_blocks(
    blocks: list[tuple[str, str]],
    scope_sel: str,
    root_classes: set[str],
    *,
    has_color_scheme_media: bool,
    theme_mode: str = '',
) -> list[str]:
    """Scope a list of `(prelude, body)` rule blocks."""
    out: list[str] = []
    for prelude, body in blocks:
        p_low = prelude.lower()
        if p_low.startswith('@keyframes'):
            out.append(f'{prelude} {{ {body} }}')
            continue
        if p_low.startswith('@media'):
            inner_blocks = _iter_css_blocks(body)
            if 'prefers-color-scheme' in p_low and 'dark' in p_low:
                out.extend(
                    _scope_rule_blocks(
                        inner_blocks,
                        scope_sel,
                        root_classes,
                        has_color_scheme_media=True,
                        theme_mode='dark',
                    )
                )
            elif 'prefers-color-scheme' in p_low and 'light' in p_low:
                out.extend(
                    _scope_rule_blocks(
                        inner_blocks,
                        scope_sel,
                        root_classes,
                        has_color_scheme_media=True,
                        theme_mode='light',
                    )
                )
            else:
                scoped_inner = _scope_rule_blocks(
                    inner_blocks,
                    scope_sel,
                    root_classes,
                    has_color_scheme_media=has_color_scheme_media,
                    theme_mode=theme_mode,
                )
                if scoped_inner:
                    out.append(f'{prelude} {{ {" ".join(scoped_inner)} }}')
            continue
        if prelude.startswith('@'):
            continue

        raw_sels = [s.strip() for s in _split_top_level(prelude, ',') if s.strip()]
        if not raw_sels:
            continue
        if not has_color_scheme_media and all(
            _is_legacy_standard_selector(s, root_classes) for s in raw_sels
        ):
            continue

        scoped_pairs = [
            _scope_single_selector(s, scope_sel, root_classes) for s in raw_sels
        ]
        valid_pairs = [(sc, is_r) for sc, is_r in scoped_pairs if sc is not None]
        if not valid_pairs:
            continue

        all_root = all(is_r for _, is_r in valid_pairs)
        filtered_body = _filter_declarations(body, is_root_selector=all_root)
        if not filtered_body:
            continue

        final_sels: list[str] = []
        for sc, _ in valid_pairs:
            if theme_mode == 'dark':
                final_sels.append(
                    f'body:not(.light-mode):not([data-theme="light"]) {sc}'
                )
            elif theme_mode == 'light':
                final_sels.append(f'body.light-mode {sc}')
                final_sels.append(f'[data-theme="light"] {sc}')
            else:
                final_sels.append(sc)
        out.append(f'{", ".join(final_sels)} {{ {filtered_body} }}')
    return out


def _scope_svg_styles(
    css_raw: str, scope_id: str, root_classes: set[str]
) -> str:
    """Scope embedded SVG CSS safely to `svg[data-svg-scope="..."]` with codex light/dark parity."""
    cleaned = re.sub(r'/\*.*?\*/', '', css_raw, flags=re.DOTALL).strip()
    if not cleaned:
        return ''
    blocks = _iter_css_blocks(cleaned)
    if not blocks:
        return ''
    has_color_scheme_media = any(
        prelude.lower().startswith('@media')
        and 'prefers-color-scheme' in prelude.lower()
        for prelude, _ in blocks
    )
    scope_sel = f'svg[data-svg-scope="{scope_id}"]'
    scoped_rules = _scope_rule_blocks(
        blocks,
        scope_sel,
        root_classes,
        has_color_scheme_media=has_color_scheme_media,
    )
    return '\n    '.join(scoped_rules)


def _fmt_svg_px(val: float) -> str:
    rounded = round(val)
    if abs(val - rounded) < 0.05:
        return str(int(rounded))
    return f'{val:.1f}'


def _normalize_svg_open_tag(
    svg_open: str,
    stem: str,
    *,
    as_thumbnail: bool,
    scope_id: str | None,
) -> tuple[str, set[str]]:
    """Normalize `<svg ...>` attributes: deduplicate classes, inject intrinsic width/height from viewBox."""
    self_closing = svg_open.rstrip().endswith('/>')
    inner = re.sub(r'^<svg\b', '', svg_open, count=1)
    inner = re.sub(r'/?>\s*$', '', inner)

    attr_pattern = re.compile(
        r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')'
    )
    attrs: list[tuple[str, str]] = []
    orig_classes: list[str] = []
    attr_map: dict[str, str] = {}

    for m in attr_pattern.finditer(inner):
        name = m.group(1)
        val = m.group(2) if m.group(2) is not None else (m.group(3) or '')
        if name == 'class':
            for tok in val.split():
                if tok not in orig_classes:
                    orig_classes.append(tok)
            continue
        if as_thumbnail and name == 'id':
            continue
        if name == 'data-svg-scope':
            continue
        attrs.append((name, val))
        attr_map[name.lower()] = val

    final_classes = ['euclid-graphic']
    if as_thumbnail:
        final_classes.append('euclid-thumbnail')
    for tok in orig_classes:
        if tok not in final_classes:
            final_classes.append(tok)

    root_classes = set(orig_classes) | {'euclid-graphic'}

    # Auto-inject explicit pixel width & height from viewBox when missing or percentage/auto
    w_raw = attr_map.get('width', '').strip().lower()
    needs_intrinsic_dims = (
        not w_raw or w_raw == 'auto' or w_raw.endswith('%')
    )
    if needs_intrinsic_dims and 'viewbox' in attr_map:
        vb_parts = [
            p for p in re.split(r'[\s,]+', attr_map['viewbox'].strip()) if p
        ]
        if len(vb_parts) == 4:
            try:
                vb_w = float(vb_parts[2])
                vb_h = float(vb_parts[3])
                if vb_w > 0 and vb_h > 0:
                    max_dim = max(vb_w, vb_h)
                    if max_dim < 120.0:
                        scale = 600.0 / max_dim
                        px_w, px_h = vb_w * scale, vb_h * scale
                    else:
                        px_w, px_h = vb_w, vb_h
                    attrs = [
                        (k, v)
                        for k, v in attrs
                        if k.lower() not in ('width', 'height')
                    ]
                    attrs.append(('width', _fmt_svg_px(px_w)))
                    attrs.append(('height', _fmt_svg_px(px_h)))
            except ValueError:
                pass

    if 'data-graphic-id' not in attr_map:
        attrs.append(('data-graphic-id', stem))
    if scope_id:
        attrs.append(('data-svg-scope', scope_id))

    serialized = [f'class="{" ".join(final_classes)}"']
    for k, v in attrs:
        serialized.append(f'{k}="{v}"')
    close_tok = '/>' if self_closing else '>'
    return f'<svg {" ".join(serialized)}{close_tok}', root_classes


def prepare_inline_svg(svg_path: Path | str, as_thumbnail: bool = False) -> str | None:
    """Read an SVG file and prepare it for inline HTML rendering.

    - Strips XML/DOCTYPE headers and full-bleed background `<rect>` elements.
    - Injects intrinsic numeric `width` and `height` attributes derived from `viewBox`
      whenever `width` is absent, `auto`, or `%` (preventing `0px` collapse inside
      `width: fit-content` figure containers).
    - Preserves custom `<style>` blocks safely scoped per-SVG via `data-svg-scope`
      with Book Codex Nocturnal / `body.light-mode` theme adaptation, while dropping
      legacy light-only boilerplate styles already governed by `_geometor.scss`.
    - When `as_thumbnail` is True, strips hidden highlight overlays and DOM IDs to
      avoid duplicate IDs on collection index pages.
    """
    path = Path(svg_path)
    if not path.is_file():
        return None
    try:
        raw_svg = path.read_text(encoding='utf-8').strip()
        raw_svg = re.sub(r'^<\?xml[^>]*\?>\s*', '', raw_svg)
        raw_svg = re.sub(r'^<!DOCTYPE[^>]*>\s*', '', raw_svg)
        # Self-contained interactive SVGs (e.g. geometor-etc-drawing) should render as static
        # <img> thumbnails in collections, and preserve their own <style>/<script> on article pages.
        if 'geometor-etc-drawing' in raw_svg:
            if as_thumbnail:
                return None
            return raw_svg.strip()

        # Extract embedded <style> blocks before stripping them from raw body
        style_chunks = re.findall(r'<style[^>]*>(.*?)</style>', raw_svg, flags=re.DOTALL)
        raw_svg = re.sub(r'\s*<style[^>]*>.*?</style>', '', raw_svg, flags=re.DOTALL)

        # Strip full-bleed background rects
        raw_svg = re.sub(
            r'\s*(?:<!--\s*Background\s*-->\s*)?<rect\b[^>]*(?:width="100%"[^>]*height="100%"|class="(?:bg|svg-bg|facsimile-bg)")[^>]*/>',
            '',
            raw_svg,
        )

        m_open = re.match(r'^(<svg\b[^>]*>)(.*)$', raw_svg.strip(), flags=re.DOTALL)
        if not m_open:
            return raw_svg.strip()

        svg_open_raw, svg_body = m_open.group(1), m_open.group(2)
        stem = path.stem
        digest = hashlib.sha1(str(path.resolve()).encode('utf-8')).hexdigest()[:8]
        tentative_scope = f's-{digest}'

        # Pre-inspect root classes so we know whether <style> produces scoped rules
        _, root_classes = _normalize_svg_open_tag(
            svg_open_raw, stem, as_thumbnail=as_thumbnail, scope_id=None
        )
        scoped_css = ''
        if style_chunks:
            scoped_css = _scope_svg_styles(
                '\n'.join(style_chunks), tentative_scope, root_classes
            )

        svg_open, _ = _normalize_svg_open_tag(
            svg_open_raw,
            stem,
            as_thumbnail=as_thumbnail,
            scope_id=tentative_scope if scoped_css else None,
        )

        if as_thumbnail:
            svg_body = re.sub(
                r'\s*(?:<!--[^>]*Highlight[^>]*-->\s*)?<g\s+id="highlights"[^>]*>.*?</g>',
                '',
                svg_body,
                flags=re.DOTALL,
            )
            svg_body = re.sub(
                r'\s+(?:id|data-ref|data-aliases|data-type)="[^"]*"',
                '',
                svg_body,
            )

        style_tag = f'\n  <style>\n    {scoped_css}\n  </style>' if scoped_css else ''
        return (svg_open + style_tag + svg_body).strip()
    except (OSError, ValueError):
        return None


class picture_node(nodes.General, nodes.Element):
    """Custom node for containing responsive picture elements."""



def _resolve_node_uri(translator: Any, uri: str) -> str:
    """Resolve URI relative to current Sphinx document, or return as-is in standalone Docutils mode."""
    if not uri:
        return ""
    builder = getattr(translator, "builder", None)
    if builder and hasattr(builder, "current_docname"):
        from sphinx.util.osutil import relative_uri

        return relative_uri(builder.current_docname, uri)
    return uri


def visit_picture_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for picture_node.

    Renders a standard <figure> with nested <picture> element for raster images,
    or a clean <figure class="photon-picture photon-svg"><svg .../></figure> for SVGs
    and standalone Docutils rendering.

    Args:
        self: The translator instance.
        node: The picture_node being visited.

    """
    atts = {}
    if 'class' in node:
        atts['class'] = ' '.join(dict.fromkeys(node['class']))

    # Start figure container
    self.body.append(self.starttag(node, 'figure', **atts))

    is_svg = bool(node.get('is_svg'))
    is_standalone = bool(node.get('standalone'))

    if is_svg or is_standalone:
        svg_content = None
        svg_abs_path = node.get('svg_abs_path')
        if is_svg and not is_standalone and svg_abs_path:
            svg_content = prepare_inline_svg(svg_abs_path)
        if not svg_content:
            svg_content = node.get('svg_content')
        if is_svg and svg_content and not is_standalone:
            self.body.append(f'    {svg_content}\n')
        else:
            fallback_src = _resolve_node_uri(self, node.get('fallback_src') or node.get('main_src', ''))
            alt_text = node.get('alt', '')
            self.body.append(f'    <img src="{fallback_src}" alt="{alt_text}"/>\n')
        if node.get('caption'):
            self.body.append(f'<figcaption>{node["caption"]}</figcaption>\n')
        self.body.append('</figure>\n')
        raise nodes.SkipNode

    # Link to original image
    if 'linked_src' in node:
        src = _resolve_node_uri(self, node['linked_src'])
        self.body.append(f'<a href="{src}">\n')

    # Picture element
    self.body.append('<picture>\n')

    # WebP Source
    if 'main_src' in node:
        src = _resolve_node_uri(self, node['main_src'])
        self.body.append(f'<source srcset="{src}" type="image/webp">\n')

    fallback_src = _resolve_node_uri(self, node.get('fallback_src', ''))

    img_atts = {
        'src': fallback_src,
        'alt': node.get('alt', ''),
    }

    # Construct img tag
    img_tag = '<img ' + ' '.join([f'{k}="{v}"' for k, v in img_atts.items()]) + '>'
    self.body.append(f'    {img_tag}\n')

    self.body.append('</picture>\n')

    if 'linked_src' in node:
        self.body.append('</a>\n')

    # Caption
    if node.get('caption'):
        self.body.append(f'<figcaption>{node["caption"]}</figcaption>\n')

    self.body.append('</figure>\n')

    raise nodes.SkipNode


def depart_picture_node(self: Any, node: nodes.Element) -> None:
    """Departure visitor for picture_node.

    Args:
        self: The translator instance.
        node: The picture_node being visited.

    """


class PictureDirective(Directive):
    """Directive for inserting responsive pictures and interactive SVG figures."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: ClassVar[dict[str, Any]] = {
        'alt': directives.unchanged,
        'class': directives.class_option,
        'caption': directives.unchanged,
    }

    @property
    def env(self) -> Any:
        """Return the Sphinx BuildEnvironment if running inside Sphinx, else None."""
        return getattr(self.state.document.settings, "env", None)

    def run(self) -> list[nodes.Node]:
        """Process the picture directive in either Sphinx or standalone Docutils mode.

        Returns:
            A list containing the picture_node.

        """
        image_path_arg = self.arguments[0].strip()
        is_svg = image_path_arg.lower().endswith('.svg')

        classes = ['photon-picture']
        if is_svg:
            classes.append('photon-svg')
        opt_classes = self.options.get('class', [])
        if isinstance(opt_classes, list):
            for c in opt_classes:
                if c not in classes:
                    classes.append(c)

        # Standalone Docutils mode (e.g., folio_review fast preview)
        if not self.env:
            node = picture_node()
            node['main_src'] = image_path_arg
            node['fallback_src'] = image_path_arg
            node['is_svg'] = is_svg
            node['standalone'] = True
            node['alt'] = self.options.get('alt', '')
            node['caption'] = self.options.get('caption', '')
            node['class'] = classes
            return [node]

        # Sphinx build mode
        from .processor import ImageProcessor

        if image_path_arg.startswith('/'):
            rel_path = image_path_arg.lstrip('/')
            srcdir_path = Path(self.env.app.srcdir)
            if not (srcdir_path / rel_path).exists():
                prefix = f"{srcdir_path.name}/"
                if rel_path.startswith(prefix):
                    stripped = rel_path[len(prefix):]
                    if (srcdir_path / stripped).exists():
                        rel_path = stripped
        else:
            doc_dir = os.path.dirname(self.env.docname)
            rel_path = os.path.join(doc_dir, image_path_arg)

        processor = ImageProcessor(self.env.app)

        try:
            variants = processor.process_image(rel_path)
            fallback_src = variants['original']
            linked_src = variants['original']
            is_svg = is_svg or bool(variants.get('is_svg'))
            if is_svg and 'photon-svg' not in classes:
                classes.insert(1, 'photon-svg')
        except FileNotFoundError:
            from sphinx.util import logging as sphinx_logging

            logger = sphinx_logging.getLogger(__name__)
            logger.warning(
                f'Featured Image not found: {image_path_arg}',
                location=(self.env.docname, self.lineno),
            )
            return []

        if 'featured_image' not in self.env.metadata[self.env.docname]:
            self.env.metadata[self.env.docname]['featured_image'] = variants['thumb']
            if self.options.get('alt'):
                self.env.metadata[self.env.docname]['featured_image_alt'] = self.options['alt']

        svg_content = None
        svg_abs_str = None
        if is_svg:
            abs_svg_path = (Path(self.env.app.srcdir) / rel_path).resolve()
            svg_abs_str = str(abs_svg_path)
            if hasattr(self.env, 'note_dependency'):
                self.env.note_dependency(svg_abs_str)
            svg_content = prepare_inline_svg(abs_svg_path)

        node = picture_node()
        node['main_src'] = variants['main']
        node['fallback_src'] = fallback_src
        node['linked_src'] = linked_src
        node['is_svg'] = is_svg
        if svg_abs_str:
            node['svg_abs_path'] = svg_abs_str
        if svg_content:
            node['svg_content'] = svg_content
        node['alt'] = self.options.get('alt', '')
        node['caption'] = self.options.get('caption', '')
        node['class'] = classes

        return [node]


def register_standalone_picture() -> None:
    """Register picture directive and HTML visitors with standalone Docutils."""
    directives.register_directive('picture', PictureDirective)
    for translator_cls in (BaseHTMLTranslator, HTML5Translator):
        translator_cls.visit_picture_node = visit_picture_node
        translator_cls.depart_picture_node = depart_picture_node
