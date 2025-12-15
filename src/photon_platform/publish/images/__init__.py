"""Image processing and directive registration."""

from .directive import PictureDirective, picture_node, visit_picture_node, depart_picture_node
from typing import Any, Dict

def setup(app: Any) -> Dict[str, Any]:
    """Register directives and nodes.

    Args:
        app: The Sphinx application instance.

    Returns:
        Extension metadata.

    """
    app.add_node(picture_node, html=(visit_picture_node, depart_picture_node))
    app.add_directive('picture', PictureDirective)
