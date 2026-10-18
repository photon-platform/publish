"""Directives for image processing."""

import os
from typing import Any, List

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.writers._html_base import HTMLTranslator as BaseHTMLTranslator
from docutils.writers.html5_polyglot import HTMLTranslator as HTML5Translator


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

        node = picture_node()
        node['main_src'] = variants['main']
        node['fallback_src'] = fallback_src
        node['linked_src'] = linked_src
        node['is_svg'] = is_svg
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
