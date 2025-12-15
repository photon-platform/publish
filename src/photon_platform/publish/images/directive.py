"""Directives for image processing."""

import os
from typing import Any, List

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from .processor import ImageProcessor

class picture_node(nodes.General, nodes.Element):
    """Custom node for containing responsive picture elements."""

    pass

def visit_picture_node(self: Any, node: nodes.Element) -> None:
    """HTML visitor for picture_node.

    Renders a standard <figure> with nested <picture> element.

    Args:
        self: The translator instance.
        node: The picture_node being visited.

    """
    atts = {}
    # docutils 'starttag' expects 'class' in atts to be a string, not a list.
    # We should rely on node['classes'] if possible, but if we stored it in node['class']
    # we can pass it, but must join it.
    if 'class' in node:
        atts['class'] = ' '.join(node['class'])
    
    # Start figure container
    self.body.append(self.starttag(node, 'figure', **atts))
    
    # Link to original image
    if 'linked_src' in node:
        src = relative_uri(self.builder.current_docname, node['linked_src'])
        self.body.append(f'<a href="{src}">\n')

    # Picture element
    self.body.append('<picture>\n')
    
    # WebP Source
    if 'main_src' in node:
        src = relative_uri(self.builder.current_docname, node['main_src'])
        self.body.append(f'<source srcset="{src}" type="image/webp">\n')
    
    # Fallback IMG
    # We use the processed MAIN image as the src here because it's optimized,
    # but strictly speaking for a fallback we might want the original JPG if WebP isn't supported?
    # However, modern Picture usage often uses the primary opt format as source.
    # But wait, <img> src usually points to a fallback format (JPG/PNG).
    # Our processor currently ONLY produces WebP.
    # TODO: Add logic to copy original file to _images as fallback if strict compat needed.
    # For now, we point to the high-quality WebP as the main <img> src, assuming modern browser support,
    # OR we can assume the user provided a jpg/png and we should copy that too?
    # Let's stick to the spec: "Render a picture_node... <source srcset=...webp> <img src=...jpg>"
    
    # Updating logic: We need to copy the ORIGINAL file to the build dir for the <img> src fallback.
    
    fallback_src = node.get('fallback_src', '')
    if fallback_src:
        fallback_src = relative_uri(self.builder.current_docname, fallback_src)
    
    img_atts = {
        'src': fallback_src,
        'alt': node.get('alt', ''),
        # 'width': '800', # Implicit max width from specs
        # 'height': ... # We'd need to calculate this content-dependently to prevent CLS
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
    
    raise nodes.SkipNode # We handled the whole subtree

def depart_picture_node(self: Any, node: nodes.Element) -> None:
    """Departure visitor for picture_node.

    Args:
        self: The translator instance.
        node: The picture_node being visited.

    """
    pass

class PictureDirective(SphinxDirective):
    """Directive for inserting responsive pictures."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'alt': directives.unchanged,
        'class': directives.class_option,
        'caption': directives.unchanged,
    }

    def run(self) -> List[nodes.Node]:
        """Process the picture directive.

        Returns:
            A list containing the picture_node.

        """
        # File path from argument
        image_path_arg = self.arguments[0]
        
        # Processor needs a reliable way to find the file
        # If path is absolute (starting with /), it is relative to srcdir
        # If relative, it is relative to current doc
        
        if image_path_arg.startswith('/'):
            rel_path = image_path_arg.lstrip('/')
        else:
            # Resolve relative to current document location
            # env.docname is "folder/file" (no extension)
            doc_dir = os.path.dirname(self.env.docname)
            rel_path = os.path.join(doc_dir, image_path_arg)
            
        processor = ImageProcessor(self.env.app)
        
        try:
            # This generates WebP variants and copies original
            variants = processor.process_image(rel_path)
            
            fallback_src = variants['original']
            linked_src = variants['original']
            
        except FileNotFoundError:
            # Warn and return a basic error node or plain image
            logger = self.env.app.logger
            logger.warning(f'Featured Image not found: {image_path_arg}', location=self.get_location())
            return []
            
        # Store metadata for thumbnails
        if 'featured_image' not in self.env.metadata[self.env.docname]:
            self.env.metadata[self.env.docname]['featured_image'] = variants['thumb']
            
        # Create Node
        node = picture_node()
        node['main_src'] = variants['main']
        node['fallback_src'] = fallback_src
        node['linked_src'] = linked_src
        node['alt'] = self.options.get('alt', '')
        node['caption'] = self.options.get('caption', '')
        node['class'] = self.options.get('class', [])
        
        # Add 'photon-picture' class by default
        if isinstance(node['class'], list):
            node['class'].append('photon-picture')
        else:
            node['class'] = ['photon-picture']
            
        return [node]
