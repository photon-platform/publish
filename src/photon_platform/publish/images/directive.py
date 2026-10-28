"""Directives for image processing."""

import os
import re
from pathlib import Path
from typing import Any, List

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator


def prepare_inline_svg(svg_path: Path | str, as_thumbnail: bool = False) -> str | None:
    """Read an SVG file and prepare it for inline HTML rendering controlled by global CSS.

    Strips XML/DOCTYPE headers, embedded <style> blocks, and hardcoded background <rect>
    elements so theme CSS variables (--geom-fg, --geom-bg, etc.) govern light/dark mode.
    When as_thumbnail is True, also strips hidden highlight overlays and element IDs to
    avoid duplicate DOM IDs on collection index pages.
    """
    path = Path(svg_path)
    if not path.is_file():
        return None
    try:
        raw_svg = path.read_text(encoding='utf-8').strip()
        raw_svg = re.sub(r'^<\?xml[^>]*\?>\s*', '', raw_svg)
        raw_svg = re.sub(r'^<!DOCTYPE[^>]*>\s*', '', raw_svg)
        # Strip embedded <style> blocks so global CSS controls colors and light/dark mode
        raw_svg = re.sub(r'\s*<style[^>]*>.*?</style>', '', raw_svg, flags=re.S)
        # Strip full-bleed background rects
        raw_svg = re.sub(
            r'\s*(?:<!--\s*Background\s*-->\s*)?<rect\b[^>]*(?:width="100%"[^>]*height="100%"|class="(?:bg|facsimile-bg)")[^>]*/>',
            '',
            raw_svg,
        )
        stem = path.stem
        if 'data-graphic-id=' not in raw_svg:
            raw_svg = re.sub(
                r'<svg\b',
                f'<svg class="euclid-graphic" data-graphic-id="{stem}"',
                raw_svg,
                count=1,
            )
        elif 'class="euclid-graphic"' not in raw_svg and 'euclid-graphic' not in raw_svg:
            raw_svg = re.sub(
                r'<svg\b',
                '<svg class="euclid-graphic"',
                raw_svg,
                count=1,
            )

        if as_thumbnail:
            # Strip hidden interactive highlight overlay group
            raw_svg = re.sub(
                r'\s*(?:<!--[^>]*Highlight[^>]*-->\s*)?<g\s+id="highlights"[^>]*>.*?</g>',
                '',
                raw_svg,
                flags=re.S,
            )
            # Separate opening <svg ...> tag from body to strip inner IDs and data-ref attributes
            m = re.match(r'^(<svg\b[^>]*>)(.*)$', raw_svg, flags=re.S)
            if m:
                svg_open, svg_body = m.group(1), m.group(2)
                svg_open = svg_open.replace(
                    'class="euclid-graphic"',
                    'class="euclid-graphic euclid-thumbnail"',
                )
                svg_body = re.sub(
                    r'\s+(?:id|data-ref|data-aliases|data-type)="[^"]*"',
                    '',
                    svg_body,
                )
                raw_svg = svg_open + svg_body

        return raw_svg.strip()
    except Exception:
        return None


class picture_node(nodes.General, nodes.Element):
    """Custom node for containing responsive picture elements."""

    pass


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
    or a clean <figure class="photon-picture photon-svg"><img .../></figure> for SVGs
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
    pass


class PictureDirective(Directive):
    """Directive for inserting responsive pictures and interactive SVG figures."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'alt': directives.unchanged,
        'class': directives.class_option,
        'caption': directives.unchanged,
    }

    @property
    def env(self) -> Any:
        """Return the Sphinx BuildEnvironment if running inside Sphinx, else None."""
        return getattr(self.state.document.settings, "env", None)

    def run(self) -> List[nodes.Node]:
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
        from pathlib import Path
        import re
        from .processor import ImageProcessor

        if image_path_arg.startswith('/'):
            rel_path = image_path_arg.lstrip('/')
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
            logger = self.env.app.logger
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
        if is_svg:
            abs_svg_path = (Path(self.env.app.srcdir) / rel_path).resolve()
            svg_content = prepare_inline_svg(abs_svg_path)

        node = picture_node()
        node['main_src'] = variants['main']
        node['fallback_src'] = fallback_src
        node['linked_src'] = linked_src
        node['is_svg'] = is_svg
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
        setattr(translator_cls, 'visit_picture_node', visit_picture_node)
        setattr(translator_cls, 'depart_picture_node', depart_picture_node)
